#!/usr/bin/env bash
set -euo pipefail
CONFIG="${1:-config.yaml}"
python3 benchmark.py -c "$CONFIG"
python3 analyze.py --summary ./runs/$(yq -r '.run_label' "$CONFIG")_summary.csv --outdir ./runs --run_label $(yq -r '.run_label' "$CONFIG")
python3 generate_report.py -c "$CONFIG" -s ./runs/$(yq -r '.run_label' "$CONFIG")_summary_clean.csv
