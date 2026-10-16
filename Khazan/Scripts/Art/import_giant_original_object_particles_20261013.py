"""Reuse the existing Cascade importer for exactly two extracted field packages."""
from pathlib import Path
import unreal as u
import os, json, hashlib, re

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve();assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
prefix=(main/'Scripts/Art/combat_effects_import.py').read_text(encoding='utf-8').split('\ntry:\n    main()')[0]
prefix=prefix.replace("task.destination_path = '/Game/_Art/Effects/Metadata'","task.destination_path = '/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Scratch'")
prefix=prefix.replace("'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'","'xxDtbFloatParticleParameter': 'DistributionFloatParticleParameter', 'xxDtbVectorParticleParameter': 'DistributionVectorParticleParameter'")
prefix=prefix.replace("put(obj, 'MirrorFlags', ['EDVMF_Different'] * 3)","obj.set_editor_property('mirror_flags', [type(obj.get_editor_property('mirror_flags')[0]).EDVMF_DIFFERENT] * 3)")
H={};exec(compile(prefix,'<existing cascade importer definitions>','exec'),H)
rows=json.loads((main/'Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json').read_text(encoding='utf-8'))
lookup={r['source_package']:r for r in rows}
for name in ['HumanOriginal','ApesYetugaOriginal']:
    for row in json.loads((main/'Metadata/MonsterVFX_20261008'/name/'ImportReadyAssetManifest.json').read_text(encoding='utf-8')):
        if row['source_package'] not in lookup:lookup[row['source_package']]=row
targets=json.loads((main/'Metadata/GiantVFX_20261013/ObjectOriginal/Requests.json').read_text(encoding='utf-8'))
selected=[]
for package in targets:
    file=main/'Metadata/GiantVFX_20261013/ObjectOriginal/Extracted'/(package+'.json')
    data=json.loads(file.read_text(encoding='utf-8-sig'));root=next(x for x in data if x['Type']=='ParticleSystem' and not x.get('Outer'))
    row={'source_package':package,'source_type':'ParticleSystem','source_json':str(file),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
         'name':root['Name'],'destination':'/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/'+root['Name']}
    lookup[package]=row;selected.append(row)
def read_exports(path):
    file=Path(path);return json.loads((file if file.is_absolute() else main/file).read_text(encoding='utf-8-sig'))
H.update(ROOT=work,BASE=out/'Staging',META=out,ROWS=selected,LOOKUP=lookup,read_exports=read_exports)
report={'selected':selected,'saved':[],'missing_references':[]}
for row in selected:
    system=H['cascade'](row)
    assert u.EditorAssetLibrary.save_loaded_asset(system,only_if_is_dirty=False)
    report['saved'].append(system.get_path_name())
(out/'OriginalObjectImport.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('GIANT_ORIGINAL_OBJECT_PARTICLES_IMPORTED: '+str(len(report['saved'])))
