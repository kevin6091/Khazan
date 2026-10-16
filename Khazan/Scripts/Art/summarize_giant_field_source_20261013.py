"""Small source-property report for the two recovered field systems."""
from pathlib import Path
import json
main=Path(__file__).resolve().parents[2]
root=main/'Metadata/GiantVFX_20261013/ObjectOriginal/Extracted/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Monster/Boss_Yetuga'
def compact(v):
    if isinstance(v,list):return [compact(x) for x in v[:6]]+(['remaining '+str(len(v)-6)] if len(v)>6 else [])
    if isinstance(v,dict):return {k:compact(x) for k,x in v.items()}
    return v
report=[]
for file in root.glob('*.json'):
    data=json.loads(file.read_text(encoding='utf-8-sig'))
    def obj(ref):return data[int(ref['ObjectPath'].rsplit('.',1)[1])]
    for emitter in [x for x in data if x['Type']=='ParticleSpriteEmitter']:
        lod=obj(emitter['Properties']['LODLevels'][0]);p=lod['Properties']
        if p.get('bEnabled',True) is False:continue
        entry={'package':file.stem,'emitter':emitter['Name'],'lod':lod['Name'],'modules':[]}
        for ref in [p.get('TypeDataModule'),p.get('RequiredModule'),p.get('SpawnModule')]+p.get('Modules',[]):
            if not ref:continue
            mod=obj(ref)
            if mod['Type'] in ['ParticleModuleColorOverLife','ParticleModuleColorScaleOverLife','ParticleModuleParameterDynamic','ParticleModuleVelocity','ParticleModuleSize','ParticleModuleSizeMultiplyLife','ParticleModuleLifetime','ParticleModuleLocation','ParticleModuleSpawn','ParticleModuleTypeDataMesh']:
                entry['modules'].append({'type':mod['Type'],'name':mod['Name'],'properties':compact(mod.get('Properties',{}))})
        report.append(entry)
target=main/'Metadata/GiantVFX_20261013/FieldSourceSummary.json';target.write_text(json.dumps(report,indent=2),encoding='utf-8')
for r in report:
    print(r['package'],r['emitter'])
    for m in r['modules']:
        if m['type'] in ['ParticleModuleLocation','ParticleModuleSize','ParticleModuleLifetime','ParticleModuleTypeDataMesh','ParticleModuleSpawn']:print(m['type'],json.dumps(m['properties'],separators=(',',':'))[:550])
