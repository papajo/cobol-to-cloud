# 0003 — EBCDIC datasets are the canonical test data

**Status:** accepted · 2026-10-18

**Context:** CardDemo ships each seed dataset twice: `app/data/EBCDIC/*.PS` (fixed-length, cp037) and `app/data/ASCII/*.txt`. Decoding the EBCDIC files with cp037 and comparing record-by-record (ref 59cc6c2) shows they are **not** equivalent:

| Dataset | Record | EBCDIC | ASCII |
|---|---|---|---|
| ACCTDATA | 49 (idx 48) | `ACCT-GROUP-ID = ZEROAPR` | `A000000000` |
| DISCGRP | 34 (idx 33) | `DEFAULT 07 0001` rate `00150{` (+15.00) | `00000{` (0.00) |

All other records in the 9 seed files match. Both diffs feed `INTCALC` (CBACT04C) directly: interest for that account/category changes, so golden output depends on which copy is loaded.

**Decision:** EBCDIC `.PS` files are the source of truth (they are what the mainframe JCL loads via IDCAMS REPRO). They are converted with `migration/ebcdic2ascii.py` (cp037, fixed LRECL, refuses binary layouts) and the oracle is compiled with `-fsign=EBCDIC` so signed zoned overpunch (`{`, `A`–`I`, `}`, `J`–`R`) is interpreted as on z/OS. `app/data/ASCII` is not used.

**Consequences:**
- Golden INTCALC output includes the ZEROAPR path, which the ASCII data never exercises — better coverage.
- `EXPORT.DATA.PS` (CVEXPORT has COMP-3) needs a field-level converter; deferred with CBIMPORT/CBEXPORT.
- Worth reporting upstream (aws-samples/aws-mainframe-modernization-carddemo) as a data drift issue.
