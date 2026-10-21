"""FastAPI app: GET / serves ui/index.html, POST /chat runs the agent.

    uvicorn api:app --app-dir agent --port 8010     # from agents/coffee-shop/

The MCP server is launched once at startup and kept open (like brokerage's app/main.py).
"""

import os
import sys
import time
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from agent import run_graph  # noqa: E402
from prompts import CUSTOMERS  # noqa: E402
from toolbox import open_toolbox  # noqa: E402

UI = Path(__file__).resolve().parent.parent / "ui" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        app.state.toolbox = await stack.enter_async_context(open_toolbox())
        yield


app = FastAPI(title="Coffee Shop Support Agent", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    customer_id: str = "CUST-201"  # demo stand-in for an authenticated session
    history: list[dict] = []


class ChatResponse(BaseModel):
    answer: str
    steps: int
    tool_calls: int
    tool_source: str
    trace: list[dict]
    latency_ms: float


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(UI)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if req.customer_id not in CUSTOMERS:
        raise HTTPException(404, "unknown customer")
    t = time.perf_counter()
    s = await run_graph(req.message, req.customer_id, app.state.toolbox, req.history)
    return ChatResponse(answer=s["answer"], steps=s["steps"], tool_calls=s["tool_calls"], tool_source=app.state.toolbox.kind,
                        trace=s["trace"], latency_ms=round((time.perf_counter() - t) * 1000, 1))
