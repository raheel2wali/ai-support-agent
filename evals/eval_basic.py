"""Tiny eval harness: question checks plus the write-confirmation flow.

Prints pass/fail per case.

Run: python -m evals.eval_basic
This is not a real eval suite — it's a smoke test I run before pushing.
A proper set would be 50+ cases with an LLM judge. On the roadmap.
"""

from app import agent

CASES = [
    # (question, keywords that must appear in the reply)
    ("what is your return policy?", ["30 days"]),
    ("where is my order 1042?", ["shipped", "Oct 12"]),
    ("where is my order 9999?", ["no order found"]),
    ("do you ship to Lahore?", ["3-5", "Lahore"]),
    ("how do I track my package?", ["tracking"]),
    ("my card was charged twice, this is fraud", ["support team"]),  # handoff
    ("asdkfjhasd kjhasd", ["support team"]),  # nonsense -> handoff
]


def check_confirmation_flow() -> bool:
    """Write tools must ask before acting, then run once approved."""
    result = agent.chat("I want to return my headphones")
    pending = result.get("pending_action")
    if not pending or pending.get("tool") != "create_ticket":
        print("[FAIL] create_ticket ran without asking first")
        print(f"       reply was: {result['reply'][:200]}")
        return False
    confirmed = agent.confirm(pending["action_id"], approved=True)
    if "ticket_id" not in confirmed:
        print(f"[FAIL] approving the action did not open a ticket: {confirmed}")
        return False
    print(f"[PASS] create_ticket asked first, then opened {confirmed['ticket_id']}")
    return True


def check_rejected_action() -> bool:
    """Rejecting a pending action must not write anything."""
    result = agent.chat("please open a ticket about my late delivery")
    pending = result.get("pending_action")
    if not pending:
        print("[FAIL] expected a pending action for the ticket request")
        return False
    rejected = agent.confirm(pending["action_id"], approved=False)
    if not rejected.get("cancelled"):
        print(f"[FAIL] rejecting the action still ran it: {rejected}")
        return False
    print("[PASS] rejected write action was cancelled, nothing written")
    return True


def main() -> None:
    passed = 0
    total = len(CASES) + 2
    for question, keywords in CASES:
        result = agent.chat(question)
        reply = result["reply"].lower()
        ok = all(k.lower() in reply for k in keywords)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] {question}")
        if not ok:
            print(f"       reply was: {result['reply'][:200]}")
    if check_confirmation_flow():
        passed += 1
    if check_rejected_action():
        passed += 1
    print(f"\n{passed}/{total} passed")


if __name__ == "__main__":
    main()
