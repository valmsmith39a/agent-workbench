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
    [trace] = body["tool_calls"]
    assert trace["name"] == "get_trade_status"
    assert trace["args"] == {"symbol": "NVDA"}
    assert trace["injected"] == {"account_id": "ACCT-DEMO-1001"}
    assert trace["result"]["orders"][0]["status"] == "FILLED"
    assert trace["latency_ms"] >= 0 and body["total_latency_ms"] >= trace["latency_ms"]
    assert "118.42" in body["answer"]


def test_chat_answers_transfer_question(client):
    res = client.post("/api/chat", json={"message": "Where is my $5,000 transfer?"})
    body = res.json()
    assert [(t["name"], t["args"]) for t in body["tool_calls"]] == [("get_transfer_status", {"amount": 5000.0})]
    assert "processing" in body["answer"]


def test_chat_answers_restriction_question(client):
    res = client.post("/api/chat", json={"message": "Why can't I place this trade?"})
    body = res.json()
    assert [(t["name"], t["args"]) for t in body["tool_calls"]] == [("get_account_restrictions", {})]
    assert "412.55" in body["answer"]


def test_no_tool_call_means_empty_trace(client):
    body = client.post("/api/chat", json={"message": "hello"}).json()
    assert body["tool_calls"] == []


def test_empty_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_chat_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Brokerage Customer Support Agent" in res.text
