# LangGraph-style agent loop (from scratch, mock)

A small, standard-library-only example of the loop that LangGraph runs for you,
written without LangGraph. The LLM and the MCP tool are both mocked, so there's
no API key, network, or MCP server.

## Run

```bash
python3 examples/langgraph_style_loop/agent.py
```

## How it works

- **State** is a plain dict: the message list plus a step counter and limit.
  Every node reads it and returns the keys it changed.
- **`call_model` node** sends the full conversation to the mock LLM and appends
  its reply, which is either tool calls or a final text answer.
- **`call_tools` node** parses each tool call's JSON arguments, runs the tool by
  name, and appends the result as a `tool` message tied to the call's id.
- **`route`** is the conditional edge: if the last reply asked for tools, go to
  `call_tools`; otherwise (or after `max_steps`) end.
- **`run_graph`** is the loop: model, route, tools, model, and so on until the
  model stops asking for tools.

## The mock MCP tool

`mcp_get_stock_valuation(ticker)` returns the stock's price, forward P/E, the
average forward P/E of its peers, and the percentage it sits above or below that
average. Peers come from the hard-coded `PEERS` mapping; the agent never picks
them. All figures are made-up fixtures, not market data.

## Next steps

Swap `mock_llm` for a real chat model with tool calling, and swap the tool
function for a call to a real MCP server. The nodes and loop stay the same.
