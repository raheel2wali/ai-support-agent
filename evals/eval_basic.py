"""Tiny eval harness: 8 questions, keyword checks, prints pass/fail.

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
    ("I want to return my headphones", ["ticket", "T-"]),  # can't resolve -> ticket... or policy
]


def main() -> None:
    passed = 0
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
    print(f"\n{passed}/{len(CASES)} passed")


if __name__ == "__main__":
    main()
