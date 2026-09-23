import os
import numpy as np
import trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation
import tkinter as tk
from tkinter import filedialog



# -------------------------------------------------------
# Rotation utility
# -------------------------------------------------------

def rotation_matrix(axis, angle_deg):

    return Rotation.from_rotvec(
        np.radians(angle_deg) * np.asarray(axis)
    ).as_matrix()



# -------------------------------------------------------
# Projected area
# -------------------------------------------------------

def projected_area(vertices):

    points = vertices[:, [0,1]]

    try:

        hull = ConvexHull(points)

        return hull.volume

    except:

        return 0



# -------------------------------------------------------
# Curvature estimation
# -------------------------------------------------------

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


        local = vertices[idx]


        local -= local.mean(axis=0)


        covariance = np.cov(
            local.T
        )


        eigenvalues = np.linalg.eigvalsh(
            covariance
        )


        # smallest eigenvalue represents
        # deviation from local plane

        curvature[i] = (
            eigenvalues[0]
            /
            eigenvalues.sum()
        )


    return curvature



# -------------------------------------------------------
# Handaxe orientation
# -------------------------------------------------------

def orient_handaxe(mesh):

    vertices = mesh.vertices.copy()


    # Centre

    vertices -= vertices.mean(axis=0)



    # -----------------------------------
    # PCA orientation
    # -----------------------------------

    covariance = np.cov(
        vertices.T
    )


    eigenvalues, eigenvectors = np.linalg.eigh(
        covariance
    )


    order = np.argsort(
        eigenvalues
    )[::-1]


    eigenvectors = eigenvectors[:,order]


    length_axis = eigenvectors[:,0]
    width_axis  = eigenvectors[:,1]
    flat_axis   = eigenvectors[:,2]


    transform = np.column_stack(
        (
            width_axis,
            length_axis,
            flat_axis
        )
    )


    vertices = vertices @ transform



    # -----------------------------------
    # Make flat face face camera
    # -----------------------------------

    if np.mean(vertices[:,2]) < 0:

        vertices[:,2] *= -1



    # -----------------------------------
    # Maximise planform exposure
    # -----------------------------------

    best_area = -1

    best = vertices.copy()


    for angle in np.arange(0,180,2):

        Ry = rotation_matrix(
            [0,1,0],
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



    # -----------------------------------
    # TIP DETECTION
    # -----------------------------------

    curvature = estimate_vertex_curvature(
        vertices
    )


    # Ignore central area because
    # maximum curvature can occur at
    # flake scars

    y = vertices[:,1]


    tip_candidates = (
        vertices[
            y > np.percentile(y,70)
        ]
    )


    candidate_curvature = curvature[
        y > np.percentile(y,70)
    ]


    if len(candidate_curvature) > 0:


        tip_point = tip_candidates[
            np.argmax(candidate_curvature)
        ]


        tip_y = tip_point[1]

    else:

        tip_y = vertices[:,1].max()



    # -----------------------------------
    # Orient tip to +Y
    # -----------------------------------

    if tip_y < 0:

        vertices[:,1] *= -1



    # -----------------------------------
    # Confirm butt is negative Y
    # -----------------------------------

    if vertices[:,1].max() < abs(
        vertices[:,1].min()
    ):

        vertices[:,1] *= -1



    # -----------------------------------
    # Final centering
    # -----------------------------------

    vertices -= vertices.mean(axis=0)


    mesh.vertices = vertices


    return mesh



# -------------------------------------------------------
# Folder processing
# -------------------------------------------------------

def process_folder(folder):


    output = os.path.join(
        folder,
        "oriented_models"
    )


    os.makedirs(
        output,
        exist_ok=True
    )


    models = [
        f for f in os.listdir(folder)
        if f.lower().endswith(".glb")
    ]


    print(
        f"{len(models)} models found."
    )


    for n, filename in enumerate(models,1):


        print(
            f"Processing {n}/{len(models)} {filename}"
        )


        try:

            mesh = trimesh.load(
                os.path.join(
                    folder,
                    filename
                ),
                force="mesh"
            )


            mesh = orient_handaxe(
                mesh
            )


            mesh.export(
                os.path.join(
                    output,
                    filename
                )
            )


        except Exception as e:

            print(
                "FAILED:",
                filename,
                e
            )



# -------------------------------------------------------
# Folder popup
# -------------------------------------------------------

def select_folder():

    root = tk.Tk()

    root.withdraw()

    folder = filedialog.askdirectory(
        title="Select GLB model folder"
    )

    root.destroy()

    return folder



# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":


    folder = select_folder()


    if folder:

        process_folder(folder)

    else:

        print(
            "No folder selected."
        )


    print(
        "Finished."
    )