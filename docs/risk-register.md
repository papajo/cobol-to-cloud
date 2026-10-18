# Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Status |
|---|---|---|---|---|---|---|
| R1 | COMP-3 rounding/truncation mismatch (ROUNDED vs truncate) | H | H | Codec tests per PIC; BigDecimal only; rounding mode from source | — | open |
| R2 | EBCDIC vs ASCII collation changes key/SORT order | H | H | EbcdicCollator; decide oracle encoding in ADR | — | open |
| R3 | VSAM alt-index / duplicate-key browse order not reproducible in SQL | M | H | Explicit ORDER BY on key + RBA surrogate | — | open |
| R4 | GDG generations and restart semantics | M | M | Map to dated file sets + Spring Batch job repository | — | open |
| R5 | GnuCOBOL diverges from Enterprise COBOL | M | M | Log in build-log; patch only via documented compat flags | — | open |
| R6 | 2-digit year windowing / Julian dates | M | M | Pinned business date; date-util tests | — | open |
| R7 | CardDemo ASCII seed data drifted from EBCDIC (ACCTDATA rec 49 group, DISCGRP rec 34 rate) | **realized** | H | ADR 0003: EBCDIC canonical; `make seed-data` | — | mitigated |
| R8 | Signed zoned (overpunch) is the dominant numeric type (14 fields incl. all ACCT balances), not COMP-3 (4, export only) | H | H | `-fsign=EBCDIC` on oracle; `codec.ZonedDecimal` tests | — | mitigated |
| R9 | VSAM alternate index path (CARDXREF AIX, used by INTCALC) | M | M | Secondary index in GnuCOBOL indexed file + SQL index; verify read order | — | open |
