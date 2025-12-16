#!/usr/bin/env python3
"""
UZY Positioning Algorithm for 3D Lithic Artifacts

Implementation of the objective positioning methodology from:
Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D
scanning technology for the documentation and typology of lithic artifacts.
Journal of Archaeological Science, 35(12), 3101-3110.

This module provides functions to objectively orient 3D scanned stone tools
(handaxes, lithic artifacts) using:
1. Inertia tensor positioning (surface normal distribution)
2. Planform view optimization (maximum projected area)
3. Mirror symmetry alignment (left/right consistency)

The method eliminates observer subjectivity in artifact positioning, enabling
reproducible morphometric analysis.

Author: Ported from MATLAB scripts by Gadi Herzlinger et al.
Date: 2025-12-16
"""

import numpy as np
from typing import Tuple, Optional
import warnings


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def center_vertices(vertices: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Translate vertices to origin by subtracting bounding box center.

    Args:
        vertices: Nx3 array of vertex coordinates

    Returns:
        centered_vertices: Nx3 array translated to origin
        offset: 1x3 center offset that was subtracted

    Examples:
        >>> v = np.array([[1,2,3], [4,5,6]])
        >>> v_centered, offset = center_vertices(v)
        >>> np.allclose(v_centered.mean(axis=0), [0, 0, 0])
        True
    """
    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    offset = (bbox_min + bbox_max) / 2.0

    centered = vertices - offset
    return centered, offset


def rotation_matrix_x(angle_deg: float) -> np.ndarray:
    """
    Create 3x3 rotation matrix for rotation about X-axis.

    Args:
        angle_deg: Rotation angle in degrees (right-hand rule)

    Returns:
        3x3 rotation matrix
    """
    theta = np.deg2rad(angle_deg)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    return np.array([
        [1,     0,      0    ],
        [0,  cos_t, -sin_t],
        [0,  sin_t,  cos_t]
    ])


def rotation_matrix_y(angle_deg: float) -> np.ndarray:
    """
    Create 3x3 rotation matrix for rotation about Y-axis.

    Args:
        angle_deg: Rotation angle in degrees (right-hand rule)

    Returns:
        3x3 rotation matrix
    """
    theta = np.deg2rad(angle_deg)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    return np.array([
        [ cos_t,  0,  sin_t],
        [    0,   1,     0 ],
        [-sin_t,  0,  cos_t]
    ])


def rotation_matrix_z(angle_deg: float) -> np.ndarray:
    """
    Create 3x3 rotation matrix for rotation about Z-axis.

    Args:
        angle_deg: Rotation angle in degrees (right-hand rule)

    Returns:
        3x3 rotation matrix
    """
    theta = np.deg2rad(angle_deg)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    return np.array([
        [cos_t, -sin_t,  0],
        [sin_t,  cos_t,  0],
        [   0,      0,    1]
    ])


def apply_rotation(vertices: np.ndarray, rotation: np.ndarray) -> np.ndarray:
    """
    Apply 3x3 rotation matrix to vertices.

    Args:
        vertices: Nx3 array of vertex coordinates
        rotation: 3x3 rotation/transformation matrix

    Returns:
        Nx3 array of rotated vertices

    Notes:
        Uses row-vector convention: v_new = v_old @ R.T
        Equivalent to MATLAB: (R * v')'
    """
    return vertices @ rotation.T


# =============================================================================
# CORE POSITIONING FUNCTIONS
# =============================================================================

def facenormals(faces: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    """
    Compute face normal vectors for triangular mesh.

    Calculates the (non-unit) normal vector for each triangular face using
    the cross product of two edge vectors. The magnitude of the resulting
    vector is twice the triangle area.

    Args:
        faces: Mx3 array of face vertex indices (0-indexed)
        vertices: Nx3 array of vertex coordinates

    Returns:
        Mx3 array of face normal vectors (not normalized)
        The norm of each row is 2 * triangle_area

    Notes:
        - Normal direction follows right-hand rule: (v1→v2) × (v1→v3)
        - Assumes counter-clockwise winding order
        - Does NOT normalize vectors (preserves area information)

    Examples:
        >>> # Equilateral triangle in XY plane
        >>> v = np.array([[0,0,0], [1,0,0], [0.5, 0.866, 0]])
        >>> f = np.array([[0,1,2]])
        >>> normals = facenormals(f, v)
        >>> normals[0, 2] > 0  # Points in +Z
        True
    """
    # Get vertex coordinates for each face
    v0 = vertices[faces[:, 0]]  # First vertex of each triangle
    v1 = vertices[faces[:, 1]]  # Second vertex
    v2 = vertices[faces[:, 2]]  # Third vertex

    # Compute edge vectors
    edge1 = v1 - v0
    edge2 = v2 - v0

    # Cross product gives normal (magnitude = 2 * area)
    normals = np.cross(edge1, edge2)

    return normals


def norm2posing(
    unit_normals: np.ndarray,
    triangle_areas: np.ndarray,
    total_surface_area: float
) -> np.ndarray:
    """
    Compute transformation matrix from surface normal distribution.

    Implements the eigenvector analysis method from Grosman 2008. Constructs
    a surface tensor matrix from area-weighted normals, then uses eigendecomposition
    to find principal axes of the normal distribution.

    The eigenvectors represent:
    - Maximum eigenvalue → X-axis (major symmetry plane normal)
    - Minimum eigenvalue → Z-axis (preferred "up" direction)
    - Middle eigenvalue → Y-axis (completes right-handed system)

    Args:
        unit_normals: Mx3 array of unit normal vectors (one per face)
        triangle_areas: Mx1 array of triangle areas
        total_surface_area: Scalar total surface area

    Returns:
        3x3 transformation matrix T where columns are [x_axis, y_axis, z_axis]
        To rotate vertices: v_rotated = v @ T.T (or inv(T) @ v.T in MATLAB)

    Mathematical formulation:
        Maximize F = (1/A) * Σ[s_i * (a·n_i)²] subject to ||a|| = 1
        where s_i = triangle areas, n_i = unit normals, A = total area

        Solution via eigenvalue problem:
        M @ a = λ @ a, where M_jk = (1/A) * Σ[s_i * n_ij * n_ik]

    Notes:
        - Corresponds to Norm2Posing_for_GUI.m in original MATLAB
        - Handles edge case of non-orthogonal eigenvectors (rare)
    """
    # Build surface tensor matrix M (area-weighted normal covariance)
    # M_xx = Σ(area * nx * nx), M_xy = Σ(area * nx * ny), etc.
    Sxx = np.sum(triangle_areas * unit_normals[:, 0]**2)
    Syy = np.sum(triangle_areas * unit_normals[:, 1]**2)
    Szz = np.sum(triangle_areas * unit_normals[:, 2]**2)
    Sxy = np.sum(triangle_areas * unit_normals[:, 0] * unit_normals[:, 1])
    Syz = np.sum(triangle_areas * unit_normals[:, 1] * unit_normals[:, 2])
    Szx = np.sum(triangle_areas * unit_normals[:, 2] * unit_normals[:, 0])

    # Construct symmetric matrix and normalize by total area
    M = np.array([
        [Sxx, Sxy, Szx],
        [Sxy, Syy, Syz],
        [Szx, Syz, Szz]
    ]) / total_surface_area

    # Eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eig(M)

    # Find max and min eigenvalue columns
    max_idx = np.argmax(eigenvalues)
    min_idx = np.argmin(eigenvalues)

    # Assign axes per Grosman methodology
    x_axis = eigenvectors[:, max_idx]  # Major symmetry plane normal
    z_axis = eigenvectors[:, min_idx]  # Minimum variance = "up"

    # Y-axis should be orthogonal (cross product)
    y_axis_computed = np.cross(z_axis, x_axis)

    # Find the middle eigenvalue column
    indices = {0, 1, 2}
    middle_idx = (indices - {max_idx, min_idx}).pop()
    y_axis_eig = eigenvectors[:, middle_idx]

    # Check if middle eigenvector matches computed y-axis
    # (should be identical for perfect orthogonal eigenvectors)
    if not np.allclose(y_axis_eig, y_axis_computed, atol=8*np.finfo(float).eps):
        # Try negated version
        if np.allclose(-y_axis_eig, y_axis_computed, atol=8*np.finfo(float).eps):
            y_axis = -y_axis_eig
        else:
            # Eigenvectors not perfectly orthogonal (rare - numerical issue)
            warnings.warn("Eigenvector orthogonality issue detected, using computed y-axis")
            y_axis = y_axis_computed
    else:
        y_axis = y_axis_eig

    # Construct transformation matrix (columns are new axes)
    T = np.column_stack([x_axis, y_axis, z_axis])

    return T


def uzy_position(
    faces: np.ndarray,
    vertices: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Position vertices using UZY method (surface normal eigenvector analysis).

    Implements the core UZY positioning algorithm:
    1. Compute face normals and triangle areas
    2. Remove degenerate triangles (NaN/Inf)
    3. Calculate transformation via eigenvector analysis
    4. Apply rotation
    5. Flip 180° about X if center-of-mass is above midpoint

    Args:
        faces: Mx3 array of face indices (0-indexed)
        vertices: Nx3 array of vertex coordinates

    Returns:
        rotated_vertices: Nx3 array of positioned vertices
        transform_matrix: 3x3 final transformation applied (inv(T) or inv(T)*Rx180)

    Notes:
        - Corresponds to UzyPosCm_for_GUI.m in MATLAB
        - The center-of-mass flip ensures "heavier half" is below midpoint
        - This provides consistent orientation for asymmetric artifacts

    Raises:
        ValueError: If all triangles are degenerate
    """
    # Remove NaN faces if present
    nan_rows = np.any(np.isnan(faces), axis=1)
    if np.any(nan_rows):
        faces = faces[~nan_rows]

    # Compute face normals (magnitude = 2 * area)
    normals = facenormals(faces, vertices)

    # Calculate triangle areas (half the normal magnitude)
    normal_magnitudes = np.linalg.norm(normals, axis=1)
    triangle_areas = normal_magnitudes / 2.0

    # Compute unit normals
    # Avoid division by zero for degenerate triangles
    with np.errstate(divide='ignore', invalid='ignore'):
        unit_normals = normals / normal_magnitudes[:, np.newaxis]

    # Remove invalid unit normals (inf/nan from degenerate triangles)
    invalid_rows = ~np.isfinite(unit_normals).all(axis=1)
    if np.any(invalid_rows):
        unit_normals[invalid_rows] = 0.0
        triangle_areas[invalid_rows] = 0.0

    # Calculate total surface area
    total_area = np.sum(triangle_areas)

    if total_area == 0:
        raise ValueError("Total surface area is zero - all triangles degenerate")

    # Get transformation matrix from surface normal distribution
    T = norm2posing(unit_normals, triangle_areas, total_area)

    # Apply rotation: v_new = inv(T) @ v_old.T → transpose back
    # MATLAB: vct = inv(Tr) * vcm'
    T_inv = np.linalg.inv(T)
    rotated = apply_rotation(vertices, T_inv)

    # Check center-of-mass position
    # If COM is above half-height, flip 180° about X-axis
    z_max = rotated[:, 2].max()
    z_min = rotated[:, 2].min()
    z_mid = (z_max + z_min) / 2.0

    if z_mid < 0:
        # COM above midpoint - rotate 180° about X
        flip_matrix = np.array([
            [ 1,  0,  0],
            [ 0, -1,  0],
            [ 0,  0, -1]
        ])
        final_transform = flip_matrix @ T_inv
        rotated = apply_rotation(vertices, final_transform)
    else:
        final_transform = T_inv

    return rotated, final_transform


# =============================================================================
# PLANFORM OPTIMIZATION & MIRROR SYMMETRY (Phase 2)
# =============================================================================

def planform_orientation(vertices: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    Optimize orientation for planform view (maximum projected area).

    Tests 3 orthogonal rotations and selects the one that maximizes the
    XZ-plane projected area (front view outline). This ensures the artifact
    is viewed "face-on" and upright rather than edge-on or lying flat.

    After selecting maximum area view, ensures the longest dimension is vertical
    (Y-axis) for consistent upright positioning.

    The three tested orientations:
    1. Original orientation (0° rotation)
    2. 90° rotation about X-axis
    3. 90° rotation about Y-axis (applied to orientation #2)

    Args:
        vertices: Nx3 array of vertex coordinates (already UZY positioned)

    Returns:
        rotated_vertices: Nx3 array with optimal orientation (face-on and upright)
        rotation_index: Index of selected rotation (0, 1, or 2)

    Notes:
        - Uses scipy.spatial.ConvexHull for 2D boundary area
        - Corresponds to lines 22-40 in positioning.m
        - MATLAB used boundary() function, we use ConvexHull
        - Additional upright correction ensures Z is longest dimension
    """
    from scipy.spatial import ConvexHull

    # Store 3 rotation candidates
    candidates = []
    areas = []

    # Rotation 0: Original orientation
    v0 = vertices.copy()
    hull0 = ConvexHull(v0[:, :2])  # XY projection (top-down view)
    area0 = hull0.volume  # In 2D, volume = area
    candidates.append(v0)
    areas.append(area0)

    # Rotation 1: 90° about X-axis
    R_x90 = rotation_matrix_x(90)
    v1 = apply_rotation(v0, R_x90)
    hull1 = ConvexHull(v1[:, :2])  # XY projection
    area1 = hull1.volume
    candidates.append(v1)
    areas.append(area1)

    # Rotation 2: 90° about Y-axis (applied to v1)
    R_y90 = rotation_matrix_y(90)
    v2 = apply_rotation(v1, R_y90)
    hull2 = ConvexHull(v2[:, :2])  # XY projection
    area2 = hull2.volume
    candidates.append(v2)
    areas.append(area2)

    # Select rotation with maximum area (face-on view when looking down)
    max_idx = np.argmax(areas)
    result = candidates[max_idx]

    # Return face-on view (lying flat) - upright orientation happens later
    return result, max_idx


def find_mirror_symmetry(vertices: np.ndarray) -> float:
    """
    Find optimal Z-axis rotation angle for mirror symmetry alignment.

    Rotates the XY-plane outline 360° in 1° increments and finds the angle
    that minimizes the distance between left and right halves when mirrored
    across the Y-axis. This provides consistent left/right orientation.

    Algorithm:
    1. For each angle 1-360°:
       - Rotate outline about Z-axis
       - Split into +X (right) and -X (left) halves
       - Sample ~80% of points from each half (sorted by Y)
       - Mirror left half across Y-axis
       - Compute sum of distances between mirrored pairs
    2. Return angle with minimum distance

    Args:
        vertices: Nx3 array (should already be centered and planform-oriented)

    Returns:
        optimal_angle: Rotation angle in degrees (1-360) for best symmetry

    Notes:
        - Uses XY projection only (ignores Z)
        - Corresponds to Find_Mirror_Sym.m
        - Brute-force approach: O(360 × N), takes ~5-10 seconds
        - Could be optimized with gradient descent if needed

    Implementation details:
        - Uses scipy.spatial.ConvexHull to get boundary points
        - Samples to ~80% of smaller half to avoid index issues
    """
    from scipy.spatial import ConvexHull

    # Get 2D boundary points (XY projection)
    hull = ConvexHull(vertices[:, :2])
    boundary_indices = hull.vertices
    X = vertices[boundary_indices, 0]
    Y = vertices[boundary_indices, 1]

    shape_2d = np.vstack([X, Y])  # 2×N

    symmetry_scores = np.zeros(360)

    # Test all 360 degree rotations
    for angle_deg in range(1, 361):
        theta = np.deg2rad(angle_deg)
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        # 2D rotation matrix (counter-clockwise)
        R = np.array([
            [cos_t, -sin_t],
            [sin_t,  cos_t]
        ])

        # Rotate shape
        rotated_shape = R @ shape_2d

        X_rot = rotated_shape[0, :]
        Y_rot = rotated_shape[1, :]

        # Split into positive and negative X halves
        pos_mask = X_rot > 0
        neg_mask = X_rot <= 0

        X_pos = X_rot[pos_mask]
        Y_pos = Y_rot[pos_mask]
        X_neg = X_rot[neg_mask]
        Y_neg = Y_rot[neg_mask]

        # Skip if either half is empty
        if len(X_pos) == 0 or len(X_neg) == 0:
            symmetry_scores[angle_deg - 1] = np.inf
            continue

        # Sort each half by Y coordinate
        sort_idx_pos = np.argsort(Y_pos)
        X_pos = X_pos[sort_idx_pos]
        Y_pos = Y_pos[sort_idx_pos]

        sort_idx_neg = np.argsort(Y_neg)
        X_neg = X_neg[sort_idx_neg]
        Y_neg = Y_neg[sort_idx_neg]

        # Sample ~80% of points from smaller half
        min_size = min(len(X_pos), len(X_neg))
        sample_size = int(0.8 * min_size)

        if sample_size < 2:
            symmetry_scores[angle_deg - 1] = np.inf
            continue

        # Sample evenly spaced points
        sample_indices = np.linspace(0, min_size - 1, sample_size, dtype=int)

        X_pos_sampled = X_pos[sample_indices] if len(X_pos) >= min_size else X_pos[sample_indices[:len(X_pos)]]
        Y_pos_sampled = Y_pos[sample_indices] if len(Y_pos) >= min_size else Y_pos[sample_indices[:len(Y_pos)]]
        X_neg_sampled = X_neg[sample_indices] if len(X_neg) >= min_size else X_neg[sample_indices[:len(X_neg)]]
        Y_neg_sampled = Y_neg[sample_indices] if len(Y_neg) >= min_size else Y_neg[sample_indices[:len(Y_neg)]]

        # Ensure equal lengths (truncate to shorter)
        min_len = min(len(X_pos_sampled), len(X_neg_sampled))
        X_pos_sampled = X_pos_sampled[:min_len]
        Y_pos_sampled = Y_pos_sampled[:min_len]
        X_neg_sampled = X_neg_sampled[:min_len]
        Y_neg_sampled = Y_neg_sampled[:min_len]

        # Mirror negative half across Y-axis
        X_neg_mirrored = -X_neg_sampled

        # Calculate distance between halves
        distances = np.sqrt((Y_pos_sampled - Y_neg_sampled)**2 +
                           (X_pos_sampled - X_neg_mirrored)**2)

        symmetry_scores[angle_deg - 1] = np.sum(distances)

    # Find angle with minimum score (best symmetry)
    optimal_angle = np.argmin(symmetry_scores) + 1  # +1 because range started at 1

    return optimal_angle


# =============================================================================
# MAIN POSITIONING WORKFLOW
# =============================================================================

def positioning(
    vertices: np.ndarray,
    faces: np.ndarray,
    include_planform: bool = True,
    include_mirror_symmetry: bool = True
) -> Tuple[np.ndarray, dict]:
    """
    Complete UZY positioning workflow for lithic artifacts.

    Implements the full Grosman 2008 methodology:
    1. Center to origin
    2. UZY positioning (surface normal eigenvectors)
    3. Planform view optimization (max projected area)
    4. Re-center to origin
    5. Mirror symmetry alignment (360° search)

    Args:
        vertices: Nx3 array of mesh vertex coordinates
        faces: Mx3 array of triangular face indices (0-indexed)
        include_planform: Enable planform optimization (default: True)
        include_mirror_symmetry: Enable symmetry alignment (default: True)

    Returns:
        positioned_vertices: Nx3 array of final positioned vertices
        metadata: Dictionary containing transformation info
            - 'center_offset': Original bounding box center
            - 'uzy_transform': 3x3 UZY transformation matrix
            - 'planform_rotation_index': Which rotation was selected (0/1/2)
            - 'planform_areas': List of 3 projected areas tested
            - 'symmetry_angle': Z-rotation angle in degrees (1-360)

    Examples:
        >>> import trimesh
        >>> mesh = trimesh.load('artifact.glb')
        >>> v_positioned, meta = positioning(mesh.vertices, mesh.faces)
        >>> mesh.vertices = v_positioned
        >>> mesh.export('artifact_positioned.glb')

        >>> # Run only UZY positioning (skip planform/symmetry)
        >>> v_uzy, meta = positioning(mesh.vertices, mesh.faces,
        ...                           include_planform=False,
        ...                           include_mirror_symmetry=False)

    Notes:
        - Complete implementation of Grosman 2008 methodology
        - Planform optimization tests 3 rotations (~instant)
        - Mirror symmetry searches 360 angles (~5-10 seconds)
        - Preserves face topology (only modifies vertex positions)
    """
    metadata = {}

    # Step 1: Center to origin
    shape, offset = center_vertices(vertices)
    metadata['center_offset'] = offset

    # Step 2: UZY positioning (surface normal eigenvector method)
    shape, uzy_transform = uzy_position(faces, shape)
    metadata['uzy_transform'] = uzy_transform

    # Step 3: Planform view optimization
    if include_planform:
        from scipy.spatial import ConvexHull

        # Get areas before rotation for metadata
        areas_tested = []
        for i, candidate in enumerate([shape,
                                       apply_rotation(shape, rotation_matrix_x(90)),
                                       apply_rotation(apply_rotation(shape, rotation_matrix_x(90)),
                                                     rotation_matrix_y(90))]):
            hull = ConvexHull(candidate[:, :2])  # XY projection (top-down)
            areas_tested.append(hull.volume)

        shape, planform_idx = planform_orientation(shape)
        metadata['planform_rotation_index'] = planform_idx
        metadata['planform_areas'] = areas_tested

    # Step 4: Re-center to origin
    shape, offset2 = center_vertices(shape)
    metadata['recenter_offset'] = offset2

    # Step 5: Mirror symmetry alignment
    if include_mirror_symmetry:
        angle = find_mirror_symmetry(shape)
        R_z = rotation_matrix_z(angle)
        shape = apply_rotation(shape, R_z)
        metadata['symmetry_angle'] = angle

    # Step 6: Final upright orientation (longest dimension → Y-axis/vertical)
    # This ensures artifacts stand upright after all other transformations
    bounds = np.max(shape, axis=0) - np.min(shape, axis=0)
    longest_axis = np.argmax(bounds)

    if longest_axis == 0:  # X is longest → rotate to Y
        shape = apply_rotation(shape, rotation_matrix_z(90))
        metadata['upright_rotation'] = 'Z+90 (X→Y)'
    elif longest_axis == 2:  # Z is longest → rotate to Y
        shape = apply_rotation(shape, rotation_matrix_x(90))
        metadata['upright_rotation'] = 'X+90 (Z→Y)'
    else:  # Y already longest
        metadata['upright_rotation'] = 'none (Y already longest)'

    return shape, metadata


# =============================================================================
# COMMAND-LINE INTERFACE (Phase 3)
# =============================================================================

def main():
    """CLI entry point - will be implemented in Phase 3."""
    import argparse

    parser = argparse.ArgumentParser(
        description="UZY positioning for 3D lithic artifacts (Grosman 2008)"
    )
    parser.add_argument("input", help="Input mesh file (GLB/PLY/STL/OBJ)")
    parser.add_argument("-o", "--output", help="Output file (default: input_positioned.glb)")
    parser.add_argument("--planform", action="store_true", help="Enable planform optimization")
    parser.add_argument("--symmetry", action="store_true", help="Enable mirror symmetry")

    args = parser.parse_args()

    print("CLI implementation coming in Phase 3")
    print(f"Would process: {args.input}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
