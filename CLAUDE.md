# CLAUDE.md — cobol-to-cloud

Capstone #5. Migrate AWS CardDemo (COBOL/JCL/VSAM/DB2) batch to Spring Batch + Postgres with byte-identical parity against golden output. Scope: **batch-first** (phases 0–5). CICS online deferred.

## Stack
- Legacy (Docker on oldbox): GnuCOBOL 3.2 `-std=ibm -fsign=EBCDIC`, indexed files (BDB) for VSAM, GixSQL → Postgres for EXEC SQL, `legacy/jcl-runner/jclrun.py` for JCL.
- Seed data: EBCDIC `app/data/EBCDIC/*.PS` is canonical (ADR 0003); `app/data/ASCII` has drifted — never use it.
- Modern: Java 21, Spring Boot 3.3, Spring Batch 5, Postgres 16, Maven multi-module (`modern/`).
- Tooling: Python 3.11 (`migration/`, `harness/`, `legacy/jcl-runner/`), Make.
- Source: `vendor/carddemo/` (git-ignored; fetched by `make fetch`, pinned in `legacy/CARDDEMO_REF`).

## Layout
```
legacy/      Dockerfile, fetch + build scripts, jcl-runner/, cics-shim/ (deferred)
golden/      captured outputs per job (input/, output/, manifest.json)
harness/     compare.py — byte/field-level parity vs golden
migration/   copybook2ddl.py, ebcdic/COMP-3 loaders, reconcile.py
modern/      codec/ (EBCDIC + COMP-3 Java lib), batch/ (Spring Batch jobs)
mapper/      COBOL/JCL parsers for Legacy Code Mapper (#2)
docs/        assessment/, adr/, risk-register.md, inventory.md
```

## Commands
```
make fetch            # clone CardDemo at pinned ref → vendor/carddemo
make inventory        # regenerate docs/inventory.{md,json}
make seed-data        # EBCDIC .PS → out/seed/*.dat (fixed ASCII records)
make legacy-build     # docker build gnucobol image; compile CB* programs + legacy/runtime stubs
make legacy-load      # IDCAMS DEFINE+REPRO equivalent: rebuild all KSDS from out/seed (baseline)
make legacy-run JOB=X # run JCL member X under jclrun.py
make golden JOB=X     # load baseline + run + capture → golden/X/ (refuses MAXCC>0)
make golden-all       # all jobs in golden/jobs.txt
make modern-test      # mvn -f modern/pom.xml verify
make parity JOB=X     # run modern job, compare vs golden/X
make db-up / db-reset # Postgres via docker compose; reset to snapshot
```

## Conventions
- Assembler/LE routines CardDemo calls are ported to COBOL in `legacy/runtime/` (CEE3ABD stub, COBDATFT port), divergences logged as risks.
- One job migrated per PR: `job/<JCLNAME>`. PR must include green `make parity JOB=<name>`.
- Golden is source of truth. Never edit golden/ by hand; re-record only via `make golden`, commit with reason.
- Pinned business date `2022-07-18` (env `CD_BUSINESS_DATE`) for both legacy and modern runs.
- Numerics: signed zoned → `codec.ZonedDecimal`, COMP-3 → `codec.PackedDecimal`. Money: `BigDecimal` only; scale from PIC clause; rounding mode must match COBOL (`ROUNDED` → HALF_UP, else DOWN/truncate). No `double`.
- Ordering: compare keys in EBCDIC collation (`codec.EbcdicCollator`) wherever COBOL SORT/VSAM key order is observable.
- Copybook is the schema: DDL and record classes are generated from `vendor/carddemo/app/cpy`, never hand-written.
- Decisions → `docs/adr/NNNN-title.md`. Risks → `docs/risk-register.md`.
- Commits: conventional (`feat(batch):`, `fix(codec):`, `test(golden):`).
