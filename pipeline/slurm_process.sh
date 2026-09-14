#!/usr/bin/env bash
#SBATCH --job-name=hobscan
#SBATCH --partition=shared
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/nobackup/jrhq77/logs/hobscan_%A_%a.out
#
# SLURM array job: run process_model.sh over one collection's manifest, CHUNK_SIZE models per task.
#
#   sbatch --array=0-<N>%50 --export=ALL,CHUNK_SIZE=20 slurm_process.sh "<collection>"
#
# make_manifest.sh prints the exact command. Reads $HOBSCAN_ROOT/wrl/<collection>/ via the manifest,
# writes $HOBSCAN_ROOT/out/<collection>/<stem>.{glb,png,json} (the transfer_from_hamilton.sh contract).
# Resubmitting is safe: models whose JSON says "complete" are skipped.
#
# Check what a task would do, without running anything:
#   SLURM_ARRAY_TASK_ID=0 slurm_process.sh --dry-run "<collection>"
#
# Resources: ~53s per model on 4 CPUs (Phase 1 test), so ~18min per 20-model task. Memory is a
# guess until the pilot measures it (sacct -j <job> -o MaxRSS).

set -uo pipefail   # not -e: one bad model must not stop the rest of the chunk

DRY_RUN=0
[[ ${1:-} == --dry-run ]] && { DRY_RUN=1; shift; }
(( $# == 1 )) || { echo "usage: slurm_process.sh [--dry-run] <collection>" >&2; exit 2; }
coll=$1

ROOT=${HOBSCAN_ROOT:-/nobackup/$USER}
CHUNK=${CHUNK_SIZE:-20}
# sbatch runs a spooled copy of this script, so locate the code by path rather than $0
CODE=${PIPELINE_CODE:-$ROOT/MeshModelRotate/pipeline}
manifest="$ROOT/manifests/$coll.lst"
out="$ROOT/out/$coll"

[[ -f $manifest ]] || { echo "no manifest: $manifest (run make_manifest.sh)" >&2; exit 1; }
[[ -n ${SLURM_ARRAY_TASK_ID:-} ]] || { echo "SLURM_ARRAY_TASK_ID not set" >&2; exit 1; }
case "$(realpath -m "$out")/" in
    "$(realpath -m "$ROOT/wrl")"/*) echo "output inside staged inputs: $out" >&2; exit 1 ;;
esac

export PIPELINE_RUNNER=singularity
export PIPELINE_SIF=${PIPELINE_SIF:-$ROOT/pipeline/pipeline.sif}
export BLENDER=${BLENDER:-$ROOT/blender-4.0.2-linux-x64/blender}
export BLENDER_THREADS=${SLURM_CPUS_PER_TASK:-4}
# The Hamilton checkout is rsynced over an older commit; VERSION is written at sync time
if [[ -z ${PIPELINE_VERSION:-} && -f $CODE/VERSION ]]; then PIPELINE_VERSION=$(<"$CODE/VERSION"); fi
export PIPELINE_VERSION=${PIPELINE_VERSION:-unknown}

mapfile -d '' files < "$manifest"
total=${#files[@]}
start=$(( SLURM_ARRAY_TASK_ID * CHUNK ))
end=$(( start + CHUNK < total ? start + CHUNK : total ))

if (( start >= total )); then
    echo "task $SLURM_ARRAY_TASK_ID: starts at model $start but '$coll' has $total; nothing to do"
    exit 0
fi
echo "task $SLURM_ARRAY_TASK_ID on $(hostname): models $start-$(( end - 1 )) of $total," \
     "collection '$coll', pipeline $PIPELINE_VERSION"

failed=0
for (( i = start; i < end; i++ )); do
    wrl=${files[i]}
    if (( DRY_RUN )); then
        printf 'WOULD RUN: %q %q %q\n' "$CODE/process_model.sh" "$wrl" "$out"
        continue
    fi
    SECONDS=0
    if "$CODE/process_model.sh" "$wrl" "$out"; then
        echo "[$i] done in ${SECONDS}s: $(basename "$wrl")"
    else
        echo "[$i] FAILED after ${SECONDS}s: $wrl"
        failed=$(( failed + 1 ))
    fi
done

(( DRY_RUN )) && { echo "dry run: $(( end - start )) models listed, nothing run"; exit 0; }
echo "task $SLURM_ARRAY_TASK_ID finished: $(( end - start - failed )) ok, $failed failed"
(( failed == 0 ))   # non-zero exit marks the task FAILED in sacct
