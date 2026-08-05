"""Legacy starter agent endpoints."""

from fastapi import APIRouter, HTTPException

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(response=result.get("response", ""), analysis=result.get("analysis", ""))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/status")
async def agent_status():
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}
