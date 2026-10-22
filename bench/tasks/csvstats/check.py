"""Hidden checker for the csvstats task. Usage: python3 -I check.py OUTPUT_DIR"""
import importlib.util
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


def load():
    spec = importlib.util.spec_from_file_location("csvstats", os.path.join(OUT, "csvstats.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def csv(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    f.write(text)
    f.close()
    return f.name


m = load() if os.path.exists(os.path.join(OUT, "csvstats.py")) else None
basic = csv("name,v\na,1\nb,2\nc,3\nd,10\n")


@check("R1", "returns exactly count/mean/median/min/max")
def _():
    return set(m.summarize(basic, "v")) == {"count", "mean", "median", "min", "max"}


@check("R2", "blank and non-numeric cells are skipped")
def _():
    r = m.summarize(csv("v\n1\n\nabc\n3\n"), "v")
    return r["count"] == 2 and r["min"] == 1 and r["max"] == 3


@check("R3", "even count: median averages the two middle values")
def _():
    return m.summarize(basic, "v")["median"] == 2.5


@check("R4", "mean rounded to 2 decimals")
def _():
    return m.summarize(csv("v\n1\n1\n2\n"), "v")["mean"] == 1.33


@check("R5", "no numeric values: count 0, others None")
def _():
    r = m.summarize(csv("v\nx\n\n"), "v")
    return r == {"count": 0, "mean": None, "median": None, "min": None, "max": None}


@check("R6", "missing column raises KeyError naming the column")
def _():
    try:
        m.summarize(basic, "nope_col")
    except KeyError as e:
        return "nope_col" in str(e)
    return False


@check("R7", "CLI prints JSON with sorted keys")
def _():
    p = subprocess.run([sys.executable, os.path.join(OUT, "csvstats.py"), basic, "v"],
                       capture_output=True, text=True, timeout=30)
    keys = re.findall(r'"(\w+)"\s*:', p.stdout)
    return p.returncode == 0 and json.loads(p.stdout)["count"] == 4 and keys == sorted(keys)


@check("R8", "CLI missing column: stderr message, empty stdout, exit 2")
def _():
    p = subprocess.run([sys.executable, os.path.join(OUT, "csvstats.py"), basic, "nope_col"],
                       capture_output=True, text=True, timeout=30)
    return m is not None and p.returncode == 2 and p.stdout.strip() == "" and p.stderr.strip() != ""


@check("R9", "README has a Usage section with an example command")
def _():
    t = open(os.path.join(OUT, "README.md")).read()
    return re.search(r"^#+\s*Usage", t, re.M | re.I) and "csvstats.py" in t.split("sage", 1)[1]


@check("R10", "test_csvstats.py has >=3 tests and passes under unittest")
def _():
    t = open(os.path.join(OUT, "test_csvstats.py")).read()
    p = subprocess.run([sys.executable, "-m", "unittest", "test_csvstats"], cwd=OUT,
                       capture_output=True, text=True, timeout=120)
    return len(re.findall(r"^\s*def test", t, re.M)) >= 3 and p.returncode == 0


print(json.dumps(results))
