"""The agent, as a LangGraph graph with two nodes.

    START -> agent --(model asked for a tool)--> tools -> agent -> ... -> END
                   \\--(model gave an answer)-------------------------> END

- agent node: sends the conversation (plus the tool descriptions) to the model.
- tools node: runs the tool calls the model asked for and adds the results to
  the conversation, then hands control back to the agent node so the model can
  write the final answer from those results.

The tools node also records a trace of each call (arguments, injected
account, structured result, latency) so the UI can show what happened.

The model is shown the tools *without* their account_id parameter. The tools
node fills account_id in from the graph state, which the caller sets for the
signed-in customer. So the model can never choose whose account is read.
"""

import copy
import json
import operator
import time
from typing import Annotated, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph

from app.agent.prompts import SYSTEM_PROMPT


class AgentState(MessagesState):
    """The conversation (from MessagesState), the signed-in customer's account,
    and a trace of every tool call made during the run."""

    account_id: str
    tool_traces: Annotated[list[dict[str, Any]], operator.add]  # each node's traces are appended


def _structured_result(message: ToolMessage) -> dict[str, Any]:
    """The tool's JSON result. MCP tools put it in the message artifact; fall back to the text."""
    artifact = message.artifact or {}
    if isinstance(artifact, dict) and artifact.get("structured_content") is not None:
        return artifact["structured_content"]
    try:
        return json.loads(message.text)
    except (json.JSONDecodeError, TypeError):
        return {"raw": message.text}


def model_facing_schema(tool: BaseTool) -> dict[str, Any]:
    """The tool's definition as the model sees it: same name and description, no account_id."""
    schema = copy.deepcopy(tool.args_schema)  # MCP tools carry their JSON schema as a dict
    schema["properties"].pop("account_id", None)
    schema["required"] = [p for p in schema.get("required", []) if p != "account_id"]
    return {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": schema}}


def build_graph(model: BaseChatModel, tools: list[BaseTool]):
    tools_by_name = {t.name: t for t in tools}
    model_with_tools = model.bind_tools([model_facing_schema(t) for t in tools])

    async def agent(state: AgentState) -> dict[str, Any]:
        response = await model_with_tools.ainvoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    async def call_tools(state: AgentState) -> dict[str, Any]:
        results, traces = [], []
        for call in state["messages"][-1].tool_calls:
            # Drop any account_id the model tried to pass; use the session's.
            model_args = {k: v for k, v in call["args"].items() if k != "account_id"}
            args = {**model_args, "account_id": state["account_id"]}
            tool = tools_by_name.get(call["name"])
            start = time.perf_counter()
            if tool is None:
                error = {"error": {"code": "UNKNOWN_TOOL", "message": f"No tool named {call['name']}."}}
                message = ToolMessage(json.dumps(error), tool_call_id=call["id"], name=call["name"])
            else:
                # Invoking with the full tool call returns a ToolMessage linked to the call's id.
                message = await tool.ainvoke({**call, "args": args})
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            results.append(message)
            traces.append(
                {
                    "name": call["name"],
                    "args": model_args,
                    "injected": {"account_id": state["account_id"]},
                    "result": _structured_result(message),
                    "latency_ms": latency_ms,
                }
            )
        return {"messages": results, "tool_traces": traces}

    def route(state: AgentState) -> str:
        last = state["messages"][-1]
        return "tools" if isinstance(last, AIMessage) and last.tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route, ["tools", END])
    graph.add_edge("tools", "agent")
    return graph.compile()
