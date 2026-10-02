"""A minimal agent harness for a finance agent, using a mock LLM.

An agent harness is just a loop:

    1. Send the conversation so far to the model.
    2. If the model asks to use a tool, run the tool, add the result to the
       conversation, and go back to step 1.
    3. If the model gives a final answer, stop and return it.

Everything below is one of three pieces: tools, the (mock) model, and the loop.
Run it with:  python examples/finance_agent/agent.py
"""

# ---------------------------------------------------------------------------
# 1. Tools: plain Python functions the model is allowed to call.
# ---------------------------------------------------------------------------

ACCOUNTS = {"checking": 2450.75, "savings": 10200.00}
STOCK_PRICES = {"AAPL": 227.50, "MSFT": 431.20, "NVDA": 118.90}


def get_balance(account: str) -> str:
    if account not in ACCOUNTS:
        return f"Error: no account named '{account}'"
    return f"${ACCOUNTS[account]:,.2f}"


def get_stock_price(ticker: str) -> str:
    if ticker not in STOCK_PRICES:
        return f"Error: no price for '{ticker}'"
    return f"${STOCK_PRICES[ticker]:,.2f}"


# The harness looks tools up by name, because the model only ever says a name.
TOOLS = {
    "get_balance": get_balance,
    "get_stock_price": get_stock_price,
}


# ---------------------------------------------------------------------------
# 2. The model: a fake LLM that returns canned responses.
#
# A real LLM would read the messages and decide what to do. This mock fakes
# that decision with a few if-statements. Its return value has the same shape
# a real model's would, so you could later swap in a real API call without
# touching the loop.
#
#   Ask for a tool:   {"type": "tool_call", "tool": "<name>", "args": {...}}
#   Final answer:     {"type": "answer", "text": "..."}
# ---------------------------------------------------------------------------


def mock_llm(messages: list[dict]) -> dict:
    last = messages[-1]

    # If we just got a tool result back, turn it into a final answer.
    if last["role"] == "tool":
        return {"type": "answer", "text": f"The result is {last['content']}."}

    # Otherwise, look at the user's question and pick a tool.
    question = last["content"].lower()
    if "balance" in question:
        account = "savings" if "savings" in question else "checking"
        return {"type": "tool_call", "tool": "get_balance", "args": {"account": account}}
    for ticker in STOCK_PRICES:
        if ticker.lower() in question:
            return {"type": "tool_call", "tool": "get_stock_price", "args": {"ticker": ticker}}

    # No tool needed.
    return {"type": "answer", "text": "I can check account balances and stock prices."}


# ---------------------------------------------------------------------------
# 3. The harness: the loop that connects the model to the tools.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = "You are a finance assistant. Use tools to look up balances and prices."
MAX_STEPS = 5  # Safety limit so a confused model can't loop forever.


def run_agent(user_input: str) -> str:
    # The conversation history is the agent's only memory.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    for step in range(MAX_STEPS):
        response = mock_llm(messages)

        if response["type"] == "answer":
            return response["text"]

        # The model asked for a tool: run it and record the result.
        name, args = response["tool"], response["args"]
        print(f"  [step {step + 1}] calling {name}({args})")
        if name in TOOLS:
            result = TOOLS[name](**args)
        else:
            result = f"Error: unknown tool '{name}'"
        print(f"  [step {step + 1}] result: {result}")

        messages.append({"role": "assistant", "content": f"call {name}({args})"})
        messages.append({"role": "tool", "content": result})

    return "Stopped: too many steps."


if __name__ == "__main__":
    questions = [
        "What's my checking balance?",
        "How much is in my savings balance?",
        "What's the price of NVDA?",
        "Hello!",
    ]
    for q in questions:
        print(f"User: {q}")
        print(f"Agent: {run_agent(q)}\n")
