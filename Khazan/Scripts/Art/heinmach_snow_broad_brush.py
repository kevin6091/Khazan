"""Scoped broad snow brush tuning; author only in the isolated background editor."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007'
MAP=Path('Content/Maps/L_HeinMach_Environment.umap')
SOURCES=[Path('Source/Khazan/Environment/KZSnowDeformation.h'),
         Path('Source/Khazan/Environment/KZSnowDeformation.cpp'),
         Path('Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')]
SETTINGS=dict(foot_radius_cm=[40.,32.],foot_contact_height_cm=20.,
              weapon_radius_cm=100.,weapon_contact_height_cm=24.)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    data['utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'Baseline.json').exists(),'Existing baseline preserved'
    files=[MAP,*SOURCES,Path('Binaries/Win64/UnrealEditor.modules')]
    hashes={str(p):sha(MAIN/p) for p in files}
    for p in files:
        destination=OUT/'Backup'/p;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(MAIN/p,destination)
    for p in (MAIN/'Saved/SnowQA').glob('*'):
        if p.is_file():
            (OUT/'Before').mkdir(exist_ok=True);shutil.copy2(p,OUT/'Before'/p.name)
    for name in ('MainVerification20261007.json','FinalVerification20261007.json'):
        p=MAIN/'Saved/ImportReports/HeinMachSnow_20261006'/name
        shutil.copy2(p,OUT/('Before_'+name))
    shutil.copy2(MAIN/MAP,STAGE/MAP)
    write('Baseline.json',dict(hashes=hashes,settings=SETTINGS,
        provenance='User requested much broader foot/weapon contact and meteor-like weapon holes; dimensions selected by assistant, not original metadata',
        map_sha256=hashes[str(MAP)]))
    print('BROAD_BRUSH_BASELINE_AND_PRIVATE_MAP_READY')

def author():
    import unreal
    assert Path(unreal.Paths.project_dir()).resolve()==STAGE
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    world=editor.get_editor_world()
    assert world.get_path_name().startswith('/Game/Maps/L_HeinMach_Environment.')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    def pose(a):
        p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
        return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
    poses={a.get_actor_label():pose(a) for a in actors}
    snow=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)]
    assert len(snow)==1 and len(actors)==9869
    a=snow[0];a.modify()
    for k,v in SETTINGS.items():
        a.set_editor_property(k,unreal.Vector2D(*v) if isinstance(v,list) else v)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/L_HeinMach_Environment')
    # Reload the exact private map and verify serialized settings, poses and preserved scene.
    unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    assert len(actors)==len(poses)
    assert all(max(abs(x-y) for x,y in zip(poses[a.get_actor_label()],pose(a)))<1e-6 for a in actors)
    snow=[a for a in actors if isinstance(a,unreal.KZSnowDeformation)][0]
    actual={}
    for k,v in SETTINGS.items():
        p=snow.get_editor_property(k);value=[p.x,p.y] if isinstance(v,list) else p
        assert value==v,(k,value,v);actual[k]=value
    parts=[c for a in actors for c in a.get_components_by_class(unreal.StaticMeshComponent)]
    assert sum(c.component_has_tag('HeinMachSnowSurface') for c in parts)==46
    assert sum(c.component_has_tag('HeinMachMicroDressing') for c in parts)==65
    assert len(snow.get_editor_property('merged_weapon_contacts'))==4
    fires=sum('KZHeinMachTutorialFire' in [str(t) for t in a.tags] for a in actors)
    assert fires==258
    write('SavedSettings.json',dict(success=True,actors=len(actors),poses_preserved=len(poses),
        snow_surfaces=46,micro_dressing=65,fire_actors=fires,settings=actual,map_sha256=sha(STAGE/MAP)))
    print('BROAD_BRUSH_SAVED_RELOAD_PASSED',json.dumps(actual))

def publish():
    baseline=json.loads((OUT/'Baseline.json').read_text())
    assert json.loads((OUT/'SavedSettings.json').read_text())['success']
    assert (OUT/'StagePIEPassed.json').is_file(),'Private native PIE must pass first'
    for p in [MAP,*SOURCES]:assert sha(MAIN/p)==baseline['hashes'][str(p)],str(p)
    # Runtime source must match the compiled stage; independent development tests stay untouched.
    differences=[]
    for p in (MAIN/'Source').rglob('*'):
        if not p.is_file() or p.relative_to(MAIN) in SOURCES:continue
        rel=p.relative_to(MAIN)
        if sha(p)!=sha(STAGE/rel):
            assert p.name=='KZMonsterAIPIETest.cpp',str(rel)
            differences.append(str(rel))
    normal=MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll';normal_sha=sha(normal)
    name='UnrealEditor-KhazanSnowBroad20261007.dll'
    dll=MAIN/'Binaries/Win64'/name
    assert not dll.exists(),'Do not replace a potentially loaded module'
    for p in SOURCES:
        temporary=(MAIN/p).with_suffix('.snowbroadtmp');shutil.copy2(STAGE/p,temporary);temporary.replace(MAIN/p)
    temporary=(MAIN/MAP).with_suffix('.snowbroadtmp');shutil.copy2(STAGE/MAP,temporary);temporary.replace(MAIN/MAP)
    shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll',dll)
    shutil.copy2(STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb',dll.with_suffix('.pdb'))
    manifest_path=MAIN/'Binaries/Win64/UnrealEditor.modules'
    manifest=json.loads(manifest_path.read_text());manifest['Modules']['Khazan']=name
    temporary=manifest_path.with_suffix('.snowbroadtmp')
    temporary.write_text(json.dumps(manifest,indent=2),encoding='utf-8');temporary.replace(manifest_path)
    assert sha(normal)==normal_sha
    write('Delivery.json',dict(success=True,settings=SETTINGS,map_sha256=sha(MAIN/MAP),
        source_sha256={str(p):sha(MAIN/p) for p in SOURCES},module=str(dll),module_sha256=sha(dll),
        normal_module_preserved_sha256=normal_sha,unrelated_development_test_differences=differences,
        restart_required_for_previously_running_editor=True))
    print('BROAD_BRUSH_MAIN_DELIVERED')

def stage_passed():
    log=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/verify.log'
    text=log.read_text(encoding='utf-8',errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in text
    assert 'Test Completed. Result={Fail}' not in text
    assert 'contactReachCm=20.000' in text
    ready=json.loads((STAGE/'Saved/SnowMailbox/Ready.json').read_text())
    assert ready['pid']==24332
    shutil.copy2(log,OUT/'StagePIE.log')
    for p in (STAGE/'Saved/SnowQA').glob('*'):
        if p.is_file():
            (OUT/'StagePreview').mkdir(exist_ok=True);shutil.copy2(p,OUT/'StagePreview'/p.name)
    write('StagePIEPassed.json',dict(success=True,pid=ready['pid'],log=str(OUT/'StagePIE.log'),
        settings=SETTINGS,compiled_module_sha256=sha(STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll')))
    print('BROAD_BRUSH_NATIVE_STAGE_SUCCESS_RECORDED')

def finalize():
    delivery=json.loads((OUT/'Delivery.json').read_text())
    native=json.loads((MAIN/'Saved/ImportReports/HeinMachSnow_20261006/MainVerification20261007.json').read_text())
    perf=json.loads((MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/Profile(20261007_152647)_SnowTick.json').read_text())
    assert delivery['success'] and native['success'] and native['pid']==28460
    assert native['snow_contact_settings']==SETTINGS
    assert sha(MAIN/MAP)==delivery['map_sha256']
    assert sha(Path(delivery['module']))==delivery['module_sha256']
    assert sha(MAIN/'Binaries/Win64/UnrealEditor-Khazan.dll')==delivery['normal_module_preserved_sha256']
    for p in SOURCES:assert sha(MAIN/p)==delivery['source_sha256'][str(p)]
    for name in ('main_verify.log','MainVerification20261007.json'):
        shutil.copy2(MAIN/'Saved/ImportReports/HeinMachSnow_20261006'/name,OUT/name)
    preview=OUT/'MainPreview';preview.mkdir(exist_ok=True)
    for p in (MAIN/'Saved/SnowQA').glob('*'):
        if p.is_file():shutil.copy2(p,preview/p.name)
    write('FinalVerification.json',dict(success=True,delivery=delivery,native=native,cpu_perf=perf,
        screenshots={p.name:sha(p) for p in preview.glob('*.png')},
        last_user_editor_observation=dict(pid=8292,world='/Game/Maps/DevMap.DevMap',game_world=None,
            dirty_content=['/Game/Data/ComboCommand/DA_Player_Combo_Definition'],dirty_maps=[],
            user_editor_saved_reloaded_or_closed=False),
        scope='Broader snow presentation contacts, same displacement depth/material/collision/nav/actor poses; assistant tuning for latest user look direction, not original parity'))
    marker='## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료'
    art='''
사용자 최신 요청의 방향은 정확한 신발 크기/위치를 복제하기보다 넓고 부드러운 눈 눌림, 무기는 운석 구멍 같은 큰 파임이다. 기존 원작 동일성 목표에서 이번 brush 크기만 사용자 룩 변경 요청을 우선했다. `/Game/Maps/L_HeinMach_Environment`의 HM_SnowDeformation을 조정했다. 발 반경17×9→40×32cm(기본 파임 지름80×64cm, 타원 면적 약8.37배), 무기 반경5→100cm(기본 지름2m, 원형 면적400배)다. 완만한 rim은 파임 경계 바깥까지 이어진다. 확대된 quintic 타원/원형 brush가 인접 발자국을 넓게 연결해 선명한 개별 신발 윤곽을 줄인다. 무기 이동 경로는 넓은 원형 눌림을 겹쳐 표현한다.

위 치수와 발 접촉 허용높이20cm/무기24cm는 요청한 방향을 위해 **어시스턴트가 선정한 임시 native tuning**이며 원작 메타데이터 직접값 또는 사용자가 숫자를 지정한 값이 아니다. 기존 깊이/압축 색·roughness/부드러운 rim의 material을 재사용했다. 기존 snow coefficient의 native15/7.5cm 해석 및 일반4cm는 유지했다. 원작 shader/pixel 동일 검증으로 표현하지 않는다.

private saved reload와 실제 main saved reload에4설정 값 일치, actor9,869/기존 source poses9,868/snow46/micro dressing65/fire258/merged weapon profile4를 검사했다. 기존 small-stone Pawn/nav 완화, Sky/PP/날리는 눈·횃불 배치와 사용자 PlayerParts/Monster 변경은 보존했다. 새 texture/material/mesh asset은0이며 기존 Actor 설정과 runtime writer만 보완했다.

실제 private Khazan.Snow.PIE Success06:15:07 UTC, main Success06:28:20 UTC/PID28460. main run411.51cm/압축2,267샘플, Dodge437.76cm/1,221샘플, 실제 Imperial_R 장비 ground1,023샘플. 날 접촉 위치에서(60,50)cm 떨어진 지점의 압축>0.1도 통과해 넓은 크레이터를 검사했다. 공중 무기 억제/4 Monster 이동·몸 접촉·합쳐진 장비/깊이14.5cm/render-collision<1cm/반복·창 이동 이력·EndPlay 복구는 통과했다. 몸/장비 pose fixture는 gameplay 넘어짐/공격 전체 montage 검증과 구분한다.

첫 자료 `Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007/{Baseline,SavedSettings,StagePIEPassed,Delivery,MainVerification20261007,FinalVerification}.json`, 실제 main 사진은 MainPreview의 PNG5다. Before/StagePreview도 보존했다. Before 사진 이후 PlayerParts/무기 등 독립 변경이 있어 이미지 차이 전체를 눈의 변화만으로 해석하지 않는다. 메인 mapSHAb9802151fccf3fd5d4c21073506014f7cba8d5d532be703d06b12c47d1b76b00. 새 native property를 포함한 별도 모듈이므로 실행 중인 user editor에는 저장 후 재시작이 필요하다. 사용자 DevMap/콤보 정의의 미저장 content1은 보존했다. 이후 크기는 같은 Actor의 FootRadiusCm/WeaponRadiusCm와 contact height 설정에서 조정한다. runtime 비용/수명은 Engineering 정본의 같은 후속 절에 분리한다.
'''
    engineering='''
기존 AKZSnowDeformation h/cpp와 development-only Snow PIE test만 보완했다. 새 runtime 파일/class/component0. FootRadiusCm40×32/FootContactHeightCm20/WeaponRadiusCm100cm, 새 WeaponContactHeightCm24cm다. 기존 WeaponRadiusCm가 brush radius와 trace reach를 동시에 소유하던 결합을 분리했다. 발과 무기의 눈 접촉 높이도 확대하면서 weapon brush100cm를 vertical trace reach100cm로 오해해 공중을 파는 문제를 방지한다. 모든 값은 이번 사용자 룩 요청에 따른 어시스턴트 임시값이며 원작 값이 아니다. 실제 캐릭터 capsule/무기 gameplay hit/damage collision에는 손대지 않았다.

큰 brush의 셀 수 증가에 대응해 기존 StampSnow를 tile 단위 loop로 보완: tile lookup/할당은 한 번, 내용이 달라진 tile만 dirty/upload. max 압축/quintic 경계/rim/고도 gate와 기존 cache 소유·EndPlay 계약을 유지한다. 접촉 경로 sample spacing=max(texel size, brush의 작은 반경×.25), weapon은 원형 반경×.25다. 따라서 현재 발8cm/무기25cm이며 C2 brush 중심의 겹침을 유지하는 기술 간격이다. .25는 원작 숫자가 아니다. Previous를 마지막 sampled contact 기준으로 누적해 느린 이동이 간격 미달로 계속 누락되지 않도록 했다. 원래 teleport256cm guard/공중 억제는 유지한다. 게임 스레드 finalized pose 관측과 기존 ASC/Ability/CMC/Animation 책임·cleanup도 그대로다.

ColdBuild_BroadBrush20261007/ColdBuild_BroadBrushQA20261007 모두 Succeeded. width 검사 추가 후 실제 다시 빌드했다. private contact PIE Success06:15:07 UTC, fresh main alias 모듈 실제 PIE Success06:28:20 UTC/PID28460. 기존 depth14.5cm/render-vs-collision<1cm/반복·cache·EndPlay, actual Player run/Dodge/Imperial_R ground-vs-air와4 Monster feet/body/merged equipment 및 새 blade 밖(60,50)cm 압축>0.1이 통과했다. 기존 map poses/collision/nav/material 보존,4serialized settings main readback 통과. global Nav/CMC/PlayerParts source를 바꾸지 않아 기존 경로 전수 검사를 근거 없이 반복하지 않았다.

CPU는 main Profile(20261007_152647).csv SnowTick active376samples 평균1.3528705/P95 3.5578/max14.1171ms. 큰 범위와 cold cache/동시 editor의 Development Editor 결과이며 이전 .9884ms와 조건이 달라 개선율/전체FPS로 읽지 않는다. private CSV151407은 SnowTick column이 없어 별도 비용 증거로 쓰지 않았다. cache/texture 예산48/32MiB는 유지한다. GPU·shippingFPS/연속 gameplay knockdown/원작 pixel parity 미검증도 유지한다.

Source3+map만 선택 전달, 기존 texture/mesh/material 신규0. 새 manifest-selected UnrealEditor-KhazanSnowBroad20261007.dll SHA3163ae8558af254eeb1d1b60035020c825a9861aab6791ed27bc7db30bd54817을 발행해 loaded normal DLL SHA516be188...57acab52를 보존했다. mapSHAb9802151...d1b76b00, 실제 Source SHA와 backup은 BroadBrush20261007/Delivery.json 및 Backup. user editor8292 DevMap/PIE없음/미저장 /Game/Data/ComboCommand/DA_Player_Combo_Definition 1개/map0를 read-only 확인했고 save/reload/close/PIE를 하지 않았다. 새 UPROPERTY layout은 실행 중인 모듈에 자동 반영되지 않으므로 user 저장·재시작이 필요하다. private24332와 background main28460는 정상 종료했다.

현재 최신 결과는 BroadBrush20261007/FinalVerification.json과 같은 폴더의 main_verify.log다. 이전 initial Delivery/FinalVerification map/moduleSHA는 당시 증거로 보존하며 현재 값을 대표하지 않는다. 초기 deliver/finalize/update_module helper를 그대로 반복하지 않는다. 후속 작업은 current main Source/map와 새 manifest 모듈에서 시작하고 current hash를 기준으로 선택 반영한다. 일반 DLL을 옛 SnowWork snapshot으로 교체하지 않으며, user dirty ComboDefinition/동시 PlayerParts 작업을 덮어쓰지 않는다.
'''
    status_art='''
최신 user 방향으로 눈 brush를 확대: 발40×32cm/무기100cm 반경, 둥근 눌림과 원형 크레이터다. assistant 임시 조정값이며 원작 값이 아니다. 현재 main map9,869poses/46surface/65micro/258fire 보존, main actual PIE06:28:20 UTC Success. 기존 material/48asset 재사용, 추가 asset0. 현재 결과는 HEINMACH_SNOW_DEFORMATION_2026-10-06.md의 후속 확대 절과 Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007/FinalVerification.json. 새 설정은 user editor 작업 저장 후 재시작으로 확인한다. 이전 작은 brush 값을 현행으로 해석하지 않는다.
'''
    status_engineering='''
Snow broad contact: 기존 owner h/cpp와 devtest만 수정, 새 runtime 타입0. foot40×32/reach20cm, weapon100/reach24cm 분리, tile lookup/dirty 최적화와 quarter-radius 누적 sampling. private build/PIE와 fresh main actual PIE06:28:20 UTC Success, actor poses/nav/collision 보존. CPU Development Editor 평균1.3529/P95 3.5578ms(376active), shipping/GPU cost 미검증. 새 aliasDLL/Source3/map selected delivery 완료; user8292의 미저장 ComboDefinition은 그대로며 새 UPROPERTY 사용에 저장·재시작 필요. 현재 SHA/범위는 HEINMACH_SNOW_IMPLEMENTATION_20261006.md 후속 확대 절/BroadBrush20261007/FinalVerification.json을 따른다.
'''
    continuity_art='''
확대 brush main 반영과 saved readback/actual PIE가 완료됐다. 발40×32cm/무기100cm 반경은 assistant 임시값, contact reach는20/24cm. mapSHAb9802151...d1b76b00, 새asset0/poses보존/PP·weather·fire·micro 충돌 변경 없음. latest Art 정본 후속 확대 절과 BroadBrush20261007/FinalVerification.json에서 재개. 초기작은 brush 기록은 이 후속 룩 지시가 대체한다. main 유저 dirty ComboDefinition1 보존, save/reload/quit 없음. 사용자 저장·재시작 후 /Game/Maps/L_HeinMach_Environment Play로 새 property/module을 확인한다. Source/module 절차는 Engineering continuity를 따른다.
'''
    continuity_engineering='''
이전 확대 진행 checkpoint의 main 미반영/QA pending은 해소됐다. Source3/map과 새 aliasDLL 선택 반영 완료, fresh main28460 actual contact PIE06:28:20 UTC Success/4설정readback/SHA passed. private24332/main28460 정상 종료. latest SHA는 BroadBrush20261007/Delivery.json, Backup/StagePIE/main_verify.log/FinalVerification.json. nativeSource09e7c3cb...e6b581b1, module3163ae85...bd54817, mapb9802151...d1b76b00. 일반 loaded DLL 보존, user8292 dirty ComboDefinition1은 건드리지 않았다. 새 class layout 확인에는 user 저장·재시작 필요. CPU active376평균1.3529/P95 3.5578ms, GPU/shipping 미검증.
현재 main을 기준으로 후속 설정만 바꾸고 초기 author/full-map/delivery/finalize helper를 재실행하지 않는다. 새로운 Source 변경은 최신 Source+Config를 private에 받아 current own hash backup→stage build→contact/범위/airnegative/saved settings QA→unique aliasDLL와 targetmap만 선택 전달→fresh background main QA. body/장비 fixture를 gameplay 넘어짐·공격 전체 검증으로 읽지 않는다. tagged PlayerPartsPIEEditor.cpp 및 PlayerParts source/dirty ComboDefinition은 이 작업 범위가 아니며 변경하지 않았다.
'''
    entries={
        'Docs/Art/HEINMACH_SNOW_DEFORMATION_2026-10-06.md':art,
        'Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md':engineering,
        'Docs/Art/ART_PROJECT_STATE.md':status_art,
        'Docs/Engineering/ENGINEERING_PROJECT_STATE.md':status_engineering,
        'Docs/Art/ART_WORK_CONTINUITY.md':continuity_art,
        'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md':continuity_engineering,
        'Docs/Art/ART_KNOWLEDGE_INDEX.md':'''\n最新 snow brush 크기는 HEINMACH_SNOW_DEFORMATION_2026-10-06.md의 후속 확대 절을 따른다. BroadBrush20261007/{Baseline,SavedSettings,StagePIEPassed,Delivery,FinalVerification}.json/main_verify.log/MainPreview가 current actor settings/source/module/map/실제 접촉·크레이터/PNG 증거다. 반경40×32/100cm와 contact20/24cm는 assistant 임시 tuning, 원작 source 계약은 기존 OriginalSnowContracts에서 읽는다. 초기 작은 brush map/module hash를 현재값으로 재사용하지 않는다.\n''',
    }
    for rel,body in entries.items():
        path=MAIN/rel
        if marker not in path.read_text(encoding='utf-8-sig'):
            with path.open('ab') as f:f.write(('\n\n'+marker+'\n'+body.rstrip()+'\n').encode('utf-8'))
    print('BROAD_BRUSH_FINAL_VERIFIED',len(entries),'documents appended')

if __name__=='__main__':{'prepare':prepare,'publish':publish,'stage_passed':stage_passed,'finalize':finalize}[sys.argv[1]]()
elif __name__=='snow_task':author()
