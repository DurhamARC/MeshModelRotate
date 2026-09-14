#!/usr/bin/env bash
# Build one collection's file list for a batch run (on Hamilton) and print the sbatch command.
#
#   make_manifest.sh "<collection>"          e.g. "British Museum", "Seaside Museum, Herne Bay"
#
# Lists $HOBSCAN_ROOT/wrl/<collection>/**/*.wrl, sorted and NUL-separated (names contain spaces),
# into $HOBSCAN_ROOT/manifests/<collection>.lst. Submits nothing.
set -euo pipefail

ROOT=${HOBSCAN_ROOT:-/nobackup/$USER}
CHUNK=${CHUNK_SIZE:-20}

(( $# == 1 )) || { sed -n '2,7s/^# \{0,1\}//p' "$0"; exit 2; }
coll=$1
case $coll in "" | . | .. | */*) echo "bad collection name: '$coll'" >&2; exit 1 ;; esac

src="$ROOT/wrl/$coll"
[[ -d $src ]] || { echo "not staged: $src (run transfer_to_hamilton.sh first)" >&2; exit 1; }

mkdir -p "$ROOT/manifests" "$ROOT/logs"
manifest="$ROOT/manifests/$coll.lst"
find "$src" -type f -name '*.wrl' -print0 | LC_ALL=C sort -z > "$manifest"

n=$(tr -cd '\0' < "$manifest" | wc -c)
(( n > 0 )) || { echo "no WRLs in $src" >&2; exit 1; }

# Outputs are flat (<stem>.glb etc.), so two WRLs with the same stem would overwrite each other
dups=$(tr '\0' '\n' < "$manifest" | sed 's#.*/##; s/\.wrl$//' | LC_ALL=C sort | uniq -d)
[[ -z $dups ]] || { printf 'duplicate names in %s:\n%s\n' "$src" "$dups" >&2; exit 1; }

tasks=$(( (n + CHUNK - 1) / CHUNK ))
echo "$n WRLs -> $manifest"
echo "$tasks array tasks of up to $CHUNK models"
echo
echo "Submit with:"
printf '  sbatch --array=0-%d%%50 --export=ALL,CHUNK_SIZE=%d %q %q\n' \
    $(( tasks - 1 )) "$CHUNK" "$(dirname "$(readlink -f "$0")")/slurm_process.sh" "$coll"
