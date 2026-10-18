#!/usr/bin/env python3
"""IDCAMS REPRO-out equivalent: unload KSDS (BDB indexed) to flat fixed-length records in primary-key order.

BDB files are not byte-stable, so goldens hash these unloads instead. Uses out/legacy/vsam/catalog.json
(written by load.py). Unloads every cataloged KSDS present in out/legacy/data → out/legacy/unload/<DSN>.

Usage (inside c2c-legacy container): unload.py [/work]
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/work").resolve()
DATA = ROOT / "out/legacy/data"
WORK = ROOT / "out/legacy/vsam"
OUT = ROOT / "out/legacy/unload"
PREFIX = "AWS.M2.CARDDEMO."


def source(c):
    pre, key, post = c["key_off"], c["key_len"], c["lrecl"] - c["key_off"] - c["key_len"]
    rec = []
    if pre:
        rec.append(f"           05  FILLER-P  PIC X({pre}).")
    rec.append(f"           05  IN-KEY    PIC X({key}).")
    if post:
        rec.append(f"           05  FILLER-T  PIC X({post}).")
    return f"""       IDENTIFICATION DIVISION.
       PROGRAM-ID. KSDSUNLD.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT IN-FILE ASSIGN TO INFILE
               ORGANIZATION IS INDEXED
               ACCESS MODE IS SEQUENTIAL
               RECORD KEY IS IN-KEY
               FILE STATUS IS WS-IN-ST.
           SELECT OUT-FILE ASSIGN TO OUTFILE
               ORGANIZATION IS SEQUENTIAL
               FILE STATUS IS WS-OUT-ST.
       DATA DIVISION.
       FILE SECTION.
       FD  IN-FILE.
       01  IN-REC.
{chr(10).join(rec)}
       FD  OUT-FILE.
       01  OUT-REC  PIC X({c['lrecl']}).
       WORKING-STORAGE SECTION.
       01  WS-IN-ST   PIC XX.
       01  WS-OUT-ST  PIC XX.
       01  WS-EOF     PIC X VALUE 'N'.
       01  WS-CNT     PIC 9(9) VALUE 0.
       PROCEDURE DIVISION.
           OPEN INPUT IN-FILE
           IF WS-IN-ST NOT = '00'
               DISPLAY 'OPEN IN STATUS ' WS-IN-ST UPON SYSERR
               MOVE 12 TO RETURN-CODE
               STOP RUN
           END-IF
           OPEN OUTPUT OUT-FILE
           PERFORM UNTIL WS-EOF = 'Y'
               READ IN-FILE NEXT
                   AT END MOVE 'Y' TO WS-EOF
                   NOT AT END
                       WRITE OUT-REC FROM IN-REC
                       ADD 1 TO WS-CNT
               END-READ
           END-PERFORM
           CLOSE IN-FILE OUT-FILE
           DISPLAY 'UNLOADED ' WS-CNT
           GOBACK.
"""


def main():
    cat = json.loads((WORK / "catalog.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    rc_max = 0
    for dsn, c in sorted(cat.items()):
        if not (DATA / dsn).exists():
            continue
        stem = "U_" + dsn.replace(PREFIX, "").replace(".", "_")
        src, exe = WORK / f"{stem}.cbl", WORK / stem
        src.write_text(source(c))
        r = subprocess.run(["cobc", "-x", "-std=ibm", "-o", str(exe), str(src)], capture_output=True, text=True)
        if r.returncode:
            print(f"FAIL {dsn}: compile\n{r.stderr[-600:]}"); rc_max = 12; continue
        env = {**os.environ, "DD_INFILE": str(DATA / dsn), "DD_OUTFILE": str(OUT / dsn)}
        r = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
        print(f"{'OK  ' if r.returncode == 0 else 'FAIL'} {dsn}: {r.stdout.strip()} {r.stderr.strip()[:200]}")
        rc_max = max(rc_max, r.returncode)
    sys.exit(rc_max)


if __name__ == "__main__":
    main()
