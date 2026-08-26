"""Server-side embeddings using sentence-transformers (local provider).

Lazy-loaded model — first call to embed() loads the model on demand.
No longer auto-loads at startup — configured in Settings → Embedding.
Use 'local' provider for built-in model, or 'api' provider for LLM endpoint."""

import logging

logger = logging.getLogger(__name__)

_MODEL = None
_MODEL_NAME = "all-MiniLM-L6-v2"
_MODEL_LOAD_ERROR = None


def _get_model():
    global _MODEL, _MODEL_LOAD_ERROR
    if _MODEL is not None:
        return _MODEL
    if _MODEL_LOAD_ERROR is not None:
        raise _MODEL_LOAD_ERROR
    try:
        from sentence_transformers import SentenceTransformer
        try:
            _MODEL = SentenceTransformer(_MODEL_NAME)
        except NotImplementedError:
            _MODEL = SentenceTransformer(_MODEL_NAME, device='cpu')
    except Exception as e:
        _MODEL_LOAD_ERROR = e
        logger.error(f"Failed to load embedding model: {e}")
        raise
    return _MODEL


def embed(text: str) -> list:
    """Return a 384-dim embedding vector for the given text."""
    try:
        model = _get_model()
        return model.encode(text, normalize_embeddings=True).tolist()
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return [0.0] * 384  # return zero vector on failure so callers don't crash


def embed_batch(texts: list[str]) -> list[list]:
    """Return embeddings for multiple texts in one call."""
    if not texts:
        return []
    try:
        model = _get_model()
        return model.encode(texts, normalize_embeddings=True).tolist()
    except Exception as e:
        logger.warning(f"Batch embedding failed: {e}")
        return []

