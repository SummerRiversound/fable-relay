---
name: relay-setup
description: One-time setup for the fable-relay plugin. Sets the user's default model to "best" (Fable 5 with Opus fallback) in ~/.claude/settings.json with a timestamped backup, and verifies that the relay agents and hooks are installed. Run when the user asks to "run relay-setup" or to finish installing fable-relay.
---

# relay-setup

Configure the one thing a plugin cannot set by itself: the default session model.

## Steps

1. **Explain and get approval.** Tell the user this will set `"model": "best"` in `~/.claude/settings.json` (Fable 5 as the chair, falling back to the latest Opus when Fable is unavailable), and that a timestamped backup of the current file will be created first. Wait for their approval before writing anything.

2. **Back up.** Copy `~/.claude/settings.json` to `~/.claude/settings.json.relay-backup-<YYYYMMDD-HHMMSS>` if the file exists.

3. **Set the model.** Read `~/.claude/settings.json` (create `{}` if missing), set the top-level `"model"` key to `"best"`, and write it back as valid JSON without disturbing any other keys.

4. **Verify the install.** Confirm all of these exist under the plugin root:
   - `agents/scout.md`, `agents/executor.md`, `agents/architect.md`, `agents/verifier.md`
   - `hooks/hooks.json` plus the three shell hooks and the two Python guard scripts
   - `python3` available on PATH (the guard hooks need it)

5. **Report.** Tell the user: what was changed, where the backup is, and that a session restart is needed for the model change and the SessionStart policy injection to take effect. Suggest the smoke test: ask "which subagent types are available?" in the new session — scout, executor, architect, and verifier should appear.
