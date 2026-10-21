# cobol-to-cloud

Mainframe batch modernization of [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo): COBOL / JCL / VSAM / DB2 → Spring Batch / Postgres, verified by byte-level parity against golden output from the original COBOL running under GnuCOBOL.

> **What this proves:** IBM mainframe experience (COBOL, JCL, VSAM, DB2), re-applied with modern tooling. Golden outputs are captured from the legacy COBOL, and every migrated piece must match them byte for byte — migration you can check, not migration you have to trust. Data migration (copybook → DDL, EBCDIC, COMP-3) is done and round-trips byte-exact; batch re-implementation in Spring Batch is next.
> Available for small, fixed-scope modernization assessments — see [my profile](https://github.com/papajo).

| Phase | Status |
|---|---|
| 0. Assessment & inventory | ✅ |
| 1. Dependency map (mapper) | ☐ |
| 2. Legacy runtime (GnuCOBOL + JCL runner) | ✅ |
| 3. Golden capture | 🟡 READ×4, POSTTRAN, INTCALC |
| 4. Data migration (copybook → DDL, EBCDIC, COMP-3) | ✅ 11 tables, byte round trip |
| 5. Batch modernization (JCL → Spring Batch) | ☐ |

See `CLAUDE.md` for commands and conventions, `docs/adr/` for decisions.
