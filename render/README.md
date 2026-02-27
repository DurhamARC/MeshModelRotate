# Thumbnail Rendering

Headless batch renderer for GLB mesh files. Produces 512×512 JPEG thumbnails
using Blender's Cycles engine with vertex colour materials.

Lighting matches the ModelViewer Omeka module: three equal sun lamps (front,
left, right) plus a low-intensity ambient, against a mid-grey background.

Output files are named `<basename>_thumb.jpg` alongside each `.glb`.

## Requirements

- **Blender 4.x** — `sudo apt-get install blender xvfb`
- **numpy** for Blender's Python (3.12) — installed into an isolated directory,
  not system Python:

```bash
python3.12 -m pip install --target .venv-blender/lib/python3.12/site-packages numpy
```

Run from the repo root (i.e. `.venv-blender/` sits alongside `render/`).

## Usage

```bash
cd render/
./render_thumbs.sh [OPTIONS] <GLB_DIR>
```

### Options

| Flag | Description |
|------|-------------|
| `-j N` | Parallel jobs (default: all CPU cores) |
| `-o DIR` | Write thumbnails to DIR instead of alongside each GLB |
| `-f` | Force re-render even if thumbnail already exists |
| `--dry-run` | Print what would be rendered without doing anything |

### Examples

```bash
# Render everything in a directory
./render_thumbs.sh /data/models/

# Use 2 cores, output thumbnails to a separate directory
./render_thumbs.sh -j 2 -o /data/thumbs/ /data/models/

# Preview what would run
./render_thumbs.sh --dry-run /data/models/
```

Failed renders leave a `<basename>_thumb.log` alongside the GLB for inspection.
