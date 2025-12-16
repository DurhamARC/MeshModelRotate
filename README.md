# GLB Model Rotation Scripts

## Overview

This repository contains scripts for rotating 3D models (GLB format) to a standardized face-on orientation using the methodology described in Grosman et al. 2008. The technique uses mathematical positioning based on the inertia tensor and surface normal distribution to objectively orient lithic artifacts (handaxes) for consistent measurement and documentation.

## Files Inventory

### Python Scripts

#### `glbutils.py`
Utility library for GLB/mesh file operations using the trimesh library.

**Functions:**
- `removeVertexColor(mesh)` - Clears all vertex attributes including color
- `setFaceColor(mesh, color)` - Sets uniform color for all faces
- `getSceneMesh(scene)` - Extracts the first mesh from a scene or returns single mesh

**Dependencies:** `trimesh`

#### `mesh2glb.py`
Batch conversion script for converting mesh files to GLB format.

**Functionality:**
- Converts PLY and WRL (VRML 2.0) files to GLB format
- Uses pymeshlab for formats not supported by trimesh
- Processes files from the `ToConvert` directory
- Optional vertex color removal

**Dependencies:** `pymeshlab`, `trimesh`, `glbutils`

**Input formats:** PLY, WRL, STL, OBJ, OFF, GLB, GLTF

### MATLAB Scripts (in `Gadi's Scripts/`)

#### `positioning.m`
Main orchestration script that implements the complete positioning workflow.

**Inputs:**
- `v` - Vertex array (Nx3 matrix of XYZ coordinates)
- `f` - Face array (Mx3 matrix of vertex indices forming triangles)

**Outputs:**
- `v` - Rotated vertex array

**Processing Steps:**
1. Translates mesh to origin (centers it)
2. Applies UZY positioning based on inertia tensor (calls `UzyPosCm_for_GUI`)
3. Tests three 90° rotations to find maximum projected area (planform view)
4. Re-centers the mesh
5. Applies mirror symmetry rotation about Z-axis (calls `Find_Mirror_Sym`)

#### `UzyPosCm_for_GUI.m`
Implements the core UZY (Uzy Smilansky) positioning method from the Grosman 2008 paper.

**Inputs:**
- `f` - Face array
- `v` - Vertex array

**Outputs:**
- `vr` - Rotated vertices
- `newTtr` - Transformation matrix applied

**Process:**
1. Calculates face normals for all triangles
2. Computes unit normals and triangle areas
3. Calls `Norm2Posing_for_GUI` to get transformation matrix based on surface tensor
4. Applies transformation and checks if inversion is needed (based on center of mass position)

#### `Norm2Posing_for_GUI.m`
Calculates the transformation matrix based on surface normal distribution.

**Inputs:**
- `vn` - Unit normal vectors (Nx3)
- `tra` - Triangle areas (Nx1)
- `SA` - Total surface area (scalar)

**Outputs:**
- `Ttr` - Transformation matrix (3x3)

**Mathematical Method:**
- Constructs the **surface tensor** T where: `T_st = (1/A) * Σ(s_i * n_s^i * n_t^i)`
- Computes eigenvalues and eigenvectors of the surface tensor
- Eigenvector with largest eigenvalue → perpendicular to major symmetry plane (X-axis)
- Eigenvector with smallest eigenvalue → Z-axis
- Middle eigenvector → Y-axis
- Returns orthogonal transformation matrix

#### `Find_Mirror_Sym.m`
Finds the optimal rotation angle around Z-axis for mirror symmetry.

**Inputs:**
- `X`, `Y` - 2D boundary coordinates (outline of object)

**Outputs:**
- `ang` - Optimal rotation angle (degrees)

**Algorithm:**
1. Rotates the 2D outline through 360° (1° increments)
2. For each angle, splits outline into positive/negative X halves
3. Mirrors the negative half and compares to positive half
4. Calculates distance metric between mirrored and actual halves
5. Returns angle that minimizes this distance (best mirror symmetry)

#### `facenormals.m`
Utility function to compute face normal vectors for triangulated meshes.

**Inputs:**
- `f` - Face array (Mx3 matrix of vertex indices)
- `v` - Vertex array (Nx3 matrix of XYZ coordinates)

**Outputs:**
- `fn` - Face normals (Mx3 matrix, magnitude = 2×triangle area)

**Note:** This function was implemented based on the standard cross-product calculation.

## Methodology: Grosman 2008 UZY Positioning

The scripts implement the methodology described in:
> Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D scanning technology for the documentation and typology of lithic artifacts. Journal of Archaeological Science, 35(12), 3101-3110.

### Key Concepts

**Problem:** Traditional manual measurement of asymmetric lithic artifacts suffers from:
- Subjective positioning decisions
- Human measurement errors
- Non-reproducible results between different researchers

**Solution:** Objective algorithmic positioning based on intrinsic object properties

### The UZY Method

1. **Inertia Tensor Positioning**
   - Calculates the inertia tensor assuming uniform mass distribution
   - Computes eigenvectors of the inertia tensor
   - These eigenvectors define the principal axes of the object
   - Provides initial objective orientation

2. **Alternative: Surface Tensor** (also implemented)
   - Uses distribution of surface normals weighted by triangle area
   - Mathematically similar to inertia tensor
   - Eigenvector with largest eigenvalue = direction perpendicular to major symmetry plane

3. **Planform Optimization**
   - Tests rotations to find orientation with maximum projected surface area
   - Represents the "face-on" view of the artifact

4. **Mirror Symmetry**
   - Rotates around vertical axis to align with mirror symmetry plane
   - Ensures consistent left/right orientation

## Input Data Format

### For MATLAB Scripts

**Required inputs:**
- `v` - Vertex matrix: Nx3 array where each row is [x, y, z] coordinates
- `f` - Face matrix: Mx3 array where each row contains 3 vertex indices (1-indexed)

**Example:**
```matlab
v = [0, 0, 0;    % vertex 1
     1, 0, 0;    % vertex 2
     0, 1, 0;    % vertex 3
     0, 0, 1];   % vertex 4

f = [1, 2, 3;    % triangle 1
     1, 2, 4;    % triangle 2
     2, 3, 4;    % triangle 3
     1, 3, 4];   % triangle 4

v_rotated = positioning(v, f);
```

### For Python Scripts

- Input files should be placed in the `ToConvert/` directory
- Supported formats: PLY, WRL, STL, OBJ, OFF, GLB, GLTF
- Files are loaded using trimesh or pymeshlab
- Output GLB files are written to the same directory

## Installation & Setup

### Quick Start with UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast Python package manager. It's the recommended way to set up this project.

UV setup scripts are included `setup-env.sh` for **macOS/Linux**, and `setup-env.bat` for **Windows**.

### Alternative: Standard pip/venv

If you prefer traditional Python tools:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  
# On Windows: .venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

## Usage Instructions

### Python

```bash
# Auto-generate output filename
python "mesh2glb.py" path/to/input.ply

# Specify output filename
python "mesh2glb.py" path/to/input.wrl path/to/output.glb
```

### MATLAB
Add files to convert under the `ToConvert/` directory.

1. **Load your 3D model** (using your preferred method to get vertices and faces)

2. **Call positioning function:**
   ```matlab
   % Assuming you have v (vertices) and f (faces)
   v_positioned = positioning(v, f);
   ```

3. **The script will:**
   - Display progress with a waitbar
   - Return rotated vertices
   - Original face indices remain unchanged

### Complete Pipeline Example (MATLAB)

```matlab
% Load mesh (example using PLY format)
[v, f] = read_ply('artifact.ply');

% Apply positioning
v_rotated = positioning(v, f);

% Save or visualize
trimesh(f, v_rotated(:,1), v_rotated(:,2), v_rotated(:,3));
axis equal;
```

## Dependencies

### Python
- **trimesh** - 3D mesh processing
- **pymeshlab** - MeshLab Python bindings for additional format support
- **numpy** - Array operations (implicit via trimesh)

Install:
```bash
pip install trimesh pymeshlab
```

### MATLAB
- **Base MATLAB** - Core functionality
- **Statistics and Machine Learning Toolbox** - For `boundary()` function
- No additional toolboxes required for core functionality

## Known Issues and Concerns

### Critical Issues

1. **Incomplete facenormals Function** ⚠️
   `UzyPosCm_for_GUI.m` calls `facenormals(f,v)` which an implementation has been made based on the expected functionality

### Design Issues

2. **No Error Handling in MATLAB**
   MATLAB scripts lack error checking for:
   - Invalid mesh topology (NaN vertices, degenerate triangles)
   - Non-manifold geometry
   - Empty meshes

3. **Coordinate System Assumptions**
   Scripts assume a specific coordinate system orientation. No validation that input meshes conform to expected conventions.

### Performance Concerns

4. **Mirror Symmetry Search is Brute Force**
   `Find_Mirror_Sym.m` tests 360 rotations at 1° increments. Could be optimized with:
   - Coarser initial search followed by refinement
   - Gradient-based optimization

### Data Format Issues

6. **Face Indexing**
    MATLAB uses 1-based indexing. When interfacing with Python/trimesh (0-based), indices need conversion.

### Usability Issues

8. **No Command-Line Interface for MATLAB**
    MATLAB scripts require manual function calls from the MATLAB environment.

## Scientific References

Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D scanning technology for the documentation and typology of lithic artifacts. Journal of Archaeological Science, 35(12), 3101-3110. doi:10.1016/j.jas.2008.06.011

## Additional Resources

The methodology produces:
- **Objective positioning** - Reproducible across researchers
- **Standard metric parameters** - Length, width, thickness at various positions
- **3D-only parameters** - Volume, surface area, center of mass position
- **Visual documentation** - Standardized views and cross-sections
