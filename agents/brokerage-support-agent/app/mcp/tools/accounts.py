"""The get_account_restrictions MCP tool. Same shape as trades.py and transfers.py."""

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.mcp.tools.common import run_tool
from app.services import mock_brokerage_service as service


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_account_restrictions(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        symbol: Annotated[str | None, Field(description="Ticker of the order to check, e.g. NVDA.")] = None,
        side: Annotated[Literal["BUY", "SELL"] | None, Field(description="Side of the order to check.")] = None,
        quantity: Annotated[int | None, Field(description="Number of shares in the order to check.")] = None,
    ) -> dict[str, Any]:
        """Check buying power, unsettled funds and account restrictions, and whether an order can be placed.

        Use for questions like "why can't I place this trade?" or "can I buy
        10 shares of NVDA?". Pass symbol, side and quantity together to check a
        specific order: the result says can_place_order and lists
        blocking_reasons (e.g. INSUFFICIENT_BUYING_POWER, UNSETTLED_FUNDS,
        ACCOUNT_RESTRICTION). With no order, returns the account's buying
        power, unsettled funds and settlement date, and active restrictions.
        """
        return run_tool(
            lambda: service.get_account_restrictions(account_id, symbol=symbol, side=side, quantity=quantity)
        )
