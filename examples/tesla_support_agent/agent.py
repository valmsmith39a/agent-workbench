"""Tesla customer support agent: a from-scratch LangGraph-style loop with a SCRIPTED model.

    START -> call_model -> route --(tool calls?)--> call_tools -> call_model ...
                              \\--(final / handoff)--> END

Run:  python3 examples/tesla_support_agent/agent.py            # demo
      python3 examples/tesla_support_agent/agent.py --trace    # show every step
      python3 examples/tesla_support_agent/agent.py -i --customer CUST-1001
Standard library only. No API key, no network, deterministic.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import HANDOFF_KEYWORDS, build_context  # noqa: E402
from tools import CUSTOMERS, TOOLS, search_faq  # noqa: E402

TRACE = False


def trace(msg: str) -> None:
    if TRACE:
        print(f"  [trace] {msg}")


# ---------------------------------------------------------------------------
# Scripted fake model. Reads the last user turn + tool results; returns the
# same shape a chat model would: content + tool_calls. customer_id/VIN come
# from the session snapshot in context, never from the user's text.
# ---------------------------------------------------------------------------

def _session(messages):
    for m in messages:
        if m["role"] == "system" and m["content"].startswith("SESSION CUSTOMER"):
            return json.loads(m["content"].split(": ", 1)[1])
    return {}


def _call(name, **args):
    return {"role": "assistant", "content": "", "tool_calls": [{"id": f"call_{name}", "name": name, "arguments": json.dumps(args)}]}


def _final(text):
    return {"role": "assistant", "content": text, "tool_calls": []}


def scripted_model(messages: list) -> dict:
    sess = _session(messages)
    last_user = max(i for i, m in enumerate(messages) if m["role"] == "user")
    q = messages[last_user]["content"].lower()
    results = {m["name"]: json.loads(m["content"]) for m in messages[last_user:] if m["role"] == "tool"}
    faq = [m["content"] for m in messages if m["role"] == "system" and m["content"].startswith("RETRIEVED FAQ")]
    vin = (sess.get("vins") or [None])[0]

    if any(k in q for k in HANDOFF_KEYWORDS):
        return _final("HANDOFF: I'm connecting you with a Tesla advisor who can help with this directly. "
                      "If anyone is hurt or in danger, contact emergency services first.")

    # Tire scheduling (no DIY). Follow-ups about cost/time/mobile are FAQ questions.
    tire = any(k in q for k in ("tire", "tyre", "flat", "puncture"))
    followup = any(k in q for k in ("cost", "covered", "how long", "mobile service available", "pay"))
    if tire and not followup:
        if not vin:
            return _final("I don't see a vehicle on your account, so I can't request tire service. A Tesla advisor can help.")
        if "schedule_service" not in results:
            d = re.search(r"\d{4}-\d{2}-\d{2}", q)
            return _call("schedule_service", vin=vin, issue="Flat tire / tire replacement",
                         preferred_date=d.group(0) if d else None, mobile="mobile" in q or "home" in q)
        a = results["schedule_service"]
        return _final(f"Tesla Service will handle the tire for you, so please don't try to change it yourself. "
                      f"Proposed appointment (not booked yet): {a['slot']} at {a['location']}, VIN {a['vin']}, "
                      f"issue: {a['issue']}. Please confirm it in the Tesla app.")

    if any(k in q for k in ("order", "delivery", "eta", "arrive")):
        if "lookup_order" not in results:
            return _call("lookup_order", customer_id=sess["customer_id"])
        o = results["lookup_order"]["orders"][0]
        return _final(f"Order {o['order_id']} ({o['model']}): {o['status']}, ETA {o['eta']} at {o['delivery_center']}.")

    if any(k in q for k in ("software", "version", "my car", "my vehicle", "warranty expire")):
        if not vin:
            return _final("I don't see a delivered vehicle on your account yet.")
        if "get_vehicle_info" not in results:
            return _call("get_vehicle_info", vin=vin)
        v = results["get_vehicle_info"]
        return _final(f"Your {v['year']} {v['model']} (VIN {v['vin']}) runs software {v['software_version']}. "
                      f"Basic warranty: {v['warranty']['basic']}, expires {v['warranty']['basic_expires']}.")

    if any(k in q for k in ("service", "appointment", "repair")):
        if "schedule_service" not in results:
            return _call("schedule_service", vin=vin, issue=messages[last_user]["content"])
        a = results["schedule_service"]
        return _final(f"Proposed appointment (not booked yet): {a['slot']} at {a['location']} for VIN {a['vin']}.")

    if faq:
        body = faq[0].split("\n", 1)[1]
        return _final("From our FAQ: " + " ".join(re.sub(r"^\[[^\]]+\] ", "", line) for line in body.splitlines()))
    return _final("I can help with orders, your vehicle, service appointments, and FAQ topics. What do you need?")


# ---------------------------------------------------------------------------
# Nodes, router, runner.
# ---------------------------------------------------------------------------

def call_model(state):
    reply = scripted_model(state["messages"])
    if reply["tool_calls"]:
        trace(f"model -> tool_call {reply['tool_calls'][0]['name']}")
    else:
        trace("model -> final answer")
    return {"messages": state["messages"] + [reply]}


def call_tools(state):
    out = []
    for c in state["messages"][-1]["tool_calls"]:
        args = json.loads(c["arguments"])
        result = TOOLS[c["name"]](**args)
        state["tool_calls"] += 1
        trace(f"tool {c['name']}({args})")
        trace(f"result {json.dumps(result)[:160]}")
        out.append({"role": "tool", "name": c["name"], "tool_call_id": c["id"], "content": json.dumps(result)})
    return {"messages": state["messages"] + out}


def route(state):
    if state["steps"] >= state["max_steps"]:
        return "end"
    return "call_tools" if state["messages"][-1]["tool_calls"] else "end"


def run_graph(question, customer_id, history=None, max_steps=6):
    customer = CUSTOMERS[customer_id]  # identity comes from the session, not the model
    hits = search_faq(question)["results"]
    trace(f"retrieved FAQ: {[h['id'] for h in hits]}")
    history = (history or []) + [{"role": "user", "content": question}]
    state = {"messages": build_context(customer_id, customer, hits, history), "steps": 0, "tool_calls": 0, "max_steps": max_steps}
    while True:
        state.update(call_model(state))
        state["steps"] += 1
        nxt = route(state)
        trace(f"route -> {nxt}")
        if nxt == "end":
            return state
        state.update(call_tools(state))


DEMO = [
    ("CUST-1003", "Where is my order? When will it arrive?"),
    ("CUST-1001", "What software version is my car on and when does the warranty expire?"),
    ("CUST-1002", "I have a flat tire, can I get mobile service on 2026-10-27?"),
    ("CUST-1002", "Is the tire cost covered and how long does it take?"),
    ("CUST-1001", "How should I set my charging limit at home?"),
    ("CUST-1001", "Is FSD fully self driving?"),
    ("CUST-1002", "I was in an accident, what do I do?"),
]


def main():
    global TRACE
    ap = argparse.ArgumentParser(description="Mock Tesla support agent")
    ap.add_argument("-i", "--interactive", action="store_true")
    ap.add_argument("--customer", default="CUST-1001", choices=sorted(CUSTOMERS))
    ap.add_argument("--trace", action="store_true")
    a = ap.parse_args()
    TRACE = a.trace
    print("MOCK DEMO: scripted model and fake Tesla data; no network calls.\n")
    if a.interactive:
        hist = []
        print(f"Session customer: {a.customer} ({CUSTOMERS[a.customer]['name']}). Ctrl-D to quit.")
        for line in sys.stdin:
            if not line.strip():
                continue
            s = run_graph(line.strip(), a.customer, hist)
            ans = s["messages"][-1]["content"]
            hist += [{"role": "user", "content": line.strip()}, {"role": "assistant", "content": ans}]
            print(f"Agent: {ans}\n")
        return
    total_steps = total_tools = 0
    for cid, q in DEMO:
        print(f"[{cid}] User: {q}")
        s = run_graph(q, cid)
        total_steps += s["steps"]
        total_tools += s["tool_calls"]
        print(f"Agent: {s['messages'][-1]['content']}\n")
    print(f"SUMMARY: questions={len(DEMO)} steps={total_steps} tool_calls={total_tools}")


if __name__ == "__main__":
    main()
