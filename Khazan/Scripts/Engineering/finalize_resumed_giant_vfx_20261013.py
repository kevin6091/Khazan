"""Complete only from saved preservation and actual, unsuppressed Main renders."""
from pathlib import Path
import datetime, hashlib, json

MAIN=Path(__file__).resolve().parents[2]
OUT=MAIN/'Metadata/GiantVFX_20261013'
def read(rel):return json.loads((OUT/rel).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

delivery=read('MainDelivery.json')
expected={r['relative']:r['after_sha256'] for r in delivery['files']}
for row in read('RefractionPlaneDelivery.json')+[read('GrabMeshUnitDelivery.json')]+read('SnowDecalDelivery01/Delivery.json')['files']:
    expected[row['relative']]=row['after_sha256']
slash=json.loads((MAIN/'Metadata/PlayerSlashAlignment_20261013/MainApply01/Applied.json').read_text(encoding='utf-8'))
notify='Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp'
expected[notify]=next(r['after'] for r in slash['files'] if r['file']==notify)
assert len(expected)==198
assert all(sha(MAIN/p)==h for p,h in expected.items())
saved=read('MainSavedSnowDecal01/Preservation.json')
assert saved['status']=='passed' and saved['sequence_count']==84
assert not saved['differences'] and not saved['null_render_bindings']
tests={}
for label in ['MainSnowDecalFinal01','MainArmageddonGASFinal01']:
    e=read(label+'/Exit.json');d=read(label+'/Driver.json')
    assert e['exit']==0 and e['input_unchanged'] and d['status']=='passed'
    assert not d['material_compile_failures']
    assert d['actual_loaded_module']==d['manifest_module']
    assert sha(Path(d['actual_loaded_module']))==d['module_sha256']
    tests[label]=d
assert len(list((OUT/'MainSnowDecalFinal01').glob('*.png')))==69
review=read('MainSnowDecalFinal01/GiantReview.json')['cases']
assert sum('age' in r for r in review)==69
assert len({r['name'] for r in review})==23
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
previous=read('FinalVerification.json')
archive=OUT/'FinalVerification_BeforeSnowDecalAcceptance.json'
if not archive.exists():archive.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=dict(previous)
report.update(completed=now,passed=True,technical_passed=True,main_applied=True,
              status='complete_current_implementation_and_review',visual_status='passed_current_unsuppressed_Main_sequential_review',
              new_assets=104,total_distinct_delivered_files=198,
              latest_actual_module_sha256=tests['MainSnowDecalFinal01']['module_sha256'],
              selected_target_sha256=expected,latest_saved_audit=saved,latest_tests=tests,
              preserved_parallel_source=read('PreservedParallelSourceResume.json'),
              visual_root_cause='One retained FMI_Decal_Deferred_D_02 projector from Attack_Armageddon_Start: in-memory shock-material suppression and all-PSC suppression left the white ground/body projection; decal-only suppression removed it. Source placeholder unlit emissive projection lacked spatial alpha support.',
              visual_fix=read('SnowDecalRepair02/SnowDecalRepair.json'),
              current_visual_evidence='MainSnowDecalFinal01/013_Attack_Armageddon_Jump_End_01.png and sequential23/69PNG; MainArmageddonGASFinal01 actual granted pattern and cancellation',
              source_writes_this_resume=0,shared_material_texture_writes_this_resume=0,
              remaining_required=[])
report['limits']=[v for v in report.get('limits',[]) if 'avoid the white FS_bill quad' not in v]
report['limits'].append('Original cooked distortion shader is unrecovered. Dedicated non-emissive frost mark preserves current source temporal alpha, colour, geometry, roughness and lifetime; opacity .12 and radial/FT_Dirt_Tex_01.R density are editable TEMP reconstruction. No claim of exact original pixels, Shipping performance or exhaustive gameplay-frame parity.')
report['evidence_contract']='Historical MainAll01 covers155cases; MainPatterns02 actual GAS8+objects3 and MainCollision01 cover preserved gameplay. Latest MainSavedSnowDecal01 strictly preserves84 sequences with only the explicit DecalMaterial remap normalized. Latest sequential23 and actual Armageddon GAS supersede the earlier white-plane visual failures. Current PlayerSlash source update is explicitly retained from its delivery receipt.'
(OUT/'FinalVerification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
state=read('ResumeState.json')
state.update(updated_at=now,status='complete_current_implementation_and_review',running=None,remaining=[],
             last_verified='FinalVerification.json:198 target hashes; original84 preservation; unsuppressed Main sequential23/69PNG and actual Armageddon GAS/cancel; PlayerSlash and other Main changes preserved.',
             resume='Completed. Read current Main and FinalVerification.json. Do not replay author/full delivery/root/FPS imports or copy private DLLs. Source cooked distortion/VAT and pixel parity limits remain documented.')
(OUT/'ResumeState.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('GIANT_VFX_RESUME_COMPLETE',len(expected),'targets; current Main visual acceptance23')
