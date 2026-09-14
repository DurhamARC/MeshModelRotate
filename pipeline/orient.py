"""Handaxe orientation: Freddie Foulds' PCA method, ported for batch use.

Result: length along Y (tip up), width along X, flattest axis along Z, face-on to a
camera on +Z, centred on the vertex mean.

Differences from FreddieScripts/Reorientation.py (see PIPELINE.md "Known issues"):
- Proper rotations only. The PCA basis is forced to det +1 and every axis flip is replaced
  by a 180 degree rotation, so the artefact is never mirrored.
- Face choice is deterministic. The original compared mean z to 0, which is always ~0
  after centring, so which face showed was down to floating-point noise. We use the sign
  of the third moment (skew) of z instead.
- Planform search runs before the face choice, so it can't undo it.
- Tip: in the original, the curvature step could never flip (its candidates are all in
  the top 30% of Y, so tip_y > 0), and the "confirm butt is -Y" extent test decided.
  We keep the extent test as the rule and record curvature at both ends as a diagnostic.
- Curvature is vectorised (one batched kd-tree query rather than a loop per vertex).
"""

import numpy as np
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.qhull import QhullError

# 180 degree rotations used in place of Freddie's single-axis flips
ROT180_Y = np.diag([-1.0, 1.0, -1.0])  # turns the other face towards +Z, tip stays up
ROT180_Z = np.diag([-1.0, -1.0, 1.0])  # turns the other end up, face stays towards +Z


def rotation_y(angle_deg):
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def projected_area(vertices):
    """Area of the convex hull of the XY projection."""
    try:
        return ConvexHull(vertices[:, :2]).volume
    except QhullError:
        return 0.0


def local_planarity(vertices, query, k=30):
    """Freddie's curvature measure: smallest eigenvalue / eigenvalue sum of the covariance
    of each query point's k nearest neighbours. High values = sharp regions."""
    _, idx = cKDTree(vertices).query(query, k=k)
    local = vertices[idx]
    local = local - local.mean(axis=1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", local, local) / (k - 1)
    eig = np.linalg.eigvalsh(cov)
    total = eig.sum(axis=1)
    return np.divide(eig[:, 0], total, out=np.zeros_like(total), where=total > 0)


def _end_curvature(v, fraction=0.3):
    """Max and 95th-percentile curvature over the top and bottom `fraction` of Y."""
    y = v[:, 1]
    out = {}
    for end, mask in (("top", y > np.quantile(y, 1 - fraction)),
                      ("bottom", y < np.quantile(y, fraction))):
        c = local_planarity(v, v[mask])
        out[end] = {"max": float(c.max()), "p95": float(np.quantile(c, 0.95))}
    return out


def orient_handaxe(vertices, planform_step=2.0):
    """Return (4x4 transform, info dict) orienting the handaxe. Does not modify input."""
    v0 = np.asarray(vertices, dtype=float)
    centre = v0.mean(axis=0)
    v = v0 - centre

    # PCA: length -> Y, width -> X, flattest -> Z
    evals, evecs = np.linalg.eigh(np.cov(v.T))
    evecs = evecs[:, np.argsort(evals)[::-1]]
    basis = np.column_stack((evecs[:, 1], evecs[:, 0], evecs[:, 2]))
    pca_sign_fixed = bool(np.linalg.det(basis) < 0)
    if pca_sign_fixed:
        basis[:, 2] *= -1  # eigenvector sign is arbitrary; pick the one giving a rotation
    R = basis.T
    v = v @ basis

    # Planform: rotate about the length axis to maximise the face-on silhouette.
    # Rotations by a and a+180 give the same area; searching [-90, 90) keeps the +Z face.
    best_area, best_angle = -1.0, 0.0
    for angle in np.arange(-90.0, 90.0, planform_step):
        area = projected_area(v @ rotation_y(angle).T)
        if area > best_area:
            best_area, best_angle = area, float(angle)
    Ry = rotation_y(best_angle)
    v = v @ Ry.T
    R = Ry @ R

    # Face towards the camera (+Z): deterministic choice by skew of z
    face_turned = bool(np.mean(v[:, 2] ** 3) < 0)
    if face_turned:
        v = v @ ROT180_Y.T
        R = ROT180_Y @ R

    # Tip up: the end farther from the centroid goes to +Y (Freddie's deciding rule)
    tip_turned = bool(v[:, 1].max() < -v[:, 1].min())
    if tip_turned:
        v = v @ ROT180_Z.T
        R = ROT180_Z @ R

    # Diagnostic: is the upper end also the sharper one, as #98 intends?
    curvature = _end_curvature(v)
    # p95 rather than Freddie's max: the max over small patches is dominated by scan noise
    curvature_agrees = curvature["top"]["p95"] >= curvature["bottom"]["p95"]

    det = float(np.linalg.det(R))
    if not np.isclose(det, 1.0, atol=1e-6):
        raise RuntimeError(f"orientation is not a proper rotation (det={det})")

    offset = v.mean(axis=0)
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = -R @ centre - offset

    info = {
        "method": "pca-freddie-v2",
        "determinant": det,
        "pca_sign_fixed": pca_sign_fixed,
        "planform_angle_deg": best_angle,
        "planform_area": float(best_area),
        "face_turned": face_turned,
        "tip_turned": tip_turned,
        "extent_up": float(v[:, 1].max() - offset[1]),
        "extent_down": float(offset[1] - v[:, 1].min()),
        "curvature": curvature,
        "curvature_agrees_with_tip": bool(curvature_agrees),
        "transform": M.tolist(),
    }
    return M, info
