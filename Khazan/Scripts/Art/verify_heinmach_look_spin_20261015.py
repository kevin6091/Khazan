"""Fresh saved readback for the two selected assets and protected donors."""
from pathlib import Path
import hashlib,json,os,re,unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);out=Path(os.environ['KZ_LOOKSPIN_OUT'])
root=Path(u.Paths.project_dir()).resolve()
source=(main/'Scripts/Art/audit_heinmach_look_spin_20261015.py').read_text(encoding='utf-8')
exec(compile(source,__file__,'exec'),globals())
baseline=json.loads((main/'Metadata/HeinMachLookSpin_20261015/BaselineAudit02/Audit.json').read_text(encoding='utf-8'))
rebase_file=main/'Metadata/HeinMachLookSpin_20261015/MapRebase.json'
if rebase_file.exists():
    rebase=json.loads(rebase_file.read_text())
    baseline['scene']=json.loads((rebase_file.parent/rebase['scene_baseline']).read_text(encoding='utf-8'))['scene']
current=json.loads((out/'Audit.json').read_text(encoding='utf-8'))
assert current['scene']['poses']==baseline['scene']['poses']
assert len(current['montages'])==3
original=baseline['montages'][0];spin=current['montages'][0]
assert original['clock']==spin['clock']
assert current['montages'][1:]==baseline['montages'][1:]
old={x['object']:x for x in original['effects'] if not str(x['EventId']).startswith('KZWeaponSlash_')}
now={x['object']:x for x in spin['effects']}
for name,data in old.items():assert now[name]==data,name
assert not any(x['NiagaraTemplate'] and 'KZ_Slash' in x['NiagaraTemplate'] for x in spin['effects'])
counts={}
for role in ['Overfury','ChargeStreak','ChargeVortex']:
    entries=[x for x in spin['effects'] if str(x['EventId']).startswith('KZSpin'+role+'_')]
    counts[role]=len(entries)//2
    for entry in entries:
        peers=[x for x in entries if x['EventId']==entry['EventId']]
        assert len(peers)==2 and {x['bEndEvent'] for x in peers}=={True,False}
        assert entry['ParticleTemplate'] and not entry['NiagaraTemplate']
assert counts=={'Overfury':6,'ChargeStreak':3,'ChargeVortex':2},counts
copy_path='/Game/_Art/Effects/Combat/Spinning/PP_Spinning_OverFury_Accent'
if u.EditorAssetLibrary.does_asset_exist(copy_path):
    import difflib
    source_path='/Game/_Art/Effects/DualAxeSword/Core/FP_Kazan_DualaxeSword_Overfury_slash_01'
    src=u.load_asset(source_path);cpy=u.load_asset(copy_path)
    export(src,out/'OverFury_Source.t3d');export(cpy,out/'OverFury_SpinCopy.t3d')
    before=(out/'OverFury_Source.t3d').read_text(encoding='utf-8-sig')
    after=(out/'OverFury_SpinCopy.t3d').read_text(encoding='utf-8-sig')
    after=after.replace(copy_path,source_path).replace(cpy.get_name(),src.get_name())
    diff=list(difflib.unified_diff(before.splitlines(),after.splitlines(),lineterm=''))
    changed=[line[1:].strip() for line in diff if line.startswith(('+','-')) and not line.startswith(('+++','---'))]
    (out/'OverFury_SpinCopy_Changes.patch').write_text('\n'.join(diff),encoding='utf-8')
    assert len(changed)==4 and all(x.startswith('Material=') for x in changed),changed
    assert all(x['ParticleTemplate']==copy_path+'.'+cpy.get_name() for x in spin['effects'] if str(x['EventId']).startswith('KZSpinOverfury_'))
for oldpp,newpp in zip(baseline['scene']['postprocess'],current['scene']['postprocess']):
    assert oldpp['actor']==newpp['actor']
    assert oldpp['settings'].replace('AutoExposureBias=-1.100000','AutoExposureBias=-2.150000')==newpp['settings']
assert len(current['scene']['lights'])==2
for light in current['scene']['lights']:
    if light['actor']=='HM_PreviewSun':assert light['intensity']==1000 and light['light_color']=='(B=255,G=186,R=150,A=255)'
    elif light['actor']=='HM_PreviewSkyLight':assert light['intensity']==10 and light['light_color']=='(B=255,G=157,R=108,A=255)'
    else:raise AssertionError(light)
for before,after in zip(baseline['scene']['fog'],current['scene']['fog']):
    expected=dict(before,volumetric_fog_emissive='(R=0.010000,G=0.024000,B=0.050000,A=1.000000)')
    assert after==expected
preparation=json.loads((main/'Metadata/HeinMachLookSpin_20261015/Preparation.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,digest in preparation['protected'].items():assert sha(main/relative)==digest,relative
if rebase_file.exists():
    verification_out=out
    portal_out=out/'PortalPreservation';portal_out.mkdir(exist_ok=True)
    os.environ['KZ_PORTAL_OUT']=str(portal_out)
    portal_source=(main/'Scripts/Engineering/readback_heinmach_portal_20261015.py').read_text(encoding='utf-8')
    portal_source=portal_source.replace("placement_root = root / 'Metadata/HeinMachPortal_20261015'","placement_root = main / 'Metadata/HeinMachPortal_20261015'")
    portal_source=portal_source.replace("root / 'Saved/ImportReports/HeinMach_PlayableCameraAnchors.json'","main / 'Saved/ImportReports/HeinMach_PlayableCameraAnchors.json'")
    exec(compile(portal_source,__file__,'exec'),globals())
    assert json.loads((portal_out/'Readback.json').read_text())['status']=='passed'
    out=verification_out
result=dict(status='passed',asset_saves=0,project=str(root),actor_count=len(current['scene']['poses']),actor_pose_changes=0,
            source_event_clock_guid_preserved=True,original_effect_objects_preserved=len(old),
            spinning_kz_slash_references=0,spinning_donor_pairs=counts,donor_montages_exact=True,
            protected_packages=len(preparation['protected']),scene_grade_and_local_exposure_unchanged=True,
            policy='BlueB explicit TEMP lighting; no global colour filter; retained VFX material exposure/fog isolation')
(out/'Verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('LOOK_SPIN_SAVED_VERIFIED',counts,len(old))
