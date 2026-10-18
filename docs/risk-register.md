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
| R10 | CBEXPORT/CBIMPORT: RECORD KEY EXPORT-SEQUENCE-NUM defined in WORKING-STORAGE, not the FD record (source defect) | **realized** | L | Skipped in build (deferred scope); fix FD to `COPY CVEXPORT` or report upstream | — | deferred |
| R11 | Tab-indented sources (CUSTREC.cpy, CSLKPCDY.cpy, tab width 3) overflow column 72 under cobc's 8-col tabs | **realized** | M | build.sh normalizes copies with `expand -t 3`; vendor untouched | — | mitigated |
| R12 | COBDATFT (asm) error path: MVC copies 38 bytes from 13-byte literal → 25 bytes literal-pool residue on z/OS | L | L | COBOL port pads spaces; CardDemo only uses valid path (type 2→2) | — | accepted |
| R13 | VB output RDW: GnuCOBOL length excludes the 4-byte RDW (12), z/OS includes it (16) | **realized** | M | Golden = GnuCOBOL convention; modern VB writer must match; convert if z/OS-faithful files ever needed | — | accepted |
| R14 | Output depends on uninitialized WORKING-STORAGE (CBACT01C reissue date bytes 9–10 via COBDATFT); differed between GnuCOBOL 3.1.2 and 3.2 | **realized** | M | ADR 0004: `-fdefaultbyte=0` (z/OS-typical X'00'); modern preserves for parity, fix after | — | mitigated |
| R9 | VSAM alternate index path (CARDXREF AIX, used by INTCALC) | M | M | Secondary index in GnuCOBOL indexed file + SQL index; verify read order | — | open |
