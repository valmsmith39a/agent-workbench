"""The agent, as a LangGraph graph with two nodes.

    START -> agent --(model asked for a tool)--> tools -> agent -> ... -> END
                   \\--(model gave an answer)-------------------------> END

- agent node: sends the conversation (plus the tool descriptions) to the model.
- tools node: runs the tool calls the model asked for and adds the results to
  the conversation, then hands control back to the agent node so the model can
  write the final answer from those results.

The model is shown the tools *without* their account_id parameter. The tools
node fills account_id in from the graph state, which the caller sets for the
signed-in customer. So the model can never choose whose account is read.
"""

import copy
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph

from app.agent.prompts import SYSTEM_PROMPT


class AgentState(MessagesState):
    """The conversation (from MessagesState) plus the signed-in customer's account."""

    account_id: str


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
        results = []
        for call in state["messages"][-1].tool_calls:
            # Drop any account_id the model tried to pass; use the session's.
            args = {k: v for k, v in call["args"].items() if k != "account_id"}
            args["account_id"] = state["account_id"]
            tool = tools_by_name.get(call["name"])
            if tool is None:
                error = {"error": {"code": "UNKNOWN_TOOL", "message": f"No tool named {call['name']}."}}
                results.append(ToolMessage(json.dumps(error), tool_call_id=call["id"], name=call["name"]))
                continue
            # Invoking with the full tool call returns a ToolMessage linked to the call's id.
            results.append(await tool.ainvoke({**call, "args": args}))
        return {"messages": results}

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
