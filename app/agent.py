"""The agent loop: retrieve -> decide -> act -> respond.

One model call, with tool use. We keep it to a single pass on purpose —
multi-step agent loops are powerful but much harder to debug, and for
support questions one good pass plus tools covers most cases.
"""

import json

from openai import OpenAI

from app import guardrails, rag, tools
from app.config import MODEL, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are ShopAssist, a support agent for an online store.
Answer from the provided context when it's relevant. If the customer asks
about an order, you MUST call order_lookup — never guess a status.
If you can't resolve the issue, call create_ticket with a clear subject.
Be concise and friendly. Never invent order numbers, dates, or policies.
When you state a fact from the context, cite it exactly like [data/faqs.md#L4-L9].
If the context doesn't cover the question, say so instead of inventing an answer.
"""


def chat(message: str, customer: str = "guest") -> dict:
    safe_message = guardrails.redact_pii(message)

    chunks = rag.retrieve(safe_message)
    top_score = chunks[0]["score"] if chunks else 0.0

    if guardrails.needs_handoff(top_score, safe_message):
        return {"reply": guardrails.HANDOFF_MESSAGE, "handoff": True}

    context = "\n\n".join(f"[{c['citation']}] {c['text']}" for c in chunks)

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nCustomer: {safe_message}"},
        ],
        tools=tools.TOOLS,
    )
    msg = resp.choices[0].message

    # Run any tool calls, then give the model the results for a final answer.
    if msg.tool_calls:
        followups = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nCustomer: {safe_message}"},
            msg,
        ]
        for call in msg.tool_calls:
            fn = tools.IMPLEMENTATIONS[call.function.name]
            args = json.loads(call.function.arguments)
            # create_ticket needs to know who it's for
            if call.function.name == "create_ticket":
                args.setdefault("customer", customer)
            result = fn(**args)
            followups.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )
        final = client.chat.completions.create(model=MODEL, messages=followups)
        return {"reply": final.choices[0].message.content, "handoff": False}

    return {"reply": msg.content, "handoff": False}
