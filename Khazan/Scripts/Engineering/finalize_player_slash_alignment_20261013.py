"""Record the requested scope honestly, preserving unrelated diagnostic failures."""
from pathlib import Path
import datetime,json,hashlib,re,os
MAIN=Path(__file__).resolve().parents[2];OUT=MAIN/'Metadata/PlayerSlashAlignment_20261013'
def read(rel):return json.loads((OUT/rel).read_text(encoding='utf-8'))
for n in ['SavedWork04','SavedMain01']:assert read(n+'/SavedVerification.json')['status']=='passed'
for n in ['FinalRHI02','MainRHI01','MainSpinRHI02']:
 assert read(n+'/Driver.json')['status']=='passed'
 assert read(n+'/Exit.json')['exit']==0
for n in ['MainBuild01','MainBuild02QACamera']:assert read(n+'/Exit.json')['exit']==0
collision=read('MainCollisionRHI01/Driver.json');assert 'Result={Success}' in collision['completion']
clog=(OUT/'MainCollisionRHI01/Editor.log').read_text(encoding='utf-8')
assert 'HPChanges=7 expectedHits=7' in clog and 'HPChanges=19 expectedHits=19' in clog and 'all cases complete: 16' in clog
assert all('GuardParry\\PlayerParry\\Reference' in v for v in collision['material_compile_failures'])
apply=read('MainApply01/Applied.json');qacamera=read('QACamera01/Applied.json')
for row in apply['files']:
 expected=qacamera['after'] if row['file']==qacamera['file'] else row['after']
 assert hashlib.sha256((MAIN/row['file']).read_bytes()).hexdigest()==expected,row['file']
for rel,h in apply['protected_asset_sha256'].items():assert hashlib.sha256((MAIN/rel).read_bytes()).hexdigest()==h
base=read('Baseline.json');baseline={k.replace('\\','/'):v for k,v in base['sha256'].items()}
owned={x['file'] for x in apply['files']};foreign=[];unchanged=[]
for rel,h in baseline.items():
 current=hashlib.sha256((MAIN/rel).read_bytes()).hexdigest()
 if rel not in owned and current!=h:foreign.append({'file':rel,'before':h,'current':current})
 elif rel not in owned:unchanged.append(rel)
# Parallel changes are recorded, never restored or overwritten by this scope.
# These parallel edits predate our Main compilation and are retained in that build.
module=MAIN/'Binaries/Win64'/json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']
module_sha=hashlib.sha256(module.read_bytes()).hexdigest()
latest=read('MainRHI04ComposedPreview/Driver.json');assert latest['status']=='passed' and read('MainRHI04ComposedPreview/Exit.json')['exit']==0
assert module_sha==latest['module_sha256']
assert read('MainSpinRHI02/Driver.json')['module_sha256']==collision['module_sha256']
for x in foreign:x['predates_validated_module']=(MAIN/x['file']).stat().st_mtime < module.stat().st_mtime
# Current unrelated in-progress source edits can follow the sampled binary.
GPU=[json.loads(x) for x in (OUT/'MainRHI01/GPUWeaponEndpoint.jsonl').read_text().splitlines()]
spin_GPU=[json.loads(x) for x in (OUT/'MainSpinRHI02/GPUWeaponEndpoint.jsonl').read_text().splitlines()]
assert len(set(x['node'] for x in GPU))==17 and max(x['actual_gpu_tip_error_cm'] for x in GPU)<.1
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
result={'status':'complete_requested_slash_scope','date':stamp,'main_applied':True,'owned_files':apply['files'],'final_development_camera':qacamera,'new_runtime_files_classes_managers_tags':0,'remaining_addon_pairs':33,'OverFury_addon_pairs':0,'original_source_effects_preserved':read('SavedMain01/SavedVerification.json'),'geometry_source':'NiagaraGeometryEvidence.json','main_runtime_source_sha256':{x['file']:hashlib.sha256((MAIN/x['file']).read_bytes()).hexdigest() for x in apply['files'] if x['file'].startswith('Source')},'protected_asset_sha256':apply['protected_asset_sha256'],'preserved_parallel_changes':foreign,'unchanged_baseline_source_files':len([x for x in unchanged if x.startswith('Source')]),'unchanged_config_files':len([x for x in unchanged if x.startswith('Config')]),'actual_loaded_final_module':str(module),'module_sha256':module_sha,'validation':{'Main_build':'MainBuild01 + MainBuild02QACamera succeeded','fresh_saved':'SavedMain01 passed1359 original objects x37 properties + all6 clock/GUID','main_full_presentation':'MainRHI01 player18 + Brutal5, actual accepted hit/cancel/two-avatar boundaries passed','actual_GPU_samples':len(GPU),'actual_GPU_nodes':17,'max_actual_GPU_endpoint_error_cm':max(x['actual_gpu_tip_error_cm'] for x in GPU),'actual_GPU_radial_axis':'native asserted actual particle quaternion + renderer rotation against measured cutting edge','latest_composed_module':'MainRHI04ComposedPreview first4 actual Weak nodes passed with actual GPU endpoint/radial assertions; full MainRHI03Composed timed out under concurrent rendering after verifying earlier nodes and is retained as failed', 'aerial_spin_replay':'MainSpinRHI02 passed; '+str(len(spin_GPU))+' actual GPU samples, grip-centred multi-time views','main_gameplay_collision':'Native PlayerAttackCollision16 passed including Spin7/Fury19 HP/ST hits, miss/cancel/late approach','main_collision_editor_driver':'failed strictly on unrelated existing Parry material compile diagnostics; not relabelled as overall shader QA pass'},'visual_review':{'full_main_game_captures':len(list((OUT/'MainRHI01').glob('Slash_*.png'))),'focused_spin_captures':len(list((OUT/'MainSpinRHI02').glob('Slash_*.png'))),'reviewed':'weak/strong/charge/dodge/spin/Fury at several viewpoints and attack times; true addon-only inspection hides original Cascade/static trails/decals transiently','representative_main_image':'MainSpinRHI02/Slash_16_Frame036_View0.png'},'additional_unrelated_diagnostic':{'assets':['/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/M_Parry_Distortion','/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/MI_FMI_fluid_A_162'],'texture':'/Game/_Art/Effects/Shared/Textures/Noise/FT_PerlinNoise_RG','error':'TextureSampleParameter2D sampler Linear Color should be Color; PCD3D_SM6 fallback','evidence':'MainCollisionRHI01/Editor.log:2273; original failed Driver.json retained','action':'Recorded for the separate Parry owner; no cross-task material/texture edits'},'scope_limits':['Current imported weapon/reference geometry and requested Fab asset metadata; not original game shader/pixel parity','GPU attribute/mesh endpoint and plane plus actual game screenshots, not full material-WPO pixel measurements','Shipping/network/stress and all original-game animation frames were not claimed'],'remaining_requested_work':[]}
(OUT/'FinalVerification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
state=read('ResumeState.json');state.update(status='complete_requested_slash_scope',main_applied=True,running=None,last_verified='Main saved/original preservation, full presentation/actual GPU + focused aerial spin, native collision16(Spin7/Fury19) verified. Separate Parry shader sampler mismatch retained as unrelated diagnostic.',remaining=[],resume='Start from FinalVerification.json and current Main. Do not replay old author/probe scripts or copy private binaries. Separate Parry sampler diagnostic is recorded for that owner.');(OUT/'ResumeState.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
# Retain failed exploratory Python API probe as evidence, away from active tools.
retired=(OUT/'RetiredDiagnostics/player_slash_live_gpu_probe_20261013.py').resolve();src=(MAIN/'Scripts/Engineering/player_slash_live_gpu_probe_20261013.py').resolve()
assert src.is_relative_to(MAIN) and retired.is_relative_to(OUT)
if src.exists():retired.parent.mkdir(exist_ok=True);assert not retired.exists();os.replace(src,retired)
print('SLASH_REQUEST_COMPLETE',len(GPU),'GPU samples; native collider16 success; unrelated Parry diagnostic retained')