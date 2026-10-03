"""Seed data for the mock brokerage. Every person, account and ID is fictional.

Four demo customers cover the scenarios the demo needs:

    ACCT-DEMO-1001  Alex Rivera    insufficient buying power
    ACCT-DEMO-1002  Jordan Lee     unsettled funds (cash account, T+1)
    ACCT-DEMO-1003  Sam Patel      account restriction (ID verification)
    ACCT-DEMO-1004  Taylor Morgan  no restriction

Trades cover FILLED / PARTIALLY_FILLED / PENDING / REJECTED and transfers
cover PROCESSING / COMPLETED / FAILED.
"""

from datetime import date

AS_OF = date(2026, 10, 2)

# Mock quotes used to estimate the cost of a proposed order. Not market data.
QUOTES = {
    "AAPL": 230.17,
    "AMD": 152.30,
    "GOOGL": 165.40,
    "MSFT": 431.20,
    "NVDA": 118.90,
    "TSLA": 251.80,
}

ACCOUNTS = {
    "ACCT-DEMO-1001": {
        "customer_name": "Alex Rivera",
        "account_type": "CASH",
        "buying_power": 412.55,
        "settled_cash": 412.55,
        "unsettled_funds": 0.0,
        "unsettled_settlement_date": None,
        "positions": {"NVDA": 10, "TSLA": 5},
        "restrictions": [],
    },
    "ACCT-DEMO-1002": {
        "customer_name": "Jordan Lee",
        "account_type": "CASH",
        "buying_power": 150.00,
        "settled_cash": 150.00,
        "unsettled_funds": 6214.59,
        "unsettled_settlement_date": date(2026, 10, 5),
        "positions": {"MSFT": 4},
        "restrictions": [],
    },
    "ACCT-DEMO-1003": {
        "customer_name": "Sam Patel",
        "account_type": "MARGIN",
        "buying_power": 18400.00,
        "settled_cash": 9200.00,
        "unsettled_funds": 0.0,
        "unsettled_settlement_date": None,
        "positions": {"GOOGL": 40},
        "restrictions": [
            {
                "code": "IDENTITY_VERIFICATION_REQUIRED",
                "description": (
                    "Opening (buy) orders are restricted until updated identity "
                    "documents are verified. Closing (sell) orders are still allowed."
                ),
                "blocks": ["BUY"],
                "resolution": (
                    "Upload a government-issued photo ID under Settings > Documents. "
                    "Reviews typically complete within 1 business day."
                ),
            }
        ],
    },
    "ACCT-DEMO-1004": {
        "customer_name": "Taylor Morgan",
        "account_type": "MARGIN",
        "buying_power": 25310.40,
        "settled_cash": 12655.20,
        "unsettled_funds": 0.0,
        "unsettled_settlement_date": None,
        "positions": {"NVDA": 30, "AAPL": 12},
        "restrictions": [],
    },
}

# Orders are listed newest first within each account.
ORDERS = {
    "ACCT-DEMO-1001": [
        {
            "order_id": "ORD-7F3K-1003",
            "symbol": "AMD",
            "side": "BUY",
            "quantity": 25,
            "order_type": "MARKET",
            "status": "REJECTED",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T15:10:44Z",
            "updated_at": "2026-10-02T15:10:44Z",
            "status_reason_code": "INSUFFICIENT_BUYING_POWER",
        },
        {
            "order_id": "ORD-7F3K-1002",
            "symbol": "TSLA",
            "side": "SELL",
            "quantity": 5,
            "order_type": "LIMIT",
            "limit_price": 265.00,
            "status": "PENDING",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T13:45:12Z",
            "updated_at": "2026-10-02T13:45:12Z",
            "status_reason_code": "LIMIT_PRICE_NOT_REACHED",
        },
        {
            "order_id": "ORD-7F3K-1001",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 10,
            "order_type": "MARKET",
            "status": "FILLED",
            "filled_quantity": 10,
            "average_fill_price": 118.42,
            "submitted_at": "2026-10-01T14:32:05Z",
            "updated_at": "2026-10-01T14:32:06Z",
        },
    ],
    "ACCT-DEMO-1002": [
        {
            "order_id": "ORD-9J4T-3002",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 20,
            "order_type": "MARKET",
            "status": "REJECTED",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T16:02:31Z",
            "updated_at": "2026-10-02T16:02:31Z",
            "status_reason_code": "INSUFFICIENT_SETTLED_FUNDS",
        },
        {
            "order_id": "ORD-9J4T-3001",
            "symbol": "AAPL",
            "side": "SELL",
            "quantity": 27,
            "order_type": "MARKET",
            "status": "FILLED",
            "filled_quantity": 27,
            "average_fill_price": 230.17,
            "submitted_at": "2026-10-02T14:05:10Z",
            "updated_at": "2026-10-02T14:05:11Z",
        },
    ],
    "ACCT-DEMO-1003": [
        {
            "order_id": "ORD-2H8D-5002",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 5,
            "order_type": "LIMIT",
            "limit_price": 115.00,
            "status": "REJECTED",
            "filled_quantity": 0,
            "submitted_at": "2026-10-02T14:20:00Z",
            "updated_at": "2026-10-02T14:20:00Z",
            "status_reason_code": "ACCOUNT_RESTRICTED",
        },
        {
            "order_id": "ORD-2H8D-5001",
            "symbol": "GOOGL",
            "side": "SELL",
            "quantity": 10,
            "order_type": "MARKET",
            "status": "FILLED",
            "filled_quantity": 10,
            "average_fill_price": 165.12,
            "submitted_at": "2026-09-30T15:00:02Z",
            "updated_at": "2026-09-30T15:00:03Z",
        },
    ],
    "ACCT-DEMO-1004": [
        {
            "order_id": "ORD-4M6X-8001",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 50,
            "order_type": "LIMIT",
            "limit_price": 118.00,
            "status": "PARTIALLY_FILLED",
            "filled_quantity": 30,
            "average_fill_price": 117.96,
            "submitted_at": "2026-10-02T14:58:40Z",
            "updated_at": "2026-10-02T15:31:17Z",
            "status_reason_code": "LIMIT_PRICE_NOT_REACHED",
        },
    ],
}

# Transfers are listed newest first within each account.
TRANSFERS = {
    "ACCT-DEMO-1001": [
        {
            "transfer_id": "TRF-5Q2M-2001",
            "amount": 5000.00,
            "direction": "DEPOSIT",
            "method": "ACH",
            "external_account": "Checking ****4821",
            "status": "PROCESSING",
            "initiated_date": "2026-10-01",
            "expected_available_date": "2026-10-05",
        },
        {
            "transfer_id": "TRF-5Q2M-2003",
            "amount": 1000.00,
            "direction": "WITHDRAWAL",
            "method": "ACH",
            "external_account": "Savings ****1177",
            "status": "FAILED",
            "initiated_date": "2026-09-28",
            "failure_reason": (
                "The receiving bank returned the transfer because the account is "
                "closed (ACH return code R02). The $1,000.00 was returned to your "
                "brokerage cash balance."
            ),
        },
        {
            "transfer_id": "TRF-5Q2M-2002",
            "amount": 2500.00,
            "direction": "DEPOSIT",
            "method": "ACH",
            "external_account": "Checking ****4821",
            "status": "COMPLETED",
            "initiated_date": "2026-09-22",
            "expected_available_date": "2026-09-24",
            "completed_date": "2026-09-24",
        },
    ],
    "ACCT-DEMO-1002": [
        {
            "transfer_id": "TRF-8W1N-4001",
            "amount": 500.00,
            "direction": "DEPOSIT",
            "method": "ACH",
            "external_account": "Checking ****0093",
            "status": "COMPLETED",
            "initiated_date": "2026-09-15",
            "expected_available_date": "2026-09-17",
            "completed_date": "2026-09-17",
        },
    ],
    "ACCT-DEMO-1003": [
        {
            "transfer_id": "TRF-3C6V-6001",
            "amount": 5000.00,
            "direction": "DEPOSIT",
            "method": "ACH",
            "external_account": "Checking ****7310",
            "status": "FAILED",
            "initiated_date": "2026-09-29",
            "failure_reason": (
                "Your bank returned the deposit for insufficient funds in the linked "
                "checking account (ACH return code R01). No money was moved."
            ),
        },
    ],
    "ACCT-DEMO-1004": [
        {
            "transfer_id": "TRF-6R9P-7002",
            "amount": 10000.00,
            "direction": "DEPOSIT",
            "method": "WIRE",
            "external_account": "Checking ****5520",
            "status": "PROCESSING",
            "initiated_date": "2026-10-02",
            "expected_available_date": "2026-10-02",
        },
        {
            "transfer_id": "TRF-6R9P-7001",
            "amount": 5000.00,
            "direction": "WITHDRAWAL",
            "method": "ACH",
            "external_account": "Checking ****5520",
            "status": "COMPLETED",
            "initiated_date": "2026-09-25",
            "expected_available_date": "2026-09-29",
            "completed_date": "2026-09-29",
        },
    ],
}
