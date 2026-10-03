"""Read-only brokerage support tools backed by hard-coded mock data.

NOTE: These tools are plain LangChain ``@tool`` functions for now. Later they
will move behind an MCP server and be loaded into the agent with
``langchain-mcp-adapters`` (``MultiServerMCPClient(...).get_tools()``), so the
agent code in ``agent.py`` should not need to change beyond where the tool list
comes from.

Every tool is READ-ONLY: nothing here places, cancels, or modifies an order or
transfer. All customers, accounts, orders, and prices are fake fixtures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

ET = ZoneInfo("America/New_York")

# Fixed "now" so demo output is deterministic (a Friday, mid-session).
MOCK_NOW = datetime(2026, 10, 2, 11, 30, tzinfo=ET)

# Mock last-trade prices used for buying-power checks (not real market data).
MOCK_PRICES = {
    "AAPL": 227.50,
    "MSFT": 431.20,
    "NVDA": 118.90,
    "TSLA": 251.00,
    "VTI": 289.40,
    "XYZQ": 3.15,  # fictional restricted security
}

# Securities the firm has restricted from trading (fictional).
RESTRICTED_SECURITIES = {"XYZQ": "Security is on the firm's restricted list (halted / under review)."}

# ---------------------------------------------------------------------------
# Mock customers
#   ACC-1001 Alice: NVDA limit order only PARTIALLY FILLED  -> "Did my NVDA trade go through?"
#   ACC-1002 Bob:   ACH deposit still PENDING               -> "Where is my transfer?"
#   ACC-1003 Carol: low cash, wants to buy 20 AAPL          -> "Why can't I place this trade?"
# ---------------------------------------------------------------------------
CUSTOMERS: dict[str, dict] = {
    "ACC-1001": {
        "name": "Alice Nguyen",
        "account_type": "margin",
        "equity": 48_200.00,
        "buying_power": 22_400.00,
        "day_trades_last_5_days": 1,
        "holds": [],
        "positions": {"NVDA": 60, "AAPL": 25},
    },
    "ACC-1002": {
        "name": "Bob Martinez",
        "account_type": "cash",
        "equity": 12_750.00,
        "buying_power": 2_100.00,
        "day_trades_last_5_days": 0,
        "holds": [],
        "positions": {"VTI": 30},
    },
    "ACC-1003": {
        "name": "Carol Smith",
        "account_type": "margin",
        "equity": 9_800.00,
        "buying_power": 1_250.00,
        "day_trades_last_5_days": 2,
        "holds": [],
        "positions": {"MSFT": 20},
    },
}

ORDERS: dict[str, list[dict]] = {
    "ACC-1001": [
        {
            "order_id": "ORD-55012",
            "ticker": "NVDA",
            "side": "buy",
            "order_type": "limit",
            "limit_price": 118.50,
            "qty": 100,
            "filled_qty": 60,
            "avg_fill_price": 118.42,
            "status": "partially_filled",
            "time_in_force": "day",
            "submitted_at": "2026-10-02T09:41:07-04:00",
            "last_fill_at": "2026-10-02T09:58:33-04:00",
            "note": "Remaining 40 shares are working at the 118.50 limit; unfilled shares cancel at market close (DAY order).",
        },
        {
            "order_id": "ORD-54877",
            "ticker": "AAPL",
            "side": "buy",
            "order_type": "market",
            "limit_price": None,
            "qty": 25,
            "filled_qty": 25,
            "avg_fill_price": 226.91,
            "status": "filled",
            "time_in_force": "day",
            "submitted_at": "2026-09-30T10:02:15-04:00",
            "last_fill_at": "2026-09-30T10:02:16-04:00",
            "note": None,
        },
        {
            "order_id": "ORD-54120",
            "ticker": "NVDA",
            "side": "sell",
            "order_type": "limit",
            "limit_price": 125.00,
            "qty": 20,
            "filled_qty": 0,
            "avg_fill_price": None,
            "status": "canceled",
            "time_in_force": "day",
            "submitted_at": "2026-09-25T13:15:00-04:00",
            "last_fill_at": None,
            "note": "Canceled by customer.",
        },
    ],
    "ACC-1002": [
        {
            "order_id": "ORD-55100",
            "ticker": "TSLA",
            "side": "buy",
            "order_type": "market",
            "limit_price": None,
            "qty": 10,
            "filled_qty": 0,
            "avg_fill_price": None,
            "status": "rejected",
            "time_in_force": "day",
            "submitted_at": "2026-10-01T15:12:40-04:00",
            "last_fill_at": None,
            "note": "Rejected: insufficient settled cash (cash account).",
        },
    ],
    "ACC-1003": [
        {
            "order_id": "ORD-55201",
            "ticker": "MSFT",
            "side": "sell",
            "order_type": "limit",
            "limit_price": 440.00,
            "qty": 5,
            "filled_qty": 0,
            "avg_fill_price": None,
            "status": "pending",
            "time_in_force": "gtc",
            "submitted_at": "2026-10-01T09:35:00-04:00",
            "last_fill_at": None,
            "note": "Working GTC limit order; MSFT is trading below the limit.",
        },
    ],
}

TRANSFERS: dict[str, list[dict]] = {
    "ACC-1001": [
        {
            "transfer_id": "TRF-9001",
            "type": "wire",
            "direction": "deposit",
            "amount": 10_000.00,
            "stage": "completed",
            "initiated_at": "2026-09-22",
            "expected_completion_date": "2026-09-22",
            "completed_at": "2026-09-22",
        },
    ],
    "ACC-1002": [
        {
            "transfer_id": "TRF-9107",
            "type": "ACH",
            "direction": "deposit",
            "amount": 5_000.00,
            "stage": "pending_bank_clearing",
            "stage_detail": "Initiated with your linked bank; ACH deposits typically clear in 3 business days.",
            "initiated_at": "2026-10-01",
            "expected_completion_date": "2026-10-06",
            "completed_at": None,
        },
        {
            "transfer_id": "TRF-8820",
            "type": "ACATS",
            "direction": "incoming",
            "amount": 7_430.00,
            "stage": "completed",
            "initiated_at": "2026-09-08",
            "expected_completion_date": "2026-09-15",
            "completed_at": "2026-09-14",
        },
    ],
    "ACC-1003": [],
}


def _unknown_account(account_id: str) -> dict:
    return {"error": f"Unknown account_id '{account_id}'."}


def _market_open(now: datetime) -> bool:
    """Regular session only: Mon-Fri 9:30-16:00 ET (holidays ignored in the mock)."""
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= minutes < 16 * 60


@tool
def get_orders(account_id: str, ticker: str | None = None) -> dict:
    """Look up the customer's recent orders, optionally filtered to one ticker.

    Returns each order's status (filled, partially_filled, pending, canceled,
    rejected), quantity, filled quantity, average fill price, and times.
    """
    if account_id not in CUSTOMERS:
        return _unknown_account(account_id)
    orders = ORDERS.get(account_id, [])
    if ticker:
        orders = [o for o in orders if o["ticker"] == ticker.upper()]
    return {"account_id": account_id, "ticker": ticker.upper() if ticker else None, "orders": orders}


@tool
def get_transfers(account_id: str) -> dict:
    """Look up the customer's money and asset transfers (ACH, wire, ACATS).

    Returns each transfer's type, direction, amount, current stage, and the
    expected completion date.
    """
    if account_id not in CUSTOMERS:
        return _unknown_account(account_id)
    return {"account_id": account_id, "transfers": TRANSFERS.get(account_id, [])}


@tool
def check_trade_eligibility(
    account_id: str, ticker: str, side: Literal["buy", "sell"], qty: int
) -> dict:
    """Check whether the customer could place a trade right now (does NOT place it).

    Returns eligible=True/False plus any blocking reasons: insufficient buying
    power, pattern day trader (PDT) restriction, market closed, restricted
    security, insufficient shares, or an account hold.
    """
    customer = CUSTOMERS.get(account_id)
    if customer is None:
        return _unknown_account(account_id)
    ticker = ticker.upper()
    side = side.lower()  # type: ignore[assignment]
    price = MOCK_PRICES.get(ticker)
    if price is None:
        return {"error": f"No mock quote for '{ticker}'."}

    estimated_value = round(price * qty, 2)
    reasons: list[dict] = []

    for hold in customer["holds"]:
        reasons.append({"code": "account_hold", "detail": hold})
    if ticker in RESTRICTED_SECURITIES:
        reasons.append({"code": "restricted_security", "detail": RESTRICTED_SECURITIES[ticker]})
    if not _market_open(MOCK_NOW):
        reasons.append({"code": "market_closed", "detail": "Regular trading hours are 9:30am-4:00pm ET, Mon-Fri."})
    if side == "buy" and estimated_value > customer["buying_power"]:
        reasons.append({
            "code": "insufficient_buying_power",
            "detail": f"Estimated cost ${estimated_value:,.2f} exceeds buying power ${customer['buying_power']:,.2f}.",
            "shortfall": round(estimated_value - customer["buying_power"], 2),
        })
    if side == "sell" and customer["positions"].get(ticker, 0) < qty:
        reasons.append({
            "code": "insufficient_shares",
            "detail": f"You hold {customer['positions'].get(ticker, 0)} shares of {ticker}.",
        })
    if (
        customer["account_type"] == "margin"
        and customer["equity"] < 25_000
        and customer["day_trades_last_5_days"] >= 3
    ):
        reasons.append({
            "code": "pdt_restriction",
            "detail": "Pattern day trader limit reached (3 day trades in 5 business days with equity under $25,000).",
        })

    return {
        "account_id": account_id,
        "ticker": ticker,
        "side": side,
        "qty": qty,
        "mock_price": price,
        "estimated_value": estimated_value,
        "buying_power": customer["buying_power"],
        "eligible": not reasons,
        "blocking_reasons": reasons,
        "as_of": MOCK_NOW.isoformat(),
    }


TOOLS = [get_orders, get_transfers, check_trade_eligibility]
