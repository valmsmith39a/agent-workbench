"""Coffee shop support agent: a plain call_model -> route -> call_tools loop.

    START -> call_model -> route --(tool calls?)--> call_tools -> call_model ...
                              \\--(final)--> END

Tools come from the MCP server (mcp-server/server.py over stdio); --local uses
direct import instead. The model is scripted (mock_model.py): no API key.

    python agent/agent.py                    # demo
    python agent/agent.py --trace            # print each step
    python agent/agent.py -i --customer CUST-202
"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mock_model import scripted_model  # noqa: E402
from prompts import CUSTOMERS, build_context  # noqa: E402
from toolbox import open_toolbox  # noqa: E402


async def run_graph(question, customer_id, toolbox, history=None, max_steps=6):
    """Returns state with messages, steps, tool_calls, and a structured trace."""
    hist = (history or []) + [{"role": "user", "content": question}]
    state = {"messages": build_context(customer_id, CUSTOMERS[customer_id], hist),
             "steps": 0, "tool_calls": 0, "trace": []}
    while True:
        reply = scripted_model(state["messages"])                  # node: call_model
        state["messages"].append(reply)
        state["steps"] += 1
        state["trace"].append({"node": "call_model", "decision": [c["name"] for c in reply["tool_calls"]] or "final"})
        nxt = "end" if state["steps"] >= max_steps or not reply["tool_calls"] else "call_tools"   # router
        state["trace"].append({"node": "route", "next": nxt})
        if nxt == "end":
            state["answer"] = reply["content"]
            return state
        for c in reply["tool_calls"]:                              # node: call_tools
            args = json.loads(c["arguments"])
            result = await toolbox.call(c["name"], args)
            state["tool_calls"] += 1
            state["trace"].append({"node": "call_tools", "tool": c["name"], "args": args, "result": result})
            state["messages"].append({"role": "tool", "name": c["name"], "tool_call_id": c["id"], "content": json.dumps(result)})


def print_trace(state):
    for t in state["trace"]:
        if t["node"] == "call_model":
            print(f"  [trace] model -> {t['decision']}")
        elif t["node"] == "route":
            print(f"  [trace] route -> {t['next']}")
        else:
            print(f"  [trace] tool {t['tool']}({t['args']})")
            print(f"  [trace] result {json.dumps(t['result'])[:160]}")


DEMO = [
    ("CUST-201", "What desserts do you have?"),
    ("CUST-202", "What sizes and allergens does the mocha have?"),
    ("CUST-203", "What are your hours and where are you located?"),
    ("CUST-201", "I'd like to order 2 large lattes with oat milk and a tiramisu for 08:30"),
    ("CUST-202", "Can I order a medium matcha?"),
    ("CUST-202", "What's the status of ORD-0900?"),
    ("CUST-202", "Please change ORD-0900 to a large americano at 09:00"),
    ("CUST-202", "Cancel ORD-0900"),
    ("CUST-201", "How many loyalty points do I have?"),
    ("CUST-201", "What rewards can I redeem?"),
    ("CUST-203", "I want to complain, my drink was wrong and the barista was rude"),
]


async def amain(a):
    async with open_toolbox(prefer_mcp=not a.local) as tb:
        print(f"MOCK DEMO: scripted model, tools via {tb.kind} ({', '.join(tb.names)}); no network calls.\n")
        if a.interactive:
            hist = []
            print(f"Session customer: {a.customer} ({CUSTOMERS[a.customer]['name']}). Ctrl-D to quit.")
            for line in sys.stdin:
                if line.strip():
                    s = await run_graph(line.strip(), a.customer, tb, hist)
                    if a.trace:
                        print_trace(s)
                    hist += [{"role": "user", "content": line.strip()}, {"role": "assistant", "content": s["answer"]}]
                    print(f"Agent: {s['answer']}\n")
            return
        steps = tools = 0
        for cid, q in DEMO:
            print(f"[{cid}] User: {q}")
            s = await run_graph(q, cid, tb)
            if a.trace:
                print_trace(s)
            steps += s["steps"]
            tools += s["tool_calls"]
            print(f"Agent: {s['answer']}\n")
        print(f"SUMMARY: questions={len(DEMO)} steps={steps} tool_calls={tools}")


def main():
    ap = argparse.ArgumentParser(description="Mock coffee shop support agent")
    ap.add_argument("-i", "--interactive", action="store_true")
    ap.add_argument("--customer", default="CUST-201", choices=sorted(CUSTOMERS))
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--local", action="store_true", help="import tools directly instead of MCP")
    asyncio.run(amain(ap.parse_args()))


if __name__ == "__main__":
    main()
