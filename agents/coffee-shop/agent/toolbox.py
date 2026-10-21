"""Tool access for the agent: MCP over stdio (default) or direct import (fallback)."""

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent / "mcp-server"


class LocalToolbox:
    """Fallback: import the same tool functions in-process."""
    kind = "local"

    def __init__(self):
        sys.path.insert(0, str(SERVER_DIR))
        import tools
        self._tools = tools.TOOLS
        self.names = sorted(self._tools)

    async def call(self, name, args):
        return self._tools[name](**args)


class MCPToolbox:
    kind = "mcp"

    def __init__(self, session, names):
        self.session, self.names = session, names

    async def call(self, name, args):
        r = await self.session.call_tool(name, args)
        if r.structuredContent is not None:
            sc = r.structuredContent
            return sc.get("result", sc) if set(sc) == {"result"} else sc
        return json.loads(r.content[0].text)


@asynccontextmanager
async def open_toolbox(prefer_mcp: bool = True):
    """Yield an MCPToolbox connected to mcp-server/server.py, else a LocalToolbox."""
    if prefer_mcp and os.environ.get("COFFEE_TOOLS", "mcp") != "local":
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            yield LocalToolbox()
            return
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER_DIR / "server.py")])
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = sorted(t.name for t in (await s.list_tools()).tools)
                yield MCPToolbox(s, names)
        return
    yield LocalToolbox()
