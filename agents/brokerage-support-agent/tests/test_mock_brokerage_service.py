import pytest

from app.services.mock_brokerage_service import (
    AccountNotFoundError,
    InvalidRequestError,
    get_trade_status,
    get_transfer_status,
)


@pytest.mark.parametrize(
    "symbol, status, filled, avg_price",
    [
        ("NVDA", "FILLED", 10, 118.42),
        ("TSLA", "PENDING", 0, None),
        ("AMD", "REJECTED", 0, None),
    ],
)
def test_trade_status_by_symbol(symbol, status, filled, avg_price):
    result = get_trade_status("ACCT-DEMO-1001", symbol=symbol.lower())
    assert len(result.orders) == 1
    order = result.orders[0]
    assert order.symbol == symbol
    assert order.status == status
    assert order.filled_quantity == filled
    assert order.average_fill_price == avg_price


def test_no_symbol_returns_all_orders():
    assert len(get_trade_status("ACCT-DEMO-1001").orders) == 3


def test_unknown_symbol_returns_no_orders():
    assert get_trade_status("ACCT-DEMO-1001", symbol="MSFT").orders == []


def test_unknown_account_raises():
    with pytest.raises(AccountNotFoundError):
        get_trade_status("ACCT-DEMO-9999")


def test_invalid_symbol_raises():
    with pytest.raises(InvalidRequestError):
        get_trade_status("ACCT-DEMO-1001", symbol="not a ticker")


@pytest.mark.parametrize(
    "amount, status, expected_available",
    [(5000, "PROCESSING", "2026-10-05"), (2500, "COMPLETED", "2026-09-24"), (1000, "FAILED", None)],
)
def test_transfer_status_by_amount(amount, status, expected_available):
    result = get_transfer_status("ACCT-DEMO-1001", amount=amount)
    [transfer] = result.transfers
    assert transfer.status == status
    assert str(transfer.expected_available_date) == str(expected_available)


def test_failed_transfer_has_a_reason():
    [transfer] = get_transfer_status("ACCT-DEMO-1001", amount=1000).transfers
    assert "account is closed" in transfer.failure_reason


def test_transfer_direction_filter():
    result = get_transfer_status("ACCT-DEMO-1001", direction="deposit")
    assert [t.amount for t in result.transfers] == [5000, 2500]


def test_transfer_validation():
    with pytest.raises(InvalidRequestError):
        get_transfer_status("ACCT-DEMO-1001", amount=-5)
    with pytest.raises(InvalidRequestError):
        get_transfer_status("ACCT-DEMO-1001", direction="sideways")
    with pytest.raises(AccountNotFoundError):
        get_transfer_status("ACCT-DEMO-9999")
