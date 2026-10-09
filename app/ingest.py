"""Build the RAG index from data/*.md into pgvector.

Run: python -m app.ingest
Needs: createdb shopassist, then CREATE EXTENSION vector; DATABASE_URL in .env

Pipeline (this is the Part 2 writeup, in code):
  docs -> clean markdown -> 400-token chunks with 50-token overlap
  -> embed -> pgvector table with line numbers + deprecation flags
"""

import glob
import re

import psycopg
from openai import OpenAI
from pgvector.psycopg import register_vector

from app.config import (
    CHUNK_OVERLAP_TOKENS,
    CHUNK_TOKENS,
    DATABASE_URL,
    EMBED_DIM,
    EMBED_MODEL,
    OPENAI_API_KEY,
)

client = OpenAI(api_key=OPENAI_API_KEY)

# Rough token estimate — ~4 chars per token for English text.
# Not exact, but close enough that chunks land where we want them.
CHARS_PER_TOKEN = 4

# If a chunk contains any of these, the doc it came from is probably stale.
DEPRECATED_MARKERS = ("deprecated", "superseded", "no longer valid", "outdated")


def clean_markdown(text: str) -> str:
    # Strip HTML comments, collapse 3+ blank lines, trim trailing whitespace.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def chunk_text(text: str, source: str) -> list[dict]:
    """Sliding-window chunks with line numbers, so answers can cite exact lines."""
    chunk_chars = CHUNK_TOKENS * CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        # Don't cut mid-line — extend to the next newline.
        if end < n:
            nl = text.find("\n", end)
            end = nl if nl != -1 else n
        piece = text[start:end].strip()
        if piece:
            line_start = text.count("\n", 0, start) + 1
            line_end = text.count("\n", 0, end) + 1
            lowered = piece.lower()
            chunks.append(
                {
                    "text": piece,
                    "source": source,
                    "line_start": line_start,
                    "line_end": line_end,
                    "is_deprecated": any(m in lowered for m in DEPRECATED_MARKERS),
                }
            )
        if end >= n:
            break
        start = max(end - overlap_chars, start + 1)
    return chunks


def get_conn():
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def main() -> None:
    with get_conn() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                line_start INT NOT NULL,
                line_end INT NOT NULL,
                is_deprecated BOOLEAN NOT NULL DEFAULT FALSE,
                embedding vector({EMBED_DIM})
            )
            """
        )
        # Full rebuild — simpler than upserts, and our corpus is tiny.
        conn.execute("TRUNCATE chunks")

        all_chunks = []
        for path in sorted(glob.glob("data/*.md")):
            with open(path) as f:
                text = clean_markdown(f.read())
            all_chunks.extend(chunk_text(text, path))
        print(f"{len(all_chunks)} chunks")

        # Embed in batches of 64 — keeps memory flat and retries cheap.
        for i in range(0, len(all_chunks), 64):
            batch = all_chunks[i : i + 64]
            resp = client.embeddings.create(
                model=EMBED_MODEL, input=[c["text"] for c in batch]
            )
            with conn.cursor() as cur:
                for c, d in zip(batch, resp.data):
                    cur.execute(
                        "INSERT INTO chunks "
                        "(text, source, line_start, line_end, is_deprecated, embedding) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            c["text"],
                            c["source"],
                            c["line_start"],
                            c["line_end"],
                            c["is_deprecated"],
                            d.embedding,
                        ),
                    )
            conn.commit()
            print(f"embedded+stored {min(i + 64, len(all_chunks))}/{len(all_chunks)}")
        print("done")


if __name__ == "__main__":
    main()
