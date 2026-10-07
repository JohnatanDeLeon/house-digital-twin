#!/usr/bin/env bash
# Pipeline PDF → hechos en metros. Uso: pipeline/pdf/run.sh [pdf] [build_dir]
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
PDF="${1:-$ROOT/sources/casa-jonhy-levantamiento.pdf}"
BUILD="${2:-$ROOT/build/pdf}"
OUT="$ROOT/data/extracted/pdf"
mkdir -p "$BUILD" "$OUT"
python3 "$HERE/extract.py" "$PDF" "$BUILD"
python3 "$HERE/calibrate.py" "$BUILD"
python3 "$HERE/openings.py" "$BUILD"
python3 "$HERE/rooms.py" "$BUILD"
python3 "$HERE/overlay.py" "$BUILD" "$ROOT/docs/analysis/01-overlay-extraccion-pdf.png"
cp "$BUILD"/{frame.json,openings.json,rooms.json} "$OUT/"
