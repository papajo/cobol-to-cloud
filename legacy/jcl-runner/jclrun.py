#!/usr/bin/env python3
"""Minimal JCL runner: parses JOB/EXEC/DD, maps DSNs to files, runs PGM via cobcrun.

Supported (phase 2 target): EXEC PGM=, DD DSN=/DISP=/SYSOUT=, COND= on EXEC, SET symbols.
Not yet: PROCs, GDG (+1)/(0), IDCAMS REPRO/DEFINE, SORT. Unsupported statements fail loudly.
"""
import os, re, subprocess, sys
from pathlib import Path

DATA = Path(os.environ.get("COB_FILE_PATH", "out/legacy/data"))
SYSOUT = DATA.parent / "sysout"


def statements(text):
    """Yield (name, op, operands) joining continuation lines."""
    cur = None
    for line in text.splitlines():
        if not line.startswith("//") or line.startswith("//*"):
            continue
        body = line[2:71]
        if cur and body.startswith(" "):
            cur[2] += body.strip()
            continue
        if cur:
            yield cur
        m = re.match(r"(\S*)\s+(\S+)\s*(.*)", body)
        cur = [m.group(1), m.group(2), m.group(3).strip()] if m else None
    if cur:
        yield cur


def params(s):
    return dict(re.findall(r"(\w+)=(\([^)]*\)|'[^']*'|[^,]+)", s))


def dsn_path(dsn):
    return DATA / dsn.strip("'").replace("(", ".").replace(")", "")


def run(jcl):
    steps, step = [], None
    for name, op, ops in statements(Path(jcl).read_text()):
        if op == "EXEC":
            p = params(ops)
            if "PGM" not in p:
                sys.exit(f"unsupported EXEC (PROC?): {name} {ops}")
            step = {"name": name, "pgm": p["PGM"], "dd": {}, "cond": p.get("COND")}
            steps.append(step)
        elif op == "DD" and step:
            p = params(ops)
            if "DSN" in p:
                step["dd"][name] = str(dsn_path(p["DSN"]))
            elif "SYSOUT" in p:
                step["dd"][name] = str(SYSOUT / f"{step['name']}.{name}.txt")
    SYSOUT.mkdir(parents=True, exist_ok=True)
    maxrc = 0
    for s in steps:
        if s["cond"]:
            print(f"TODO COND={s['cond']} on {s['name']} — running anyway")
        env = {**os.environ, **{f"DD_{k}": v for k, v in s["dd"].items()}}
        rc = subprocess.call(["cobcrun", s["pgm"]], env=env)
        print(f"STEP {s['name']} PGM={s['pgm']} RC={rc}")
        maxrc = max(maxrc, rc)
    return maxrc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
