import bpy
from bpy.app.handlers import persistent
from ..auto_export.export_gltf import export_gltf
from ...core.helpers_collections import set_active_collection

@persistent
def remove_temp_scene(scene_name):
    if scene_name in bpy.data.scenes:
        bpy.data.scenes.remove(bpy.data.scenes[scene_name], do_unlink=True)
    else:
        print(f"Scene {scene_name} not found in bpy.data.scenes")

def generate_and_export(addon_prefs, export_settings, gltf_output_path, temp_scene_name="__temp_scene", temp_scene_filler=None, temp_scene_cleaner=None):
    """ 
    Generates a temporary scene, fills it with data, and cleans up after itself.
    """
    temp_scene = bpy.data.scenes.new(name=temp_scene_name)
    temp_root_collection = temp_scene.collection

    original_scene = bpy.context.window.scene
    original_collection = bpy.context.view_layer.active_layer_collection
    original_mode = bpy.context.mode if bpy.context.object else None

    if original_mode and original_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.window.scene = temp_scene

    try:
        set_active_collection(bpy.context.scene, temp_root_collection.name)
        
        if temp_scene_filler:
            scene_filler_data = temp_scene_filler(temp_root_collection)
        
        export_gltf(gltf_output_path, export_settings)
        
        if temp_scene_cleaner:
            temp_scene_cleaner(temp_scene, scene_filler_data)
        
    except Exception as error:
        print("Failed to export GLTF!", error)
        raise
    finally:
        # Reset the original context
        bpy.context.window.scene = original_scene
        bpy.context.view_layer.active_layer_collection = original_collection
        
        if original_mode:
            bpy.ops.object.mode_set(mode=original_mode)
        
        # Schedule the removal of the temporary scene to ensure all references are cleared
        bpy.app.timers.register(lambda: remove_temp_scene(temp_scene_name), first_interval=0.1)