"""Targeted original HeinMach fire/component metadata and dependency preparation."""
from pathlib import Path
from collections import Counter
import json
import hashlib
import sys
import subprocess
import shutil
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'HeinMach'))
from audit_heinmach_root_template_coverage import PackageResolver, package_from_object_path, object_index, is_actor
from audit_heinmach_child_template_coverage import attachment_parent_chain, local_transform

ROOT = Path(__file__).resolve().parents[2]
EX = ROOT / 'Saved/Extracted/HeinMachTutorialFires_20261006'
META = ROOT / 'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
FM = Path('C:/Users/user/Desktop/카잔')
LEVELS = FM / 'Exports/BBQ/Content/_Kazan_/Level/HeinMach'
PLACEMENTS = ROOT / 'Content/_Art/Player/Environment/HeinMach/Metadata/HeinMach_EnvironmentPlacements.json'


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def provider(mode, packages, label, output=None):
    output = output or EX / 'Source'
    request = EX / (label + '_Requests.json')
    write(request, sorted(set(packages)))
    output.mkdir(parents=True, exist_ok=True)
    with (EX / (label + '.log')).open('w', encoding='utf-8') as log:
        p = subprocess.run([str(ROOT/'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.exe'),mode,str(output),str(request)],
                           stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert p.returncode == 0, label
    report = read(output / ('MetadataExtractionReport.json' if mode=='metadata' else 'ExportReport.json'))
    failures = [r for r in report if (r.get('status')!='ok' if mode=='metadata' else not r.get('Success'))]
    assert not failures, failures
    print(label,len(report),'failures',len(failures),flush=True)


def fire_name(value):
    return any(t in str(value).lower() for t in ('torch', 'bonfire', 'lightobj', 'fire', 'flame', 'brazier', 'lamp'))


def catalog():
    placements = read(PLACEMENTS)['placements']
    selected = [r for r in placements if fire_name(r['actor_name']) or fire_name(r['template_package'])]
    write(EX / 'FireActorCandidates.json', selected)
    print('Fire candidates', len(selected), dict(Counter(r['source_level'] for r in selected)))
    for r in selected:
        print(r['source_level'], r['source_object_index'], r['actor_name'], r['template_package'], r['transform']['location_cm'])
    # The level is cached already. Inspect only explicitly named fire blueprints
    # plus direct particle and light exports, rather than a fresh whole-game scan.
    rows = []
    for level in sorted({r['source_level'] for r in selected} | {'HeinMach_Light'}):
        p = LEVELS / (level + '.json')
        data = read(p)
        candidates = {r['source_object_index'] for r in selected if r['source_level'] == level}
        names = {data[i]['Name'] for i in candidates}
        for i, obj in enumerate(data):
            typ = obj['Type']
            if i in candidates or ('ParticleSystemComponent' in typ or 'NiagaraComponent' in typ or 'LightComponent' in typ) or (str(obj.get('Outer', {}).get('ObjectName', '')).split("'")[-2].split(':')[-1] in names if "'" in str(obj.get('Outer',{}).get('ObjectName','')) else False):
                rows.append({'level': level, 'index': i, 'export': obj})
    write(EX / 'LevelFireAndLightExports.json', rows)
    print('Component exports', len(rows), dict(Counter(r['export']['Type'] for r in rows)))


def inspect():
    rows = read(EX / 'FireActorCandidates.json')
    for level, index in [('HeinMach_SubLV02_Blizzard', 46), ('HeinMach_Spawn_Main01', 720), ('HeinMach_SubLV03_Cave', 1711)]:
        data = read(LEVELS / (level + '.json'))
        obj = data[index]
        print(level, index, json.dumps(obj.get('Properties',{}), ensure_ascii=False))
        for i, o in enumerate(data):
            if o.get('Outer', {}).get('ObjectPath') == 'BBQ/Content/_Kazan_/Level/HeinMach/' + level + '.' + str(index):
                if 'Light' in o['Type']:
                    print('  child', i, json.dumps(o.get('Properties',{}), ensure_ascii=False))
    packages = {r['template_package'] for r in rows if r['template_package']}
    for pkg in sorted(packages):
        file = FM / 'Exports' / (pkg + '.json')
        print('TEMPLATE', pkg, 'cached', file.is_file())
        if file.is_file():
            for i, o in enumerate(read(file)):
                if o['Name'].startswith('Default__'):
                    print(i, json.dumps(o.get('Properties',{}), ensure_ascii=False))


def components():
    resolver = PackageResolver(FM)
    candidates = [r for r in read(EX / 'FireActorCandidates.json') if not r['source_level'].startswith('HeinMach_Cine_')]
    result, spawners = [], []
    for row in candidates:
        package = row['source_package']
        data = resolver.load_package(package)
        actor = data[row['source_object_index']]
        if actor['Type'] == 'xxDestructiblePropSpawner':
            spawners.append({'placement': row, 'properties': actor.get('Properties',{})})
            continue
        root, _, _, ri = resolver.resolve_ref(actor.get('Properties',{}).get('RootComponent'), package, data)
        assert root and ri is not None, row
        for i, component in enumerate(data):
            if component.get('Outer',{}).get('ObjectPath') != package + '.' + str(row['source_object_index']):
                continue
            if not any(t in component['Type'] for t in ('ParticleSystemComponent','NiagaraComponent','PointLightComponent','SpotLightComponent','DecalComponent')):
                continue
            # Resolve property inheritance and retain exact origins per field.
            lineage, seen, merged, origins = [], set(), {}, {}
            obj, pkg, objs, ix = component, package, data, i
            while obj and (pkg,ix) not in seen:
                seen.add((pkg,ix));lineage.append({'package':pkg,'index':ix,'name':obj['Name']})
                for k,v in obj.get('Properties',{}).items():
                    if k not in merged:
                        merged[k] = v
                        origins[k] = {'file':str(resolver.paths.get(pkg) or LEVELS/(row['source_level']+'.json')),'index':ix,'field':'Properties.'+k}
                obj,pkg,objs,ix = resolver.resolve_ref(obj.get('Template'),pkg,objs)
            chain,error = attachment_parent_chain(resolver, component, i, root, ri, package, data)
            assert not error, (row['actor_name'],component['Name'],error)
            item = {'actor':row,'component_index':i,'component_name':component['Name'],'component_type':component['Type'],
                    'properties':merged,'property_origins':origins,'lineage':lineage,
                    'local_transform':local_transform(resolver,component,package,data),'parent_chain':chain}
            result.append(item)
    write(EX/'Components.json',result)
    write(EX/'DestructibleFireSpawners.json',spawners)
    print('Components',len(result),dict(Counter(r['component_type'] for r in result)))
    print('Source particle packages',sorted({r['properties'].get('Template',{}).get('ObjectPath','') for r in result if 'Particle' in r['component_type']}))
    print('Source Niagara packages',sorted({r['properties'].get('Asset',{}).get('ObjectPath','') for r in result if 'Niagara' in r['component_type']}))
    print('Cached inheritance packages',len(resolver.cache),'missing',[p for p,d in resolver.cache.items() if d is None])
    print('DESTRUCTIBLE classes',sorted({r['properties']['DestructiblePropBP']['ObjectPath'].split('.')[0] for r in spawners}))
    for r in result:
        if 'Light' in r['component_type'] and r['actor']['actor_name']=='WBP_CTR_Lamp_Metal_001_14':
            print('LIGHT',r['component_name'],{k:v for k,v in r['properties'].items() if k in ('Intensity','AttenuationRadius','bAffectsWorld','bUseInverseSquaredFalloff','LightColor','CastShadows')})


def extract_dynamic():
    rows = read(EX/'DestructibleFireSpawners.json')
    packages = {r['properties']['DestructiblePropBP']['ObjectPath'].split('.')[0] for r in rows}
    packages |= {r['properties']['Template']['ObjectPath'].split('.')[0] for r in read(EX/'Components.json') if 'Particle' in r['component_type']}
    packages |= {r['properties']['DecalMaterial']['ObjectPath'].split('.')[0] for r in read(EX/'Components.json') if 'Decal' in r['component_type'] and r['properties'].get('DecalMaterial')}
    provider('metadata',packages,'FireAndChaosRoots')
    for pkg in sorted(packages):
        if '/Chaos/' not in pkg: continue
        data=read(EX/'Source'/(pkg+'.json'))
        print('CHAOS',pkg)
        for i,o in enumerate(data):
            if o['Name'].startswith('Default__') or ('Component' in o['Type'] and 'Geometry' not in o['Type'] and 'Handler' not in o['Type']):
                props={k:v for k,v in o.get('Properties',{}).items() if k in ('LightIntensity','LightRadius','StaticMeshArray','Template','Intensity','AttenuationRadius','RelativeLocation','RelativeRotation','RelativeScale3D','bAutoActivate','bAffectsWorld')}
                print(i,o['Type'],o['Name'],'template',o.get('Template'),'super',o.get('SuperStruct'),json.dumps(props,ensure_ascii=False))


class FireResolver(PackageResolver):
    def load_package(self, package):
        if package in self.cache: return self.cache[package]
        path=EX/'Source'/(package+'.json')
        if path.is_file():
            self.cache[package]=read(path);self.paths[package]=str(path);return self.cache[package]
        data=super().load_package(package)
        if data is not None: return data
        provider('metadata',[package],'Inherited_'+package.split('/')[-1])
        self.cache[package]=read(path);self.paths[package]=str(path);return self.cache[package]


def effective(resolver,obj,pkg,data,ix):
    merged,origins,lineage,seen={},{},[],set()
    while obj and (pkg,ix) not in seen:
        seen.add((pkg,ix));lineage.append({'package':pkg,'index':ix,'name':obj['Name']})
        for k,v in obj.get('Properties',{}).items():
            if k not in merged:
                merged[k]=v;origins[k]={'file':resolver.paths[pkg],'index':ix,'field':'Properties.'+k}
        obj,pkg,data,ix=resolver.resolve_ref(obj.get('Template'),pkg,data)
    return merged,origins,lineage


def dynamic_components():
    resolver=FireResolver(FM)
    rows=read(EX/'DestructibleFireSpawners.json')
    components=read(EX/'Components.json');fixtures=[]
    for row in rows:
        pkg=row['properties']['DestructiblePropBP']['ObjectPath'].split('.')[0]
        data=resolver.load_package(pkg)
        cdo=next(o for o in data if o['Name'].startswith('Default__'))
        cp,co,cl=effective(resolver,cdo,pkg,data,data.index(cdo))
        level_pkg=row['placement']['source_package'];level=resolver.load_package(level_pkg)
        overrides={}
        for entry in row['properties'].get('EffectParamInfo',{}).get('ParameterMap',[]):
            o,p,ds,ix=resolver.resolve_ref(entry['Value'],level_pkg,level)
            overrides[entry['Key']]={'properties':o.get('Properties',{}),'origin':{'file':resolver.paths[p],'index':ix}}
        write(EX/'DynamicOverrideExample.json',overrides) if not fixtures else None
        mesh=cp['StaticMeshArray'][0]
        fixtures.append({'actor':row['placement'],'static_mesh':mesh,'cdo_properties':{k:v for k,v in cp.items() if k in ('LightIntensity','LightRadius','SecondLightIntensity','SecondLightRadius') or k.startswith(('Fire_','Ember_','Smoke_','CameraOffset'))},'cdo_origins':co,'effect_parameter_overrides':overrides})
        # Child BP component overrides and inherited SCS templates, leaf first.
        all_data=[]
        for entry in cl:
            ds=resolver.load_package(entry['package']);all_data.append((entry['package'],ds))
        available={}
        for p,ds in all_data:
            for ix,o in enumerate(ds):
                if o['Type'] in ('xxPointLightComponent','xxParticleSystemComponent','ParticleSystemComponent'):
                    name=o['Name'].removesuffix('_GEN_VARIABLE')
                    available.setdefault(name,(o,p,ds,ix))
        for name,(o,p,ds,ix) in available.items():
            props,origins,lineage=effective(resolver,o,p,ds,ix)
            if props.get('bAutoActivate') is False: continue  # extinguishing effect is event-only
            item={'actor':row['placement'],'component_index':ix,'component_package':p,'component_name':name,'component_type':o['Type'],
                  'properties':props,'property_origins':origins,'lineage':lineage,'local_transform':local_transform(resolver,o,p,ds),
                  'parent_chain':[],'dynamic_fixture':True,'fixture_index':len(fixtures)-1}
            components.append(item)
    write(EX/'Components.json',components)
    write(EX/'DynamicFixtures.json',fixtures)
    print('Total components',len(components),dict(Counter(r['component_type'] for r in components)),flush=True)
    print('Dynamic fixture meshes',sorted({r['static_mesh']['ObjectPath'].split('.')[0] for r in fixtures}))
    print('Particle roots',sorted({r['properties']['Template']['ObjectPath'].split('.')[0] for r in components if 'Particle' in r['component_type']}))
    print('Override example saved with exact Value and bIsDefaultValue fields')


def visual_refs(value):
    if isinstance(value,dict):
        if 'ObjectPath' in value and value.get('ObjectName','').startswith(('Material','Texture','StaticMesh','VectorField','Curve','ParticleSystem')):
            yield value['ObjectPath'].split('.')[0]
        for v in value.values():yield from visual_refs(v)
    elif isinstance(value,list):
        for v in value:yield from visual_refs(v)


def closure():
    components=read(EX/'Components.json')
    roots={r['properties']['Template']['ObjectPath'].split('.')[0] for r in components if 'Particle' in r['component_type']}
    roots |= {r['properties']['DecalMaterial']['ObjectPath'].split('.')[0] for r in components if 'Decal' in r['component_type'] and r['properties'].get('DecalMaterial')}
    roots |= {r['properties']['IESTexture']['ObjectPath'].split('.')[0] for r in components if 'Light' in r['component_type'] and r['properties'].get('IESTexture')}
    roots |= {r['static_mesh']['ObjectPath'].split('.')[0] for r in read(EX/'DynamicFixtures.json')}
    queue=set(roots);visited=set();wave=0
    while queue:
        batch=sorted(queue-visited)
        missing=[p for p in batch if not (EX/'Source'/(p+'.json')).is_file()]
        if missing:provider('metadata',missing,'VisualClosure_'+str(wave))
        nextq=set()
        for pkg in batch:
            data=read(EX/'Source'/(pkg+'.json'));visited.add(pkg)
            nextq |= set(visual_refs(data))-{pkg}
        queue=nextq-visited;wave+=1
    reuse={r['source_package']:r for r in read(ROOT/'Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json')}
    result=[]
    for pkg in sorted(visited):
        p=EX/'Source'/(pkg+'.json');data=read(p)
        obj=next((o for o in data if o['Name']==pkg.split('/')[-1]),data[-1]);typ=obj['Type'];name=pkg.split('/')[-1]
        folder='Particles' if typ=='ParticleSystem' else 'Textures' if 'Texture' in typ else 'Materials' if 'Material' in typ else 'Meshes' if typ=='StaticMesh' else 'Data'
        dest='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires/'+folder+'/'+name
        # Only identical source texture/data assets are shared. Task-owned fire
        # shader graphs and emitters allow corrections without changing combat FX.
        reused=typ in ('Texture2D','TextureCube','VectorFieldStatic','CurveFloat','MaterialParameterCollection') and pkg in reuse
        if reused:dest=reuse[pkg]['destination']
        result.append({'source_package':pkg,'source_type':typ,'name':name,'source_json':str(p.relative_to(ROOT)).replace('\\','/'),
                       'source_sha256':sha(p),'destination':dest,'reuse_existing':reused,'is_requested_root':pkg in roots})
    names=Counter(r['destination'].lower() for r in result)
    for r in result:
        if names[r['destination'].lower()]>1:
            r['destination'] += '_'+hashlib.sha256(r['source_package'].encode()).hexdigest()[:8]
    assert len({r['destination'].lower() for r in result})==len(result)
    write(META/'AssetManifest.json',result);write(EX/'AssetManifest.json',result)
    native=[r for r in result if not r['reuse_existing']]
    print('Closure',len(result),dict(Counter(r['source_type'] for r in result)),'reuse',len(result)-len(native),flush=True)
    provider('raw',[r['source_package'] for r in result],'OriginalFireRaw',EX/'OriginalRaw')
    provider('export',[r['source_package'] for r in native if r['source_type'] in ('Texture2D','TextureCube','StaticMesh','TextureLightProfile')],'FirePayload',EX/'Payload')
    shutil.copytree(EX/'Source',META/'Source',dirs_exist_ok=True)
    for n in ('Components.json','DynamicFixtures.json','DestructibleFireSpawners.json','FireActorCandidates.json'):
        shutil.copy2(EX/n,META/n)


def recipes():
    rows=read(META/'AssetManifest.json')
    for row in rows:
        if row['source_type']=='Material' and row['name']!='M_WorldProp':
            data=read(ROOT/row['source_json']);obj=next(o for o in data if o['Type']=='Material')
            cached=obj.get('CachedExpressionData',obj.get('Properties',{}).get('CachedExpressionData',{})).get('Parameters',{})
            params={v:dict(zip([p['Name'] for p in cached.get(e,{}).get('ParameterInfos',[])],cached.get(v,[]))) for e,v in [('RuntimeEntries','ScalarValues'),('RuntimeEntries[1]','VectorValues'),('RuntimeEntries[2]','TextureValues')]}
            print('MASTER',row['name'],params)
        elif row['source_type']=='MaterialInstanceConstant' and row['name'].startswith('FMI'):
            props=read(ROOT/row['source_json'])[-1].get('Properties',{})
            print('MI',row['name'],{k:{p['ParameterInfo']['Name']:p.get('ParameterValue',p.get('Value')) for p in props.get(k,[])} for k in ('ScalarParameterValues','VectorParameterValues','TextureParameterValues')})
        elif row['source_type']=='ParticleSystem':
            data=read(ROOT/row['source_json']);print('PARTICLE',row['name'])
            for o in data:
                if o['Type'] in ('ParticleModuleRequired','ParticleModuleSize','ParticleModuleColor','ParticleModuleSubUV','ParticleSpriteEmitter'):
                    print(o['Type'],o['Name'],{k:v for k,v in o.get('Properties',{}).items() if k in ('EmitterName','Material','SubImages_Horizontal','SubImages_Vertical','InterpolationMethod','EmitterLoops','StartSize','StartColor','bUseLocalSpace','SubImageIndex')})


def core_diagnosis():
    for row in read(EX/'AssetManifest.json'):
        if row['source_type']!='ParticleSystem':continue
        data=read(ROOT/row['source_json']);root=next(o for o in data if o['Type']=='ParticleSystem')
        print('SYSTEM',row['name'],root['Properties'])
        for e in data:
            if e.get('Properties',{}).get('EmitterName')!='core_fire':continue
            print('CORE',e)
            lod=data[object_index(e['Properties']['LODLevels'][0])];print('LOD',lod)
            queue=[object_index(r) for r in lod['Properties'].get('Modules',[])]
            queue += [object_index(lod['Properties'][k]) for k in ('RequiredModule','SpawnModule') if lod['Properties'].get(k)]
            seen=set()
            while queue:
                i=queue.pop(0)
                if i in seen:continue
                seen.add(i);obj=data[i];print('EXPORT',i,obj)
                def local_refs(v):
                    if isinstance(v,dict):
                        if v.get('ObjectPath','').split('.')[0]==row['source_package']:yield object_index(v)
                        for v2 in v.values():yield from local_refs(v2)
                    elif isinstance(v,list):
                        for v2 in v:yield from local_refs(v2)
                queue+=list(local_refs(obj.get('Properties',{})))


if __name__ == '__main__':
    if 'core' in sys.argv: core_diagnosis()
    elif 'recipes' in sys.argv: recipes()
    elif 'closure' in sys.argv: closure()
    elif 'dynamic_components' in sys.argv: dynamic_components()
    elif 'dynamic' in sys.argv: extract_dynamic()
    elif 'components' in sys.argv: components()
    elif 'inspect' in sys.argv: inspect()
    else: catalog()
