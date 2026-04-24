"""
Chat with Data — vector search + Claude Q&A pipeline.
Flow: embed question → ChromaDB search → fetch reviews → Claude → parse chart → respond
"""
import json
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.schemas.chat import ChatRequest, ChatResponse, ChartData, ChatMessage
from app.models.review import Review
from app.models.user import User
from anthropic import Anthropic

router = APIRouter()
logger = logging.getLogger(__name__)

_claude_client: Optional[Anthropic] = None


def _get_claude() -> Anthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _claude_client


# ─── Sync helpers (run in threadpool) ─────────────────────────────────────────

def _embed_and_search(question: str, tenant_id: str, n_results: int = 8) -> list[str]:
    """Embed the question and query ChromaDB for similar review IDs."""
    try:
        from app.services.nlp.embedder import embed_text
        from app.core.chroma import get_chroma_client

        vector = embed_text(question)
        if not vector:
            return []

        client = get_chroma_client()
        collection_name = f"reviews_{tenant_id.replace('-', '_')}"

        try:
            collection = client.get_collection(collection_name)
        except Exception:
            # Collection doesn't exist yet — no reviews have been embedded
            return []

        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_embeddings=[vector],
            n_results=min(n_results, count),
            include=["documents", "metadatas"],
        )
        return results.get("ids", [[]])[0]

    except Exception as e:
        logger.error(f"Vector search error: {e}")
        return []


# ─── Claude system prompt ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert customer experience analyst with access to real customer review data.
You help business owners understand their customer feedback and make data-driven decisions.

Guidelines:
- Answer ONLY based on the provided customer review context
- Be specific — cite numbers, percentages, and direct quotes when possible
- Keep answers concise (2-3 paragraphs max)
- If the provided context doesn't contain enough data for the question, say so honestly
- Do not make up data not present in the context

When the user asks for a chart or visualization (or when a chart would clearly help), append a chart block at the END of your response using this exact format:
<chart>
{"chart_type": "bar", "title": "Chart Title", "data": [{"label": "X", "value": 10}], "x_key": "label", "y_key": "value"}
</chart>

Supported chart_type values: "bar", "line", "pie"
For "pie" charts, data items need "name" and "value" keys.
For "bar" and "line" charts, use "x_key" and "y_key" to specify which data keys to plot."""


# ─── Route ─────────────────────────────────────────────────────────────────────

@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Q&A over review data — vector search → context → Claude → optional chart."""
    tenant_id = current_user.tenant_id

    # ── Step 1: Vector search (sync in threadpool) ──────────────────────────
    review_ids = await asyncio.to_thread(
        _embed_and_search, body.question, tenant_id
    )

    # ── Step 2: Fetch matched reviews from PostgreSQL ───────────────────────
    context_reviews: list[dict] = []
    if review_ids:
        result = await db.execute(
            select(Review).where(
                and_(
                    Review.tenant_id == tenant_id,
                    Review.id.in_(review_ids),
                    Review.processing_status == "completed",
                )
            ).limit(8)
        )
        db_reviews = result.scalars().all()
        context_reviews = [
            {
                "id": r.id,
                "text": r.translated_text or r.raw_text,
                "sentiment": r.sentiment or "neutral",
                "score": round(r.sentiment_score or 0.0, 2),
                "source": r.source,
                "product_id": r.product_id,
                "aspects": r.aspects or {},
                "keywords": r.keywords or [],
                "date": r.review_date.isoformat() if r.review_date else None,
            }
            for r in db_reviews
        ]

    # ── Step 3: Build context string for Claude ─────────────────────────────
    if context_reviews:
        lines = []
        for i, r in enumerate(context_reviews, 1):
            meta = f"sentiment={r['sentiment']} score={r['score']}"
            if r["product_id"]:
                meta += f" product={r['product_id']}"
            meta += f" source={r['source']}"
            lines.append(f"[Review {i} | {meta}]\n{r['text'][:500]}")
        context_str = "\n\n".join(lines)
    else:
        context_str = "No matching reviews found in the database. The database may be empty or embeddings haven't been generated yet."

    # ── Step 4: Build conversation messages ─────────────────────────────────
    messages: list[dict] = []

    # Inject prior conversation turns (without the context — keep it lean)
    for msg in (body.conversation_history or []):
        messages.append({"role": msg.role, "content": msg.content})

    # Current turn: inject retrieved context + question
    user_content = f"""Relevant customer reviews from our database:

{context_str}

---
Question: {body.question}"""
    messages.append({"role": "user", "content": user_content})

    # ── Step 5: Call Claude (sync in threadpool) ─────────────────────────────
    try:
        raw_answer = await asyncio.to_thread(
            lambda: _get_claude().messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            ).content[0].text.strip()
        )
    except Exception as e:
        logger.error(f"Claude chat error: {e}")
        return ChatResponse(
            answer="I'm having trouble connecting to the AI engine. Please try again in a moment.",
            chart=None,
            supporting_reviews=[],
            confidence=0.0,
        )

    # ── Step 6: Extract optional chart block ─────────────────────────────────
    chart: Optional[ChartData] = None
    answer = raw_answer

    if "<chart>" in raw_answer and "</chart>" in raw_answer:
        try:
            c_start = raw_answer.index("<chart>") + len("<chart>")
            c_end = raw_answer.index("</chart>")
            chart_json = raw_answer[c_start:c_end].strip()
            chart_data = json.loads(chart_json)
            chart = ChartData(
                chart_type=chart_data.get("chart_type", "bar"),
                title=chart_data.get("title", "Chart"),
                data=chart_data.get("data", []),
                x_key=chart_data.get("x_key"),
                y_key=chart_data.get("y_key"),
            )
            # Strip chart block from answer text
            answer = (
                raw_answer[: raw_answer.index("<chart>")]
                + raw_answer[raw_answer.index("</chart>") + len("</chart>"):]
            ).strip()
        except Exception as e:
            logger.warning(f"Chart parse failed (non-critical): {e}")

    # ── Step 7: Build supporting review snippets ─────────────────────────────
    supporting = [
        {
            "id": r["id"],
            "text": r["text"][:200] + ("…" if len(r["text"]) > 200 else ""),
            "sentiment": r["sentiment"],
            "source": r["source"],
        }
        for r in context_reviews[:3]
    ]

    confidence = 0.85 if len(context_reviews) >= 3 else (0.6 if context_reviews else 0.2)

    return ChatResponse(
        answer=answer,
        chart=chart,
        supporting_reviews=supporting,
        confidence=round(confidence, 2),
    )
