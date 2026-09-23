import pymeshlab as ml
import trimesh
import glbutils
import os
import tempfile
import numpy as np
import tkinter as tk
from tkinter import filedialog

from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation


# =========================================================
# ROTATION UTILITY
# =========================================================

def rotation_matrix(axis, angle_deg):

    return Rotation.from_rotvec(
        np.radians(angle_deg) * np.asarray(axis)
    ).as_matrix()


# =========================================================
# PROJECTED AREA
# =========================================================

def projected_area(vertices):

    points = vertices[:, [0, 1]]

    try:

        hull = ConvexHull(points)

        return hull.volume

    except:

        return 0


# =========================================================
# CURVATURE ESTIMATION
# =========================================================

def estimate_vertex_curvature(vertices, neighbours=30):
    """
    Estimate local curvature using deviation
    from local PCA plane.

    High values indicate sharp regions
    such as the tip.
    """

    tree = cKDTree(vertices)

    curvature = np.zeros(
        len(vertices)
    )

    for i, vertex in enumerate(vertices):

        _, idx = tree.query(
            vertex,
            k=neighbours
        )

        local = vertices[idx].copy()

        local -= local.mean(axis=0)

        covariance = np.cov(
            local.T
        )

        eigenvalues = np.linalg.eigvalsh(
            covariance
        )

        # Smallest eigenvalue represents
        # deviation from local plane

        curvature[i] = (
            eigenvalues[0]
            /
            eigenvalues.sum()
        )

    return curvature


# =========================================================
# HANDAXE ORIENTATION
# =========================================================

def orient_handaxe(mesh):

    vertices = mesh.vertices.copy()

    # -----------------------------------------------------
    # Centre
    # -----------------------------------------------------

    vertices -= vertices.mean(axis=0)


    # -----------------------------------------------------
    # PCA ORIENTATION
    # -----------------------------------------------------

    covariance = np.cov(
        vertices.T
    )

    eigenvalues, eigenvectors = np.linalg.eigh(
        covariance
    )

    order = np.argsort(
        eigenvalues
    )[::-1]

    eigenvectors = eigenvectors[:, order]

    length_axis = eigenvectors[:, 0]
    width_axis = eigenvectors[:, 1]
    flat_axis = eigenvectors[:, 2]

    transform = np.column_stack(
        (
            width_axis,
            length_axis,
            flat_axis
        )
    )

    vertices = vertices @ transform


    # -----------------------------------------------------
    # MAKE FLAT FACE FACE CAMERA
    # -----------------------------------------------------

    if np.mean(vertices[:, 2]) < 0:

        vertices[:, 2] *= -1


    # -----------------------------------------------------
    # MAXIMISE PLANFORM EXPOSURE
    # -----------------------------------------------------

    best_area = -1

    best = vertices.copy()

    for angle in np.arange(0, 180, 2):

        Ry = rotation_matrix(
            [0, 1, 0],
            angle
        )

        test = vertices @ Ry.T

        area = projected_area(
            test
        )

        if area > best_area:

            best_area = area

            best = test

    vertices = best


    # -----------------------------------------------------
    # TIP DETECTION
    # -----------------------------------------------------

    curvature = estimate_vertex_curvature(
        vertices
    )

    # Ignore central area because maximum
    # curvature can occur at flake scars

    y = vertices[:, 1]

    tip_mask = (
        y > np.percentile(y, 70)
    )

    tip_candidates = vertices[
        tip_mask
    ]

    candidate_curvature = curvature[
        tip_mask
    ]

    if len(candidate_curvature) > 0:

        tip_point = tip_candidates[
            np.argmax(candidate_curvature)
        ]

        tip_y = tip_point[1]

    else:

        tip_y = vertices[:, 1].max()


    # -----------------------------------------------------
    # ORIENT TIP TO +Y
    # -----------------------------------------------------

    if tip_y < 0:

        vertices[:, 1] *= -1


    # -----------------------------------------------------
    # CONFIRM BUTT IS NEGATIVE Y
    # -----------------------------------------------------

    if vertices[:, 1].max() < abs(
        vertices[:, 1].min()
    ):

        vertices[:, 1] *= -1


    # -----------------------------------------------------
    # FINAL CENTRING
    # -----------------------------------------------------

    vertices -= vertices.mean(axis=0)

    mesh.vertices = vertices

    return mesh


# =========================================================
# SELECT SOURCE DIRECTORY
# =========================================================

root = tk.Tk()
root.withdraw()

directory = filedialog.askdirectory(
    title="Select the folder containing the WRL files"
)

root.destroy()


# Exit if no folder was selected

if not directory:

    print("No folder selected. Script cancelled.")

    exit()


# =========================================================
# CREATE OUTPUT DIRECTORY
# =========================================================

out_directory = os.path.join(
    directory,
    "Decimated GLBs"
)

os.makedirs(
    out_directory,
    exist_ok=True
)


# =========================================================
# ASK FOR TARGET NUMBER OF FACES
# =========================================================

print(
    "\nThis script will:"
)

print(
    "1. Load each WRL file."
)

print(
    "2. Decimate the mesh."
)

print(
    "3. Reorient the handaxe using PCA and curvature."
)

print(
    "4. Export the result as a GLB."
)

print(
    "\nOriginal filenames will be retained, "
    "with the extension changed to .glb."
)

print(
    "\nSelected source directory:"
)

print(
    directory
)

print(
    "\nDecimated and reoriented GLB files will be saved to:"
)

print(
    out_directory
)


# Get target face count

while True:

    try:

        TARGET = int(
            input(
                "\nEnter the number of faces you want "
                "to decimate to "
                "(recommended 200 000):\n"
            )
        )

        if TARGET <= 0:

            print(
                "Please enter a positive number."
            )

            continue

        break

    except ValueError:

        print(
            "Please enter a whole number."
        )


# =========================================================
# FIND AND PROCESS WRL FILES
# =========================================================

wrl_files = [

    filename

    for filename in os.listdir(directory)

    if filename.lower().endswith(".wrl")

]


print(
    "\n"
    + "=" * 70
)

print(
    len(wrl_files),
    "WRL files found."
)

print(
    "=" * 70
)


# =========================================================
# PROCESS EACH WRL
# =========================================================

for n, filename in enumerate(
    wrl_files,
    1
):

    input_path = os.path.join(
        directory,
        filename
    )

    output_filename = (
        os.path.splitext(filename)[0]
        + ".glb"
    )

    output_path = os.path.join(
        out_directory,
        output_filename
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        f"Processing {n}/{len(wrl_files)}: {filename}"
    )

    print(
        "=" * 70
    )


    # -----------------------------------------------------
    # CREATE NEW MESHSET
    # -----------------------------------------------------

    ms = ml.MeshSet()


    # -----------------------------------------------------
    # LOAD WRL
    # -----------------------------------------------------

    try:

        ms.load_new_mesh(
            input_path
        )

    except Exception as e:

        print(
            "ERROR: Could not load",
            filename
        )

        print(e)

        continue


    m = ms.current_mesh()


    print(
        "Input mesh:"
    )

    print(
        "  Vertices:",
        m.vertex_number()
    )

    print(
        "  Faces:",
        m.face_number()
    )


    # -----------------------------------------------------
    # DECIMATE
    # -----------------------------------------------------

    try:

        ms.apply_filter(
            'meshing_decimation_quadric_edge_collapse',
            targetfacenum=TARGET,
            preservenormal=True
        )

    except Exception as e:

        print(
            "ERROR: Decimation failed for",
            filename
        )

        print(e)

        continue


    m = ms.current_mesh()


    print(
        "Decimated mesh:"
    )

    print(
        "  Vertices:",
        m.vertex_number()
    )

    print(
        "  Faces:",
        m.face_number()
    )


    # -----------------------------------------------------
    # CREATE UNIQUE TEMPORARY PLY
    # -----------------------------------------------------

    temp_fd, temp_ply = tempfile.mkstemp(
        suffix=".ply",
        prefix="_temporary_decimated_",
        dir=directory
    )

    os.close(
        temp_fd
    )

    os.remove(
        temp_ply
    )


    # -----------------------------------------------------
    # CONVERT TEMPORARY PLY → ORIENTED GLB
    # -----------------------------------------------------

    try:

        # -------------------------------------------------
        # Save decimated PyMeshLab mesh as PLY
        # -------------------------------------------------

        ms.save_current_mesh(
            temp_ply
        )


        # -------------------------------------------------
        # Load PLY with Trimesh
        # -------------------------------------------------

        tmesh = trimesh.load(
            temp_ply
        )


        # -------------------------------------------------
        # Convert scene to a single mesh
        # -------------------------------------------------

        mesh = glbutils.getSceneMesh(
            tmesh
        )


        # -------------------------------------------------
        # REORIENT HANDAXE
        # -------------------------------------------------

        print(
            "Reorienting handaxe..."
        )

        mesh = orient_handaxe(
            mesh
        )


        # -------------------------------------------------
        # EXPORT FINAL GLB
        # -------------------------------------------------

        mesh.export(
            output_path
        )


        print(
            "Saved:"
        )

        print(
            output_path
        )


    except Exception as e:

        print(
            "\nERROR processing",
            filename
        )

        print(e)


    finally:

        # -------------------------------------------------
        # ALWAYS REMOVE TEMPORARY PLY
        # -------------------------------------------------

        if os.path.exists(
            temp_ply
        ):

            try:

                os.remove(
                    temp_ply
                )

                print(
                    "Temporary PLY removed."
                )

            except Exception as cleanup_error:

                print(
                    "WARNING: Could not remove "
                    "temporary PLY:"
                )

                print(
                    temp_ply
                )

                print(
                    cleanup_error
                )


# =========================================================
# FINISHED
# =========================================================

print(
    "\n"
    + "=" * 70
)

print(
    "DECIMATION, ORIENTATION AND GLB CONVERSION COMPLETE"
)

print(
    "=" * 70
)

print(
    "\nDecimated and reoriented GLBs have been saved to:"
)

print(
    out_directory
)