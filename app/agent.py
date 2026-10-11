"""The agent loop: retrieve -> decide -> act -> respond.

One model call, with tool use. We keep it to a single pass on purpose —
multi-step agent loops are powerful but much harder to debug, and for
support questions one good pass plus tools covers most cases.

Reads run freely; writes pause for confirmation. See _execute_tool.
"""

import json

from openai import OpenAI

from app import guardrails, rag, tools
from app.config import DRY_RUN, MODEL, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are ShopAssist, a support agent for an online store.
Answer from the provided context when it's relevant. If the customer asks
about an order, you MUST call order_lookup — never guess a status.
If you can't resolve the issue, call create_ticket with a clear subject.
Be concise and friendly. Never invent order numbers, dates, or policies.
When you state a fact from the context, cite it exactly like [data/faqs.md#L4-L9].
If the context doesn't cover the question, say so instead of inventing an answer.
Note: actions that change state (like create_ticket) ask the customer to
confirm first — never claim a ticket was opened until it actually was.
"""

# Write actions waiting on a human. In production this lives in Redis or
# the database — a module dict is fine for the demo and easy to follow.
_pending: dict[str, dict] = {}


def _execute_tool(call, customer: str) -> dict:
    """Run one tool call. Reads run free; writes pause for confirmation.

    Returns the tool result, or a dict with confirmation_required=True
    when a write needs a human to say yes first.
    """
    name = call.function.name
    args = json.loads(call.function.arguments)
    # create_ticket needs to know who it's for
    if name == "create_ticket":
        args.setdefault("customer", customer)

    if tools.SCOPES.get(name, "read") == "read":
        return tools.IMPLEMENTATIONS[name](**args)

    if DRY_RUN:
        # Log it, don't do it. Nothing gets written anywhere.
        print(f"[dry-run] would call {name}({args})")
        return {"tool": name, "dry_run": True, "args": args}

    action_id = f"a-{len(_pending) + 1:04d}"
    _pending[action_id] = {"tool": name, "args": args}
    return {
        "tool": name,
        "confirmation_required": True,
        "action_id": action_id,
        "args": args,
    }


def confirm(action_id: str, approved: bool) -> dict:
    """Approve or reject a pending write action. Runs the tool on approval."""
    action = _pending.pop(action_id, None)
    if action is None:
        return {"error": f"unknown or expired action {action_id}"}
    if not approved:
        return {"tool": action["tool"], "cancelled": True}
    result = tools.IMPLEMENTATIONS[action["tool"]](**action["args"])
    return {"tool": action["tool"], **result}


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
        tool_results = []
        pending = None
        for call in msg.tool_calls:
            result = _execute_tool(call, customer)
            tool_results.append((call, result))
            if isinstance(result, dict) and result.get("confirmation_required"):
                pending = result

        if pending is not None:
            # A write is waiting on the customer — don't run the final
            # model pass yet, there is nothing to report.
            args_summary = ", ".join(f"{k}={v}" for k, v in pending["args"].items())
            return {
                "reply": (
                    f"Before I do this, I need your OK: "
                    f"{pending['tool']}({args_summary}). "
                    "Reply 'yes' to confirm or 'no' to cancel."
                ),
                "handoff": False,
                "pending_action": pending,
            }

        followups = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nCustomer: {safe_message}"},
            msg,
        ]
        for call, result in tool_results:
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
