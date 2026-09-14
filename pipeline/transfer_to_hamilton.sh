#!/usr/bin/env bash
# Stage one collection's WRLs from SRS onto Hamilton as a read-only copy.
#
#   transfer_to_hamilton.sh "<collection>"     e.g. "British Museum", "Seaside Museum, Herne Bay"
#   transfer_to_hamilton.sh --list
#
# SRS "WRL Files/" or "Museum Files/<museum>/"  →  ham8:/nobackup/jrhq77/wrl/<collection>/
# Snapshots the source (size+mtime) before and after; the "to-before" snapshot is the baseline
# transfer_from_hamilton.sh diffs against later. Restartable; run inside tmux.
set -euo pipefail
. "$(dirname "$(readlink -f "$0")")/transfer_common.sh"

[[ ${1:-} == --list ]] && { list_collections; exit 0; }
(( $# == 1 )) || { sed -n '2,9s/^# \{0,1\}//p' "$0"; exit 2; }

coll=$1
src=$(source_dir "$coll") || exit 1
dest="$REMOTE_ROOT/wrl/$coll"
require_master

before=$(snapshot "$coll" to-before "$src")
echo "snapshot: $(wc -l < "$before") files in $src → $before"

# Re-runs: the staged tree was made a-w last time. rsync replaces files by rename, so only the
# directories need to be writable.
ssh "$REMOTE" "mkdir -p $(rq "$dest") && find $(rq "$dest") -type d -exec chmod u+w {} +"

filters=(--include='*/' --include='*.wrl' --exclude='*' --prune-empty-dirs)
# NB: never --delete; SRS is only ever the source here.
rsync -rt -s --partial --info=stats1,progress2 "${filters[@]}" "$src/" "$REMOTE:$dest/"

# Verify: a dry-run must find nothing left to transfer.
pending=$(rsync -rtn -s --itemize-changes "${filters[@]}" "$src/" "$REMOTE:$dest/" | grep -v '^\.' || true)
[[ -z $pending ]] || { printf '%s\n' "$pending" >&2; die "staged copy differs from source"; }

ssh "$REMOTE" "chmod -R a-w $(rq "$dest")"
remote_n=$(ssh "$REMOTE" "find $(rq "$dest") -type f -name '*.wrl' | wc -l")
echo "staged: $remote_n WRLs in $REMOTE:$dest (read-only)"

after=$(snapshot "$coll" to-after "$src")
compare_snapshots "$before" "$after"
