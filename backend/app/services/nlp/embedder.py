"""
Embedding service using sentence-transformers.
Generates dense vector representations for reviews (used in Q&A / vector search).
"""
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None


def get_model():
    """Lazy-load the embedding model (heavy, load once)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            _model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def embed_text(text: str) -> list[float]:
    """Generate embedding vector for a single text."""
    if not text or not text.strip():
        return []
    try:
        model = get_model()
        vector = model.encode(text[:512], normalize_embeddings=True)
        return vector.tolist()
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts. More efficient than one-by-one."""
    if not texts:
        return []
    try:
        model = get_model()
        # Truncate each text
        truncated = [t[:512] for t in texts]
        vectors = model.encode(truncated, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        return [v.tolist() for v in vectors]
    except Exception as e:
        logger.error(f"Batch embedding error: {e}")
        return [[] for _ in texts]
