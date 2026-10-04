"""Call the MCP tools through a real MCP client session.

The session is connected to the server in memory (no subprocess), but every
call still goes through the MCP protocol: list_tools, call_tool, JSON results.
"""

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from app.mcp.server import mcp

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def session():
    async with create_connected_server_and_client_session(mcp) as session:
        yield session


async def call(session, name, **args):
    result = await session.call_tool(name, args)
    assert not result.isError
    return result.structuredContent


async def test_server_advertises_all_tools(session):
    tools = await session.list_tools()
    assert [t.name for t in tools.tools] == ["get_trade_status", "get_transfer_status", "get_account_restrictions"]


@pytest.mark.parametrize(
    "symbol, status, avg_price",
    [("NVDA", "FILLED", 118.42), ("TSLA", "PENDING", None), ("AMD", "REJECTED", None)],
)
async def test_get_trade_status(session, symbol, status, avg_price):
    data = await call(session, "get_trade_status", account_id="ACCT-DEMO-1001", symbol=symbol)
    assert data["symbol"] == symbol
    [order] = data["orders"]
    assert order["status"] == status
    assert order["average_fill_price"] == avg_price


async def test_errors_come_back_as_structured_data(session):
    data = await call(session, "get_trade_status", account_id="ACCT-DEMO-9999")
    assert data["error"]["code"] == "ACCOUNT_NOT_FOUND"
    data = await call(session, "get_trade_status", account_id="ACCT-DEMO-1001", symbol="not a ticker")
    assert data["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("amount, status", [(5000, "PROCESSING"), (2500, "COMPLETED"), (1000, "FAILED")])
async def test_get_transfer_status(session, amount, status):
    data = await call(session, "get_transfer_status", account_id="ACCT-DEMO-1001", amount=amount)
    [transfer] = data["transfers"]
    assert transfer["status"] == status
    assert transfer["transfer_id"].startswith("TRF-")


async def test_transfer_errors_come_back_as_structured_data(session):
    data = await call(session, "get_transfer_status", account_id="ACCT-DEMO-1001", amount=-1)
    assert data["error"]["code"] == "INVALID_REQUEST"


async def test_get_account_restrictions(session):
    data = await call(
        session, "get_account_restrictions", account_id="ACCT-DEMO-1001", symbol="NVDA", side="BUY", quantity=10
    )
    assert data["can_place_order"] is False
    assert data["blocking_reasons"][0]["code"] == "UNSETTLED_FUNDS"
    assert data["unsettled_settlement_date"] == "2026-10-05"
