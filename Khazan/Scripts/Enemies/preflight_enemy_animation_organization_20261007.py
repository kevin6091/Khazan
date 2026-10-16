"""Read-only UE preflight; synchronize exact referencers in the isolated workspace."""
from pathlib import Path
from collections import Counter
import hashlib, json, shutil
import unreal

WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Metadata/EnemyAnimationOrganization_20261007'
plan=json.loads((OUT/'RenamePlan.json').read_text(encoding='utf-8'))
assert plan['status']=='PreflightReady'
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
registry=unreal.AssetRegistryHelpers.get_asset_registry()
options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True)
before=json.loads((OUT/'BeforeManifest.json').read_text(encoding='utf-8'))
known={r['path']:r['sha256'] for r in before['files']}
rows=[];incoming=set();destinations=set()
def v(t):return dict(translation=[t.translation.x,t.translation.y,t.translation.z],rotation=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],scale=[t.scale3d.x,t.scale3d.y,t.scale3d.z])
for index,row in enumerate(plan['rows']):
    asset=unreal.load_asset(row['old']); assert isinstance(asset,unreal.AnimSequence),row['old']
    assert row['new'].lower() not in destinations;destinations.add(row['new'].lower())
    assert not unreal.EditorAssetLibrary.does_asset_exist(row['new']),row['new']
    model=asset.controller.get_model_interface()
    skeleton=asset.get_editor_property('skeleton')
    bones=[str(b) for b in skeleton.get_reference_pose().get_bone_names()]
    tracks=[str(b) for b in model.get_bone_track_names()]
    assert tracks and tracks[0].lower()==bones[0].lower(),row['old']
    length=asset.get_play_length();rate=model.get_frame_rate()
    refs=[str(p) for p in registry.get_referencers(row['old'],options)]
    incoming.update(refs)
    rows.append(dict(old=row['old'],new=row['new'],family=row['family'],category=row['category'],
                     skeleton=skeleton.get_path_name(),root=bones[0],first_track=tracks[0],model=model.get_class().get_name(),
                     frames=model.get_number_of_frames(),keys=model.get_number_of_keys(),fps=[rate.numerator,rate.denominator],length=length,
                     rate_scale=asset.get_editor_property('rate_scale'),enable_root_motion=asset.get_editor_property('enable_root_motion'),force_root_lock=asset.get_editor_property('force_root_lock'),
                     root_lock=str(asset.get_editor_property('root_motion_root_lock')),root_extraction=[v(unreal.AnimationLibrary.extract_root_track_transform(asset,t)) for t in [0.0,length*.5,length]],
                     referencers=refs))
    if (index+1)%50==0:(OUT/'PreflightProgress.json').write_text(json.dumps(dict(done=index+1,total=len(plan['rows']))),encoding='utf-8')
reference_files=[]
for package in sorted(incoming):
    if not package.startswith('/Game/'):continue
    relative='Content/'+package.removeprefix('/Game/')
    suffix=next((s for s in ['.uasset','.umap'] if (MAIN/(relative+s)).is_file()),None)
    if not suffix:raise RuntimeError('Missing Main referencer '+package)
    relative+=suffix;source=MAIN/relative;sha=hashlib.sha256(source.read_bytes()).hexdigest()
    backup=OUT/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if backup.exists():assert hashlib.sha256(backup.read_bytes()).hexdigest()==sha,relative
    else:shutil.copy2(source,backup)
    if relative not in known:
        target=WORK/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        before['files'].append(dict(path=relative,sha256=sha));known[relative]=sha
    reference_files.append(dict(package=package,file=relative,sha256=sha))
# Captured from byte-identical Main BP packages in the original stock work module.
# Never divide an already changed native default again on an author retry.
policy=json.loads((OUT/'AITuningPlan.json').read_text(encoding='utf-8'))
assert len(policy)==4
(OUT/'BeforeManifest.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
(OUT/'Preflight.json').write_text(json.dumps(dict(status='Passed',rows=rows,reference_files=reference_files),indent=2),encoding='utf-8')
print(json.dumps(dict(status='Passed',assets=len(rows),models=dict(Counter(r['model'] for r in rows)),roots=dict(Counter(r['root'] for r in rows)),referencers=len(reference_files))))
