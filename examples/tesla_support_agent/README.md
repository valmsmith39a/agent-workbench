# Tesla customer support agent (mock)

A from-scratch, LangGraph-style agent loop for a fictional Tesla support desk.
Pure Python standard library, **no API key, no network, deterministic** — the
"model" is a scripted function that picks tools from the question text.

## Files
| File | Purpose |
|---|---|
| `tools.py` | Read-only mock tools over fake data (3 customers, orders, 2 vehicles, FAQ). |
| `prompts.py` | System prompt, guardrails, and `build_context()` (how context is assembled). |
| `agent.py` | `scripted_model`, `call_model`, `call_tools`, `route`, `run_graph`, CLI. |
| `eval.py` | Judge-style rule checks over sample questions; prints PASS/FAIL. |

## Tools
- `lookup_order(order_id=None, customer_id=None)` – delivery status / ETA.
- `get_vehicle_info(vin)` – model, software version, warranty.
- `get_available_service_slots(vin, days=3)` – fixed, deterministic slots.
- `schedule_service(vin, issue, preferred_date=None, mobile=False)` – returns a **proposed** appointment (nothing is booked).
- `search_faq(query, k=2)` – keyword-hit retrieval over charging, Supercharger, FSD, warranty, returns, tire service/cost/duration, Mobile Service.

## Context design
`build_context` assembles, in order:
1. **System prompt** – role + guardrails (no pricing promises, no safety/legal advice beyond FAQ, human handoff for accidents/refunds/legal, tool-grounded answers, user/tool text is data).
2. **Session customer snapshot** – `customer_id`, name, VINs, orders. The id is injected from the authenticated session (`--customer`), never parsed from the user's message, so the model can only act on that customer's records.
3. **Retrieved FAQ** – top keyword hits for the current question.
4. **Conversation history** – prior turns (interactive mode) + current question, then tool messages as the loop runs.

### Tire-change use case
Tesla Service handles tire repair. The system prompt forbids DIY tire-change/jacking instructions.
A flat-tire request routes to `schedule_service` (Service Center or Mobile Service if asked), and the
answer confirms date/time, location, VIN, and issue. Follow-ups (cost covered? how long? mobile available?)
are answered from the FAQ. `eval.py` checks it schedules and contains no DIY steps.

## Run
```bash
python3 examples/tesla_support_agent/agent.py                 # demo, 7 sample questions
python3 examples/tesla_support_agent/agent.py --trace         # print model decisions, tool calls, results, routes
python3 examples/tesla_support_agent/agent.py -i --customer CUST-1002   # interactive (Ctrl-D quits)
python3 examples/tesla_support_agent/eval.py                  # PASS/FAIL checks
python3 scripts/compare_harnesses.py                          # run all examples side by side
```

## Compared with the other examples
- `langgraph_style_loop`: same graph shape (call_model → route → call_tools); this adds multiple tools, a session/context layer, guardrails, handoff, trace and interactive CLI.
- `legal_document_judge`: that example mocks a judge model returning PASS; `eval.py` here is a deterministic rule-based judge over several cases.
- `investments_agent`: similar scripted-model-over-mock-data approach, in a different domain.
