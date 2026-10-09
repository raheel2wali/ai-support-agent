import os

from dotenv import load_dotenv

load_dotenv()

# Fail fast if the key is missing — better than a cryptic 401 three calls deep.
OPENAI_API_KEY=<redacted>

MODEL = os.getenv("MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))  # matches text-embedding-3-small

# Postgres + pgvector. createdb shopassist, then CREATE EXTENSION vector;
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/shopassist")

# RAG tuning — the numbers from the Part 2 writeup.
CHUNK_TOKENS = int(os.getenv("CHUNK_TOKENS", "400"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
RETRIEVE_TOP_K = int(os.getenv("RETRIEVE_TOP_K", "8"))  # candidates from pgvector
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "3"))  # what the agent actually sees
FRESHNESS_PENALTY = float(os.getenv("FRESHNESS_PENALTY", "0.4"))  # deprecated docs get down-ranked

# Retrieval score below this -> we don't trust the answer, hand off to a human.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
