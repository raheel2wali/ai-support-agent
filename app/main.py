"""FastAPI front door. Two endpoints: POST /chat, POST /confirm."""

from fastapi import FastAPI
from pydantic import BaseModel

from app import agent

app = FastAPI(title="ShopAssist")


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
    result = agent.chat(req.message, customer=req.customer)
    return ChatResponse(**result)


@app.post("/confirm")
def confirm(req: ConfirmRequest) -> dict:
    # The customer answered yes/no to a pending write action.
    return agent.confirm(req.action_id, req.approved)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
