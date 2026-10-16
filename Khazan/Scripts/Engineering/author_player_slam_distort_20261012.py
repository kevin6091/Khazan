"""Append one owned floor burst at the existing plunge landing Start/End markers."""
from pathlib import Path
import json, os, re, traceback, unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT']);MAIN=Path(os.environ['KZ_PARRY_MAIN'])
BASE=MAIN/'Metadata/PlayerSlamDistort_20261012'
MONTAGE='/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack'
SOURCE='/Game/VFX/03_SlashHit/KZ_Parring_Distort'
VARIANT='/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort'
ID='KZExtra_PlungeDistort'
report={'success':False,'project':str(ROOT),'saved':[],'binding':[]}
def export(asset,name):
    task=u.AssetExportTask();task.object=asset;task.exporter=u.ObjectExporterT3D();task.filename=str(OUT/name);task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    return (OUT/name).read_text(encoding='utf-8-sig')
try:
    assert ROOT==MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
    assert (ROOT/'Content/_Art/Effects/Combat/PlayerSlamDistort').resolve().is_relative_to(ROOT)
    effect=u.load_asset(VARIANT)
    if not effect:effect=u.EditorAssetLibrary.duplicate_asset(SOURCE,VARIANT)
    assert effect
    report['exposed_parameters']='Native DEV authored User.KZFloorNormal Vec3'
    # These source GPU emitters use local space. Default SpriteFacing is +X
    # (UE NiagaraConstants.cpp). A geometric +90-degree pitch in the Notify
    # maps that local normal onto the traced floor normal; no gameplay tuning.
    for emitter in ['M_SW_distort_Sprite_0','M_SW_distort_Sprite001_1','Hit003_6']:
        renderer=u.load_object(None,effect.get_path_name()+':'+emitter+'.NiagaraSpriteRendererProperties_0');assert renderer
        binding=renderer.get_editor_property('sprite_facing_binding')
        report['binding'].append({'renderer':renderer.get_path_name(),'before':str(renderer.get_editor_property('facing_mode')),'binding':binding.export_text()})
        renderer.set_editor_property('facing_mode',u.NiagaraSpriteFacingMode.CUSTOM_FACING_VECTOR)
        data=binding.export_text()
        data=re.sub(r'RootName="[^"]+"','RootName="User.KZFloorNormal"',data)
        data=data.replace('Name="Particles.SpriteFacing"','Name="User.KZFloorNormal"').replace('Name="KZFloorNormal"','Name="User.KZFloorNormal"')
        data=data.replace('DataSetName="SpriteFacing"','DataSetName="KZFloorNormal"').replace('BindingSourceMode=ImplicitFromSource','BindingSourceMode=ExplicitUser')
        data=data.replace('bIsCachedParticleValue=True','bIsCachedParticleValue=False')
        assert binding.import_text(data)
        renderer.set_editor_property('sprite_facing_binding',binding)
        assert renderer.get_editor_property('facing_mode')==u.NiagaraSpriteFacingMode.CUSTOM_FACING_VECTOR
    assert u.EditorAssetLibrary.save_loaded_asset(effect,only_if_is_dirty=False);report['saved'].append(VARIANT)
    export(effect,'FloorNiagara.t3d')
    montage=u.load_asset(MONTAGE);assert montage
    original=export(montage,'MontageBefore.t3d')
    before_events=list(u.AnimationLibrary.get_animation_notify_events(montage))
    guid=lambda e:re.search(r'Guid=([0-9A-F]+)',e.export_text()).group(1)
    before_by_guid={guid(e):e.export_text() for e in before_events}
    changed=0
    for event in before_events:
        parent=event.get_editor_property('notify')
        if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
        children=list(parent.get_editor_property('batched_effects'))
        source=next((c for c in [parent]+children if str(c.get_editor_property('event_id'))=='KZExtra_PlungeGround'),None)
        if not source:continue
        children=[c for c in children if str(c.get_editor_property('event_id'))!=ID]
        child=u.new_object(u.KZAnimNotify_CombatEffect,outer=parent)
        for field in ['WindowStartTime','WindowEndTime','bEndEvent','bSpawnOnFloor','bAbsoluteRotation',
            'bAttached','bOnlyStartAttach','bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','bDestroyOnAnimEnd']:
            child.set_editor_property(field,source.get_editor_property(field))
        child.set_editor_property('event_id',ID)
        child.set_editor_property('niagara_template',effect)
        child.set_editor_property('relative_rotation',u.Rotator(pitch=0,yaw=0,roll=0))
        child.set_editor_property('source_socket','None')
        child.set_editor_property('relative_location',u.Vector(0,0,0))
        child.set_editor_property('source_package',SOURCE)
        child.set_editor_property('source_field','User requested asset; existing KZExtra_PlungeGround clock; floor-facing geometric adapter')
        children.append(child);parent.set_editor_property('batched_effects',children);changed+=1
        report['binding'].append({'id':ID,'start':child.get_editor_property('window_start_time'),'end':child.get_editor_property('window_end_time'),'stop':child.get_editor_property('bEndEvent')})
    assert changed==2
    for event in u.AnimationLibrary.get_animation_notify_events(montage):
        assert event.export_text()==before_by_guid[guid(event)]
    assert u.EditorAssetLibrary.save_loaded_asset(montage,only_if_is_dirty=False);report['saved'].append(MONTAGE)
    export(montage,'MontageAfter.t3d')
    report['success']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (OUT/'Authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SLAM_DISTORT_AUTHOR',report['success'],report.get('error',''))
if not report['success']:raise RuntimeError(report.get('error','Authoring failed'))
