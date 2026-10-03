from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.mcp.tools.common import run_tool
from app.services.brokerage_service import BrokerageService


def register(mcp: FastMCP, service: BrokerageService) -> None:
    @mcp.tool()
    def get_account_restrictions(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        symbol: Annotated[str | None, Field(description="Ticker of the order the customer wants to place.")] = None,
        side: Annotated[Literal["BUY", "SELL"] | None, Field(description="Side of the order to check.")] = None,
        quantity: Annotated[int | None, Field(description="Number of shares in the order to check.")] = None,
    ) -> dict[str, Any]:
        """Check buying power, unsettled funds and account restrictions, and whether an order can be placed.

        Use for questions like "why can't I place this trade?" or "how much can I
        buy?". Pass symbol, side and quantity together to run pre-trade checks on
        a specific order. If all three are omitted, it re-checks the customer's
        most recent rejected order (or does an account-level check if there is
        none). Returns
        buying power, settled cash, unsettled funds and settlement date, active
        restrictions, can_trade, and blocking_reasons explaining why trading is
        blocked.
        """
        return run_tool(
            lambda: service.get_account_restrictions(account_id, symbol=symbol, side=side, quantity=quantity)
        )
