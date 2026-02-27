#!/usr/bin/env bash
# Position and render GLB files as JPEG thumbnails.
#
# Pipeline per file:
#   1. positioning.py <file>.glb  ->  <file>_positioned.glb
#   2. render_thumbs.py <file>_positioned.glb  ->  <file>_positioned_thumb.jpg
#
# After verifying results, remove originals with:
#   rm <GLB_DIR>/*.glb (excludes *_positioned.glb via the glob below)
#   rm /path/to/glbs/!(*.positioned.glb)   -- bash extglob
#   Or simply: ls <GLB_DIR>/*.glb | grep -v _positioned
#
# Usage:
#   ./pipeline.sh [OPTIONS] <GLB_DIR>
#
# Options:
#   -j N       Parallel jobs (default: number of CPU cores)
#   -o DIR     Output directory for thumbnails (default: same dir as GLB)
#   -f         Force re-run even if _positioned.glb already exists
#   --dry-run  Print what would run without doing it
#
# Requires:
#   - blender, xvfb-run  (sudo apt-get install blender xvfb)
#   - ../.venv with trimesh/pymeshlab/numpy (cd .. && uv venv --seed && pip install -r requirements.txt)
#   - ../.venv-blender/lib/python3.12/site-packages with numpy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR/.."
BLENDER_SCRIPT="$SCRIPT_DIR/render_thumbs.py"
POSITIONING_SCRIPT="$REPO_DIR/positioning.py"
POSITIONING_PYTHON="$REPO_DIR/.venv/bin/python"
PYTHONPATH="$REPO_DIR/.venv-blender/lib/python3.12/site-packages"
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
  echo "ERROR: directory not found: $GLB_DIR" >&2
  exit 1
fi

for req in blender xvfb-run; do
  if ! command -v "$req" &>/dev/null; then
    echo "ERROR: $req not found in PATH" >&2
    exit 1
  fi
done

if [[ ! -x "$POSITIONING_PYTHON" ]]; then
  echo "ERROR: positioning venv not found at $POSITIONING_PYTHON" >&2
  echo "  Run: cd $REPO_DIR && uv venv --seed && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

process_one() {
  local glb="$1"
  local base dir
  base="$(basename "${glb%.glb}")"
  dir="$(dirname "$glb")"

  # Skip files that are already positioned outputs
  if [[ "$base" == *_positioned ]]; then
    return 0
  fi

  local positioned="${dir}/${base}_positioned.glb"

  local outdir
  if [[ -n "$OUT_DIR" ]]; then
    outdir="$OUT_DIR"
  else
    outdir="$dir"
  fi

  local thumb="${outdir}/${base}_positioned_thumb.jpg"
  local logfile="${outdir}/${base}_positioned_thumb.log"

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "WOULD RUN: $base"
    echo "  position: $glb -> $positioned"
    echo "  render:   $positioned -> $thumb"
    return 0
  fi

  # Step 1: position
  if [[ $FORCE -eq 1 || ! -f "$positioned" ]]; then
    echo "POSITIONING: $base"
    if ! "$POSITIONING_PYTHON" "$POSITIONING_SCRIPT" "$glb" -o "$positioned" --quiet \
        >> "$logfile" 2>&1; then
      echo "FAILED (positioning): $base (see $logfile)" >&2
      return 1
    fi
  else
    echo "SKIP positioning (exists): $positioned"
  fi

  # Step 2: render
  if [[ $FORCE -eq 1 || ! -f "$thumb" ]]; then
    echo "RENDERING: $base"
    if ! PYTHONPATH="$PYTHONPATH" xvfb-run --auto-servernum blender \
        --background \
        --python "$BLENDER_SCRIPT" \
        -- "$positioned" "$thumb" \
        >> "$logfile" 2>&1; then
      echo "FAILED (render): $base (see $logfile)" >&2
      return 1
    fi
    echo "OK: $thumb"
  else
    echo "SKIP render (exists): $thumb"
  fi
}

export -f process_one
export POSITIONING_PYTHON POSITIONING_SCRIPT BLENDER_SCRIPT OUT_DIR FORCE DRY_RUN PYTHONPATH

if [[ -n "$OUT_DIR" ]]; then
  mkdir -p "$OUT_DIR"
fi

# Match only originals - exclude *_positioned.glb
mapfile -t GLB_FILES < <(find "$GLB_DIR" -maxdepth 1 -name "*.glb" ! -name "*_positioned.glb")
TOTAL=${#GLB_FILES[@]}

echo "Found $TOTAL original GLB files in $GLB_DIR"
echo "Jobs: $JOBS | Force: $FORCE | Dry-run: $DRY_RUN"
echo "Output: ${OUT_DIR:-'(alongside each GLB)'}"
echo ""
echo "To remove originals after verification:"
echo "  find $GLB_DIR -maxdepth 1 -name '*.glb' ! -name '*_positioned.glb' -print"
echo "  # add -delete when satisfied"
echo ""

printf '%s\n' "${GLB_FILES[@]}" | \
  xargs -P "$JOBS" -I{} bash -c 'process_one "$@"' _ {}

echo ""
echo "Done."
