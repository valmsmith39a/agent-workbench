# Brokerage Customer Support Agent

An AI customer support agent for investment brokerage accounts that uses LangGraph and MCP tools to resolve customer-specific trade, transfer, and account restriction questions.

This project is being built in small steps. Each step adds one layer and can be run on its own.

## Build steps

- [x] **Step 1: mock brokerage data and a trade status lookup.** Plain Python, no AI yet.
- [x] **Step 2: expose the lookup as an MCP tool (`get_trade_status`)**
- [x] **Step 3: a LangGraph agent that calls the tool to answer "Did my NVDA trade go through?"**
- [x] **Step 4: a FastAPI chat endpoint**
- [x] **Step 5: a simple chat UI**
- [x] **Step 6: add `get_transfer_status`**
- [x] **Step 7: add `get_account_restrictions`**
- [ ] Step 8: tool trace in the UI, and a fuller README

## Step 1: the data layer

```
app/models/brokerage.py                 Pydantic models: Order, TradeStatusResult
app/services/mock_brokerage_service.py  fake order data + get_trade_status()
tests/test_mock_brokerage_service.py
```

Run it:

```bash
cd agents/brokerage-support-agent
pip install -r requirements.txt
python -m app.services.mock_brokerage_service   # prints the NVDA order as JSON
pytest
```

## Step 2: the MCP tool

```
app/mcp/server.py         creates the FastMCP server and registers tools; runs over stdio
app/mcp/tools/trades.py   get_trade_status tool: calls the service, returns JSON
app/mcp/client_demo.py    launches the server and calls the tool, no LLM involved
tests/test_mcp_tools.py   calls the tool through a real MCP client session
```

The tool is a thin wrapper. It describes itself (name, description, input
schema), calls `get_trade_status` in the service, and returns the result as
JSON. Expected errors (unknown account, bad ticker) come back as
`{"error": {"code", "message"}}` so a caller can explain them.

Run it:

```bash
python -m app.mcp.client_demo   # lists the tools, then calls get_trade_status for NVDA
pytest
```

## Step 3: the agent

```
app/agent/graph.py      LangGraph graph: agent node + tools node; injects account_id
app/agent/prompts.py    system prompt
app/agent/llm.py        picks Claude (if ANTHROPIC_API_KEY is set) or the offline stand-in
app/agent/mock_llm.py   offline stand-in: keyword rules, not an LLM
app/agent/cli.py        ask one question from the terminal and print each step
tests/test_agent.py
```

The graph:

```
START -> agent --(model asked for a tool)--> tools -> agent -> END
               \--(model answered)--------------------------> END
```

The agent starts the MCP server from step 2 as a subprocess and loads its
tools with `langchain-mcp-adapters`. The model sees the tool without its
`account_id` parameter; the tools node fills it in for the signed-in customer,
so the model can't read another customer's account.

Run it:

```bash
python -m app.agent.cli "Did my NVDA trade go through?"
export ANTHROPIC_API_KEY=...   # optional: use Claude instead of the offline stand-in
pytest
```

## Step 4: the chat API

```
app/main.py          FastAPI app: starts the MCP server on startup, POST /api/chat
app/config.py        demo account and MCP server settings, shared by the CLI and API
app/models/api.py    ChatRequest / ChatResponse
tests/test_api.py    calls the API end to end
```

On startup the app launches the MCP server once and keeps the session open;
each request runs the agent graph. The customer's account is set on the server
(a fixed demo account until there is authentication), not sent by the client.

Run it:

```bash
uvicorn app.main:app --reload
curl -s localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message": "Did my NVDA trade go through?"}'
```

Interactive API docs: http://localhost:8000/docs

## Step 5: the chat UI

```
frontend/index.html   single-page chat UI (plain HTML/CSS/JS, no build step)
app/main.py           now also serves the page at GET /
```

The page posts each message to `/api/chat` and shows the answer, plus which
tool the agent used. Click a suggested question or type your own.

Run it:

```bash
uvicorn app.main:app --reload
# open http://localhost:8000
```

## Step 6: the transfer tool

Adding a second tool touches each layer once, and nothing else:

```
app/models/brokerage.py                 + Transfer, TransferStatusResult
app/services/mock_brokerage_service.py  + transfer data, get_transfer_status(); BrokerageError base class
app/mcp/tools/transfers.py              new get_transfer_status MCP tool
app/mcp/tools/common.py                 new run_tool helper shared by both tools
app/mcp/server.py                       registers the transfers tool
app/agent/prompts.py                    tells the model when to use each tool
app/agent/mock_llm.py                   offline stand-in learns transfer questions
frontend/index.html                     transfer questions in the suggestions
```

The agent graph didn't change: it works with whatever tools the MCP server
advertises.

Mock transfers: a $5,000 deposit that is **processing**, a $2,500 deposit that
**completed**, and a $1,000 withdrawal that **failed** (bank account closed).

```bash
python -m app.agent.cli "Where is the \$5,000 I transferred from my checking account?"
```

## Step 7: the account restrictions tool

```
app/models/brokerage.py                 + Restriction, ProposedOrder, BlockingReason, AccountRestrictionsResult
app/services/mock_brokerage_service.py  + account balances, restrictions, mock quotes, pre-trade checks
app/mcp/tools/accounts.py               new get_account_restrictions MCP tool
app/mcp/server.py                       registers it
app/agent/prompts.py, mock_llm.py       when and how to use it
```

The pre-trade checks are plain code in the service, not the model. Given a
symbol, side and quantity, the service prices the order with a mock quote and
returns `can_place_order` plus each blocking reason. The model only explains
the result.

The demo account (cash account, $412.55 buying power, $1,381.02 unsettled from
an AAPL sale that settles 2026-10-05, insider flag on GOOGL) shows each case:

| Order | Result |
|---|---|
| buy 2 NVDA | allowed |
| buy 10 NVDA | blocked: **unsettled funds** (covered after 2026-10-05) |
| buy 25 AMD | blocked: **insufficient buying power** |
| buy 1 GOOGL | blocked: **account restriction** (insider pre-clearance) |
| sell 9 TSLA | blocked: holds only 5 shares |

With no order named ("Why can't I place this trade?"), the tool returns the
account's buying power, unsettled funds and restrictions, and the agent asks
which order the customer means.

```bash
python -m app.agent.cli "Why can't I buy 10 shares of NVDA?"
```
