import pymeshlab as ml
import os
import tkinter as tk
from tkinter import filedialog


# ---------------------------------------------------------
# Select the directory containing the WRL files
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Create output directory
# ---------------------------------------------------------

out_directory = os.path.join(directory, "Decimated WRLs")

os.makedirs(out_directory, exist_ok=True)


# ---------------------------------------------------------
# Set up PyMeshLab
# ---------------------------------------------------------

ms = ml.MeshSet()


# ---------------------------------------------------------
# Ask for target number of faces
# ---------------------------------------------------------

print("\nThis script decimates 3D model files with extension .wrl.")
print("Original filenames will be retained.")
print("\nSelected source directory:")
print(directory)

print("\nDecimated files will be saved to:")
print(out_directory)

TARGET = int(
    input(
        "\nEnter the number of faces you want to decimate "
        "to (recommended 200 000):\n"
    )
)


# ---------------------------------------------------------
# Find and process WRL files
# ---------------------------------------------------------

for filename in os.listdir(directory):

    if filename.lower().endswith(".wrl"):

        # Full path to the input file
        input_path = os.path.join(directory, filename)

        # Full path to the output file
        # The ORIGINAL filename is retained.
        output_path = os.path.join(out_directory, filename)

        print("\n" + "=" * 60)
        print("Processing:", filename)

        # Load the WRL file
        ms.load_new_mesh(input_path)

        m = ms.current_mesh()

        print(
            "Input mesh has",
            m.vertex_number(),
            "vertices and",
            m.face_number(),
            "faces"
        )

        numFaces = TARGET

        # -------------------------------------------------
        # Simplify the mesh
        # -------------------------------------------------

        ms.apply_filter(
            'meshing_decimation_quadric_edge_collapse',
            targetfacenum=numFaces,
            preservenormal=True
        )

        # -------------------------------------------------
        # Retain the original calculation from the
        # original script
        # -------------------------------------------------

        numFaces = numFaces - (
            ms.current_mesh().vertex_number() - TARGET
        )

        m = ms.current_mesh()

        print(
            "Output mesh has",
            m.vertex_number(),
            "vertices and",
            m.face_number(),
            "faces"
        )

        # -------------------------------------------------
        # Save the decimated WRL
        # -------------------------------------------------

        ms.save_current_mesh(output_path)

        print("Saved to:")
        print(output_path)


# ---------------------------------------------------------
# Finished
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("DECIMATION COMPLETE")
print("=" * 60)

print("\nDecimated WRLs have been saved to:")
print(out_directory)