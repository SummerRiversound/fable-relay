"""Hidden checker for the slug task. Usage: python3 -I check.py OUTPUT_DIR"""
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys

OUT = os.path.abspath(sys.argv[1])
SRC = os.path.join(OUT, "slug.py")
results = {}


def check(rid, desc):
    def wrap(fn):
        try:
            ok = bool(fn())
        except Exception:
            ok = False
        results[rid] = {"desc": desc, "ok": ok}
    return wrap


def load():
    spec = importlib.util.spec_from_file_location("slug", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = load() if os.path.exists(SRC) else None


def public_funcs():
    tree = ast.parse(open(SRC).read())
    return [n for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]


@check("R1", "lowercase words joined by single hyphens")
def _():
    return m.slugify("Hello World") == "hello-world"


@check("R2", "accents transliterated to ASCII")
def _():
    return m.slugify("Crème Brûlée") == "creme-brulee"


@check("R3", "punctuation/whitespace runs collapse, no edge hyphens")
def _():
    return m.slugify("  --Hi!!  there-- ") == "hi-there"


@check("R4", "DEFAULT_MAX_LEN constant is 50 and is the default")
def _():
    return m.DEFAULT_MAX_LEN == 50 and len(m.slugify("word " * 30)) <= 50


@check("R5", "truncation never leaves a trailing hyphen")
def _():
    s = m.slugify("a" * 49 + " b")
    t = m.slugify("abc def", max_len=4)
    return s == "a" * 49 and t == "abc"


@check("R6", "empty result becomes n-a")
def _():
    return m.slugify("!!!") == "n-a"


@check("R7", "unique_slug returns first free -N suffix")
def _():
    return (m.unique_slug("Hello", {"hello", "hello-2"}) == "hello-3"
            and m.unique_slug("Hello", set()) == "hello")


@check("R8", "unique_slug does not mutate the given set")
def _():
    s = {"hello"}
    m.unique_slug("Hello", s)
    return s == {"hello"}


@check("R9", "every public function has a docstring")
def _():
    fs = public_funcs()
    return len(fs) >= 2 and all(ast.get_docstring(f) for f in fs)


@check("R10", "type hints on every public parameter and return, tests pass")
def _():
    fs = public_funcs()
    hinted = all(f.returns is not None and all(a.annotation is not None for a in f.args.args) for f in fs)
    p = subprocess.run([sys.executable, "-m", "unittest", "test_slug"], cwd=OUT,
                       capture_output=True, text=True, timeout=120)
    return hinted and p.returncode == 0


print(json.dumps(results))
