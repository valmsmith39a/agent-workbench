import pytest
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.shared.memory import create_connected_server_and_client_session

from app.mcp.server import create_mcp_server
from app.services.mock_brokerage_service import MockBrokerageService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def mcp_session():
    """A real MCP client session connected in-memory to the brokerage server."""
    server = create_mcp_server(MockBrokerageService())
    async with create_connected_server_and_client_session(server) as session:
        yield session


@pytest.fixture
async def mcp_tools(mcp_session):
    return await load_mcp_tools(mcp_session)
