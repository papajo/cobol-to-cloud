#!/usr/bin/env python3
"""Independent business check for POSTTRAN (CBTRN02C), not derived from the COBOL:
for every account, balance_after == balance_before + Σ amounts of its non-rejected daily transactions.

Decodes raw records with its own overpunch logic (z/OS convention), so it validates the oracle's sign
handling too. Works on any POSTTRAN output dir laid out like golden/POSTTRAN (legacy golden or modern run).
Usage: posttran_reconcile.py [RESULT_DIR=golden/POSTTRAN] [SEED_DIR=out/seed]
"""
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

POS, NEG = "{ABCDEFGHI", "}JKLMNOPQR"
P = "AWS.M2.CARDDEMO."


def zoned(s, scale):
    last, sign = s[-1], 1
    if last.isdigit():
        d = last
    elif last in POS:
        d = str(POS.index(last))
    else:
        d, sign = str(NEG.index(last)), -1
    return sign * Decimal(s[:-1] + d).scaleb(-scale)


def records(path, lrecl):
    b = Path(path).read_bytes()
    if len(b) % lrecl:
        sys.exit(f"{path}: size {len(b)} not a multiple of {lrecl}")
    return [b[i:i + lrecl].decode("latin-1") for i in range(0, len(b), lrecl)]


def main(result=Path("golden/POSTTRAN"), seed=Path("out/seed")):
    dal = records(seed / f"{P}DALYTRAN.PS", 350)                    # CVTRA06Y
    rejf = sorted((result / "data").glob(f"{P}DALYREJS.G*"))
    rej = {r[:16] for r in records(rejf[-1], 430)} if rejf else set()  # 350 tran + 80 reason trailer
    xref = {r[:16]: r[25:36] for r in records(seed / f"{P}CARDXREF.PS", 50)}          # CVACT03Y card→acct
    before = {r[:11]: zoned(r[12:24], 2) for r in records(seed / f"{P}ACCTDATA.PS", 300)}  # CVACT01Y
    after = {r[:11]: zoned(r[12:24], 2) for r in records(result / "vsam" / f"{P}ACCTDATA.VSAM.KSDS", 300)}
    posted = defaultdict(Decimal)
    for t in dal:
        if t[:16] not in rej:
            posted[xref[t[262:278]]] += zoned(t[132:143], 2)       # TRAN-AMT S9(9)V99 @132, CARD-NUM @262
    bad = [a for a in before if before[a] + posted[a] != after.get(a)]
    print(f"accounts={len(before)} posted={len(dal) - len(rej)} rejected={len(rej)} total={sum(posted.values())}")
    if bad:
        for a in bad[:10]:
            print(f"  MISMATCH acct {a}: before {before[a]} + posted {posted[a]} != after {after.get(a)}")
        sys.exit(1)
    print("OK: all account balances reconcile")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:3]))
