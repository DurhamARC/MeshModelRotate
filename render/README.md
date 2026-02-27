# Thumbnail Rendering

Headless batch renderer for GLB mesh files. Produces 512×512 PNG thumbnails
(RGBA, transparent background) using Blender's Cycles engine with vertex colour
materials and a shadow-catcher plane.

Lighting: warm amber key light (upper-left, 75° elevation), dim cool fill,
minimal rim. AgX colour management with slight exposure boost for vertex colour
saturation. Background mid-grey (#6b6b6b).

Output files are named `<basename>_thumb.png` alongside each `.glb`.

## Pipeline overview

For each GLB, the pipeline runs two steps:

1. **Positioning** (`positioning.py`) — applies the UZY algorithm (Grosman 2008)
   to orient the artifact objectively: longest axis vertical, face toward -Z
   (glTF) / -Y (Blender). Outputs `<basename>_positioned.glb`.
2. **Render** (`render_thumbs.py`) — Blender headless render of the positioned
   GLB to a PNG thumbnail.

`pipeline.sh` automates both steps for a directory of GLBs. `render_thumbs.sh`
runs the render step only (if GLBs are already positioned).

## Local setup (Ubuntu/Debian)

Install Blender and a virtual framebuffer:

```bash
sudo apt-get install blender xvfb
```

Install numpy for Blender's bundled Python. Blender 4.0 ships Python 3.12;
use `--target` rather than a venv since Blender's Python is not a standard
interpreter:

```bash
python3.12 -m pip install --target .venv-blender/lib/python3.12/site-packages numpy
```

Install positioning dependencies into the repo venv:

```bash
uv venv --seed
.venv/bin/pip install trimesh numpy scipy
```

## Local usage

```bash
cd render/
./pipeline.sh [OPTIONS] <GLB_DIR>
```

| Flag | Description |
|------|-------------|
| `-j N` | Parallel jobs (default: all CPU cores) |
| `-o DIR` | Write thumbnails to DIR instead of alongside each GLB |
| `-f` | Force re-run even if outputs already exist |
| `--dry-run` | Print what would run without doing anything |

On a quad-core desktop, expect roughly 5–10s per model (positioning dominates).

## Hamilton8 HPC setup

Hamilton8 is a Tier-3 x86 cluster at Durham running Rocky Linux 8 with Slurm.
This is an embarrassingly parallel workload — each GLB is fully independent —
making it well-suited to a Slurm array job.

### One-time setup

```bash
# Download and extract Blender (no sudo required)
cd /nobackup/your_du_user
wget https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz
tar -xf blender-4.0.2-linux-x64.tar.xz

# Install numpy for Blender's bundled Python (3.10 in this tarball)
mkdir -p MeshModelRotate/.venv-blender/lib/python3.10/site-packages
blender-4.0.2-linux-x64/4.0/python/bin/python3.10 -m pip install \
    --target MeshModelRotate/.venv-blender/lib/python3.10/site-packages numpy

# Set up positioning venv
cd MeshModelRotate
module load python/3.12.5
python3 -m venv .venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
.venv/bin/pip install trimesh numpy scipy
```

Note: Blender's bundled Python version varies by release — check
`blender-*/*/python/bin/` to confirm before installing numpy.

### Submitting the job

```bash
mkdir -p /nobackup/your_du_user/logs
sbatch MeshModelRotate/render/slurm_pipeline.sh
```

Monitor progress:

```bash
watch -n 5 'squeue --me; echo "---"; ls /nobackup/your_du_user/glbs/*_positioned_thumb.png | wc -l'
```

Tail a running task's log:

```bash
tail -f /nobackup/your_du_user/logs/thumb_<JOBID>_0.out
```

### Parallelism

The job is split into array tasks of 20 GLBs each (132 tasks for 2,637 files).
This is a reasonable chunk size for Hamilton8, providing a balance between 
scheduler overhead and linearity:

- **Too few files per task** (e.g. 1): Slurm scheduling overhead dominates;
  thousands of array tasks saturate the scheduler.
- **Too many files per task** (e.g. 100): tasks run sequentially for too long,
  wasting node time if one model is slow; less opportunity for load balancing.
- **20 files per task**: ~3–5 minutes per task at Hamilton8 speeds; 132 tasks
  all dispatch quickly and the scheduler handles load balancing naturally.

To resubmit after partial failures (already-completed thumbnails are skipped
automatically):

```bash
sbatch MeshModelRotate/render/slurm_pipeline.sh
```

Check for failures after completion:

```bash
grep -rl "Error\|Traceback" /nobackup/your_du_user/glbs/*_positioned_thumb.log | wc -l
```

### Retrieving results

Once complete, rsync thumbnails back to the Omeka server:

```bash
rsync -av your_du_user@ham8:/nobackup/your_du_user/glbs/*_positioned_thumb.png \
    /home/sam/Code/omeka_vagrant/glbs/
```
