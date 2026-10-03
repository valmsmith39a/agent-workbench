# Brokerage Customer Support Agent

An AI customer support agent for investment brokerage accounts that uses LangGraph and MCP tools to resolve customer-specific trade, transfer, and account restriction questions.

This project is being built in small steps. Each step adds one layer and can be run on its own.

## Build steps

- [x] **Step 1: mock brokerage data and a trade status lookup.** Plain Python, no AI yet.
- [ ] Step 2: expose the lookup as an MCP tool (`get_trade_status`)
- [ ] Step 3: a LangGraph agent that calls the tool to answer "Did my NVDA trade go through?"
- [ ] Step 4: a FastAPI chat endpoint
- [ ] Step 5: a simple chat UI
- [ ] Step 6: add `get_transfer_status`
- [ ] Step 7: add `get_account_restrictions`
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
