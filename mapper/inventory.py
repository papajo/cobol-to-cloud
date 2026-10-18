#!/usr/bin/env python3
"""Phase 0 inventory: scan CardDemo app/ and emit docs/inventory.md + docs/inventory.json.

Edges captured: JOB → STEP → PGM/PROC/UTILITY, STEP DD → DSN (DISP, GDG),
PGM → COPY, PGM → CALL, PGM SELECT → DD (ORGANIZATION/ACCESS), EXEC SQL/CICS density.
Usage: inventory.py vendor/carddemo/app docs/
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

UTILITIES = {"IDCAMS", "SORT", "IEFBR14", "IEBGENER", "IKJEFT01", "IKJEFT1B", "FTP", "DFSRRC00",
             "IEBCOPY", "ICEGENER", "SYNCSORT", "DFHCSDUP", "SDSF", "TXT2PDF", "COBSWAIT"}


# ---------- JCL ----------
def jcl_statements(text):
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.startswith("//") or line.startswith("//*"):
            continue
        body = line[2:72].rstrip()
        if cur is not None and body[:1] == " " and not re.match(r"\s+(EXEC|DD|JOB|PROC|PEND|SET|IF|ENDIF|ELSE|INCLUDE|JCLLIB)\b", body):
            cur[2] += body.strip()
            continue
        if cur:
            yield cur
        m = re.match(r"(\S*)\s+(\S+)\s*(.*)", body)
        cur = [m.group(1), m.group(2), m.group(3).strip()] if m else None
    if cur:
        yield cur


def kv(s):
    return {k.upper(): v for k, v in re.findall(r"(\w+)=(\([^()]*(?:\([^()]*\))*[^()]*\)|'[^']*'|[^,\s]+)", s)}


def parse_jcl(path):
    job = {"member": path.stem.upper(), "file": path.name, "steps": [], "comment": ""}
    text = path.read_text(errors="replace")
    for line in text.splitlines():
        if line.startswith("//*") and re.search(r"[a-z]", line) and "Copyright" not in line and "License" not in line \
                and "WITHOUT" not in line and "express" not in line and "may " not in line and "Ver:" not in line \
                and "apache" not in line.lower() and "Unless" not in line and "AS IS" not in line and "Rights" not in line:
            job["comment"] += line[3:].strip(" *") + " "
    step = None
    for name, op, ops in jcl_statements(text):
        if op == "EXEC":
            p = kv(ops)
            pgm = p.get("PGM")
            proc = p.get("PROC") or (None if pgm else ops.split(",")[0].strip())
            step = {"name": name, "pgm": pgm, "proc": proc, "parm": p.get("PARM", "").strip("'"),
                    "cond": p.get("COND"), "dd": []}
            job["steps"].append(step)
        elif op == "DD" and step is not None:
            p = kv(ops)
            dsn = p.get("DSN") or p.get("DSNAME")
            if dsn:
                step["dd"].append({"dd": name or "(concat)", "dsn": dsn, "disp": p.get("DISP", "SHR"),
                                   "gdg": bool(re.search(r"\([+-]?\d+\)$", dsn))})
            elif "SYSOUT" in p:
                step["dd"].append({"dd": name, "dsn": None, "sysout": True})
            elif ops.startswith("*") or "DATA" in ops:
                step["dd"].append({"dd": name, "dsn": None, "instream": True})
    job["comment"] = job["comment"].strip()
    return job


# ---------- COBOL ----------
def cobol_lines(path):
    for raw in path.read_text(errors="replace").splitlines():
        if len(raw) > 6 and raw[6] in "*/":
            continue
        yield raw[7:72] if len(raw) > 7 else ""


def parse_cobol(path):
    code = [l for l in cobol_lines(path) if l.strip()]
    text = "\n".join(code)
    up = text.upper()
    selects = []
    for m in re.finditer(r"SELECT\s+([\w-]+)\s+ASSIGN\s+TO\s+([\w-]+)(.*?)\.", up, re.S):
        tail = m.group(3)
        org = re.search(r"ORGANIZATION\s+(?:IS\s+)?(\w+)", tail)
        acc = re.search(r"ACCESS\s+(?:MODE\s+)?(?:IS\s+)?(\w+)", tail)
        selects.append({"file": m.group(1), "dd": m.group(2),
                        "org": org.group(1) if org else "SEQUENTIAL", "access": acc.group(1) if acc else "SEQUENTIAL",
                        "open": []})
    by_file = {s["file"]: s for s in selects}
    for m in re.finditer(r"\bOPEN\s+((?:(?:INPUT|OUTPUT|I-O|EXTEND)\s+(?:[\w-]+\s*)+)+)", up):
        mode = None
        for tok in m.group(1).split():
            if tok in ("INPUT", "OUTPUT", "I-O", "EXTEND"):
                mode = tok
            elif tok in by_file and mode not in by_file[tok]["open"]:
                by_file[tok]["open"].append(mode)
    return {
        "program": path.stem.upper(),
        "file": path.name,
        "kind": "batch" if path.stem.upper().startswith("CB") else ("online" if path.stem.upper().startswith("CO") else "util"),
        "loc": len(code),
        "copies": sorted(set(re.findall(r"\bCOPY\s+([\w-]+)", up))),
        "calls": sorted(set(re.findall(r"\bCALL\s+'([\w-]+)'", up))),
        "selects": selects,
        "exec_cics": len(re.findall(r"EXEC\s+CICS", up)),
        "exec_sql": len(re.findall(r"EXEC\s+SQL", up)),
        "goto": len(re.findall(r"\bGO\s+TO\b", up)),
        "perform": len(re.findall(r"\bPERFORM\b", up)),
        "compute": len(re.findall(r"\bCOMPUTE\b", up)),
        "rounded": len(re.findall(r"\bROUNDED\b", up)),
        "comp3": len(re.findall(r"COMP-3|PACKED-DECIMAL", up)),
        "sort": len(re.findall(r"^\s*SORT\s", up, re.M)),
    }


def parse_copybook(path):
    up = "\n".join(cobol_lines(path)).upper()
    return {"copybook": path.stem.upper(), "file": path.name,
            "comp3": len(re.findall(r"COMP-3|PACKED-DECIMAL", up)),
            "zoned_signed": len([l for l in up.splitlines() if re.search(r"PIC\s+S9", l) and "COMP" not in l]),
            "redefines": len(re.findall(r"\bREDEFINES\b", up)),
            "occurs": len(re.findall(r"\bOCCURS\b", up)),
            "fields": len(re.findall(r"\bPIC\b", up))}


def complexity(job, progs):
    """Score = Σ program (LOC/100 + 2·files + 3·SQL + 5·CICS + 2·GOTO>0) + 3·GDG DDs + 2·utility steps."""
    s = 0.0
    for st in job["steps"]:
        p = progs.get(st["pgm"] or "")
        if p:
            s += p["loc"] / 100 + 2 * len(p["selects"]) + 3 * (p["exec_sql"] > 0) + 5 * (p["exec_cics"] > 0) + 2 * (p["goto"] > 0)
        elif (st["pgm"] or st["proc"] or "") in UTILITIES or st["pgm"] in UTILITIES:
            s += 2
        else:
            s += 1
        s += 3 * sum(1 for d in st["dd"] if d.get("gdg"))
    return round(s, 1)


def main(app, out):
    app, out = Path(app), Path(out)
    jobs = [parse_jcl(p) for p in sorted((app / "jcl").glob("*")) if p.suffix.lower() == ".jcl"]
    progs = {p["program"]: p for p in (parse_cobol(f) for f in sorted((app / "cbl").glob("*")) if f.suffix.lower() == ".cbl")}
    cpys = {c["copybook"]: c for c in (parse_copybook(f) for f in sorted((app / "cpy").glob("*")) if f.suffix.lower() == ".cpy")}
    procs = sorted(p.stem.upper() for p in (app / "proc").glob("*"))

    dsn_users = defaultdict(lambda: {"read": set(), "write": set()})
    pgm_jobs = defaultdict(set)
    for j in jobs:
        j["complexity"] = complexity(j, progs)
        j["utilities"] = sorted({st["pgm"] for st in j["steps"] if st["pgm"] in UTILITIES} |
                                {st["proc"] for st in j["steps"] if st["proc"]})
        j["cobol"] = sorted({st["pgm"] for st in j["steps"] if st["pgm"] in progs and progs[st["pgm"]]["kind"] == "batch"})
        for st in j["steps"]:
            if st["pgm"]:
                pgm_jobs[st["pgm"]].add(j["member"])
            prog = progs.get(st["pgm"] or "")
            dd_open = {s["dd"]: s["open"] for s in prog["selects"]} if prog else {}
            for d in st["dd"]:
                if d.get("dsn") and "LOADLIB" not in d["dsn"]:
                    base = re.sub(r"\([+-]?\d+\)$", "", d["dsn"])
                    if d["dd"] in dd_open and dd_open[d["dd"]]:
                        modes = dd_open[d["dd"]]
                        write = any(m in ("OUTPUT", "I-O", "EXTEND") for m in modes)
                    else:  # utility step or unopened DD: fall back to DISP
                        write = bool(re.search(r"NEW|MOD|OLD", d["disp"])) or d["dd"] in ("OUTDATA", "SORTOUT", "SYSUT2", "SORTOF01")
                    dsn_users[base]["write" if write else "read"].add(j["member"])
    for p in progs.values():  # programs reached only via CALL
        for callee in p["calls"]:
            if callee in progs:
                for jm in pgm_jobs.get(p["program"], []):
                    pgm_jobs[callee].add(f"{jm} (via {p['program']})")

    vsam = sorted(d for d in dsn_users if ".VSAM." in d or d.endswith(".KSDS"))
    gdg = sorted({re.sub(r"\([+-]?\d+\)$", "", d["dsn"]).replace("AWS.M2.CARDDEMO.", "")
                  for j in jobs for st in j["steps"] for d in st["dd"] if d.get("gdg")})
    batch = [p for p in progs.values() if p["kind"] == "batch"]
    online = [p for p in progs.values() if p["kind"] == "online"]
    cobol_jobs = sorted((j for j in jobs if j["cobol"]), key=lambda j: j["complexity"])

    graph = {"jobs": jobs, "programs": progs, "copybooks": cpys, "procs": procs,
             "datasets": {k: {m: sorted(v) for m, v in u.items()} for k, u in dsn_users.items()},
             "program_jobs": {k: sorted(v) for k, v in pgm_jobs.items()}}
    (out / "inventory.json").write_text(json.dumps(graph, indent=1, default=sorted) + "\n")

    L = ["# Inventory (phase 0)", "",
         "Generated by `mapper/inventory.py` from `vendor/carddemo/app` "
         f"(ref in `legacy/CARDDEMO_REF`). Do not edit by hand; re-run `make inventory`.", "",
         "## Summary", "", "| Type | Count | Notes |", "|---|---|---|",
         f"| COBOL programs (batch, CB*) | {len(batch)} | {sum(p['loc'] for p in batch)} LOC |",
         f"| COBOL programs (online, CO*) | {len(online)} | {sum(p['loc'] for p in online)} LOC; out of scope |",
         f"| COBOL programs (other) | {len(progs) - len(batch) - len(online)} | |",
         f"| Copybooks | {len(cpys)} | {sum(c['fields'] for c in cpys.values())} PIC fields, "
         f"{sum(c['comp3'] for c in cpys.values())} COMP-3, {sum(c['zoned_signed'] for c in cpys.values())} signed zoned (overpunch), "
         f"{sum(c['redefines'] for c in cpys.values())} REDEFINES, "
         f"{sum(c['occurs'] for c in cpys.values())} OCCURS |",
         f"| JCL members | {len(jobs)} | {len(cobol_jobs)} run CardDemo COBOL; rest are utility/setup |",
         f"| PROCs | {len(procs)} | {', '.join(procs)} |",
         f"| VSAM datasets (referenced) | {len(vsam)} | |",
         f"| GDG bases (referenced) | {len(gdg)} | {', '.join(gdg)} |",
         "", "## Batch programs", "",
         "| Program | LOC | Files (DD:org/access) | Copybooks | CALLs | SQL | GO TO | COMPUTE/ROUNDED | Jobs |",
         "|---|---|---|---|---|---|---|---|---|"]
    for p in sorted(batch, key=lambda p: p["program"]):
        files = "<br>".join(f"{s['dd']}:{s['org'][:3]}/{s['access'][:3]} {'/'.join(s['open'])}" for s in p["selects"])
        L.append(f"| {p['program']} | {p['loc']} | {files} | {', '.join(p['copies'])} | {', '.join(p['calls'])} | "
                 f"{p['exec_sql']} | {p['goto']} | {p['compute']}/{p['rounded']} | {', '.join(sorted(pgm_jobs.get(p['program'], []))) or '— (no JCL)'} |")
    L += ["", "## Jobs running CardDemo COBOL (migration order = ascending complexity)", "",
          "Complexity = Σ program (LOC/100 + 2·files + 3·SQL + 5·CICS + 2·[GO TO]) + 3·GDG DDs + 2·utility steps.", "",
          "| # | JCL | Steps | Programs | Utilities/PROCs | GDG | Complexity | Purpose | Golden | Migrated |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for i, j in enumerate(cobol_jobs, 1):
        g = sum(1 for st in j["steps"] for d in st["dd"] if d.get("gdg"))
        L.append(f"| {i} | {j['member']} | {len(j['steps'])} | {', '.join(j['cobol'])} | {', '.join(j['utilities'])} | "
                 f"{g} | {j['complexity']} | {j['comment'][:90]} | ☐ | ☐ |")
    L += ["", "## Utility / setup jobs (support golden env, not migrated as business logic)", "",
          "| JCL | Steps | Utilities/PROCs | Purpose |", "|---|---|---|---|"]
    for j in sorted((j for j in jobs if not j["cobol"]), key=lambda j: j["member"]):
        L.append(f"| {j['member']} | {len(j['steps'])} | {', '.join(j['utilities']) or '—'} | {j['comment'][:90]} |")
    L += ["", "## VSAM datasets", "", "| Dataset | Read by | Written by |", "|---|---|---|"]
    for d in vsam:
        u = dsn_users[d]
        L.append(f"| {d} | {', '.join(sorted(u['read']))} | {', '.join(sorted(u['write']))} |")
    L += ["", "## Copybooks with migration hazards", "",
          "| Copybook | Fields | Signed zoned | COMP-3 | REDEFINES | OCCURS |", "|---|---|---|---|---|---|"]
    for c in sorted(cpys.values(), key=lambda c: -(c["zoned_signed"] + c["comp3"] + c["redefines"] + c["occurs"])):
        if c["zoned_signed"] or c["comp3"] or c["redefines"] or c["occurs"]:
            L.append(f"| {c['copybook']} | {c['fields']} | {c['zoned_signed']} | {c['comp3']} | {c['redefines']} | {c['occurs']} |")
    (out / "inventory.md").write_text("\n".join(L) + "\n")
    print(f"jobs={len(jobs)} cobol_jobs={len(cobol_jobs)} programs={len(progs)} batch={len(batch)} copybooks={len(cpys)} vsam={len(vsam)} gdg={len(gdg)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
