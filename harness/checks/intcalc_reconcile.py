#!/usr/bin/env python3
"""Independent business check for INTCALC (CBACT04C), run after POSTTRAN, not derived from the COBOL:
  monthly interest per category balance = TRUNC(bal × rate / 1200, 2)   (COMPUTE without ROUNDED)
  rate = DISCGRP[acct group, type, cat], falling back to DISCGRP['DEFAULT', type, cat]
  account balance += Σ its interest; cycle credit/debit reset to 0; one SYSTRAN record per non-zero rate.

Inputs: POSTTRAN result (its TCATBALF + ACCTDATA are INTCALC's inputs) and seed DISCGRP.
Known defect R17 (CardDemo source): CBACT04C's final control-break update sits in an ELSE branch that is
unreachable under PERFORM UNTIL END-OF-FILE = 'Y', so the LAST account (in TCATBAL key order) gets its
interest written to SYSTRAN but never applied to its balance. Parity requires reproducing it; this check
accepts exactly that deviation by default and reports it. --strict checks intended behaviour (for the fix).

Usage: intcalc_reconcile.py [RESULT=golden/INTCALC] [PRE=golden/POSTTRAN] [SEED=out/seed] [--strict]
"""
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_DOWN
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
    return [b[i:i + lrecl].decode("latin-1") for i in range(0, len(b), lrecl)]


def main(result=Path("golden/INTCALC"), pre=Path("golden/POSTTRAN"), seed=Path("out/seed")):
    tcat = records(pre / "vsam" / f"{P}TCATBALF.VSAM.KSDS", 50)                        # CVTRA01Y
    acct0 = {r[:11]: r for r in records(pre / "vsam" / f"{P}ACCTDATA.VSAM.KSDS", 300)}  # CVACT01Y
    acct1 = {r[:11]: r for r in records(result / "vsam" / f"{P}ACCTDATA.VSAM.KSDS", 300)}
    disc = {r[:16]: zoned(r[16:22], 2) for r in records(seed / f"{P}DISCGRP.PS", 50)}  # CVTRA02Y
    systran = sorted((result / "data").glob(f"{P}SYSTRAN.G*"))
    nsys = len(records(systran[-1], 350)) if systran else 0

    interest, expect_tx = defaultdict(Decimal), 0
    for t in tcat:
        acct, typ, cat, bal = t[:11], t[11:13], t[13:17], zoned(t[17:28], 2)
        group = acct0[acct][112:122]
        rate = disc.get(group + typ + cat, disc.get("DEFAULT   " + typ + cat, Decimal(0)))
        if rate != 0:
            interest[acct] += (bal * rate / 1200).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            expect_tx += 1
    bad = []
    for a, r0 in acct0.items():
        r1 = acct1[a]
        if a in {t[:11] for t in tcat}:
            ok = (zoned(r1[12:24], 2) == zoned(r0[12:24], 2) + interest[a]
                  and zoned(r1[78:90], 2) == 0 and zoned(r1[90:102], 2) == 0)
        else:
            ok = r1 == r0
        if not ok:
            bad.append(a)
    print(f"tcatbal={len(tcat)} interest_txns expected={expect_tx} written={nsys} "
          f"total_interest={sum(interest.values())} accounts_mismatched={len(bad)}")
    for a in bad[:10]:
        print(f"  MISMATCH acct {a}: before {zoned(acct0[a][12:24], 2)} + int {interest[a]} "
              f"!= after {zoned(acct1[a][12:24], 2)} (cyc cr/db {acct1[a][78:90]}/{acct1[a][90:102]})")
    last = sorted({t[:11] for t in tcat})[-1]
    if not STRICT and bad == [last] and acct1[last] == acct0[last]:
        print(f"KNOWN DEFECT R17: last account {last} interest {interest[last]} written to SYSTRAN, not applied")
        bad = []
    if bad or expect_tx != nsys:
        sys.exit(1)
    print("OK: interest and account balances reconcile" + (" (strict)" if STRICT else " (with known defect R17)"))


STRICT = "--strict" in sys.argv
if __name__ == "__main__":
    main(*(Path(a) for a in [x for x in sys.argv[1:] if not x.startswith("--")][:3]))
