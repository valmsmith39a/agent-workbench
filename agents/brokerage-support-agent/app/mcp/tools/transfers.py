from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.mcp.tools.common import run_tool
from app.services.brokerage_service import BrokerageService


def register(mcp: FastMCP, service: BrokerageService) -> None:
    @mcp.tool()
    def get_transfer_status(
        account_id: Annotated[str, Field(description="Brokerage account ID, e.g. ACCT-DEMO-1001.")],
        transfer_id: Annotated[str | None, Field(description="Specific transfer ID, e.g. TRF-5Q2M-2001.")] = None,
        amount: Annotated[float | None, Field(description="Exact transfer amount in USD, e.g. 5000.")] = None,
        direction: Annotated[
            Literal["DEPOSIT", "WITHDRAWAL"] | None,
            Field(description="DEPOSIT (money into the brokerage) or WITHDRAWAL (money out)."),
        ] = None,
    ) -> dict[str, Any]:
        """Look up the status of money transfers between the customer's bank and brokerage account.

        Use for questions like "where is my $5,000 deposit?" or "did my withdrawal
        go through?". Returns each matching transfer with amount, direction,
        method, status (PROCESSING, COMPLETED, FAILED), initiated date, expected
        availability date, and failure reason if any. With no filters, returns
        recent transfers.
        """
        return run_tool(
            lambda: service.get_transfer_status(account_id, transfer_id=transfer_id, amount=amount, direction=direction)
        )
