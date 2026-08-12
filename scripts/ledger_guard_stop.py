#!/usr/bin/env python3
"""fable-relay Stop guard: hold a turn-end while the Requirements Ledger has open items.

Open item = a line matching '- [ ]'. Closed: '- [x]' (done + verified)
or '- [~] deferred: <reason>' (user-approved).

Blocking is scoped so the reminder does not tax every conversational
turn: once per session per ledger, tracked in a temp-dir sidecar. A
`stop_hook_active` check prevents infinite loops — the guard blocks a
close at most once, lists the open items, and lets the next stop pass.

Any live `.workflow/LEDGER*.md` counts (most recent wins, `*-archive.md`
retired), searched from the working directory upward to the first `.git`
boundary or $HOME — the exact same resolution as the spawn guard, so the
two guards always agree on whether a session has a ledger.

Fenced code blocks are excluded: a ``` example checklist in the ledger's
notes is not an open item.

Configuration:
    FABLE_RELAY_STOP_MODE=every-turn   restore per-turn blocking
"""
import json
import os
import re
import sys
import tempfile
import time

OPEN_ITEM_RE = r"^\s*[-*] \[ \](?:\s.*)?$"


def stop_sidecar_path(session_id):
    if not session_id:
        return None
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_")
    return os.path.join(tempfile.gettempdir(), f"fable-relay-stop-{safe}.json")


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
        if low[6:7] not in (".", "-", "_"):
            continue
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


def _outside_fences(text):
    """Drop fenced code blocks — a ``` example checklist is not an open item."""
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return "\n".join(kept)


def _read_blocked(path):
    try:
        with open(path, encoding="utf-8") as f:
            blocked = json.load(f).get("blocked")
        return blocked if isinstance(blocked, dict) else {}
    except Exception:
        return {}


def already_reminded(session_id, ledger):
    path = stop_sidecar_path(session_id)
    if not path or not os.path.isfile(path):
        return False
    return ledger in _read_blocked(path)


def record_reminder(session_id, ledger):
    path = stop_sidecar_path(session_id)
    if not path:
        return
    blocked = _read_blocked(path)
    try:
        blocked[ledger] = round(time.time(), 3)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"blocked": blocked}, f)
    except Exception:
        pass


def run_guard(data):
    # Loop guard: we already blocked this stop once; let it through now.
    if data.get("stop_hook_active"):
        return

    ledger = find_ledger(data.get("cwd"))
    if not ledger:
        return

    try:
        with open(ledger, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return

    open_items = re.findall(OPEN_ITEM_RE, _outside_fences(text), flags=re.M)
    if not open_items:
        return

    session_id = data.get("session_id")
    mode = (os.environ.get("FABLE_RELAY_STOP_MODE") or "once-per-session").strip().lower()
    if mode != "every-turn":
        if already_reminded(session_id, ledger):
            return
        record_reminder(session_id, ledger)

    preview = "\n".join(line.strip()[:200] for line in open_items[:10])
    more = f"\n(+{len(open_items) - 10} more)" if len(open_items) > 10 else ""
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"LEDGER GUARD: {ledger} still has {len(open_items)} "
            f"open item(s):\n{preview}{more}\n\n"
            "If you are CLOSING a workflow: address each item and mark it "
            "'- [x]' (only after verification confirms it), or "
            "'- [~] deferred: <reason>' with user approval, and run the "
            "fresh-eyes verifier if you haven't — only its evidence closes "
            "item V. If you are NOT closing a workflow, acknowledge the "
            "open-item count in one short line and stop — this reminder "
            "fires once per session. Archive the ledger (rename to "
            "LEDGER-<topic>-archive.md) if the task is truly abandoned."
        ),
    }))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    try:
        run_guard(data)
    except Exception:
        pass  # the guard fails open; it never crashes the hook pipeline


if __name__ == "__main__":
    main()
