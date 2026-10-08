# ShopAssist — AI Support Agent

I'm building an AI support agent for an online store, in public. This repo is the code companion to my 5-part LinkedIn series where I walk through the whole thing: architecture, RAG, tools, guardrails, and shipping it.

## Why this exists

Rule-based chatbots frustrate people — they only know the 10 questions someone bothered to hardcode. I wanted an agent that can actually *do* things: look up an order, open a ticket, and only bother a human when it genuinely should. So I built one.

Nothing here is magic. It's a Python backend, an LLM, a pile of markdown docs, and a few function calls. That's kind of the point.

## What it does

- Answers product and support questions from your own docs (RAG over `data/`)
- Looks up order status via a tool call
- Creates support tickets when it can't resolve something itself
- Hands off to a human when confidence is low
- Redacts phone numbers and emails before anything gets logged

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your OPENAI_API_KEY
python -m app.ingest   # builds the vector index from data/
uvicorn app.main:app --reload
```

Talk to it:

```bash
curl -X POST localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "where is my order 1042?"}'
```

## How it's put together

```
app/
  config.py      # env-based settings, fails fast if the API key is missing
  ingest.py      # chunks data/*.md, embeds, writes data/index.json
  rag.py         # loads the index, cosine-similarity search
  tools.py       # order_lookup, create_ticket (stand-ins for real APIs)
  guardrails.py  # PII redaction, confidence threshold, human handoff
  agent.py       # the loop: retrieve -> decide -> act -> respond
  main.py        # FastAPI, single /chat endpoint
evals/
  eval_basic.py  # 8 question/answer checks, prints pass/fail
data/
  faqs.md        # sample knowledge base
  index.json     # built by ingest.py (gitignored)
```

The vector store is just a JSON file with embeddings and numpy cosine similarity. Deliberately boring — no database to operate for v1. When this outgrows JSON, pgvector is the obvious next step.

## What broke along the way

- Chunking by fixed size gave garbage retrieval. Chunking by markdown heading worked much better.
- The agent used to "helpfully" invent order statuses. Fixed by forcing every order answer to come from the `order_lookup` tool, never from memory.
- First version had no confidence threshold and confidently answered things it shouldn't have. Now anything below the threshold goes to a human.

## Roadmap

- [ ] Swap JSON index for pgvector
- [ ] Add conversation memory (right now every message is stateless)
- [ ] Urdu support — half my customers ask in Roman Urdu
- [ ] Proper eval set (50+ cases instead of 8)

PRs welcome. If you build something with this, tell me — I like seeing where it goes.
