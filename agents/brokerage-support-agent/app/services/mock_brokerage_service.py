"""A fake brokerage backend: hard-coded data plus the lookups on top of it.

Later steps put an MCP tool in front of this, then an agent in front of the
tool. Nothing in this file knows about either; it just returns structured data.
All names and IDs are fictional.
"""

import re

from app.models.brokerage import Order, TradeStatusResult

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

SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")


class AccountNotFoundError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


def get_trade_status(account_id: str, symbol: str | None = None) -> TradeStatusResult:
    """Return the account's orders, optionally only those for one ticker."""
    if account_id not in ORDERS:
        raise AccountNotFoundError(f"Account '{account_id}' was not found.")

    if symbol is not None:
        symbol = symbol.strip().upper()
        if not SYMBOL_RE.match(symbol):
            raise InvalidRequestError(f"'{symbol}' is not a valid ticker symbol.")

    orders = [
        Order(**raw)
        for raw in ORDERS[account_id]
        if symbol is None or raw["symbol"] == symbol
    ]
    return TradeStatusResult(account_id=account_id, symbol=symbol, orders=orders)


if __name__ == "__main__":
    # Try it:  python -m app.services.mock_brokerage_service
    result = get_trade_status("ACCT-DEMO-1001", symbol="nvda")
    print(result.model_dump_json(indent=2))
