import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import Settings


@pytest.fixture
def client(monkeypatch):
    # Offline model; the MCP server still runs as a real stdio subprocess.
    monkeypatch.setattr(main, "settings", Settings(llm_provider="mock"))
    with TestClient(main.app) as c:
        yield c


def test_chat_trade_status_end_to_end(client):
    res = client.post("/api/chat", json={"message": "Did my NVDA trade go through?", "account_id": "ACCT-DEMO-1001"})
    assert res.status_code == 200
    body = res.json()
    assert body["tool_calls"][0]["tool"] == "get_trade_status"
    assert body["tool_calls"][0]["result"]["orders"][0]["status"] == "FILLED"
    assert "ORD-7F3K-1001" in body["answer"]


def test_config_and_unknown_account(client):
    assert len(client.get("/api/config").json()["demo_accounts"]) == 4
    res = client.post("/api/chat", json={"message": "hi", "account_id": "ACCT-OTHER-0001"})
    assert res.status_code == 403
