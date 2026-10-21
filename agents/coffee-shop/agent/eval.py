"""Judge-style eval over the MCP tools: deterministic rule checks per category. Prints PASS/FAIL.

Cases run in order against one MCP server session (in-memory state carries over),
so the status -> modify -> cancel flow is exercised end to end.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import run_graph  # noqa: E402
from toolbox import open_toolbox  # noqa: E402


def used(s):
    return [t["tool"] for t in s["trace"] if t["node"] == "call_tools"]


CASES = [
    # MENU
    ("menu: list desserts", "CUST-201", "What desserts do you have?",
     lambda s, a: used(s) == ["list_menu"] and "tiramisu" in a and "latte" not in a),
    ("menu: item details", "CUST-202", "What sizes and allergens does the mocha have?",
     lambda s, a: used(s) == ["get_item_details"] and "$5.75" in a and "soy" in a and "staff" in a),
    ("menu: dessert allergens", "CUST-203", "Does the almond croissant have nuts?", lambda s, a: "tree nuts" in a),
    ("menu: hours/location", "CUST-203", "When do you open and where are you?",
     lambda s, a: used(s) == ["get_store_info"] and "123 Main St" in a and "Sun 8:00-16:00" in a),
    # ORDERING
    ("order: multi-item", "CUST-201", "I'd like to order 2 large lattes with oat milk and a tiramisu",
     lambda s, a: used(s) == ["place_order"] and "ORD-" in a and "$16.40" in a and "pay at pickup" in a and "card" not in a.lower()),
    ("order: not on menu", "CUST-202", "Can I order a medium matcha?", lambda s, a: "not on the menu" in a and "ORD-1" not in a),
    ("order: invalid size", "CUST-202", "I want to order a small cold brew", lambda s, a: "comes in medium, large" in a),
    ("order: status", "CUST-202", "What's the status of ORD-0900?",
     lambda s, a: used(s) == ["get_order_status"] and "preparing" in a),
    ("order: modify", "CUST-202", "Please change ORD-0900 to a large americano at 09:00",
     lambda s, a: used(s) == ["get_order_status", "modify_order"] and "large americano" in a and "09:00" in a and "$4.25" in a),
    ("order: cancel", "CUST-202", "Cancel ORD-0900", lambda s, a: "cancel_order" in used(s) and "cancelled" in a),
    ("order: cancel twice refused", "CUST-202", "Cancel ORD-0900", lambda s, a: "couldn't cancel" in a),
    ("order: other customer's order", "CUST-203", "Cancel ORD-0900",
     lambda s, a: "cancel_order" not in used(s) and "your own account" in a),
    # ACCOUNT
    ("account: loyalty", "CUST-201", "How many loyalty points do I have?",
     lambda s, a: used(s) == ["get_loyalty_account"] and "Gold" in a and "240 points" in a),
    ("account: rewards", "CUST-201", "What rewards can I redeem?",
     lambda s, a: used(s) == ["get_rewards"] and "Free drink (any size)" in a and "60 points" in a),
    ("account: not enrolled", "CUST-203", "Check my rewards", lambda s, a: "not enrolled" in a),
    ("account: complaint", "CUST-203", "I want to complain, my drink was wrong",
     lambda s, a: used(s) == ["submit_feedback"] and "sorry" in a.lower() and "TKT-" in a and "manager" in a),
    ("account: feedback", "CUST-201", "Some feedback: I loved the new tiramisu",
     lambda s, a: used(s) == ["submit_feedback"] and "Thank you" in a and "TKT-" in a),
]


async def main():
    passed = 0
    async with open_toolbox() as tb:
        print(f"tools via {tb.kind}")
        for name, cid, q, check in CASES:
            s = await run_graph(q, cid, tb)
            ok = bool(check(s, s["answer"]))
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {s['answer']} {used(s)}"))
    print(f"\n{passed}/{len(CASES)} passed")
    return passed == len(CASES)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
