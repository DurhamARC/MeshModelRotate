# WRL → GLB pipeline

Converts HoBScan WRL scans into decimated, oriented GLBs with PNG thumbnails for Omeka.
Design, decisions and runbook: `PIPELINE.md` in the omeka workspace.

## Container

pymeshlab (the only WRL reader we have) needs glibc ≥ 2.35; Hamilton (Rocky 8) has 2.28.
The conversion step therefore runs in a container. Hamilton has no fakeroot, so `%post`
def-file builds are impossible there — build with Docker locally and convert the saved image,
which Singularity can do unprivileged.

```bash
# Local
docker build -t hobscan-pipeline pipeline/
docker save hobscan-pipeline -o hobscan-pipeline.tar
rsync -a hobscan-pipeline.tar ham8:/nobackup/jrhq77/pipeline/

# Hamilton
export SINGULARITY_CACHEDIR=/nobackup/jrhq77/.singularity
cd /nobackup/jrhq77/pipeline
singularity build --force pipeline.sif docker-archive://hobscan-pipeline.tar
rm hobscan-pipeline.tar
```

The build fails if pymeshlab's plugins can't load (they `dlopen` system GL libraries and
only warn when missing, after which WRL loading fails with "Unknown format for load: wrl").

Local runs use the same image; always mount source WRLs read-only:

```bash
docker run -i --rm -v "/mnt/srs/HoBScan/Museum Files/<museum>:/in:ro" -v "$PWD/out:/out" \
    hobscan-pipeline python ...
```

Blender is not in the image; renders use the Blender 4.0.2 tarball on `/nobackup`.

## Processing one model

```bash
pipeline/process_model.sh [-f] <input.wrl> <output_dir>
```

| Step | Where | Script | Output |
|------|-------|--------|--------|
| Load, decimate to 200k faces, orient, export | container | `convert.py` (+ `orient.py`) | `<name>.glb`, `<name>.json` (`status: converted`) |
| Render 512² RGBA thumbnail | host Blender | `../render/render_thumbs.py` | `<name>.png` |
| Lossless PNG optimisation | container | `optimise_png.py` | `<name>.png`, `<name>.json` (`status: complete`) |

Models whose JSON says `complete` are skipped; `-f` redoes everything. The input directory is
mounted read-only in the container, and `convert.py` also refuses output locations inside the
input's directory or the SRS source trees (`PIPELINE_PROTECTED` adds more). GLB and JSON are
written to a temp name and renamed, so a killed job never leaves a file that looks finished.

On Hamilton: `PIPELINE_RUNNER=singularity BLENDER=/nobackup/jrhq77/blender-4.0.2-linux-x64/blender`,
and pass `PIPELINE_VERSION` (the code is rsynced into an older checkout, so `git describe` there is wrong).

Orientation tests: `docker run --rm -v "$PWD/pipeline:/code:ro" -w /code hobscan-pipeline python test_orient.py`

## Batch (Hamilton)

After `transfer_to_hamilton.sh "<collection>"` has staged the WRLs:

```bash
cd /nobackup/jrhq77
MeshModelRotate/pipeline/make_manifest.sh "<collection>"    # writes manifests/<collection>.lst, prints the sbatch line
SLURM_ARRAY_TASK_ID=0 MeshModelRotate/pipeline/slurm_process.sh --dry-run "<collection>"   # optional check
sbatch --array=0-<N>%50 --export=ALL,CHUNK_SIZE=20 MeshModelRotate/pipeline/slurm_process.sh "<collection>"
MeshModelRotate/pipeline/summarise.sh "<collection>"        # after the job; exit 1 if anything is missing/bad
```

| Script | Does |
|--------|------|
| `make_manifest.sh` | NUL-separated sorted list of `wrl/<collection>/**/*.wrl`; refuses duplicate stems (outputs are flat); prints the `sbatch` command with `--array` sized to the manifest. Submits nothing. |
| `slurm_process.sh` | Array task *k* runs `process_model.sh` on models `k×CHUNK_SIZE …` into `out/<collection>/`. `shared`, 4 CPUs, 8GB, 1h. A failed model is logged `FAILED` and the rest of the chunk continues; the task exits non-zero if any failed. Resubmit to retry: complete models are skipped. Logs: `logs/hobscan_<job>_<task>.out`. |
| `summarise.sh` | Checks every manifest entry has glb/png/json, JSON `complete`, GLB header shows the expected faces and `COLOR_0`; gathers `FAILED` log lines; lists `curvature_agrees_with_tip: false` models for review. Lists go to `reports/<collection>/<UTC>/` (outside `out/`, so not transferred). `HOBSCAN_OUT` overrides the output dir. |

Syncing code: the Hamilton checkout is older, so rsync `pipeline/` and `render/` over it and write
the version the JSON records:

```bash
rsync -rt --exclude __pycache__ pipeline render ham8:/nobackup/jrhq77/MeshModelRotate/
git describe --always --dirty | ssh ham8 'cat > /nobackup/jrhq77/MeshModelRotate/pipeline/VERSION'
```

## Measured

`Lewes/Slindon_1955_28_1.wrl` (1M faces), Hamilton `test` node, 4 CPUs: **53s total** — load 8.6s,
decimate 11.2s, orient 1.8s, render ~19s, oxipng few s. GLB 4.0MB with vertex colours.

Blender writes the PNG uncompressed (512×512×4 ≈ 1.05MB whatever `compression` says); oxipng takes
it to ~180KB. Denoising is on (OpenImageDenoise), which also helps the PNG compress.
