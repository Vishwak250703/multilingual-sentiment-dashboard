"""
Shared ChromaDB client factory.

Supports two modes controlled by the CHROMA_MODE env var:
  http      — HttpClient pointing at a separate chromadb container (default, used in Docker)
  embedded  — PersistentClient running inside this process (used on free cloud platforms)
"""
import logging
import os

logger = logging.getLogger(__name__)

_client = None


def get_chroma_client():
    """Return a module-level singleton ChromaDB client."""
    global _client
    if _client is not None:
        return _client

    import chromadb
    from app.core.config import settings

    if settings.CHROMA_MODE == "embedded":
        os.makedirs(settings.CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
        logger.info(f"ChromaDB: embedded PersistentClient at {settings.CHROMA_PATH}")
    else:
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        logger.info(f"ChromaDB: HttpClient → {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")

    return _client


def get_chroma_collection(tenant_id: str):
    """Get or create a per-tenant ChromaDB collection."""
    client = get_chroma_client()
    collection_name = f"reviews_{tenant_id.replace('-', '_')}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )
