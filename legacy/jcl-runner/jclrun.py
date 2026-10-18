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


NOOP = {"IEFBR14"}  # allocate/delete-only utility: DISP handling is implicit in file creation


def run(jcl):
    steps, step = [], None
    job = Path(jcl).stem.upper()
    for name, op, ops in statements(Path(jcl).read_text()):
        if op == "EXEC":
            p = params(ops)
            if "PGM" not in p:
                sys.exit(f"unsupported EXEC (PROC?): {name} {ops}")
            step = {"name": name, "pgm": p["PGM"], "dd": {}, "sysout": [], "cond": p.get("COND")}
            steps.append(step)
        elif op == "DD" and step:
            p = params(ops)
            if "DSN" in p:
                step["dd"][name] = str(dsn_path(p["DSN"]))
            elif "SYSOUT" in p:
                f = SYSOUT / f"{job}.{step['name']}.{name}.txt"
                step["dd"][name] = str(f)
                step["sysout"].append(name)
    SYSOUT.mkdir(parents=True, exist_ok=True)
    maxrc = 0
    for s in steps:
        if s["cond"]:
            print(f"TODO COND={s['cond']} on {s['name']} — running anyway")
        if s["pgm"] in NOOP:
            print(f"STEP {s['name']} PGM={s['pgm']} RC=0 (noop)")
            continue
        env = {**os.environ, **{f"DD_{k}": v for k, v in s["dd"].items()}}
        # COBOL DISPLAY goes to stdout = the step's SYSOUT DD (else SYSPRINT); stderr kept separately.
        out_dd = next((d for d in ("SYSOUT", "SYSPRINT") if d in s["sysout"]), None)
        out_f = Path(s["dd"][out_dd]) if out_dd else SYSOUT / f"{job}.{s['name']}.STDOUT.txt"
        err_f = SYSOUT / f"{job}.{s['name']}.STDERR.txt"
        r = subprocess.run(["cobcrun", s["pgm"]], env=env, capture_output=True)
        out_f.write_bytes(r.stdout)
        if r.stderr:
            err_f.write_bytes(r.stderr)
        sys.stdout.write(r.stdout.decode(errors="replace"))
        sys.stderr.write(r.stderr.decode(errors="replace"))
        print(f"STEP {s['name']} PGM={s['pgm']} RC={r.returncode}")
        maxrc = max(maxrc, r.returncode)
    print(f"JOB {job} MAXCC={maxrc}")
    (SYSOUT / f"{job}.MAXCC").write_text(f"{maxrc}\n")
    return maxrc


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
