"""The get_transfer_status MCP tool. Same shape as trades.py."""

from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.mcp.tools.common import run_tool
from app.services import mock_brokerage_service as service


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    def get_transfer_status(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        amount: Annotated[float | None, Field(description="Exact transfer amount in USD, e.g. 5000.")] = None,
        direction: Annotated[
            Literal["DEPOSIT", "WITHDRAWAL"] | None,
            Field(description="DEPOSIT (bank to brokerage) or WITHDRAWAL (brokerage to bank)."),
        ] = None,
    ) -> dict[str, Any]:
        """Look up the status of money transfers between the customer's bank and brokerage account.

        Use for questions like "where is my $5,000 deposit?" or "did my
        withdrawal go through?". Returns each matching transfer with amount,
        direction, linked bank account, status (PROCESSING, COMPLETED, FAILED),
        initiated date, expected availability date, and the failure reason if
        it failed. With no filters, returns all recent transfers.
        """
        return run_tool(lambda: service.get_transfer_status(account_id, amount=amount, direction=direction))
