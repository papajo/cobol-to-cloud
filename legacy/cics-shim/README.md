# EXEC CICS shim (deferred — phase 6)

Precompiler that rewrites `EXEC CICS READ/WRITE/REWRITE/STARTBR/READNEXT/LINK/RETURN` into GnuCOBOL file I/O and CALL with COMMAREA, so online programs can be golden-captured per transaction. Out of batch-first scope.
