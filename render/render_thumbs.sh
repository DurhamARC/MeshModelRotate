#!/usr/bin/env bash
# Render JPEG thumbnails from GLB files using Blender headlessly.
#
# Usage:
#   ./render_thumbs.sh [OPTIONS] <GLB_DIR>
#
# Options:
#   -j N       Parallel jobs (default: number of CPU cores)
#   -o DIR     Output directory (default: same directory as each GLB)
#   -f         Force re-render even if thumbnail already exists
#   --dry-run  Print what would be rendered without doing it
#
# Output files are named <basename>_thumb.jpg alongside each .glb,
# or in the output directory if -o is specified.
#
# Requires: blender, xvfb-run
# Requires: ../.venv-blender/lib/python3.12/site-packages with numpy installed
#   Setup: python3.12 -m pip install --target ../.venv-blender/lib/python3.12/site-packages numpy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLENDER_SCRIPT="$SCRIPT_DIR/render_thumbs.py"
PYTHONPATH="$SCRIPT_DIR/../.venv-blender/lib/python3.12/site-packages"
export PYTHONPATH

JOBS=$(nproc)
OUT_DIR=""
FORCE=0
DRY_RUN=0
GLB_DIR=""

usage() {
  grep '^#' "$0" | sed 's/^# \?//' | tail -n +2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -j) JOBS="$2"; shift 2 ;;
    -o) OUT_DIR="$2"; shift 2 ;;
    -f) FORCE=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) GLB_DIR="$1"; shift ;;
  esac
done

if [[ -z "$GLB_DIR" ]]; then
  echo "ERROR: GLB_DIR is required" >&2
  usage
fi

if [[ ! -d "$GLB_DIR" ]]; then
  echo "ERROR: GLB directory not found: $GLB_DIR" >&2
  exit 1
fi

if [[ ! -f "$BLENDER_SCRIPT" ]]; then
  echo "ERROR: render_thumbs.py not found at $BLENDER_SCRIPT" >&2
  exit 1
fi

if ! command -v blender &>/dev/null; then
  echo "ERROR: blender not found in PATH" >&2
  exit 1
fi

if ! command -v xvfb-run &>/dev/null; then
  echo "ERROR: xvfb-run not found. Install with: sudo apt-get install xvfb" >&2
  exit 1
fi

render_one() {
  local glb="$1"
  local base
  base="$(basename "${glb%.glb}")"

  local outdir
  if [[ -n "$OUT_DIR" ]]; then
    outdir="$OUT_DIR"
  else
    outdir="$(dirname "$glb")"
  fi

  local thumb="${outdir}/${base}_thumb.jpg"

  if [[ $FORCE -eq 0 && -f "$thumb" ]]; then
    echo "SKIP (exists): $thumb"
    return 0
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "WOULD RENDER: $glb -> $thumb"
    return 0
  fi

  echo "RENDERING: $base"
  if xvfb-run --auto-servernum blender \
      --background \
      --python "$BLENDER_SCRIPT" \
      -- "$glb" "$thumb" \
      > "${outdir}/${base}_thumb.log" 2>&1; then
    echo "OK: $thumb"
  else
    echo "FAILED: $glb (see ${outdir}/${base}_thumb.log)" >&2
  fi
}

export -f render_one
export BLENDER_SCRIPT OUT_DIR FORCE DRY_RUN

# Create output dir if specified
if [[ -n "$OUT_DIR" ]]; then
  mkdir -p "$OUT_DIR"
fi

GLB_FILES=("$GLB_DIR"/*.glb)
TOTAL=${#GLB_FILES[@]}

echo "Found $TOTAL GLB files in $GLB_DIR"
echo "Jobs: $JOBS | Force: $FORCE | Dry-run: $DRY_RUN"
echo "Output: ${OUT_DIR:-'(alongside each GLB)'}"
echo ""

printf '%s\n' "${GLB_FILES[@]}" | \
  xargs -P "$JOBS" -I{} bash -c 'render_one "$@"' _ {}

echo ""
echo "Done."
