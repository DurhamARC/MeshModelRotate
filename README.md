# UZY Positioning for Lithic Artifacts

Python implementation of the Grosman 2008 UZY positioning methodology for objective, reproducible orientation of 3D scanned lithic artifacts.

---

## Overview

This repository provides a complete Python implementation of the UZY (Uzy Smilansky) positioning method for objectively orienting 3D lithic artifacts. The methodology uses:

- **Eigenvector analysis** of surface normal distribution (inertia tensor)
- **Planform optimization** (maximum projected area for face-on view)
- **Mirror symmetry alignment** (bilateral symmetry detection)
- **Upright orientation** (longest dimension vertical)

This eliminates researcher subjectivity in artifact measurement. The original paper demonstrated 18-28% measurement variation depending on manual positioning choices.

---

## Quick Start

### Installation

#### Option 1: UV (Recommended)
[UV](https://github.com/astral-sh/uv) is a fast Python package manager.

```bash
# Setup environment
./setup-env.sh          # macOS/Linux
# or
setup-env.bat           # Windows

# Activate
source .venv/bin/activate
```

#### Option 2: Standard pip/venv
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Command-Line Usage

```bash
# Process single file (default: save as <input>_positioned.glb)
python positioning.py artifact.glb

# Specify output file
python positioning.py artifact.glb -o output.glb

# UZY positioning only (skip planform/symmetry)
python positioning.py artifact.glb --uzy-only

# Save transformation metadata to JSON
python positioning.py artifact.glb --save-metadata metadata.json

# Verbose output with statistics
python positioning.py artifact.glb --verbose

# Open 3D viewer after processing
python positioning.py artifact.glb --show

# Quiet mode (errors only)
python positioning.py artifact.glb --quiet
```

### Python API Usage

```python
import trimesh
from positioning import positioning

# Load mesh
mesh = trimesh.load('artifact.glb')

# Apply complete positioning
v_positioned, metadata = positioning(
    mesh.vertices,
    mesh.faces,
    include_planform=True,
    include_mirror_symmetry=True
)

# Save result
mesh.vertices = v_positioned
mesh.export('artifact_positioned.glb')

# Check metadata
print(f"Planform rotation: {metadata['planform_rotation_index']}")
print(f"Symmetry angle: {metadata['symmetry_angle']}°")
print(f"Upright rotation: {metadata['upright_rotation']}")
```

---

## Repository Structure

```
MeshModelRotate/
├── positioning.py              # Main implementation (678 lines, production-ready)
├── test_positioning.py         # Single-file test script
├── utilities/
│   ├── test_rotations.py       # Rotation matrix verification
│   ├── glbutils.py             # Mesh utilities
│   └── mesh2glb copy.py        # Format converter
├── 3DModels/                   # Sample GLB files (Wansunt collection)
├── MATLAB/                     # Original MATLAB implementation (reference)
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Pip dependencies
├── setup-env.sh / .bat         # Environment setup scripts
├── CLAUDE.md                   # Development documentation
└── README.md                   # This file
```

---

## Methodology: Grosman 2008 UZY Positioning

The implementation follows the methodology described in:

> Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D scanning technology for the documentation and typology of lithic artifacts. *Journal of Archaeological Science*, 35(12), 3101-3110.

### The 6-Step Pipeline

1. **Center to Origin**
   - Translates mesh bounding box center to (0, 0, 0)

2. **UZY Positioning**
   - Computes eigenvectors of surface normal distribution (inertia tensor)
   - Aligns artifact with principal axes
   - Provides initial objective orientation

3. **Planform Optimization**
   - Tests 3 orthogonal rotations (90° increments)
   - Selects orientation with maximum XY projected area
   - Ensures "face-on" view (lying flat)

4. **Re-center to Origin**
   - Translates to origin after rotation

5. **Mirror Symmetry Alignment**
   - Rotates 360° in 1° steps about Z-axis
   - Finds angle minimizing distance between mirrored halves
   - Ensures consistent left/right orientation

6. **Final Upright Orientation**
   - Identifies longest dimension
   - Rotates to make it vertical (Y-axis)
   - Ensures artifact stands upright

### Performance

- UZY positioning: ~instant
- Planform optimization: ~instant (3 rotations)
- Mirror symmetry: ~1-2 seconds (360° search)
- **Total:** ~2 seconds per artifact

---

## Coordinate System

- **Right-handed coordinate system** (glTF/GLB standard)
- **X-axis:** Width (left/right)
- **Y-axis:** Height (vertical, up/down)
- **Z-axis:** Depth (front/back)

Final output: face-on, symmetry-aligned, upright (longest dimension vertical)

---

## API Reference

### `positioning(vertices, faces, include_planform=True, include_mirror_symmetry=True)`

Complete UZY positioning workflow.

**Parameters:**
- `vertices` (np.ndarray): Nx3 array of vertex coordinates
- `faces` (np.ndarray): Mx3 array of triangle face indices (0-indexed)
- `include_planform` (bool): Enable planform optimization (default: True)
- `include_mirror_symmetry` (bool): Enable symmetry alignment (default: True)

**Returns:**
- `positioned_vertices` (np.ndarray): Nx3 array of final positioned vertices
- `metadata` (dict): Transformation information
  - `center_offset`: Original bounding box center
  - `uzy_transform`: 3x3 UZY transformation matrix
  - `planform_rotation_index`: Selected rotation (0=original, 1=90°X, 2=90°X+90°Y)
  - `planform_areas`: List of 3 projected areas tested
  - `symmetry_angle`: Z-rotation angle in degrees (1-360)
  - `upright_rotation`: Final rotation applied ('Z+90 (X→Y)', 'X+90 (Z→Y)', or 'none')

**Example:**
```python
# Full positioning
v_positioned, meta = positioning(mesh.vertices, mesh.faces)

# UZY only (skip planform/symmetry)
v_uzy, meta = positioning(
    mesh.vertices,
    mesh.faces,
    include_planform=False,
    include_mirror_symmetry=False
)
```

---

## Utilities

### Format Conversion

Convert mesh files to GLB format:

```bash
# Single file
python utilities/mesh2glb.py input.ply output.glb

# Batch conversion
python utilities/mesh2glb.py  # Processes ToConvert/ directory
```

**Supported formats:** PLY, WRL, STL, OBJ, OFF, GLB, GLTF

### Testing & Validation

```bash
# Test rotation matrices
python utilities/test_rotations.py

# Export to MATLAB format
python utilities/save_mat_for_matlab.py artifact.glb
```

---

## Dependencies

### Required
- **trimesh** ≥4.0.0 - 3D mesh processing
- **scipy** ≥1.11.0 - ConvexHull for projected area
- **numpy** ≥1.24.0 - Array operations

### Optional
- **pymeshlab** ≥2022.2 - Additional format support (WRL, etc.)

Install all:
```bash
pip install trimesh scipy numpy pymeshlab
```

---

## Known Issues & Limitations

### Performance
- Mirror symmetry uses brute-force 360° search (could be optimized with gradient descent)

### Data Format
- Input meshes should be manifold, watertight
- No validation for degenerate triangles or NaN vertices
- Face indices must be 0-indexed (Python/NumPy convention)

### Coordinate System
- Assumes right-handed coordinate system (glTF standard)
- No automatic detection/conversion of coordinate system conventions

---

## Reference Implementation

The original MATLAB implementation is available in `MATLAB/` for reference and validation purposes. The Python implementation is recommended for production use.

See `MATLAB/README.md` for details on the MATLAB scripts.

---

## Scientific Reference

Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D scanning technology for the documentation and typology of lithic artifacts. *Journal of Archaeological Science*, 35(12), 3101-3110. doi:10.1016/j.jas.2008.06.011
