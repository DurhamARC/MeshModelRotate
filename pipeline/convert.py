#!/usr/bin/env python
"""WRL -> decimated, oriented GLB plus a provenance JSON. Runs inside the pipeline container.

    convert.py <input.wrl> <output_dir> [--faces 200000] [--source-label PATH] [--force]

Writes <output_dir>/<name>.glb and <output_dir>/<name>.json, each via a temp file and
rename so a killed job never leaves a file that looks finished. The input is only ever
opened for reading.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pymeshlab
import trimesh

from orient import orient_handaxe

# Source trees that must never be written to (PIPELINE.md "Constraints"). Extend with
# PIPELINE_PROTECTED=/path/a:/path/b, e.g. the read-only staging area on Hamilton.
PROTECTED = [Path("/mnt/srs/HoBScan/WRL Files"), Path("/mnt/srs/HoBScan/Museum Files")]
PROTECTED += [Path(p) for p in os.environ.get("PIPELINE_PROTECTED", "").split(":") if p]


def check_output_dir(input_path, out_dir):
    """Refuse any output location inside the input's directory or a protected tree."""
    out = out_dir.resolve()
    for tree in [input_path.resolve().parent] + [p.resolve() for p in PROTECTED]:
        if out == tree or tree in out.parents:
            sys.exit(f"ERROR: output dir {out} is inside input/protected tree {tree}")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_atomic(path, write):
    tmp = path.with_name(f".{path.name}.partial")
    write(tmp)
    os.replace(tmp, path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--faces", type=int, default=200_000, help="decimation target")
    parser.add_argument("--source-label", help="source path to record (host path if in a container)")
    parser.add_argument("--force", action="store_true", help="overwrite existing outputs")
    args = parser.parse_args()

    src = args.input
    if not src.is_file():
        sys.exit(f"ERROR: input not found: {src}")
    check_output_dir(src, args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    name = src.stem
    glb_path = args.output_dir / f"{name}.glb"
    json_path = args.output_dir / f"{name}.json"
    if glb_path.exists() and json_path.exists() and not args.force:
        print(f"SKIP (exists): {glb_path}")
        return

    timings = {}
    stat = src.stat()
    t = time.time()
    source = {
        "path": args.source_label or str(src),
        "size": stat.st_size,
        "mtime": datetime.datetime.fromtimestamp(stat.st_mtime, datetime.timezone.utc).isoformat(),
        "sha256": sha256(src),
    }
    timings["hash"] = time.time() - t

    t = time.time()
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(str(src))
    m = ms.current_mesh()
    input_stats = {"vertices": m.vertex_number(), "faces": m.face_number(),
                   "vertex_colour": m.has_vertex_color()}
    timings["load"] = time.time() - t

    t = time.time()
    decimation = {"filter": "meshing_decimation_quadric_edge_collapse",
                  "targetfacenum": args.faces, "preservenormal": True}
    if m.face_number() > args.faces:
        ms.apply_filter(decimation["filter"], targetfacenum=args.faces, preservenormal=True)
        m = ms.current_mesh()
    else:
        decimation["skipped"] = "input already at or below target"
    timings["decimate"] = time.time() - t

    colours = None
    if m.has_vertex_color():
        colours = (m.vertex_color_matrix() * 255).round().astype(np.uint8)
    mesh = trimesh.Trimesh(m.vertex_matrix(), m.face_matrix(), vertex_colors=colours, process=False)
    volume_before = float(mesh.volume) if mesh.is_watertight else None

    t = time.time()
    transform, orientation = orient_handaxe(mesh.vertices)
    mesh.apply_transform(transform)
    timings["orient"] = time.time() - t
    if volume_before is not None and np.sign(mesh.volume) != np.sign(volume_before):
        sys.exit("ERROR: orientation inverted the mesh (volume changed sign)")

    t = time.time()
    write_atomic(glb_path, lambda p: mesh.export(p, file_type="glb"))
    timings["export"] = time.time() - t

    record = {
        "name": name,
        "status": "converted",
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": source,
        "input": input_stats,
        "decimation": decimation,
        "orientation": orientation,
        "output": {
            "glb": glb_path.name,
            "glb_size": glb_path.stat().st_size,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "vertex_colour": colours is not None,
            "watertight": bool(mesh.is_watertight),
            "volume": float(mesh.volume) if mesh.is_watertight else None,
            "extents": mesh.extents.tolist(),
        },
        "versions": {
            "pipeline": os.environ.get("PIPELINE_VERSION", "unknown"),
            **{pkg: version(pkg) for pkg in ("pymeshlab", "trimesh", "numpy", "scipy")},
        },
        "timings_s": {k: round(v, 2) for k, v in timings.items()},
    }
    write_atomic(json_path, lambda p: p.write_text(json.dumps(record, indent=2)))
    print(f"OK: {glb_path} ({input_stats['faces']} -> {len(mesh.faces)} faces, "
          f"{sum(timings.values()):.1f}s)")


if __name__ == "__main__":
    main()
