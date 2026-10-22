"""Score every TASK-ARM run in RUNS_DIR and print a markdown table plus JSON.

Usage: python3 -I bench/score.py RUNS_DIR > bench/results/results.json
"""
import glob
import json
import os
import subprocess
import sys

runs = os.path.abspath(sys.argv[1])
bench = os.path.dirname(os.path.abspath(__file__))
rows = []

for log in sorted(glob.glob(os.path.join(runs, "*.jsonl"))):
    name = os.path.basename(log)[:-6]
    task, arm = name.rsplit("-", 1)
    out = os.path.join(runs, name)
    check = subprocess.run([sys.executable, "-I", os.path.join(bench, "tasks", task, "check.py"), out],
                           capture_output=True, text=True, timeout=600)
    reqs = json.loads(check.stdout)
    result, spawns, model, denied, held = {}, 0, None, 0, 0
    for line in open(log):
        denied += "LEDGER GUARD: this looks like a detailed delegation" in line
        held += "LEDGER GUARD:" in line and "still has" in line
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            model = d.get("model")
        if d.get("type") == "result":
            result = d
        if d.get("type") == "assistant" and d.get("parent_tool_use_id") is None:
            for c in d["message"].get("content", []):
                if c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task", "Workflow"):
                    spawns += 1
    ledger = bool(glob.glob(os.path.join(out, ".workflow", "LEDGER*.md")))
    per_model = {k: round(v.get("costUSD", 0), 2) for k, v in (result.get("modelUsage") or {}).items()}
    rows.append({
        "task": task, "arm": arm, "model": model,
        "met": sum(r["ok"] for r in reqs.values()), "total": len(reqs),
        "missed": [f'{k} {v["desc"]}' for k, v in reqs.items() if not v["ok"]],
        "cost_usd": round(result.get("total_cost_usd", 0), 2), "cost_by_model": per_model,
        "output_tokens_by_model": {k: v.get("outputTokens") for k, v in (result.get("modelUsage") or {}).items()},
        "wall_s": int(open(os.path.join(runs, name + ".wall")).read()),
        "turns": result.get("num_turns"), "spawns": spawns, "ledger": ledger,
        "spawn_denied": denied, "stop_held": held,
        "is_error": result.get("is_error"), "stop_reason": result.get("subtype"),
    })

print("| task | arm | requirements met | cost (USD) | of which Fable | Fable output tokens | wall (s) | delegation calls (denied) | ledger |", file=sys.stderr)
print("|---|---|---|---|---|---|---|---|---|", file=sys.stderr)
for r in rows:
    fable = [k for k in r["cost_by_model"] if "fable" in k]
    print(f'| {r["task"]} | {r["arm"]} | {r["met"]}/{r["total"]} | {r["cost_usd"]:.2f} | '
          f'{sum(r["cost_by_model"][k] for k in fable):.2f} | {sum(r["output_tokens_by_model"][k] for k in fable)} | '
          f'{r["wall_s"]} | {r["spawns"]} ({r["spawn_denied"]}) | {"yes" if r["ledger"] else "no"} |', file=sys.stderr)
print(json.dumps(rows, indent=2))
