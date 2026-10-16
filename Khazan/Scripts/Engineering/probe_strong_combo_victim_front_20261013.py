"""Read only the actual StrongCombo and the four existing victim montages."""
import unreal as u
import os, json
from pathlib import Path

out = Path(os.environ['KZ_COMBAT_FINISH_OUT'])
def path(obj):
    return obj.get_path_name() if obj else None
def montage(obj):
    slots = obj.get_editor_property('slot_anim_tracks')
    return {'asset': path(obj), 'length': obj.get_play_length(),
            'sections': [str(obj.get_section_name(i)) for i in range(obj.get_num_sections())],
            'segments': [{'asset': path(s.get_editor_property('anim_reference')),
                          'start_pos': s.get_editor_property('start_pos'),
                          'anim_start_time': s.get_editor_property('anim_start_time'),
                          'anim_end_time': s.get_editor_property('anim_end_time')}
                         for t in slots for s in t.get_editor_property('anim_track').get_editor_property('anim_segments')]}
def execution_materials(obj):
    result = []
    for slot in obj.get_editor_property('slot_anim_tracks'):
        for segment in slot.get_editor_property('anim_track').get_editor_property('anim_segments'):
            seq = segment.get_editor_property('anim_reference')
            for event in u.AnimationLibrary.get_animation_notify_events(seq):
                state = event.get_editor_property('notify_state_class')
                if state and state.get_class().get_name() == 'KZAnimNotifyState_MonsterVisual':
                    if state.get_editor_property('material_overrides'):
                        result.append({'sequence': path(seq), 'notify': path(state),
                            'scalar_parameter': str(state.get_editor_property('scalar_parameter_name')),
                            'scalar_curve': str(state.get_editor_property('scalar_curve_name')),
                            'vector_parameter': str(state.get_editor_property('vector_parameter_name'))})
    return result
report = {'nodes': [], 'humanoids': []}
definition = u.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
for node in definition.get_editor_property('nodes'):
    report['nodes'].append({'id': str(node.get_editor_property('node_id')),
        'montage': path(node.get_editor_property('montage')),
        'section': str(node.get_editor_property('section_name')),
        'windows': [{'reaction': str(w.get_editor_property('hit_reaction')), 'source': w.get_editor_property('source')}
                    for w in node.get_editor_property('attack_windows')]})
for family in ['Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite']:
    character = u.load_asset('/Game/Monsters/'+family+'/Data/DA_Character_'+family)
    front = u.load_asset('/Game/Monsters/'+family+'/Animations/AM_BrutalVictimFront')
    reaction = character.get_editor_property('hit_reactions')
    report['humanoids'].append({'family': family, 'definition': path(character),
        'short': [path(m) for m in reaction.get_editor_property('short_hits')],
        'knockback': [path(m) for m in reaction.get_editor_property('knockbacks')],
        'victim': montage(front), 'victim_material_notifies': execution_materials(front)})
(out/'Probe.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('STRONG_VICTIM_PROBE_DONE')
