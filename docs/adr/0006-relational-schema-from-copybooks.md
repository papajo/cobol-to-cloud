# 0006 — Relational schema generated from copybooks, proven by byte round trip

**Status:** accepted · 2026-10-18

**Context:** Phase 4 moves VSAM/flat datasets to Postgres. The modern jobs must produce byte-identical output to the goldens, so the database must be able to hold *every* byte the legacy files hold, and the mapping must not drift from the copybooks.

**Decision:**
- `migration/copybook.py` parses copybooks into layout JSON (`migration/layouts/`): one source for DDL, the loader, and the Java codec. REDEFINES/OCCURS raise rather than being modelled approximately.
- `migration/gen_schema.py` generates `modern/batch/src/main/resources/db/schema.sql`. Primary keys come from CardDemo's IDCAMS `KEYS(len off)`, mapped onto the fields covering that span (fails if the key does not align with field boundaries).
- Types: `X(n)` → `char(n) COLLATE "C"` (byte order = the oracle's key order); `9(n)` → `numeric(n,0)`; `S9(n)V9(m)` → `numeric(n+m,m)` (overpunch decoded on load, re-encoded on unload); flat datasets get a `seq` PK to keep record order.
- **FILLER → `bytea`**, kept byte-exact. CardDemo fillers hold spaces, `'0'`s (TCATBAL, DISCGRP, TRANTYPE, TRANCATG) or X'00' (TRANSACT records written by CBTRN02C from uninitialized storage — see ADR 0004). Dropping or space-padding them would break parity.
- Data fields are decoded strictly: non-digits in `9(n)`, bad overpunch, negative zero, or X'00' in a data field fail the load with dataset/record/field.
- The TRANSACT seed's single record, whose key is all LOW-VALUES, is a VSAM "file must not be empty" placeholder (CICS cannot open an empty KSDS). It is not migrated — the `transaction` table starts empty — and both load and reconcile report it (`drop_placeholder` in `migration/datasets.json`).

**Proof:** `make db-load db-reconcile` loads every seed dataset, exports each table `ORDER BY` its primary key, rebuilds fixed-width records and byte-compares with the source (key-ordered for KSDS). 11/11 datasets, 736 records identical, with control totals. The same layouts round-trip the COBOL-written VSAM outputs in `golden/POSTTRAN` and `golden/INTCALC` (account, tran_cat_balance incl. 50 program-created rows, 262 transactions with X'00' fillers).

**Consequences:**
- Columns are named after the COBOL fields (`acct_curr_bal`) and commented with PIC/offset — traceable, not pretty. A friendlier model (views, renames) can follow after parity.
- Collation follows the oracle (ASCII byte order). z/OS EBCDIC key order differs for mixed letter/digit keys (R2); revisit only if z/OS-faithful ordering is required.
- Filler columns are migration scaffolding; drop them once parity has been signed off.
