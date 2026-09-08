# fable-relay 🏃

**Fable 5 holds the baton. The ledger keeps the score. Fresh eyes call the finish.**

A Claude Code plugin that makes Fable 5 a token-frugal orchestrator. The chair keeps the judgment — intent, architecture, decomposition, tradeoffs, final review — running at low-to-medium effort. Tiered subagents on Opus, Sonnet, and Haiku do the labor at whatever effort the task demands. A hook-enforced Requirements Ledger stops silent detail loss, and every close with a diff worth checking gets fresh-eyes verification.

## Why

Two problems, one design:

1. **Cost routing.** Fable 5 is the strongest model on a Claude subscription and the most expensive one to burn on grep runs and boilerplate. Each piece of work goes to the cheapest tier that can do it well — and deep reasoning goes into the *effort of the spawn*, never into the chair grinding inline.
2. **Silent detail loss.** Naive delegation has a failure mode worse than the cost it saves: requirements vanish at the task→plan translation step, subagents return confident summaries, and nobody notices what got dropped until it ships broken. The Requirements Ledger makes detail loss *visible* — and two guard hooks make the ledger *mechanical*, not advisory.

## How it works

**Four tiered agents**, each pinned to a model:

| Agent | Model | Owns |
|---|---|---|
| `fable-relay:scout` | Haiku (medium effort) | Discovery, reading files/logs, batched lookups, simple checks |
| `fable-relay:executor` | Sonnet (high effort) | Scoped implementation from a five-part spec, tests, routine edits |
| `fable-relay:architect` | Opus (max effort) | Complex implementation, deep debugging, high-risk work, reviewing cheaper agents |
| `fable-relay:verifier` | Sonnet (Opus for high-risk closes) | Fresh-eyes checks against the Ledger; verifies, never fixes |

**Verification is scoped, not automatic.** A fresh verifier runs on a repo diff of ~300 lines or more, on anything high-risk at any size, and on documents whose claims cite evidence. Smaller green-gated diffs close on the chair reading the diff, and external state (issue lists, setup steps) is checked with a few commands instead. The verifier reads the producer's saved gate output rather than re-running it.

**Three soft-enforcement layers** (a one-time policy is not enough — models drift back to doing everything inline):

- **SessionStart** injects the orchestration policy, auto-detecting the chair's tier (Fable/Opus/Sonnet/Haiku) and appending a tier adaptation so the cost logic stays correct even mid-session-switcheroo.
- **UserPromptSubmit** re-asserts a one-line tier-aware reminder every turn.
- **PostToolUse** deterministically counts consecutive inline tool calls and injects a delegation notice once the streak crosses `FABLE_RELAY_TRIPWIRE` (default 10). Agent/Task calls reset it, and subagent calls are ignored.

**Two hard guard hooks** — they fence the two ends of the failure pipeline, where details die entering and leaving the workflow:

| Guard | Trigger | Effect |
|---|---|---|
| **Spawn guard** (`PreToolUse` on `Agent\|Task`) | A detailed delegation (spawn prompt > 1500 chars) while no live `./.workflow/LEDGER*.md` exists | The spawn is denied with instructions: write the numbered ledger first. Short prompts (quick scouts) always pass. Forks are exempt (they inherit the ledger through context). |
| **Close guard** (`Stop`) | The turn ends while the ledger has open `- [ ]` items | The stop is held once per session, with the open items listed. `- [x]` (done + verified) and `- [~] deferred: <reason>` count as closed. |

**Ledger format** — the last item is always the verification gate, and only evidence closes it:

```
- [ ] 1. Every explicit requirement, one line each
- [ ] 2. Implicit expectations and constraints too
- [x] 3. Marked done only after verification confirms it
- [~] 4. deferred: user approved postponing this
- [ ] V. fresh-eyes verification passed
```

**Filesystem is shared memory.** Bulk lives in `./.workflow/scratch/`; agents return paths + briefs (≤40 lines), never dumps. Context does not survive compaction; files do.

## Install

```
/plugin marketplace add SummerRiversound/fable-relay
/plugin install fable-relay@fable-relay
```

Then ask Claude to **"run relay-setup"** — it sets `model: "best"` in `~/.claude/settings.json` (with your approval and a backup) and verifies the install. Restart your session and you're done.

### Requirements

- Claude Code with plugin support and a subscription that includes Fable 5 (the `best` alias falls back to the latest Opus otherwise — the tier adaptation handles that automatically)
- `python3` on PATH (default on macOS, Linux, and WSL)

## Day-to-day

Nothing. Every new chat starts with the policy loaded and the agents available. To check it's active: ask *"which subagent types are available?"* — you should see `fable-relay:scout`, `fable-relay:executor`, `fable-relay:architect`, and `fable-relay:verifier`. Plugin agents are namespaced, so that prefix is part of the name you spawn with. To skip orchestration for a session, just say so ("don't delegate in this session") — the policy defers to your instructions.

### Configuration

| Env var | Default | Meaning |
|---|---|---|
| `FABLE_RELAY_TRIPWIRE` | `10` | Consecutive inline tool calls before the counter notice fires |
| `FABLE_RELAY_LEDGER_THRESHOLD` | `1500` | Spawn-prompt chars above which a delegation requires a ledger |
| `FABLE_RELAY_STOP_MODE` | `once-per-session` | Set `every-turn` for legacy per-turn close blocking |

Set them in `~/.claude/settings.json` under `"env"`.

## Honest limitations

- Hooks check ledger *existence* and checkbox *state* — not ledger fidelity. Writing a faithful ledger remains a judgment task, which is exactly why it's assigned to the chair, not a subagent.
- Marking `- [x]` without actually verifying is possible; the fresh-eyes rule is prompt-level. The hooks fence exactly the two failure points that get skipped the most.
- A fully-closed ledger from a previous session satisfies the spawn guard until you archive it (`LEDGER-<topic>-archive.md`). Archive finished ledgers.

## Credits

This plugin is a deliberate synthesis of four designs:

- [realgarit/fable-baton](https://github.com/realgarit/fable-baton) — the 4-tier agent skeleton, the three soft-enforcement layers, tier auto-detection, and "skills define WHAT, not WHO".
- [Rylaa/fable5-orchestrator](https://github.com/Rylaa/fable5-orchestrator) — the Requirements Ledger, both guard hooks, filesystem-as-shared-memory, effort routing, and mandatory fresh-eyes verification.
- [DannyMac180/fable-advisor](https://github.com/DannyMac180/fable-advisor) — the five-part spec contract, the "empty diff is never complete" rule, and structured report formats.
- [barkain/claude-code-workflow-orchestration](https://github.com/barkain/claude-code-workflow-orchestration) — escalating-nudge philosophy and the lean-injection lesson (keep session-start cost small).

## License

MIT
