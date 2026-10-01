#!/bin/bash
# Run from an installed TimesFM environment; output goes to an explicit external directory.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:?Usage: run_example.sh OUTPUT_DIR}"
python3 "$SCRIPT_DIR/run_forecast.py" --output-dir "$OUTPUT_DIR"
python3 "$SCRIPT_DIR/visualize_forecast.py" --output-dir "$OUTPUT_DIR"
echo "[OK] Illustrative forecast and plot written to $OUTPUT_DIR"
