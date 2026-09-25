#!/usr/bin/env python3
"""Add the pipeline's material to GLBs made before convert.py wrote one, in place.

    patch_material.py [--apply] <dir> [<dir> ...]

Each <dir> is searched recursively for <name>.glb with a <name>.json beside it, e.g.
/mnt/srs/HoBScan/Processed or one collection within it. A dry run (the default) reads only the GLB
headers and reports what would change; --apply writes.

Only the GLB's JSON chunk changes: the material is added (material.py) and the binary chunk --
geometry and vertex colours -- is copied through, then checked byte for byte against the original.
Each file is written to a temp file and renamed, as in convert.py. The provenance JSON gets
output.material, the new output.glb_size, and an entry in "patches" recording what was done.
Prints a line per file and a progress summary every 100 files. Standard library only, so it runs
on the machine the share is mounted on.

Idempotent: a GLB that already has the material is left alone, and a JSON that already records it
is too. If a run is interrupted between a GLB and its JSON, rerunning completes the JSON.
"""

import argparse
import datetime
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

from material import MATERIAL, add_material, has_material

GLB_MAGIC, JSON_CHUNK, BIN_CHUNK = b"glTF", 0x4E4F534A, 0x004E4942

# Source trees that must never be written to (as in convert.py)
PROTECTED = [Path("/mnt/srs/HoBScan/WRL Files"), Path("/mnt/srs/HoBScan/Museum Files")]


def read_header(path):
    """Return the gltf tree from a GLB's JSON chunk, reading only that far."""
    with open(path, "rb") as f:
        head = f.read(20)
        check_header(head)
        return json.loads(f.read(struct.unpack_from("<I", head, 12)[0]))


def check_header(head):
    magic, glb_version, _, _, kind = struct.unpack_from("<4sIIII", head)
    if magic != GLB_MAGIC or glb_version != 2:
        raise ValueError("not a glTF 2.0 GLB")
    if kind != JSON_CHUNK:
        raise ValueError("first chunk is not JSON")


def parse_glb(data):
    """Return (gltf tree, binary chunk bytes) from a whole GLB."""
    check_header(data)
    length = struct.unpack_from("<I", data, 12)[0]
    tree = json.loads(data[20:20 + length])
    rest = data[20 + length:]
    chunks = []
    while rest:
        length, kind = struct.unpack_from("<II", rest)
        chunks.append((kind, rest[8:8 + length]))
        rest = rest[8 + length:]
    if [kind for kind, _ in chunks] != [BIN_CHUNK]:
        raise ValueError("expected exactly one BIN chunk after the JSON")
    return tree, chunks[0][1]


def glb_bytes(tree, binary):
    """Assemble a GLB; the JSON chunk is padded with spaces to 4 bytes, as the spec requires."""
    text = json.dumps(tree, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(binary)
    return (struct.pack("<4sII", GLB_MAGIC, 2, total) + struct.pack("<II", len(text), JSON_CHUNK) + text
            + struct.pack("<II", len(binary), BIN_CHUNK) + binary)


def write_atomic(path, data):
    tmp = path.with_name(f".{path.name}.partial")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def pipeline_version():
    here = Path(__file__).resolve().parent
    try:
        return subprocess.run(["git", "-C", str(here), "describe", "--always", "--dirty"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return os.environ.get("PIPELINE_VERSION", "unknown")


def patch_glb(glb_path):
    """Add the material; return the patch facts for the JSON. The original is checked first."""
    before = glb_path.read_bytes()
    tree, binary = parse_glb(before)
    add_material(tree)
    data = glb_bytes(tree, binary)
    write_atomic(glb_path, data)

    check_tree, check_binary = parse_glb(glb_path.read_bytes())
    if check_binary != binary or not has_material(check_tree):
        raise RuntimeError("verification failed after writing")
    return {
        "glb_sha256_before": hashlib.sha256(before).hexdigest(),
        "glb_sha256_after": hashlib.sha256(data).hexdigest(),
        "bin_chunk_unchanged": True,
    }


def patch_json(json_path, glb_path, facts, version):
    record = json.loads(json_path.read_text())
    output = record.setdefault("output", {})
    output["material"] = MATERIAL
    output["glb_size"] = glb_path.stat().st_size
    record.setdefault("patches", []).append({
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script": "pipeline/patch_material.py",
        "pipeline": version,
        "change": "added material (was glTF's default, which is fully metallic); "
                  "geometry and vertex colours unchanged",
        **facts,
    })
    write_atomic(json_path, (json.dumps(record, indent=2)).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dirs", nargs="+", type=Path)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = parser.parse_args()

    for d in args.dirs:
        if not d.is_dir():
            sys.exit(f"ERROR: not a directory: {d}")
        for tree in PROTECTED:
            if d.resolve() == tree or tree in d.resolve().parents or d.resolve() in tree.parents:
                sys.exit(f"ERROR: {d} overlaps protected source tree {tree}")

    # Line-buffered, so progress shows through a pipe (e.g. into tee) as it happens
    sys.stdout.reconfigure(line_buffering=True)
    version = pipeline_version()
    glbs = sorted(p for d in args.dirs for p in d.rglob("*.glb") if not p.name.startswith("."))
    total = len(glbs)
    print(f"{'Applying' if args.apply else 'Dry run'} (pipeline {version}): {total} GLBs under "
          f"{', '.join(str(d) for d in args.dirs)}")

    counts = {"patched": 0, "json_only": 0, "done": 0, "no_json": 0, "error": 0}
    started = time.time()
    for i, glb_path in enumerate(glbs, 1):
        t = time.time()
        name = f"{glb_path.parent.name}/{glb_path.name}"
        json_path = glb_path.with_suffix(".json")
        try:
            if not json_path.exists():
                outcome = "no_json"
            else:
                glb_done = has_material(read_header(glb_path))
                json_done = "material" in json.loads(json_path.read_text()).get("output", {})
                if glb_done and json_done:
                    outcome = "done"
                elif not args.apply:
                    outcome = "json_only" if glb_done else "patched"
                elif glb_done:
                    # Interrupted after the GLB was written: record it without its hashes
                    patch_json(json_path, glb_path, {"note": "GLB already patched when the JSON was updated"},
                               version)
                    outcome = "json_only"
                else:
                    patch_json(json_path, glb_path, patch_glb(glb_path), version)
                    outcome = "patched"
            counts[outcome] += 1
            label = {"patched": "PATCHED" if args.apply else "WOULD PATCH",
                     "json_only": "JSON ONLY" if args.apply else "WOULD FIX JSON",
                     "done": "ALREADY DONE", "no_json": "SKIP (no JSON)"}[outcome]
            print(f"[{i}/{total}] {label}: {name} ({glb_path.stat().st_size / 1e6:.1f} MB, "
                  f"{time.time() - t:.1f}s)")
        except Exception as e:  # report and carry on with the rest
            counts["error"] += 1
            print(f"[{i}/{total}] ERROR: {name}: {e}")

        if i % 100 == 0 and i < total:
            elapsed = time.time() - started
            eta = elapsed / i * (total - i)
            print(f"--- {i}/{total} ({100 * i / total:.0f}%) in {elapsed / 60:.1f} min, "
                  f"{i / elapsed:.1f} files/s, ETA {eta / 60:.1f} min; "
                  + ", ".join(f"{k} {v}" for k, v in counts.items() if v))

    verb = "patched" if args.apply else "to patch"
    print(f"{'Applied' if args.apply else 'Dry run'} (pipeline {version}) in "
          f"{(time.time() - started) / 60:.1f} min: "
          f"{counts['patched']} {verb}, {counts['json_only']} JSON only, {counts['done']} already done, "
          f"{counts['no_json']} without JSON, {counts['error']} errors")
    sys.exit(1 if counts["error"] else 0)


if __name__ == "__main__":
    main()
