#!/usr/bin/env python3
"""Convert a fixed-length EBCDIC (cp037) dataset to fixed-length ASCII records for the GnuCOBOL oracle.

Only valid for all-DISPLAY layouts (signed zoned overpunch survives cp037 as {,A-I,},J-R; compile with -fsign=EBCDIC).
Refuses copybooks containing COMP/COMP-3/BINARY — those need a field-level converter.
Usage: ebcdic2ascii.py IN.PS LRECL OUT [--copybook X.cpy] [--newline]
"""
import argparse, re, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("lrecl", type=int); ap.add_argument("dst")
ap.add_argument("--copybook"); ap.add_argument("--newline", action="store_true", help="LINE SEQUENTIAL output")
a = ap.parse_args()

if a.copybook and re.search(r"\bCOMP(?:-\d)?\b|\bBINARY\b|PACKED-DECIMAL", Path(a.copybook).read_text().upper()):
    sys.exit(f"{a.copybook}: binary/packed fields present; byte-level cp037 decode would corrupt them")

raw = Path(a.src).read_bytes()
if len(raw) % a.lrecl:
    sys.exit(f"{a.src}: size {len(raw)} not a multiple of LRECL {a.lrecl}")
recs = [raw[i:i + a.lrecl].decode("cp037") for i in range(0, len(raw), a.lrecl)]
# X'00' (LOW-VALUES) is legal in DISPLAY data and identical in both encodings; other controls mean binary fields.
bad = [i for i, r in enumerate(recs) if any(ord(c) > 126 or (0 < ord(c) < 32) for c in r)]
if bad:
    sys.exit(f"{a.src}: non-printable chars after decode in records {bad[:5]} (binary fields?)")
Path(a.dst).parent.mkdir(parents=True, exist_ok=True)
with open(a.dst, "w", encoding="ascii", newline="") as f:
    for r in recs:
        f.write(r + ("\n" if a.newline else ""))
print(f"{a.src} → {a.dst}: {len(recs)} records × {a.lrecl}")
