import json
import bpy
from bpy.types import Operator
from .preferences import AutoExportGltfAddonPreferences, AutoExportGltfPreferenceNames
from .auto_export import auto_export
from ..helpers.generate_complete_preferences_dict import generate_complete_preferences_dict_auto


def bubble_up_changes(obj, changes_per_scene):
    if obj.parent:
        changes_per_scene[obj.parent.name] = bpy.data.objects[obj.parent.name]
        bubble_up_changes(obj.parent, changes_per_scene)


def serialize_scene():
    scene_data = {}
    for scene in bpy.data.scenes:
        scene_data[scene.name] = {}
        for obj in scene.objects:
            scene_data[scene.name][obj.name] = {
                "location": obj.location[:],
                "rotation_euler": obj.rotation_euler[:],
                "scale": obj.scale[:],
                # Add other relevant properties here
            }
    return json.dumps(scene_data, indent=4)


def compare_scenes(current, previous):
    changes_per_scene = {}
    for scene_name, current_objects in current.items():
        previous_objects = previous.get(scene_name, {})
        added = set(current_objects) - set(previous_objects)
        removed = set(previous_objects) - set(current_objects)
        changed = {
            obj_name: current_objects[obj_name]
            for obj_name in set(current_objects) & set(previous_objects)
            if current_objects[obj_name] != previous_objects[obj_name]
        }

        if added or removed or changed:
            changes_per_scene[scene_name] = {
                "added": list(added),
                "removed": list(removed),
                "changed": changed,
            }
    return changes_per_scene


class AutoExportGLTF(Operator, AutoExportGltfAddonPreferences):
    """Auto export gltf"""

    bl_idname = "export_scenes.auto_gltf"
    bl_label = "Apply settings"
    bl_options = {"PRESET"}

    white_list = [
        "auto_export",
        "project_root_path",
        "assets_path",
        "change_detection",
        "export_scene_settings",
        "main_scene_names",
        "library_scene_names",
        "export_blueprints",
        "blueprints_path",
        "export_marked_assets",
        "collection_instances_combine_mode",
        "levels_path",
        "export_separate_dynamic_and_static_objects",
        "export_materials_library",
        "materials_path",
    ]

    def format_settings(self):
        all_props = self.properties
        export_props = {
            x: getattr(self, x)
            for x in dir(all_props)
            if (x.startswith("export_") or x in self.white_list)
            and all_props.get(x) is not None
        }
        return export_props

    def save_settings(self, context):
        auto_export_settings = self.format_settings()
        settings_name = ".gltf_auto_export_settings"
        stored_settings = bpy.data.texts.get(settings_name) or bpy.data.texts.new(settings_name)
        
        stored_settings.clear()
        auto_export_settings = generate_complete_preferences_dict_auto(auto_export_settings)
        
        # Avoid duplicating settings
        current_settings = json.loads(stored_settings.as_string()) if stored_settings.as_string() else {}
        current_settings.update(auto_export_settings)
        
        stored_settings.write(json.dumps(current_settings, indent=4))
        print("Saved settings", current_settings)

    def load_settings(self, context):
        settings_name = ".gltf_auto_export_settings"
        settings_text = bpy.data.texts.get(settings_name)
        
        if settings_text:
            try:
                settings = json.loads(settings_text.as_string())
                for k, v in settings.items():
                    setattr(self, k, v)
                self.will_save_settings = True
            except Exception as error:
                print("Error loading settings:", error)
                self.report({"ERROR"}, "Loading export settings failed. Removed corrupted settings.")
                bpy.data.texts.remove(settings_text)
        else:
            self.will_save_settings = True

    def did_export_settings_change(self):
        """ previous_auto_settings = bpy.data.texts.get(".gltf_auto_export_settings_previous")
        previous_gltf_settings = bpy.data.texts.get(".gltf_auto_export_gltf_settings_previous")
        current_auto_settings = bpy.data.texts.get(".gltf_auto_export_settings")
        current_gltf_settings = bpy.data.texts.get(".gltf_auto_export_gltf_settings")

        if not previous_auto_settings or not previous_gltf_settings:
            return True

        previous_auto_dict = json.loads(previous_auto_settings.as_string())
        current_auto_dict = json.loads(current_auto_settings.as_string())
        previous_gltf_dict = json.loads(previous_gltf_settings.as_string())
        current_gltf_dict = json.loads(current_gltf_settings.as_string())
        return True"""
        # compare both the auto export settings & the gltf settings
        previous_auto_settings = bpy.data.texts[".gltf_auto_export_settings_previous"] if ".gltf_auto_export_settings_previous" in bpy.data.texts else None
        previous_gltf_settings = bpy.data.texts[".blenvy_gltf_settings_previous"] if ".blenvy_gltf_settings_previous" in bpy.data.texts else None

        current_auto_settings = bpy.data.texts[".gltf_auto_export_settings"] if ".gltf_auto_export_settings" in bpy.data.texts else None
        current_gltf_settings = bpy.data.texts[".blenvy_gltf_settings"] if ".blenvy_gltf_settings" in bpy.data.texts else None

        #check if params have changed
        
        # if there were no setting before, it is new, we need export
        changed = False
        if previous_auto_settings == None:
            #print("previous settings missing, exporting")
            changed = True
        elif previous_gltf_settings == None:
            #print("previous gltf settings missing, exporting")
            previous_gltf_settings = bpy.data.texts.new(".blenvy_gltf_settings_previous")
            previous_gltf_settings.write(json.dumps({}))
            if current_gltf_settings == None:
                current_gltf_settings = bpy.data.texts.new(".blenvy_gltf_settings")
                current_gltf_settings.write(json.dumps({}))

        auto_settings_changed = sorted(previous_auto_dict.items()) != sorted(current_auto_dict.items())
        gltf_settings_changed = sorted(previous_gltf_dict.items()) != sorted(current_gltf_dict.items())

        if auto_settings_changed or gltf_settings_changed:
            bpy.data.texts[".gltf_auto_export_settings_previous"].clear()
            bpy.data.texts[".gltf_auto_export_settings_previous"].write(json.dumps(current_auto_dict, indent=4))
            bpy.data.texts[".gltf_auto_export_gltf_settings_previous"].clear()
            bpy.data.texts[".gltf_auto_export_gltf_settings_previous"].write(json.dumps(current_gltf_dict, indent=4))

        changed = auto_settings_changed or gltf_settings_changed
        # now write the current settings to the "previous settings"
        if current_auto_settings != None:
            previous_auto_settings = bpy.data.texts[".gltf_auto_export_settings_previous"] if ".gltf_auto_export_settings_previous" in bpy.data.texts else bpy.data.texts.new(".gltf_auto_export_settings_previous")
            previous_auto_settings.clear()
            previous_auto_settings.write(current_auto_settings.as_string()) # TODO : check if this is always valid

        if current_gltf_settings != None:
            previous_gltf_settings = bpy.data.texts[".blenvy_gltf_settings_previous"] if ".blenvy_gltf_settings_previous" in bpy.data.texts else bpy.data.texts.new(".blenvy_gltf_settings_previous")
            previous_gltf_settings.clear()
            previous_gltf_settings.write(current_gltf_settings.as_string())

        return changed
    
    def did_objects_change(self):
        current_frames = [scene.frame_current for scene in bpy.data.scenes]
        for scene in bpy.data.scenes:
            scene.frame_set(0)

        current_scene = bpy.context.window.scene
        bpy.context.window.scene = bpy.data.scenes[0]
        current_scene_data = json.loads(serialize_scene())
        bpy.context.window.scene = current_scene

        for index, scene in enumerate(bpy.data.scenes):
            scene.frame_set(current_frames[index])

        previous_scene_text = bpy.data.texts.get(".scene_serialized")
        if not previous_scene_text:
            previous_scene_text = bpy.data.texts.new(".scene_serialized")
            previous_scene_text.write(json.dumps(current_scene_data, indent=4))
            return {}

        previous_scene_data = json.loads(previous_scene_text.as_string())
        changes_per_scene = compare_scenes(current_scene_data, previous_scene_data)

        previous_scene_text.clear()
        previous_scene_text.write(json.dumps(current_scene_data, indent=4))

        return changes_per_scene

    def execute(self, context):
        blenvy = context.window_manager.blenvy
        auto_export_settings = blenvy.auto_export
        bpy.context.window_manager.auto_export_tracker.disable_change_detection()

        if self.direct_mode:
            self.load_settings(context)

        self.save_settings(context)

        if auto_export_settings.auto_export:
            changes_per_scene = self.did_objects_change()
            params_changed = self.did_export_settings_change()
            auto_export(changes_per_scene, params_changed, blenvy)
            bpy.context.window_manager.auto_export_tracker.clear_changes()
            bpy.app.timers.register(bpy.context.window_manager.auto_export_tracker.enable_change_detection, first_interval=0.1)
        else:
            print("Auto export disabled, skipping")

        return {"FINISHED"}

    def invoke(self, context, event):
        bpy.context.window_manager.auto_export_tracker.disable_change_detection()
        self.load_settings(context)
        return context.window_manager.invoke_props_dialog(self, title="Auto export", width=640)

    def cancel(self, context):
        bpy.app.timers.register(bpy.context.window_manager.auto_export_tracker.enable_change_detection, first_interval=1)


def register():
    bpy.utils.register_class(AutoExportGLTF)


def unregister():
    bpy.utils.unregister_class(AutoExportGLTF)