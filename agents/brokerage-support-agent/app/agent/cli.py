"""Ask the agent a question from the command line and watch each step.

Starts the MCP server from step 2 as a subprocess, loads its tools, builds
the graph, and runs one question for a demo customer.

    python -m app.agent.cli "Did my NVDA trade go through?"
"""

import asyncio
import sys

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from app.agent.graph import build_graph
from app.agent.llm import create_chat_model
from app.config import DEMO_ACCOUNT_ID, MCP_SERVERS


async def main(question: str) -> None:
    model, model_name = create_chat_model()
    print(f"Model: {model_name}\nCustomer: {DEMO_ACCOUNT_ID}\n")

    client = MultiServerMCPClient(MCP_SERVERS)
    async with client.session("brokerage") as session:
        tools = await load_mcp_tools(session)
        graph = build_graph(model, tools)
        state = await graph.ainvoke({"messages": [HumanMessage(question)], "account_id": DEMO_ACCOUNT_ID})

    for message in state["messages"]:
        if isinstance(message, HumanMessage):
            print(f"[customer]  {message.text}")
        elif isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                print(f"[agent]     calls tool {call['name']}({call['args']})")
        elif isinstance(message, ToolMessage):
            print(f"[tool]      {message.text}")
        elif isinstance(message, AIMessage):
            print(f"[agent]     {message.text}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Did my NVDA trade go through?"))
