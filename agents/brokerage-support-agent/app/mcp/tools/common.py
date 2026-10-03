"""Shared helpers for MCP tool definitions."""

from typing import Any

from pydantic import BaseModel

from app.services.brokerage_service import BrokerageError


def run_tool(call) -> dict[str, Any]:
    """Run a service call and return JSON-safe structured data.

    Expected failures (bad input, unknown account) come back as a structured
    error the agent can explain, instead of a protocol-level exception.
    """
    try:
        result: BaseModel = call()
    except BrokerageError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}}
    return result.model_dump(mode="json")
