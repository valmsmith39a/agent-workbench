"""The get_trade_status MCP tool.

The tool is a thin wrapper: it describes itself to MCP clients, calls the
service, and turns the result (or an expected error) into JSON. All lookup
and validation logic stays in the service.
"""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.services import mock_brokerage_service as service


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_trade_status(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        symbol: Annotated[str | None, Field(description="Ticker symbol to filter by, e.g. NVDA.")] = None,
    ) -> dict[str, Any]:
        """Look up the status of the customer's stock orders.

        Use for questions like "did my trade go through?" or "was my order
        filled?". Returns each matching order with side, quantity, status
        (FILLED, PENDING, REJECTED), filled quantity, average fill price, and
        the reason an order is pending or rejected. With no symbol, returns
        all of the customer's recent orders.
        """
        try:
            result = service.get_trade_status(account_id, symbol=symbol)
        except service.AccountNotFoundError as exc:
            return {"error": {"code": "ACCOUNT_NOT_FOUND", "message": str(exc)}}
        except service.InvalidRequestError as exc:
            return {"error": {"code": "INVALID_REQUEST", "message": str(exc)}}
        return result.model_dump(mode="json")
