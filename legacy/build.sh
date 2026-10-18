#!/usr/bin/env bash
# Compile CardDemo batch programs as loadable modules. Log failures to docs/build-log.md.
set -uo pipefail
SRC=/work/vendor/carddemo/app
OUT=/work/out/legacy/lib
mkdir -p "$OUT"
ok=0; fail=0
for f in "$SRC"/cbl/CB*.cbl; do
  n=$(basename "$f" .cbl)
  if cobc -m -std=ibm -I "$SRC/cpy" -o "$OUT/$n.so" "$f" 2>"/tmp/$n.err"; then
    ok=$((ok+1))
  else
    fail=$((fail+1)); echo "FAIL $n"; head -5 "/tmp/$n.err"
  fi
done
echo "compiled=$ok failed=$fail"
