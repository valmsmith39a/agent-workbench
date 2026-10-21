"""Run each example non-interactively and print a side-by-side summary. Failures are reported, not fatal."""

import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESSES = [
    ("langgraph_style_loop", "examples/langgraph_style_loop/agent.py"),
    ("legal_document_judge", "examples/legal_document_judge/main.py"),
    ("investments_agent", "examples/investments_agent/agent.py"),
    ("coffee_shop_agent", "agents/coffee-shop/agent/agent.py"),
    ("coffee_shop_eval", "agents/coffee-shop/agent/eval.py"),
]


def run(path):
    t = time.time()
    try:
        p = subprocess.run([sys.executable, str(ROOT / path)], cwd=ROOT, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        out, code = p.stdout + p.stderr, p.returncode
    except Exception as e:  # missing file, timeout, etc.
        out, code = str(e), "ERR"
    return out, code, time.time() - t


def metrics(out):
    m = re.search(r"steps=(\d+) tool_calls=(\d+)", out)
    if m:
        return m.group(1), m.group(2)
    tools = len(re.findall(r"\[tool\]", out))
    steps = len(re.findall(r"\[route\]", out))
    return (str(steps) if steps else "-"), (str(tools) if tools else "-")


def main():
    rows = []
    for name, path in HARNESSES:
        if not (ROOT / path).exists():
            rows.append((name, "-", "-", "MISSING", "-", ""))
            continue
        out, code, dt = run(path)
        steps, tools = metrics(out)
        passes = re.search(r"(\d+/\d+) passed", out) or re.search(r"\b(PASS|FAIL)\b", out)
        rows.append((name, steps, tools, str(code), f"{dt*1000:.0f}ms", passes.group(1) if passes else ""))
    hdr = ("harness", "steps", "tool_calls", "exit", "runtime", "judge")
    w = [max(len(str(r[i])) for r in rows + [hdr]) for i in range(len(hdr))]
    for r in [hdr] + rows:
        print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))


if __name__ == "__main__":
    main()
