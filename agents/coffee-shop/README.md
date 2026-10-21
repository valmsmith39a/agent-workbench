# Coffee shop support agent (mock)

A small monorepo for a fictional coffee shop ("Bean There") support agent, following the
patterns in `agents/brokerage-support-agent`: an MCP server (official `mcp` SDK, FastMCP,
stdio) with tools grouped by category, a support agent that loads those tools over MCP, a
FastAPI `/chat` endpoint, and a static chat UI. The model is a **scripted mock** (`agent/mock_model.py`),
so there's no API key and no network calls, and output is deterministic.

## Layout
```
agents/coffee-shop/
├── README.md
├── requirements.txt        # mcp>=1.20,<2, fastapi, uvicorn, pydantic, pytest, httpx
├── pytest.ini
├── mcp-server/
│   ├── server.py           # FastMCP("coffee-shop-support"), registers each category, stdio
│   └── tools/
│       ├── __init__.py     # CATEGORIES + TOOLS registry (used by the local fallback)
│       ├── data.py         # fake customers/menu/stores/rewards + in-memory orders & tickets
│       ├── menu.py
│       ├── ordering.py
│       └── account.py
├── agent/
│   ├── agent.py            # call_model -> route -> call_tools loop + CLI (demo, -i, --trace, --local)
│   ├── mock_model.py       # scripted model: intent -> tool calls -> final answer
│   ├── prompts.py          # system prompt, guardrails, context assembly, session customers
│   ├── toolbox.py          # MCP stdio client (default) with direct-import fallback
│   ├── api.py              # FastAPI: GET / (UI), POST /chat
│   ├── eval.py             # 17 judge-style PASS/FAIL checks over MCP
│   └── tests/              # test_tools.py, test_agent.py (incl. MCP server), test_api.py
└── ui/
    └── index.html          # chat page calling /chat, customer picker, trace toggle
```

## MCP tools (3 categories, 10 tools)
| Category | Tool | Purpose |
|---|---|---|
| menu | `list_menu(category?: 'coffee'\|'dessert')` | Items with starting price |
| menu | `get_item_details(item_name)` | Prices per size, sizes, milk options, allergens |
| menu | `get_store_info(store_id?)` | Hours, address, phone (default STORE-1) |
| ordering | `place_order(customer_id, items[{name,size,milk,qty}], pickup_time?)` | Validates against menu; returns order id, total, ETA. Pay at pickup, nothing charged |
| ordering | `get_order_status(order_id)` | Status, items, pickup time, total |
| ordering | `modify_order(order_id, items?, pickup_time?)` | Re-validates items; refused if cancelled/picked up |
| ordering | `cancel_order(order_id)` | Marks cancelled; refused if already cancelled |
| account | `get_loyalty_account(customer_id)` | Tier and points |
| account | `get_rewards(customer_id)` | Redeemable rewards and the next one |
| account | `submit_feedback(customer_id, message, order_id?, type: 'feedback'\|'complaint')` | Returns a ticket id |

Mock data: customers CUST-201 (Gold, 240 pts), CUST-202 (Green, 45 pts, owns seeded order ORD-0900),
CUST-203 (not enrolled). Menu: latte, cappuccino, americano, cold brew, mocha, plus the desserts almond croissant,
chocolate chip cookie, and tiramisu. State is in memory per server process.

## Agent design
- **Loop:** `call_model` → `route` (tool calls? → `call_tools`, else end) → … (max 6 steps), the same shape as
  `examples/langgraph_style_loop` and the brokerage graph, written as a plain async loop.
- **Context:** system prompt (tools + guardrails) → verified session snapshot (`customer_id` from the
  session/CLI/request, never parsed from the message) → conversation history → tool results.
- **Guardrails:** menu facts only from tools; orders only via ordering tools; no payment details; allergen
  lists plus "check with staff"; complaints get an apology, a ticket, and a manager-handoff offer; order
  status, modify, and cancel first check the order belongs to the session customer.
- **Trace:** each step records the model decision, route, tool call, args, and result (`--trace`, `/chat` `trace`, UI toggle).

## Run (from `agents/coffee-shop/`)
```bash
pip install -r requirements.txt

# mcp-server: start on its own (stdio; an MCP client launches it the same way)
python mcp-server/server.py

# agent: CLI
python agent/agent.py                         # demo of 11 questions across all categories
python agent/agent.py --trace                 # print model decisions, tool calls, results, routes
python agent/agent.py -i --customer CUST-202  # interactive (Ctrl-D quits)
python agent/agent.py --local                 # import tools directly instead of MCP
python agent/eval.py                          # PASS/FAIL checks
python -m pytest                              # tools, agent, MCP server, API tests

# agent API + ui
uvicorn api:app --app-dir agent --port 8010   # open http://localhost:8010/ for the UI
curl -s localhost:8010/chat -H 'content-type: application/json' \
  -d '{"message":"I would like to order a large latte with oat milk","customer_id":"CUST-202"}'
```
If `mcp` isn't installed, the agent falls back to direct import automatically (`COFFEE_TOOLS=local` forces it).
From the repo root, `python scripts/compare_harnesses.py` runs this demo and eval alongside the other examples.
