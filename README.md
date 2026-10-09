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
createdb shopassist && psql shopassist -c "CREATE EXTENSION vector;"
python -m app.ingest   # chunks docs, embeds, stores in pgvector
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
  ingest.py      # cleans markdown, 400-token chunks (50 overlap), embeds into pgvector
  rag.py         # pgvector top-8 -> rerank top-3, citations, freshness filter
  tools.py       # order_lookup, create_ticket (stand-ins for real APIs)
  guardrails.py  # PII redaction, confidence threshold, human handoff
  agent.py       # the loop: retrieve -> decide -> act -> respond
  main.py        # FastAPI, single /chat endpoint
evals/
  eval_basic.py  # 8 question/answer checks, prints pass/fail
data/
  faqs.md        # sample knowledge base
```

The RAG pipeline (Part 2 of the series): docs are cleaned to markdown, cut into 400-token chunks with 50-token overlap, and embedded into pgvector with line numbers and deprecation flags. At query time we pull the top-8 candidates, down-rank deprecated docs (freshness filter), rerank on keyword overlap, and keep the top-3. Every chunk carries a citation like `data/faqs.md#L4-L9`, and the agent is instructed to quote it — or say it doesn't know.

## What broke along the way

- Chunking by fixed size gave garbage retrieval. Chunking by markdown heading worked much better.
- The agent used to "helpfully" invent order statuses. Fixed by forcing every order answer to come from the `order_lookup` tool, never from memory.
- First version had no confidence threshold and confidently answered things it shouldn't have. Now anything below the threshold goes to a human.
- First RAG version leaked raw PDFs into the prompt and quoted 2019 policy dates. Fixed with 400-token chunking, citations on every answer, and a freshness filter that down-ranks deprecated docs.

## Roadmap

- [x] Swap JSON index for pgvector (Part 2)
- [ ] Add conversation memory (right now every message is stateless)
- [ ] Multi-language support
- [ ] Proper eval set (50+ cases instead of 8)

PRs welcome. If you build something with this, tell me — I like seeing where it goes.
