"""FastAPI front door. POST /chat, POST /confirm, GET /stats, GET /health."""

import time

from fastapi import FastAPI
from pydantic import BaseModel

from app import agent

app = FastAPI(title="ShopAssist")

# Dead simple monitoring. In-memory counters are enough at this scale:
# if the process restarts, the numbers reset, and that's fine for now.
stats = {
    "chats": 0,
    "handoffs": 0,
    "pending_actions": 0,
    "total_latency_ms": 0.0,
}


class ChatRequest(BaseModel):
    message: str
    customer: str = "guest"


class ChatResponse(BaseModel):
    reply: str
    handoff: bool = False
    pending_action: dict | None = None


class ConfirmRequest(BaseModel):
    action_id: str
    approved: bool


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    start = time.perf_counter()
    result = agent.chat(req.message, customer=req.customer)
    stats["chats"] += 1
    stats["total_latency_ms"] += (time.perf_counter() - start) * 1000
    if result.get("handoff"):
        stats["handoffs"] += 1
    if result.get("pending_action"):
        stats["pending_actions"] += 1
    return ChatResponse(**result)


@app.post("/confirm")
def confirm(req: ConfirmRequest) -> dict:
    # The customer answered yes/no to a pending write action.
    return agent.confirm(req.action_id, req.approved)


@app.get("/stats")
def get_stats() -> dict:
    # The whole "dashboard": volume, handoff rate, average response time.
    # Watch the handoff rate. If it climbs, the agent or the docs need work.
    chats = stats["chats"]
    return {
        **stats,
        "handoff_rate": round(stats["handoffs"] / chats, 3) if chats else 0.0,
        "avg_latency_ms": round(stats["total_latency_ms"] / chats) if chats else 0,
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True}
