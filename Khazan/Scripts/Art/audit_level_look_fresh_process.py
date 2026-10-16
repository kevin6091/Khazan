"""Fresh serialization audit; run once in a separate NullRHI editor commandlet.

Never saves game packages, imports content, or drives the user's live editor.
NullRHI is deliberately not considered a visual or runtime gameplay test.
"""
from pathlib import Path
import json
import runpy
import sys
import unreal

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
h = runpy.run_path(str(root / 'Scripts/Art/restore_level_look.py'))
results = []
for level in ('StormPass', 'HeinMach'):
    world = unreal.EditorLoadingAndSavingUtils.load_map(h['MAPS'][level])
    if not world:
        raise RuntimeError('Fresh-process map load failed: ' + level)
    result = h['audit_restored_level'](level, 'FreshProcess')
    checks = result['checks']
    assert not checks['missing_mesh_material_slots']
    assert not checks['packed_input_mismatches']
    if level == 'StormPass':
        assert not checks['deleted_plan_actors_still_present']
        assert not checks['missing_preserved_actors']
        assert all(r['hit'] for r in checks['ground_support'])
    else:
        assert not checks['restored_tombstones']
        assert not checks['manual_override_changes_since_snapshot']
        assert not checks['PlayerStart_changes_since_snapshot']
    results.append({'level':level, 'actors':result['actor_count'],
                    'used_materials':result['material_count_used']})

bp = unreal.load_asset('/Game/_Art/Player/Character/Bluprints/BP_Player')
subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
components = []
for handle in handles:
    data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
    obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object_for_blueprint(data, bp)
    if isinstance(obj, unreal.SkeletalMeshComponent) and obj.get_editor_property('skeletal_mesh'):
        components.append({'component':obj.get_name(), 'custom_depth':obj.get_editor_property('render_custom_depth'),
                           'stencil':obj.get_editor_property('custom_depth_stencil_value')})
assert components and all(c['custom_depth'] and c['stencil'] == h['STENCIL'] for c in components)
h['write']('FreshProcessSummary', {'passed':True, 'maps':results, 'Player_components':components,
          'custom_depth_project':unreal.SystemLibrary.get_console_variable_int_value('r.CustomDepth'),
          'boundary':'Fresh map/material/Blueprint serialization readback under NullRHI; no visual, shader execution or combat PIE proof'})
print('KZ_LOOK_FRESH_AUDIT_PASSED ' + json.dumps(results))
