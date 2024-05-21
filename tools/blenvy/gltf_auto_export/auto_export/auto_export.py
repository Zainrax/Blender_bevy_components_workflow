import os
import bpy
import traceback
from pathlib import Path
from ..helpers.helpers_scenes import get_scenes
from .get_blueprints_to_export import get_blueprints_to_export
from .get_levels_to_export import get_levels_to_export
from .get_standard_exporter_settings import get_standard_exporter_settings
from .export_main_scenes import export_main_scene
from .export_blueprints import export_blueprints
from ..modules.export_materials import cleanup_materials, export_materials
from ..modules.bevy_scene_components import remove_scene_components, upsert_scene_components
from ...blueprints.blueprints_scan import blueprints_scan
from ...blueprints.blueprint_helpers import inject_export_path_into_internal_blueprints

from pathlib import Path

def setup_export_paths(addon_prefs, blend_file_path):
    project_root_path = Path(addon_prefs.project_root_path)
    
    if not project_root_path.is_absolute():
        project_root_path = Path(blend_file_path) / project_root_path

    assets_path = project_root_path / addon_prefs.assets_path

    addon_prefs.export_assets_path_full = str(assets_path)
    addon_prefs.export_blueprints_path_full = str(assets_path / addon_prefs.blueprints_path)
    addon_prefs.export_levels_path_full = str(assets_path / addon_prefs.levels_path)
    addon_prefs.export_materials_path_full = str(assets_path / addon_prefs.materials_path)

def inject_light_shadows():
    for light in bpy.data.lights:
        enabled = 'true' if light.use_shadow else 'false'
        light['BlenderLightShadows'] = f"(enabled: {enabled}, buffer_bias: {light.shadow_buffer_bias})"

def export_main_scenes(main_scenes_to_export, blend_file_path, addon_prefs, blueprints_data):
    if main_scenes_to_export:
        print("Exporting MAIN scenes")
        for scene_name in main_scenes_to_export:
            print(f"     Exporting scene: {scene_name}")
            export_main_scene(bpy.data.scenes[scene_name], blend_file_path, addon_prefs, blueprints_data)

def export_library_scenes(do_export_library_scene, blueprints_to_export, addon_prefs, blueprints_data):
    if do_export_library_scene:
        print("Exporting LIBRARY")
        export_blueprints(blueprints_to_export, addon_prefs, blueprints_data)

def handle_error(error):
    print(traceback.format_exc())

    def error_message(self, context):
        self.layout.label(text=f"Failure during auto_export: Error: {error}")

    bpy.context.window_manager.popup_menu(error_message, title="Error", icon='ERROR')

def auto_export(changes_per_scene, changed_export_parameters, addon_prefs):
    print("changed_export_parameters", changed_export_parameters)
    try:
        file_path = bpy.data.filepath
        blend_file_path = os.path.dirname(file_path)
        # get the preferences for our addon
        project_root_path = getattr(addon_prefs, "project_root_path")
        assets_path = getattr(addon_prefs,"assets_path")

        #should we use change detection or not 
        change_detection = getattr(addon_prefs.auto_export, "change_detection")
        export_scene_settings = getattr(addon_prefs.auto_export,"export_scene_settings")
        do_export_blueprints = getattr(addon_prefs.auto_export,"export_blueprints")
        export_materials_library = getattr(addon_prefs.auto_export,"export_materials_library")

        # standard gltf export settings are stored differently
        standard_gltf_exporter_settings = get_standard_exporter_settings()
        gltf_extension = standard_gltf_exporter_settings.get("export_format", 'GLB')
        gltf_extension = '.glb' if gltf_extension == 'GLB' else '.gltf'
       
        # generate the actual complete output paths
        """addon_prefs.assets_path_full = os.path.join(blend_file_path, project_root_path, assets_path)
        addon_prefs.blueprints_path_full = os.path.join(addon_prefs.assets_path_full, getattr(addon_prefs,"blueprints_path"))
        addon_prefs.levels_path_full = os.path.join(addon_prefs.assets_path_full, getattr(addon_prefs,"levels_path"))
        addon_prefs.materials_path_full = os.path.join(addon_prefs.assets_path_full, getattr(addon_prefs,"materials_path"))"""
        addon_prefs.export_gltf_extension = gltf_extension
        
        main_scene_names, level_scenes, library_scene_names, library_scenes = get_scenes(addon_prefs)
        
        blueprints_data = blueprints_scan(level_scenes, library_scenes, addon_prefs)
        blueprints_per_scene = blueprints_data.blueprints_per_scenes
        internal_blueprints = [blueprint.name for blueprint in blueprints_data.internal_blueprints]
        external_blueprints = [blueprint.name for blueprint in blueprints_data.external_blueprints]

        # we inject the blueprints export path
        blueprints_path = getattr(addon_prefs,"blueprints_path")
        inject_export_path_into_internal_blueprints(internal_blueprints=blueprints_data.internal_blueprints, blueprints_path=blueprints_path, gltf_extension=gltf_extension)
        
        for blueprint in blueprints_data.blueprints:
            bpy.context.window_manager.blueprints_registry.upsert_blueprint(blueprint)
        
        if addon_prefs.auto_export.export_scene_settings:
            upsert_scene_components(level_scenes)
        #inject/ update light shadow information
        for light in bpy.data.lights:
            enabled = 'true' if light.use_shadow else 'false'
            light['BlenderLightShadows'] = f"(enabled: {enabled}, buffer_bias: {light.shadow_buffer_bias})"

        # export
        if do_export_blueprints:
            print("EXPORTING")
            # get blueprints/collections infos
            (blueprints_to_export) = get_blueprints_to_export(changes_per_scene, changed_export_parameters, blueprints_data, addon_prefs)
             
            # get level/main scenes infos
            (main_scenes_to_export) = get_levels_to_export(changes_per_scene, changed_export_parameters, blueprints_data, addon_prefs)

            # since materials export adds components we need to call this before blueprints are exported
            # export materials & inject materials components into relevant objects
            if export_materials_library:
                export_materials(blueprints_data.blueprint_names, library_scenes, addon_prefs)
            
            bpy.context.window_manager.auto_export_tracker.exports_total = len(blueprints_to_export) + len(main_scenes_to_export) + (1 if addon_prefs.auto_export.export_materials_library else 0)
            bpy.context.window_manager.auto_export_tracker.exports_count = bpy.context.window_manager.auto_export_tracker.exports_total
            
            old_current_scene = bpy.context.scene
            old_selections = bpy.context.selected_objects[:]
            
            export_main_scenes(main_scenes_to_export, blend_file_path, addon_prefs, blueprints_data)
            do_export_library_scene = not addon_prefs.auto_export.change_detection or changed_export_parameters or len(blueprints_to_export) > 0
            export_library_scenes(do_export_library_scene, blueprints_to_export, addon_prefs, blueprints_data)
            
            bpy.context.window.scene = old_current_scene
            for obj in old_selections:
                obj.select_set(True)
            if addon_prefs.auto_export.export_materials_library:
                cleanup_materials(blueprints_data.blueprint_names, library_scenes)
        else:
            for scene_name in main_scene_names:
                export_main_scene(bpy.data.scenes[scene_name], blend_file_path, addon_prefs, [])
    except Exception as error:
        handle_error(error)
    finally:
        main_scene_names, main_scenes, library_scene_names, library_scenes = get_scenes(addon_prefs)
        if addon_prefs.auto_export.export_scene_settings:
            remove_scene_components(main_scenes)