# MeshModelRotate

Tools for objective positioning and thumbnail rendering of 3D scanned lithic artefacts, developed as part of the AHRC-funded project [*Digital Technologies, Acheulean Handaxes and the Social Landscapes of the Lower Palaeolithic*](https://gtr.ukri.org/projects?ref=AH%2FW009951%2F1) (AH/W009951/1).

---

## Durham University Project Team

| Project Member | Contact | Role | Unit |
|---|---|---|---|
| Dr. [Samantha Finnigan](https://github.com/sjmf) | [samantha.finnigan@dur.ac.uk](mailto:samantha.finnigan@durham.ac.uk) | Research Software Engineer (RSE) | [Advanced Research Computing](https://www.dur.ac.uk/arc/rse/) |
| Dr. Freddie Foulds | [frederick.w.foulds@durham.ac.uk](mailto:frederick.w.foulds@durham.ac.uk) | Researcher Development Manager | [Durham Centre for Academic Development](https://www.durham.ac.uk/departments/academic/durham-centre-for-academic-development/) |
| Matthew Phillips MA MCLIP | [m.e.phillips@durham.ac.uk](mailto:m.e.phillips@durham.ac.uk) | Head of Research and Systems | [University Library and Collections](https://www.durham.ac.uk/library/) |

---

## Two orientation methods

Orienting an artefact to a canonical pose is the core problem here, and this repository holds **two
different answers to it**. They are not interchangeable and they do not generally agree on a pose.

| | [**UZY**](uzy/) — `uzy/positioning.py` | [**PCA + tip curvature**](pca/) — `pipeline/orient.py` |
|---|---|---|
| Orients from | Distribution of **surface normals** (inertia tensor over face normals) | Distribution of **vertices** (PCA on point positions) |
| Source | Grosman et al. 2008, validated against the original MATLAB | Dr Freddie Foulds' method, ported and bug-fixed |
| Steps | Eigenvector analysis → planform optimisation → mirror-symmetry alignment → upright | PCA axes → face to camera → planform search → tip up by curvature |
| Speed | ~2s per model | ~2s per model |
| Use it for | New analytical work, where objective paper-conformant positioning matters and results must be comparable between artefacts | The HoBScan collections pipeline, for continuity with British Museum models already published in Omeka |

The collections pipeline deliberately uses the PCA method rather than UZY: the British Museum GLBs
already uploaded were produced with it, so switching to UZY would silently change the orientation of
everything already published. That decision, and the four faults fixed while porting the method (one
of them mirroring, a scientific error), are documented in [`pca/README.md`](pca/README.md).

---

## Layout

```
MeshModelRotate/
├── uzy/            # Method 1: UZY positioning (Grosman 2008) + MATLAB reference, SLURM batch
├── pca/            # Method 2: PCA + tip curvature — the method, and Freddie's original scripts
├── pipeline/       # Production WRL -> GLB collections pipeline (uses the PCA method)
├── render/         # Headless Blender thumbnail renderer (used by both methods)
├── 3DModels/       # Sample GLBs (Wansunt collection)
├── ToConvert/      # Drop directory for uzy/utilities/mesh2glb.py
└── pyproject.toml, requirements.txt, setup-env.sh/.bat
```

Run commands from the repository root, so relative paths to `3DModels/` and `ToConvert/` resolve.

| Directory | Start here |
|---|---|
| [`uzy/README.md`](uzy/README.md) | UZY usage, Python API, methodology, HPC batch processing |
| [`pca/README.md`](pca/README.md) | The PCA method, what the port fixed, Freddie's originals |
| [`pipeline/README.md`](pipeline/README.md) | WRL → GLB: container, per-model steps, Hamilton batch runbook |
| [`render/README.md`](render/README.md) | Blender thumbnail rendering, local and on Hamilton |

Design, decisions and the running state of the collections work live in `PIPELINE.md` in the parent
`omeka` workspace.

---

## Installation

```bash
# Setup environment
./setup-env.sh          # or setup-env.bat on Windows

# Activate
source .venv/bin/activate
```

Requires Python ≥ 3.9, with trimesh, numpy and scipy; pymeshlab is needed only for the WRL reading
in `pipeline/` (which runs it in a container, since it needs glibc ≥ 2.35).

---

## Scientific Reference

Grosman, L., Smikt, O., & Smilansky, U. (2008). On the application of 3-D scanning technology for the documentation and typology of lithic artifacts. *Journal of Archaeological Science*, 35(12), 3101-3110. doi:10.1016/j.jas.2008.06.011
