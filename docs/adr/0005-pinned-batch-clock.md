# 0005 — Pinned batch clock

**Status:** accepted · 2026-10-18

**Context:** POSTTRAN produced a different TRANSACT unload on every run. CBTRN02C (line 693) and CBACT04C (line 614) stamp `TRAN-PROC-TS` from `FUNCTION CURRENT-DATE`; CBIMPORT/CBEXPORT also read the clock. Downstream, TRANREPT selects transactions by `TRAN-PROC-TS(1:10)`, so the clock changes not just bytes but which records a later job reports.

GnuCOBOL honours `COB_CURRENT_DATE`, but `YYYY/MM/DD hh:mm:ss` alone still takes **hundredths from the wall clock**; the fraction must be given (`... hh:mm:ss.00`) to pin fully (verified empirically).

**Decision:** Every legacy step runs with `COB_CURRENT_DATE = <CD_BUSINESS_DATE> <CD_BATCH_TIME>`, set by `jclrun` (defaults: business date from the Makefile, `2022-07-18`; batch time `02:00:00.00`). `jclrun` refuses to run without `CD_BUSINESS_DATE`. The modern side must read time only through an injected `Clock` fixed to the same instant.

**Consequences:**
- POSTTRAN golden is deterministic (`TRAN-PROC-TS = 2022-07-18-02.00.00.000000`).
- Same pattern as struts-to-boot's pinned clock — the harness owns time, programs never see the wall clock.
- Running the daily chain for several business days later means advancing `CD_BUSINESS_DATE` per run, as a scheduler would.
