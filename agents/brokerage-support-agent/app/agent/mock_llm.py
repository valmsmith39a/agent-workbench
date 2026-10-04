"""An offline stand-in for the LLM, used when no API key is set and in tests.

This is NOT an LLM. It fakes the two things the real model does in this
graph, using simple rules:

1. Given the customer's question, decide whether to call a tool and with
   which arguments (here: spot a ticker, call get_trade_status).
2. Given the tool's JSON result, write a reply.

It lets the whole flow run without network access. Set ANTHROPIC_API_KEY to
use Claude instead; nothing else changes.
"""

import json
import re
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

NOT_TICKERS = {"I", "A", "OK", "ID", "US", "USD"}
TRADE_WORDS = ("trade", "order", "fill", "go through", "execute", "bought", "sold")


def pick_tool_call(question: str) -> dict[str, Any] | None:
    symbol = next((t for t in re.findall(r"\b[A-Z]{1,5}\b", question) if t not in NOT_TICKERS), None)
    if symbol is None and not any(w in question.lower() for w in TRADE_WORDS):
        return None
    args = {"symbol": symbol} if symbol else {}
    return {"name": "get_trade_status", "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}


def describe_order(o: dict[str, Any]) -> str:
    what = f"your {o['side'].lower()} order for {o['quantity']} shares of {o['symbol']} ({o['order_id']})"
    if o["status"] == "FILLED":
        return f"Yes, {what} filled: {o['filled_quantity']} shares at an average price of ${o['average_fill_price']:,.2f}."
    if o["status"] == "PENDING":
        return f"Not yet. {what[0].upper() + what[1:]} is still pending: {o['status_reason']}"
    return f"No. {what[0].upper() + what[1:]} was rejected: {o['status_reason']}"


def write_reply(result: dict[str, Any]) -> str:
    if "error" in result:
        return f"Sorry, I couldn't look that up: {result['error']['message']}"
    if not result["orders"]:
        which = f"{result['symbol']} " if result["symbol"] else ""
        return f"I couldn't find any {which}orders on your account."
    return " ".join(describe_order(o) for o in result["orders"])


class MockBrokerageChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock-keyword-router"

    def bind_tools(self, tools, **kwargs):
        return self  # it already knows its one tool

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            reply = AIMessage(content=write_reply(json.loads(last.text)))
        else:
            call = pick_tool_call(last.text if isinstance(last, HumanMessage) else "")
            if call:
                reply = AIMessage(content="", tool_calls=[call])
            else:
                reply = AIMessage(content="I can help you check the status of your orders. Which trade are you asking about?")
        return ChatResult(generations=[ChatGeneration(message=reply)])
