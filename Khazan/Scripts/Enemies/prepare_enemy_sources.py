"""Resolve the two HeinMach tutorial visual recipes and their art dependencies.

Runs outside UE with its bundled Python. Extraction uses the installed FModel
configuration; no credentials are copied to any report.
"""
import json
import pathlib
import subprocess
import hashlib
import datetime

PROJECT = pathlib.Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'Saved/Extracted/HeinMachEnemies'
META = ROOT / 'Metadata'
DOTNET = pathlib.Path.home() / '.dotnet/dotnet.exe'
DLL = PROJECT / 'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.dll'

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def refs(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ('AssetPathName', 'ObjectPath') and isinstance(v, str):
                if v.startswith('/Game/'):
                    yield v.split('.')[0].replace('/Game/', 'BBQ/Content/')
                elif v.startswith(('BBQ/Content/', 'Engine/Content/')):
                    yield v.split('.')[0]
            yield from refs(v)
    elif isinstance(value, list):
        for v in value:
            yield from refs(v)

def extract_metadata(packages, tag):
    packages = sorted(p for p in set(packages) if not (META/(p+'.json')).exists())
    if packages:
        path = ROOT / ('Request_'+tag+'.json')
        write(path, packages)
        subprocess.run([str(DOTNET), str(DLL), 'metadata', str(META), str(path)], check=True)

def main():
    recipes = {}
    for family, name in [('Sword','CD_RD_Human_Adult_M_EmpireWounded_001'), ('SwordShield','CD_RD_Human_Adult_M_EmpireWoounded_SwordShield_001')]:
        file = next(META.rglob(name+'.json'))
        data = read(file)
        props = data[-1]['Properties']
        recipes[family] = {'source':str(file.relative_to(META)).replace('\\','/')[:-5], 'properties':props}
    write(ROOT/'VisualRecipes.json', recipes)
    requested = set()
    for recipe in recipes.values():
        requested.update(refs(recipe['properties']))
    cb_names = ['CB_EmpireSword_Early','CB_Empire_SwordShield','CB_EmpireHalberd_E_Early']
    design = set()
    for name in cb_names:
        file = next(META.rglob(name+'.json'))
        design.add(str(file.relative_to(META)).replace('\\','/')[:-5])
        data = read(file)
        for obj in data:
            props = obj.get('Properties',{})
            if 'SkeletalMesh' in props:
                requested.update(refs(props['SkeletalMesh']))
            if obj.get('Name','').startswith('Default__'):
                for key in ['DefaultDefaultWeaponSlots','AnimationBlueprint','AnimationProfiles']:
                    design.update(refs(props.get(key)))
            if isinstance(obj.get('SuperStruct'),dict):
                design.update(refs(obj['SuperStruct']))
    requested.update(refs(read(next(META.rglob('WS_EmpireSword_Early_Equip.json')))))
    extract_metadata(requested | design, 'visual_roots')
    visual_types = {'SkeletalMesh','StaticMesh','Texture2D','TextureCube','Texture2DArray','AnimSequence'}
    expand_types = visual_types | {'MaterialInstanceConstant','Material','PhysicsAsset','Skeleton','AnimBlueprintGeneratedClass'}
    visited=set(); exports=set(); missing=set(); dependencies=[]
    pending=requested | design
    round_no=0
    while pending:
        round_no+=1
        extract_metadata(pending, 'closure_%02d'%round_no)
        next_pending=set()
        for package in sorted(pending):
            visited.add(package)
            file=META/(package+'.json')
            if not file.exists():
                missing.add(package);continue
            objs=read(file)
            for obj in objs:
                typ=obj['Type']
                if typ in visual_types: exports.add(package)
                if typ in expand_types:
                    # Skeleton sockets/physics are preserved but their preview meshes
                    # and animation notify defaults must not drag in other enemies.
                    if typ in {'Skeleton','PhysicsAsset'}: continue
                    if typ=='AnimBlueprintGeneratedClass':
                        candidates = {r for r in refs(obj) if '/Art/Character/' in r}
                    else:
                        candidates=set(refs(obj))
                    for ref in candidates:
                        if ref!=package:
                            dependencies.append({'source':package,'target':ref,'owner_type':typ})
                            if ref not in visited and ref not in pending and ref not in missing:next_pending.add(ref)
        pending=next_pending
    # Only renderable art is passed to ActorX/texture exporters.
    write(ROOT/'ArtExportRequests.json', sorted(exports))
    write(ROOT/'SourceClosure.json', {'packages':sorted(visited),'exports':sorted(exports),'missing':sorted(missing),'dependencies':dependencies})
    with open(ROOT/'ArtExport.log','w',encoding='utf-8') as log:
        proc=subprocess.run([str(DOTNET),str(DLL),'export',str(ROOT/'Assets'),str(ROOT/'ArtExportRequests.json')],stdout=log,stderr=subprocess.STDOUT)
    print('SOURCE_CLOSURE packages=%d exports=%d missing=%d export_exit=%d'%(len(visited),len(exports),len(missing),proc.returncode))
    if proc.returncode:raise RuntimeError('Inspect ArtExport.log and Assets/ExportReport.json')
    write(ROOT/'SourceFileHashes.json',{str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for base in [META,ROOT/'Assets'] for f in base.rglob('*') if f.is_file()})

if __name__=='__main__': main()
