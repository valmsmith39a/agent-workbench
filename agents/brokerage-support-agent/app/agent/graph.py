"""The single-agent LangGraph flow.

    START -> agent --(tool calls?)--> tools -> agent -> ... -> END
                   \\--(final answer)--------------------------> END

The model sees the brokerage tools *without* their account_id parameter. The
tools node fills account_id in from graph state, which the API sets from the
signed-in session, so the model cannot choose (or be talked into choosing)
whose account it reads.
"""

import copy
import json
import operator
import time
from typing import Annotated, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph

from app.agent.prompts import SYSTEM_PROMPT

CONTEXT_ARGS = ("account_id",)  # supplied by the application, never by the model
MAX_GRAPH_STEPS = 8


class AgentState(MessagesState):
    account_id: str
    tool_traces: Annotated[list[dict[str, Any]], operator.add]


def model_facing_schema(tool: BaseTool) -> dict[str, Any]:
    """The tool's schema in OpenAI function format, minus application-supplied args."""
    schema = tool.args_schema if isinstance(tool.args_schema, dict) else tool.args_schema.model_json_schema()
    schema = copy.deepcopy(schema)
    for arg in CONTEXT_ARGS:
        schema.get("properties", {}).pop(arg, None)
        if arg in schema.get("required", []):
            schema["required"].remove(arg)
    return {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": schema}}


def _structured_result(message: ToolMessage) -> dict[str, Any]:
    artifact = message.artifact or {}
    if isinstance(artifact, dict) and artifact.get("structured_content") is not None:
        return artifact["structured_content"]
    try:
        return json.loads(message.text)
    except (json.JSONDecodeError, TypeError):
        return {"raw": message.text}


def build_graph(model: BaseChatModel, tools: list[BaseTool]):
    tools_by_name = {t.name: t for t in tools}
    model_with_tools = model.bind_tools([model_facing_schema(t) for t in tools])

    async def agent(state: AgentState) -> dict[str, Any]:
        response = await model_with_tools.ainvoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    async def call_tools(state: AgentState) -> dict[str, Any]:
        last: AIMessage = state["messages"][-1]
        messages: list[BaseMessage] = []
        traces: list[dict[str, Any]] = []
        for call in last.tool_calls:
            model_args = {k: v for k, v in call["args"].items() if k not in CONTEXT_ARGS}
            args = {**model_args, "account_id": state["account_id"]}
            tool = tools_by_name.get(call["name"])
            start = time.perf_counter()
            if tool is None:
                result = {"error": {"code": "UNKNOWN_TOOL", "message": f"No tool named {call['name']}."}}
                message = ToolMessage(json.dumps(result), tool_call_id=call["id"], name=call["name"])
            else:
                try:
                    message = await tool.ainvoke({**call, "args": args})
                    result = _structured_result(message)
                except Exception as exc:  # surface tool failures to the model instead of crashing the turn
                    result = {"error": {"code": "TOOL_FAILURE", "message": str(exc)}}
                    message = ToolMessage(json.dumps(result), tool_call_id=call["id"], name=call["name"])
            latency_ms = round((time.perf_counter() - start) * 1000, 1)
            messages.append(message)
            traces.append(
                {
                    "tool": call["name"],
                    "arguments": model_args,
                    "context": {"account_id": state["account_id"]},
                    "result": result,
                    "latency_ms": latency_ms,
                    "is_error": "error" in result,
                }
            )
        return {"messages": messages, "tool_traces": traces}

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
