# Conversion environment for the WRL -> GLB pipeline.
#
# pymeshlab wheels need glibc >= 2.35; Hamilton (Rocky 8) has 2.28, so this runs as a
# Singularity image there. Hamilton has no fakeroot, so we build with Docker locally and
# convert the saved image on Hamilton (see pipeline/README.md):
#
#   docker build -t hobscan-pipeline pipeline/
#   docker save hobscan-pipeline -o hobscan-pipeline.tar
#   singularity build pipeline.sif docker-archive://hobscan-pipeline.tar
#
# Blender is NOT included; the render step uses the Blender tarball on /nobackup.

FROM python:3.12-slim-bookworm

# Shared libraries pymeshlab's bundled Qt/MeshLab plugins link against
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libopengl0 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        pymeshlab==2025.7.post1 \
        trimesh==4.11.2 \
        numpy==2.4.2 \
        scipy==1.17.1 \
        pyoxipng==9.1.1

# Fail the build if anything won't import, or if pymeshlab's plugins (which dlopen system
# libs, failing only with a warning) can't read VRML and decimate.
RUN python -c "import trimesh, numpy, scipy, oxipng" \
    && printf '#VRML V2.0 utf8\nShape { geometry IndexedFaceSet { coord Coordinate { point [0 0 0, 1 0 0, 0 1 0, 0 0 1] } coordIndex [0 1 2 -1, 0 1 3 -1, 0 2 3 -1, 1 2 3 -1] } }\n' > /tmp/t.wrl \
    && python -c "import pymeshlab as ml; ms = ml.MeshSet(); ms.load_new_mesh('/tmp/t.wrl'); \
ms.apply_filter('meshing_decimation_quadric_edge_collapse', targetfacenum=2); print('pymeshlab ok')" \
    && rm /tmp/t.wrl
