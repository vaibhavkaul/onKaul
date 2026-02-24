"""Local chat endpoints for CLI and playground usage."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agent.core import agent

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request payload."""

    message: str = Field(min_length=1, description="User message for the agent")
    context: str = Field(default="", description="Optional additional context")


class ChatResponse(BaseModel):
    """Chat response payload."""

    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Run an investigation directly and return the response text."""
    response = agent.investigate(payload.message, context=payload.context)
    return ChatResponse(response=response)
