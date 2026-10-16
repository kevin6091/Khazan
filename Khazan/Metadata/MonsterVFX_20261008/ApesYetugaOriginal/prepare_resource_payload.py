"""Import-ready original resource union; preserve existing and Human destinations."""
from pathlib import Path
from collections import Counter
import importlib.util
import hashlib
import json

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def main():
    spec=importlib.util.spec_from_file_location('human_payload',ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/prepare_human_payload.py')
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    h.OUT=OUT
    human={r['source_package']:r for r in h.read(ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/ImportReadyAssetManifest.json')}
    original=h.read(h.MANIFEST)
    reserved={r['destination'].lower():r['source_package'] for r in original+list(human.values()) if r.get('destination')}
    rows=[]
    for r in h.read(OUT/'ResourceClosure.json')['resources']:
        p=r['source_package']
        if p in human:
            row=dict(human[p],union_reused_human_manifest=True,
                requested_by_apes_yetuga_root=r['requested_directly_by_notify'])
            rows.append(row)
            continue
        assert r['source_file'],p
        file=ROOT/r['source_file'];data=h.read(file);name=p.rsplit('/',1)[-1]
        obj=next((o for o in data if o.get('Name')==name and not o.get('Outer')),None)
        obj=obj or next((o for o in data if not o.get('Outer')),data[-1])
        typ=obj['Type'];dest=r['native_destination']
        context=typ in ('SkeletalMesh','Skeleton','AnimSequence','PhysicsAsset','AnimBlueprintGeneratedClass','AnimBoneCompressionSettings','AnimCurveCompressionSettings','KawaiiPhysicsLimitsDataAsset')
        if not dest:
            folder={'Texture2D':'Shared/Textures/MonsterApesYetuga','TextureCube':'Shared/Textures/MonsterApesYetuga',
                'VolumeTexture':'Shared/Textures/MonsterApesYetuga','TextureLightProfile':'Shared/Textures/MonsterApesYetuga',
                'StaticMesh':'Shared/Meshes/MonsterApesYetuga','Material':'Shared/Materials/MonsterApesYetuga',
                'MaterialInstanceConstant':'Shared/Materials/MonsterApesYetuga','VectorFieldStatic':'Shared/VectorFields/MonsterApesYetuga',
                'ParticleSystem':'Monsters/ApesYetuga','NiagaraSystem':'Monsters/ApesYetuga'}.get(typ,'Shared/Data/MonsterApesYetuga')
            dest='/Game/_Art/Effects/'+folder+'/'+name
            if dest.lower() in reserved and reserved[dest.lower()]!=p:
                dest+='_'+hashlib.sha256(p.encode()).hexdigest()[:8]
            assert dest.lower() not in reserved or reserved[dest.lower()]==p
            reserved[dest.lower()]=p
        source_only='Actor body/animation/physics context: audit only, do not create or replace gameplay character assets.' if context else None
        if typ in ('NiagaraSystem','MaterialFunction'):
            source_only='Cooked graph unavailable; native adapter requires explicit evidence and source-only disclosure.'
        rows.append({'source_package':p,'source_type':typ,'name':name,'source_json':r['source_file'],
            'source_sha256':h.sha(file),'destination':dest,'source_root_export_index':data.index(obj),'source_root_export_name':obj['Name'],
            'is_requested_root':r['requested_directly_by_notify'],'reused_native':r['native_file_exists'],
            'existing_native_sha256':r['native_sha256'],'existing_native_file':r['native_file'],'source_only_reason':source_only,
            'audit_only_actor_context':context,'union_reused_human_manifest':False})
    delta=[r for r in rows if not r['reused_native'] and not r.get('union_reused_human_manifest') and not r.get('audit_only_actor_context')]
    payload=[r['source_package'] for r in delta if r['source_type'] in ('Texture2D','TextureCube','VolumeTexture','StaticMesh')]
    h.extract('raw',[r['source_package'] for r in delta],'OriginalRawDelta')
    h.extract('export',payload,'VisualPayloadDelta')
    for r in rows:
        if r.get('union_reused_human_manifest'):
            continue
        base=OUT/'Payload'/r['source_package']
        r['payload_files']=[{'file':h.relative(p),'sha256':h.sha(p),'bytes':p.stat().st_size}
            for p in base.parent.glob(base.name+'.*') if p.is_file()] if base.parent.exists() else []
        raw=OUT/'OriginalRaw'/r['source_package']
        r['raw_source_files']=[{'file':h.relative(p),'sha256':h.sha(p),'bytes':p.stat().st_size}
            for p in raw.parent.glob(raw.name+'.*') if p.is_file()] if raw.parent.exists() else []
        if r['source_package'] in payload:
            assert r['payload_files'],'Missing requested visual payload: '+r['source_package']
    h.write('ImportReadyAssetManifest.json',rows)
    h.write('ImportDeltaAssetManifest.json',[r for r in rows if not r['reused_native'] and not r.get('audit_only_actor_context')])
    result={'asset_rows':len(rows),'existing_native':sum(r['reused_native'] for r in rows),
        'reused_human_manifest_rows':sum(r.get('union_reused_human_manifest',False) for r in rows),
        'own_new_delta':len(delta),'own_new_delta_types':dict(Counter(r['source_type'] for r in delta)),
        'own_visual_payload_packages':len(payload),'actor_context_excluded':sum(r.get('audit_only_actor_context',False) for r in rows),
        'scope':'Owned metadata/raw/payload extraction only; no private Effects/native/editor/Content mutation'}
    h.write('ImportPreparationSummary.json',result)
    print(json.dumps(result))

if __name__=='__main__':
    main()
