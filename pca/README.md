# PCA + tip-curvature orientation (Freddie's method)

The orientation method used for the HoBScan museum collections. Developed by Dr Freddie Foulds and
used for the initial British Museum upload; the maintained implementation is
[`../pipeline/orient.py`](../pipeline/orient.py), with Freddie's originals kept verbatim in
`original/` for reference.

This is **one of two orientation methods** in this repository — see the
[top-level README](../README.md) for how it differs from [UZY](../uzy/) and which to use.

## The algorithm

1. Centre the mesh on its bounding-box midpoint.
2. **PCA** on the vertices: longest axis → Y, widest → X, flattest → Z.
3. Turn the flat face toward the camera (+Z).
4. **Planform search**: rotate about Y in 2° steps, keeping the angle that maximises the XY
   convex-hull area — the largest silhouette, i.e. a face-on view.
5. **Tip detection** by curvature: the smallest local-PCA eigenvalue ratio (k=30 neighbours) over
   the upper portion of the artefact.
6. Orient tip to +Y, butt to −Y, and recentre.

The camera convention that follows from this: the viewer sits on glTF +Z (Blender −Y), Y up.

## Why two methods

UZY orients from the *distribution of surface normals* (an inertia tensor over face normals), which
is what Grosman 2008 specifies and what makes measurements comparable between artefacts. This method
orients from the *distribution of vertices*. They are not equivalent, and they do not generally
agree on a pose.

The collections pipeline uses this method rather than UZY because it is the method Freddie
specified and wrote. The port fixes its faults but keeps its algorithm, rather than substituting a
different archaeological judgement about how a handaxe should be oriented. Note this is *not* a
compatibility constraint: the whole batch is reprocessed from the source WRLs and supersedes the
earlier GLBs entirely. Use UZY for new analytical work where objective, paper-conformant positioning
matters.

## `original/` — Freddie's scripts, unmodified

Byte-identical to `Scripts/` on research storage (`/mnt/srs/HoBScan/Scripts/`).

| File | Does |
|------|------|
| `WRL_Decimator.py` | pymeshlab quadric edge collapse (`preservenormal=True`), writes decimated WRLs |
| `mesh2glb.py` | pymeshlab → temp PLY → trimesh → GLB |
| `Reorientation.py` | `orient_handaxe()` over a folder of GLBs |
| `GLB_Conversion_Reorientation_Pipeline.py` | All three combined |

**These are kept as a reference, not for running.** They are not headless (tkinter folder dialog and
an `input()` prompt), they write temp files inside the source WRL directory, `GLB_Conversion_…`
imports a `glbutils` that is not beside it, and errors are swallowed by bare `except:`.

## What the port changed

`../pipeline/orient.py` reimplements the method for HPC, fixing four faults found while porting.
Full detail, with line numbers, is under "Known issues" in `PIPELINE.md` at the workspace root.

**Mirroring (a scientific error, now fixed).** The original could emit a mirror image rather than a
rotation, via three improper transforms (determinant −1): the `eigh` PCA basis has arbitrary column
signs, and both the "face the camera" and "tip up" steps were single-axis reflections. Whether a
given model came out mirrored depended on parity, with no visible pattern. A mirrored handaxe is a
chirally different object — flake-scar sequences and edge asymmetry read the wrong way round — and
inverted winding makes normals point inward. The port forces the basis to det +1, replaces each flip
with a 180° rotation about a perpendicular axis, asserts det ≈ +1, and records it in the output JSON;
`convert.py` additionally checks the signed volume stays positive.

**Face choice was noise.** `mean(z) < 0` was tested on mesh centred on its own mean, so mean z is
always ~0 and the result came down to floating-point rounding. The port uses the sign of the third
moment of z — deterministic, though still arbitrary between the two faces.

**Planform search could undo the face choice.** Searching 0–178° about Y meant angles past 90°
turned the other face to the camera. The port searches −90–88°, the same set of silhouettes, then
picks the face.

**Curvature tip detection never fired.** Candidates were taken above the 70th percentile of Y, so
the tip was always already at +Y and the flip was unreachable; what actually decided orientation was
the "butt is −Y" check, i.e. the end farther from the centroid goes up. The port keeps that rule and
records 95th-percentile curvature at both ends plus `curvature_agrees_with_tip`, so disagreements
are flagged for review instead of silently deciding. Freddie's max-curvature measure is dominated by
scan noise.

Because every GLB in `GLB Files/` on research storage went through the original script (confirmed by
Freddie, 2026-09-14), any of them may be mirrored; the collections run reprocesses from the source
WRLs.

## Tests

```bash
docker run --rm -v "$PWD/pipeline:/code:ro" -w /code hobscan-pipeline python test_orient.py
```

A synthetic chiral handaxe is oriented from 20 random poses: determinant stays +1, volume stays
positive, the tip ends up up, every pose converges to the same result, and a mirrored input does
*not* match.
