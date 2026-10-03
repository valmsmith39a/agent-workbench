from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Demo stand-in for authentication: in production this comes from the
    # authenticated session, never from the request body.
    account_id: str | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ToolTrace(BaseModel):
    tool: str
    arguments: dict[str, Any]
    context: dict[str, Any]
    result: dict[str, Any]
    latency_ms: float
    is_error: bool


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolTrace]
    model: str
    total_latency_ms: float
