from langchain_core.language_models.chat_models import BaseChatModel

from app.agent.mock_llm import MockBrokerageChatModel
from app.config import Settings


def create_chat_model(settings: Settings) -> tuple[BaseChatModel, str]:
    """Return the chat model and a display name for it."""
    provider = settings.resolved_provider
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=settings.anthropic_model, temperature=0, max_tokens=1024), settings.anthropic_model
    if provider == "mock":
        return MockBrokerageChatModel(), "offline mock (keyword router)"
    raise ValueError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'. Use anthropic, mock or auto.")
