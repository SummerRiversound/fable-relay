Build a tiny to-do list CLI as a Python package named `todo` in the current directory, runnable as `python3 -m todo`. Keep storage code in `todo/store.py`, separate from the command-line handling.

Commands: `add TEXT` prints `added N` where N is the new task's id; `list` prints one line per task in id order, formatted like `[ ] 1 Buy milk` for an open task and `[x] 2 Call mom` for a finished one; `list --pending` shows only open tasks; `done ID` marks a task finished; `remove ID` deletes it. Ids start at 1, go up by one, and are never reused, even after a task is removed. For an unknown id, `done` and `remove` print `no such task: ID` to stderr and exit with code 1.

Tasks are stored as JSON in the file named by the `TODO_FILE` environment variable, defaulting to `todo.json` in the current directory. A missing or empty file means an empty list, not a crash. Save atomically: write to a temporary file and move it into place with `os.replace`.

Document the `TODO_FILE` variable in a README.md, and add a CHANGELOG.md with a `## 0.1.0` entry. Standard library only. Do not ask questions; finish the task.
