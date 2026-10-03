from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool

from app.agent.graph import MAX_GRAPH_STEPS, build_graph


@dataclass
class AgentReply:
    answer: str
    tool_traces: list[dict[str, Any]]


class BrokerageSupportAgent:
    def __init__(self, model: BaseChatModel, tools: list[BaseTool]):
        self.graph = build_graph(model, tools)

    async def reply(self, message: str, account_id: str, history: list[dict[str, str]] | None = None) -> AgentReply:
        messages = [
            HumanMessage(turn["content"]) if turn["role"] == "user" else AIMessage(turn["content"])
            for turn in history or []
        ]
        messages.append(HumanMessage(message))
        state = await self.graph.ainvoke(
            {"messages": messages, "account_id": account_id, "tool_traces": []},
            config={"recursion_limit": MAX_GRAPH_STEPS},
        )
        return AgentReply(answer=state["messages"][-1].text, tool_traces=state["tool_traces"])
