      *****************************************************************
      * z/OS EXEC PGM=xxx,PARM='...' equivalent for GnuCOBOL.
      * On z/OS the main program receives the PARM as its first USING
      * parameter: a halfword length followed by the text. cobcrun has
      * no such convention, so jclrun runs this driver instead, which
      * builds that area from env CD_PARM and CALLs env CD_PGM with it.
      * Compiled with the same -std=ibm flags as the programs, so the
      * S9(4) COMP length is big-endian like on z/OS.
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PARMDRV.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-PGM                  PIC X(8)   VALUE SPACES.
       01  WS-PARM-AREA.
           05  WS-PARM-LEN         PIC S9(4)  COMP.
           05  WS-PARM-TEXT        PIC X(100) VALUE SPACES.
       01  WS-RAW                  PIC X(100) VALUE SPACES.
       01  WS-LEN                  PIC S9(4)  COMP VALUE 0.
       PROCEDURE DIVISION.
           ACCEPT WS-PGM FROM ENVIRONMENT 'CD_PGM'
           ACCEPT WS-RAW FROM ENVIRONMENT 'CD_PARM'
           IF WS-PGM = SPACES
               DISPLAY 'PARMDRV: CD_PGM not set' UPON SYSERR
               MOVE 16 TO RETURN-CODE
               GOBACK
           END-IF
           IF WS-RAW NOT = SPACES
               INSPECT FUNCTION REVERSE(WS-RAW)
                   TALLYING WS-LEN FOR LEADING SPACES
               COMPUTE WS-LEN = LENGTH OF WS-RAW - WS-LEN
           END-IF
           MOVE WS-LEN TO WS-PARM-LEN
           MOVE WS-RAW TO WS-PARM-TEXT
           CALL WS-PGM USING WS-PARM-AREA
               ON EXCEPTION
                   DISPLAY 'PARMDRV: cannot load ' WS-PGM UPON SYSERR
                   MOVE 16 TO RETURN-CODE
           END-CALL
           GOBACK.
