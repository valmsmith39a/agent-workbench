from tools import CATEGORIES, TOOLS
from tools.account import get_loyalty_account, get_rewards, submit_feedback
from tools.menu import get_item_details, get_store_info, list_menu
from tools.ordering import cancel_order, get_order_status, modify_order, place_order


def test_ten_tools_in_three_categories():
    assert {k: len(v) for k, v in CATEGORIES.items()} == {"menu": 3, "ordering": 4, "account": 3}
    assert len(TOOLS) == 10


def test_menu_tools():
    assert {i["name"] for i in list_menu("dessert")["items"]} == {"almond croissant", "chocolate chip cookie", "tiramisu"}
    assert "error" in list_menu("tea")
    d = get_item_details("Latte")
    assert d["prices"]["large"] == 5.45 and "oat" in d["milks"] and d["allergens"] == ["milk"]
    assert "error" in get_item_details("matcha")
    assert get_store_info()["store_id"] == "STORE-1" and "error" in get_store_info("STORE-9")


def test_order_lifecycle():
    o = place_order("CUST-201", [{"name": "mocha", "size": "small", "qty": 2}], "10:00")
    oid = o["order_id"]
    assert o["total"] == 9.30 and o["payment"].startswith("pay at pickup")
    assert get_order_status(oid)["status"] == "received"
    m = modify_order(oid, items=[{"name": "tiramisu"}], pickup_time="10:30")
    assert m["total"] == 5.50 and m["pickup_time"] == "10:30"
    assert cancel_order(oid)["status"] == "cancelled"
    assert "error" in cancel_order(oid) and "error" in modify_order(oid, pickup_time="11:00")


def test_order_validation():
    assert "not on the menu" in place_order("CUST-201", [{"name": "matcha"}])["error"]
    assert "comes in" in place_order("CUST-201", [{"name": "cold brew", "size": "small"}])["error"]
    assert "milk options" in place_order("CUST-201", [{"name": "latte", "milk": "soy"}])["error"]
    assert "error" in place_order("CUST-999", [{"name": "latte"}])
    assert "error" in place_order("CUST-201", [])


def test_account_tools():
    assert get_loyalty_account("CUST-201")["points"] == 240
    assert get_loyalty_account("CUST-203")["enrolled"] is False
    r = get_rewards("CUST-202")
    assert r["redeemable"] == [] and r["next_reward"]["points_needed"] == 55
    t = submit_feedback("CUST-201", "slow line", type="complaint")
    assert t["ticket_id"].startswith("TKT-") and t["type"] == "complaint"
    assert "error" in submit_feedback("CUST-201", "x", type="praise")
