"""Read-only saved scene/API probe, used in an isolated NullRHI process."""
from pathlib import Path
import hashlib
import json
import sys
import unreal

sys.dont_write_bytecode = True
ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
OUT.mkdir(parents=True, exist_ok=True)


def props(obj, fields):
    result = {}
    for key in fields:
        try:
            value = obj.get_editor_property(key)
            result[key] = value if isinstance(value, (float, int, str, bool)) else str(value)
        except Exception as e:
            result[key] = 'UNAVAILABLE: ' + str(e)
    return result


def pose(actor):
    p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    return [p.x, p.y, p.z, r.pitch, r.yaw, r.roll, s.x, s.y, s.z]


world = unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
assert world
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
rows = []
pp = []
env = []
fields = ['auto_exposure_method', 'auto_exposure_min_brightness', 'auto_exposure_max_brightness',
          'auto_exposure_bias', 'auto_exposure_speed_up', 'auto_exposure_speed_down',
          'bloom_intensity', 'bloom_threshold', 'lens_flare_intensity', 'bloom_dirt_mask_intensity',
          'color_saturation', 'color_saturation_shadows', 'color_saturation_midtones',
          'color_saturation_highlights', 'color_contrast_midtones', 'color_gain_shadows',
          'color_gain_highlights', 'color_contrast_highlights', 'color_correction_shadows_max',
          'color_correction_highlights_min', 'scene_color_tint', 'film_slope', 'film_toe',
          'film_shoulder', 'scene_fringe_intensity', 'motion_blur_amount', 'motion_blur_target_fps',
          'depth_of_field_focal_distance', 'depth_of_field_fstop', 'weighted_blendables']
for a in actors:
    label = a.get_actor_label()
    row = {'label': label, 'class': a.get_class().get_name(), 'pose': pose(a)}
    rows.append(row)
    if isinstance(a, unreal.PostProcessVolume):
        settings = a.get_editor_property('settings')
        pp.append(dict(row, settings=props(settings, fields + ['override_' + n for n in fields]),
                       policy=props(a, ['unbound', 'enabled', 'priority', 'blend_radius', 'blend_weight'])))
    if label.startswith(('HM_Preview', 'HM_Environment')):
        entry = dict(row, components=[])
        for c in a.get_components_by_class(unreal.SceneComponent):
            cr = {'class': c.get_class().get_name(), 'name': c.get_name(),
                  'properties': props(c, ['visible', 'hidden_in_game', 'mobility'])}
            if isinstance(c, unreal.StaticMeshComponent):
                mesh = c.get_editor_property('static_mesh')
                cr['mesh'] = mesh.get_path_name() if mesh else None
                cr['materials'] = [c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]
            if isinstance(c, unreal.LightComponentBase):
                cr['properties'].update(props(c, ['intensity', 'light_color']))
            entry['components'].append(cr)
        env.append(entry)
snapshot = {'world': world.get_path_name(), 'count': len(rows), 'actors': rows,
            'post_process': pp, 'environment': env,
            'map_sha256': hashlib.sha256((ROOT / 'Content/Maps/L_HeinMach_Environment.umap').read_bytes()).hexdigest()}
(OUT / 'Before.json').write_text(json.dumps(snapshot, indent=2) + '\n', encoding='utf-8')
names = ['FXConverterUtilitiesLibrary', 'NiagaraSystemConversionContext', 'NiagaraEmitterConversionContext',
         'NiagaraScriptConversionContext', 'NiagaraEmitter', 'NiagaraSystem', 'NiagaraComponent',
         'NiagaraScriptConversionContextInput', 'NiagaraSpriteRendererProperties', 'AssetTools',
         'BlueprintEditorLibrary', 'MaterialExpressionCustom', 'NiagaraPythonScriptModuleInput']
api = {}
for name in names:
    cls = getattr(unreal, name, None)
    api[name] = {'doc': getattr(cls, '__doc__', ''), 'members': {n: getattr(getattr(cls, n), '__doc__', '')
                    for n in dir(cls) if not n.startswith('_') and any(k in n for k in ['create', 'set_', 'final', 'emitter', 'module', 'compile', 'parameter', 'renderer'])}} if cls else None
(OUT / 'EditorAPI.json').write_text(json.dumps(api, indent=2) + '\n', encoding='utf-8')
print('KZ_HEINMACH_WEATHER_PROBE ' + json.dumps({'count': len(rows), 'PP':len(pp), 'environment':len(env), 'out':str(OUT)}))
