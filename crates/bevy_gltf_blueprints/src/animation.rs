use bevy::prelude::*;
use bevy::utils::HashMap;

#[derive(Component, Reflect, Default, Debug)]
#[reflect(Component)]
/// storage for animations for a given entity's BLUEPRINT (ie for example a characters animations), essentially a clone of gltf's `named_animations`
pub struct BlueprintAnimations {
    pub named_animations: HashMap<String, Handle<AnimationClip>>,
}

#[derive(Component, Debug)]
/// Stop gap helper component : this is inserted into a "root" entity (an entity representing a whole gltf file)
/// so that the root entity knows which of its children contains an actualy `AnimationPlayer` component
/// this is for convenience, because currently , Bevy's gltf parsing inserts `AnimationPlayers` "one level down"
/// ie armature/root for animated models, which means more complex queries to trigger animations that we want to avoid
pub struct BlueprintAnimationPlayerLink(pub Entity);

#[derive(Component, Reflect, Default, Debug)]
#[reflect(Component)]
/// storage for scene level animations for a given entity (hierarchy), essentially a clone of gltf's `named_animations`
pub struct SceneAnimations {
    pub named_animations: HashMap<String, Handle<AnimationClip>>,
}

#[derive(Component, Debug)]
/// Stop gap helper component : this is inserted into a "root" entity (an entity representing a whole gltf file)
/// so that the root entity knows which of its children contains an actualy `AnimationPlayer` component
/// this is for convenience, because currently , Bevy's gltf parsing inserts `AnimationPlayers` "one level down"
/// ie armature/root for animated models, which means more complex queries to trigger animations that we want to avoid
pub struct SceneAnimationPlayerLink(pub Entity);

/// Stores Animation information: name, frame informations etc
#[derive(Reflect, Default, Debug)]
pub struct AnimationInfo {
    pub name: String,
    pub frame_start: f32,
    pub frame_end: f32,
    pub frames_length: f32,
    pub frame_start_override: f32,
    pub frame_end_override: f32,
}

/// Stores information about animations, to make things a bit easier api wise:
/// these components are automatically inserted by `gltf_auto_export` on entities that have animations
#[derive(Component, Reflect, Default, Debug)]
#[reflect(Component)]
pub struct AnimationInfos {
    pub animations: Vec<AnimationInfo>,
}

#[derive(Reflect, Default, Debug)]
pub struct AnimationMarker {
    // pub frame: u32,
    pub name: String,
    pub handled_for_cycle: bool,
}

/// Stores information about animation markers: practical for adding things like triggering events at specific keyframes etc
/// it is essentiall a hashmap of `AnimationName` => `HashMap`<`FrameNumber`, Vec of marker names>
#[derive(Component, Reflect, Default, Debug)]
#[reflect(Component)]
pub struct AnimationMarkers(pub HashMap<String, HashMap<u32, Vec<String>>>);

/// Event that gets triggered once a specific marker inside an animation has been reached (frame based)
/// Provides some usefull information about which entity , wich animation, wich frame & which marker got triggered
#[derive(Event, Debug)]
pub struct AnimationMarkerReached {
    pub entity: Entity,
    pub animation_name: String,
    pub frame: u32,
    pub marker_name: String,
}

#[derive(Component)]
pub struct CurrentAnimationInfo {
    pub animation_name: String,
    pub animation_length_seconds: f32,
    pub animation_length_frames: f32,
    pub last_triggered_markers: HashMap<String, u32>,
}

#[allow(clippy::too_many_arguments)]
fn trigger_animation_marker_events(
    commands: &mut Commands,
    entity: Entity,
    animation_name: &str,
    animation_length_seconds: f32,
    animation_length_frames: f32,
    frame: u32,
    markers: &AnimationMarkers,
    current_animation_info: Option<&CurrentAnimationInfo>,
    animation_marker_events: &mut EventWriter<AnimationMarkerReached>,
) {
    if let Some(matching_animation_marker) = markers.0.get(animation_name) {
        if let Some(matching_markers_per_frame) = matching_animation_marker.get(&frame) {
            for marker in matching_markers_per_frame {
                if let Some(current_info) = current_animation_info {
                    if let Some(last_triggered_frame) =
                        current_info.last_triggered_markers.get(marker)
                    {
                        if frame > *last_triggered_frame {
                            animation_marker_events.send(AnimationMarkerReached {
                                entity,
                                animation_name: animation_name.to_string(),
                                frame,
                                marker_name: marker.clone(),
                            });
                            commands.entity(entity).insert(CurrentAnimationInfo {
                                animation_name: animation_name.to_string(),
                                animation_length_seconds,
                                animation_length_frames,
                                last_triggered_markers: {
                                    let mut markers = current_info.last_triggered_markers.clone();
                                    markers.insert(marker.clone(), frame);
                                    markers
                                },
                            });
                        }
                    } else {
                        animation_marker_events.send(AnimationMarkerReached {
                            entity,
                            animation_name: animation_name.to_string(),
                            frame,
                            marker_name: marker.clone(),
                        });
                        commands.entity(entity).insert(CurrentAnimationInfo {
                            animation_name: animation_name.to_string(),
                            animation_length_seconds,
                            animation_length_frames,
                            last_triggered_markers: {
                                let mut markers = current_info.last_triggered_markers.clone();
                                markers.insert(marker.clone(), frame);
                                markers
                            },
                        });
                    }
                } else {
                    animation_marker_events.send(AnimationMarkerReached {
                        entity,
                        animation_name: animation_name.to_string(),
                        frame,
                        marker_name: marker.clone(),
                    });
                    commands.entity(entity).insert(CurrentAnimationInfo {
                        animation_name: animation_name.to_string(),
                        animation_length_seconds,
                        animation_length_frames,
                        last_triggered_markers: {
                            let mut markers = HashMap::new();
                            markers.insert(marker.clone(), frame);
                            markers
                        },
                    });
                }
            }
        }
    }
}

pub fn trigger_instance_animation_markers_events(
    mut commands: Commands,
    blueprint_animation_infos: Query<(
        Entity,
        &AnimationMarkers,
        &SceneAnimationPlayerLink,
        &SceneAnimations,
        Option<&CurrentAnimationInfo>,
    )>,
    animation_players: Query<&AnimationPlayer>,
    animation_clips: Res<Assets<AnimationClip>>,
    mut animation_marker_events: EventWriter<AnimationMarkerReached>,
) {
    for (entity, markers, link, animations, current_animation_info) in
        blueprint_animation_infos.iter()
    {
        let animation_player = animation_players.get(link.0).unwrap();
        let animation_clip = animation_clips.get(animation_player.animation_clip());

        if let Some(animation_clip) = animation_clip {
            let animation_name = animations
                .named_animations
                .iter()
                .find_map(|(key, value)| {
                    if value == animation_player.animation_clip() {
                        Some(key.clone())
                    } else {
                        None
                    }
                })
                .unwrap_or_default();

            let animation_length_seconds = animation_clip.duration();
            let animation_length_frames = current_animation_info
                .map(|info| info.animation_length_frames)
                .unwrap_or_default();

            let time_in_animation = animation_player.elapsed()
                - (animation_player.completions() as f32) * animation_length_seconds;
            let frame_seconds =
                (animation_length_frames / animation_length_seconds) * time_in_animation;
            let frame = frame_seconds as u32;

            trigger_animation_marker_events(
                &mut commands,
                entity,
                &animation_name,
                animation_length_seconds,
                animation_length_frames,
                frame,
                markers,
                current_animation_info,
                &mut animation_marker_events,
            );
        }
    }
}

pub fn trigger_blueprint_animation_markers_events(
    mut commands: Commands,
    blueprint_animation_infos: Query<(
        Entity,
        &BlueprintAnimationPlayerLink,
        &BlueprintAnimations,
        Option<&CurrentAnimationInfo>,
    )>,
    animation_markers_and_infos: Query<(Entity, &AnimationMarkers, &AnimationInfos, &Parent)>,
    animation_players: Query<&AnimationPlayer>,
    animation_clips: Res<Assets<AnimationClip>>,
    mut animation_marker_events: EventWriter<AnimationMarkerReached>,
) {
    for (entity, link, animations, current_animation_info) in blueprint_animation_infos.iter() {
        let animation_player = animation_players.get(link.0).unwrap();
        let animation_clip = animation_clips.get(animation_player.animation_clip());

        if let Some(animation_clip) = animation_clip {
            let animation_name = animations
                .named_animations
                .iter()
                .find_map(|(key, value)| {
                    if value == animation_player.animation_clip() {
                        Some(key.clone())
                    } else {
                        None
                    }
                })
                .unwrap_or_default();

            let animation_length_seconds = animation_clip.duration();
            let animation_length_frames = animation_markers_and_infos
                .iter()
                .find_map(|(_, _, animation_infos, parent)| {
                    if parent.get() == entity {
                        animation_infos
                            .animations
                            .iter()
                            .find(|anim| anim.name == animation_name)
                            .map(|anim| anim.frames_length)
                    } else {
                        None
                    }
                })
                .unwrap_or_default();

            let time_in_animation = animation_player.elapsed()
                - (animation_player.completions() as f32) * animation_length_seconds;
            let frame_seconds =
                (animation_length_frames / animation_length_seconds) * time_in_animation;
            let frame = frame_seconds.ceil() as u32;

            let markers = animation_markers_and_infos
                .iter()
                .find_map(|(_, markers, _, parent)| {
                    if parent.get() == entity {
                        Some(markers)
                    } else {
                        None
                    }
                })
                .expect("No markers found for animation");

            trigger_animation_marker_events(
                &mut commands,
                entity,
                &animation_name,
                animation_length_seconds,
                animation_length_frames,
                frame,
                markers,
                current_animation_info,
                &mut animation_marker_events,
            );
        }
    }
}
