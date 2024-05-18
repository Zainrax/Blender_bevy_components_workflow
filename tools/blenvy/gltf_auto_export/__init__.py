import os
import json
import bpy
from .helpers.generate_complete_preferences_dict import generate_complete_preferences_dict_gltf

def cleanup_file():
    gltf_filepath = "/home/ckaos/projects/bevy/Blender_bevy_components_worklflow/testing/bevy_example/assets/____dummy____.glb"
    if os.path.exists(gltf_filepath):
        os.remove(gltf_filepath)
        return None
    else:
        return 1
    
def gltf_post_export_callback(data):
    bpy.context.window_manager.auto_export_tracker.export_finished()

    gltf_settings_backup = getattr(bpy.context.window_manager, "gltf_settings_backup", "")
    gltf_filepath = data["gltf_filepath"]
    gltf_export_id = data['gltf_export_id']
    if gltf_export_id == "gltf_auto_export":
        bpy.context.window_manager.auto_export_tracker.dummy_file_path = gltf_filepath
        try:
            bpy.app.timers.unregister(cleanup_file)
        except:
            pass
        bpy.app.timers.register(cleanup_file, first_interval=1)

        scene = bpy.context.scene
        if "glTF2ExportSettings" in scene:
            settings = scene["glTF2ExportSettings"]
            export_settings = bpy.data.texts[".gltf_auto_export_gltf_settings"] if ".gltf_auto_export_gltf_settings" in bpy.data.texts else bpy.data.texts.new(".gltf_auto_export_gltf_settings")
            export_settings.clear()

            current_gltf_settings = generate_complete_preferences_dict_gltf(dict(settings))
            export_settings.write(json.dumps(current_gltf_settings))
        
        if gltf_settings_backup != "":
            scene["glTF2ExportSettings"] = json.loads(gltf_settings_backup)
        else:
            if "glTF2ExportSettings" in scene:
                del scene["glTF2ExportSettings"]
       
        last_operator = bpy.context.window_manager.auto_export_tracker.last_operator
        last_operator.filepath = ""
        last_operator.gltf_export_id = ""