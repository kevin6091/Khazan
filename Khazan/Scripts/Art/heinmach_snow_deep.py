"""Scoped deeper snow authoring; reversible backups, private editor, guarded delivery."""
from pathlib import Path
import datetime
import csv
import hashlib
import json
import re
import shutil
import statistics
import sys

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
BASE=MAIN/'Saved/ImportReports/HeinMachSnow_20261006'
OUT=BASE/'DeepSnow20261007'
MAP=Path('Content/Maps/L_HeinMach_Environment.umap')
SOURCES=[Path('Source/Khazan/Environment/KZSnowDeformation.h'),
         Path('Source/Khazan/Environment/KZSnowDeformation.cpp'),
         Path('Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')]
MATERIALS=[Path('Content/_Art/Player/Environment/Rendering/HeinMachSnow/Materials/M_HM_Deformable_'+g+'.uasset')
           for g in ('Landscape1','Landscape2')]
DELIVERED_MATERIALS=[p.with_name(p.stem+'_Deep20261007.uasset') for p in MATERIALS]
# Max pile 60 cm + existing substrate contact tolerance 24 cm, for this level only.
SETTINGS=dict(foot_compression=0.7,weapon_contact_height_cm=84.)
# Assistant-selected temporary centimetres, deliberately thicker per the user request.
HEIGHTS=dict(DeepSnow=60.,DeepSnow2=36.)
OTHER_HEIGHT=18.
RIM_HEIGHT=12.
BOUND_CM=75.
ALIAS='UnrealEditor-KhazanSnowDeep20261007.dll'

# Pixel normal only: central differences over two field texels soften bilinear
# derivative steps in deep walls, without increasing the CPU field resolution.
NORMAL_CODE='''
float3 dx=ddx(World), dy=ddy(World);
float determinant=dx.x*dy.y-dx.y*dy.x;
float2 slope=0.0;
if (abs(determinant)>0.00001)
    slope=float2(ddx(SnowHeight)*dy.y-ddy(SnowHeight)*dx.y,
                 ddy(SnowHeight)*dx.x-ddx(SnowHeight)*dy.x)/determinant;
slope *= 1.0-saturate(FieldValue.y/max(SnowMask,0.00001));
if (FieldValue.y+FieldValue.z>0.0)
{
    float stepCm=max(Transform.w*2.0,0.01);
    float2 uv=frac(World.xy/max(Transform.z,1.0));
    float d=stepCm/max(Transform.z,1.0);
    float4 xp=Texture2DSampleLevel(Field,FieldSampler,uv+float2(d,0),0);
    float4 xm=Texture2DSampleLevel(Field,FieldSampler,uv-float2(d,0),0);
    float4 yp=Texture2DSampleLevel(Field,FieldSampler,uv+float2(0,d),0);
    float4 ym=Texture2DSampleLevel(Field,FieldSampler,uv-float2(0,d),0);
    float4 x=float4(World.x+stepCm,World.x-stepCm,World.x,World.x);
    float4 y=float4(World.y,World.y,World.y+stepCm,World.y-stepCm);
    float4 ex=min(x-Transform.x,Transform.x+Transform.z-x)/max(Transform.w,0.01);
    float4 ey=min(y-Transform.y,Transform.y+Transform.z-y)/max(Transform.w,0.01);
    float4 inside=saturate(min(ex,ey)/16.0);
    inside=inside*inside*(3.0-2.0*inside);
    float4 valid=float4(xp.a,xm.a,yp.a,ym.a)*inside*
        (1.0-smoothstep(HeightTolerance*0.75,HeightTolerance,
                       abs(World.z-float4(xp.b,xm.b,yp.b,ym.b))));
    float4 heights=(-SnowHeight*saturate(float4(xp.r,xm.r,yp.r,ym.r))+
                   RimHeight*SnowMask*saturate(float4(xp.g,xm.g,yp.g,ym.g)))*valid;
    slope+=float2(heights.x-heights.y,heights.z-heights.w)/(2.0*stepCm);
}
return normalize(BaseNormal+float3(-slope,0.0));
'''

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    data['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'Baseline.json').exists(),'Preserve the existing baseline'
    files=[MAP,*MATERIALS,*SOURCES,Path('Binaries/Win64/UnrealEditor.modules')]
    hashes={p.as_posix():sha(MAIN/p) for p in files}
    for p in files:
        dest=OUT/'Backup'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/p,dest)
    for p in (MAIN/'Saved/SnowQA').glob('*'):
        if p.is_file():
            (OUT/'Before').mkdir(exist_ok=True);shutil.copy2(p,OUT/'Before'/p.name)
    for name in ('MainVerification20261007.json','main_verify.log','verify.log'):
        if (BASE/name).exists():shutil.copy2(BASE/name,OUT/('Before_'+name))
    for p in [MAP,*MATERIALS]:shutil.copy2(MAIN/p,STAGE/p)
    write('Baseline.json',dict(hashes=hashes,settings=SETTINGS,height_cm=HEIGHTS,
        other_snow_height_cm=OTHER_HEIGHT,rim_height_cm=RIM_HEIGHT,bound_cm=BOUND_CM,
        provenance='Assistant temporary tuning requested by user; not verified original centimetres',
        normal_module_sha256=sha(MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll')))
    print('DEEP_SNOW_BASELINE_READY')

def author():
    import unreal
    assert Path(unreal.Paths.project_dir()).resolve()==STAGE
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    world=editor.get_editor_world()
    assert world.get_path_name().startswith('/Game/Maps/L_HeinMach_Environment.')
    lib=unreal.MaterialEditingLibrary
    results=[]
    for relative in MATERIALS:
        asset='/Game/'+relative.relative_to('Content').with_suffix('').as_posix()
        mat=unreal.load_asset(asset);assert mat
        mat.modify();params={}
        expressions=lib.get_material_expressions(mat)
        field=next(n for n in expressions if isinstance(n,unreal.MaterialExpressionCustom) and
            'float4 field = Texture2DSampleLevel' in n.get_editor_property('code'))
        normal=lib.get_material_property_input_node(mat,unreal.MaterialProperty.MP_NORMAL)
        assert isinstance(normal,unreal.MaterialExpressionCustom)
        field_nodes=dict(zip(lib.get_material_expression_input_names(field),lib.get_inputs_for_material_expression(mat,field)))
        inputs=list(normal.get_editor_property('inputs'))
        existing={str(i.get_editor_property('input_name')) for i in inputs}
        for key in ('Transform','Field','SnowHeight','SnowMask','RimHeight','HeightTolerance','FieldValue'):
            if key not in existing:
                i=unreal.CustomInput();i.set_editor_property('input_name',unreal.Name(key));inputs.append(i)
        normal.set_editor_property('inputs',inputs)
        for key in ('Transform','Field','SnowHeight','SnowMask','RimHeight','HeightTolerance'):
            assert lib.connect_material_expressions(field_nodes[key],'RGBA' if key=='Transform' else '',normal,key)
        assert lib.connect_material_expressions(field,'',normal,'FieldValue')
        normal.set_editor_property('code',NORMAL_CODE)
        for node in expressions:
            if not isinstance(node,unreal.MaterialExpressionScalarParameter):continue
            key=str(node.get_editor_property('parameter_name'))
            if key.startswith('SnowHeightCm_'):
                value=HEIGHTS.get(key.removeprefix('SnowHeightCm_'),OTHER_HEIGHT)
            elif key=='SnowRimHeightCm_Temporary':value=RIM_HEIGHT
            else:continue
            node.set_editor_property('default_value',value);params[key]=value
        assert params.get('SnowHeightCm_DeepSnow')==60. and params.get('SnowRimHeightCm_Temporary')==12.
        divides=[n for n in expressions if isinstance(n,unreal.MaterialExpressionDivide) and n.get_editor_property('const_b') in (18.,BOUND_CM)]
        assert len(divides)==1
        divides[0].set_editor_property('const_b',BOUND_CM)
        scaling=mat.get_editor_property('displacement_scaling')
        scaling.set_editor_property('magnitude',BOUND_CM/100.);scaling.set_editor_property('center',0.)
        mat.set_editor_property('displacement_scaling',scaling)
        unreal.KZSnowDeformation.configure_material_displacement(mat,divides[0])
        unreal.EditorAssetLibrary.set_metadata_tag(mat,'SnowDeformationVersion','3')
        unreal.EditorAssetLibrary.set_metadata_tag(mat,'SnowDepthProvenance','Assistant temporary cm tuning: user requested thicker snow and deep craters, 2026-10-07')
        errors=list(lib.recompile_material(mat));assert not errors,errors
        assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
        stats=lib.get_statistics(mat)
        assert stats.num_pixel_shader_instructions>0,str(stats)
        task=unreal.AssetExportTask();task.object=mat;task.exporter=unreal.ObjectExporterT3D()
        task.filename=str(OUT/(mat.get_name()+'.t3d'));task.automated=True;task.prompt=False
        assert unreal.Exporter.run_asset_export_task(task)
        assert 'Displacement=(Expression=' in Path(task.filename).read_text(encoding='utf-8-sig')
        results.append(dict(asset=asset,parameters=params,displacement_magnitude=0.75,compile_errors=errors,
            pixel_instructions=stats.num_pixel_shader_instructions,vertex_instructions=stats.num_vertex_shader_instructions))
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    snow=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)]
    assert len(snow)==1 and len(actors)==9869
    snow[0].modify()
    for key,value in SETTINGS.items():snow[0].set_editor_property(key,value)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    assert len(actors)==9869
    snow=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)][0]
    assert all(abs(snow.get_editor_property(key)-value)<1e-6 for key,value in SETTINGS.items())
    write('SavedSettings.json',dict(success=True,actors=len(actors),settings=SETTINGS,materials=results,
        asset_sha256={p.as_posix():sha(STAGE/p) for p in [MAP,*MATERIALS]}))
    print('DEEP_SNOW_AUTHOR_AND_SAVE_PASSED',json.dumps(results))

def stage_passed():
    text=(BASE/'verify.log').read_text(encoding='utf-8',errors='replace')
    ready=json.loads((STAGE/'Saved/SnowMailbox/Ready.json').read_text())
    assert ready['pid']==int(sys.argv[2]),'Fresh owned process required'
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in text
    assert 'Test Completed. Result={Fail}' not in text
    assert 'SnowFootGPU dentCm=' in text and 'SnowGPU before=' in text
    shutil.copy2(BASE/'verify.log',OUT/'StagePIE.log')
    for p in (STAGE/'Saved/SnowQA').glob('*'):
        if p.is_file():
            (OUT/'StagePreview').mkdir(exist_ok=True);shutil.copy2(p,OUT/'StagePreview'/p.name)
    write('StagePIEPassed.json',dict(success=True,pid=ready['pid'],module_sha256=sha(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')))
    print('DEEP_SNOW_STAGE_PIE_PASSED')

def unlocked_variants():
    import unreal
    assert Path(unreal.Paths.project_dir()).resolve()==STAGE
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    saved=json.loads((OUT/'SavedSettings.json').read_text())
    if not (OUT/'PreAliasSavedSettings.json').exists():shutil.copy2(OUT/'SavedSettings.json',OUT/'PreAliasSavedSettings.json')
    pairs={};assets=[]
    for relative,destination,row in zip(MATERIALS,DELIVERED_MATERIALS,saved['materials']):
        source=unreal.load_asset('/Game/'+relative.relative_to('Content').with_suffix('').as_posix())
        asset='/Game/'+destination.relative_to('Content').with_suffix('').as_posix()
        assert not (MAIN/destination).exists(),'Never overwrite a live material'
        duplicate=unreal.load_asset(asset) if unreal.EditorAssetLibrary.does_asset_exist(asset) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(destination.stem,asset.rsplit('/',1)[0],source)
        assert duplicate
        errors=list(unreal.MaterialEditingLibrary.recompile_material(duplicate));assert not errors,errors
        assert unreal.EditorAssetLibrary.save_loaded_asset(duplicate,only_if_is_dirty=False)
        pairs[source.get_path_name()]=duplicate;row['asset']=asset;assets.append(asset)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    changed=0
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not component.component_has_tag('HeinMachSnowSurface'):continue
            for slot in range(component.get_num_materials()):
                material=component.get_material(slot)
                if material and material.get_path_name() in pairs:
                    component.modify();component.set_material(slot,pairs[material.get_path_name()]);changed+=1
    assert changed==46,changed
    assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    count=sum(c.component_has_tag('HeinMachSnowSurface') and c.get_material(0).get_path_name().split('.')[0] in assets
        for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent))
    assert count==46
    saved.update(material_assets=assets,live_original_materials_preserved=True,
        asset_sha256={p.as_posix():sha(STAGE/p) for p in [MAP,*DELIVERED_MATERIALS]})
    write('SavedSettings.json',saved)
    print('DEEP_SNOW_UNLOCKED_VARIANTS_SAVED',assets,changed)

def publish():
    baseline=json.loads((OUT/'Baseline.json').read_text())
    assert json.loads((OUT/'SavedSettings.json').read_text())['success']
    assert json.loads((OUT/'StagePIEPassed.json').read_text())['success']
    pre_alias=json.loads((OUT/'PreAliasSavedSettings.json').read_text())
    for p in [MAP,*SOURCES]:
        allowed={baseline['hashes'][p.as_posix()],sha(STAGE/p)}
        if p==MAP:allowed.add(pre_alias['asset_sha256'][p.as_posix()])
        assert sha(MAIN/p) in allowed,str(p)
    for p in MATERIALS:assert sha(MAIN/p)==baseline['hashes'][p.as_posix()],str(p)
    differences=[]
    for p in (MAIN/'Source').rglob('*'):
        if not p.is_file() or p.relative_to(MAIN) in SOURCES:continue
        rel=p.relative_to(MAIN)
        if not (STAGE/rel).is_file() or sha(p)!=sha(STAGE/rel):differences.append(rel.as_posix())
    assert not differences,('Re-intake current unrelated sources before building',differences)
    assert json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text())['BuildId']==json.loads((STAGE/'Binaries/Win64/UnrealEditor.modules').read_text())['BuildId']
    normal=MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll';normal_sha=sha(normal)
    dll=MAIN/'Binaries/Win64'/ALIAS;assert not dll.exists(),'Do not replace a loaded alias'
    for p in [*SOURCES,MAP,*DELIVERED_MATERIALS]:
        temp=(MAIN/p).with_suffix('.snowdeeptmp');shutil.copy2(STAGE/p,temp);temp.replace(MAIN/p)
    shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll',dll)
    shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb',dll.with_suffix('.pdb'))
    manifest_path=MAIN/'Binaries/Win64/UnrealEditor.modules'
    manifest=json.loads(manifest_path.read_text());manifest['Modules']['Khazan']=ALIAS
    temp=manifest_path.with_suffix('.snowdeeptmp')
    temp.write_text(json.dumps(manifest,indent=2),encoding='utf-8');temp.replace(manifest_path)
    assert sha(normal)==normal_sha
    write('Delivery.json',dict(success=True,settings=SETTINGS,
        hashes={p.as_posix():sha(MAIN/p) for p in [*SOURCES,MAP,*DELIVERED_MATERIALS]},
        material_assets=json.loads((OUT/'SavedSettings.json').read_text())['material_assets'],
        original_materials_preserved={p.as_posix():sha(MAIN/p) for p in MATERIALS},
        module=str(dll),module_sha256=sha(dll),normal_module_preserved_sha256=normal_sha,
        restart_required_for_previously_running_editor=True))
    print('DEEP_SNOW_MAIN_DELIVERED')

def finalize():
    delivery=json.loads((OUT/'Delivery.json').read_text())
    native=json.loads((BASE/'MainVerification20261007.json').read_text())
    assert delivery['success'] and native['success'] and native['native_pie_passed']
    assert Path(native['module_path']).resolve()==Path(delivery['module']).resolve()
    assert datetime.datetime.fromisoformat(native['utc'])>datetime.datetime.fromisoformat(delivery['utc'])
    assert all(abs(native['snow_depth_settings'][k]-v)<1e-6 for k,v in SETTINGS.items())
    for p,value in delivery['hashes'].items():assert sha(MAIN/p)==value,p
    for p,value in delivery['original_materials_preserved'].items():assert sha(MAIN/p)==value,p
    assert sha(Path(delivery['module']))==delivery['module_sha256']
    assert sha(MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll')==delivery['normal_module_preserved_sha256']
    assert json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text())['Modules']['Khazan']==ALIAS
    log=(BASE/'main_verify.log').read_text(encoding='utf-8',errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in log
    assert 'Test Completed. Result={Fail}' not in log
    gpu=re.search(r'SnowGPU before=([\d.]+) after=([\d.]+) dentCm=([\d.]+)',log)
    foot=re.search(r'SnowFootGPU dentCm=([\d.]+)',log);assert gpu and foot
    depth=dict(before_scene_depth_cm=float(gpu[1]),after_scene_depth_cm=float(gpu[2]),
        crater_depth_cm=float(gpu[3]),foot_depth_cm=float(foot[1]),
        condition='Actual GPU centre sample on exposed mixed source layers near (12000,13500,109.190) cm')
    cutoff=datetime.datetime.fromisoformat(delivery['utc']).timestamp()
    captures=sorted((MAIN/'Saved/Profiling/CSV').glob('*.csv'),key=lambda p:p.stat().st_mtime,reverse=True)
    perf=None
    for p in captures:
        if p.stat().st_mtime<cutoff:continue
        with p.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);key=next((k for k in reader.fieldnames if k.endswith('/SnowTick')),None)
            if not key:continue
            values=[]
            for row in reader:
                try:v=float(row[key])
                except (ValueError,TypeError,KeyError):continue
                if v>0:values.append(v)
        if not values:continue
        values.sort();perf=dict(csv=str(p),column=key,active_samples=len(values),mean_ms=statistics.mean(values),
            p95_ms=values[int((len(values)-1)*.95)],max_ms=values[-1],
            scope='SnowTick CPU, background Development Editor, cold assets and concurrent editors; not shipping FPS or GPU cost')
        shutil.copy2(p,OUT/p.name);break
    assert perf,'Actual main SnowTick CSV required'
    shutil.copy2(BASE/'MainVerification20261007.json',OUT/'MainVerification.json')
    shutil.copy2(BASE/'main_verify.log',OUT/'MainPIE.log')
    for p in (MAIN/'Saved/SnowQA').glob('*'):
        if p.is_file():
            (OUT/'MainPreview').mkdir(exist_ok=True);shutil.copy2(p,OUT/'MainPreview'/p.name)
    write('FinalVerification.json',dict(success=True,main=native,depth=depth,performance=perf,
        delivery_sha256=sha(OUT/'Delivery.json'),native_runtime_file_additions=0,
        limits=['Original pixel parity and shader units not established','Shipping GPU/FPS not benchmarked',
                'Weapon reach is a conservative substrate trace, not physical displaced-mesh collision']))
    title='\n\n## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료\n\n'
    art=f'''사용자 직접 요청으로 기존 snow graph를 활용한 material 복사본2개와 현재 HeinMach map의 설정을 선택 변경했다. DeepSnow15→60cm, DeepSnow2 7.5→36cm, 기타 snow4→18cm, rim2.5→12cm는 어시스턴트 임시 튜닝값이다. 원작 scalar의 shader 단위/최종 world displacement가 미확인이므로 이 높이를 원작 검증값으로 표현하지 않는다. 원본 metadata 경로·직접 scalar의 출처는 앞선 OriginalSnowContracts 절을 유지한다. 새 값의 출처는 이번 사용자 룩 요청에 맞춘 assistant 선택이다. 현재 조정 위치는 M_HM_Deformable_Landscape1_Deep20261007/2_Deep20261007의 SnowHeightCm_<layer>/SnowRimHeightCm_Temporary이며 source D/N/S/기존 weight/표면 배치는 유지한다.\n\n발은 FootCompression.7로 부분 압축하고 무기/몸은1로 바닥까지 압축한다. max accumulation으로 반복 접촉이 물리 바닥 아래를 파지 않는다. 깊은 layer의 이론 발42cm/무기60cm, rim 상한12cm이며 레이어 weight 때문에 위치별 실제 깊이는 달라진다. native displacement normalization75cm/magnitude.75/center0와 기존 terrain scale100을 함께 설정해 60+12cm를 bound 안에 넣었다. HeinMach 무기 contact reach84cm는 최대 snow60+기존 substrate tolerance24로 계산한 보수적 임시값이다. 발 radius40×32/무기 radius100cm와 foot reach20cm를 유지한다. 실제 GPU snow top collision이 아니며 얇은 layer에서도 공통 최대 reach를 사용한다.\n\n깊은 벽에서 2cm bilinear field의 미분이 각지게 보이는 것을 normal-only ±2texel 중앙차분(현재 ±4cm)으로 완화했다. 새로운 CPU texel/mesh/texture allocation은 없으며 수정 pixel에서 field4회 추가 sample, untouched pixel에서는 기존 source normal/weight height derivative를 사용한다. material RHI compile errors0, pixel instructions600/624/vertex148. Nanite mesh46의 precision/fallback/collision은 이번 변경0.\n\nFresh main PID{native['pid']} native actual contact PIE Success: GPU 발{depth['foot_depth_cm']:.3f}cm/크레이터{depth['crater_depth_cm']:.3f}cm, 바닥 render-vs-collision<1cm, 반복/이동창 이력/실제 Player run·Dodge/4 Monster 발·몸·합쳐진 무기/공중 억제/EndPlay passed. QA 좌표의 혼합 layer 때문에 첫 pure60cm 가정2항목 실패는 InitialMixedWeightQAFailure.log에 보존하고 실제 깊이×.7 비율 검사로 정정했다. 저장 scene9869/기존 poses9868/fire258/snow46/micro65와 source weapon profile4를 main readback 검사했다. native fixture는 모든 실제 공격 montage·knockdown 연출 검증이나 원작 pixel parity를 의미하지 않는다.\n\n첫 main 전달은 loaded material의 Windows file lock으로 Source3/map까지만 반영되고 material 단계가 실패했다. 잘못 이어 실행한 read-only verifier17840은 init assertion으로 진행하지 못해 normal close가 불가능했으며 해당 own process만 종료했다. user19684와 다른 작업 process는 조작하지 않았다. live RESETLOADERS/강제 package 해제 없이 private editor16088에서 Deep20261007 복사본2를 만들고46 surface 참조를 바꿨다. 이전 material2의 main SHA는 baseline 그대로다. 초기 전달/검증 실패는 IncompleteDeliveryStartupFailure.log/PreAliasSavedSettings.json에 남겼다. 새 main entry는 init exception에서도 own editor를 정상 종료하도록 보완했다.\n\n자료 정본은 Saved/ImportReports/HeinMachSnow_20261006/DeepSnow20261007/{{Baseline,SavedSettings,StagePIEPassed,Delivery,FinalVerification}}.json, StagePIE/MainPIE.log, MainPreview의 PNG6 및 RuntimeGeometry.json이다. 메인 Source3/map/new material2 선택 전달, 새 alias {ALIAS}; 일반 DLL은 전달 시 최신 hash {delivery['normal_module_preserved_sha256']} 그대로 보존했다. 사용자 에디터의 save/reload/PIE/camera/close를 실행하지 않았다. 새 native property는 기존 실행 중 에디터에 반영되지 않아 사용자가 작업을 저장하고 재시작해야 한다. 현재 값이 과하면 위 scalar/FootCompression/WeaponContactHeightCm에서 조정하고 같은 fixture와 실제 플레이 화면을 다시 검사한다.\n'''
    engineering=f'''기존 presentation owner AKZSnowDeformation h/cpp만 작은 수정: 조정 가능한 FootCompression.7을 추가하고 foot stamp에만 공급했다. body/weapon1, finalized pose GT/PostUpdateWork, contact/cache/tile upload/EndPlay 수명과 기존 ASC/Ability/CMC/AI 책임을 유지한다. 새 runtime 파일/class/manager0, KZComboActionAbility.cpp 수정0. 머테리얼·높이 provenance/normal smoothing은 Art 정본의 같은 후속 절에 분리했다.\n\nColdBuild_DeepSnow20261007(81.49s)/DeepSnowQA20261007(16.54s) Succeeded. development-only QA에 partial foot GPU readback과 authored fraction 검사를 추가했다. 테스트 좌표가 pure layer라고 가정해 실패한2검사 로그를 보존하고 mixed layer의 실제 full depth×FootCompression과 비교했다. scalar maximum bound·full crater>partial foot·compressed render agreement/반복·scroll 이력과 기존 actual Player/Monster/equipment/airborne/EndPlay 회귀를 검사했다. private 및 fresh main PID{native['pid']} 실제 PIE Success.\n\n메인 CPU CSV {Path(perf['csv']).name}: active{perf['active_samples']} 평균{perf['mean_ms']:.6f}/P95 {perf['p95_ms']:.6f}/max{perf['max_ms']:.6f}ms. cold asset/cache와 다른 editor 경쟁을 포함한 Development Editor SnowTick 측정이다. 이전 조건과 달라 개선율로 계산하지 않는다. CPU cache48MiB/GPU field32MiB/2cm·2048² 예산 유지. 추가 normal 샘플은 pixel shader에만 있으며 실제 GPU 전체 비용/shippingFPS는 미검증이다.\n\n현재 Source3/map/material2/module hash는 DeepSnow20261007/Delivery.json/FinalVerification.json과 Backup을 따른다. current unrelated Source를 compiled stage와 byte 비교한 후에만 선택 전달했고 normal DLL을 보존했다. 기존 사용자/독립 Monster·PlayerParts 작업을 old snapshot으로 되돌리지 않는다. 기존 running editor 새 layout에는 사용자 저장·재시작 필요. initial/broad helper의 strict old SHA를 현재값으로 재사용하지 않는다. 후속 수정은 최신 main Source intake(own3 수정은 별도 보존), native cold build, private actual RHI, guarded selected delivery, fresh main PIE 순이다.\n'''
    continuity='이번 checkpoint의 미반영/QA pending은 해소됐다. latest 자료와 source 계약은 해당 snow 정본의 “두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료” 절 및 DeepSnow20261007/FinalVerification.json을 따른다. own 검증 에디터는 정상 종료한다. 사용자 live save/reload/PIE/close는 실행하지 않는다. 실행 중인 editor에서 새 FootCompression 사용에는 사용자 저장·재시작이 필요하다. 후속 크기·높이 변경은 해당 material scalars/level Actor 설정에서 시작하고 original pixel parity/shippingGPU 완료로 확대하지 않는다.\n'
    notes={
        'Docs/Art/HEINMACH_SNOW_DEFORMATION_2026-10-06.md':art,
        'Docs/Art/ART_PROJECT_STATE.md':f'깊은 눈 후속 main 반영 완료. layer60/36/18cm, 발.7압축, rim12cm 및 normal 중앙차분. 실제 GPU 발{depth["foot_depth_cm"]}cm/무기{depth["crater_depth_cm"]}cm와 native contact PIE passed. 어시스턴트 임시값이며 원작 검증값이 아니다. 변경/범위/재시작/자료는 snow 정본 최신 절.\n',
        'Docs/Art/ART_WORK_CONTINUITY.md':continuity,
        'Docs/Art/ART_KNOWLEDGE_INDEX.md':'HeinMach snow 현재 높이·깊이/연락 범위·shader 정상성은 HEINMACH_SNOW_DEFORMATION_2026-10-06.md 최신 두꺼운 눈 절과 DeepSnow20261007의 SavedSettings/Delivery/FinalVerification 및 MainPreview를 따른다. 이전 broad 높이15cm/weapon reach24cm를 현재 HeinMach 값으로 재사용하지 않는다.\n',
        'Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md':engineering,
        'Docs/Engineering/ENGINEERING_PROJECT_STATE.md':f'Snow existing owner h/cpp에 FootCompression만 추가, 새 runtime 타입0. DeepSnow actual main PIE PID{native["pid"]} Success, CPU 평균{perf["mean_ms"]:.4f}/P95 {perf["p95_ms"]:.4f}ms(Development/cold). Source3/map/material2+unique alias selective delivery, normal DLL 보존. 새 property는 사용자 저장·재시작 필요. 현재 proof는 snow Engineering 정본 최신 절/DeepSnow20261007/FinalVerification.json.\n',
        'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md':continuity}
    assert not (OUT/'DocsAppended.json').exists(),'Do not append final notes twice'
    for relative,note in notes.items():
        with (MAIN/relative).open('a',encoding='utf-8') as f:f.write(title+note)
    write('DocsAppended.json',dict(success=True,documents=list(notes)))
    print('DEEP_SNOW_FINAL_VERIFICATION',json.dumps(dict(depth=depth,performance=perf),ensure_ascii=False))

if __name__=='__main__':
    {'prepare':prepare,'author':author,'unlocked_variants':unlocked_variants,'stage_passed':stage_passed,'publish':publish,'finalize':finalize}[sys.argv[1]]()
