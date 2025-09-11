import numpy as np
from stl import mesh
from math import atan2, sqrt, pi
import os
import trimesh
from trimesh import boolean

from pathlib import Path
from pymeshfix import MeshFix


def crop_stl_with_cube(input_path, output_path, debug_temp_path=None):
    """
    Crop STL using a cube by boolean intersection (actual mesh cutting).
    """
    print(f" Performing boolean crop on: {input_path}")

    # Load original mesh
    mesh_in = trimesh.load_mesh(str(input_path), force='mesh')

    # Define cube via box from 8 vertices (AABB)
    cube_vertices = np.array([
        [0, -100, 0.1],
        [100, -100, 0.1],
        [100, -100, -0.1],
        [0, -100, -0.1],
        [0, 100, 0.1],
        [100, 100, 0.1],
        [100, 100, -0.1],
        [0, 100, -0.1]
    ])
    min_bound = cube_vertices.min(axis=0)
    max_bound = cube_vertices.max(axis=0)

    # Create a cube mesh
    cube_box = trimesh.creation.box(extents=(max_bound - min_bound), transform=trimesh.transformations.translation_matrix(
        (max_bound + min_bound) / 2.0))

    # Perform boolean intersection (may require Blender or OpenSCAD installed)
    try:
        cut_mesh = boolean.intersection([mesh_in, cube_box], engine='scad')
    except BaseException as e:
        print(f" Boolean intersection failed: {e}")
        return

    if cut_mesh.is_empty:
        print(" Resulting mesh is empty after cutting.")
        return

    cut_mesh.export(output_path)
    print(f" Cut mesh saved to: {output_path}")

    if debug_temp_path:
        debug_file = debug_temp_path / f"cropped_{input_path.name}"
        cut_mesh.export(debug_file)
        print(f" Debug mesh also saved to: {debug_file}")


def unwrap_vertex(x, y, z):
    R = sqrt(x**2 + z**2)
    theta = atan2(round(x, 4), round(z, 4))
    if theta < 0:
        theta += 2 * pi
    x_new = R * theta
    z_new = R
    return [x_new, y, z_new], theta

def calculate_normal(v0, v1, v2):
    u = np.array(v1) - np.array(v0)
    v = np.array(v2) - np.array(v0)
    normal = np.cross(u, v)
    norm = np.linalg.norm(normal)
    return normal / norm if norm != 0 else [0, 0, 0]



def unwrap_and_repair_stl(input_path, output_path, debug_temp_path: Path = None):
    print(f"Loading and repairing STL: {input_path}")
    tm = trimesh.load_mesh(str(input_path), force='mesh')

    # Initial check
    if not tm.is_watertight:
        print(" Mesh is not watertight. Attempting repair...")

        # Apply all core repairs
        tm.repair.fix_normals()
        tm.repair.fill_holes()
        tm.repair.fix_winding()
        tm.remove_duplicate_faces()
        tm.remove_degenerate_faces()
        tm.remove_unreferenced_vertices()
        tm.process(validate=True)

        # Check again
        if tm.is_watertight:
            print(" Mesh repaired and now watertight.")
        else:
            print(" Mesh repaired but still NOT watertight.")

    if debug_temp_path:
        repaired_temp_path = debug_temp_path / f"repaired_{input_path.name}"
        tm.export(repaired_temp_path)
        print(f" Repaired STL saved to: {repaired_temp_path}")

    # Convert to numpy-stl for unwrapping
    original_vectors = tm.vertices[tm.faces]
    valid_triangles = []

    for triangle in original_vectors:
        v0, t0 = unwrap_vertex(*triangle[0])
        v1, t1 = unwrap_vertex(*triangle[1])
        v2, t2 = unwrap_vertex(*triangle[2])
        thetas = [t0, t1, t2]

        # Reject triangles spanning >250 degree
        if (max(thetas) - min(thetas) )> (250* pi / 180):
            continue

        normal = calculate_normal(v0, v1, v2)
        valid_triangles.append((v0, v1, v2, normal))

    # Save filtered triangles to STL
    repaired_data = np.zeros(len(valid_triangles), dtype=mesh.Mesh.dtype)
    repaired_mesh = mesh.Mesh(repaired_data)

    for i, (v0, v1, v2, normal) in enumerate(valid_triangles):
        repaired_mesh.vectors[i] = [v0, v1, v2]
        repaired_mesh.normals[i] = normal

    repaired_mesh.save(output_path, mode=mesh.stl.Mode.ASCII)
    print(f" Unwrapped and repaired STL saved to: {output_path}")

# Reload and verify final STL
    print(f" Verifying saved STL: {output_path}")
    tm_check = trimesh.load_mesh(str(output_path), force='mesh')

    if tm_check.is_watertight:
        print(" Mesh is already watertight. No changes made.")
    else:
        print(" Mesh is not watertight. Attempting repair...")
        # Perform repairs
        trimesh.repair.fix_normals(tm_check)
        trimesh.repair.fill_holes(tm_check)
        trimesh.repair.fix_winding(tm_check)
        tm_check.remove_duplicate_faces()
        tm_check.remove_degenerate_faces()
        tm_check.remove_unreferenced_vertices()
        tm_check.process(validate=True)

        if tm_check.is_watertight:
            print(" Mesh repaired and now watertight. Overwriting file...")
        else:
            print(" Repair attempted but mesh is still NOT watertight. Overwriting file anyway to save intermediate state.")


        if not tm_check.is_watertight:
            print(" Repair failed. Trying pymeshfix...")

            mf = MeshFix(tm_check.vertices, tm_check.faces)
            mf.repair(verbose=False, joincomp=True)

            # Rebuild as a proper Trimesh object
            fixed_mesh = trimesh.Trimesh(vertices=mf.v, faces=mf.f, process=True)

            # Optional cleanup
            components = fixed_mesh.split(only_watertight=False)
            large_components = [c for c in components if len(c.faces) >= 100]

            if not large_components:
                print("All pymeshfix components were too small. Nothing to save.")
                return

            fixed_mesh = trimesh.util.concatenate(large_components)

            if fixed_mesh.is_watertight:
                print(" pymeshfix succeeded. Mesh is watertight.")
            else:
                print("pymeshfix ran but result is still NOT watertight.")

            fixed_mesh.export(output_path)
            print(f" Final mesh saved to: {output_path}")
