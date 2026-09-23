# MATLAB UZY Positioning Scripts (Reference Implementation)

**Status:** Reference implementation - Python version is production-ready

This directory contains the MATLAB implementation by Gadi Herzlinger of the Grosman 2008 UZY positioning methodology. These scripts are provided for reference and validation purposes. The Python implementation in `positioning.py` is complete and recommended for production use.

---

## MATLAB Scripts

### `positioning.m`
Main orchestration script that implements the complete positioning workflow.

**Inputs:**
- `v` - Vertex array (Nx3 matrix of XYZ coordinates)
- `f` - Face array (Mx3 matrix of vertex indices forming triangles, 1-indexed)

**Outputs:**
- `v` - Rotated vertex array

**Processing Steps:**
1. Translates mesh to origin (centers it)
2. Applies UZY positioning based on inertia tensor (calls `UzyPosCm_for_GUI`)
3. Tests three 90° rotations to find maximum projected area (planform view)
4. Re-centers the mesh
5. Applies mirror symmetry rotation about Z-axis (calls `Find_Mirror_Sym`)

### `UzyPosCm_for_GUI.m`
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

### `Norm2Posing_for_GUI.m`
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

### `Find_Mirror_Sym.m`
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

### `facenormals.m`
Utility function to compute face normal vectors for triangulated meshes.

**Inputs:**
- `f` - Face array (Mx3 matrix of vertex indices, 1-indexed)
- `v` - Vertex array (Nx3 matrix of XYZ coordinates)

**Outputs:**
- `fn` - Face normals (Mx3 matrix, magnitude = 2×triangle area)

**Note:** This function was implemented based on the standard cross-product calculation.

---

## Input Data Format

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

---

## Usage

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

### Complete Pipeline Example

```matlab
% Load mesh (example using PLY format)
[v, f] = read_ply('artifact.ply');

% Apply positioning
v_rotated = positioning(v, f);

% Save or visualize
trimesh(f, v_rotated(:,1), v_rotated(:,2), v_rotated(:,3));
axis equal;
```

---

## Dependencies

- **Base MATLAB** - Core functionality
- **Statistics and Machine Learning Toolbox** - For `boundary()` function

---

## Known Issues

### Design Issues

1. **No Error Handling**
   MATLAB scripts lack error checking for:
   - Invalid mesh topology (NaN vertices, degenerate triangles)
   - Non-manifold geometry
   - Empty meshes

2. **Coordinate System Assumptions**
   Scripts assume a specific coordinate system orientation. No validation that input meshes conform to expected conventions.

### Performance Concerns

3. **Mirror Symmetry Search is Brute Force**
   `Find_Mirror_Sym.m` tests 360 rotations at 1° increments. Could be optimized with:
   - Coarser initial search followed by refinement
   - Gradient-based optimization

### Usability Issues

4. **No Command-Line Interface**
   MATLAB scripts require manual function calls from the MATLAB environment.

5. **Face Indexing**
   MATLAB uses 1-based indexing. When interfacing with Python/trimesh (0-based), indices need conversion.

---

## For Production Use

**Use the Python implementation instead:**
- See `../positioning.py` for complete, production-ready implementation
- Includes error handling, type safety, and batch processing support
- Command-line interface and SLURM HPC integration
- No MATLAB license required
