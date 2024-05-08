use bevy::{
    core::Name,
    ecs::{
        entity::Entity,
        query::{Added, Without},
        reflect::{AppTypeRegistry, ReflectComponent},
        world::World,
    },
    gltf::GltfExtras,
    hierarchy::Parent,
    log::{info, warn},
    reflect::{Reflect, TypeRegistration},
    utils::HashMap,
};

use crate::{ronstring_to_reflect_component, GltfProcessed};

pub fn add_components_from_gltf_extras(world: &mut World) {
    let mut entity_component_map: HashMap<Entity, Vec<(Box<dyn Reflect>, TypeRegistration)>> =
        HashMap::new();

    register_missing_types(world);
    {
        let mut extras = world.query_filtered::<(Entity, &Name, &GltfExtras, &Parent), (Added<GltfExtras>, Without<GltfProcessed>)>();
        let type_registry: &AppTypeRegistry = world.resource();
        let type_registry = type_registry.read();
        for (entity, name, gltf_extras, parent) in extras.iter(world) {
            info!("Processing entity: {:?}, name: {}", entity, name);

            let reflect_components =
                ronstring_to_reflect_component(&gltf_extras.value, &type_registry);
            let target_entity = get_target_entity(entity, name, parent);

            update_entity_component_map(
                &mut entity_component_map,
                target_entity,
                reflect_components,
            );
        }
    }
    insert_components(world, &entity_component_map);
}

fn insert_components(
    world: &mut World,
    entity_component_map: &HashMap<Entity, Vec<(Box<dyn Reflect>, TypeRegistration)>>,
) {
    let type_registry: &AppTypeRegistry = world.resource();
    let type_registry = type_registry.clone();
    let type_registry = type_registry.read();
    for (entity, components) in entity_component_map {
        info!("Inserting components for entity: {:?}", entity);

        for (component, type_registration) in components {
            let component_type = component.get_represented_type_info().unwrap().type_path();
            info!("Inserting component: {}", component_type);

            match type_registration.data::<ReflectComponent>() {
                Some(reflect_component) => {
                    let mut entity_mut = world.entity_mut(*entity);
                    reflect_component.insert(&mut entity_mut, component.as_ref(), &type_registry);

                    entity_mut.insert(GltfProcessed);
                }
                None => {
                    warn!("Unable to reflect component: {}", component_type);
                    continue;
                }
            }
        }
    }
}
fn register_missing_types(world: &mut World) {
    let type_registry: &AppTypeRegistry = world.resource();
    let mut type_registry = type_registry.write();

    type_registry.register::<Vec<String>>();
    type_registry.register::<HashMap<String, Vec<String>>>();
    // Register other missing types...
}

fn get_target_entity(entity: Entity, name: &Name, parent: &Parent) -> Entity {
    if name.as_str().contains("components") || name.as_str().ends_with("_pa") {
        info!("Adding components to parent entity");
        parent.get()
    } else {
        entity
    }
}

fn update_entity_component_map(
    entity_component_map: &mut HashMap<Entity, Vec<(Box<dyn Reflect>, TypeRegistration)>>,
    target_entity: Entity,
    reflect_components: Vec<(Box<dyn Reflect>, TypeRegistration)>,
) {
    if let Some(components) = entity_component_map.get_mut(&target_entity) {
        components.extend(reflect_components);
    } else {
        entity_component_map.insert(target_entity, reflect_components);
    }
}
