#!/bin/bash
set -e

YEAR=${1:-2026}
MONTH=${2:-07}
DATA_RELEASE=${3:-2026-07}

docker compose exec hint python manage.py load_data \
  "$YEAR" \
  "$MONTH" \
  "/home/app/data/${DATA_RELEASE}/HINT_format/taxa/" \
  /home/app/data/psi-mi.obo \
  /home/app/data/${DATA_RELEASE}/HINT_format/protein_meta.txt \
  /home/app/data/speclist.tsv \
  /home/app/data/tissue-meta.txt
