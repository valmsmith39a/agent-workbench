"""A LangGraph-style agent loop built from scratch (no LangGraph, no real LLM).

LangGraph models an agent as a graph:
    - STATE: one shared dict that every node reads and updates.
    - NODES: plain functions that take the state and return an update.
    - EDGES: a router that looks at the state and picks the next node.

Our graph has two nodes and one router:

    START -> call_model -> route --(tool calls?)--> call_tools -> call_model ...
                              \\--(no tool calls)--> END

Run it with:  python3 examples/langgraph_style_loop/agent.py
Standard library only. Everything below is mocked: no network, no MCP server.
"""

import json

# ---------------------------------------------------------------------------
# 1. Mock MCP tool
#
# A real MCP server would expose this over a protocol. Here it's one function
# that returns the same kind of JSON payload such a server might send back.
# ---------------------------------------------------------------------------

# Hard-coded mock market data (not real prices).
MARKET_DATA = {
    "AAPL": {"price": 227.50, "forward_pe": 29.0},
    "MSFT": {"price": 431.20, "forward_pe": 32.0},
    "GOOGL": {"price": 165.40, "forward_pe": 21.0},
    "META": {"price": 560.10, "forward_pe": 24.0},
    "NVDA": {"price": 118.90, "forward_pe": 38.0},
    "AMD": {"price": 152.30, "forward_pe": 30.0},
    "INTC": {"price": 22.80, "forward_pe": 25.0},
}

# Peers come from a fixed mapping. The agent never decides who the peers are.
PEERS = {
    "AAPL": ["MSFT", "GOOGL", "META"],
    "MSFT": ["AAPL", "GOOGL", "META"],
    "NVDA": ["AMD", "INTC"],
}


def mcp_get_stock_valuation(ticker: str) -> dict:
    """Simulates an MCP tool call: price, forward P/E, and peer comparison."""
    ticker = ticker.upper()
    if ticker not in MARKET_DATA or ticker not in PEERS:
        return {"error": f"No data for '{ticker}'"}

    stock = MARKET_DATA[ticker]
    peers = PEERS[ticker]
    peer_avg_pe = sum(MARKET_DATA[p]["forward_pe"] for p in peers) / len(peers)
    diff_pct = (stock["forward_pe"] - peer_avg_pe) / peer_avg_pe * 100

    return {
        "ticker": ticker,
        "price": stock["price"],
        "forward_pe": stock["forward_pe"],
        "peers": peers,
        "peer_avg_forward_pe": round(peer_avg_pe, 2),
        "pe_vs_peers_pct": round(diff_pct, 1),
        "pe_vs_peers": "above" if diff_pct > 0 else "below" if diff_pct < 0 else "equal to",
    }


# The tool registry: the model only ever says a tool's NAME.
TOOLS = {"get_stock_valuation": mcp_get_stock_valuation}


# ---------------------------------------------------------------------------
# 2. Mock LLM
#
# A real model would read the messages and decide. This fake one follows a
# fixed script: if no tool result is in the conversation yet, request the
# tool; otherwise, write a final answer from the tool result. Its output has
# the same shape a real chat model's would: text content plus tool_calls.
# ---------------------------------------------------------------------------

def mock_llm(messages: list) -> dict:
    tool_results = [m for m in messages if m["role"] == "tool"]

    if not tool_results:
        question = messages[-1]["content"].upper()
        ticker = next((t for t in PEERS if t in question), None)
        if ticker is None:
            return {"role": "assistant", "content": "Which ticker should I look up? I know AAPL, MSFT, and NVDA.", "tool_calls": []}
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "call_1",
                "name": "get_stock_valuation",
                "arguments": json.dumps({"ticker": ticker}),  # real models send JSON strings
            }],
        }

    data = json.loads(tool_results[-1]["content"])
    if "error" in data:
        return {"role": "assistant", "content": data["error"], "tool_calls": []}
    answer = (
        f"{data['ticker']} trades at ${data['price']:,.2f} with a forward P/E of "
        f"{data['forward_pe']}. Its peers ({', '.join(data['peers'])}) average "
        f"{data['peer_avg_forward_pe']}, so it's {abs(data['pe_vs_peers_pct'])}% "
        f"{data['pe_vs_peers']} the peer average."
    )
    return {"role": "assistant", "content": answer, "tool_calls": []}


# ---------------------------------------------------------------------------
# 3. Nodes: each takes the state dict and returns the keys it changed.
# ---------------------------------------------------------------------------

def call_model(state: dict) -> dict:
    """Model node: send the whole conversation, append the model's reply."""
    reply = mock_llm(state["messages"])
    return {"messages": state["messages"] + [reply]}


def call_tools(state: dict) -> dict:
    """Tool node: parse each requested call, run it, append a tool message."""
    last = state["messages"][-1]
    new_messages = []
    for call in last["tool_calls"]:
        args = json.loads(call["arguments"])           # parse the tool call
        print(f"  [tool] {call['name']}({args})")
        result = TOOLS[call["name"]](**args)           # run it
        new_messages.append({                          # feed the result back
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result),
        })
    return {"messages": state["messages"] + new_messages}


def route(state: dict) -> str:
    """Router (conditional edge): more tools to run, or are we done?"""
    if state["steps"] >= state["max_steps"]:
        return "end"
    return "call_tools" if state["messages"][-1]["tool_calls"] else "end"


# ---------------------------------------------------------------------------
# 4. The graph runner: the loop that LangGraph would run for you.
# ---------------------------------------------------------------------------

def run_graph(question: str, max_steps: int = 5) -> dict:
    state = {"messages": [{"role": "user", "content": question}], "steps": 0, "max_steps": max_steps}
    while True:
        state.update(call_model(state))                # node: call_model
        state["steps"] += 1
        next_node = route(state)                       # edge: router decides
        print(f"  [route] -> {next_node}")
        if next_node == "end":
            return state
        state.update(call_tools(state))                # node: call_tools, then loop


if __name__ == "__main__":
    print("MOCK DEMO: fake LLM and fake MCP tool; no network calls.\n")
    for q in ["How is NVDA valued against its peers?", "Is AAPL expensive?", "Hello!"]:
        print(f"User: {q}")
        final = run_graph(q)
        print(f"Agent: {final['messages'][-1]['content']}\n")
