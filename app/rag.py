"""Retrieval over the JSON index built by ingest.py.

Deliberately simple: load embeddings into numpy, cosine similarity,
return the top_k chunks. No database to operate for v1.
"""

import json

import numpy as np
from openai import OpenAI

from app.config import EMBED_MODEL, INDEX_PATH, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

_texts: list[str] = []
_sources: list[str] = []
_matrix: np.ndarray | None = None


def _load() -> None:
    global _texts, _sources, _matrix
    if _matrix is not None:
        return
    with open(INDEX_PATH) as f:
        index = json.load(f)
    _texts = [c["text"] for c in index]
    _sources = [c["source"] for c in index]
    mat = np.array([c["embedding"] for c in index], dtype=np.float32)
    # Normalize once so search is a single dot product.
    _matrix = mat / np.linalg.norm(mat, axis=1, keepdims=True)


def retrieve(query: str, top_k: int = 4) -> list[dict]:
    _load()
    assert _matrix is not None

    resp = client.embeddings.create(model=EMBED_MODEL, input=query)
    q = np.array(resp.data[0].embedding, dtype=np.float32)
    q = q / np.linalg.norm(q)

    scores = _matrix @ q
    top = np.argsort(scores)[::-1][:top_k]
    return [
        {"text": _texts[i], "source": _sources[i], "score": float(scores[i])}
        for i in top
    ]
