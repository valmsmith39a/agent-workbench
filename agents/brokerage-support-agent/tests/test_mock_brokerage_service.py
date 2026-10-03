import pytest

from app.services.mock_brokerage_service import (
    AccountNotFoundError,
    InvalidRequestError,
    get_trade_status,
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
