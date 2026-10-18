# 0002 — GnuCOBOL as legacy oracle

**Status:** accepted · 2026-10-18

**Context:** No z/OS access (ZD&T is licensed). Golden output must come from the original COBOL.

**Decision:** GnuCOBOL 3.2 `-std=ibm` in Docker; BDB indexed files emulate VSAM KSDS; GixSQL → Postgres for EXEC SQL; custom Python JCL runner.

**Consequences:** Oracle is "COBOL semantics under GnuCOBOL", not z/OS. Known divergences (ASCII vs EBCDIC collation, file status codes, numeric edge cases) are logged in `docs/risk-register.md` and pinned by codec tests.
