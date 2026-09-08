#!/bin/bash
# fable-relay PostToolUse hook: deterministically count consecutive inline tool
# calls (Bash/Read/Grep/Glob/Edit/Write/NotebookEdit) and inject a delegation
# notice once the count crosses FABLE_RELAY_TRIPWIRE (default 4), then every
# 6 calls after that. Agent/Task calls reset the counter to 0. Subagent calls
# are ignored entirely. Any parse failure or unrecognized tool is a silent
# no-op - this must never break a session.
python3 -c '
import json
import os
import re
import sys
import tempfile

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    # Subagents are not the audience: the notice tells the chair to hand the
    # block to an agent, and an agent doing that block has nobody to hand it
    # to. They also share the chair session_id, so their calls were inflating
    # the chair streak in the same state file. PostToolUse payloads carry
    # agent_id/agent_type only inside a subagent - the main thread sends
    # neither key - so their presence is the signal.
    if payload.get("agent_id") or payload.get("agent_type"):
        return

    tool_name = payload.get("tool_name")
    session_id = payload.get("session_id") or "default"

    inline_tools = {"Bash", "Read", "Grep", "Glob", "Edit", "Write", "NotebookEdit"}
    reset_tools = {"Agent", "Task", "Workflow"}

    if tool_name not in inline_tools and tool_name not in reset_tools:
        return

    safe_session = re.sub(r"[^A-Za-z0-9-]", "", str(session_id)) or "default"
    state_file = os.path.join(tempfile.gettempdir(), "fable-relay-count-" + safe_session)

    tier = "fable"
    try:
        with open(os.path.join(tempfile.gettempdir(), "fable-relay-tier-" + safe_session)) as f:
            value = f.read().strip()
        if value in ("fable", "opus", "sonnet", "haiku"):
            tier = value
    except Exception:
        pass

    if tool_name in reset_tools:
        count = 0
    else:
        try:
            with open(state_file, "r") as f:
                count = int(f.read().strip())
        except Exception:
            count = 0
        count += 1

    try:
        with open(state_file, "w") as f:
            f.write(str(count))
    except Exception:
        pass

    if tool_name in reset_tools:
        return

    try:
        threshold = int(os.environ.get("FABLE_RELAY_TRIPWIRE", "4"))
    except Exception:
        threshold = 4

    if count >= threshold and (count - threshold) % 6 == 0:
        if tier == "sonnet":
            message = (
                "[fable-relay] " + str(count) + " consecutive inline tool calls. "
                "Sonnet chair: inline edits are fine at your tier, but if this "
                "streak is discovery or bulk reading, hand it to scout to keep "
                "your context lean."
            )
        elif tier == "opus":
            message = (
                "[fable-relay] " + str(count) + " consecutive inline tool calls "
                "without delegating. Opus chair: this block belongs to a cheaper "
                "agent (scout for discovery, executor for edits); architect is your "
                "own tier, so it saves nothing here."
            )
        elif tier == "haiku":
            message = (
                "[fable-relay] " + str(count) + " consecutive inline tool calls "
                "without delegating. Haiku chair: if this work is nontrivial, "
                "route it up (executor for implementation, architect for hard "
                "problems)."
            )
        else:
            message = (
                "[fable-relay] " + str(count) + " consecutive inline tool calls without "
                "delegating. Chair: this block belongs to an agent (scout for "
                "discovery, executor for edits) - delegate the remainder now, and put "
                "the deep thinking into the spawn effort."
            )
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }
        }
        sys.stdout.write(json.dumps(output, separators=(",", ":")) + "\n")

main()
'
exit 0
