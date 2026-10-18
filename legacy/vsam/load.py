#!/usr/bin/env python3
"""IDCAMS DEFINE CLUSTER/ALTERNATEINDEX + REPRO equivalent for the GnuCOBOL oracle.

Parses CardDemo's own IDCAMS JCL for KSDS definitions (KEYS, RECORDSIZE) and alternate indexes,
and REPRO INFILE→OUTFILE pairs for seed sources. For each KSDS it generates a tiny COBOL loader,
compiles it, and loads out/seed/<seed DSN> into out/legacy/data/<KSDS DSN> (BDB indexed file).
KSDS with no seed are created empty. Writes out/legacy/vsam/catalog.json.

Usage (inside c2c-legacy container): load.py [/work]
"""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/work").resolve()  # absolute: COB_FILE_PATH prefixes relative names
JCL = ROOT / "vendor/carddemo/app/jcl"
SEED = ROOT / "out/seed"
DATA = ROOT / "out/legacy/data"
WORK = ROOT / "out/legacy/vsam"
PREFIX = "AWS.M2.CARDDEMO."


def strip_jcl(text):
    """Remove sequence area (73-80) and JCL comment lines; keep in-stream SYSIN."""
    return "\n".join(l[:72] for l in text.splitlines() if not l.startswith("//*"))


def parse_catalog():
    clusters, aixes, repro = {}, [], {}
    for f in sorted(JCL.iterdir()):
        if f.suffix.lower() != ".jcl":
            continue
        text = strip_jcl(f.read_text(errors="replace"))
        flat = re.sub(r"-\s*\n", " ", text)          # IDCAMS continuation
        dd = dict(re.findall(r"^//(\w+)\s+DD\s+.*?DSN=([\w.$#@()+-]+)", re.sub(r",\s*\n//\s+", ",", text), re.M))
        for blk in re.split(r"\bDEFINE\b", flat)[1:]:
            blk = re.split(r"\n/\*|\bDEFINE\b|\bREPRO\b|\bDELETE\b|\bBLDINDEX\b|\bLISTCAT\b", blk)[0]
            name = re.search(r"NAME\(([\w.]+)\)", blk)
            keys = re.search(r"KEYS\((\d+)[ ,]+(\d+)\)", blk)
            rs = re.search(r"RECORDSIZE\((\d+)[ ,]+(\d+)\)", blk)
            if not name:
                continue
            if blk.lstrip().startswith("CLUSTER") and "INDEXED" in blk and keys and rs:
                clusters[name.group(1)] = {"dsn": name.group(1), "key_len": int(keys.group(1)),
                                           "key_off": int(keys.group(2)), "lrecl": int(rs.group(2)),
                                           "aix": [], "source_jcl": f.name}
            elif blk.lstrip().startswith(("ALTERNATEINDEX", "AIX")) and keys:
                rel = re.search(r"RELATE\(([\w.]+)\)", blk)
                aixes.append({"dsn": name.group(1), "base": rel.group(1) if rel else None,
                              "key_len": int(keys.group(1)), "key_off": int(keys.group(2)),
                              "dups": "UNIQUEKEY" not in blk or "NONUNIQUEKEY" in blk})
        for i, o in re.findall(r"REPRO\s+INFILE\((\w+)\)\s+OUTFILE\((\w+)\)", flat):
            if i in dd and o in dd:
                repro.setdefault(dd[o], []).append(dd[i])
    for a in aixes:  # same AIX may be defined in several jobs (TRANFILE, TRANIDX, TRANBKP)
        base = clusters.get(a["base"])
        if base and a["dsn"] not in {x["dsn"] for x in base["aix"]}:
            base["aix"].append(a)
    for c in clusters.values():  # seed = the flat (.PS/.INIT) REPRO source, not GDG backups
        c["seed"] = next((s for s in repro.get(c["dsn"], []) if s.endswith((".PS", ".INIT"))), None)
    return {k: v for k, v in clusters.items() if k.startswith(PREFIX)}


def loader_source(c):
    """Fixed-format COBOL: sequential IN → indexed OUT (RANDOM write, rejects duplicate keys)."""
    fields, pos, n = [], 0, 0
    spans = sorted([(c["key_off"], c["key_len"], "OUT-KEY")] +
                   [(a["key_off"], a["key_len"], f"OUT-AK{i}") for i, a in enumerate(c["aix"], 1)])
    for off, ln, nm in spans:
        if off < pos:
            raise ValueError(f"overlapping key definitions at offset {off}")
        if off > pos:
            n += 1; fields.append(f"           05  FILLER-{n}  PIC X({off - pos}).")
        fields.append(f"           05  {nm}  PIC X({ln})."); pos = off + ln
    if pos < c["lrecl"]:
        fields.append(f"           05  FILLER-T  PIC X({c['lrecl'] - pos}).")
    alt = "".join(f"\n               ALTERNATE RECORD KEY IS OUT-AK{i}" + (" WITH DUPLICATES" if a["dups"] else "")
                  for i, a in enumerate(c["aix"], 1))
    return f"""       IDENTIFICATION DIVISION.
       PROGRAM-ID. KSDSLOAD.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT IN-FILE ASSIGN TO INFILE
               ORGANIZATION IS SEQUENTIAL
               FILE STATUS IS WS-IN-ST.
           SELECT OUT-FILE ASSIGN TO OUTFILE
               ORGANIZATION IS INDEXED
               ACCESS MODE IS RANDOM
               RECORD KEY IS OUT-KEY{alt}
               FILE STATUS IS WS-OUT-ST.
       DATA DIVISION.
       FILE SECTION.
       FD  IN-FILE.
       01  IN-REC  PIC X({c['lrecl']}).
       FD  OUT-FILE.
       01  OUT-REC.
{chr(10).join(fields)}
       WORKING-STORAGE SECTION.
       01  WS-IN-ST   PIC XX.
       01  WS-OUT-ST  PIC XX.
       01  WS-EOF     PIC X VALUE 'N'.
       01  WS-CNT     PIC 9(9) VALUE 0.
       01  WS-DUP     PIC 9(9) VALUE 0.
       01  WS-HAVE-IN PIC X VALUE '{'Y' if c['seed'] else 'N'}'.
       PROCEDURE DIVISION.
           OPEN OUTPUT OUT-FILE
           IF WS-OUT-ST NOT = '00'
               DISPLAY 'OPEN OUT STATUS ' WS-OUT-ST UPON SYSERR
               MOVE 12 TO RETURN-CODE
               STOP RUN
           END-IF
           IF WS-HAVE-IN = 'Y'
               OPEN INPUT IN-FILE
               IF WS-IN-ST NOT = '00'
                   DISPLAY 'OPEN IN STATUS ' WS-IN-ST UPON SYSERR
                   MOVE 12 TO RETURN-CODE
                   STOP RUN
               END-IF
               PERFORM UNTIL WS-EOF = 'Y'
                   READ IN-FILE
                       AT END MOVE 'Y' TO WS-EOF
                       NOT AT END
                           MOVE IN-REC TO OUT-REC
                           WRITE OUT-REC
                               INVALID KEY
                                   ADD 1 TO WS-DUP
                                   DISPLAY 'DUPKEY ' OUT-KEY UPON SYSERR
                               NOT INVALID KEY
                                   ADD 1 TO WS-CNT
                           END-WRITE
                   END-READ
               END-PERFORM
               CLOSE IN-FILE
           END-IF
           CLOSE OUT-FILE
           DISPLAY 'LOADED ' WS-CNT ' DUPS ' WS-DUP
           IF WS-DUP > 0
               MOVE 8 TO RETURN-CODE
           END-IF
           GOBACK.
"""


def main():
    WORK.mkdir(parents=True, exist_ok=True); DATA.mkdir(parents=True, exist_ok=True)
    cat = parse_catalog()
    (WORK / "catalog.json").write_text(json.dumps(cat, indent=1) + "\n")
    rc_max = 0
    for dsn, c in sorted(cat.items()):
        seed = SEED / c["seed"] if c["seed"] else None
        if seed and not seed.exists():
            print(f"MISS {dsn}: seed {seed.name} not found (run make seed-data)"); rc_max = 12; continue
        stem = dsn.replace(PREFIX, "").replace(".", "_")
        src, exe = WORK / f"{stem}.cbl", WORK / stem
        try:
            src.write_text(loader_source(c))
        except ValueError as e:
            print(f"FAIL {dsn}: {e}"); rc_max = 12; continue
        r = subprocess.run(["cobc", "-x", "-std=ibm", "-o", str(exe), str(src)], capture_output=True, text=True)
        if r.returncode:
            print(f"FAIL {dsn}: compile\n{r.stderr[-800:]}"); rc_max = 12; continue
        out = DATA / dsn
        for old in DATA.glob(dsn + "*"):  # BDB keeps alt keys in sidecar files
            old.unlink()
        env = {**os.environ, "DD_INFILE": str(seed or "/dev/null"), "DD_OUTFILE": str(out)}
        r = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
        tag = "OK  " if r.returncode == 0 else "FAIL"
        aix = f" aix={[(a['key_len'], a['key_off']) for a in c['aix']]}" if c["aix"] else ""
        print(f"{tag} {dsn} keys=({c['key_len']},{c['key_off']}) lrecl={c['lrecl']}{aix} "
              f"seed={c['seed'] or '-'}: {r.stdout.strip()} {r.stderr.strip()[:300]}")
        rc_max = max(rc_max, r.returncode)
    sys.exit(rc_max)


if __name__ == "__main__":
    main()
