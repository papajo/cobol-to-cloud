      *****************************************************************
      * Stub for Language Environment CEE3ABD (abend with user code).
      * Logs the user abend code to stderr and ends the run unit with
      * RC=16 (exit status is 8-bit; the U-code itself is in the log).
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CEE3ABD.
       DATA DIVISION.
       LINKAGE SECTION.
       01  ABCODE                  PIC S9(9) BINARY.
       01  TIMING                  PIC S9(9) BINARY.
       PROCEDURE DIVISION USING ABCODE, TIMING.
           DISPLAY 'CEE3ABD: ABEND U' ABCODE ' TIMING ' TIMING
               UPON SYSERR
           MOVE 16 TO RETURN-CODE
           STOP RUN.
