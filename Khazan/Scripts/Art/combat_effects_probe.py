"""Transient reflection probe. Does not save or modify existing packages."""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/Extracted/CombatEffects_20261006'
result = {}
objects = []
for name in ('ParticleSystem', 'ParticleSpriteEmitter', 'ParticleLODLevel',
             'ParticleModuleLifetime', 'ParticleModuleTypeDataGpu'):
    try:
        cls = unreal.load_class(None, '/Script/Engine.' + name)
        obj = unreal.new_object(cls, outer=objects[0] if name.startswith('ParticleModule') else None)
        objects.append(obj)
        result[name] = {'class': str(cls), 'python_type': type(obj).__name__}
        fields = {'ParticleSystem': ['Emitters', 'LODDistances'],
                  'ParticleSpriteEmitter': ['LODLevels', 'EmitterName'],
                  'ParticleLODLevel': ['RequiredModule', 'Modules', 'SpawnModule'],
                  'ParticleModuleLifetime': ['Lifetime'],
                  'ParticleModuleTypeDataGpu': ['EmitterInfo', 'ResourceData']}.get(name, [])
        for key in fields:
            try:
                value = obj.get_editor_property(key)
                result[name][key] = {'type': type(value).__name__, 'value': str(value)[:300]}
                obj.set_editor_property(key, value, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                if key == 'Lifetime':
                    table = value.get_editor_property('Table')
                    table.set_editor_property('Values', [0.5, 1.5])
                    table.set_editor_property('Op', 2)
                    table.set_editor_property('EntryCount', 1)
                    table.set_editor_property('EntryStride', 2)
                    table.set_editor_property('SubEntryStride', 1)
                    value.set_editor_property('Table', table)
                    value.set_editor_property('Distribution', None)
                    obj.set_editor_property(key, value, notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
                    result[name][key]['table_readback'] = obj.get_editor_property(key).get_editor_property('Table').export_text()
            except Exception as e:
                result[name][key] = {'error': str(e)}
    except Exception:
        result[name] = {'error': traceback.format_exc()}
(OUT / 'ReflectionProbe.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('KZ_COMBAT_EFFECTS_PROBE_COMPLETE')

ps = objects[0]
emitter = unreal.new_object(unreal.load_class(None, '/Script/Engine.ParticleSpriteEmitter'), outer=ps, name='CombatTransientProbeEmitter')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world, 'SETNOPEC ' + ps.get_path_name() + ' Emitters (ParticleSpriteEmitter\'' + emitter.get_path_name() + '\')')
result['console_set'] = {'path': ps.get_path_name(), 'getters': [s for s in dir(unreal.FXConverterUtilitiesLibrary) if 'cascade' in s or 'lifetime' in s]}
try:
    result['console_set']['emitters'] = [e.get_path_name() for e in unreal.FXConverterUtilitiesLibrary.get_cascade_system_emitters(ps)]
except Exception as e:
    result['console_set']['error'] = str(e)
(OUT / 'ReflectionProbe.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
