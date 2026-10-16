"""Fresh-load the two saved presentation assets; protect the original montage contracts."""
from pathlib import Path
import json,os,traceback,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_PARRY_MAIN']);OUT=Path(os.environ['KZ_PARRY_OUT'])
BASE=MAIN/'Metadata/PlayerSlamDistort_20261012';report={'success':False,'project':str(ROOT),'asset_saves':0}
try:
    montage=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack');assert montage
    original=u.load_asset('/Game/VFX/03_SlashHit/KZ_Parring_Distort');assert original
    effect=u.load_asset('/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort');assert effect
    report['renderers']=[]
    for emitter in ['M_SW_distort_Sprite_0','M_SW_distort_Sprite001_1','Hit003_6']:
        original_renderer=u.load_object(None,original.get_path_name()+':'+emitter+'.NiagaraSpriteRendererProperties_0')
        renderer=u.load_object(None,effect.get_path_name()+':'+emitter+'.NiagaraSpriteRendererProperties_0')
        assert renderer and original_renderer
        assert renderer.get_editor_property('facing_mode')==u.NiagaraSpriteFacingMode.CUSTOM_FACING_VECTOR
        normal=renderer.get_editor_property('sprite_facing_binding').export_text()
        assert 'User.KZFloorNormal' in normal and 'bBindingExistsOnSource=True' in normal,normal
        assert original_renderer.get_editor_property('facing_mode')==u.NiagaraSpriteFacingMode.FACE_CAMERA
        current_material=renderer.get_editor_property('material');original_material=original_renderer.get_editor_property('material')
        if current_material!=original_material:
            assert current_material.get_path_name().startswith('/Game/_Art/Effects/Combat/PlayerSlamDistort/')
            lib=u.MaterialEditingLibrary
            for key in lib.get_scalar_parameter_names(original_material):assert lib.get_material_instance_scalar_parameter_value(current_material,key)==lib.get_material_instance_scalar_parameter_value(original_material,key)
            for key in lib.get_vector_parameter_names(original_material):assert lib.get_material_instance_vector_parameter_value(current_material,key)==lib.get_material_instance_vector_parameter_value(original_material,key)
            for key in lib.get_texture_parameter_names(original_material):assert lib.get_material_instance_texture_parameter_value(current_material,key)==lib.get_material_instance_texture_parameter_value(original_material,key)
        report['renderers'].append({'path':renderer.get_path_name(),'material':renderer.get_editor_property('material').get_path_name(),'floor_normal_binding':normal})
    report['markers']=[]
    for event in u.AnimationLibrary.get_animation_notify_events(montage):
        parent=event.get_editor_property('notify')
        if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
        children=[parent]+list(parent.get_editor_property('batched_effects'))
        ground=next((x for x in children if str(x.get_editor_property('EventId'))=='KZExtra_PlungeGround'),None)
        new=[x for x in children if str(x.get_editor_property('EventId'))=='KZExtra_PlungeDistort']
        if new:
            assert ground and len(new)==1
            child=new[0]
            for field in ['WindowStartTime','WindowEndTime','bEndEvent','bSpawnOnFloor','bAbsoluteRotation','bAttached','bOnlyStartAttach',
                'bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','bDestroyOnAnimEnd']:
                assert child.get_editor_property(field)==ground.get_editor_property(field),field
            assert child.get_editor_property('NiagaraTemplate')==effect and not child.get_editor_property('ParticleTemplate')
            assert str(child.get_editor_property('SourceSocket'))=='None'
            assert child.get_editor_property('Scale3D')==u.Vector(1,1,1)
            assert child.get_editor_property('RelativeRotation')==u.Rotator(pitch=0,yaw=0,roll=0)
            report['markers'].append({'stop':child.get_editor_property('bEndEvent'),'start':child.get_editor_property('WindowStartTime'),'end':child.get_editor_property('WindowEndTime')})
    assert len(report['markers'])==2 and sorted(x['stop'] for x in report['markers'])==[False,True]
    task=u.AssetExportTask();task.object=montage;task.exporter=u.ObjectExporterT3D();task.filename=str(OUT/'Montage.t3d');task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    before=(BASE/'Author01/MontageBefore.t3d').read_text(encoding='utf-8-sig').splitlines()
    after=(OUT/'Montage.t3d').read_text(encoding='utf-8-sig').splitlines()
    protected=lambda lines:[x.strip() for x in lines if x.strip().startswith(('Notifies(', 'CompositeSections(', 'SlotAnimTracks(', 'BlendIn=', 'BlendOut=', 'RateScale='))]
    assert protected(before)==protected(after),'Existing event/section/segment/blend data changed'
    report['protected_montage_rows']=len(protected(before));report['success']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (OUT/'SavedAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SLAM_DISTORT_SAVED',report['success'],report.get('error',''))
if not report['success']:raise RuntimeError(report.get('error','Saved audit failed'))
