#!/usr/bin/env bash
# Compile CardDemo batch programs (CB*.cbl / CB*.CBL) as loadable modules.
set -uo pipefail
shopt -s nullglob nocaseglob
SRC=/work/vendor/carddemo/app
OUT=/work/out/legacy/lib
# Deferred (ADR 0003 / risk R10): RECORD KEY defined outside the FD record in CardDemo source.
SKIP=" CBEXPORT CBIMPORT "
mkdir -p "$OUT"
ok=0; fail=0; skip=0
for f in "$SRC"/cbl/CB*.cbl; do
  n=$(basename "${f%.*}" | tr a-z A-Z)
  if [[ "$SKIP" == *" $n "* ]]; then skip=$((skip+1)); echo "SKIP $n"; continue; fi
  # -fsign=EBCDIC: signed DISPLAY uses z/OS overpunch ({,A-I,},J-R) — required for CardDemo data (ADR 0003)
  if cobc -m -std=ibm -fsign=EBCDIC -I "$SRC/cpy" -o "$OUT/$n.so" "$f" 2>"/tmp/$n.err"; then
    ok=$((ok+1)); echo "OK   $n"
  else
    fail=$((fail+1)); echo "FAIL $n"; head -8 "/tmp/$n.err"
  fi
done
echo "compiled=$ok failed=$fail skipped=$skip"
exit $(( fail > 0 ))
