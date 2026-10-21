from fastapi.testclient import TestClient

from api import app


def test_chat_endpoint_over_mcp():
    with TestClient(app) as c:
        r = c.post("/chat", json={"message": "What desserts do you have?", "customer_id": "CUST-201"})
        assert r.status_code == 200
        j = r.json()
        assert "tiramisu" in j["answer"] and j["tool_source"] == "mcp" and j["tool_calls"] == 1
        assert any(t["node"] == "call_tools" for t in j["trace"])
        assert c.post("/chat", json={"message": "hi", "customer_id": "CUST-999"}).status_code == 404
        assert c.get("/").status_code == 200
