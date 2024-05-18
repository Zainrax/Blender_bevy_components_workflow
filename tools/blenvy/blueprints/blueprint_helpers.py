import os
import json
import bpy
from ..core.scene_helpers import add_scene_property

def find_blueprints_not_on_disk(blueprints, folder_path, extension):
    not_found_blueprints = [
        blueprint for blueprint in blueprints
        if not os.path.isfile(os.path.join(folder_path, blueprint.name + extension))
    ]
    return not_found_blueprints

def check_if_blueprint_on_disk(scene_name, folder_path, extension):
    gltf_output_path = os.path.join(folder_path, scene_name + extension)
    found = os.path.isfile(gltf_output_path)
    print(f"Level {scene_name}, found: {found}, path: {gltf_output_path}")
    return found

def inject_export_path_into_internal_blueprints(internal_blueprints, blueprints_path, gltf_extension):
    for blueprint in internal_blueprints:
        blueprint_exported_path = os.path.join(blueprints_path, f"{blueprint.name}{gltf_extension}")
        blueprint.collection["export_path"] = blueprint_exported_path

def inject_blueprints_list_into_main_scene(scene, blueprints_data, addon_prefs):
    project_root_path = getattr(addon_prefs, "project_root_path")
    blueprints_path = os.path.join(project_root_path, getattr(addon_prefs, "blueprints_path"))
    export_gltf_extension = getattr(addon_prefs, "export_gltf_extension")

    blueprint_assets_list = []
    blueprint_instance_names_for_scene = blueprints_data.blueprint_instances_per_main_scene.get(scene.name, None)
    if blueprint_instance_names_for_scene:
        for blueprint_name in blueprint_instance_names_for_scene:
            blueprint = blueprints_data.blueprints_per_name.get(blueprint_name, None)
            if blueprint:
                blueprint_exported_path = (
                    os.path.join(blueprints_path, f"{blueprint.name}{export_gltf_extension}")
                    if blueprint.local else
                    blueprint.collection.get('export_path')
                )
                if blueprint_exported_path:
                    blueprint_assets_list.append({
                        "name": blueprint.name,
                        "path": blueprint_exported_path,
                        "type": "MODEL",
                        "internal": True
                    })

    scene["assets"] = json.dumps(blueprint_assets_list)
    print(f"Blueprint assets for scene '{scene.name}': {blueprint_assets_list}")

def remove_blueprints_list_from_main_scene(scene):
    assets_list_name = f"assets_list_{scene.name}_components"
    assets_list = next((obj for obj in scene.objects if obj.name == assets_list_name), None)
    if assets_list:
        bpy.data.objects.remove(assets_list, do_unlink=True)