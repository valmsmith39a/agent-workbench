"""An offline stand-in for the LLM, used when no API key is configured and in tests.

It is NOT an LLM: it routes on keywords and phrases its answer from the
deterministic `status_explanation` / `blocking_reasons` fields the service
returns. It exists so the demo and test suite run end to end without network
access. Set ANTHROPIC_API_KEY to use a real model.
"""

import json
import re
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

NOT_TICKERS = {"I", "A", "ACH", "ID", "OK", "USD", "US", "IRA", "ETF", "BUY", "SELL"}
RESTRICTION_WORDS = ("can't", "can i", "cannot", "can not", "unable", "not able", "won't let", "restrict", "buying power", "blocked")
TRANSFER_WORDS = ("transfer", "deposit", "withdraw", "money", "ach", "wire", "$")
TRADE_WORDS = ("trade", "order", "fill", "go through", "execute", "bought", "sold", "buy", "sell")


def route(text: str) -> tuple[str, dict[str, Any]] | None:
    lower = text.lower()
    symbol = next((t for t in re.findall(r"\b[A-Z]{1,5}\b", text) if t not in NOT_TICKERS), None)
    if any(w in lower for w in RESTRICTION_WORDS):
        args: dict[str, Any] = {}
        qty = re.search(r"\b(\d+)\s+(?:shares?\s+(?:of\s+)?)?[A-Z]{1,5}\b", text)
        side = "SELL" if "sell" in lower else "BUY" if "buy" in lower else None
        if symbol and qty and side:
            args = {"symbol": symbol, "side": side, "quantity": int(qty.group(1))}
        return "get_account_restrictions", args
    if any(w in lower for w in TRANSFER_WORDS):
        args = {}
        amount = re.search(r"\$\s?([\d,]+(?:\.\d{1,2})?)", text)
        if amount:
            args["amount"] = float(amount.group(1).replace(",", ""))
        return "get_transfer_status", args
    if any(w in lower for w in TRADE_WORDS) or symbol:
        return "get_trade_status", {"symbol": symbol} if symbol else {}
    return None


def summarize(tool_name: str, result: dict[str, Any]) -> str:
    if "error" in result:
        return f"Sorry, I couldn't look that up: {result['error']['message']}"
    if tool_name == "get_trade_status":
        lines = [o["status_explanation"] for o in result["orders"]]
        return " ".join(lines) or "I couldn't find any matching orders on your account."
    if tool_name == "get_transfer_status":
        lines = [t["status_explanation"] for t in result["transfers"]]
        return " ".join(lines) or "I couldn't find any matching transfers on your account."
    reasons = [b["message"] for b in result["blocking_reasons"]]
    if reasons:
        return "Here's what's blocking trading on your account: " + " ".join(reasons)
    return "I don't see anything blocking trading on your account. " + " ".join(result["notes"])


class MockBrokerageChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock-keyword-router"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            tool_name = next(
                c["name"]
                for m in reversed(messages)
                if isinstance(m, AIMessage)
                for c in m.tool_calls
                if c["id"] == last.tool_call_id
            )
            message = AIMessage(content=summarize(tool_name, json.loads(last.text)))
        else:
            text = last.text if isinstance(last, HumanMessage) else ""
            routed = route(text)
            if routed is None:
                message = AIMessage(
                    content="I can help with order status, transfers, and why a trade can't be placed. What would you like to check?"
                )
            else:
                name, args = routed
                message = AIMessage(
                    content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}]
                )
        return ChatResult(generations=[ChatGeneration(message=message)])
