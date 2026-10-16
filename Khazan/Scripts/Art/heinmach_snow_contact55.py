"""User-specified 55/35/50 cm snow and bounded 8x5 cm foot disturbance."""
from pathlib import Path
import csv
import ctypes
import datetime
import importlib.util
import json
import re
import shutil
import statistics
import sys
import time

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
spec=importlib.util.spec_from_file_location('snow_deep',ROOT/'Scripts/Art/heinmach_snow_deep.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.OUT=d.BASE/'Contact55_20261007'
d.MATERIALS=list(d.DELIVERED_MATERIALS)
d.DELIVERED_MATERIALS=[p.with_name(p.stem.replace('_Deep20261007','_Contact55_20261007')+'.uasset') for p in d.MATERIALS]
d.SETTINGS=dict(foot_radius_cm=[8./1.4,5./1.4],foot_contact_height_cm=8.,
    foot_compression=35./55.,weapon_compression=50./55.,weapon_contact_height_cm=55.+24.)
d.HEIGHTS=dict(DeepSnow=55.,DeepSnow2=36.)
d.ALIAS='UnrealEditor-KhazanSnowContact55_20261007.dll'

FIELD_CODE='''
float2 windowUV = (World.xy-Transform.xy)/max(Transform.z,1.0);
float2 uv = frac(World.xy/max(Transform.z,1.0));
float4 field = Texture2DSampleLevel(Field,FieldSampler,uv,0);
float2 edge = min(windowUV,1.0-windowUV)*Transform.z/max(Transform.w,0.01);
float inside = saturate(min(edge.x,edge.y)/16.0);
inside = inside*inside*(3.0-2.0*inside);
float altitude = 1.0-smoothstep(HeightTolerance*0.75,HeightTolerance,abs(World.z-field.b));
float valid = field.a*inside*altitude;
float requestedDepth = DepthReferenceCm*saturate(field.r);
float depth = min(max(SnowHeight,0.0),requestedDepth)*valid;
float compression = depth/max(SnowHeight,0.00001);
float rim = saturate(field.g)*valid;
float capped = (SnowHeight>0.0 && requestedDepth>=SnowHeight) ? valid : 0.0;
return float4(SnowHeight-depth+RimHeight*rim*SnowMask,compression*SnowMask,rim*SnowMask,capped);
'''
NORMAL_CODE=d.NORMAL_CODE.replace('slope *= 1.0-saturate(FieldValue.y/max(SnowMask,0.00001));','slope *= 1.0-FieldValue.w;').replace(
    'float4 heights=(-SnowHeight*saturate(float4(xp.r,xm.r,yp.r,ym.r))+',
    'float4 heights=(-min(max(SnowHeight,0.0),DepthReferenceCm*saturate(float4(xp.r,xm.r,yp.r,ym.r)))+')

def prepare():
    d.prepare()
    d.write('RequestedContract.json',dict(source='Explicit user tuning, 2026-10-07',max_pile_cm=55.,
        foot_depth_cm=35.,weapon_depth_cm=50.,full_foot_envelope_semiaxes_cm=[8.,5.],
        foot_trace_reach_cm=8.,reference_cm=55.,thin_layer_rule='Clip depth at physical substrate',
        foot_fraction_calculation='35/55',weapon_fraction_calculation='50/55',
        brush_radius_calculation='Full envelope / existing 1.4 rim support',weapon_reach_calculation='55+existing 24 cm tolerance'))

def author():
    import unreal
    assert Path(unreal.Paths.project_dir()).resolve()==d.STAGE
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    lib=unreal.MaterialEditingLibrary;pairs={};rows=[];assets=[]
    for source_path,dest in zip(d.MATERIALS,d.DELIVERED_MATERIALS):
        path='/Game/'+dest.relative_to('Content').with_suffix('').as_posix()
        assert not (ROOT/dest).exists(),'Never replace a potentially loaded material'
        source=unreal.load_asset('/Game/'+source_path.relative_to('Content').with_suffix('').as_posix());assert source
        mat=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(dest.stem,path.rsplit('/',1)[0],source)
        assert mat;mat.modify()
        expressions=lib.get_material_expressions(mat)
        params={}
        for node in expressions:
            if not isinstance(node,unreal.MaterialExpressionScalarParameter):continue
            key=str(node.get_editor_property('parameter_name'))
            if key=='SnowHeightCm_DeepSnow':node.set_editor_property('default_value',55.)
            params[key]=node.get_editor_property('default_value')
        reference=next((n for n in expressions if isinstance(n,unreal.MaterialExpressionScalarParameter) and
            str(n.get_editor_property('parameter_name'))=='HM_DepthReferenceCm_User'),None)
        if not reference:reference=lib.create_material_expression(mat,unreal.MaterialExpressionScalarParameter)
        reference.set_editor_property('parameter_name','HM_DepthReferenceCm_User');reference.set_editor_property('default_value',55.)
        params['HM_DepthReferenceCm_User']=55.
        field=next(n for n in expressions if isinstance(n,unreal.MaterialExpressionCustom) and
            'float4 field = Texture2DSampleLevel' in n.get_editor_property('code'))
        normal=lib.get_material_property_input_node(mat,unreal.MaterialProperty.MP_NORMAL)
        for node in (field,normal):
            inputs=list(node.get_editor_property('inputs'))
            if 'DepthReferenceCm' not in [str(i.get_editor_property('input_name')) for i in inputs]:
                i=unreal.CustomInput();i.set_editor_property('input_name','DepthReferenceCm');inputs.append(i)
                node.set_editor_property('inputs',inputs)
            assert lib.connect_material_expressions(reference,'',node,'DepthReferenceCm')
        field.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT4)
        field.set_editor_property('code',FIELD_CODE);normal.set_editor_property('code',NORMAL_CODE)
        unreal.EditorAssetLibrary.set_metadata_tag(mat,'SnowDeformationVersion','4')
        unreal.EditorAssetLibrary.set_metadata_tag(mat,'SnowDepthProvenance','User-specified55cm pile/35cm foot/50cm weapon, 2026-10-07; fieldR normalized against55cm')
        errors=list(lib.recompile_material(mat));assert not errors,errors
        stats=lib.get_statistics(mat);assert stats.num_pixel_shader_instructions>0
        assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
        pairs[source.get_path_name()]=mat;assets.append(path)
        rows.append(dict(asset=path,parameters=params,compile_errors=errors,
            pixel_instructions=stats.num_pixel_shader_instructions,vertex_instructions=stats.num_vertex_shader_instructions))
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors();assert len(actors)==9869
    snow=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)];assert len(snow)==1
    snow[0].modify()
    for key,value in d.SETTINGS.items():snow[0].set_editor_property(key,unreal.Vector2D(*value) if isinstance(value,list) else value)
    changed=0
    for actor in actors:
        for c in actor.get_components_by_class(unreal.StaticMeshComponent):
            if not c.component_has_tag('HeinMachSnowSurface'):continue
            for slot in range(c.get_num_materials()):
                old=c.get_material(slot)
                if old and old.get_path_name() in pairs:c.modify();c.set_material(slot,pairs[old.get_path_name()]);changed+=1
    assert changed==46
    assert unreal.EditorLoadingAndSavingUtils.save_map(editor.get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors();assert len(actors)==9869
    snow=next(a for a in actors if isinstance(a,unreal.KZSnowDeformation))
    actual={}
    for key,value in d.SETTINGS.items():
        v=snow.get_editor_property(key);actual[key]=[v.x,v.y] if isinstance(value,list) else v
        assert all(abs(a-b)<1e-6 for a,b in zip(actual[key],value)) if isinstance(value,list) else abs(actual[key]-value)<1e-6
    count=sum(c.component_has_tag('HeinMachSnowSurface') and c.get_material(0).get_path_name().split('.')[0] in assets
        for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent));assert count==46
    d.write('SavedSettings.json',dict(success=True,settings=actual,material_assets=assets,materials=rows,actors=9869,snow_surfaces=46,
        asset_sha256={p.as_posix():d.sha(d.STAGE/p) for p in [d.MAP,*d.DELIVERED_MATERIALS]}))
    d.write('PreAliasSavedSettings.json',dict(asset_sha256={d.MAP.as_posix():json.loads((d.OUT/'Baseline.json').read_text())['hashes'][d.MAP.as_posix()]}))
    print('CONTACT55_SAVED_RELOAD_PASSED',json.dumps(actual))

def stage_passed():
    text=(d.BASE/'verify.log').read_text(encoding='utf-8',errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in text and 'Test Completed. Result={Fail}' not in text
    ready=json.loads((d.STAGE/'Saved/SnowMailbox/Ready.json').read_text());assert ready['pid']==int(sys.argv[2])
    shutil.copy2(d.BASE/'verify.log',d.OUT/'StagePIE.log')
    for p in (d.STAGE/'Saved/SnowQA').glob('*'):
        if p.is_file():(d.OUT/'StagePreview').mkdir(exist_ok=True);shutil.copy2(p,d.OUT/'StagePreview'/p.name)
    d.write('StagePIEPassed.json',dict(success=True,pid=ready['pid'],module_sha256=d.sha(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')))
    print('CONTACT55_STAGE_PASSED')

def publish():
    passed=json.loads((d.OUT/'StagePIEPassed.json').read_text())
    assert passed['success']
    assert d.sha(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')==passed['module_sha256'],'Rebuilt DLL requires fresh Stage PIE verification'
    d.publish()

PREVIEW_MAP=Path('Content/Maps/L_HeinMach_Environment_Contact55_20261007.umap')
PREVIEW_ASSET='/Game/Maps/L_HeinMach_Environment_Contact55_20261007'

def atomic_json(name,data):
    path=d.OUT/name;temporary=path.with_suffix('.snowcontacttmp')
    data.setdefault('utc',datetime.datetime.now(datetime.timezone.utc).isoformat())
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8');temporary.replace(path)

def process_alive(pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:return ctypes.get_last_error()!=87 # Access denied/unknown state stays protected.
    try:
        code=ctypes.c_uint32()
        return not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259
    finally:kernel.CloseHandle(handle)

def publish_unlocked():
    locked_pid=int(sys.argv[2]);assert locked_pid>0 and process_alive(locked_pid)
    baseline=json.loads((d.OUT/'Baseline.json').read_text());saved=json.loads((d.OUT/'SavedSettings.json').read_text())
    passed=json.loads((d.OUT/'StagePIEPassed.json').read_text())
    assert saved['success'] and passed['success']
    assert d.sha(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')==passed['module_sha256']
    assert d.sha(ROOT/d.MAP)==baseline['hashes'][d.MAP.as_posix()],'Canonical map changed; preserve user work'
    for path in d.SOURCES:assert d.sha(ROOT/path) in {baseline['hashes'][path.as_posix()],d.sha(d.STAGE/path)},str(path)
    for path in d.MATERIALS:assert d.sha(ROOT/path)==baseline['hashes'][path.as_posix()],str(path)
    differences=[p.relative_to(ROOT).as_posix() for p in (ROOT/'Source').rglob('*')
        if p.is_file() and p.relative_to(ROOT) not in d.SOURCES and
        (not (d.STAGE/p.relative_to(ROOT)).is_file() or d.sha(p)!=d.sha(d.STAGE/p.relative_to(ROOT)))]
    assert not differences,('Re-intake unrelated sources and rebuild before publishing',differences)
    assert json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text())['BuildId']==json.loads((d.STAGE/'Binaries/Win64/UnrealEditor.modules').read_text())['BuildId']
    assert (d.STAGE/PREVIEW_MAP).is_file(),'Save the isolated preview map before publication'
    dll=ROOT/'Binaries/Win64'/d.ALIAS;assert not dll.exists(),'Never replace a loaded alias'
    for path in [PREVIEW_MAP,*d.DELIVERED_MATERIALS]:assert not (ROOT/path).exists(),'Unique asset already exists: '+str(path)
    normal=ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll';normal_sha=d.sha(normal)
    pending=d.OUT/'PendingCanonical'/d.MAP.name;pending.parent.mkdir(exist_ok=True)
    shutil.copy2(d.STAGE/d.MAP,pending);pending_sha=d.sha(pending)
    assert pending_sha==d.sha(d.STAGE/d.MAP)
    for path in [*d.SOURCES,PREVIEW_MAP,*d.DELIVERED_MATERIALS]:
        temporary=(ROOT/path).with_suffix('.snowcontacttmp');shutil.copy2(d.STAGE/path,temporary);temporary.replace(ROOT/path)
    shutil.copy2(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll',dll)
    shutil.copy2(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb',dll.with_suffix('.pdb'))
    manifest_path=ROOT/'Binaries/Win64/UnrealEditor.modules';manifest=json.loads(manifest_path.read_text());manifest['Modules']['Khazan']=d.ALIAS
    temporary=manifest_path.with_suffix('.snowcontacttmp');temporary.write_text(json.dumps(manifest,indent=2),encoding='utf-8');temporary.replace(manifest_path)
    assert d.sha(normal)==normal_sha and d.sha(ROOT/d.MAP)==baseline['hashes'][d.MAP.as_posix()]
    atomic_json('Delivery.json',dict(success=True,settings=d.SETTINGS,
        hashes={p.as_posix():d.sha(ROOT/p) for p in [*d.SOURCES,PREVIEW_MAP,*d.DELIVERED_MATERIALS]},
        material_assets=saved['material_assets'],original_materials_preserved={p.as_posix():d.sha(ROOT/p) for p in d.MATERIALS},
        module=str(dll),module_sha256=d.sha(dll),normal_module_preserved_sha256=normal_sha,
        map_asset=PREVIEW_ASSET,preview_map_asset=PREVIEW_ASSET,canonical_map_asset='/Game/Maps/L_HeinMach_Environment',
        canonical_map=d.MAP.as_posix(),canonical_map_pending=True,canonical_baseline_sha256=baseline['hashes'][d.MAP.as_posix()],
        pending_canonical_path=str(pending),pending_canonical_sha256=pending_sha,
        locked_editor_pid=locked_pid,locked_editor_session=f'MainUserEditorPID{locked_pid}',restart_required_for_previously_running_editor=True))
    print('CONTACT55_PREVIEW_DELIVERED_CANONICAL_PENDING',PREVIEW_ASSET,locked_pid)

def update_fixture_module():
    delivery=json.loads((d.OUT/'Delivery.json').read_text());assert delivery['success']
    passed=json.loads((d.OUT/'StagePIEPassed.json').read_text());assert passed['success']
    assert d.sha(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')==passed['module_sha256']
    for path,value in delivery['hashes'].items():assert d.sha(ROOT/path)==value,path
    for path,value in delivery['original_materials_preserved'].items():assert d.sha(ROOT/path)==value,path
    assert d.sha(ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll')==delivery['normal_module_preserved_sha256']
    assert d.sha(Path(delivery['module']))==delivery['module_sha256']
    manifest_path=ROOT/'Binaries/Win64/UnrealEditor.modules';manifest=json.loads(manifest_path.read_text())
    assert manifest['Modules']['Khazan']==Path(delivery['module']).name
    assert manifest['BuildId']==json.loads((d.STAGE/'Binaries/Win64/UnrealEditor.modules').read_text())['BuildId']
    if 'canonical_baseline_sha256' in delivery:
        expected=delivery['canonical_baseline_sha256'] if delivery['canonical_map_pending'] else delivery['canonical_applied_sha256']
        assert d.sha(ROOT/d.MAP)==expected
        assert d.sha(Path(delivery['pending_canonical_path']))==delivery['pending_canonical_sha256']
    test=Path('Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')
    assert d.sha(ROOT/test)==delivery['hashes'][test.as_posix()]
    differences=[p.relative_to(ROOT).as_posix() for p in (ROOT/'Source').rglob('*')
        if p.is_file() and p.relative_to(ROOT)!=test and
        (not (d.STAGE/p.relative_to(ROOT)).is_file() or d.sha(p)!=d.sha(d.STAGE/p.relative_to(ROOT)))]
    assert not differences,('Only the test-owned fixture may change',differences)
    alias=ROOT/'Binaries/Win64/UnrealEditor-KhazanSnowContact55QA_20261007.dll'
    assert not alias.exists(),'Never overwrite an existing QA module'
    temporary=(ROOT/test).with_suffix('.snowcontacttmp');shutil.copy2(d.STAGE/test,temporary);temporary.replace(ROOT/test)
    shutil.copy2(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll',alias)
    shutil.copy2(d.STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb',alias.with_suffix('.pdb'))
    manifest['Modules']['Khazan']=alias.name;temporary=manifest_path.with_suffix('.snowcontacttmp')
    temporary.write_text(json.dumps(manifest,indent=2),encoding='utf-8');temporary.replace(manifest_path)
    assert d.sha(ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll')==delivery['normal_module_preserved_sha256']
    delivery['hashes'][test.as_posix()]=d.sha(ROOT/test)
    delivery.update(module=str(alias),module_sha256=d.sha(alias),
        fixture_revision_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),fixture_revision='Freeze only the lying-torso test pose')
    atomic_json('Delivery.json',delivery)
    print('CONTACT55_FIXTURE_MODULE_UPDATED',alias.name)

def apply_pending():
    delivery=json.loads((d.OUT/'Delivery.json').read_text());assert delivery['success']
    if not delivery.get('canonical_map_pending',False):return 'AlreadyApplied'
    def status(state,**extra):
        atomic_json('PendingApplyStatus.json',dict(state=state,canonical_map_pending=True,locked_editor_pid=delivery['locked_editor_pid'],**extra))
        return state
    if process_alive(delivery['locked_editor_pid']):return status('WaitingForUserEditorExit')
    target=(ROOT/delivery['canonical_map']).resolve();pending=Path(delivery['pending_canonical_path']).resolve()
    assert target== (ROOT/d.MAP).resolve() and pending.parent== (d.OUT/'PendingCanonical').resolve()
    expected=delivery['canonical_baseline_sha256'];actual=d.sha(target)
    if actual!=expected:return status('BlockedCanonicalChanged',expected_sha256=expected,actual_sha256=actual)
    assert d.sha(pending)==delivery['pending_canonical_sha256']
    temporary=target.with_suffix('.snowcontacttmp')
    try:
        shutil.copy2(pending,temporary)
        if d.sha(target)!=expected:return status('BlockedCanonicalChanged',expected_sha256=expected,actual_sha256=d.sha(target))
        temporary.replace(target)
    except PermissionError as error:return status('WaitingForCanonicalUnlock',error=str(error))
    applied_sha=d.sha(target);assert applied_sha==delivery['pending_canonical_sha256']
    delivery.update(canonical_map_pending=False,canonical_applied_sha256=applied_sha,
        canonical_applied_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),canonical_apply_evidence='Hash-verified pending authored map; no new canonical-map PIE')
    delivery['hashes'][delivery['canonical_map']]=applied_sha
    atomic_json('Delivery.json',delivery) # Preserve original delivery UTC for native freshness guard.
    atomic_json('PendingApplyStatus.json',dict(state='Applied',canonical_map_pending=False,canonical_map=delivery['canonical_map'],sha256=applied_sha))
    print('CONTACT55_CANONICAL_APPLIED',applied_sha)
    return 'Applied'

def wait_apply():
    while True:
        state=apply_pending()
        if state in ('Applied','AlreadyApplied'):
            try:
                finalize()
                spec=importlib.util.spec_from_file_location('contact55_docs',ROOT/'Scripts/Art/heinmach_snow_contact55_docs.py')
                docs=importlib.util.module_from_spec(spec);spec.loader.exec_module(docs);docs.main()
            except Exception as error:
                atomic_json('PendingApplyStatus.json',dict(state='AppliedVerificationPending',canonical_map_pending=False,error=str(error)))
                raise
            print('CONTACT55_PENDING_HANDOFF_COMPLETE');return
        if state=='BlockedCanonicalChanged':raise RuntimeError('User canonical map changed; preserved without replacement')
        time.sleep(3.)

def finalize():
    delivery=json.loads((d.OUT/'Delivery.json').read_text());main=json.loads((d.BASE/'MainVerification20261007.json').read_text())
    assert delivery['success'] and main['success'] and main['native_pie_passed'] and Path(main['module_path']).resolve()==Path(delivery['module']).resolve()
    verification_cutoff=delivery.get('fixture_revision_utc',delivery['utc'])
    assert datetime.datetime.fromisoformat(main['utc'])>datetime.datetime.fromisoformat(verification_cutoff),'Fresh main verification required after delivery/fixture revision'
    assert main.get('map_asset')==delivery.get('map_asset','/Game/Maps/L_HeinMach_Environment'),'Verify the delivered map in the fresh main process'
    assert json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text())['Modules']['Khazan']==Path(delivery['module']).name
    for key,expected in d.SETTINGS.items():
        actual=main['snow_depth_settings'][key]
        if isinstance(expected,(list,tuple)):
            assert len(actual)==len(expected) and all(abs(float(a)-float(b))<1e-6 for a,b in zip(actual,expected)),key
        else:assert abs(float(actual)-float(expected))<1e-6,key
    for p,h in delivery['hashes'].items():assert d.sha(ROOT/p)==h,p
    for p,h in delivery['original_materials_preserved'].items():assert d.sha(ROOT/p)==h,p
    assert d.sha(Path(delivery['module']))==delivery['module_sha256']
    assert d.sha(ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll')==delivery['normal_module_preserved_sha256']
    pending=delivery.get('canonical_map_pending',False)
    if 'canonical_baseline_sha256' in delivery:
        assert d.sha(ROOT/d.MAP)==(delivery['canonical_baseline_sha256'] if pending else delivery['canonical_applied_sha256'])
        assert d.sha(Path(delivery['pending_canonical_path']))==delivery['pending_canonical_sha256']
    log=(d.BASE/'main_verify.log').read_text(encoding='utf-8',errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in log and 'Test Completed. Result={Fail}' not in log
    foot=re.search(r'SnowFootGPU dentCm=([\d.]+)',log);weapon=re.search(r'SnowGPU before=[\d.]+ after=[\d.]+ dentCm=([\d.]+)',log);assert foot and weapon
    cutoff=datetime.datetime.fromisoformat(verification_cutoff).timestamp()
    captures=sorted((ROOT/'Saved/Profiling/CSV').glob('*.csv'),key=lambda p:p.stat().st_mtime,reverse=True)
    latest=None;perf=None
    for capture in captures:
        if capture.stat().st_mtime<cutoff:continue
        with capture.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);key=next((k for k in (reader.fieldnames or []) if k.endswith('/SnowTick')),None)
            if not key:continue
            values=[]
            for row in reader:
                try:v=float(row[key])
                except (ValueError,TypeError,KeyError):continue
                if v>0:values.append(v)
        if not values:continue
        values.sort();latest=capture
        perf=dict(csv=str(capture),column=key,active_samples=len(values),mean_ms=statistics.mean(values),p95_ms=values[int((len(values)-1)*.95)],max_ms=values[-1],
            scope='SnowTick CPU, background Development Editor, cold assets and concurrent editors; not shipping FPS or GPU cost')
        break
    assert latest and perf,'Actual post-delivery main SnowTick CSV required'
    shutil.copy2(latest,d.OUT/latest.name);shutil.copy2(d.BASE/'main_verify.log',d.OUT/'MainPIE.log')
    shutil.copy2(d.BASE/'MainVerification20261007.json',d.OUT/'MainVerification.json')
    for p in (ROOT/'Saved/SnowQA').glob('*'):
        if p.is_file():(d.OUT/'MainPreview').mkdir(exist_ok=True);shutil.copy2(p,d.OUT/'MainPreview'/p.name)
    d.write('FinalVerification.json',dict(success=not pending,preview_verified=True,canonical_map_pending=pending,
        status='PreviewVerifiedCanonicalPending' if pending else 'VerifiedAndCanonicalApplied',
        native_verified_map_asset=main.get('map_asset',delivery.get('preview_map_asset','/Game/Maps/L_HeinMach_Environment')),
        canonical_apply_evidence=delivery.get('canonical_apply_evidence'),main=main,foot_depth_cm=float(foot[1]),weapon_depth_cm=float(weapon[1]),performance=perf,
        contract=json.loads((d.OUT/'RequestedContract.json').read_text()),limits=['Depth clips to substrate on thin snow','GPU/shipping performance unmeasured','Actual airborne foot just above8cm not independently isolated']))
    print('CONTACT55_PREVIEW_VERIFIED_CANONICAL_PENDING' if pending else 'CONTACT55_FINAL_PASSED',json.dumps(dict(foot_cm=float(foot[1]),weapon_cm=float(weapon[1]),performance=perf)))

if __name__=='__main__':
    {'prepare':prepare,'author':author,'stage_passed':stage_passed,'publish':publish,'publish_unlocked':publish_unlocked,'update_fixture_module':update_fixture_module,
     'apply_pending':apply_pending,'wait_apply':wait_apply,'finalize':finalize}[sys.argv[1]]()
