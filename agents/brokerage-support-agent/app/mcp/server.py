"""The brokerage MCP server.

Run standalone over stdio (this is how the FastAPI app launches it):

    python -m app.mcp.server
"""

from mcp.server.fastmcp import FastMCP

from app.mcp.tools import accounts, trades, transfers
from app.services.brokerage_service import BrokerageService
from app.services.mock_brokerage_service import MockBrokerageService


def create_mcp_server(service: BrokerageService) -> FastMCP:
    mcp = FastMCP("brokerage-support")
    trades.register(mcp, service)
    transfers.register(mcp, service)
    accounts.register(mcp, service)
    return mcp


mcp = create_mcp_server(MockBrokerageService())

if __name__ == "__main__":
    mcp.run(transport="stdio")
