#!/usr/bin/env python3
"""
Test script for complete UZY positioning implementation.

Tests the full Grosman 2008 methodology on a single GLB file:
- Phase 1: UZY positioning (eigenvector analysis)
- Phase 2: Planform optimization + mirror symmetry
"""

import sys
from pathlib import Path
import trimesh
import numpy as np
import positioning


def load_mesh_from_file(filepath: str) -> trimesh.Trimesh:
    """Load mesh, handling both direct meshes and Scene objects."""
    loaded = trimesh.load(filepath)

    if isinstance(loaded, trimesh.Scene):
        if len(loaded.geometry) == 0:
            raise ValueError(f"Scene has no geometry: {filepath}")
        # Get first geometry
        mesh = list(loaded.geometry.values())[0]
        print(f"  Extracted mesh from Scene (had {len(loaded.geometry)} geometries)")
    else:
        mesh = loaded

    return mesh


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_positioning.py <input.glb> [--uzy-only] [--show]")
        print("\nExamples:")
        print("  python test_positioning.py ToConvert/Wansunt_1931_7_11_10.glb")
        print("  python test_positioning.py model.glb --uzy-only  # Skip planform/symmetry")
        print("  python test_positioning.py model.glb --show      # Visualize result")
        return 1

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return 1

    # Parse flags
    uzy_only = '--uzy-only' in sys.argv
    show_viz = '--show' in sys.argv

    print(f"Loading: {input_file}")
    mesh = load_mesh_from_file(str(input_file))

    print(f"  Vertices: {len(mesh.vertices)}")
    print(f"  Faces: {len(mesh.faces)}")
    print(f"  Bounds: {mesh.bounds}")

    if uzy_only:
        print("\nRunning Phase 1 only (UZY positioning)...")
    else:
        print("\nRunning complete positioning (UZY + Planform + Mirror Symmetry)...")

    v_original = mesh.vertices.copy()

    try:
        v_positioned, metadata = positioning.positioning(
            mesh.vertices,
            mesh.faces,
            include_planform=not uzy_only,
            include_mirror_symmetry=not uzy_only
        )
        print("  ✓ Positioning succeeded")
    except Exception as e:
        print(f"  ✗ Positioning failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Analyze transformation
    print("\nMetadata:")
    print(f"  Center offset: {metadata['center_offset']}")
    print(f"  UZY transform:\n{metadata['uzy_transform']}")

    if 'planform_rotation_index' in metadata:
        print(f"\nPlanform optimization:")
        print(f"  Selected rotation: {metadata['planform_rotation_index']} (0=orig, 1=90°X, 2=90°Y)")
        print(f"  Projected areas: {[f'{a:.2f}' for a in metadata['planform_areas']]}")

    if 'symmetry_angle' in metadata:
        print(f"\nMirror symmetry:")
        print(f"  Optimal Z-rotation: {metadata['symmetry_angle']}°")

    if 'upright_rotation' in metadata:
        print(f"\nUpright orientation:")
        print(f"  Final rotation: {metadata['upright_rotation']}")

    # Check vertex displacement
    displacement = np.linalg.norm(v_positioned - v_original, axis=1)
    print(f"\nVertex displacement stats:")
    print(f"  Mean: {displacement.mean():.4f}")
    print(f"  Max: {displacement.max():.4f}")
    print(f"  Min: {displacement.min():.4f}")

    # Update mesh and save in same directory as source
    mesh.vertices = v_positioned
    suffix = "_uzy_only.glb" if uzy_only else "_positioned.glb"
    output_file = input_file.parent / (input_file.stem + suffix)
    mesh.export(str(output_file))
    print(f"\n✓ Saved to: {output_file}")

    # Optionally visualize
    if show_viz:
        print("\nOpening 3D viewer...")
        mesh.show()
    else:
        print("\n(Use --show flag to visualize)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
