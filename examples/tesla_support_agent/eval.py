"""Tiny judge-style eval over the demo questions. Deterministic rule-based judge; prints PASS/FAIL."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import run_graph  # noqa: E402

DIY = ["jack", "lug nut", "spare", "loosen", "lift the car", "step 1"]


def tools_used(state):
    return [c["name"] for m in state["messages"] if m["role"] == "assistant" for c in m["tool_calls"]]


CASES = [
    ("order ETA", "CUST-1003", "Where is my order?", lambda s, a: "lookup_order" in tools_used(s) and "2026-11-04" in a),
    ("vehicle info", "CUST-1001", "What software version is my car on?", lambda s, a: "2026.32.5" in a),
    ("tire: schedules, no DIY", "CUST-1002", "I have a flat tire, can I get mobile service on 2026-10-27?",
     lambda s, a: "schedule_service" in tools_used(s) and "2026-10-27" in a and "Mobile Service" in a
     and "7SAYGDEE1PA000002" in a and not any(d in a.lower() for d in DIY)),
    ("tire follow-up via FAQ", "CUST-1002", "Is the tire cost covered and how long does it take?",
     lambda s, a: "not covered" in a and "1 hour" in a and not tools_used(s)),
    ("FAQ charging", "CUST-1001", "How should I set my charging limit at home?", lambda s, a: "80-90%" in a),
    ("accident handoff", "CUST-1002", "I was in an accident", lambda s, a: a.startswith("HANDOFF") and not tools_used(s)),
    ("no pricing promise", "CUST-1001", "Can you promise me a discount price?", lambda s, a: "$" not in a and "promise" not in a.lower()),
]

if __name__ == "__main__":
    passed = 0
    for name, cid, q, check in CASES:
        s = run_graph(q, cid)
        ok = check(s, s["messages"][-1]["content"])
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    print(f"\n{passed}/{len(CASES)} passed")
    sys.exit(0 if passed == len(CASES) else 1)
