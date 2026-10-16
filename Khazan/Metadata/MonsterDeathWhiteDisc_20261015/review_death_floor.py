"""Owned RHI playback and unsaved per-component floor-decal isolation."""
import ctypes
import hashlib
import json
import os
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = Path(os.environ['KZ_DEATH_DISC_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
AUDIT = json.loads((ROOT / 'Metadata/MonsterDeathWhiteDisc_20261015/SavedAudit.json').read_text())
assert AUDIT['status'] == 'passed'
rows = []
for index, clip in enumerate(AUDIT['clips']):
    name = '%02d_%s_%s' % (index, clip['family'], clip['asset'].rsplit('/', 1)[1])
    rows.append('\t'.join((name, clip['family'], 'animation', clip['asset'])))
(OUT / 'GiantReviewCases.tsv').write_text('\n'.join(rows) + '\n', encoding='utf-8')
os.environ['KZ_MONSTER_REPAIR_OUT'] = str(OUT)
TEST = 'Khazan.GiantVFX.ReviewPIE'
LOG = OUT / 'Editor.log'
ISOLATE = os.environ.get('KZ_DEATH_DISC_ISOLATE', '1') == '1'
u.load_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground', False)
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')

manifest = json.loads((ROOT / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
kernel.GetModuleHandleW.restype = ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint]
kernel.GetModuleFileNameW.restype = ctypes.c_uint
buffer = ctypes.create_unicode_buffer(32768)
handle = kernel.GetModuleHandleW(manifest['Modules']['Khazan'])
assert handle and kernel.GetModuleFileNameW(handle, buffer, len(buffer))
module = Path(buffer.value).resolve()
report = {'status': 'running', 'project': str(ROOT), 'actual_module': str(module),
          'module_sha256': hashlib.sha256(module.read_bytes()).hexdigest(),
          'saved_packages': 0, 'test': TEST, 'isolate': ISOLATE, 'death_clips': len(rows), 'decals': [], 'isolations': []}
BAD_MATERIALS = {
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/FMI_Decal_Deferred_D_02.FMI_Decal_Deferred_D_02',
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/MI_Decal_Deferred_D_00.MI_Decal_Deferred_D_00',
}
BAD_EVENTS = {event['event_id'] for clip in AUDIT['clips'] for event in clip['events'] if event['decal'] in BAD_MATERIALS}
EXPECTED_DECALS = {event['event_id'] for clip in AUDIT['clips'] for event in clip['events']
                   if event['decal'] and event['decal'] not in BAD_MATERIALS}
if not ISOLATE:
    authoring = json.loads((ROOT / 'Metadata/MonsterDeathWhiteDisc_20261015/Authoring.json').read_text())
    assert authoring['status'] == 'passed' and len(authoring['saved']) == 8
    for item in authoring['saved']:
        asset = u.load_asset(item['asset'])
        events = u.AnimationLibrary.get_animation_notify_events(asset)
        assert {'seconds': asset.get_play_length(), 'notify_events': [event.export_text() for event in events]} == item['snapshot']
        matches = []
        for event in events:
            state = event.get_editor_property('notify_state_class')
            if isinstance(state, u.KZAnimNotifyState_MonsterVisual):
                effect = state.get_editor_property('Effect')
                if effect and str(effect.get_editor_property('EventId')) == item['event_id']:
                    matches.append(effect)
        assert len(matches) == 1 and matches[0].get_editor_property('DecalMaterial') is None
    for clip in AUDIT['clips']:
        if clip['asset'] in authoring['unchanged']:
            file = ROOT / 'Content' / (clip['asset'].removeprefix('/Game/') + '.uasset')
            assert hashlib.sha256(file.read_bytes()).hexdigest() == clip['sha256']
    for family in AUDIT['families']:
        default = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/Bluprints/Monsters/BP_Monster_' + family['family']))
        for field, expected in (('HitBloodEffect', family['blood']), ('HitBloodDecalMaterial', family['blood_decal']), ('DeathAshEffect', family['ash'])):
            assert default.get_editor_property(field).get_path_name() == expected
    report['fresh_saved_asset_verification'] = {'cleared_bindings': 8, 'notify_layout_and_timing_unchanged': True,
                                                'other_death_packages_unchanged': 10, 'blood_and_ash_families_unchanged': 6}
START = time.monotonic()
started = requested = done = busy = False
seen = set()
pending = []
isolation = None
world = None


def material_path(component):
    material = component.get_decal_material()
    while isinstance(material, u.MaterialInstanceDynamic):
        material = material.get_editor_property('parent')
    return material.get_path_name() if material else None


def capture(name):
    file = OUT / (name + '.png')
    u.SystemLibrary.execute_console_command(world, 'Shot filename="' + str(file) + '" -nosuffix')
    return str(file)


def finish(error=None):
    global done
    if done:
        return
    done = True
    if world:
        u.GameplayStatics.set_game_paused(world, False)
    u.unregister_slate_post_tick_callback(CALLBACK)
    report['status'] = 'failed' if error else 'passed'
    if error:
        report['error'] = error
        u.log_error(error)
    (OUT / 'RuntimeReport.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.SystemLibrary.quit_editor()


def tick(delta):
    global started, requested, busy, world, isolation
    if busy or done:
        return
    busy = True
    try:
        wall = time.monotonic()
        if wall - START > 950:
            finish('Death floor playback watchdog')
            return
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if world:
            clock = u.GameplayStatics.get_time_seconds(world)
            for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
                for component in actor.get_components_by_class(u.DecalComponent):
                    tags = [str(tag) for tag in component.get_editor_property('component_tags')]
                    key = component.get_path_name()
                    if key in seen or 'KZCombatEffect' not in tags:
                        continue
                    seen.add(key)
                    record = {'component': key, 'owner': actor.get_path_name(), 'material': material_path(component),
                              'tags': tags, 'time': clock, 'location': str(component.get_world_location()),
                              'size': str(component.get_editor_property('decal_size'))}
                    report['decals'].append(record)
                    u.log('KZ_DEATH_FLOOR_DECAL ' + json.dumps(record))
                    if ISOLATE:
                        pending.append({'component': component, 'record': record, 'born': clock})
            if isolation:
                component = isolation['component']
                if not u.SystemLibrary.is_valid(component):
                    u.GameplayStatics.set_game_paused(world, False)
                    isolation = None
                elif wall >= isolation['at']:
                    stage = isolation['stage']
                    if stage == 0:
                        isolation['result']['before'] = capture('Isolation_%02d_Before' % isolation['index'])
                    elif stage == 1:
                        component.set_visibility(False, True)
                    elif stage == 2:
                        isolation['result']['after'] = capture('Isolation_%02d_After' % isolation['index'])
                    else:
                        u.GameplayStatics.set_game_paused(world, False)
                        report['isolations'].append(isolation['result'])
                        isolation = None
                    if isolation:
                        isolation['stage'] += 1
                        isolation['at'] = wall + 0.25
            if not isolation and pending:
                item = pending[0]
                if not u.SystemLibrary.is_valid(item['component']):
                    pending.pop(0)
                elif clock - item['born'] >= 0.3:
                    pending.pop(0)
                    u.GameplayStatics.set_game_paused(world, True)
                    isolation = dict(item, index=len(report['isolations']), stage=0, at=wall+0.25,
                                     result={'decal': item['record'], 'only_hidden_component': item['record']['component']})
        data = LOG.read_text(encoding='utf-8', errors='replace') if LOG.exists() else ''
        completed = [line for line in data.splitlines() if 'Test Completed' in line and ('Path={' + TEST + '}') in line]
        if completed:
            report['completion'] = completed[-1]
            report['material_compile_failures'] = [line for line in data.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
            assert 'Result={Success}' in completed[-1] and not report['material_compile_failures'], completed[-1]
            if not ISOLATE:
                observed_events = {tag for item in report['decals'] for tag in item['tags'] if tag.startswith('KZMVFX_')}
                assert not (observed_events & BAD_EVENTS), 'Suppressed death decal still spawned'
                assert not [item for item in report['decals'] if item['material'] in BAD_MATERIALS]
                assert observed_events == EXPECTED_DECALS, 'Legitimate remaining death decal did not replay'
                review = json.loads((OUT / 'GiantReview.json').read_text())
                assert review['passed']
                finished_cases = [item for item in review['cases'] if 'peak_components' in item]
                assert len(finished_cases) == 18
                report['runtime_verification'] = {'suppressed_white_decal_components': 0, 'legitimate_decal_events': sorted(observed_events),
                                                   'completed_death_clips': len(finished_cases)}
            finish()
            return
        if wall - START < 8:
            return
        if not started:
            started = True
            u.SystemLibrary.execute_console_command(None, 't.MaxFPS 60')
            u.SystemLibrary.execute_console_command(None, 'Automation RunTests ' + TEST)
        elif not requested and 'Test Started' in data and ('Path={' + TEST + '}') in data:
            requested = True
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    except Exception:
        finish(traceback.format_exc())
    finally:
        busy = False


CALLBACK = u.register_slate_post_tick_callback(tick)
