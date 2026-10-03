from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.mcp.tools.common import run_tool
from app.services.brokerage_service import BrokerageService


def register(mcp: FastMCP, service: BrokerageService) -> None:
    @mcp.tool()
    def get_trade_status(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        symbol: Annotated[str | None, Field(description="Ticker symbol to filter by, e.g. NVDA.")] = None,
        order_id: Annotated[str | None, Field(description="Specific order ID, e.g. ORD-7F3K-1001.")] = None,
    ) -> dict[str, Any]:
        """Look up the status of the customer's stock orders.

        Use for questions like "did my trade go through?", "was my order filled?"
        or "why was my order rejected?". Returns each matching order with side,
        quantity, status (FILLED, PARTIALLY_FILLED, PENDING, REJECTED, CANCELED),
        filled quantity, average fill price, and the reason it is pending or
        rejected. With no filters, returns the customer's recent orders.
        """
        return run_tool(lambda: service.get_trade_status(account_id, symbol=symbol, order_id=order_id))
