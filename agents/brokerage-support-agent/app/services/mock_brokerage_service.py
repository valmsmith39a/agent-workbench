"""A fake brokerage backend: hard-coded data plus the lookups on top of it.

Later steps put an MCP tool in front of this, then an agent in front of the
tool. Nothing in this file knows about either; it just returns structured data.
All names and IDs are fictional.
"""

import re

from app.models.brokerage import Order, TradeStatusResult, Transfer, TransferDirection, TransferStatusResult

ORDERS = {
    "ACCT-DEMO-1001": [
        {
            "order_id": "ORD-7F3K-1001",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 10,
            "status": "FILLED",
            "filled_quantity": 10,
            "average_fill_price": 118.42,
            "submitted_at": "2026-10-01T14:32:05Z",
        },
        {
            "order_id": "ORD-7F3K-1002",
            "symbol": "TSLA",
            "side": "SELL",
            "quantity": 5,
            "status": "PENDING",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T13:45:12Z",
            "status_reason": "Limit price of $265.00 has not been reached.",
        },
        {
            "order_id": "ORD-7F3K-1003",
            "symbol": "AMD",
            "side": "BUY",
            "quantity": 25,
            "status": "REJECTED",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T15:10:44Z",
            "status_reason": "Estimated cost of $3,807.50 exceeded buying power of $412.55.",
        },
    ],
}

TRANSFERS = {
    "ACCT-DEMO-1001": [
        {
            "transfer_id": "TRF-5Q2M-2001",
            "amount": 5000.00,
            "direction": "DEPOSIT",
            "external_account": "Checking ****4821",
            "status": "PROCESSING",
            "initiated_date": "2026-10-01",
            "expected_available_date": "2026-10-05",
        },
        {
            "transfer_id": "TRF-5Q2M-2002",
            "amount": 2500.00,
            "direction": "DEPOSIT",
            "external_account": "Checking ****4821",
            "status": "COMPLETED",
            "initiated_date": "2026-09-22",
            "expected_available_date": "2026-09-24",
        },
        {
            "transfer_id": "TRF-5Q2M-2003",
            "amount": 1000.00,
            "direction": "WITHDRAWAL",
            "external_account": "Savings ****1177",
            "status": "FAILED",
            "initiated_date": "2026-09-28",
            "failure_reason": (
                "The receiving bank returned the transfer because the account is closed. "
                "The $1,000.00 was returned to your brokerage cash balance."
            ),
        },
    ],
}

ACCOUNT_IDS = {"ACCT-DEMO-1001"}
SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")


class BrokerageError(Exception):
    """Base class for expected failures. `code` is what callers see."""

    code = "BROKERAGE_ERROR"


class AccountNotFoundError(BrokerageError):
    code = "ACCOUNT_NOT_FOUND"


class InvalidRequestError(BrokerageError):
    code = "INVALID_REQUEST"


def _require_account(account_id: str) -> None:
    if account_id not in ACCOUNT_IDS:
        raise AccountNotFoundError(f"Account '{account_id}' was not found.")


def get_trade_status(account_id: str, symbol: str | None = None) -> TradeStatusResult:
    """Return the account's orders, optionally only those for one ticker."""
    _require_account(account_id)

    if symbol is not None:
        symbol = symbol.strip().upper()
        if not SYMBOL_RE.match(symbol):
            raise InvalidRequestError(f"'{symbol}' is not a valid ticker symbol.")

    orders = [
        Order(**raw)
        for raw in ORDERS.get(account_id, [])
        if symbol is None or raw["symbol"] == symbol
    ]
    return TradeStatusResult(account_id=account_id, symbol=symbol, orders=orders)


def get_transfer_status(
    account_id: str, amount: float | None = None, direction: str | None = None
) -> TransferStatusResult:
    """Return the account's transfers, optionally filtered by exact amount and/or direction."""
    _require_account(account_id)

    if amount is not None and amount <= 0:
        raise InvalidRequestError("Transfer amount must be greater than zero.")
    if direction is not None:
        try:
            direction = TransferDirection(direction.strip().upper())
        except ValueError:
            raise InvalidRequestError("Direction must be DEPOSIT or WITHDRAWAL.") from None

    transfers = [
        Transfer(**raw)
        for raw in TRANSFERS.get(account_id, [])
        if (amount is None or abs(raw["amount"] - amount) < 0.005)  # compare money to the cent
        and (direction is None or raw["direction"] == direction)
    ]
    return TransferStatusResult(account_id=account_id, amount=amount, direction=direction, transfers=transfers)


if __name__ == "__main__":
    # Try it:  python -m app.services.mock_brokerage_service
    print(get_trade_status("ACCT-DEMO-1001", symbol="nvda").model_dump_json(indent=2))
    print(get_transfer_status("ACCT-DEMO-1001", amount=5000).model_dump_json(indent=2))
