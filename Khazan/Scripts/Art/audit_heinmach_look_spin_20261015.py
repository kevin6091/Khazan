"""Targeted saved readback, not a repeated Content/FModel survey."""
from pathlib import Path
import hashlib,json,os,unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);out=Path(os.environ['KZ_LOOKSPIN_OUT'])
root=Path(u.Paths.project_dir()).resolve()
paths=['/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack',
 '/Game/_Art/Player/Animation/InGame/DAS/OverFury/AM_DAS_Player_OverFury',
 '/Game/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongChargeAttack']
def export(asset,path):
    task=u.AssetExportTask();task.object=asset;task.filename=str(path)
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
rows=[]
for path in paths:
    asset=u.load_asset(path);assert asset,path
    export(asset,out/(asset.get_name()+'.t3d'))
    row=dict(asset=path,clock=[],effects=[])
    for event in u.AnimationLibrary.get_animation_notify_events(asset):
        row['clock'].append(event.export_text())
        parent=event.get_editor_property('Notify')
        if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
        for fx in [parent]+list(parent.get_editor_property('BatchedEffects')):
            data=dict(object=fx.get_path_name())
            for key in ['EventId','bEndEvent','ParticleTemplate','NiagaraTemplate','SourceSocket',
                        'WindowStartTime','WindowEndTime','RelativeLocation','RelativeRotation','Scale3D',
                        'bAttached','bOnlyStartAttach','bSpawnOnFloor','bUseSourceCorrection','CustomTimeDilation',
                        'bDestroyOnAnimEnd','bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','OnNotifyEndDeattach',
                        'bAlignToWeaponSweep','bUseWorldParticleUnits','bOnAttackSuccessed']:
                value=fx.get_editor_property(key)
                if value is None or isinstance(value,(str,int,float,bool)):data[key]=value
                elif hasattr(value,'get_path_name'):data[key]=value.get_path_name()
                else:data[key]=value.export_text() if hasattr(value,'export_text') else str(value)
            row['effects'].append(data)
    rows.append(row)
world=u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment');assert world
scene=dict(poses={},lights=[],fog=[],postprocess=[])
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    scene['poses'][actor.get_actor_label()]=actor.get_actor_transform().export_text()
    for cls,key,fields in [(u.DirectionalLightComponent,'lights',['intensity','light_color']),
                          (u.SkyLightComponent,'lights',['intensity','light_color','real_time_capture','cubemap']),
                          (u.ExponentialHeightFogComponent,'fog',['fog_density','fog_inscattering_luminance','fog_max_opacity','fog_height_falloff','start_distance','directional_inscattering_luminance','volumetric_fog_emissive'])]:
        for c in actor.get_components_by_class(cls):
            data=dict(actor=actor.get_actor_label(),component=c.get_path_name())
            for field in fields:
                try:
                    v=c.get_editor_property(field);data[field]=v if v is None or isinstance(v,(str,int,float,bool)) else (v.export_text() if hasattr(v,'export_text') else str(v))
                except Exception:pass
            scene[key].append(data)
    if isinstance(actor,u.PostProcessVolume):scene['postprocess'].append(dict(actor=actor.get_actor_label(),settings=actor.get_editor_property('settings').export_text()))
(out/'Audit.json').write_text(json.dumps(dict(status='passed',project=str(root),asset_saves=0,montages=rows,scene=scene),indent=2),encoding='utf-8')
print('LOOK_SPIN_AUDIT_PASSED')
