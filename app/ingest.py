"""Build the vector index from data/*.md.

Run: python -m app.ingest
Writes data/index.json — a list of {text, embedding, source}.
"""

import glob
import json
import re

from openai import OpenAI

from app.config import EMBED_MODEL, INDEX_PATH, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def chunk_markdown(text: str) -> list[str]:
    # Split on headings. Fixed-size chunking gave us garbage retrieval
    # because it cut answers in half — headings keep each chunk about
    # one idea, which is what we actually want to retrieve.
    parts = re.split(r"(?m)^#{1,3} ", text)
    chunks = [p.strip() for p in parts if p.strip()]
    return chunks


def main() -> None:
    chunks: list[dict] = []
    for path in sorted(glob.glob("data/*.md")):
        with open(path) as f:
            text = f.read()
        for chunk in chunk_markdown(text):
            chunks.append({"text": chunk, "source": path})

    print(f"{len(chunks)} chunks from {path}")
    texts = [c["text"] for c in chunks]

    # Embed in batches of 64 — the API handles bigger, but this keeps
    # memory flat and retries cheap if one batch fails.
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), 64):
        batch = texts[i : i + 64]
        resp = client.embeddings.create(model=EMBED_MODEL, input=batch)
        embeddings.extend([d.embedding for d in resp.data])
        print(f"embedded {min(i + 64, len(texts))}/{len(texts)}")

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb

    with open(INDEX_PATH, "w") as f:
        json.dump(chunks, f)
    print(f"wrote {INDEX_PATH}")


if __name__ == "__main__":
    main()
