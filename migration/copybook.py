#!/usr/bin/env python3
"""COBOL copybook → record layout (offsets, lengths, types). The single source for DDL, loaders and Java codecs.

Supports: level numbers, group items, PIC X/A/9 with S and V, USAGE DISPLAY / COMP-3 (PACKED-DECIMAL) /
COMP / BINARY, FILLER (numbered), 88-levels (skipped). REDEFINES and OCCURS raise — layouts that need them
(CVEXPORT) are out of scope and must not be modelled silently wrong.

Layout JSON:
  {copybook, record, lrecl, fields: [{name, column, offset, length, kind, digits, scale, pic, filler}],
   groups: {GROUP-NAME: [offset, length]}}
kind: X (alphanumeric) | 9 (unsigned zoned) | S9 (signed zoned, overpunch) | P (packed) | B (binary)

Usage: copybook.py CPYFILE [--lrecl N]   → prints layout JSON
"""
import json, re, sys
from pathlib import Path


def statements(text):
    """Fixed-format source → period-terminated statements (cols 8-72, comments dropped)."""
    buf = []
    for raw in text.expandtabs(8).splitlines():
        if len(raw) > 6 and raw[6] in "*/":
            continue
        buf.append(raw[7:72] if len(raw) > 7 else "")
    for st in re.split(r"\.\s*(?:\n|$)", "\n".join(buf)):
        st = " ".join(st.split())
        if st:
            yield st


def parse_pic(pic):
    p = re.sub(r"(\w)\((\d+)\)", lambda m: m.group(1) * int(m.group(2)), pic.upper())
    if re.fullmatch(r"[XA]+", p):
        return {"kind": "X", "digits": None, "scale": 0, "chars": len(p)}
    m = re.fullmatch(r"(S?)(9+)(?:V(9*))?", p)
    if not m:
        raise ValueError(f"unsupported PIC {pic}")
    intd, dec = len(m.group(2)), len(m.group(3) or "")
    return {"kind": "S9" if m.group(1) else "9", "digits": intd + dec, "scale": dec, "chars": intd + dec}


def storage_length(pt, usage):
    if pt["kind"] == "X" or usage == "DISPLAY":
        return pt["chars"]
    if usage == "COMP-3":
        return pt["digits"] // 2 + 1
    if usage == "BINARY":
        return 2 if pt["digits"] <= 4 else 4 if pt["digits"] <= 9 else 8
    raise ValueError(usage)


def parse(path, lrecl=None):
    items, filler_n = [], 0
    for st in statements(Path(path).read_text(errors="replace")):
        m = re.match(r"(\d{2})\s+([\w-]+)(.*)", st)
        if not m:
            continue
        level, name, rest = int(m.group(1)), m.group(2).upper(), m.group(3).upper()
        if level == 88:
            continue
        if re.search(r"\bREDEFINES\b|\bOCCURS\b", rest):
            raise NotImplementedError(f"{path}: {name} uses REDEFINES/OCCURS — not supported by this generator")
        pic = re.search(r"\bPIC(?:TURE)?\s+(?:IS\s+)?(\S+)", rest)
        usage = "DISPLAY"
        if re.search(r"\bCOMP-3\b|\bPACKED-DECIMAL\b", rest):
            usage = "COMP-3"
        elif re.search(r"\bCOMP(?:-4|-5)?\b|\bBINARY\b", rest):
            usage = "BINARY"
        is_filler = name == "FILLER"
        if is_filler:
            filler_n += 1
            name = f"FILLER-{filler_n}"
        items.append({"level": level, "name": name, "pic": pic.group(1) if pic else None,
                      "usage": usage, "filler": is_filler})

    record, fields, groups, stack, off = None, [], {}, [], 0
    for it in items:
        while stack and stack[-1][0] >= it["level"]:
            lvl, gname, start = stack.pop()
            groups[gname] = [start, off - start]
        if it["pic"] is None:  # group item
            if record is None:
                record = it["name"]
            stack.append((it["level"], it["name"], off))
            continue
        pt = parse_pic(it["pic"])
        ln = storage_length(pt, it["usage"])
        kind = {"COMP-3": "P", "BINARY": "B"}.get(it["usage"], pt["kind"]) if pt["kind"] != "X" else "X"
        fields.append({"name": it["name"], "column": it["name"].lower().replace("-", "_"), "offset": off,
                       "length": ln, "kind": kind, "digits": pt["digits"], "scale": pt["scale"],
                       "pic": it["pic"], "filler": it["filler"]})
        off += ln
    while stack:
        lvl, gname, start = stack.pop()
        groups[gname] = [start, off - start]
    if lrecl is not None and off != lrecl:
        raise ValueError(f"{path}: layout length {off} != LRECL {lrecl}")
    groups.pop(record, None)
    return {"copybook": Path(path).stem.upper(), "record": record, "lrecl": off, "fields": fields, "groups": groups}


if __name__ == "__main__":
    lrecl = int(sys.argv[sys.argv.index("--lrecl") + 1]) if "--lrecl" in sys.argv else None
    print(json.dumps(parse(sys.argv[1], lrecl), indent=1))
