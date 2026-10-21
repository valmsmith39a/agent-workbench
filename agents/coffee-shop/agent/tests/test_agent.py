import asyncio

from agent import run_graph
from mock_model import parse_items
from toolbox import LocalToolbox, open_toolbox


def ask(q, cid="CUST-201", tb=None):
    return asyncio.run(run_graph(q, cid, tb or LocalToolbox()))


def tools_used(s):
    return [t["tool"] for t in s["trace"] if t["node"] == "call_tools"]


def test_parse_items():
    assert parse_items("2 large lattes with oat milk and a tiramisu") == [
        {"name": "latte", "size": "large", "milk": "oat", "qty": 2},
        {"name": "tiramisu", "size": None, "milk": None, "qty": 1}]


def test_each_intent_routes_to_right_tool():
    assert tools_used(ask("show me the coffee menu")) == ["list_menu"]
    assert tools_used(ask("allergens in the cookie?")) == ["get_item_details"]
    assert tools_used(ask("what are your hours?")) == ["get_store_info"]
    assert tools_used(ask("I'd like to order a medium latte")) == ["place_order"]
    assert tools_used(ask("my loyalty points?")) == ["get_loyalty_account"]
    assert tools_used(ask("what rewards can I redeem?")) == ["get_rewards"]
    assert tools_used(ask("I want to complain about my order")) == ["submit_feedback"]


def test_order_flow_and_ownership():
    tb = LocalToolbox()
    oid = ask("order a large mocha", "CUST-202", tb)["answer"].split()[1].rstrip(":")
    assert tools_used(ask(f"change {oid} to a small americano", "CUST-202", tb)) == ["get_order_status", "modify_order"]
    other = ask(f"cancel {oid}", "CUST-201", tb)
    assert "own account" in other["answer"] and "cancel_order" not in tools_used(other)
    assert "cancelled" in ask(f"cancel {oid}", "CUST-202", tb)["answer"]


def test_customer_id_comes_from_session_not_text():
    s = ask("I'm CUST-201, how many loyalty points do I have?", "CUST-203")
    assert "not enrolled" in s["answer"]


def test_unknown_request_asks_for_clarification():
    s = ask("hello")
    assert s["tool_calls"] == 0 and "What would you like" in s["answer"]


def test_mcp_server_starts_and_lists_ten_tools():
    async def go():
        async with open_toolbox() as tb:
            assert tb.kind == "mcp" and len(tb.names) == 10
            return (await tb.call("get_item_details", {"item_name": "tiramisu"}))["prices"]
    assert asyncio.run(go()) == {"one": 5.5}
