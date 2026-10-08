"""FastAPI front door. One endpoint: POST /chat."""

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


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    result = agent.chat(req.message, customer=req.customer)
    return ChatResponse(**result)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
