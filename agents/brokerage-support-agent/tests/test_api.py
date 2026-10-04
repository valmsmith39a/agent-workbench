"""Call the HTTP API end to end: FastAPI -> agent -> MCP server subprocess -> service."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # always use the offline stand-in here
    with TestClient(app) as c:  # "with" runs startup: launches the MCP server
        yield c


def test_chat_answers_trade_status_question(client):
    res = client.post("/api/chat", json={"message": "Did my NVDA trade go through?"})
    assert res.status_code == 200
    body = res.json()
    assert body["tool_calls"] == [{"name": "get_trade_status", "args": {"symbol": "NVDA"}}]
    assert "118.42" in body["answer"]


def test_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_chat_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Brokerage Customer Support Agent" in res.text
