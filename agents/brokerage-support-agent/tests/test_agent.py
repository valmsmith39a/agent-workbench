"""Run the full agent graph against the real MCP tools, using the offline model."""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.shared.memory import create_connected_server_and_client_session

from app.agent.graph import build_graph, model_facing_schema
from app.agent.mock_llm import MockBrokerageChatModel
from app.mcp.server import mcp

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def tools():
    async with create_connected_server_and_client_session(mcp) as session:
        yield await load_mcp_tools(session)


async def ask(model, tools, question, account_id="ACCT-DEMO-1001"):
    graph = build_graph(model, tools)
    state = await graph.ainvoke({"messages": [HumanMessage(question)], "account_id": account_id})
    return state["messages"]


async def test_nvda_question_calls_get_trade_status_and_answers(tools):
    messages = await ask(MockBrokerageChatModel(), tools, "Did my NVDA trade go through?")
    human, tool_request, tool_result, answer = messages
    assert tool_request.tool_calls[0]["name"] == "get_trade_status"
    assert tool_request.tool_calls[0]["args"] == {"symbol": "NVDA"}
    assert isinstance(tool_result, ToolMessage) and '"FILLED"' in tool_result.text
    assert "118.42" in answer.text


async def test_transfer_question_calls_get_transfer_status_and_answers(tools):
    messages = await ask(MockBrokerageChatModel(), tools, "Where is the $5,000 I transferred from my checking account?")
    human, tool_request, tool_result, answer = messages
    assert tool_request.tool_calls[0]["name"] == "get_transfer_status"
    assert tool_request.tool_calls[0]["args"] == {"amount": 5000.0}
    assert '"PROCESSING"' in tool_result.text
    assert "2026-10-05" in answer.text


async def test_question_without_a_trade_gets_no_tool_call(tools):
    messages = await ask(MockBrokerageChatModel(), tools, "hello")
    assert len(messages) == 2 and not messages[1].tool_calls


async def test_model_never_sees_account_id(tools):
    for tool in tools:
        params = model_facing_schema(tool)["function"]["parameters"]
        assert "account_id" not in params["properties"]
        assert "account_id" not in params["required"]


class AccountSwitchingModel(BaseChatModel):
    """Misbehaves on purpose: asks for a different customer's account."""

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if isinstance(messages[-1], ToolMessage):
            msg = AIMessage(content="done")
        else:
            call = {"name": "get_trade_status", "args": {"account_id": "ACCT-SOMEONE-ELSE"}, "id": "call_1"}
            msg = AIMessage(content="", tool_calls=[call])
        return ChatResult(generations=[ChatGeneration(message=msg)])


async def test_account_id_from_the_model_is_ignored(tools):
    messages = await ask(AccountSwitchingModel(), tools, "show my orders")
    tool_result = messages[2]
    assert '"account_id":"ACCT-DEMO-1001"' in tool_result.text.replace(" ", "")
