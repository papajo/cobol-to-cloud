#!/usr/bin/env python3
"""Generate Postgres DDL from a COBOL copybook.

Handles: level numbers, PIC X/9/S9 with V, COMP-3, COMP. TODO: REDEFINES, OCCURS, 88-levels.
Usage: copybook2ddl.py CVACT01Y.cpy TABLE_NAME
"""
import re, sys
from pathlib import Path

PIC = re.compile(r"^\s*(\d\d)\s+([\w-]+)(?:\s+PIC\s+(\S+?))?(\s+COMP(?:-3)?)?\s*\.", re.I)


def expand(pic):
    return re.sub(r"(\w)\((\d+)\)", lambda m: m.group(1) * int(m.group(2)), pic.upper())


def sqltype(pic):
    p = expand(pic)
    if "X" in p or "A" in p:
        return f"CHAR({len(p)})"
    intpart, _, dec = p.lstrip("S").partition("V")
    return f"NUMERIC({len(intpart) + len(dec)},{len(dec)})"


def ddl(cpy, table):
    cols = []
    for line in Path(cpy).read_text().splitlines():
        line = line[6:72] if len(line) > 6 else line
        m = PIC.match(line)
        if m and m.group(3) and m.group(2).upper() != "FILLER":
            cols.append(f"  {m.group(2).lower().replace('-', '_')} {sqltype(m.group(3))}")
    return f"CREATE TABLE {table} (\n" + ",\n".join(cols) + "\n);"


if __name__ == "__main__":
    print(ddl(sys.argv[1], sys.argv[2]))
