# 0004 — Pin uninitialized WORKING-STORAGE to X'00'

**Status:** accepted · 2026-10-18

**Context:** Recording the READACCT golden on GnuCOBOL 3.1.2 (Claude workspace) and 3.2 (oldbox) produced different `ACCTDATA.PSCOMP` files; SYSOUT and the other datasets matched. Cause: CBACT01C moves `CODATECN-0UT-DATE` (20 bytes, copybook `CODATECN`, **no VALUE clause**) into the 10-byte `OUT-ACCT-REISSUE-DATE`. COBDATFT writes only the first 8 bytes, so bytes 9–10 are whatever the storage held at load time. GnuCOBOL's default for fields without VALUE (`-fdefaultbyte`, "initialize to picture" → spaces for PIC X) differs by version/dialect config; on z/OS the content is governed by the LE `STORAGE` runtime option and is commonly binary zeros.

**Decision:** Compile all legacy programs with `-fdefaultbyte=0`, so storage without a VALUE clause starts as X'00' on every GnuCOBOL version — the common z/OS behaviour (`STORAGE(00,...)`).

**Consequences:**
- Goldens no longer depend on the GnuCOBOL version; READACCT re-recorded (reissue date bytes 9–10 now X'00').
- The modern side must reproduce this: an unwritten tail of a field copied from uninitialized storage is X'00', not spaces. This is a *legacy bug being preserved for parity*, flagged in the risk register (R14) so it can be fixed deliberately after parity, not silently.
- Any other program relying on uninitialized storage is now deterministic too; differences between versions should be reported as findings, not absorbed.
