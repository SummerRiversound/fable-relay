# Benchmark: plugin off vs on

A small headless comparison of the same model with and without fable-relay. It asks one question: does the plugin change how many explicit requirements end up met, and what does it cost?

## Method

- **Tasks.** Three self-contained Python tasks, each in a fresh, git-initialised empty folder. Each prompt is written as prose, the way a person asks, and carries ten requirements, a few of them easy to drop (an edge case, a naming rule, a README or CHANGELOG line). The prompts are in `tasks/<task>/prompt.md`.
- **Arms.** Both arms run `claude -p` with `--model best` (the model `relay-setup` sets), `--setting-sources project,local` so the owner's user-level settings, plugins, hooks and CLAUDE.md stay out, `--permission-mode bypassPermissions` inside the throwaway folder, and a `--max-budget-usd 10` cap. The `on` arm adds `--plugin-dir` pointing at this repo. One run per arm per task.
- **Scoring.** `tasks/<task>/check.py` is never shown to the session. It checks the ten requirements deterministically (calls the functions, runs the CLI, parses the AST, runs the session's own unit tests). Each checker was first run against a hand-written reference solution (10 of 10) and an empty folder (0 of 10).
- **Recorded.** Requirements met, total cost and per-model cost as reported by the CLI's result event (API-equivalent dollars, not subscription usage), wall time, top-level Agent/Task/Workflow calls, whether a ledger file was written, and how often the spawn guard denied a delegation.

To reproduce:

```
bench/run.sh csvstats off /tmp/runs   # repeat for each task and arm
python3 -I bench/score.py /tmp/runs > bench/results/results.json
```

## Results

Run on 2026-10-22 with Claude Code 2.1.308 and plugin v1.1.2; the session model resolved to `claude-fable-5-1` in every run. Raw per-run data is in `results/results.json`.

| task | arm | requirements met | cost (USD) | of which Fable | Fable output tokens | wall (s) | delegation calls (denied) | ledger |
|---|---|---|---|---|---|---|---|---|
| csvstats | off | 10/10 | 0.63 | 0.63 | 3980 | 47 | 0 (0) | no |
| csvstats | on | 10/10 | 1.11 | 0.77 | 3982 | 203 | 3 (1) | yes |
| slug | off | 10/10 | 0.48 | 0.48 | 1993 | 26 | 0 (0) | no |
| slug | on | 10/10 | 0.66 | 0.66 | 3925 | 64 | 1 (1) | no |
| todo | off | 10/10 | 0.62 | 0.62 | 3614 | 47 | 0 (0) | no |
| todo | on | 10/10 | 1.32 | 0.97 | 5952 | 405 | 3 (1) | yes |

**Both arms met all 30 requirements, so on these tasks the plugin bought no completeness and cost more.** With the plugin, total cost was 1.4 to 2.1 times higher and wall time 2.5 to 8.6 times longer. Fable's own spend did not drop either: its output tokens stayed level or rose. In each `on` run the first delegation was denied by the spawn guard; on the two larger tasks Fable then wrote a ledger and delegated to the executor and verifier, and on `slug` it did the work itself.

The likely reason is that the tasks were small enough for one Fable session to hold every requirement, so there was no detail loss to prevent. This run does not show whether the ledger helps on longer, multi-phase work; it shows what the overhead costs when it does not.

This is one run per cell on three small tasks (n=1), so treat every number as directional.
