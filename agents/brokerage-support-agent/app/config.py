"""Settings shared by the CLI and the API."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Stand-in for the signed-in customer until there is real authentication.
DEMO_ACCOUNT_ID = "ACCT-DEMO-1001"

# How to launch the brokerage MCP server: as a subprocess speaking MCP over stdio.
MCP_SERVERS = {
    "brokerage": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "app.mcp.server"],
        "cwd": str(PROJECT_ROOT),
    },
}
