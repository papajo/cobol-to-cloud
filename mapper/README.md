# mapper — COBOL/JCL front-end for Legacy Code Mapper (#2)

Adds parsers so the existing mapper (struts-to-boot/mapper) emits the same call-graph/rules/MCP output for:
- JCL: JOB → STEP → PGM, DD → DSN
- COBOL: PERFORM/CALL/COPY edges, file SELECT/FD → DD name, EXEC SQL table refs
Target metric: % PERFORM/CALL edges traced (parity with #2's 94.7% on Java).
