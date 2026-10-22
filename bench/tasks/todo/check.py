"""Hidden checker for the todo task. Usage: python3 -I check.py OUTPUT_DIR"""
import json
import os
import re
import subprocess
import sys
import tempfile

OUT = os.path.abspath(sys.argv[1])
results = {}


def check(rid, desc):
    def wrap(fn):
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        results[rid] = {"desc": desc, "ok": ok}
    return wrap


def session(env_file=True):
    """Fresh temp cwd; returns a runner for `python3 -m todo ...`."""
    cwd = tempfile.mkdtemp()
    env = dict(os.environ, PYTHONPATH=OUT)
    env.pop("TODO_FILE", None)
    if env_file:
        env["TODO_FILE"] = os.path.join(cwd, "store.json")

    def run(*args):
        return subprocess.run([sys.executable, "-m", "todo", *args], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=30)
    run.cwd = cwd
    return run


@check("R1", "add prints 'added N'")
def _():
    r = session()
    return r("add", "Buy milk").stdout.strip() == "added 1" and r("add", "x").stdout.strip() == "added 2"


@check("R2", "ids never reused after remove")
def _():
    r = session()
    r("add", "a"); r("add", "b"); r("remove", "2")
    return r("add", "c").stdout.strip() == "added 3"


@check("R3", "list format '[ ] 1 text' / '[x] 2 text' in id order")
def _():
    r = session()
    r("add", "Buy milk"); r("add", "Call mom"); r("done", "2")
    return r("list").stdout.strip().splitlines() == ["[ ] 1 Buy milk", "[x] 2 Call mom"]


@check("R4", "list --pending shows only open tasks")
def _():
    r = session()
    r("add", "a"); r("add", "b"); r("done", "1")
    return r("list", "--pending").stdout.strip().splitlines() == ["[ ] 2 b"]


@check("R5", "unknown id: 'no such task: ID' on stderr, exit 1 (done and remove)")
def _():
    r = session()
    r("add", "a")
    d, x = r("done", "7"), r("remove", "7")
    return all(p.returncode == 1 and "no such task: 7" in p.stderr for p in (d, x))


@check("R6", "TODO_FILE honoured; default todo.json in cwd")
def _():
    r = session()
    r("add", "a")
    d = session(env_file=False)
    d("add", "a")
    return os.path.exists(os.path.join(r.cwd, "store.json")) and os.path.exists(os.path.join(d.cwd, "todo.json"))


@check("R7", "storage in todo/store.py, saved via os.replace")
def _():
    return "os.replace" in open(os.path.join(OUT, "todo", "store.py")).read()


@check("R8", "missing or empty file is an empty list")
def _():
    r = session()
    missing = r("list")
    open(os.path.join(r.cwd, "store.json"), "w").close()
    empty = r("list")
    return missing.returncode == 0 and empty.returncode == 0 and r("add", "a").stdout.strip() == "added 1"


@check("R9", "README documents TODO_FILE")
def _():
    return "TODO_FILE" in open(os.path.join(OUT, "README.md")).read()


@check("R10", "CHANGELOG.md has a '## 0.1.0' entry")
def _():
    return re.search(r"^##\s*\[?0\.1\.0", open(os.path.join(OUT, "CHANGELOG.md")).read(), re.M)


print(json.dumps(results))
