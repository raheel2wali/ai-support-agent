"""Guardrails: PII redaction, confidence gating, human handoff.

Small and explicit on purpose. Every rule here exists because
something went wrong without it.
"""

import re

from app.config import CONFIDENCE_THRESHOLD

# Pakistani mobile formats + email. Good enough for logs;
# not a substitute for a real DLP pass if you handle payments.
PHONE_RE = re.compile(r"\b0?3\d{2}[-\s]?\d{7}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def redact_pii(text: str) -> str:
    text = PHONE_RE.sub("[phone]", text)
    text = EMAIL_RE.sub("[email]", text)
    return text


# Crude prompt-injection tripwires. Catches the obvious "ignore your
# instructions" class; a real deployment wants a classifier here.
INJECTION_PATTERNS = (
    "ignore your instructions",
    "ignore all previous instructions",
    "disregard your instructions",
    "forget your instructions",
)


def needs_handoff(top_score: float, message: str) -> bool:
    # Low retrieval confidence -> don't guess, get a human.
    if top_score < CONFIDENCE_THRESHOLD:
        return True
    lowered = message.lower()
    # Angry customers shouldn't be debugged by a bot.
    if any(w in lowered for w in ("refund", "complaint", "lawyer", "fraud", "scam")):
        return True
    # Obvious prompt-injection attempts go to a human, not the model.
    if any(p in lowered for p in INJECTION_PATTERNS):
        return True
    return False


HANDOFF_MESSAGE = (
    "I'm not confident I can resolve this correctly, so I've flagged it "
    "for our support team — they'll pick it up shortly. Sorry about that."
)
