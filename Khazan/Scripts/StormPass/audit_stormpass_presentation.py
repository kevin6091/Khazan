"""Read-only review audit, extending source placement checks with live state.

Run against the already-open map; this never opens DevMap or saves assets.
Review-policy differences are explicit and checked separately, not silently
ignored. The original reconstruction reports remain historical evidence.
"""
import collections
import os
import runpy

import unreal

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
core = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/restore_stormpass_surface_controls.py'))
route = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/restore_stormpass_route_presentation.py'))
read, write = core['read'], core['write']
REPORT = os.path.join(ROOT, 'Saved/ImportReports/StormPass_PresentationAudit_20260908.json')


def record_stage(name, value):
    report = read(REPORT) if os.path.isfile(REPORT) else {'stages': {}}
    report['stages'][name] = value
    report['failed_stages'] = [k for k, v in report['stages'].items() if v.get('failure_count', len(v.get('failures', [])))]
    write(REPORT, report)
    print('%s: failures=%s' % (name, value.get('failure_count', len(value.get('failures', [])))))
    return value


def geometry():
    legacy = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/audit_stormpass_final_reconstruction.py'))
    modules = {name: legacy['load_module']('sp_review_' + name, path) for name, path in legacy['MODULE_PATHS'].items()}
    actors = route['actors']()
    for name, module in [('root_props', None), ('child_props', 'child'), ('landscape', 'landscape'),
                         ('foliage', 'foliage'), ('lights', 'light'), ('fog', 'fog'), ('native_water', 'water')]:
        fn = legacy['audit_' + name]
        result = fn(actors) if module is None else fn(actors, modules[module])
        if name == 'landscape' and result['failure_count']:
            baseline = read(route['STATE'])
            current = read(os.path.join(core['META'], 'StormPass_CurrentReviewVariant.json'))['active_variant']
            inactive = {r['label'] for r in baseline['actors'] if r['variant'] != current}
            expected = [r for r in result['failures'] if r.get('label') in inactive and r.get('issues') == ['collision']]
            # Legacy reports truncate at 20. Only reconcile when the complete
            # difference list is available and every difference is explained.
            if result['failure_count'] == len(result['failures']) == len(expected):
                result['expected_review_policy_differences'] = expected
                result['failure_count'] = 0
                result['failures'] = []
        record_stage(name, result)


def review_state():
    actors = route['actors']()
    by_label = {a.get_actor_label(): a for a in actors}
    baseline = read(route['STATE'])
    current = read(os.path.join(core['META'], 'StormPass_CurrentReviewVariant.json'))['active_variant']
    access = read(os.path.join(core['META'], 'StormPass_RouteAccessActors.json'))['actors']
    failures = []
    if len(actors) != 14408 + len(access):
        failures.append('actor inventory')
    if len([a for a in actors if isinstance(a, unreal.PlayerStart)]) != 1:
        failures.append('PlayerStart count')
    for row in baseline['actors']:
        a = by_label.get(row['label'])
        if not a:
            failures.append(row['label'] + ': missing')
            continue
        active = row['variant'] == current
        if bool(a.get_editor_property('hidden')) != (row['hidden_in_game'] if active else True):
            failures.append(row['label'] + ': hidden in game')
        components = {c.get_name(): c for c in a.get_components_by_class(unreal.SceneComponent)}
        for source in row['components']:
            c = components.get(source['name'])
            if not c or bool(c.get_editor_property('visible')) != (source['visible'] if active else False):
                failures.append(row['label'] + ': component visibility')
            if c and 'collision' in source:
                expected = getattr(unreal.CollisionEnabled, source['collision']) if active else unreal.CollisionEnabled.NO_COLLISION
                if c.get_collision_enabled() != expected:
                    failures.append(row['label'] + ': collision')
    anchors = {r['source_name']: r for r in read(os.path.join(core['META'], 'StormPass_PlayableCameraAnchors.json'))['anchors']}
    for row in access:
        a = by_label.get(row['label'])
        source = anchors[row['source_name']]
        key = 'review_camera_location_cm' if row.get('editor_only') else 'location_cm'
        if not a or (a.get_actor_location() - unreal.Vector(*source[key])).length() > .002:
            failures.append(row['label'] + ': source location')
        if row.get('editor_only') and a and not a.get_editor_property('is_editor_only_actor'):
            failures.append(row['label'] + ': not editor-only')
    record_stage('review_state', {'actor_count': len(actors), 'source_actor_count': 14408,
                                 'review_access_actors': len(access), 'phase_actors_retained': len(baseline['actors']),
                                 'active_variant': current, 'failure_count': len(failures), 'failures': failures})


def materials():
    native = core['audit']()
    record_stage('native_surface_controls', dict(native, failure_count=len(native['failures'])))
    actors = route['actors']()
    slots, materials = 0, {}
    failures = []
    for a in actors:
        if a.get_actor_label().startswith(('SP_ReviewCamera_', 'SP_PlayerStart_')):
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            for i in range(c.get_num_materials()):
                slots += 1
                m = c.get_material(i)
                path = m.get_path_name() if m else ''
                if not m or any(n in path for n in ('WorldGridMaterial', 'DefaultMaterial', 'MI_DisplayColor')):
                    failures.append(a.get_actor_label() + ': slot %d %s' % (i, path))
                if m:
                    materials[path] = m
    sss_report = read(os.path.join(core['META'], 'StormPass_SubsurfaceRestoration_20260908.json'))
    for path, row in sss_report['materials'].items():
        m = unreal.load_asset(path)
        if m.get_editor_property('parent').get_path_name() != row['parent']:
            failures.append(path + ': SSS parent')
        mask = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(m, 'SP_SSS_Mask')
        if not mask or mask.get_path_name() != row['mask']:
            failures.append(path + ': SSS texture')
        for name, expected in [('SP_SSS_Intensity', row['sss_intensity']), ('SP_SSS_Opacity', row['sss_opacity'])]:
            actual = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(m, name)
            if abs(actual - expected) > .00001:
                failures.append(path + ': ' + name)
        if m.get_editor_property('base_property_overrides').get_editor_property('shading_model') != unreal.MaterialShadingModel.MSM_SUBSURFACE:
            failures.append(path + ': SSS shading model')
    expected_sss = sum(r['source_use_sss'] for r in read(core['PLAN'])['materials'])
    if len(sss_report['materials']) != expected_sss:
        failures.append('Incomplete SSS material count')
    cart = read(os.path.join(core['META'], 'StormPass_CartSectionCorrection_20260907.json'))
    by_label = {a.get_actor_label(): a for a in actors}
    for label in cart['actors']:
        c = by_label[label].get_component_by_class(unreal.StaticMeshComponent)
        for i, expected in enumerate(cart['corrected_imported_materials']):
            if c.get_material(i).get_path_name() != expected:
                failures.append(label + ': corrected cart slot %d' % i)
    record_stage('live_material_inputs', {'live_material_count': len(materials), 'live_slot_count': slots,
                                         'subsurface_material_count': len(sss_report['materials']),
                                         'failure_count': len(failures), 'failures': failures})
