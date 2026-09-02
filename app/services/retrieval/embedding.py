import logfire
from sentence_transformers import SentenceTransformer

BATCH_SIZE = 50
EMBEDDING_DIM = 768  # all-mpnet-base-v2
MODEL_NAME = "all-mpnet-base-v2"

_model: SentenceTransformer | None = None


# ── Model initialisation ───────────────────────────────────────────────────────

def _init():
    """Load the sentence-transformers model once per process (lazy)."""
    global _model
    if _model is not None:
        return
    logfire.info(f"Loading embedding model: {MODEL_NAME} ({EMBEDDING_DIM}-dim, local).")
    _model = SentenceTransformer(MODEL_NAME)


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_embedding_dim() -> int:
    """Return the vector dimension (always 768 for all-mpnet-base-v2)."""
    return EMBEDDING_DIM


# ── Public API ─────────────────────────────────────────────────────────────────

def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    _init()
    return _model.encode([query])[0].tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts in batches."""
    _init()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        with logfire.span("Embed batch", model=MODEL_NAME, start=i, size=len(batch)):
            all_embeddings.extend(_model.encode(batch, show_progress_bar=False).tolist())
    return all_embeddings