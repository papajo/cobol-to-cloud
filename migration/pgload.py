#!/usr/bin/env python3
"""Fixed-width records ⇄ CSV for Postgres, driven by generated layouts (migration/layouts/).

  pgload.py to-csv   DSN SRC_FILE OUT.csv     records → CSV in table column order (seq first for flat datasets)
  pgload.py from-csv DSN IN.csv OUT_FILE      CSV exported from Postgres → fixed-width records
  pgload.py reconcile DSN SRC_FILE RT_FILE    byte-compare source vs round trip (+ counts, control totals)

Decoding is strict: a 9(n) field must be digits, S9 must end in a valid overpunch, X must not contain X'00'
(Postgres text cannot hold NUL). Anything else fails with dataset/record/field — data defects are surfaced,
never coerced.
"""
import csv, hashlib, json, sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAY = ROOT / "migration/layouts"
POS, NEG = "{ABCDEFGHI", "}JKLMNOPQR"


def meta(dsn):
    d = json.loads((LAY / "datasets.json").read_text())[dsn]
    d["layout"] = json.loads((LAY / f"{d['copybook']}.json").read_text())
    return d


def records(path, lrecl):
    b = Path(path).read_bytes()
    if len(b) % lrecl:
        sys.exit(f"{path}: size {len(b)} not a multiple of LRECL {lrecl}")
    return [b[i:i + lrecl].decode("latin-1") for i in range(0, len(b), lrecl)]


def decode(f, s, where):
    if f["filler"]:
        return "\\x" + s.encode("latin-1").hex()   # bytea hex input format
    k = f["kind"]
    if k == "X":
        if "\x00" in s:
            raise ValueError(f"{where}: {f['name']} contains X'00' (LOW-VALUES) — not storable in Postgres text")
        return s
    if k == "9":
        if not s.isdigit():
            raise ValueError(f"{where}: {f['name']} PIC {f['pic']} not numeric: {s!r}")
        return str(Decimal(s).scaleb(-f["scale"]))
    if k == "S9":
        last, head = s[-1], s[:-1]
        if not head.isdigit() or not (last.isdigit() or last in POS or last in NEG):
            raise ValueError(f"{where}: {f['name']} PIC {f['pic']} bad zoned value: {s!r}")
        d, neg = (last, False) if last.isdigit() else ((str(POS.index(last)), False) if last in POS else (str(NEG.index(last)), True))
        if neg and int(head + d) == 0:
            raise ValueError(f"{where}: {f['name']} negative zero {s!r} would not round-trip")
        v = Decimal(head + d).scaleb(-f["scale"])
        return str(-v if neg else v)
    raise ValueError(f"{where}: {f['name']} kind {k} not supported in phase 4")


def encode(f, v):
    k, n = f["kind"], f["length"]
    if f["filler"]:
        b = bytes.fromhex(v[2:])
        if len(b) != n:
            raise ValueError(f"{f['name']}: bytea length {len(b)} != {n}")
        return b.decode("latin-1")
    if k == "X":
        if len(v) > n:
            raise ValueError(f"{f['name']}: value longer than {n}")
        return v.ljust(n)
    q = Decimal(v).scaleb(f["scale"])
    if q != q.to_integral_value():
        raise ValueError(f"{f['name']}: {v} has more than {f['scale']} decimals")
    i = int(q)
    if k == "9":
        if i < 0 or len(str(i)) > n:
            raise ValueError(f"{f['name']}: {v} does not fit PIC {f['pic']}")
        return str(i).zfill(n)
    if k == "S9":
        digits = str(abs(i)).zfill(n)
        if len(digits) > n:
            raise ValueError(f"{f['name']}: {v} does not fit PIC {f['pic']}")
        return digits[:-1] + (NEG if i < 0 else POS)[int(digits[-1])]
    raise ValueError(k)


def placeholder(m, r):
    """VSAM 'not empty' placeholder: whole primary key is LOW-VALUES (e.g. TRANSACT INIT record)."""
    if not m.get("drop_placeholder"):
        return False
    off, ln = m["key"]
    return r[off:off + ln] == "\x00" * ln


def source_records(m, src):
    recs = records(src, m["lrecl"])
    kept = [r for r in recs if not placeholder(m, r)]
    if len(kept) != len(recs):
        print(f"NOTE {m['table']}: {len(recs) - len(kept)} LOW-VALUES placeholder record(s) not migrated (ADR 0006)")
    return kept


def to_csv(dsn, src, out):
    m = meta(dsn)
    fields = m["layout"]["fields"]
    n = 0
    with open(out, "w", newline="", encoding="latin-1") as fh:
        w = csv.writer(fh)
        for n, r in enumerate(source_records(m, src), 1):
            row = [decode(f, r[f["offset"]:f["offset"] + f["length"]], f"{dsn} rec {n}") for f in fields]
            w.writerow(([n] if m["flat"] else []) + row)
    print(f"{m['table']}: {n} rows → {out}")


def from_csv(dsn, src, out):
    m = meta(dsn)
    fields = m["layout"]["fields"]
    with open(src, newline="", encoding="latin-1") as fh, open(out, "wb") as o:
        for row in csv.reader(fh):
            vals = row[1:] if m["flat"] else row
            o.write("".join(encode(f, v) for f, v in zip(fields, vals)).encode("latin-1"))


def reconcile(dsn, src, rt):
    m = meta(dsn)
    a, b = source_records(m, src), records(rt, m["lrecl"])
    if not m["flat"]:  # a KSDS holds records in key order; compare against the key-ordered source
        a = sorted(a)
        b_sorted = sorted(b)
        if b != b_sorted:
            print(f"FAIL {m['table']}: export not in key byte order (ORDER BY / collation mismatch)")
            return False
    money = [f for f in m["layout"]["fields"] if f["kind"] == "S9"]
    tot = lambda recs, f: sum(Decimal(decode(f, r[f["offset"]:f["offset"] + f["length"]], "")) for r in recs)
    totals = ", ".join(f"{f['column']}={tot(a, f)}" for f in money)
    if a == b == []:
        print(f"OK   {m['table']:18} rows=   0  (empty after placeholder removal)")
        return True
    if a == b:
        h = hashlib.sha256("".join(b).encode("latin-1")).hexdigest()[:12]
        print(f"OK   {m['table']:18} rows={len(b):4}  bytes identical  sha={h}  {totals}")
        return True
    print(f"FAIL {m['table']}: rows source={len(a)} roundtrip={len(b)}")
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            for f in m["layout"]["fields"]:
                s = slice(f["offset"], f["offset"] + f["length"])
                if x[s] != y[s]:
                    print(f"  rec {i + 1} {f['name']}: {x[s]!r} → {y[s]!r}")
            break
    return False


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    try:
        if cmd == "to-csv":
            to_csv(*args)
        elif cmd == "from-csv":
            from_csv(*args)
        elif cmd == "reconcile":
            sys.exit(0 if reconcile(*args) else 1)
        else:
            sys.exit(__doc__)
    except ValueError as e:
        sys.exit(f"DATA ERROR {e}")
