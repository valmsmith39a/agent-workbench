"""The brokerage MCP server.

Creates the server and registers its tools. Run it over stdio, the way an
MCP client (and later, the agent) launches it:

    python -m app.mcp.server
"""

from mcp.server.fastmcp import FastMCP

from app.mcp.tools import trades, transfers

mcp = FastMCP("brokerage-support")
trades.register(mcp)
transfers.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
