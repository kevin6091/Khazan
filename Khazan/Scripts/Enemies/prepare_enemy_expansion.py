"""Targeted V2 source closure: selected human CBs, visual recipes and animations.

Preserves source paths and original metadata. No invented equipment or cross-
family animation assignments. Runtime gameplay code/VFX/audio are not imported.
"""
import pathlib,json,runpy,subprocess,shutil,collections
D=runpy.run_path(str(pathlib.Path(__file__).with_name('discover_enemy_expansion.py')))
ROOT=D['ROOT']; OLD=D['OLD']; META=D['META']; read=D['read']; write=D['write']; refs=D['refs']; ensure=D['ensure']

def run(mode,output,packages,label):
    request=ROOT/('Request_'+label+'.json');write(request,sorted(packages))
    with (ROOT/(label+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([str(D['DOTNET']),str(D['DLL']),mode,str(output),str(request)],stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(label+' failed; inspect log/report')

def main():
    cbs=read(ROOT/'HumanCBRequests.json')
    magic='BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireMagic/Base_Setting/'
    cbs += [magic+'CB_EmpireMagic',magic+'CB_EmpireMagic_Hard']
    # All sequence assets within the selected six families, plus their named
    # animation clips and BlendSpaces. This is a targeted index, not a game scan.
    index=read(ROOT/'FamilyIndex/TargetedPackageIndex.json')
    animation_roots={p[:-7] for p in index if '/Animation/' in p}
    timing_roots={p[:-7] for p in index if '/Design/Monster/Human/Empire/' in p and p.rsplit('/',1)[-1].startswith(('AC_','BS_','AM_'))}
    pending=set(cbs)|animation_roots|timing_roots;visited=set();edges=[];export=set();excluded=set();types={};round_no=0;missing_sources=set()
    while pending:
        round_no+=1
        try:objects=ensure(pending,'expansion_closure_%02d'%round_no)
        except RuntimeError:
            failed=read(META/'MetadataExtractionReport.json')
            errors=[v for v in failed if v['status']=='failed']
            if not errors or any(v['error']!='Package is not in the mounted FModel snapshot' for v in errors):raise
            missing_sources.update(v['source'] for v in errors)
            objects={p:read(META/(p+'.json')) for p in pending if p not in missing_sources}
        next_pending=set()
        for p,objs in objects.items():
            visited.add(p);types[p]=sorted(set(o['Type'] for o in objs))
            for o in objs:
                t=o['Type'];pr=o.get('Properties',{})
                if t in {'SkeletalMesh','StaticMesh','Texture2D','AnimSequence'}:export.add(p)
                if t in {'Skeleton','PhysicsAsset','AnimBoneCompressionSettings','AnimCurveCompressionSettings'}:continue
                if t=='AnimSequence':
                    candidates=set(refs({k:v for k,v in pr.items() if k in ['Skeleton','BoneCompressionSettings','CurveCompressionSettings','AdditiveAnimRefPose','RefPoseSeq']}))
                elif t in {'SkeletalMesh','StaticMesh','Material','MaterialInstanceConstant','Texture2D','xxWeaponSlot','xxWeaponSlotInfoSkeletalMesh'} or '/RandomLookInfo/' in p or '/ColorInfo/' in p or '/BoneModInfo/' in p:
                    candidates=set(refs(o))
                elif '/Design/' in p:
                    # Follow source animation/action links, retaining the entire
                    # owning object's metadata (including all rates and events).
                    candidates={v for v in refs(o) if '/Art/Character/' in v or '/RandomLookInfo/' in v or
                                ('/Design/' in v and v.rsplit('/',1)[-1].startswith(('AC_','AM_','AP_','AB_','BS_','SI_','SB_','WS_','CB_')))}
                else:candidates=set()
                for v in candidates:
                    if v==p:continue
                    # Compiled control rig graphs remain referenced in source
                    # JSON; they must not recursively pull in preview characters.
                    if v.rsplit('/',1)[-1].startswith(('CR_','CF_')) or '/Facial/' in v or '/FX/' in v:
                        excluded.add(v);continue
                    edges.append({'source':p,'target':v,'owner_type':t})
                    if v not in visited and v not in pending and v not in missing_sources:next_pending.add(v)
        print('V2_CLOSURE',round_no,'visited',len(visited),'next',len(next_pending),flush=True)
        pending=next_pending
    write(ROOT/'SourceClosure.json',{'packages':sorted(visited),'exports':sorted(export),'dependencies':edges,'types':types,'external_graph_references':sorted(excluded),'missing':sorted(missing_sources)})
    # Reuse byte-identical previous exports; only export newly needed sources.
    new=[]
    for p in sorted(export):
        typ=types[p];suffix='.psa' if 'AnimSequence' in typ else '.png' if 'Texture2D' in typ else '.psk'
        target=ROOT/'Assets'/(p+suffix)
        if target.exists():continue
        prev=OLD/('Animation' if suffix=='.psa' else 'Assets')/(p+suffix)
        if not prev.exists():prev=OLD/'Assets'/(p+suffix)
        if prev.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            for f in prev.parent.glob(prev.stem+'*'):
                if f.is_file():shutil.copy2(f,target.parent/f.name)
        else:new.append(p)
    if new:run('export',ROOT/'Assets',new,'ArtAnimationExport')
    missing=[p for p in export if not any((ROOT/'Assets'/(p+s)).exists() for s in ['.psa','.psk','.pskx','.png'])]
    if missing:raise RuntimeError('Missing exports '+str(missing))
    write(ROOT/'ExpansionSummary.json',{'source_packages':len(visited),'exports':len(export),'new_exports':len(new),'types':dict(collections.Counter(t for p in export for t in types[p] if t in ['SkeletalMesh','StaticMesh','Texture2D','AnimSequence']))})
    print(read(ROOT/'ExpansionSummary.json'),flush=True)

if __name__=='__main__':main()
