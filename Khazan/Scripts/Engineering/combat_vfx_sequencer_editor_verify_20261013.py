"""Use the real editor/Sequencer; leave gameplay assets untouched in create mode."""
from pathlib import Path
import os, json, traceback, time
import unreal as u
import kz_combat_vfx_sequencer as tool

OUT = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
report = {'status': 'running', 'mode': os.environ.get('KZ_SEQ_MODE', 'create')}
def run_verification():
    try:
        sequence = tool.open_weak02()
        report['asset'] = sequence.get_path_name()
        report['manifest'] = tool._metadata(sequence)
        report['bindings'] = [{'name': str(b.get_display_name()), 'id': tool._guid(b),
                              'tracks': [t.get_class().get_name() for t in b.get_tracks()]} for b in sequence.get_bindings()]
        u.LevelSequenceEditorBlueprintLibrary.set_current_time(18)
        u.LevelSequenceEditorBlueprintLibrary.force_update()
        bodies = [b for b in sequence.get_bindings() if tool._guid(b) == report['manifest']['body_binding']]
        objects = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(bodies[0]))
        assert objects, 'Player preview did not spawn'
        actor = objects[0]
        report['parts'] = [{'name': c.get_name(), 'mesh': str(c.get_editor_property('SkeletalMeshAsset'))}
                           for c in actor.get_components_by_class(u.SkeletalMeshComponent)]
        base = actor.get_actor_location()
        camera = base + u.Vector(-480, 80, 320)
        u.EditorLevelLibrary.set_level_viewport_camera_info(camera, u.MathLibrary.find_look_at_rotation(camera, base))
        manifest, edits = tool.collect_edits(sequence)
        (OUT / 'Edits.json').write_text(json.dumps(edits, indent=2), encoding='utf-8')
        report['baked_effects'] = len(edits['effects'])
        report['baked_keys'] = {r['id']: len(r['keys']) for r in edits['effects']}
        assert edits['effects'] and all(any(abs(k['location'][a] - r['keys'][0]['location'][a]) > 0.1 for k in r['keys'] for a in range(3)) for r in edits['effects']), 'Imported trajectory did not animate'
        component_binding = next(b for b in sequence.get_bindings() if tool._guid(b.get_parent()) in report['manifest']['bindings'])
        def niagara_state():
            items = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(component_binding))
            return {'bound': len(items), 'active': bool(items and items[0].is_active()),
                    'visible': bool(items and items[0].is_visible())}
        report['niagara_after_collection'] = niagara_state()
        life = next(t for t in component_binding.get_tracks() if isinstance(t, u.MovieSceneNiagaraSystemTrack)).get_sections()[0]
        report['lifecycle'] = {'start': life.get_start_frame_seconds(), 'end': life.get_end_frame_seconds(),
                               'start_behavior': str(life.get_section_start_behavior()),
                               'evaluate_behavior': str(life.get_section_evaluate_behavior()),
                               'age_mode': str(life.get_age_update_mode())}
        report['seek_states'] = []
        for frame in [0, 10, 12, 14, 18, 24, 30, 40]:
            u.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)
            u.LevelSequenceEditorBlueprintLibrary.force_update()
            report['seek_states'].append({'frame': frame, **niagara_state()})
        u.LevelSequenceEditorBlueprintLibrary.set_current_time(18)
        u.LevelSequenceEditorBlueprintLibrary.force_update()
        report['niagara_after_reseek'] = niagara_state()
        items = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(component_binding))
        live_asset = items[0].get_asset()
        report['live_asset_before_manual'] = live_asset.get_path_name() if live_asset else None
        report['template_asset'] = next(b for b in sequence.get_bindings() if tool._guid(b) in report['manifest']['bindings']).get_object_template().get_editor_property('NiagaraComponent').get_asset().get_path_name()
        items[0].activate()
        report['niagara_after_manual_activate'] = niagara_state()
        items[0].set_asset(u.load_asset('/Game/VFX/01_ARPGEssentials/KZ_Slash'))
        items[0].activate()
        report['niagara_after_manual_asset'] = niagara_state()
        if report['mode'] == 'apply_probe':
            error = u.KZAnimNotify_CombatEffect.apply_sequencer_edits(u.load_asset(manifest['montage']), json.dumps(edits))
            assert not error, error
            report['applied_in_memory_only'] = True
        report['status'] = 'passed'
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        u.log_error(report['error'])
    (OUT / 'EditorVerification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


start = time.monotonic()
ran = False
busy = False
reseeking = False
delayed = False

def finish(delta):
    global ran, start, busy, reseeking, delayed
    if busy: return
    if not ran:
        if time.monotonic() - start < (45 if os.environ.get('KZ_SEQ_DEBUG_HOLD') == '1' else 8): return
        ran = True
        busy = True
        try:
            run_verification()
        finally:
            busy = False
            start = time.monotonic()
        return
    if not reseeking:
        if time.monotonic() - start < 4: return
        reseeking = True
        u.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
        u.LevelSequenceEditorBlueprintLibrary.force_update()
        u.LevelSequenceEditorBlueprintLibrary.set_current_time(20)
        u.LevelSequenceEditorBlueprintLibrary.force_update()
        sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        manifest = tool._metadata(sequence)
        body = next(b for b in sequence.get_bindings() if tool._guid(b) == manifest['body_binding'])
        actor = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(body))[0]
        base = actor.get_actor_location()
        camera = base + u.Vector(80, -480, 320)
        u.EditorLevelLibrary.set_level_viewport_camera_info(camera, u.MathLibrary.find_look_at_rotation(camera, base))
        start = time.monotonic()
        return
    if not delayed:
        if time.monotonic() - start < 1: return
        delayed = True
        sequence = u.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
        manifest = tool._metadata(sequence)
        component_binding = next(b for b in sequence.get_bindings() if tool._guid(b.get_parent()) in manifest['bindings'])
        items = u.LevelSequenceEditorBlueprintLibrary.get_bound_objects(sequence.get_binding_id(component_binding))
        report['delayed_after_compile'] = {'bound': len(items), 'active': bool(items and items[0].is_active()),
                                           'visible': bool(items and items[0].is_visible()),
                                           'desired_age': items[0].get_desired_age() if items else None,
                                           'age_mode': str(items[0].get_age_update_mode()) if items else None,
                                           'component_name': items[0].get_name() if items else None}
        u.AutomationLibrary.take_high_res_screenshot(1600, 900, str(OUT / 'EditorPreview.png'))
        (OUT / 'EditorVerification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        start = time.monotonic()
        return
    if time.monotonic() - start < 8: return
    u.unregister_slate_post_tick_callback(handle)
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    u.SystemLibrary.quit_editor()
handle = u.register_slate_post_tick_callback(finish)
