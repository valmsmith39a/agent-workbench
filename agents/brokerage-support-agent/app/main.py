"""The web app: GET / serves the chat page, POST /api/chat sends one customer
message to the agent.

On startup the app launches the brokerage MCP server as a subprocess, keeps
one MCP session open for as long as the app runs, and builds the agent graph
once. Each request then just runs the graph.

    uvicorn app.main:app --reload
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app.agent.graph import build_graph
from app.agent.llm import create_chat_model
from app.config import DEMO_ACCOUNT_ID, MCP_SERVERS, PROJECT_ROOT
from app.models.api import ChatRequest, ChatResponse, ToolTrace


@asynccontextmanager
async def lifespan(app: FastAPI):
    model, model_name = create_chat_model()
    client = MultiServerMCPClient(MCP_SERVERS)
    async with client.session("brokerage") as session:  # MCP server runs until the app stops
        tools = await load_mcp_tools(session)
        app.state.graph = build_graph(model, tools)
        app.state.model_name = model_name
        yield


app = FastAPI(title="Brokerage Customer Support Agent", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # The account comes from the server side (later: the authenticated session),
    # never from the request body or the model.
    start = time.perf_counter()
    state = await app.state.graph.ainvoke(
        {"messages": [HumanMessage(req.message)], "account_id": DEMO_ACCOUNT_ID, "tool_traces": []}
    )
    return ChatResponse(
        answer=state["messages"][-1].text,
        tool_calls=[ToolTrace(**trace) for trace in state["tool_traces"]],
        model=app.state.model_name,
        total_latency_ms=round((time.perf_counter() - start) * 1000, 1),
    )
