"""Shared helper for MCP tool definitions."""

from typing import Any, Callable

from pydantic import BaseModel

from app.services.mock_brokerage_service import BrokerageError


def run_tool(call: Callable[[], BaseModel]) -> dict[str, Any]:
    """Run a service call and return its result as JSON-safe data.

    Expected failures (unknown account, bad input) come back as a structured
    error the agent can explain, instead of a protocol-level exception.
    """
    try:
        result = call()
    except BrokerageError as exc:
        return {"error": {"code": exc.code, "message": str(exc)}}
    return result.model_dump(mode="json")
