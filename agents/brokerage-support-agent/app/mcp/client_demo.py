"""Talk to the brokerage MCP server the way an agent will, but without an LLM.

Launches the server as a subprocess, connects over stdio, lists the tools it
advertises, and calls get_trade_status.

    python -m app.mcp.client_demo
"""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp.server"])


async def main() -> None:
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools the server advertises:")
            for tool in tools.tools:
                print(f"\n- {tool.name}")
                print(f"  description: {tool.description.splitlines()[0]}")
                print(f"  input schema: {json.dumps(tool.inputSchema['properties'], indent=4)}")

            print("\nCalling get_trade_status(account_id='ACCT-DEMO-1001', symbol='NVDA'):")
            result = await session.call_tool("get_trade_status", {"account_id": "ACCT-DEMO-1001", "symbol": "NVDA"})
            print(json.dumps(result.structuredContent, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
