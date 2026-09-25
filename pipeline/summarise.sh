#!/usr/bin/env bash
# Report on one collection's batch run (on Hamilton). Reads outputs; writes only the report.
#
#   summarise.sh "<collection>"
#
# For every manifest entry: <stem>.{glb,png,json} exist, the JSON says "complete", and the GLB
# (read from its own header, not the JSON) has vertex colours, a non-metallic material and the
# decimation target's face count. Also lists FAILED lines from this collection's job logs, and models whose curvature check
# disagrees with the tip-up choice (for review, not failures). Lists go to
# $HOBSCAN_ROOT/reports/<collection>/<UTC>/ — outside out/, so transfer_from_hamilton.sh ignores them.
# HOBSCAN_OUT overrides the output dir (e.g. to check the pilot). Exit 1 if anything is missing or bad.
set -euo pipefail

ROOT=${HOBSCAN_ROOT:-/nobackup/$USER}
FACES=${TARGET_FACES:-200000}

(( $# == 1 )) || { sed -n '2,12s/^# \{0,1\}//p' "$0"; exit 2; }
coll=$1
manifest="$ROOT/manifests/$coll.lst"
out=${HOBSCAN_OUT:-$ROOT/out/$coll}
report="$ROOT/reports/$coll/$(date -u +%Y%m%dT%H%M%SZ)"
[[ -f $manifest ]] || { echo "no manifest: $manifest" >&2; exit 1; }
[[ -d $out ]] || { echo "no outputs: $out" >&2; exit 1; }
mkdir -p "$report"

# FAILED lines from logs of tasks that ran this collection
{ grep -lF "collection '$coll'," "$ROOT"/logs/hobscan_*.out 2>/dev/null || true; } |
    while IFS= read -r log; do grep -H "FAILED" "$log" || true; done > "$report/failed_in_logs.txt"

status=0
python3 - "$manifest" "$out" "$report" "$FACES" <<'EOF' || status=$?
import json, os, struct, sys

manifest, out, report, target = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
with open(manifest, "rb") as f:
    stems = [os.path.splitext(os.path.basename(p.decode()))[0] for p in f.read().split(b"\0") if p]


def glb_info(path):
    """Face count, and whether every primitive has COLOR_0 and a non-metallic material, from the
    GLB's JSON chunk. A primitive without a material gets glTF's default, which is fully metallic."""
    with open(path, "rb") as f:
        magic, _, _ = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF":
            raise ValueError("not a GLB")
        length, _ = struct.unpack("<I4s", f.read(8))
        gltf = json.loads(f.read(length).decode())
    faces, colour, material = 0, True, True
    for mesh in gltf["meshes"]:
        for prim in mesh["primitives"]:
            faces += gltf["accessors"][prim["indices"]]["count"] // 3
            colour = colour and "COLOR_0" in prim["attributes"]
            pbr = gltf["materials"][prim["material"]].get("pbrMetallicRoughness", {}) if "material" in prim else {}
            material = material and pbr.get("metallicFactor", 1.0) == 0
    return faces, colour, material


lists = {"missing": [], "incomplete": [], "bad_glb": [], "review_orientation": []}
complete = 0
for s in stems:
    paths = {e: os.path.join(out, s + "." + e) for e in ("glb", "png", "json")}
    absent = [e for e, p in sorted(paths.items()) if not os.path.exists(p)]
    if absent:
        lists["missing"].append("{}\t{}".format(s, ",".join(absent)))
        continue
    with open(paths["json"]) as f:
        rec = json.load(f)
    if rec.get("status") != "complete":
        lists["incomplete"].append("{}\tstatus={}".format(s, rec.get("status")))
        continue
    try:
        faces, colour, material = glb_info(paths["glb"])
    except Exception as e:
        lists["bad_glb"].append("{}\tunreadable: {}".format(s, e))
        continue
    # Inputs already at or below the target aren't decimated, so expect min(target, input faces).
    # Quadric edge collapse stops when no further valid collapse exists, so it can finish a few
    # faces short of the target -- 105 of 4,388 models landed 1-16 faces under, all otherwise
    # sound. Allow 0.1% under (200 faces at the 200k target), but never over.
    expected = min(target, rec["input"]["faces"])
    floor = int(expected * 0.999)
    if not (floor <= faces <= expected) or not colour or not material:
        lists["bad_glb"].append("{}\tfaces={} expected={} (min {}) colour={} material={}".format(
            s, faces, expected, floor, colour, material))
        continue
    complete += 1
    if not rec["orientation"].get("curvature_agrees_with_tip", True):
        lists["review_orientation"].append(s)

for name, items in lists.items():
    with open(os.path.join(report, name + ".txt"), "w") as f:
        f.writelines(i + "\n" for i in items)

print("{} models in manifest, {} complete and valid".format(len(stems), complete))
for name, items in lists.items():
    print("  {:<20} {}".format(name, len(items)))
sys.exit(1 if lists["missing"] or lists["incomplete"] or lists["bad_glb"] else 0)
EOF

echo "  failed_in_logs       $(wc -l < "$report/failed_in_logs.txt")"
echo "lists: $report"
exit $status
