from types import SimpleNamespace
import bpy
from .blueprint import Blueprint

# blueprints: any collection with either
# - an instance
# - marked as asset
# - with the "auto_export" flag
# https://blender.stackexchange.com/questions/167878/how-to-get-all-collections-of-the-current-scene
def blueprints_scan(main_scenes, library_scenes, addon_prefs):
    export_marked_assets = getattr(addon_prefs.auto_export, "export_marked_assets", False)

    blueprints = {}
    blueprints_from_objects = {}
    blueprint_name_from_instances = {}
    collections = []
    
    # main scenes
    blueprint_instances_per_main_scene = {}
    internal_collection_instances = {}
    external_collection_instances = {}

    # meh
    def add_object_to_collection_instances(collection_name, object, internal=True):
        collection_category = internal_collection_instances if internal else external_collection_instances
        if collection_name not in collection_category.keys():
            collection_category[collection_name] = []
        collection_category[collection_name].append(object)

    for scene in main_scenes:
        for object in scene.objects:
            if object.instance_type == 'COLLECTION':
                collection = object.instance_collection
                collection_name = object.instance_collection.name

                collection_from_library = any(library_scene.user_of_id(collection) > 0 for library_scene in library_scenes)
                add_object_to_collection_instances(collection_name=collection_name, object=object, internal=not collection_from_library)
                
                if scene.name not in blueprint_instances_per_main_scene.keys():
                    blueprint_instances_per_main_scene[scene.name] = {}
                if collection_name not in blueprint_instances_per_main_scene[scene.name].keys():
                    blueprint_instances_per_main_scene[scene.name][collection_name] = []
                blueprint_instances_per_main_scene[scene.name][collection_name].append(object)

                blueprint_name_from_instances[object] = collection_name

    for collection in bpy.data.collections:
        collection_from_library = any(scene.user_of_id(collection) > 0 for scene in library_scenes)
        if not collection_from_library: 
            continue
        
        if (
            'AutoExport' in collection and collection['AutoExport'] == True or
            export_marked_assets and collection.asset_data is not None or
            collection.name in list(internal_collection_instances.keys())
        ):
            blueprint = Blueprint(collection.name)
            blueprint.local = True
            blueprint.marked = 'AutoExport' in collection and collection['AutoExport'] == True or export_marked_assets and collection.asset_data is not None
            blueprint.objects = [object.name for object in collection.all_objects if object.instance_type != 'COLLECTION']
            blueprint.nested_blueprints = [object.instance_collection.name for object in collection.all_objects if object.instance_type == 'COLLECTION']
            blueprint.collection = collection
            blueprint.instances = internal_collection_instances.get(collection.name, [])
            blueprint.scene = next((scene for scene in library_scenes if scene.user_of_id(collection) > 0), None)
            blueprints[collection.name] = blueprint

            for object in collection.all_objects:
                if object.instance_type == 'COLLECTION':
                    add_object_to_collection_instances(collection_name=object.instance_collection.name, object=object, internal=blueprint.local)

            for object in collection.all_objects:
                blueprints_from_objects[object.name] = blueprint

        collections.append(collection)

    for collection_name in external_collection_instances:
        collection = bpy.data.collections[collection_name]
        blueprint = Blueprint(collection.name)
        blueprint.local = False
        blueprint.marked = True
        blueprint.objects = [object.name for object in collection.all_objects if object.instance_type != 'COLLECTION']
        blueprint.nested_blueprints = [object.instance_collection.name for object in collection.all_objects if object.instance_type == 'COLLECTION']
        blueprint.collection = collection
        blueprint.instances = external_collection_instances.get(collection.name, [])
        blueprint.scene = None
        blueprints[collection.name] = blueprint

        for object in collection.all_objects:
            blueprints_from_objects[object.name] = blueprint

    for blueprint_name in list(blueprints.keys()):
        parent_blueprint = blueprints[blueprint_name]

        for nested_blueprint_name in parent_blueprint.nested_blueprints:
            if nested_blueprint_name not in blueprints.keys():
                collection = bpy.data.collections[nested_blueprint_name]
                blueprint = Blueprint(collection.name)
                blueprint.local = parent_blueprint.local
                blueprint.objects = [object.name for object in collection.all_objects if object.instance_type != 'COLLECTION']
                blueprint.nested_blueprints = [object.instance_collection.name for object in collection.all_objects if object.instance_type == 'COLLECTION']
                blueprint.collection = collection
                blueprint.instances = external_collection_instances.get(collection.name, [])
                blueprint.scene = parent_blueprint.scene if parent_blueprint.local else None
                blueprints[collection.name] = blueprint

                for object in collection.all_objects:
                    blueprints_from_objects[object.name] = blueprint

    blueprints = dict(sorted(blueprints.items()))

    blueprints_per_name = blueprints
    blueprints = []
    internal_blueprints = []
    external_blueprints = []
    blueprints_per_scenes = {}

    blueprint_instances_per_library_scene = {}

    for blueprint in blueprints_per_name.values():
        blueprints.append(blueprint)
        if blueprint.local:
            internal_blueprints.append(blueprint)
            if blueprint.scene:
                if blueprint.scene.name not in blueprints_per_scenes:
                    blueprints_per_scenes[blueprint.scene.name] = []
                blueprints_per_scenes[blueprint.scene.name].append(blueprint.name)
        else:
            external_blueprints.append(blueprint)

    data = {
        "blueprints": blueprints,
        "blueprints_per_name": blueprints_per_name,
        "blueprint_names": list(blueprints_per_name.keys()),
        "blueprints_from_objects": blueprints_from_objects,
        "internal_blueprints": internal_blueprints,
        "external_blueprints": external_blueprints,
        "blueprints_per_scenes": blueprints_per_scenes,
        "blueprint_instances_per_main_scene": blueprint_instances_per_main_scene,
        "blueprint_instances_per_library_scene": blueprint_instances_per_library_scene,
        "internal_collection_instances": internal_collection_instances,
        "external_collection_instances": external_collection_instances,
        "blueprint_name_from_instances": blueprint_name_from_instances
    }

    return SimpleNamespace(**data)
