# cobol-to-cloud

Mainframe batch modernization of [AWS CardDemo](https://github.com/aws-samples/aws-mainframe-modernization-carddemo): COBOL / JCL / VSAM / DB2 → Spring Batch / Postgres, verified by byte-level parity against golden output from the original COBOL running under GnuCOBOL.

| Phase | Status |
|---|---|
| 0. Assessment & inventory | ☐ |
| 1. Dependency map (mapper) | ☐ |
| 2. Legacy runtime (GnuCOBOL + JCL runner) | ☐ |
| 3. Golden capture | ☐ |
| 4. Data migration (copybook → DDL, EBCDIC, COMP-3) | ☐ |
| 5. Batch modernization (JCL → Spring Batch) | ☐ |

See `CLAUDE.md` for commands and conventions, `docs/adr/` for decisions.
