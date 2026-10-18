# 0001 — Batch-first scope

**Status:** accepted · 2026-10-18

**Context:** CardDemo has batch (JCL + COBOL + VSAM/DB2) and online (CICS/BMS). No open-source CICS runtime exists; online parity needs a custom EXEC CICS shim (high risk).

**Decision:** Phases 0–5 only — assessment, dependency map, GnuCOBOL legacy runtime, golden capture, data migration, JCL → Spring Batch. CICS online (phases 6–7) deferred.

**Consequences:** Byte-level batch parity is achievable and demonstrable in ≈4–6 weeks. Online modernization is a follow-on with its own ADR.
