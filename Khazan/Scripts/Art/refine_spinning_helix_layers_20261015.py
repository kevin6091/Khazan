"""Spin-only OverFury copy: retain slash/sprites, hide the two helix mesh layers."""
from pathlib import Path
import hashlib,json,os,unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);work=Path(os.environ['KZ_LOOKSPIN_WORK'])
out=Path(os.environ['KZ_LOOKSPIN_OUT']);assert Path(u.Paths.project_dir()).resolve()==work
source_path='/Game/_Art/Effects/DualAxeSword/Core/FP_Kazan_DualaxeSword_Overfury_slash_01'
copy_path='/Game/_Art/Effects/Combat/Spinning/PP_Spinning_OverFury_Accent'
file='Content/'+copy_path.removeprefix('/Game/')+'.uasset'
assert not (main/file).exists() and not (work/file).exists()
source=u.load_asset(source_path);assert source
particle=u.AssetToolsHelpers.get_asset_tools().duplicate_asset('PP_Spinning_OverFury_Accent',copy_path.rsplit('/',1)[0],source)
assert isinstance(particle,u.ParticleSystem)
FX=u.FXConverterUtilitiesLibrary;changes=[]
hidden=u.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/M_KZGiant_TechnicalHidden')
assert hidden
for index,emitter in enumerate(FX.get_cascade_system_emitters(particle)):
    for level in range(max(1,len(particle.get_editor_property('lod_distances')))):
        lod=FX.get_cascade_emitter_lod_level(emitter,level);typedata=FX.get_lod_level_type_data_module(lod)
        if index in (1,2):
            assert typedata and typedata.get_editor_property('Mesh').get_name()=='FS_Spline_Helix_08'
            required=FX.get_lod_level_required_module(lod)
            before=required.get_editor_property('Material')
            required.set_editor_property('Material',hidden)
            assert required.get_editor_property('Material')==hidden
            changes.append(dict(emitter_index=index,lod=level,mesh=typedata.get_editor_property('Mesh').get_path_name(),
                                before_material=before.get_path_name(),after_material=hidden.get_path_name()))
assert len(changes)==2,changes
u.EditorAssetLibrary.set_metadata_tag(particle,'KZSourceParticle',source_path)
u.EditorAssetLibrary.set_metadata_tag(particle,'KZSpinOnlyPresentation','TEMP: suppress two helix sheets observed as angular grey membranes; source slash/GPU sprites/timing remain.')
assert u.EditorAssetLibrary.save_loaded_asset(particle,only_if_is_dirty=False)
montage=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack');assert montage
events=u.AnimationLibrary.get_animation_notify_events(montage);clock=[x.export_text() for x in events];count=0
for event in events:
    parent=event.get_editor_property('Notify')
    if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
    for fx in [parent]+list(parent.get_editor_property('BatchedEffects')):
        if str(fx.get_editor_property('EventId')).startswith('KZSpinOverfury_'):
            assert fx.get_editor_property('ParticleTemplate')==source
            fx.set_editor_property('ParticleTemplate',particle)
            fx.set_editor_property('SourceField',fx.get_editor_property('SourceField')+'; Spin-only copy omits helix membranes')
            count+=1
assert count==12 and clock==[x.export_text() for x in u.AnimationLibrary.get_animation_notify_events(montage)]
assert u.EditorAssetLibrary.save_loaded_asset(montage,only_if_is_dirty=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
preparation=json.loads((main/'Metadata/HeinMachLookSpin_20261015/Preparation.json').read_text())
for relative,digest in preparation['protected'].items():assert sha(main/relative)==digest,relative
report=dict(status='isolated_refinement_saved',asset_saves=2,source=source_path,particle=copy_path,file=file,
            main_before_sha256=None,work_after_sha256=sha(work/file),hidden_helix_emitters=changes,
            montage_reference_changes=count,notify_clock_guid_preserved=True,original_particle_unchanged=True)
(out/'Refinement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(main/'Metadata/HeinMachLookSpin_20261015/AdditionalTargets.json').write_text(json.dumps(dict(targets={file:None}),indent=2),encoding='utf-8')
print('SPIN_HELIX_REFINEMENT_SAVED',count,len(changes))
