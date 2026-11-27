import bpy
import os
import zipfile
import tempfile

# --- CONFIGURATION ---
TARGET_DIR = r"C:\Users\veizou\vei-z\public\content\genshin\npc"
# ---------------------

def keep_only_diffuse():
    """Keeps the exact Diffuse image already assigned by the FBX, removing broken alpha/specular links."""
    # Ensure primary UV map is active
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.data.uv_layers:
            obj.data.uv_layers.active_index = 0

    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Grab the exact image the FBX already linked to this material
        existing_image = None
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                existing_image = node.image
                break

        if not existing_image:
            continue

        # Rebuild a clean Principled BSDF using ONLY that exact Diffuse image
        nodes.clear()
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.85
        if 'Specular IOR Level' in bsdf.inputs:
            bsdf.inputs['Specular IOR Level'].default_value = 0.0

        tex_node = nodes.new(type='ShaderNodeTexImage')
        tex_node.image = existing_image
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])

def convert_fbx_list(fbx_files, out_folder, folder_name):
    total_fbx = len(fbx_files)
    for index, fbx_path in enumerate(fbx_files, start=1):
        glb_name = str(index) if total_fbx > 1 else folder_name
        glb_path = os.path.join(out_folder, f"{glb_name}.glb")

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        keep_only_diffuse()
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')

def process_in_place():
    for root, dirs, files in os.walk(TARGET_DIR):
        folder_name = os.path.basename(root)

        fbx_files = [os.path.join(root, f) for f in sorted(files) if f.lower().endswith(".fbx")]
        zip_files = [f for f in sorted(files) if f.lower().endswith(".zip")]

        if fbx_files:
            convert_fbx_list(fbx_files, root, folder_name)
            print(f"Updated (from loose files): {folder_name}")
        elif zip_files:
            first_zip = next(iter(zip_files))
            zip_path = os.path.join(root, first_zip)
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(temp_dir)

                zip_fbx = []
                for z_root, z_dirs, z_files in os.walk(temp_dir):
                    for file in sorted(z_files):
                        if file.lower().endswith(".fbx"):
                            zip_fbx.append(os.path.join(z_root, file))

                if zip_fbx:
                    convert_fbx_list(zip_fbx, root, folder_name)
                    print(f"Updated (from ZIP): {folder_name}")

if __name__ == "__main__":
    process_in_place()
