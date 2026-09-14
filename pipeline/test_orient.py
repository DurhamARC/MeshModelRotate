#!/usr/bin/env python
"""Checks for orient.py on a synthetic, chiral, handaxe-like mesh. Plain asserts (no pytest):

    python pipeline/test_orient.py
"""

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

from orient import orient_handaxe


def synthetic_handaxe():
    """Flattened ellipsoid, pointed at one end, domed on one face, with an off-axis bump
    so that a mirrored copy is distinguishable from a rotated one."""
    m = trimesh.creation.icosphere(subdivisions=4)
    v = m.vertices * [35.0, 60.0, 15.0]
    top = v[:, 1] > 0
    v[top, 1] *= 1.6                                   # tip: farther from the centroid
    v[top, 0] *= 1 - 0.6 * v[top, 1] / v[:, 1].max()   # taper to a point
    v[v[:, 2] > 0, 2] *= 1.4                           # one face more domed
    bump = np.exp(-np.sum((v - [25.0, 20.0, 10.0]) ** 2, axis=1) / 150.0)
    v += bump[:, None] * [6.0, 0.0, 4.0]               # chiral marker
    return trimesh.Trimesh(v, m.faces, process=False)


def oriented(mesh, rotation):
    m = mesh.copy()
    M = np.eye(4)
    M[:3, :3] = rotation
    m.apply_transform(M)
    T, info = orient_handaxe(m.vertices)
    m.apply_transform(T)
    return m, info


def main():
    base = synthetic_handaxe()
    assert base.is_watertight and base.volume > 0
    size = base.extents.max()
    rng = np.random.default_rng(0)

    reference, _ = oriented(base, np.eye(3))
    for i in range(20):
        m, info = oriented(base, Rotation.random(random_state=rng).as_matrix())
        assert np.isclose(info["determinant"], 1.0), info["determinant"]
        assert m.volume > 0, "mesh inverted"
        assert info["extent_up"] > info["extent_down"], "tip not up"
        assert np.mean(m.vertices[:, 2] ** 3) > 0, "face choice not applied"
        assert np.allclose(m.vertices.mean(axis=0), 0, atol=1e-6)
        err = np.abs(m.vertices - reference.vertices).max() / size
        assert err < 0.03, f"start {i}: result depends on starting pose ({err:.3f})"

    # A mirrored input is a different object: it must not come out matching the original
    mirrored = base.copy()
    mirrored.vertices[:, 0] *= -1
    mirrored.invert()
    m, _ = oriented(mirrored, np.eye(3))
    assert np.abs(m.vertices - reference.vertices).max() / size > 0.03

    print("orient tests passed")


if __name__ == "__main__":
    main()
