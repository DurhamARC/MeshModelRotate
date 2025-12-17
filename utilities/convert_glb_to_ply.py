#!/usr/bin/env python3
"""Batch-convert 3DModels/*.glb (and other supported formats) to PLY.

Outputs are written to `ToConvert/converted/` to keep originals separate.
Run: python ToConvert/convert_glb_to_ply.py
"""
from pathlib import Path
import sys
import traceback

try:
    import trimesh
except Exception:
    print("Error: 'trimesh' is required. Install with: pip install trimesh")
    sys.exit(1)


INPUT_DIR = Path("ToConvert")
OUTPUT_DIR = Path("ToConvert") / "converted"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXT = {".glb", ".gltf", ".stl", ".ply", ".obj", ".off", ".wrl", ".x3d"}


def convert_file(path: Path, outdir: Path):
    outpath = outdir / (path.stem + ".ply")
    print(f"Converting {path} -> {outpath}")
    try:
        loaded = trimesh.load(path, force=None)

        # If it's a Scene, try to take the first geometry
        if isinstance(loaded, trimesh.Scene):
            if len(loaded.geometry) == 0:
                print(f"  Warning: scene {path} has no geometry; skipping")
                return
            first_geom = next(iter(loaded.geometry.values()))
            mesh = first_geom
        else:
            mesh = loaded

        # Export as PLY
        mesh.export(outpath)
    except Exception:
        print(f"  Failed to convert {path}")
        traceback.print_exc()


def main():
    if not INPUT_DIR.exists():
        print(f"Input directory not found: {INPUT_DIR}")
        sys.exit(1)

    files = sorted([p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXT])
    if not files:
        print(f"No supported files found in {INPUT_DIR}")
        return

    for f in files:
        convert_file(f, OUTPUT_DIR)


if __name__ == "__main__":
    main()
