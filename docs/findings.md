# Findings

What the parity harness surfaced in AWS CardDemo (ref 59cc6c2) before any code was migrated. Each item is
reproducible from this repo; risk/ADR references point to the detail.

| # | Finding | Kind | How found | Impact | Handling |
|---|---|---|---|---|---|
| F1 | **INTCALC never applies interest to the last account.** CBACT04C's final control-break update is in an `ELSE` branch that cannot run under `PERFORM UNTIL END-OF-FILE = 'Y'`. Account 00000000050: 18.77 interest written to SYSTRAN, balance unchanged, cycle totals not reset. | Logic defect (would occur on z/OS too) | `harness/checks/intcalc_reconcile.py` (independent of COBOL) | Ledger and interest transactions disagree for one account per run | R17. Modern reproduces for parity, then fixes in a separate, flagged change (`--strict` check) |
| F2 | **Seed data shipped twice, and the copies disagree.** ASCII `acctdata.txt`/`discgrp.txt` differ from the EBCDIC originals in 2 records (account group `ZEROAPR` missing; a 15.00% rate shown as 0.00). | Data drift | cp037 decode + record compare | INTCALC results depend on which copy is loaded | ADR 0003: EBCDIC canonical |
| F3 | **Output depends on uninitialized storage.** CBACT01C copies 2 never-set bytes (COBDATFT writes 8 of 10) into the account extract; GnuCOBOL 3.1.2 and 3.2 disagreed. | Latent defect | Cross-version golden diff | Non-deterministic file content | ADR 0004 (`-fdefaultbyte=0`), R14 |
| F4 | **Signed zoned decimal, not COMP-3, is the dominant money format** (14 fields incl. every account balance; 50 of 300 daily transactions are credits whose sign lives only in the overpunch). | Migration hazard | Copybook scan + reconciliation | Sign errors invisible in text views | `-fsign=EBCDIC`, `codec.ZonedDecimal`, R8 |
| F5 | **Timestamps from the wall clock** (`FUNCTION CURRENT-DATE` in CBTRN02C/CBACT04C); downstream TRANREPT filters on them. GnuCOBOL still takes hundredths from the real clock unless the fraction is pinned. | Determinism | Repeat-run diff | Goldens irreproducible; report selection shifts by run date | ADR 0005, R16 |
| F6 | **INTCALC fees are not implemented** (`1400-COMPUTE-FEES` is an empty paragraph). | Incomplete logic | Source review | Fees always zero | Documented; not invented in modern code |
| F7 | **CBEXPORT/CBIMPORT do not compile**: `RECORD KEY` names a WORKING-STORAGE field, not one in the FD record. | Source defect | Compile | Export/import jobs unusable | R10, deferred |
| F8 | **Tab-indented copybooks** (CUSTREC, CSLKPCDY; tab width 3) overflow column 72 under 8-column tab expansion. | Source hygiene | Compile | CBSTM03A fails to compile | Normalized copies at build, R11 |
| F9 | **Interest is truncated, not rounded** (`COMPUTE` without `ROUNDED`). Parity-safe only if the modern code truncates toward zero (`RoundingMode.DOWN`). | Migration hazard | Source review | Cent-level drift if rounded | CLAUDE.md numerics rule |
