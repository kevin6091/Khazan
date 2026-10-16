"""Target the two actual pattern definitions and their current notify consumers."""
from pathlib import Path
import unreal as u
import json, os

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_COMBAT_FINISH_OUT'])
path = lambda obj: obj.get_path_name() if obj else None
report = {'project': str(root), 'families': [], 'sequences': {}, 'systems': {}, 'saves': 0}
def effect(e):
    return {'object': path(e), 'particle': path(e.get_editor_property('particle_template')),
        'niagara': path(e.get_editor_property('niagara_template')),
        'socket': str(e.get_editor_property('source_socket')), 'scale': str(e.get_editor_property('scale3d')),
        'location': str(e.get_editor_property('relative_location')), 'rotation': str(e.get_editor_property('relative_rotation')),
        'attached': e.get_editor_property('bAttached'), 'floor': e.get_editor_property('bSpawnOnFloor'),
        'winter': e.get_editor_property('bWinterOnly'), 'source_package': e.get_editor_property('source_package'),
        'source_field': e.get_editor_property('source_field')}
sequences = {}
for family in ['ApesStoneHandElite', 'Yetuga']:
    definition = u.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family)
    if not definition and family == 'ApesStoneHandElite':
        definition = u.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_Apes')
    assert definition, family
    row = {'family': family, 'definition': path(definition), 'nodes': [], 'objects': []}
    for node in definition.get_editor_property('nodes'):
        montage = node.get_editor_property('montage')
        row['nodes'].append({'id': str(node.get_editor_property('node_id')), 'montage': path(montage),
            'section': str(node.get_editor_property('section_name')), 'actions': [a.export_text() for a in node.get_editor_property('pattern_actions')]})
        if montage:
            for slot in montage.get_editor_property('slot_anim_tracks'):
                for segment in slot.get_editor_property('anim_track').get_editor_property('anim_segments'):
                    seq = segment.get_editor_property('anim_reference')
                    if seq: sequences[path(seq)] = seq
    for obj in definition.get_editor_property('pattern_objects'):
        row['objects'].append(obj.export_text())
        for seq in obj.get_editor_property('animations').values():
            if seq: sequences[path(seq)] = seq
    # Include both walking loops and every owned animation already registered for this family.
    for asset in u.EditorAssetLibrary.list_assets('/Game/Monsters/'+family+'/Animations', recursive=True):
        seq = u.load_asset(asset)
        if isinstance(seq, u.AnimSequence): sequences[path(seq)] = seq
    report['families'].append(row)
for name, seq in sequences.items():
    events = []
    for event in u.AnimationLibrary.get_animation_notify_events(seq):
        state = event.get_editor_property('notify_state_class')
        notify = event.get_editor_property('notify')
        record = {'event': event.export_text(), 'class': path(state.get_class()) if state else path(notify.get_class()) if notify else None}
        if state and state.get_class().get_name() == 'KZAnimNotifyState_MonsterVisual':
            e = state.get_editor_property('effect')
            if e:
                record['effect'] = effect(e)
                ps = e.get_editor_property('particle_template')
                if ps: report['systems'][path(ps)] = {'export': None}
        events.append(record)
    report['sequences'][name] = {'length': seq.get_play_length(), 'rate': seq.get_editor_property('rate_scale'), 'events': events}
(out/'Probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('GIANT_VFX_PROBE: sequences='+str(len(sequences))+' particles='+str(len(report['systems'])))
