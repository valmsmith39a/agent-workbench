"""Investment brokerage support agent: a minimal LangGraph scaffold.

Graph (same shape as examples/langgraph_style_loop, but built with LangGraph):

    START -> agent --(tools_condition: tool calls?)--> tools -> agent ...
                  \\--(no tool calls)----------------> END

- ``agent`` node: calls the chat model with a system prompt + the conversation.
- ``tools`` node: LangGraph's prebuilt ``ToolNode`` runs the requested tools.
- ``tools_condition``: prebuilt router; goes to "tools" if the last AI message
  has tool_calls, otherwise END.

The model is a NO-API-KEY scripted fake (``ScriptedFakeChatModel``) so this runs
offline. Swap it for a real model in ``get_model()``.

Run:
    python agents/investment_brokerage_support_agent/agent.py               # 3 demo questions
    python agents/investment_brokerage_support_agent/agent.py -i --account ACC-1001   # REPL
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableConfig
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

try:  # works both as a script and as a package import
    from .tools import MOCK_PRICES, TOOLS
except ImportError:  # pragma: no cover
    from tools import MOCK_PRICES, TOOLS

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a customer support agent for an online investment brokerage.

The customer is already logged in. Their account_id is: {account_id}
Always use exactly this account_id when calling tools; never ask the customer for it
and never look up any other account.

Rules:
- You are READ-ONLY. You can look up orders, transfers, and trade eligibility. You
  cannot place, modify, or cancel orders or transfers. If asked to, explain that
  you can't and tell the customer how to do it themselves or offer a human agent.
- Do NOT give investment advice (no buy/sell/hold recommendations, price
  predictions, or suitability opinions). Stick to facts about their account.
- Ground every answer in tool results. Don't guess order statuses, amounts, or dates.
- If you can't answer with the available tools, or the customer is upset, reports
  fraud, or asks for an exception, escalate: say you're handing off to a human
  support specialist.
- Be concise and clear; give the specific numbers (quantities, prices, dates).
"""


# ---------------------------------------------------------------------------
# State: MessagesState plus an optional account_id.
# account_id can come from config["configurable"]["account_id"] (preferred) or
# from the graph state.
# ---------------------------------------------------------------------------
class SupportState(MessagesState):
    account_id: Optional[str]


# ---------------------------------------------------------------------------
# No-API-key fake chat model that supports tool calls.
#
# It follows a fixed script, like mock_llm in examples/langgraph_style_loop:
#   1. If the last message is a ToolMessage -> write a final answer from it.
#   2. Otherwise classify the user's question by keywords and emit an
#      AIMessage with the matching tool_call (or a refusal / escalation).
# ---------------------------------------------------------------------------
class ScriptedFakeChatModel(BaseChatModel):
    """Deterministic fake model that emits tool_calls; no network, no API key."""

    @property
    def _llm_type(self) -> str:
        return "scripted-fake-brokerage"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any):
        # Accept tools the same way real chat models do, so swapping is painless.
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._respond(messages))])

    # --- scripted behaviour -------------------------------------------------
    def _respond(self, messages: list[BaseMessage]) -> AIMessage:
        account_id = self._account_from_system(messages)
        last = messages[-1]
        if isinstance(last, ToolMessage):
            return AIMessage(content=self._final_answer(last))

        text = last.content if isinstance(last.content, str) else str(last.content)
        lower = text.lower()
        ticker = self._find_ticker(text)

        if re.search(r"\bshould i\b|\brecommend|\bgood (buy|investment)\b|\bwill .* go up\b", lower):
            return AIMessage(content=(
                "I'm not able to give investment advice or recommendations. I can help with "
                "your orders, transfers, or whether a trade can be placed. If you'd like to "
                "discuss your investment strategy, I can connect you with a licensed representative."
            ))
        if re.search(r"\bcan'?t\b|\bcannot\b|\bunable\b|\bwon'?t let\b|\beligib", lower) and ticker:
            side = "sell" if re.search(r"\bsell", lower) else "buy"
            qty_match = re.search(r"\b(\d+)\s*(shares?)?\b", lower)
            qty = int(qty_match.group(1)) if qty_match else 1
            return self._call("check_trade_eligibility", account_id=account_id, ticker=ticker, side=side, qty=qty)
        if re.search(r"transfer|deposit|withdraw|ach|wire|acats", lower):
            return self._call("get_transfers", account_id=account_id)
        if re.search(r"order|trade|fill|go through|went through|execute", lower):
            return self._call("get_orders", account_id=account_id, ticker=ticker)

        return AIMessage(content=(
            "I'm not able to help with that using the tools I have. Let me hand you off to a "
            "human support specialist who can take a closer look."
        ))

    @staticmethod
    def _call(name: str, **args: Any) -> AIMessage:
        args = {k: v for k, v in args.items() if v is not None}
        return AIMessage(content="", tool_calls=[{"id": f"call_{name}", "name": name, "args": args, "type": "tool_call"}])

    @staticmethod
    def _account_from_system(messages: list[BaseMessage]) -> Optional[str]:
        for m in messages:
            if isinstance(m, SystemMessage):
                match = re.search(r"account_id is: (\S+)", str(m.content))
                if match:
                    return match.group(1)
        return None

    @staticmethod
    def _find_ticker(text: str) -> Optional[str]:
        for word in re.findall(r"\b[A-Za-z]{2,5}\b", text):
            if word.upper() in MOCK_PRICES and (word.isupper() or len(word) > 3):
                return word.upper()
        return None

    @staticmethod
    def _final_answer(tool_msg: ToolMessage) -> str:
        try:
            data = json.loads(tool_msg.content)
        except (TypeError, json.JSONDecodeError):
            return "Something went wrong looking that up. Let me connect you with a human support specialist."
        if "error" in data:
            return f"I couldn't look that up ({data['error']}). Let me connect you with a human support specialist."

        if tool_msg.name == "get_orders":
            orders = data["orders"]
            if not orders:
                what = f" for {data['ticker']}" if data.get("ticker") else ""
                return f"I don't see any recent orders{what} on your account."
            o = orders[0]  # most recent first
            side, t = o["side"], o["ticker"]
            if o["status"] == "filled":
                return f"Yes. Your {side} order for {o['qty']} {t} filled completely at an average price of ${o['avg_fill_price']:,.2f} (filled {o['last_fill_at']})."
            if o["status"] == "partially_filled":
                remaining = o["qty"] - o["filled_qty"]
                return (
                    f"Partially. Your {o['order_type']} {side} order for {o['qty']} shares of {t} "
                    f"(order {o['order_id']}, limit ${o['limit_price']:,.2f}) has filled {o['filled_qty']} "
                    f"shares at an average price of ${o['avg_fill_price']:,.2f}; the last fill was at "
                    f"{o['last_fill_at']}. The remaining {remaining} shares are still working at the "
                    f"limit; because it's a {o['time_in_force'].upper()} order, any unfilled shares cancel at market close."
                )
            if o["status"] == "pending":
                return f"Your {side} order for {o['qty']} {t} is still pending and hasn't filled yet. {o['note'] or ''}".strip()
            return f"Your {side} order for {o['qty']} {t} was {o['status']}. {o['note'] or ''}".strip()

        if tool_msg.name == "get_transfers":
            transfers = data["transfers"]
            if not transfers:
                return "I don't see any transfers on your account."
            open_ = [t for t in transfers if t["stage"] != "completed"]
            t = open_[0] if open_ else transfers[0]
            if t["stage"] == "completed":
                return f"Your most recent transfer, a {t['type']} {t['direction']} of ${t['amount']:,.2f}, completed on {t['completed_at']}."
            return (
                f"Your {t['type']} {t['direction']} of ${t['amount']:,.2f} (transfer {t['transfer_id']}, "
                f"started {t['initiated_at']}) is still in progress; it's at the "
                f"'{t['stage']}' stage. {t.get('stage_detail', '')} It's expected to complete by "
                f"{t['expected_completion_date']}. If it hasn't arrived by then, I can connect you with a specialist."
            )

        if tool_msg.name == "check_trade_eligibility":
            if data["eligible"]:
                return (
                    f"Nothing is blocking that trade: you could {data['side']} {data['qty']} {data['ticker']} "
                    f"(estimated ${data['estimated_value']:,.2f}). I can't place it for you; please submit it from the trade ticket."
                )
            lines = []
            for r in data["blocking_reasons"]:
                if r["code"] == "insufficient_buying_power":
                    lines.append(
                        f"insufficient buying power: {data['qty']} {data['ticker']} at about ${data['mock_price']:,.2f} "
                        f"is roughly ${data['estimated_value']:,.2f}, but your buying power is ${data['buying_power']:,.2f} "
                        f"(short by ${r['shortfall']:,.2f})"
                    )
                else:
                    lines.append(f"{r['code'].replace('_', ' ')}: {r['detail']}")
            return (
                f"That {data['side']} order for {data['qty']} {data['ticker']} is blocked because of "
                + "; ".join(lines)
                + ". To proceed you could deposit funds or reduce the order size. I can't place or change orders for you."
            )

        return "I've looked that up, but I'm not sure how to summarize it. Let me connect you with a human specialist."


def get_model() -> BaseChatModel:
    """Return the chat model. Swap the fake for a real one here, e.g.:

        from langchain.chat_models import init_chat_model   # pip install langchain langchain-openai
        return init_chat_model("openai:gpt-4o-mini", temperature=0)   # needs OPENAI_API_KEY
    """
    return ScriptedFakeChatModel()


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def build_graph(model: Optional[BaseChatModel] = None):
    llm_with_tools = (model or get_model()).bind_tools(TOOLS)

    def agent(state: SupportState, config: RunnableConfig) -> dict:
        """Agent node: system prompt + conversation -> model reply (text or tool_calls)."""
        account_id = (config.get("configurable") or {}).get("account_id") or state.get("account_id")
        if not account_id:
            return {"messages": [AIMessage(content="I couldn't identify your account. Let me connect you with a human support specialist.")]}
        system = SystemMessage(content=SYSTEM_PROMPT.format(account_id=account_id))
        reply = llm_with_tools.invoke([system, *state["messages"]], config)
        return {"messages": [reply]}

    graph = StateGraph(SupportState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # -> "tools" or END
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_turn(app, question: str, account_id: str, history: Optional[list] = None, verbose: bool = True) -> list:
    """Run one user turn; print node steps, tool calls, tool results, and the answer."""
    messages = list(history or []) + [HumanMessage(content=question)]
    config = {"configurable": {"account_id": account_id}, "recursion_limit": 10}
    final_messages = messages
    for update in app.stream({"messages": messages}, config, stream_mode="updates"):
        for node, delta in update.items():
            for msg in delta.get("messages", []):
                final_messages = final_messages + [msg]
                if not verbose:
                    continue
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"  [{node}] tool call -> {tc['name']}({json.dumps(tc['args'])})")
                elif isinstance(msg, ToolMessage):
                    print(f"  [{node}] {msg.name} result: {msg.content}")
    answer = final_messages[-1]
    print(f"Agent: {answer.content}\n")
    return final_messages


DEMOS = [
    ("ACC-1001", "Did my NVDA trade go through?"),
    ("ACC-1002", "Where is my transfer?"),
    ("ACC-1003", "Why can't I place this trade? I'm trying to buy 20 shares of AAPL."),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Investment brokerage support agent (mock).")
    parser.add_argument("-i", "--interactive", action="store_true", help="start a simple REPL")
    parser.add_argument("--account", default="ACC-1001", help="logged-in account_id for the REPL")
    args = parser.parse_args()

    app = build_graph()
    print("MOCK DEMO: scripted fake chat model + mock read-only tools; no API key, no network.\n")

    if args.interactive:
        print(f"Logged in as {args.account}. Type 'quit' to exit.\n")
        history: list = []
        while True:
            try:
                q = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if q.lower() in {"quit", "exit", "q"}:
                break
            if q:
                history = run_turn(app, q, args.account, history)
        return

    for account_id, question in DEMOS:
        print(f"[{account_id}] User: {question}")
        run_turn(app, question, account_id)


if __name__ == "__main__":
    main()
