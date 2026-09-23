#!/usr/bin/env python3
"""Save mesh vertices and faces to a .mat file for MATLAB.

Usage: python save_mat_for_matlab.py <input_mesh> [-o OUT]
Examples:
  python save_mat_for_matlab.py 3DModels/model.glb
  python save_mat_for_matlab.py 3DModels/model.ply -o ToConvert/converted/model.mat
"""
import argparse
from pathlib import Path
import sys
import traceback

import trimesh
import scipy.io as sio
import numpy as np


def main():
    p = argparse.ArgumentParser(description="Export mesh to .mat (v,f) for MATLAB")
    p.add_argument("input", help="Input mesh file (GLB/PLY/STL/OBJ/...)")
    p.add_argument("-o", "--out", help="Output .mat file path (optional)")
    args = p.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"Input file not found: {inp}")
        sys.exit(1)

    try:
        mesh = trimesh.load(inp)
    except Exception:
        print(f"Failed to load mesh: {inp}")
        traceback.print_exc()
        sys.exit(2)

    # If a Scene, pick the first geometry
    if isinstance(mesh, trimesh.Scene):
        if len(mesh.geometry) == 0:
            print(f"Scene has no geometry: {inp}")
            sys.exit(3)
        mesh = next(iter(mesh.geometry.values()))

    v = np.asarray(mesh.vertices)

    # faces may be empty for point clouds
    if hasattr(mesh, "faces") and mesh.faces is not None and len(mesh.faces) > 0:
        f = np.asarray(mesh.faces).astype(int)
        # Convert to 1-based indexing for MATLAB
        f_mat = (f + 1).astype(int)
    else:
        f_mat = np.empty((0, 3), dtype=int)

    if args.out:
        out = Path(args.out)
    else:
        outdir = Path("ToConvert") / "converted"
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / (inp.stem + ".mat")

    sio.savemat(out, {"v": v, "f": f_mat})
    print("Wrote:", out)


if __name__ == "__main__":
    main()

