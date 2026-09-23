#!/usr/bin/env bash
# Build manifests and submit the batch for every staged collection (on Hamilton).
#
#   submit_all.sh [options] [<collection> ...]     default: all of $HOBSCAN_ROOT/wrl/*/
#
#   --submit              actually sbatch (without it, this is a dry run that submits nothing)
#   --chunk N             models per array task (default 20)
#   --max-concurrent N    total array tasks running at once, across all collections (default 50)
#   --quiet-mins N        refuse a collection whose staged tree changed in the last N minutes,
#                         i.e. a transfer still in flight (default 10; 0 disables)
#   --force               submit anyway despite the quiet-period guard
#
# Rebuilds each manifest from what is staged now, so re-running after a transfer finishes picks up
# the new files. Resubmitting is safe: models whose JSON says "complete" are skipped by the job.
# Submitted job IDs are recorded in $HOBSCAN_ROOT/logs/submitted_<UTC>.tsv.
set -euo pipefail

ROOT=${HOBSCAN_ROOT:-/nobackup/$USER}
CODE=${PIPELINE_CODE:-$(dirname "$(readlink -f "$0")")}
CHUNK=${CHUNK_SIZE:-20}
MAX_CONC=50
QUIET_MINS=10
SUBMIT=0
FORCE=0

die() { echo "submit_all.sh: $*" >&2; exit 1; }

colls=()
while (( $# )); do
    case $1 in
        --submit)         SUBMIT=1 ;;
        --force)          FORCE=1 ;;
        --chunk)          CHUNK=${2:?--chunk needs a number}; shift ;;
        --max-concurrent) MAX_CONC=${2:?--max-concurrent needs a number}; shift ;;
        --quiet-mins)     QUIET_MINS=${2:?--quiet-mins needs a number}; shift ;;
        -h|--help)        sed -n '2,18s/^# \{0,1\}//p' "$0"; exit 0 ;;
        -*)               die "unknown option: $1" ;;
        *)                colls+=("$1") ;;
    esac
    shift
done

for n in "$CHUNK" "$MAX_CONC" "$QUIET_MINS"; do
    [[ $n =~ ^[0-9]+$ ]] || die "not a number: '$n'"
done
(( CHUNK > 0 ))    || die "--chunk must be > 0"
(( MAX_CONC > 0 )) || die "--max-concurrent must be > 0"

# --- preflight: everything the job will need on the compute nodes ---------------------------
[[ -d $ROOT/wrl ]]                  || die "no staged inputs: $ROOT/wrl"
[[ -x $CODE/slurm_process.sh ]]     || die "not executable: $CODE/slurm_process.sh"
[[ -x $CODE/make_manifest.sh ]]     || die "not executable: $CODE/make_manifest.sh"
[[ -f ${PIPELINE_SIF:-$ROOT/pipeline/pipeline.sif} ]] \
    || die "no container: ${PIPELINE_SIF:-$ROOT/pipeline/pipeline.sif}"
[[ -x ${BLENDER:-$ROOT/blender-4.0.2-linux-x64/blender} ]] \
    || die "no blender: ${BLENDER:-$ROOT/blender-4.0.2-linux-x64/blender}"
# Outputs record this; an empty or missing VERSION would stamp every JSON "unknown"
version=$(cat "$CODE/VERSION" 2>/dev/null || true)
[[ -n $version ]] || die "no $CODE/VERSION — write it when you rsync the code, or every output
    records pipeline version 'unknown':
      git describe --always --dirty | ssh ham8 'cat > $CODE/VERSION'"
mkdir -p "$ROOT/manifests" "$ROOT/logs"

if (( ${#colls[@]} == 0 )); then
    while IFS= read -r d; do colls+=("$(basename "$d")"); done \
        < <(find "$ROOT/wrl/" -mindepth 1 -maxdepth 1 -type d | LC_ALL=C sort)
fi
(( ${#colls[@]} )) || die "no collections found under $ROOT/wrl/"

# --- pass 1: manifests, sizes, and the quiet-period guard ------------------------------------
names=() models=() tasks=() done_n=() skip=()
total_tasks=0 total_models=0 blocked=0
now=$(date +%s)

for coll in "${colls[@]}"; do
    src="$ROOT/wrl/$coll"
    [[ -d $src ]] || die "not staged: $src"

    reason=""
    # A tree still being rsynced into will have a recent mtime somewhere inside it. Submitting then
    # would freeze a manifest that is missing whatever has not landed yet.
    if (( QUIET_MINS > 0 )) && ! (( FORCE )); then
        newest=$(find "$src" -newermt "@$(( now - QUIET_MINS * 60 ))" -print -quit 2>/dev/null || true)
        [[ -z $newest ]] || reason="staged tree changed in the last ${QUIET_MINS}m — transfer still running?"
    fi

    if [[ -z $reason ]]; then
        if ! CHUNK_SIZE=$CHUNK "$CODE/make_manifest.sh" "$coll" > /dev/null 2>&1; then
            reason=$(CHUNK_SIZE=$CHUNK "$CODE/make_manifest.sh" "$coll" 2>&1 >/dev/null | head -1)
            reason=${reason:-make_manifest.sh failed}
        fi
    fi

    n=0 t=0
    if [[ -z $reason ]]; then
        n=$(tr -cd '\0' < "$ROOT/manifests/$coll.lst" | wc -c)
        t=$(( (n + CHUNK - 1) / CHUNK ))
        total_tasks=$(( total_tasks + t ))
        total_models=$(( total_models + n ))
    else
        blocked=$(( blocked + 1 ))
    fi

    # Outputs already present are skipped by the job; shown so a resubmission's size is obvious
    d=0
    [[ -d $ROOT/out/$coll ]] && d=$(find "$ROOT/out/$coll" -maxdepth 1 -name '*.json' | wc -l)

    names+=("$coll"); models+=("$n"); tasks+=("$t"); done_n+=("$d"); skip+=("$reason")
done

# --- pass 2: share the concurrency budget out in proportion to size --------------------------
printf '%-42s %7s %7s %6s %5s  %s\n' COLLECTION MODELS DONE TASKS CAP NOTE
caps=()
for i in "${!names[@]}"; do
    cap=0
    if (( tasks[i] > 0 )); then
        cap=$(( (MAX_CONC * tasks[i] + total_tasks / 2) / total_tasks ))
        (( cap < 1 )) && cap=1
        (( cap > tasks[i] )) && cap=${tasks[i]}
    fi
    caps+=("$cap")
    printf '%-42s %7s %7s %6s %5s  %s\n' \
        "${names[i]}" "${models[i]}" "${done_n[i]}" "${tasks[i]}" "${cap:-–}" "${skip[i]}"
done
echo
echo "$total_models models, $total_tasks array tasks, chunk $CHUNK, pipeline $version"
echo "concurrency budget: $MAX_CONC tasks ≈ $(( MAX_CONC * 4 )) CPUs (shared QOS allows 5077)"
(( blocked )) && echo "$blocked collection(s) not submittable — see NOTE above" >&2

if ! (( SUBMIT )); then
    echo
    echo "dry run — nothing submitted. Re-run with --submit to queue these."
    exit 0
fi
(( total_tasks )) || die "nothing to submit"

# --- submit ----------------------------------------------------------------------------------
record="$ROOT/logs/submitted_$(date -u +%Y%m%dT%H%M%SZ).tsv"
printf 'jobid\tcollection\tmodels\ttasks\tcap\tversion\n' > "$record"
rc=0
for i in "${!names[@]}"; do
    (( tasks[i] > 0 )) || continue
    jobid=$(sbatch --parsable \
                --array="0-$(( tasks[i] - 1 ))%${caps[i]}" \
                --export=ALL,CHUNK_SIZE="$CHUNK" \
                "$CODE/slurm_process.sh" "${names[i]}") || { rc=1; echo "FAILED to submit: ${names[i]}" >&2; continue; }
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$jobid" "${names[i]}" "${models[i]}" "${tasks[i]}" "${caps[i]}" "$version" >> "$record"
    echo "submitted $jobid  ${names[i]} (${tasks[i]} tasks%${caps[i]})"
done

echo
echo "record: $record"
echo "watch:  squeue --me"
echo "then:   for c in \$(cut -f2 $(printf '%q' "$record") | tail -n +2); do $(printf '%q' "$CODE/summarise.sh") \"\$c\"; done"
exit $rc
