"""An offline stand-in for the LLM, used when no API key is set and in tests.

This is NOT an LLM. It fakes the two things the real model does in this
graph, using simple rules:

1. Given the customer's question, decide whether to call a tool and with
   which arguments ("can't"/"can I" -> get_account_restrictions, money
   words -> get_transfer_status, a ticker or trade words -> get_trade_status).
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

NOT_TICKERS = {"I", "A", "OK", "ID", "US", "USD", "ACH"}
TRADE_WORDS = ("trade", "order", "fill", "go through", "execute", "bought", "sold")
TRANSFER_WORDS = ("transfer", "deposit", "withdraw", "money", "$")
FALLBACK_REPLY = "I can help with your orders, transfers, and why a trade can't be placed. What would you like to look up?"
RESTRICTION_WORDS = ("can't", "cannot", "can i", "unable", "buying power", "restrict", "not allowed")


def find_ticker(question: str) -> str | None:
    return next((t for t in re.findall(r"\b[A-Z]{1,5}\b", question) if t not in NOT_TICKERS), None)


def pick_tool_call(question: str) -> dict[str, Any] | None:
    lower = question.lower()
    if any(w in lower for w in RESTRICTION_WORDS):
        name, args = "get_account_restrictions", {}
        symbol = find_ticker(question)
        quantity = re.search(r"\b(\d+)\s+(?:shares?\s+(?:of\s+)?)?[A-Z]{1,5}\b", question)
        side = "SELL" if "sell" in lower else "BUY" if "buy" in lower else None
        if symbol and quantity and side:
            args = {"symbol": symbol, "side": side, "quantity": int(quantity.group(1))}
    elif any(w in lower for w in TRANSFER_WORDS):
        name, args = "get_transfer_status", {}
        amount = re.search(r"\$\s?([\d,]+(?:\.\d{1,2})?)", question)
        if amount:
            args["amount"] = float(amount.group(1).replace(",", ""))
        if "withdraw" in lower:
            args["direction"] = "WITHDRAWAL"
        elif "deposit" in lower:
            args["direction"] = "DEPOSIT"
    else:
        symbol = find_ticker(question)
        if symbol is None and not any(w in lower for w in TRADE_WORDS):
            return None
        name, args = "get_trade_status", {"symbol": symbol} if symbol else {}
    return {"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:12]}"}


def capitalize(text: str) -> str:
    return text[0].upper() + text[1:]


def describe_order(o: dict[str, Any]) -> str:
    what = f"your {o['side'].lower()} order for {o['quantity']} shares of {o['symbol']} ({o['order_id']})"
    if o["status"] == "FILLED":
        return f"Yes, {what} filled: {o['filled_quantity']} shares at an average price of ${o['average_fill_price']:,.2f}."
    if o["status"] == "PENDING":
        return f"Not yet. {capitalize(what)} is still pending: {o['status_reason']}"
    return f"No. {capitalize(what)} was rejected: {o['status_reason']}"


def describe_transfer(t: dict[str, Any]) -> str:
    preposition = "from" if t["direction"] == "DEPOSIT" else "to"
    what = (
        f"your ${t['amount']:,.2f} {t['direction'].lower()} {preposition} {t['external_account']} "
        f"({t['transfer_id']}), started {t['initiated_date']},"
    )
    if t["status"] == "COMPLETED":
        return f"{capitalize(what)} is complete. The money was available on {t['expected_available_date']}."
    if t["status"] == "PROCESSING":
        return f"{capitalize(what)} is still processing. It should be available on {t['expected_available_date']}."
    return f"{capitalize(what)} failed. {t['failure_reason']}"


def describe_restrictions(r: dict[str, Any]) -> str:
    order = r["proposed_order"]
    if order is not None:
        noun = "share" if order["quantity"] == 1 else "shares"
        what = f"{order['side'].lower()} {order['quantity']} {noun} of {order['symbol']}"
        cost = f"(estimated cost ${order['estimated_cost']:,.2f})"
        if r["can_place_order"]:
            return f"Yes, you can {what} {cost}. Your buying power is ${r['buying_power']:,.2f}."
        reasons = " ".join(b["message"] for b in r["blocking_reasons"])
        return f"You can't {what} {cost} right now. {reasons}"
    parts = [f"Your buying power is ${r['buying_power']:,.2f}."]
    if r["unsettled_funds"]:
        parts.append(
            f"${r['unsettled_funds']:,.2f} from a recent sale is unsettled until {r['unsettled_settlement_date']}."
        )
    for x in r["restrictions"]:
        parts.append(x["description"])
    parts.append("Which order are you trying to place (ticker, buy or sell, and number of shares)? I can check it exactly.")
    return " ".join(parts)


def write_reply(tool_name: str, result: dict[str, Any]) -> str:
    if "error" in result:
        return f"Sorry, I couldn't look that up: {result['error']['message']}"
    if tool_name == "get_account_restrictions":
        return describe_restrictions(result)
    if tool_name == "get_transfer_status":
        if not result["transfers"]:
            return "I couldn't find a matching transfer on your account."
        return " ".join(describe_transfer(t) for t in result["transfers"])
    if not result["orders"]:
        which = f"{result['symbol']} " if result["symbol"] else ""
        return f"I couldn't find any {which}orders on your account."
    return " ".join(describe_order(o) for o in result["orders"])


class MockBrokerageChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "mock-keyword-router"

    def bind_tools(self, tools, **kwargs):
        return self  # it already knows its tools

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            reply = AIMessage(content=write_reply(last.name, json.loads(last.text)))
        else:
            call = pick_tool_call(last.text if isinstance(last, HumanMessage) else "")
            if call:
                reply = AIMessage(content="", tool_calls=[call])
            else:
                reply = AIMessage(content=FALLBACK_REPLY)
        return ChatResult(generations=[ChatGeneration(message=reply)])
