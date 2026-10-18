#!/usr/bin/env bash
# Phase 4 driver: schema → load seed → export → round-trip reconcile, for every dataset in migration/layouts/datasets.json.
#   migration/db.sh load        apply generated schema, load out/seed via CSV + \copy
#   migration/db.sh reconcile   export each table ORDER BY pk, rebuild fixed records, byte-compare with seed
# PSQL defaults to the compose service; override for a local server, e.g. PSQL="psql -h localhost -U carddemo -d carddemo".
set -euo pipefail
PSQL=${PSQL:-docker compose exec -T db psql -U carddemo -d carddemo}
OUT=out/pg; mkdir -p "$OUT/csv" "$OUT/export" "$OUT/roundtrip"
datasets() {  # dsn table pk seed   (seed = file in out/seed; '-' when the dataset has none)
  python3 -c "import json; [print(k, v['table'], ','.join(v['pk']), v['seed'] or '-') for k, v in json.load(open('migration/layouts/datasets.json')).items()]"
}

case ${1:-} in
load)
  $PSQL -q -v ON_ERROR_STOP=1 -f - < modern/batch/src/main/resources/db/schema.sql
  while read -r dsn table pk seed; do
    if [[ "$seed" == - ]]; then echo "skip $table (no seed)"; continue; fi
    python3 migration/pgload.py to-csv "$dsn" "out/seed/$seed" "$OUT/csv/$table.csv"
    $PSQL -q -v ON_ERROR_STOP=1 -c "\\copy \"$table\" from stdin with (format csv)" < "$OUT/csv/$table.csv"
  done < <(datasets) ;;
reconcile)
  rc=0
  while read -r dsn table pk seed; do
    [[ "$seed" != - ]] || continue
    $PSQL -q -v ON_ERROR_STOP=1 -c "\\copy (select * from \"$table\" order by $pk) to stdout with (format csv)" > "$OUT/export/$table.csv"
    python3 migration/pgload.py from-csv "$dsn" "$OUT/export/$table.csv" "$OUT/roundtrip/$dsn"
    python3 migration/pgload.py reconcile "$dsn" "out/seed/$seed" "$OUT/roundtrip/$dsn" || rc=1
  done < <(datasets); exit $rc ;;
*) sed -n '2,5p' "$0"; exit 2 ;;
esac
