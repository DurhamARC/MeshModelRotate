#!/usr/bin/env bash
# Process one WRL: convert (container) -> render thumbnail (Blender) -> optimise PNG (container).
#
# Usage:
#   process_model.sh [-f] <input.wrl> <output_dir>
#
# Outputs <output_dir>/<name>.{glb,png,json}; skipped if <name>.json says "complete" (-f forces).
# Inside the container the input directory is mounted read-only at /in, so the conversion
# step cannot write next to the source WRL whatever the code does.
#
# Environment:
#   PIPELINE_RUNNER   singularity | docker   (default: singularity if installed, else docker)
#   PIPELINE_SIF      Singularity image      (default: /nobackup/$USER/pipeline/pipeline.sif)
#   PIPELINE_IMAGE    Docker image           (default: hobscan-pipeline)
#   BLENDER           Blender binary         (default: blender on PATH)
#   PIPELINE_VERSION  recorded in the JSON   (default: git describe of this checkout)
#   BLENDER_THREADS   render threads         (default: 0 = all cores Blender can see)

set -euo pipefail

FORCE=()
if [[ "${1:-}" == "-f" ]]; then FORCE=(--force); shift; fi
if [[ $# -ne 2 ]]; then
  grep '^#' "$0" | sed 's/^# \?//' | tail -n +2 >&2
  exit 2
fi

INPUT="$(realpath "$1")"
OUT_DIR="$(realpath -m "$2")"
CODE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_SCRIPT="$CODE_DIR/../render/render_thumbs.py"
IN_DIR="$(dirname "$INPUT")"
NAME="$(basename "${INPUT%.*}")"

[[ -f "$INPUT" ]] || { echo "ERROR: input not found: $INPUT" >&2; exit 1; }
case "$OUT_DIR/" in
  "$IN_DIR"/*) echo "ERROR: output dir is inside the input dir: $OUT_DIR" >&2; exit 1 ;;
esac
mkdir -p "$OUT_DIR"

GLB="$OUT_DIR/$NAME.glb"
PNG="$OUT_DIR/$NAME.png"
JSON="$OUT_DIR/$NAME.json"

if [[ ${#FORCE[@]} -eq 0 && -f "$JSON" ]] && grep -q '"status": "complete"' "$JSON"; then
  echo "SKIP (complete): $NAME"
  exit 0
fi

RUNNER="${PIPELINE_RUNNER:-$(command -v singularity >/dev/null && echo singularity || echo docker)}"
# On Hamilton the code is rsynced into an older checkout, so the batch script passes the version in
PIPELINE_VERSION="${PIPELINE_VERSION:-$(git -C "$CODE_DIR" describe --always --dirty 2>/dev/null || echo unknown)}"

# Run a pipeline script in the container with /in (read-only), /out and /code mounted
in_container() {
  case "$RUNNER" in
    singularity)
      singularity exec --cleanenv --env "PIPELINE_VERSION=$PIPELINE_VERSION" \
        --bind "$IN_DIR:/in:ro,$OUT_DIR:/out,$CODE_DIR:/code:ro" \
        "${PIPELINE_SIF:-/nobackup/$USER/pipeline/pipeline.sif}" python "$@" ;;
    docker)
      docker run --rm --user "$(id -u):$(id -g)" -e "PIPELINE_VERSION=$PIPELINE_VERSION" \
        -v "$IN_DIR:/in:ro" -v "$OUT_DIR:/out" -v "$CODE_DIR:/code:ro" \
        "${PIPELINE_IMAGE:-hobscan-pipeline}" python "$@" ;;
    *) echo "ERROR: unknown PIPELINE_RUNNER: $RUNNER" >&2; exit 1 ;;
  esac
}

# Force re-render when reconverting, so the thumbnail matches the GLB
[[ ${#FORCE[@]} -gt 0 ]] && rm -f "$PNG"

in_container /code/convert.py "/in/$(basename "$INPUT")" /out \
  --source-label "$INPUT" "${FORCE[@]}"

if [[ ! -f "$PNG" ]]; then
  # xvfb-run can exit non-zero *after* a successful render: its cleanup kills an X server that has
  # already exited ("xvfb-run: line 186: kill: (PID) - No such process"). Same spurious exit that
  # 4a7900d worked around in render/slurm_pipeline.sh. Judge the render by whether the PNG was
  # written, not by the exit status, or ~1 model in 3 is thrown away after all the work is done.
  rc=0
  xvfb-run --auto-servernum "${BLENDER:-blender}" --threads "${BLENDER_THREADS:-0}" \
    --background --python "$RENDER_SCRIPT" \
    -- "$GLB" "$PNG" > "$OUT_DIR/.$NAME.render.log" 2>&1 || rc=$?
  [[ -f "$PNG" ]] || {
    echo "ERROR: render failed (exit $rc), see $OUT_DIR/.$NAME.render.log" >&2; exit 1; }
  (( rc == 0 )) || echo "NOTE: xvfb-run exited $rc but the PNG was written: $NAME" >&2
  rm -f "$OUT_DIR/.$NAME.render.log"
fi

in_container /code/optimise_png.py "/out/$NAME.png" "/out/$NAME.json"
