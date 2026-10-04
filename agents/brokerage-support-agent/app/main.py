"""The HTTP API: POST /api/chat sends one customer message to the agent.

On startup the app launches the brokerage MCP server as a subprocess, keeps
one MCP session open for as long as the app runs, and builds the agent graph
once. Each request then just runs the graph.

    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app.agent.graph import build_graph
from app.agent.llm import create_chat_model
from app.config import DEMO_ACCOUNT_ID, MCP_SERVERS
from app.models.api import ChatRequest, ChatResponse, ToolCall


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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # The account comes from the server side (later: the authenticated session),
    # never from the request body or the model.
    state = await app.state.graph.ainvoke({"messages": [HumanMessage(req.message)], "account_id": DEMO_ACCOUNT_ID})
    tool_calls = [
        ToolCall(name=call["name"], args=call["args"])
        for message in state["messages"]
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]
    return ChatResponse(answer=state["messages"][-1].text, tool_calls=tool_calls, model=app.state.model_name)
