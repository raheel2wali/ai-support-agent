import os

from dotenv import load_dotenv

load_dotenv()

# Fail fast if the key is missing — better than a cryptic 401 three calls deep.
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

MODEL = os.getenv("MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
INDEX_PATH = os.getenv("INDEX_PATH", "data/index.json")

# Retrieval score below this -> we don't trust the answer, hand off to a human.
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.35"))
