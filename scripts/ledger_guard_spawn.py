#!/usr/bin/env python3
"""fable-relay PreToolUse guard (Agent|Task): keep detailed delegation on the ledger.

Rule 1: a detailed delegation (spawn prompt longer than the threshold)
requires a Requirements Ledger — any live `.workflow/LEDGER*.md`
(most recently modified wins, `*-archive.md` / `*_archive.md` excluded),
searched from the working directory upward to the first `.git` boundary
or $HOME. Short spawn prompts (quick lookups) always pass, so casual
scout agents are never blocked.

Design notes (inherited from fable5-orchestrator, credit where due):
- The threshold defaults to 1500 chars — strict on purpose. On a
  Fable 5 chair even small delegations should carry a ledger: detail
  loss at task->plan translation is exactly what the ledger catches.
- `LEDGER*.md` matches per-task names (`LEDGER-auth.md`) as well as the
  bare name, but "ledger" must be a whole segment (`ledgers.md` does
  not count) and a trailing `-archive` / `_archive` segment retires it.
- The upward walk stops at the first dir containing `.git` (checked
  with os.path.exists, not isdir — in worktrees and submodules .git is
  a FILE) or at $HOME; realpath so a symlinked cwd climbs the real tree.
- The hook contract is exit 0 always: any failure fails OPEN.

Configuration:
    FABLE_RELAY_LEDGER_THRESHOLD  gate in chars (default 1500)
"""
import json
import os
import sys

DEFAULT_THRESHOLD = 1500


def threshold():
    raw = os.environ.get("FABLE_RELAY_LEDGER_THRESHOLD")
    if raw is not None:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


def active_ledger_in(dirpath):
    """The live ledger in dirpath/.workflow, or None."""
    workflow = os.path.join(dirpath, ".workflow")
    try:
        names = os.listdir(workflow)
    except OSError:
        return None
    best, best_mtime = None, -1.0
    for name in names:
        low = name.lower()
        if not (low.startswith("ledger") and low.endswith(".md")):
            continue
        # "ledger" must be a whole segment: LEDGER.md, LEDGER-topic.md,
        # LEDGER_topic.md — but not ledgers.md or ledgerish.md.
        if low[6:7] not in (".", "-", "_"):
            continue
        # Retired only when "archive" is the trailing segment; a live
        # ledger ABOUT archives (LEDGER-archive-migration.md) still counts.
        if low.endswith("-archive.md") or low.endswith("_archive.md"):
            continue
        path = os.path.join(workflow, name)
        try:
            if not os.path.isfile(path) or not os.access(path, os.R_OK):
                continue
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime > best_mtime:
            best, best_mtime = path, mtime
    return best


def find_ledger(start_dir):
    """Path of the live .workflow/ ledger from start_dir up to the repo root or $HOME."""
    if not isinstance(start_dir, str) or not start_dir:
        start_dir = os.getcwd()
    d = os.path.realpath(start_dir)
    home = os.path.realpath(os.path.expanduser("~"))
    while True:
        candidate = active_ledger_in(d)
        if candidate:
            return candidate
        if os.path.exists(os.path.join(d, ".git")) or d == home:
            return None
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _guard(data):
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    # Forks inherit the full conversation context — the ledger is
    # already in front of them; forcing a file adds nothing.
    if str(tool_input.get("subagent_type") or "").strip().lower() == "fork":
        return

    text = tool_input.get("prompt") or tool_input.get("script") or ""
    if not isinstance(text, str):
        text = ""

    limit = threshold()
    if len(text) <= limit:
        return

    if find_ledger(data.get("cwd")):
        return

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"LEDGER GUARD: this looks like a detailed delegation "
                f"(spawn prompt > {limit} chars) but no active ledger exists "
                "in any .workflow/ from the working directory up to the repo "
                "root. Per Rule 1, first write the numbered Requirements "
                "Ledger to ./.workflow/LEDGER.md (checkbox format: "
                "'- [ ] N. <item>', last item '- [ ] V. fresh-eyes "
                "verification passed'), then re-spawn citing which ledger "
                "items each agent covers. If this is genuinely a small "
                "single-phase task, do it directly; if it is multi-phase, "
                "write the ledger and delegate — never keep multi-phase "
                "work solo."
            ),
        }
    }))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # malformed input -> never block
    if not isinstance(data, dict):
        return
    try:
        _guard(data)
    except Exception:
        return  # the guard fails open; it never crashes the hook pipeline


if __name__ == "__main__":
    main()
