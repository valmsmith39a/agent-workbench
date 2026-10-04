import os

from langchain_core.language_models.chat_models import BaseChatModel

from app.agent.mock_llm import MockBrokerageChatModel

DEFAULT_MODEL = "claude-sonnet-5-5"


def create_chat_model() -> tuple[BaseChatModel, str]:
    """Claude if ANTHROPIC_API_KEY is set, otherwise the offline stand-in.

    Returns the model and a name to display for it.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic

        model_name = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
        return ChatAnthropic(model=model_name, temperature=0, max_tokens=1024), model_name
    return MockBrokerageChatModel(), "offline stand-in (keyword router, not an LLM)"
