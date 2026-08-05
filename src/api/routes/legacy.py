"""Legacy starter agent endpoints."""

import logging

from fastapi import APIRouter

from src.agents.graph import agent
from src.models.api.errors import INTERNAL_ERROR, DomainError
from src.models.schemas import ChatRequest, ChatResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(response=result.get("response", ""), analysis=result.get("analysis", ""))
    except Exception as exc:
        logger.exception("Legacy agent route failed", extra={"route": "/api/v1/chat", "exception_type": type(exc).__name__})
        raise DomainError(INTERNAL_ERROR, "Internal server error.", 500) from exc


@router.get("/status")
async def agent_status():
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
