"""Request and response bodies for the chat API."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ToolTrace(BaseModel):
    """One MCP tool call the agent made while answering."""

    name: str
    args: dict[str, Any]  # what the model chose
    injected: dict[str, Any]  # what the server added (the customer's account), not the model
    result: dict[str, Any]  # the tool's structured JSON result
    latency_ms: float


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolTrace]
    model: str
    total_latency_ms: float
