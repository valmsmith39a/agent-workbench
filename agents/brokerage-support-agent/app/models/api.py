"""Request and response bodies for the chat API."""

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]  # the arguments the model chose (account_id is added by the server)


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCall]
    model: str
