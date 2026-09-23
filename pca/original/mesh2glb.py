#! /usr/bin/env python

""" Convert a mesh file to a GLB file. """
import sys
import os
os.chdir('C:/Users/frede/Dropbox/Projects/AHRC HoB Scan/PyHandaxeScanConvert_v1_0')
import pymeshlab as ml
import trimesh
import glbutils


def mesh2glb(inname, outname, removeColor=False):
    """Convert a mesh file to a GLB file.

    If the input file is in a format Trimesh supports, we load it with
    Trimesh and write out a GLB file.  Formats supported by Trimesh
    include STL, PLY, OBJ, OFF, GLB and GLTF.

    For formats not supported by Trimesh, particularly X3D and VRML 2.0,
    we use MeshLab to create an intermediate PLY file.  This PLY file
    is then passed to Trimesh to produce the final GLB.

    Note that in creating this PLY file, any scene hierarchy and non-mesh
    data such as camera, lights or animation are discarded.  All mesh
    objects in the scene graph are merged into one bundle of triangles.

    """

    words = inname.split(".")
    suffix = words[-1]

    tmpname = ""

    if suffix in trimesh.exchange.load.available_formats():
        # skip the meshlab stuff if trimesh supports in input format
        tmpname = inname
    else:
        # Use meshlab to read the mesh
        ms = ml.MeshSet()
        try:
            ms.load_new_mesh(inname)

            # remove the suffix of the input name
            dotpos = inname.rfind(".")
            if dotpos != -1:
                rootname = inname[0:dotpos]
            else:
                rootname = inname

            tmpname = rootname + ".ply"

            # Save a temporary PLY file
            ms.save_current_mesh(tmpname)
        except ValueError:
            print("Error: failed to load ", inname)
            sys.exit(1)

    try:
        tmesh = trimesh.load(tmpname)
    except ValueError:
        print("Error: failed to load", tmpname)
        sys.exit(2)

    mesh = glbutils.getSceneMesh(tmesh)

    if removeColor:
        glbutils.removeVertexColor(mesh)

   
    try:
        tmesh.export(outname)
    except ValueError:
        print("Error: failed to write ", outname)

    # Clean up the temp PLY file
    if tmpname != inname:
        os.remove(tmpname)

directory = 'ToConvert'

for filename in os.listdir(directory):
    if filename.endswith('.ply'):
        with open(os.path.join(directory, filename)):
            f = os.path.join(directory, filename)

            if __name__ == "__main__":
                in_name = filename
                out_name = filename.replace(".ply", ".glb")

                if len(sys.argv) > 1:
                    in_name = sys.argv[1]
                    if len(sys.argv) > 2:
                        out_name = sys.argv[2]
                    else:
                        out_name = filename.replace(".wrl", ".glb")
            print("Converting", in_name, "to", out_name)
            mesh2glb(f, out_name, removeColor= False)            
    else:
        if filename.endswith('.wrl'):
            with open(os.path.join(directory, filename)):
                f = os.path.join(directory, filename)
            
                if __name__ == "__main__":
                    in_name = filename
                    out_name = filename.replace(".wrl", ".glb")

                    if len(sys.argv) > 1:
                        in_name = sys.argv[1]
                        if len(sys.argv) > 2:
                            out_name = sys.argv[2]
                        else:
                            out_name = filename.replace(".wrl", ".glb")
                print("Converting", in_name, "to", out_name)
                mesh2glb(f, out_name, removeColor= False)  
    
   