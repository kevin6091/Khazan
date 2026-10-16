"""Restore the existing character stencil contract on newly assembled parts."""
from pathlib import Path
import hashlib
import json
import traceback
import unreal
STAGE=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
ROOT=STAGE.parents[2]
assert STAGE==ROOT/'Saved/ArtStaging/HeinMachGhostingParts_20261008',STAGE
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008/Parts'
REL=Path('Content/_Art/Player/Character/Bluprints/BP_Player.uasset')
ASSET='/Game/_Art/Player/Character/Bluprints/BP_Player'
MODE='audit' if '-GhostPartsMode=audit' in unreal.SystemLibrary.get_command_line() else 'author'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
REPORT={'success':False,'mode':MODE,'main_before_sha256':sha(ROOT/REL),
        'stage_before_sha256':sha(STAGE/REL),'stage':str(STAGE),'asset':ASSET}

def snapshot(bp):
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib=unreal.SubobjectDataBlueprintFunctionLibrary
    rows=[];objects={}
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data=lib.get_data(h)
        obj=lib.get_object_for_blueprint(data,bp)
        if not isinstance(obj,unreal.SkeletalMeshComponent) or obj.get_path_name() in objects:
            continue
        objects[obj.get_path_name()]=obj
        fields={}
        for key in ('render_custom_depth','custom_depth_stencil_value','skeletal_mesh_asset',
                    'anim_class','animation_mode','physics_asset_override','visible','hidden_in_game',
                    'visibility_based_anim_tick_option','enable_update_rate_optimizations',
                    'relative_location','relative_rotation','relative_scale3d','simulate_physics',
                    'per_bone_motion_blur'):
            try:
                value=obj.get_editor_property(key)
                if isinstance(value,unreal.Object):value=value.get_path_name()
                elif isinstance(value,unreal.Vector):value=[value.x,value.y,value.z]
                elif isinstance(value,unreal.Rotator):value=[value.pitch,value.yaw,value.roll]
                elif not isinstance(value,(str,int,float,bool,type(None))):value=str(value)
                fields[key]=value
            except Exception as e:fields[key]={'not_exposed':str(e)}
        rows.append({'component':obj.get_name(),'fields':fields})
    return sorted(rows,key=lambda x:x['component']),objects

try:
    bp=unreal.load_asset(ASSET)
    assert bp is not None
    before,objects=snapshot(bp)
    REPORT['before']=before
    if MODE=='author':
        (OUT/'Before').mkdir(parents=True,exist_ok=True)
        (OUT/'Before/BP_Player.uasset').write_bytes((ROOT/REL).read_bytes())
        bp.modify()
        changed=[]
        for obj in objects.values():
            if not obj.get_editor_property('skeletal_mesh_asset') or not obj.get_editor_property('visible'):
                continue
            old=obj.get_editor_property('custom_depth_stencil_value')
            assert old in (0,254),(obj.get_path_name(),old)
            if old!=254 or not obj.get_editor_property('render_custom_depth'):
                obj.modify()
                obj.set_editor_property('render_custom_depth',True)
                obj.set_editor_property('custom_depth_stencil_value',254)
                changed.append(obj.get_name())
        assert len(changed)==7,changed
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp,only_if_is_dirty=False)
        REPORT['changed_components']=changed
    after,_=snapshot(bp)
    REPORT['after']=after
    assert len(after)==8,after
    assert all(r['fields']['render_custom_depth'] and r['fields']['custom_depth_stencil_value']==254 for r in after)
    if MODE=='author':
        def preserved(row):
            return {'component':row['component'],'fields':{k:v for k,v in row['fields'].items()
                    if k not in ('render_custom_depth','custom_depth_stencil_value')}}
        assert list(map(preserved,before))==list(map(preserved,after)),'Non-render settings changed'
    else:
        author=json.loads((OUT/'authorReport.json').read_text(encoding='utf-8'))
        assert after==author['after'],'Fresh load changed templates'
        assert sha(STAGE/REL)==author['stage_after_sha256']
    REPORT['blueprint_status']=str(bp.get_editor_property('status'))
    assert 'BS_UP_TO_DATE' in REPORT['blueprint_status'],REPORT['blueprint_status']
    REPORT.update(success=True,main_after_sha256=sha(ROOT/REL),stage_after_sha256=sha(STAGE/REL))
    assert REPORT['main_before_sha256']==REPORT['main_after_sha256'],'Main changed during private authoring'
    print('KZ_HEINMACH_GHOST_PARTS_'+MODE.upper()+'_PASSED')
except Exception:
    REPORT['error']=traceback.format_exc()
    raise
finally:
    (OUT/(MODE+'Report.json')).write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
