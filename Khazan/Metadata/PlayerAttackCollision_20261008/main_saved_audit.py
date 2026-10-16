"""Read-only saved Main audit in the new owned process; never saves assets."""
import os,json,hashlib,datetime,traceback
from pathlib import Path
import unreal

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT=ROOT/'Metadata/PlayerAttackCollision_20261008'
report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),
        'project':str(Path(unreal.Paths.project_dir()).resolve()),'success':False,
        'asset_saved':False,'PIE_started':False,'existing_Main_touched':False}
try:
    assert Path(report['project'])==ROOT
    assert os.getpid()!=31344
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    before_dirty=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    assert not before_dirty
    receipt=json.loads((OUT/'SourceContentDelivered.json').read_text(encoding='utf-8'))
    for row in receipt['files']:
        assert hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()==row['after']
    definition=unreal.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
    assert definition
    report['draw_green_enabled']=definition.get_editor_property('draw_attack_collision')
    effect=definition.get_editor_property('attack_damage_effect')
    assert effect
    cdo=unreal.get_default_object(effect)
    mods=list(cdo.get_editor_property('modifiers'))
    assert len(mods)==2 and cdo.get_editor_property('duration_policy')==unreal.GameplayEffectDurationType.INSTANT
    report['effect']=effect.get_path_name()
    report['modifiers']=[m.export_text() for m in mods]
    report['nodes']=[]
    keys=windows=attack_nodes=0
    for node in definition.get_editor_property('nodes'):
        rows=list(node.get_editor_property('attack_windows'))
        node_id=str(node.get_editor_property('node_id'))
        count=sum(len(w.get_editor_property('keys')) for w in rows)
        if rows: attack_nodes+=1
        keys+=count;windows+=len(rows)
        assert all(w.get_editor_property('end_time')>=w.get_editor_property('start_time') and w.get_editor_property('source') for w in rows)
        report['nodes'].append({'node_id':node_id,'windows':len(rows),'keys':count,
          'HPDamage':[w.get_editor_property('hp_damage') for w in rows],
          'StaminaDamage':[w.get_editor_property('stamina_damage') for w in rows]})
    assert len(report['nodes'])==26 and attack_nodes==18 and windows==60 and keys==553
    report.update(attack_nodes=attack_nodes,window_count=windows,key_count=keys)
    bp=unreal.load_asset('/Game/_Art/Player/Character/Bluprints/BP_Player')
    report['player_BP_status']=str(bp.get_editor_property('status'))
    assert bp.get_editor_property('status')==unreal.BlueprintStatus.BS_UP_TO_DATE
    after_dirty=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    assert not after_dirty
    report.update(success=True,dirty_content=after_dirty,world=editor.get_editor_world().get_path_name())
except Exception:
    report['error']=traceback.format_exc()
(OUT/'MainFreshSavedReadback.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('PLAYER_ATTACK_SAVED_MAIN_AUDIT',json.dumps({k:v for k,v in report.items() if k not in ('nodes','modifiers')}))
assert report['success'],report.get('error')
