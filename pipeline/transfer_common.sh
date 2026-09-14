# shellcheck shell=bash disable=SC2034
# Shared by transfer_to_hamilton.sh / transfer_from_hamilton.sh. Source, don't execute.
#
# SRS source trees (WRL Files/, Museum Files/) are only ever read: they appear as an rsync
# *source* or a `find` root, never a destination. No --delete anywhere.

SRS_ROOT=/mnt/srs/HoBScan
PROCESSED_ROOT=${HOBSCAN_PROCESSED:-$SRS_ROOT/Processed}
REMOTE=${HOBSCAN_REMOTE:-ham8}
REMOTE_ROOT=${HOBSCAN_REMOTE_ROOT:-/nobackup/jrhq77}
STATE_DIR=${HOBSCAN_STATE:-$HOME/.local/state/hobscan}
BM="British Museum"

die() { echo "$(basename "$0"): $*" >&2; exit 1; }

# Quote a path for the remote (bash) shell.
rq() { printf '%q' "$1"; }

list_collections() {
    echo "$BM"
    find "$SRS_ROOT/Museum Files" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | LC_ALL=C sort
}

# Collection name → SRS source directory. Call as: src=$(source_dir "$c") || exit 1
source_dir() {
    case $1 in
        "$BM") echo "$SRS_ROOT/WRL Files" ;;
        "" | . | .. | */*) die "bad collection name: '$1'" ;;
        *) [[ -d "$SRS_ROOT/Museum Files/$1" ]] || die "unknown collection: '$1' (see --list)"
           echo "$SRS_ROOT/Museum Files/$1" ;;
    esac
}

require_master() {
    ssh -O check "$REMOTE" 2>/dev/null ||
        die "no SSH ControlMaster for $REMOTE — run 'ssh $REMOTE' interactively (password+MFA) first"
}

# snapshot <collection> <label> <dir> → prints path of a sorted "path<TAB>size<TAB>mtime" listing.
# Size+mtime rather than hashes: re-reading 224GB over CIFS is too slow.
snapshot() {
    local dir="$STATE_DIR/$1" out
    mkdir -p "$dir"
    out="$dir/$(date -u +%Y%m%dT%H%M%SZ)-$2.tsv"
    find "$3" -type f -printf '%P\t%s\t%T@\n' | LC_ALL=C sort > "$out"
    echo "$out"
}

# compare_snapshots <before> <after>: non-zero (and a .diff beside <after>) if the source changed.
compare_snapshots() {
    local d="${2%.tsv}.diff"
    if diff -u "$1" "$2" > "$d"; then
        rm -f "$d"
        echo "source unchanged: $(wc -l < "$2") files, size+mtime identical"
    else
        echo "WARNING: SOURCE TREE CHANGED between snapshots — see $d" >&2
        return 1
    fi
}
