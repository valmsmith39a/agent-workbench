import pytest

pytestmark = pytest.mark.anyio


async def call(session, name, **args):
    result = await session.call_tool(name, args)
    assert not result.isError
    return result.structuredContent


async def test_server_exposes_three_tools(mcp_session):
    tools = await mcp_session.list_tools()
    assert {t.name for t in tools.tools} == {"get_trade_status", "get_transfer_status", "get_account_restrictions"}


@pytest.mark.parametrize(
    "account_id, symbol, status, filled, avg_price, reason",
    [
        ("ACCT-DEMO-1001", "NVDA", "FILLED", 10, 118.42, None),
        ("ACCT-DEMO-1001", "TSLA", "PENDING", 0, None, "LIMIT_PRICE_NOT_REACHED"),
        ("ACCT-DEMO-1001", "AMD", "REJECTED", 0, None, "INSUFFICIENT_BUYING_POWER"),
        ("ACCT-DEMO-1004", "NVDA", "PARTIALLY_FILLED", 30, 117.96, "LIMIT_PRICE_NOT_REACHED"),
    ],
)
async def test_get_trade_status(mcp_session, account_id, symbol, status, filled, avg_price, reason):
    data = await call(mcp_session, "get_trade_status", account_id=account_id, symbol=symbol.lower())
    assert data["match_count"] == 1
    order = data["orders"][0]
    assert order["symbol"] == symbol
    assert order["status"] == status
    assert order["filled_quantity"] == filled
    assert order["average_fill_price"] == avg_price
    assert order["status_reason_code"] == reason
    assert order["order_id"].startswith("ORD-")
    assert order["status_explanation"]


async def test_get_trade_status_by_order_id_and_no_match(mcp_session):
    data = await call(mcp_session, "get_trade_status", account_id="ACCT-DEMO-1001", order_id="ORD-7F3K-1002")
    assert [o["symbol"] for o in data["orders"]] == ["TSLA"]
    data = await call(mcp_session, "get_trade_status", account_id="ACCT-DEMO-1001", symbol="MSFT")
    assert data["match_count"] == 0 and data["message"]


@pytest.mark.parametrize(
    "account_id, amount, status",
    [
        ("ACCT-DEMO-1001", 5000, "PROCESSING"),
        ("ACCT-DEMO-1001", 2500, "COMPLETED"),
        ("ACCT-DEMO-1001", 1000, "FAILED"),
    ],
)
async def test_get_transfer_status(mcp_session, account_id, amount, status):
    data = await call(mcp_session, "get_transfer_status", account_id=account_id, amount=amount)
    assert data["match_count"] == 1
    transfer = data["transfers"][0]
    assert transfer["status"] == status
    assert transfer["amount"] == amount
    assert transfer["transfer_id"].startswith("TRF-")
    assert transfer["initiated_date"]
    if status == "PROCESSING":
        assert transfer["expected_available_date"] == "2026-10-05"
    if status == "FAILED":
        assert "R02" in transfer["failure_reason"]


@pytest.mark.parametrize(
    "account_id, order, can_trade, code",
    [
        ("ACCT-DEMO-1001", {}, False, "INSUFFICIENT_BUYING_POWER"),  # re-checks rejected AMD order
        ("ACCT-DEMO-1002", {"symbol": "NVDA", "side": "BUY", "quantity": 20}, False, "UNSETTLED_FUNDS"),
        ("ACCT-DEMO-1003", {}, False, "IDENTITY_VERIFICATION_REQUIRED"),
        ("ACCT-DEMO-1004", {}, True, None),
        ("ACCT-DEMO-1004", {"symbol": "NVDA", "side": "BUY", "quantity": 100}, True, None),
    ],
)
async def test_get_account_restrictions(mcp_session, account_id, order, can_trade, code):
    data = await call(mcp_session, "get_account_restrictions", account_id=account_id, **order)
    assert data["can_trade"] is can_trade
    assert [b["code"] for b in data["blocking_reasons"]] == ([code] if code else [])
    assert isinstance(data["buying_power"], float)
    assert "unsettled_funds" in data


async def test_sell_allowed_while_buy_restricted(mcp_session):
    data = await call(
        mcp_session, "get_account_restrictions", account_id="ACCT-DEMO-1003", symbol="GOOGL", side="SELL", quantity=5
    )
    assert data["can_trade"] is True


async def test_validation_and_unknown_account_return_structured_errors(mcp_session):
    data = await call(mcp_session, "get_trade_status", account_id="ACCT-DEMO-1001", symbol="NOT A TICKER")
    assert data["error"]["code"] == "INVALID_REQUEST"
    data = await call(mcp_session, "get_account_restrictions", account_id="ACCT-DEMO-1001", symbol="NVDA")
    assert data["error"]["code"] == "INVALID_REQUEST"
    data = await call(mcp_session, "get_transfer_status", account_id="ACCT-DEMO-9999")
    assert data["error"]["code"] == "ACCOUNT_NOT_FOUND"
