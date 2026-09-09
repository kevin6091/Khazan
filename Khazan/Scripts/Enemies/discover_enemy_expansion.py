"""Reuse stored sources and follow only requested human enemy art/animation roots."""
import pathlib,json,subprocess,shutil
PROJECT=pathlib.Path(__file__).resolve().parents[2]
OLD=PROJECT/'Saved/Extracted/HeinMachEnemies'
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
META=ROOT/'Metadata'
DOTNET=pathlib.Path.home()/'.dotnet/dotnet.exe'
DLL=PROJECT/'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.dll'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def refs(v):
    if isinstance(v,dict):
        for k,x in v.items():
            if k in ['AssetPathName','ObjectPath'] and isinstance(x,str):
                if x.startswith('/Game/'):yield x.split('.')[0].replace('/Game/','BBQ/Content/')
                elif x.startswith(('BBQ/Content/','Engine/Content/')):yield x.split('.')[0]
            if isinstance(x,(dict,list)):yield from refs(x)
    elif isinstance(v,list):
        for x in v:yield from refs(x)
def ensure(packages,label):
    need=[]
    for p in sorted(set(packages)):
        target=META/(p+'.json');previous=OLD/'Metadata'/(p+'.json')
        if not target.exists() and previous.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(previous,target)
        if not target.exists():need.append(p)
    if need:
        request=ROOT/('Request_'+label+'.json');write(request,need)
        with (ROOT/('Metadata_'+label+'.log')).open('w',encoding='utf-8') as log:
            subprocess.run([str(DOTNET),str(DLL),'metadata',str(META),str(request)],stdout=log,stderr=subprocess.STDOUT,check=True)
        failures=[p for p in need if not (META/(p+'.json')).exists()]
        if failures:raise RuntimeError('Missing metadata '+str(failures))
    return {p:read(META/(p+'.json')) for p in sorted(set(packages))}
def main():
    cbs=ensure(read(ROOT/'HumanCBRequests.json'),'human_cbs')
    roots=set();entries=[]
    for p,objs in cbs.items():
        row={'package':p,'meshes':[],'recipes':[],'profiles':[],'animation_blueprints':[],'weapon_slots':[]}
        for o in objs:
            pr=o.get('Properties',{})
            row['meshes'].extend(refs(pr.get('SkeletalMesh')))
            if o.get('Name','').startswith('Default__'):
                row['scale']=pr.get('Scale');row['profiles'].extend(refs(pr.get('AnimationProfiles')))
                row['animation_blueprints'].extend(refs(pr.get('AnimationBlueprint')))
                row['weapon_slots'].extend(refs(pr.get('DefaultDefaultWeaponSlots')))
            row['recipes'].extend(x for x in refs(pr.get('ComponentClass')) if '/RandomLookInfo/' in x)
        for k in ['meshes','recipes','profiles','animation_blueprints','weapon_slots']:row[k]=sorted(set(row[k]));roots.update(row[k])
        entries.append(row)
    ensure(roots,'human_visual_roots')
    write(ROOT/'HumanSourceInventory.json',entries)
    for r in entries:print(json.dumps(r,ensure_ascii=False))
if __name__=='__main__':main()
