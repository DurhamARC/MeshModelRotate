#!/usr/bin/env bash
#SBATCH --job-name=glb_thumbs
#SBATCH --partition=shared
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --array=0-26
#SBATCH --output=/nobackup/jrhq77/logs/thumb_%A_%a.out
#SBATCH --error=/nobackup/jrhq77/logs/thumb_%A_%a.err

# Slurm array job: position + render GLBs in chunks of 100 files per task.
# 27 tasks (0-26) x 100 files = 2700 slots, handles up to 2700 GLBs.
# Submit from /nobackup/jrhq77:
#   mkdir -p logs
#   sbatch MeshModelRotate/render/slurm_pipeline.sh

set -uo pipefail

CHUNK_SIZE=100
REPO=/nobackup/jrhq77/MeshModelRotate
GLB_DIR=/nobackup/jrhq77/glbs
BLENDER=/nobackup/jrhq77/blender-4.0.2-linux-x64/blender
POSITIONING_PYTHON="$REPO/.venv/bin/python"
POSITIONING_SCRIPT="$REPO/positioning.py"
BLENDER_SCRIPT="$REPO/render/render_thumbs.py"
BLENDER_PYTHONPATH="$REPO/.venv-blender/lib/python3.10/site-packages"

# Build sorted list of original GLBs (exclude *_positioned.glb)
mapfile -t GLB_FILES < <(find "$GLB_DIR" -maxdepth 1 -name "*.glb" ! -name "*_positioned.glb" | sort)

TOTAL=${#GLB_FILES[@]}
START=$(( SLURM_ARRAY_TASK_ID * CHUNK_SIZE ))
END=$(( START + CHUNK_SIZE - 1 ))
[[ $END -ge $TOTAL ]] && END=$(( TOTAL - 1 ))

echo "Task $SLURM_ARRAY_TASK_ID: files $START-$END of $TOTAL"

for (( i=START; i<=END; i++ )); do
    GLB="${GLB_FILES[$i]}"
    BASE="$(basename "${GLB%.glb}")"
    DIR="$(dirname "$GLB")"
    POSITIONED="${DIR}/${BASE}_positioned.glb"
    THUMB="${DIR}/${BASE}_positioned_thumb.png"
    LOG="${DIR}/${BASE}_positioned_thumb.log"

    # Step 1: position
    if [[ ! -f "$POSITIONED" ]]; then
        PYTHONPATH="" "$POSITIONING_PYTHON" "$POSITIONING_SCRIPT" "$GLB" -o "$POSITIONED" --quiet \
            >> "$LOG" 2>&1
        echo "Positioned: $BASE"
    else
        echo "SKIP positioning (exists): $BASE"
    fi

    # Step 2: render
    if [[ ! -f "$THUMB" ]]; then
        PYTHONPATH="$BLENDER_PYTHONPATH" xvfb-run --auto-servernum "$BLENDER" \
            --background \
            --python "$BLENDER_SCRIPT" \
            -- "$POSITIONED" "$THUMB" \
            >> "$LOG" 2>&1
        echo "Rendered: $BASE"
    else
        echo "SKIP render (exists): $BASE"
    fi
done

echo "Task $SLURM_ARRAY_TASK_ID done."
