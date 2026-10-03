import os

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.agent.graph import model_facing_schema
from app.agent.mock_llm import MockBrokerageChatModel
from app.agent.support_agent import BrokerageSupportAgent

pytestmark = pytest.mark.anyio

CORE_INTENTS = [
    ("Did my NVDA trade go through?", "get_trade_status", "118.42"),
    ("Where is the $5,000 I transferred from my checking account?", "get_transfer_status", "2026-10-05"),
    ("Why can't I place this trade?", "get_account_restrictions", "412.55"),
]


async def test_model_never_sees_account_id(mcp_tools):
    for tool in mcp_tools:
        params = model_facing_schema(tool)["function"]["parameters"]
        assert "account_id" not in params["properties"]
        assert "account_id" not in params.get("required", [])


@pytest.mark.parametrize("question, expected_tool, expected_fact", CORE_INTENTS)
async def test_end_to_end_with_offline_model(mcp_tools, question, expected_tool, expected_fact):
    agent = BrokerageSupportAgent(MockBrokerageChatModel(), mcp_tools)
    reply = await agent.reply(question, account_id="ACCT-DEMO-1001")
    assert [t["tool"] for t in reply.tool_traces] == [expected_tool]
    trace = reply.tool_traces[0]
    assert trace["context"] == {"account_id": "ACCT-DEMO-1001"}
    assert not trace["is_error"] and trace["latency_ms"] >= 0
    assert expected_fact in reply.answer


class ScriptedModel(BaseChatModel):
    """Emits one tool call that tries to read someone else's account, then answers."""

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if messages[-1].type == "tool":
            msg = AIMessage(content="done")
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": "get_trade_status", "args": {"account_id": "ACCT-DEMO-1004"}, "id": "call_1"}],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])


async def test_account_id_from_model_is_ignored(mcp_tools):
    agent = BrokerageSupportAgent(ScriptedModel(), mcp_tools)
    reply = await agent.reply("show my orders", account_id="ACCT-DEMO-1001")
    trace = reply.tool_traces[0]
    assert trace["arguments"] == {}
    assert trace["result"]["account_id"] == "ACCT-DEMO-1001"


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="live LLM routing test needs ANTHROPIC_API_KEY")
@pytest.mark.parametrize("question, expected_tool, expected_fact", CORE_INTENTS)
async def test_live_llm_selects_correct_tool(mcp_tools, question, expected_tool, expected_fact):
    from app.agent.llm import create_chat_model
    from app.config import Settings

    model, _ = create_chat_model(Settings(llm_provider="anthropic"))
    reply = await BrokerageSupportAgent(model, mcp_tools).reply(question, account_id="ACCT-DEMO-1001")
    assert expected_tool in [t["tool"] for t in reply.tool_traces]
    assert reply.answer
