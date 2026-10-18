#!/usr/bin/env bash
# Compile CardDemo batch programs (CB*.cbl / CB*.CBL) as loadable modules.
set -uo pipefail
shopt -s nullglob nocaseglob
VSRC=/work/vendor/carddemo/app
SRC=/work/out/legacy/src
OUT=/work/out/legacy/lib
# Deferred (ADR 0003 / risk R10): RECORD KEY defined outside the FD record in CardDemo source.
SKIP=" CBEXPORT CBIMPORT "

# Normalize sources (vendor/ stays pristine): a few CardDemo files are tab-indented with
# tab width 3; cobc expands tabs to 8, pushing code past column 72 (risk R11).
rm -rf "$SRC" && mkdir -p "$SRC/cbl" "$SRC/cpy" "$OUT"
for d in cbl cpy; do
  for f in "$VSRC/$d"/*; do
    if grep -q $'\t' "$f"; then expand -t 3 "$f" > "$SRC/$d/$(basename "$f")"; echo "NORM $d/$(basename "$f") (tabs→3)"
    else cp "$f" "$SRC/$d/"; fi
  done
done

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
