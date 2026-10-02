# Legal document judge (mock)

A minimal, fixed two-call workflow in plain Python. Both the answering model
and judge return hard-coded mock responses. No API key, network connection,
LangChain, or LangGraph is required.

## Run

From the repository root:

```bash
python3 examples/legal_document_judge/main.py
```

Requires Python 3.9 or newer. No installation step is needed.
The contract path is relative to the script, so this also works from other
working directories.

## Follow the code

1. Read the fictional service agreement in `contract.txt`.
2. Package the question and contract for the first `call_model` invocation.
3. Package the answer, question, and contract for the second invocation,
   using `JUDGE_SYSTEM_PROMPT` as the rubric.
4. Parse and validate the judge JSON.
5. Print the answer, judgment, and simulated PASS/FAIL/UNJUDGED status.

The judge has two fields: `correctness_score` and
`correctness_explanation`. The rubric defines scores 1–3; the Python code
requires 3 for PASS. A null score means UNJUDGED.

## What the mocks demonstrate

The supplied answer cites Clauses 2 and 3. The supplied judgment has score 3,
so the default run prints a simulated PASS. These are fixtures, not measured
model quality. The stub ignores the prompt contents: changing the contract,
question, answer, or rubric does **not** cause it to reassess the score.

To explore the plumbing, edit `MOCK_JUDGMENT` to use score 1 or 2 (FAIL),
or null/None (UNJUDGED). Malformed JSON or invalid field values raise an error
rather than silently producing a passing score.

## Add a real model later

Replace the body of `call_model` with your provider's SDK call, passing
`system_prompt` and `user_prompt` and returning the response text. Stop using
the `mock_response` fixture and update the mock labels when live calls are
implemented. Configure credentials outside the source code.

Then add more questions and manually reviewed expected answers to check
whether the judge agrees with your assessment. This example checks fidelity
to a fictional document, not legal validity or current law.

## Files

- `main.py`: prompts, mock model boundary, two-call workflow, JSON validation.
- `contract.txt`: fictional source evidence.
- `requirements.txt`: documents that no external dependencies are needed.
