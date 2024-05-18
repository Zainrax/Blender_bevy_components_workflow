from types import SimpleNamespace
import bpy
import json
import os
import uuid
from pathlib import Path
from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty, EnumProperty, PointerProperty

from ..settings import load_settings
from ..gltf_auto_export.helpers.helpers_scenes import get_scenes
from .blueprints_scan import blueprints_scan

class BlueprintsRegistry(PropertyGroup):
    blueprints_data = {}
    blueprints_list = []

    asset_name_selector: StringProperty(
        name="Asset Name",
        description="Name of asset to add",
    ) 

    asset_type_selector: EnumProperty(
        name="Asset Type",
        description="Type of asset to add",
         items=(
                ('model', "Model", ""),
                ('audio', "Audio", ""),
                ('image', "Image", ""),
        )
    ) 

    asset_path_selector: StringProperty(
        name="Asset Path",
        description="Path of asset to add",
        subtype='FILE_PATH'
    ) 

    @classmethod
    def register(cls):
        bpy.types.WindowManager.blueprints_registry = PointerProperty(type=BlueprintsRegistry)

    @classmethod
    def unregister(cls):
        del bpy.types.WindowManager.blueprints_registry

    @classmethod
    def initialize_blueprints_data(cls):
        print("Adding blueprints data")
        addon_prefs = load_settings(".gltf_auto_export_settings")
        if addon_prefs is not None: 
            print("addon_prefs", addon_prefs)
            addon_prefs["export_marked_assets"] = False
            
            # Ensure addon_prefs is a SimpleNamespace and has the correct structure
            if isinstance(addon_prefs, dict):
                addon_prefs = SimpleNamespace(**addon_prefs)
            if not hasattr(addon_prefs, 'auto_export'):
                addon_prefs.auto_export = SimpleNamespace(export_marked_assets=False)
            
            [main_scene_names, level_scenes, library_scene_names, library_scenes] = get_scenes(addon_prefs)
            blueprints_data = blueprints_scan(level_scenes, library_scenes, addon_prefs)
            cls.blueprints_data = blueprints_data

    def add_blueprint(self, blueprint): 
        self.blueprints_list.append(blueprint)
    
    def upsert_blueprint(self, blueprint):
        for i, bp in enumerate(self.blueprints_list):
            if bp.name == blueprint.name:
                self.blueprints_list[i] = blueprint
                return
        self.add_blueprint(blueprint)