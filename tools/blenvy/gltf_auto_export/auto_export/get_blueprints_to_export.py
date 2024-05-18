import os
from ..helpers.helpers_scenes import get_scenes
from ...blueprints.blueprint_helpers import find_blueprints_not_on_disk

def get_blueprints_to_export(changes_per_scene, changed_export_parameters, blueprints_data, addon_prefs):
    export_gltf_extension = getattr(addon_prefs, "export_gltf_extension", ".glb")
    export_blueprints_path_full = getattr(addon_prefs, "export_blueprints_path_full", "")
    change_detection = getattr(addon_prefs.auto_export, "change_detection")
    collection_instances_combine_mode = getattr(addon_prefs.auto_export, "collection_instances_combine_mode")

    main_scene_names, level_scenes, library_scene_names, library_scenes = get_scenes(addon_prefs)
    internal_blueprints = blueprints_data.blueprints
    blueprints_to_export = internal_blueprints

    if change_detection and not changed_export_parameters:
        changed_blueprints = []
        blueprints_not_on_disk = find_blueprints_not_on_disk(internal_blueprints, export_blueprints_path_full, export_gltf_extension)

        for scene in library_scenes:
            if scene.name in changes_per_scene:
                changed_objects = list(changes_per_scene[scene.name].keys())
                changed_blueprints.extend([
                    blueprints_data.blueprints_from_objects[changed]
                    for changed in changed_objects
                    if changed in blueprints_data.blueprints_from_objects
                ])
                changed_local_blueprints = [
                    blueprint for blueprint in changed_blueprints
                    if blueprint.name in blueprints_data.blueprints_per_name and blueprint.local
                ]
                changed_blueprints.extend(changed_local_blueprints)

        blueprints_to_export = list(set(changed_blueprints + blueprints_not_on_disk))

    filtered_blueprints = [
        blueprint for blueprint in blueprints_to_export
        if blueprint.marked or any(
            instance.get('_combine', collection_instances_combine_mode) == "Split"
            for instance in blueprints_data.internal_collection_instances.get(blueprint.name, [])
        )
    ]

    blueprints_to_export = list(set(filtered_blueprints))
    return blueprints_to_export