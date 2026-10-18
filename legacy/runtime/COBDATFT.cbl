      *****************************************************************
      * COBOL port of CardDemo assembler routine COBDATFT (asm/COBDATFT
      * + maclib/COCDATFT DSECT). Byte-for-byte the same moves:
      *  type '1' (YYYYMMDD)   -> out YYYY-MM-DD, writes bytes 1-10 only
      *  type '2' (YYYY-MM-DD) -> out YYYYMMDD,   writes bytes 1-8 only
      *  rejects: type 1 with '-' at pos 5, type 1->outtype '2',
      *           type 2->outtype '1', any other type.
      * Untouched: rest of out date, error msg on success.
      * Known divergence (risk R12): on error the original MVC copies 38
      * bytes from a 13-byte literal (25 bytes of literal-pool residue);
      * here the remainder is spaces.
      *****************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. COBDATFT.
       DATA DIVISION.
       LINKAGE SECTION.
       01  COREC.
           05  COINTYPE                PIC X.
           05  COINPDT                 PIC X(20).
           05  COOUTYPE                PIC X.
           05  COOUTDT                 PIC X(20).
           05  COERMSG                 PIC X(38).
       PROCEDURE DIVISION USING COREC.
           EVALUATE COINTYPE
             WHEN '1'
               IF COINPDT(5:1) = '-' OR COOUTYPE = '2'
                   PERFORM GOTOERR
               ELSE
                   MOVE COINPDT(1:4) TO COOUTDT(1:4)
                   MOVE '-'          TO COOUTDT(5:1)
                   MOVE COINPDT(5:2) TO COOUTDT(6:2)
                   MOVE '-'          TO COOUTDT(8:1)
                   MOVE COINPDT(7:2) TO COOUTDT(9:2)
               END-IF
             WHEN '2'
               IF COOUTYPE = '1'
                   PERFORM GOTOERR
               ELSE
                   MOVE COINPDT(1:4) TO COOUTDT(1:4)
                   MOVE COINPDT(6:2) TO COOUTDT(5:2)
                   MOVE COINPDT(9:2) TO COOUTDT(7:2)
               END-IF
             WHEN OTHER
               PERFORM GOTOERR
           END-EVALUATE
           MOVE 0 TO RETURN-CODE
           GOBACK.
       GOTOERR.
           MOVE 'INVALID INPUT' TO COERMSG.
