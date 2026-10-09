"""Retrieval for ShopAssist: pgvector top-8 -> rerank -> top-3, with citations.

This is the Part 2 pipeline in code:
  1. cosine search in pgvector, take top-8 candidates
  2. down-rank deprecated docs (freshness filter)
  3. heuristic rerank on keyword overlap, keep top-3
  4. every chunk carries a citation: source file + line range
"""

import re

import psycopg
from openai import OpenAI
from pgvector.psycopg import register_vector

from app.config import (
    DATABASE_URL,
    EMBED_MODEL,
    FRESHNESS_PENALTY,
    OPENAI_API_KEY,
    RERANK_TOP_K,
    RETRIEVE_TOP_K,
)

client = OpenAI(api_key=OPENAI_API_KEY)


def _get_conn():
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def _keyword_overlap(query: str, text: str) -> float:
    # Cheap rerank signal: fraction of meaningful query words found in the chunk.
    # No cross-encoder yet — cosine plus this gets us surprisingly far.
    stop = {
        "what", "whats", "is", "the", "a", "an", "my", "i", "do", "does",
        "how", "to", "of", "for", "in", "on", "it", "are", "can", "your",
    }
    words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in stop}
    if not words:
        return 0.0
    lowered = text.lower()
    return sum(1 for w in words if w in lowered) / len(words)


def retrieve(query: str, top_k: int = RERANK_TOP_K) -> list[dict]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=query)
    qvec = resp.data[0].embedding

    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT text, source, line_start, line_end, is_deprecated,
                   embedding <=> %s AS distance
            FROM chunks
            ORDER BY distance
            LIMIT %s
            """,
            (qvec, RETRIEVE_TOP_K),
        ).fetchall()

    scored = []
    for text, source, line_start, line_end, is_deprecated, distance in rows:
        score = 1.0 - float(distance)  # cosine distance -> similarity
        if is_deprecated:
            score *= FRESHNESS_PENALTY  # old policies sink; they don't disappear
        score = 0.7 * score + 0.3 * _keyword_overlap(query, text)
        scored.append(
            {
                "text": text,
                "source": source,
                "score": score,
                "citation": f"{source}#L{line_start}-L{line_end}",
            }
        )
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]
