"""Preserve the newer Main map; reapply only the six reviewed lighting fields."""
from pathlib import Path
import hashlib,json,os,shutil,sys
main=Path(__file__).resolve().parents[2]
base=main/'Metadata/HeinMachLookSpin_20261015'
prep=json.loads((base/'Preparation.json').read_text())
work=Path(prep['work']);relative='Content/Maps/L_HeinMach_Environment.umap'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[-1]=='prepare':
    assert json.loads((base/'MainConflictAudit01/Audit.json').read_text())['status']=='passed'
    assert not (base/'MapRebase.json').exists()
    source=main/relative;target=work/relative
    digest=sha(source)
    backup=base/'RebaseBefore'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(target,backup)
    before=base/'RebaseMainBefore'/relative;before.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,before);assert sha(before)==digest
    temp=target.with_name(target.name+'.lookrebase');shutil.copy2(before,temp);temp.replace(target)
    assert sha(target)==digest and not os.path.samefile(source,target)
    report=dict(status='prepared',scene_baseline='MainConflictAudit01/Audit.json',
        targets={relative:digest},original_preparation_digest=prep['targets'][relative],
        previous_work_candidate_digest=sha(backup),main_asset_writes=0)
    (base/'MapRebase.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('MAP_REBASE_PREPARED',digest)
else:
    import unreal as u
    assert Path(u.Paths.project_dir()).resolve()==work
    rebase=json.loads((base/'MapRebase.json').read_text())
    assert sha(main/relative)==sha(work/relative)==rebase['targets'][relative]
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment');assert world
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    by_label={a.get_actor_label():a for a in actors}
    portal=by_label['HM_Yetuga_EntrancePortal']
    assert portal.get_class().get_name()=='KZBossPortal'
    assert portal.get_editor_property('exit_point')==by_label['HM_Yetuga_ArenaArrival']
    assert portal.get_editor_property('portal_effect').get_asset().get_path_name()=='/Game/VFX/Portal/YetugaEntrance/NS_YetugaEntrance.NS_YetugaEntrance'
    sun=by_label['HM_PreviewSun'].get_component_by_class(u.DirectionalLightComponent)
    sky=by_label['HM_PreviewSkyLight'].get_component_by_class(u.SkyLightComponent)
    pp=[a for a in actors if isinstance(a,u.PostProcessVolume) and a.get_actor_label().startswith('Art_NaturalLighting_')]
    fogs=[c for a in actors for c in a.get_components_by_class(u.ExponentialHeightFogComponent)]
    assert len(pp)==len(fogs)==1
    # TEMP reviewed BlueB values, same provenance as CandidateAuthor01; no new tuning.
    sun.set_editor_property('intensity',1000.)
    sun.set_editor_property('light_color',u.Color(r=150,g=186,b=255,a=255))
    sky.set_editor_property('intensity',10.)
    sky.set_editor_property('light_color',u.Color(r=108,g=157,b=255,a=255))
    settings=pp[0].get_editor_property('settings')
    assert not settings.get_editor_property('weighted_blendables').get_editor_property('array')
    settings.set_editor_property('auto_exposure_bias',-2.15);pp[0].set_editor_property('settings',settings)
    fogs[0].set_editor_property('volumetric_fog_emissive',u.LinearColor(r=.010,g=.024,b=.050,a=1.))
    assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
    assert sha(main/relative)==rebase['targets'][relative]
    out=Path(os.environ['KZ_LOOKSPIN_OUT'])
    (out/'Rebase.json').write_text(json.dumps(dict(status='saved',asset_saves=1,
        newer_main_preserved=True,owned_fields=6,after_sha256=sha(work/relative)),indent=2),encoding='utf-8')
    print('MAP_REBASE_SAVED')
