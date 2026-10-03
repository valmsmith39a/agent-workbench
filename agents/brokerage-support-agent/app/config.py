import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    # "anthropic", "mock", or "auto" (anthropic when ANTHROPIC_API_KEY is set, else mock).
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto").lower()
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    has_anthropic_key: bool = bool(os.getenv("ANTHROPIC_API_KEY"))
    default_account_id: str = os.getenv("DEFAULT_ACCOUNT_ID", "ACCT-DEMO-1001")

    @property
    def resolved_provider(self) -> str:
        if self.llm_provider == "auto":
            return "anthropic" if self.has_anthropic_key else "mock"
        return self.llm_provider


settings = Settings()
