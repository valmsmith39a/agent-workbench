"""The interface the MCP tools depend on.

Swap MockBrokerageService for a real brokerage client by implementing this
protocol; the MCP tool contracts and the agent stay the same.
"""

from typing import Protocol

from app.models.brokerage import (
    AccountRestrictionsResult,
    TradeStatusResult,
    TransferStatusResult,
)


class BrokerageError(Exception):
    code = "BROKERAGE_ERROR"


class AccountNotFoundError(BrokerageError):
    code = "ACCOUNT_NOT_FOUND"


class InvalidRequestError(BrokerageError):
    code = "INVALID_REQUEST"


class BrokerageService(Protocol):
    def get_trade_status(
        self, account_id: str, symbol: str | None = None, order_id: str | None = None
    ) -> TradeStatusResult: ...

    def get_transfer_status(
        self,
        account_id: str,
        transfer_id: str | None = None,
        amount: float | None = None,
        direction: str | None = None,
    ) -> TransferStatusResult: ...

    def get_account_restrictions(
        self,
        account_id: str,
        symbol: str | None = None,
        side: str | None = None,
        quantity: int | None = None,
    ) -> AccountRestrictionsResult: ...
