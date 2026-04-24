"""
Celery tasks for generating and storing review embeddings in ChromaDB.
"""
import logging
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_chroma_collection(tenant_id: str):
    """Get or create a ChromaDB collection for a tenant."""
    from app.core.chroma import get_chroma_collection
    return get_chroma_collection(tenant_id)


@celery_app.task(
    name="app.tasks.embed_reviews.embed_review",
    queue="nlp",
    max_retries=3,
    default_retry_delay=10,
)
def embed_review(review_id: str, text: str, tenant_id: str):
    """Generate embedding for a single review and upsert into ChromaDB."""
    if not text or not text.strip():
        return

    try:
        from app.services.nlp.embedder import embed_text

        vector = embed_text(text)
        if not vector:
            logger.warning(f"Empty embedding for review {review_id}")
            return

        collection = _get_chroma_collection(tenant_id)
        collection.upsert(
            ids=[review_id],
            embeddings=[vector],
            documents=[text[:1000]],
            metadatas=[{"review_id": review_id, "tenant_id": tenant_id}],
        )
        logger.debug(f"Embedded review {review_id}")

    except Exception as e:
        logger.error(f"Embedding failed for {review_id}: {e}")


@celery_app.task(
    name="app.tasks.embed_reviews.batch_embed",
    queue="nlp",
)
def batch_embed(review_ids: list[str], texts: list[str], tenant_id: str):
    """Embed a batch of reviews — more efficient than one-by-one."""
    if not review_ids or not texts:
        return

    try:
        from app.services.nlp.embedder import embed_batch

        vectors = embed_batch(texts)
        if not any(vectors):
            return

        collection = _get_chroma_collection(tenant_id)

        # Filter out empty vectors
        valid = [
            (rid, vec, doc)
            for rid, vec, doc in zip(review_ids, vectors, texts)
            if vec
        ]
        if not valid:
            return

        ids, embeds, docs = zip(*valid)
        collection.upsert(
            ids=list(ids),
            embeddings=list(embeds),
            documents=[d[:1000] for d in docs],
            metadatas=[{"review_id": rid, "tenant_id": tenant_id} for rid in ids],
        )
        logger.info(f"Batch embedded {len(ids)} reviews for tenant {tenant_id}")

    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
