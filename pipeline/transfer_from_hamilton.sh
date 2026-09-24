#!/usr/bin/env bash
# Copy one collection's pipeline outputs from Hamilton back to SRS.
#
#   transfer_from_hamilton.sh [--no-baseline] "<collection>"
#   transfer_from_hamilton.sh --list
#
# --no-baseline: proceed when no staging snapshot exists for the collection, i.e. it was staged by
# some route other than transfer_to_hamilton.sh from this machine. The return copy and completeness
# check are unaffected; only the "source unchanged since staging" proof is skipped, so establish
# that some other way first. A baseline, if present, is always compared regardless of this flag.
#
# ham8:/nobackup/jrhq77/out/<collection>/  →  /mnt/srs/HoBScan/Processed/<collection>/
# Copies only <name>.{glb,png,json}; never deletes. Afterwards re-snapshots the WRL source and
# diffs it against the baseline from transfer_to_hamilton.sh, and lists models with missing outputs.
set -euo pipefail
. "$(dirname "$(readlink -f "$0")")/transfer_common.sh"

[[ ${1:-} == --list ]] && { list_collections; exit 0; }
NO_BASELINE=0
[[ ${1:-} == --no-baseline ]] && { NO_BASELINE=1; shift; }
(( $# == 1 )) || { sed -n '2,15s/^# \{0,1\}//p' "$0"; exit 2; }

coll=$1
src=$(source_dir "$coll") || exit 1
remote_out="$REMOTE_ROOT/out/$coll"
dest="$PROCESSED_ROOT/$coll"
case "$(realpath -m "$dest")/" in
    "$SRS_ROOT/WRL Files/"* | "$SRS_ROOT/Museum Files/"*) die "refusing to write into a source tree: $dest" ;;
esac

baseline=$(ls -1 "$STATE_DIR/$coll"/*-to-before.tsv 2>/dev/null | tail -n1) || baseline=""
if [[ -z $baseline ]]; then
    (( NO_BASELINE )) ||
        die "no baseline snapshot for '$coll' — was it staged with transfer_to_hamilton.sh from this
    machine? Pass --no-baseline to continue once you have established another way that the source is
    unchanged since staging."
    echo "WARNING: no baseline for '$coll'; skipping the source-unchanged check (--no-baseline)" >&2
fi
require_master
ssh "$REMOTE" "test -d $(rq "$remote_out")" || die "no outputs on $REMOTE: $remote_out"

mkdir -p "$dest"
filters=(--include='*/' --include='*.glb' --include='*.png' --include='*.json' --exclude='*' --prune-empty-dirs)
# CIFS destination: no perms/owners (-rt only), and allow for coarse timestamps.
rsync -rt -s --modify-window=1 --partial --info=stats1,progress2 "${filters[@]}" "$REMOTE:$remote_out/" "$dest/"

pending=$(rsync -rtn -s --modify-window=1 --itemize-changes "${filters[@]}" "$REMOTE:$remote_out/" "$dest/" | grep -v '^\.' || true)
[[ -z $pending ]] || { printf '%s\n' "$pending" >&2; die "SRS copy differs from Hamilton outputs"; }

# Completeness: every source WRL should have all three outputs.
after=$(snapshot "$coll" from-after "$src")
missing="${after%.tsv}-missing.txt"
stems=$(cut -f1 "$after" | sed -E 's#.*/##; s/\.wrl$//' | LC_ALL=C sort)
for ext in glb png json; do
    LC_ALL=C comm -23 <(printf '%s\n' "$stems") \
        <(find "$dest" -type f -name "*.$ext" -printf '%f\n' | sed "s/\.$ext\$//" | LC_ALL=C sort) |
        sed "s/\$/.$ext/"
done > "$missing"
if [[ -s $missing ]]; then
    echo "WARNING: $(wc -l < "$missing") expected outputs missing — see $missing" >&2
else
    rm -f "$missing"
    echo "complete: $(wc -l <<< "$stems") models × {glb,png,json} in $dest"
fi

if [[ -n $baseline ]]; then
    compare_snapshots "$baseline" "$after"
else
    echo "source-unchanged check skipped: no staging baseline for '$coll'"
fi
