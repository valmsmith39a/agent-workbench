"""Coffee shop MCP server (official mcp SDK >=1.20,<2, FastMCP, stdio).

    python mcp-server/server.py          # from agents/coffee-shop/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp.server.fastmcp import FastMCP  # noqa: E402

from tools import account, menu, ordering  # noqa: E402

mcp = FastMCP("coffee-shop-support", log_level="WARNING")  # quiet "Processing request" logs
menu.register(mcp)
ordering.register(mcp)
account.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
