"""FastAPI entrypoint: serves the chat UI and the /api/chat endpoint.

On startup it launches the brokerage MCP server as a stdio subprocess, keeps
one MCP session open for the life of the app, and builds the agent from the
tools that server advertises.
"""

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.errors import GraphRecursionError

from app.agent.llm import create_chat_model
from app.agent.support_agent import BrokerageSupportAgent
from app.config import PROJECT_ROOT, settings
from app.models.api import ChatRequest, ChatResponse
from app.services.mock_data import ACCOUNTS

logger = logging.getLogger("brokerage-support-agent")

MCP_CONNECTIONS = {
    "brokerage": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["-m", "app.mcp.server"],
        "cwd": str(PROJECT_ROOT),
    }
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model, model_name = create_chat_model(settings)
    client = MultiServerMCPClient(MCP_CONNECTIONS)
    async with client.session("brokerage") as session:
        tools = await load_mcp_tools(session)
        logger.info("Loaded MCP tools: %s; model: %s", [t.name for t in tools], model_name)
        app.state.agent = BrokerageSupportAgent(model, tools)
        app.state.model_name = model_name
        yield


app = FastAPI(title="Brokerage Customer Support Agent", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


@app.get("/api/config")
def config():
    # Demo customers for the "signed in as" switcher. A real app would have
    # exactly one: the authenticated user.
    return {
        "model": app.state.model_name,
        "default_account_id": settings.default_account_id,
        "demo_accounts": [{"account_id": k, "name": v["customer_name"]} for k, v in ACCOUNTS.items()],
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    account_id = req.account_id or settings.default_account_id
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=403, detail="Unknown demo account.")
    start = time.perf_counter()
    try:
        reply = await app.state.agent.reply(req.message, account_id, [t.model_dump() for t in req.history])
    except GraphRecursionError:
        raise HTTPException(status_code=500, detail="The agent took too many steps. Please rephrase.") from None
    return ChatResponse(
        answer=reply.answer,
        tool_calls=reply.tool_traces,
        model=app.state.model_name,
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
    )
