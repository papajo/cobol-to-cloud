#!/usr/bin/env bash
# Record one golden: baseline load → prerequisite jobs (not captured) → JOB → KSDS unload → capture.
#
# golden/jobs.txt line format:  JOB [MAXCC] [after=PRE1,PRE2]
#   MAXCC  highest acceptable return code for that job (default 0); applies to prerequisites too.
#   after= jobs that must run first from the same baseline (the nightly order), e.g. INTCALC after POSTTRAN.
#
# Usage: harness/golden.sh JOB         (runs legacy steps in the c2c-legacy container)
#        LOCAL=1 harness/golden.sh JOB (runs them directly; needs cobc + COB_* env, used in CI/dev)
set -euo pipefail
JOB=${1:?usage: golden.sh JOB}
IMG=${IMG:-c2c-legacy}
export CD_BUSINESS_DATE=${CD_BUSINESS_DATE:-2022-07-18}

line() { grep -E "^$1( |$)" golden/jobs.txt || true; }
maxrc() { local l; l=$(line "$1"); awk '{ if ($2 ~ /^[0-9]+$/) print $2; else print 0 }' <<<"${l:-$1}"; }
prereq() { line "$1" | grep -o 'after=[^ ]*' | cut -d= -f2 | tr ',' ' ' || true; }

legacy() {  # run a python entrypoint either locally or in the legacy container
  if [[ -n "${LOCAL:-}" ]]; then python3 "$@"
  else docker run --rm -e CD_BUSINESS_DATE -e CD_BATCH_TIME -v "$PWD":/work -w /work "$IMG" python3 "$@"; fi
}

run_job() {  # run_job NAME → runs JCL, enforces that job's MAXCC
  local j=$1 lim rc
  lim=$(maxrc "$j")
  set +e; legacy legacy/jcl-runner/jclrun.py "vendor/carddemo/app/jcl/$j.jcl"; rc=$?; set -e
  if (( rc > lim )); then echo "golden: $j MAXCC=$rc > $lim" >&2; exit 1; fi
}

[[ -n "$(line "$JOB")" ]] || { echo "golden: $JOB not in golden/jobs.txt" >&2; exit 1; }
legacy legacy/vsam/load.py . >/dev/null
for p in $(prereq "$JOB"); do echo "== prerequisite $p"; run_job "$p" >/dev/null; done
mkdir -p out/legacy && touch out/legacy/.runstart && sleep 1
echo "== $JOB"
run_job "$JOB"
legacy legacy/vsam/unload.py . >/dev/null
python3 harness/capture.py "$JOB" --max-rc "$(maxrc "$JOB")"
