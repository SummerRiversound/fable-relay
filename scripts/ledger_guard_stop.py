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

Two silences, both measured: over 8 days every single fire landed either
while a spawned agent was still working (the chair parking a turn, not
closing one) or on a ledger a different session had written. So the guard
stays quiet while an async spawn has not reported back, and quiet unless
this session wrote the ledger itself. Neither silence spends the
once-per-session reminder. Without a readable transcript both checks are
skipped and the guard behaves as before.

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
NOTIFICATION_RE = re.compile(r"<tool-use-id>(toolu_[A-Za-z0-9_-]+)</tool-use-id>")
LEDGER_WRITE_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit", "Bash")
TRANSCRIPT_TAIL_BYTES = 4 * 1024 * 1024


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


def transcript_entries(transcript_path):
    """Parsed entries from the tail of the session transcript, or None."""
    if not isinstance(transcript_path, str) or not os.path.isfile(transcript_path):
        return None
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            f.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            data = f.read()
    except OSError:
        return None
    lines = data.decode("utf-8", errors="replace").splitlines()
    if size > TRANSCRIPT_TAIL_BYTES and lines:
        lines = lines[1:]  # a tail read starts mid-line
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _blocks(entry):
    message = entry.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def agents_still_running(entries):
    """True while a spawned agent has not reported back.

    An Agent/Task spawn returns "Async agent launched successfully" at once and
    reports later as a `<task-notification>` user message carrying the spawn's
    tool-use id. A launch with no notification is still working — the chair is
    waiting, not closing. Spawns that return their result directly never enter
    the launched set, so synchronous hosts keep the old behaviour.
    """
    launched, reported = set(), set()
    for entry in entries:
        for block in _blocks(entry):
            if block.get("type") != "tool_result":
                continue
            if "Async agent launched" in json.dumps(block.get("content"), default=str):
                launched.add(block.get("tool_use_id"))
        if entry.get("type") == "user":
            reported.update(NOTIFICATION_RE.findall(json.dumps(entry.get("message"), default=str)))
    return bool(launched - reported)


def session_wrote_ledger(entries, ledger):
    """True when this session edited the ledger itself.

    A session that only searched or answered questions in a folder someone
    else left a ledger in is not closing that ledger's work. Spawn prompts
    quote item numbers constantly, so only file-touching tools count.
    """
    name = os.path.basename(ledger)
    for entry in entries:
        for block in _blocks(entry):
            if block.get("type") != "tool_use" or block.get("name") not in LEDGER_WRITE_TOOLS:
                continue
            if name in json.dumps(block.get("input"), default=str):
                return True
    return False


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

    entries = transcript_entries(data.get("transcript_path"))
    if entries is not None:
        if agents_still_running(entries):
            return  # the turn is a pause in delegated work, not a close
        if not session_wrote_ledger(entries, ledger):
            return  # someone else's ledger; this session is a visitor here

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
