"""Two isolated assets only: selected blue lighting and source-effect Spin layers."""
from pathlib import Path
import hashlib,json,os
import unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);root=Path(u.Paths.project_dir()).resolve()
out=Path(os.environ['KZ_LOOKSPIN_OUT']);work=Path(os.environ['KZ_LOOKSPIN_WORK'])
assert root==work
preparation=json.loads((main/'Metadata/HeinMachLookSpin_20261015/Preparation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,digest in preparation['targets'].items():assert sha(root/relative)==digest,relative
for relative,digest in preparation['protected'].items():assert sha(main/relative)==digest,relative

def export(asset,path):
    task=u.AssetExportTask();task.object=asset;task.filename=str(path)
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)

path='/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack'
montage=u.load_asset(path);assert montage
export(montage,out/'Spinning_Before.t3d')
events=u.AnimationLibrary.get_animation_notify_events(montage)
clock=[e.export_text() for e in events]
fields=['WindowStartTime','WindowEndTime','bEndEvent','SourceSocket','RelativeLocation',
        'RelativeLocationRandomMin','RelativeLocationRandomMax','RelativeRotation',
        'RelativeRotationRandomMin','RelativeRotationRandomMax','Scale3D','CustomTimeDilation',
        'bUseWorldParticleUnits','bAttached','bOnlyStartAttach','OnNotifyEndDeattach','bAbsoluteRotation',
        'bFaceCameraOutsideMeshBounds','TranslucencySortPriority','bSpawnOnFloor','bWinterOnly',
        'bDestroyOnNotifyEnd','bDestroyOnNotifyEndDeactived','bDestroyOnAnimEnd','bOnAttackSuccessed',
        'SurfaceRoutes','bOverrideSurface','SurfaceOverride','InstanceParameters','bUseSourceCorrection',
        'CorrectionBoneName','SourceCorrectionTransform','bUseCorrectionCurves',
        'SourceCorrectionTranslation','SourceCorrectionRotation','SourceCorrectionScale']
originals=[];replacements=[];added=[];ids=set()
over=u.load_asset('/Game/_Art/Effects/DualAxeSword/Core/FP_Kazan_DualaxeSword_Overfury_slash_01')
flow=u.load_asset('/Game/_Art/Effects/DualAxeSword/Core/FP_PlaneSlash_Flow_Strong')
burst=u.load_asset('/Game/_Art/Effects/DualAxeSword/Core/FP_Kazan_Dualaxesword_flow_burst_01')
assert over and flow and burst
# TEMP composite: six authored Spin sweeps + three Charge streak accents and
# two Charge vortices. Source clocks remain unchanged; donor PSs are untouched.
white_suffixes={'c85f84be','1e4b39e6','df5d8525'}
burst_suffixes={'c85f84be','a6066b61'}
for event in events:
    parent=event.get_editor_property('Notify')
    if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
    children=list(parent.get_editor_property('BatchedEffects'))
    source_by_id={str(fx.get_editor_property('EventId')):fx for fx in [parent]+children
                  if not str(fx.get_editor_property('EventId')).startswith('KZWeaponSlash_')}
    for fx in [parent]+children:
        ident=str(fx.get_editor_property('EventId'))
        if not ident.startswith('KZWeaponSlash_'):
            originals.append((fx,{f:str(fx.get_editor_property(f)) for f in fields+['ParticleTemplate','NiagaraTemplate','SourcePackage','SourceField']}))
            continue
        source_id=ident.removeprefix('KZWeaponSlash_');source=source_by_id[source_id]
        assert source.get_editor_property('ParticleTemplate').get_name()=='FP_Kazan_SpinningBeast_Axe_Slash_01'
        ending=bool(source.get_editor_property('bEndEvent'));key=(source_id,ending)
        assert key not in ids;ids.add(key)
        for field in fields:fx.set_editor_property(field,source.get_editor_property(field))
        fx.set_editor_property('EventId','KZSpinOverfury_'+source_id)
        fx.set_editor_property('NiagaraTemplate',None);fx.set_editor_property('ParticleTemplate',over)
        fx.set_editor_property('bAlignToWeaponSweep',False)
        fx.set_editor_property('WeaponEdgeNearSocket','None');fx.set_editor_property('WeaponEdgeTipSocket','None')
        fx.set_editor_property('WeaponSlashReferenceSpan',0.);fx.set_editor_property('WeaponSlashOutwardOffsetCm',0.)
        fx.set_editor_property('bUseSequencerTransform',False)
        fx.set_editor_property('Scale3D',u.Vector(1.12,1.12,1.0))
        fx.set_editor_property('SourcePackage','ProjectLookDev: reuse '+over.get_path_name())
        fx.set_editor_property('SourceField','TEMP Spinning composite; original Spin window/transform '+source_id)
        replacements.append(dict(id=str(fx.get_editor_property('EventId')),ending=ending,source_id=source_id,
                                 template=over.get_path_name(),scale_TEMP=[1.12,1.12,1.0]))
        for role,template,wanted,scale in [('ChargeStreak',flow,white_suffixes,1.08),('ChargeVortex',burst,burst_suffixes,1.2)]:
            if source_id[-8:] not in wanted:continue
            accent=u.new_object(u.KZAnimNotify_CombatEffect,outer=parent,
                name='Spin'+role+'_'+source_id+('_End' if ending else '_Begin'));assert accent
            for field in fields:accent.set_editor_property(field,source.get_editor_property(field))
            accent.set_editor_property('EventId','KZSpin'+role+'_'+source_id)
            accent.set_editor_property('ParticleTemplate',template)
            accent.set_editor_property('Scale3D',u.Vector(scale,scale,scale))
            if role=='ChargeVortex':
                accent.set_editor_property('SourceSocket','Bip001')
                accent.set_editor_property('RelativeLocation',u.Vector(0,0,0))
                accent.set_editor_property('RelativeRotation',u.Rotator(pitch=0,yaw=0,roll=0))
                accent.set_editor_property('bOnlyStartAttach',False)
            accent.set_editor_property('SourcePackage','ProjectLookDev: reuse '+template.get_path_name())
            accent.set_editor_property('SourceField','TEMP Spinning '+role+'; original Spin window '+source_id)
            children.append(accent)
            added.append(dict(id=str(accent.get_editor_property('EventId')),ending=ending,template=template.get_path_name(),scale_TEMP=scale))
    parent.set_editor_property('BatchedEffects',children)
assert len(ids)==12 and len(added)==10,(len(ids),len(added))
for fx,values in originals:assert values=={f:str(fx.get_editor_property(f)) for f in values},fx.get_path_name()
assert clock==[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(montage)]
u.EditorAssetLibrary.set_metadata_tag(montage,'KZSpinningPresentation','TEMP OverFury 6 + ChargeStreak 3 + ChargeVortex 2; original Spin retained; no KZ_Slash')
assert u.EditorAssetLibrary.save_loaded_asset(montage,only_if_is_dirty=False)
export(montage,out/'Spinning_After.t3d')

policy=dict(name='BlueB',sun_lux=1000.,sky_intensity=10.,exposure_bias_ev=-2.15,
            sun_rgb_srgb=[150,186,255],sky_rgb_srgb=[108,157,255],fog_emissive_linear=[.010,.024,.050])
world=u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment');assert world
changes=[]
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    for cls,intensity,rgb in [(u.DirectionalLightComponent,policy['sun_lux'],policy['sun_rgb_srgb']),
                              (u.SkyLightComponent,policy['sky_intensity'],policy['sky_rgb_srgb'])]:
        for component in actor.get_components_by_class(cls):
            component.set_editor_property('intensity',intensity)
            r,g,b=rgb;component.set_editor_property('light_color',u.Color(r=r,g=g,b=b,a=255))
            changes.append(dict(actor=actor.get_actor_label(),intensity=intensity,colour=component.get_editor_property('light_color').export_text()))
    if isinstance(actor,u.PostProcessVolume) and actor.get_actor_label().startswith('Art_NaturalLighting_'):
        settings=actor.get_editor_property('settings')
        assert not settings.get_editor_property('weighted_blendables').get_editor_property('array')
        settings.set_editor_property('auto_exposure_bias',policy['exposure_bias_ev'])
        actor.set_editor_property('settings',settings)
    for component in actor.get_components_by_class(u.ExponentialHeightFogComponent):
        r,g,b=policy['fog_emissive_linear']
        component.set_editor_property('volumetric_fog_emissive',u.LinearColor(r=r,g=g,b=b,a=1))
assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
for relative,digest in preparation['protected'].items():assert sha(main/relative)==digest,relative
report=dict(status='isolated_candidate_saved',asset_saves=2,lighting_policy_TEMP=policy,
            spin_replacements=replacements,spin_new_children=added,spin_original_objects_preserved=len(originals),
            notify_clock_guid_preserved=True,new_runtime_classes=0,new_particle_assets=0,
            rows=[dict(file=relative,before_sha256=digest,after_sha256=sha(root/relative)) for relative,digest in preparation['targets'].items()])
(out/'Author.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('LOOK_SPIN_CANDIDATE_SAVED',2,len(replacements),len(added))
