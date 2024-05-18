import bpy
from pathlib import Path
from typing import List, Optional

from ...core.helpers_collections import traverse_tree
from ...core.object_makers import make_cube
from ...materials.materials_helpers import get_all_materials
from ..helpers.generate_and_export import generate_and_export
from ..auto_export.export_gltf import generate_gltf_export_preferences

def clear_material_info(collection_names: List[str], library_scenes: List[bpy.types.Scene]) -> None:
    """Remove MaterialInfo property from objects in specified collections within library scenes."""
    for scene in library_scenes:
        root_collection = scene.collection
        for cur_collection in traverse_tree(root_collection):
            if cur_collection.name in collection_names:
                for obj in cur_collection.all_objects:
                    if 'MaterialInfo' in obj:
                        del obj["MaterialInfo"]

def make_material_object(name: str, location: List[float] = [0, 0, 0], rotation: List[float] = [0, 0, 0], 
                         scale: List[float] = [1, 1, 1], material: Optional[bpy.types.Material] = None, 
                         collection: Optional[bpy.types.Collection] = None) -> bpy.types.Object:
    """Create a new object with the specified material."""
    obj = make_cube(name, location=location, rotation=rotation, scale=scale, collection=collection)
    if material:
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
    return obj

def generate_materials_scene_content(root_collection: bpy.types.Collection, used_material_names: List[str]) -> None:
    """Generate content for the materials scene."""
    for index, material_name in enumerate(used_material_names):
        material = bpy.data.materials.get(material_name)
        if material:
            make_material_object(f"Material_{material_name}", [index * 0.2, 0, 0], material=material, collection=root_collection)

def clear_materials_scene(temp_scene: bpy.types.Scene) -> None:
    """Clear the temporary materials scene."""
    root_collection = temp_scene.collection
    scene_objects = list(root_collection.objects)
    for obj in scene_objects:
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
        except KeyError:
            pass

def export_materials(collections: List[str], library_scenes: List[bpy.types.Scene], addon_prefs: bpy.types.AddonPreferences) -> None:
    """Export the materials used in the current project."""
    gltf_export_preferences = generate_gltf_export_preferences(addon_prefs)
    export_materials_path_full = Path(addon_prefs.export_materials_path_full)

    used_material_names = get_all_materials(collections, library_scenes)
    current_project_name = Path(bpy.context.blend_data.filepath).stem

    export_settings = {
        **gltf_export_preferences,
        'use_active_scene': True,
        'use_active_collection': True,
        'use_active_collection_with_nested': True,
        'use_visible': False,
        'use_renderable': False,
        'export_apply': True
    }

    gltf_output_path = export_materials_path_full / f"{current_project_name}_materials_library"

    print(f"Exporting materials to {gltf_output_path}.gltf/glb")

    def temp_scene_filler(temp_collection: bpy.types.Collection):
        generate_materials_scene_content(temp_collection, used_material_names)

    def temp_scene_cleaner(temp_scene: bpy.types.Scene, params):
        clear_materials_scene(temp_scene)

    generate_and_export(
        addon_prefs,
        temp_scene_name="__materials_scene",
        export_settings=export_settings,
        gltf_output_path=str(gltf_output_path),
        temp_scene_filler=temp_scene_filler,
        temp_scene_cleaner=temp_scene_cleaner
    )

def cleanup_materials(collections: List[str], library_scenes: List[bpy.types.Scene]) -> None:
    """Clean up materials by removing temporary components."""
    clear_material_info(collections, library_scenes)
