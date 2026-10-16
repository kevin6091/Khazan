"""Read-only inventory of every player montage that references KZ_Slash."""
from pathlib import Path
import json
import os
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
assert root == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out = Path(os.environ['KZ_SLASH_OUT'])
out.mkdir(parents=True, exist_ok=True)
assets = [
    '/Game/_Art/Player/Animation/InGame/DAS/DodgeAttack/AM_DAS_Player_DodgeAttack',
    '/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack',
    '/Game/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongAttackCombo',
    '/Game/_Art/Player/Animation/InGame/DAS/StrongAttack/AM_DAS_StrongChargeAttack',
    '/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo',
]
fields = [
    'EventId', 'bEndEvent', 'WindowStartTime', 'WindowEndTime',
    'NiagaraTemplate', 'ParticleTemplate', 'RelativeLocation',
    'RelativeRotation', 'Scale3D', 'WeaponEdgeNearSocket',
    'WeaponEdgeTipSocket', 'WeaponSlashReferenceSpan',
    'bAlignToWeaponSweep', 'bUseSequencerTransform', 'SourceField',
]

def value(obj, field):
    v = obj.get_editor_property(field)
    if isinstance(v, u.Object):
        return v.get_path_name()
    if field in ('RelativeLocation', 'Scale3D'):
        return [v.x, v.y, v.z]
    if field == 'RelativeRotation':
        return [v.pitch, v.yaw, v.roll]
    return str(v) if field.endswith('Socket') or field in ('EventId', 'SourceField') else v

rows = []
for path in assets:
    montage = u.load_asset(path)
    assert montage, path
    events = list(u.AnimationLibrary.get_animation_notify_events(montage))
    row = {'asset': path, 'event_clock_guid': [e.export_text() for e in events],
           'objects': []}
    for index, event in enumerate(events):
        parent = event.get_editor_property('Notify')
        if not isinstance(parent, u.KZAnimNotify_CombatEffect):
            continue
        for obj in [parent] + list(parent.get_editor_property('BatchedEffects')):
            item = {'path': obj.get_path_name(), 'event_index': index}
            item.update({field: value(obj, field) for field in fields})
            row['objects'].append(item)
    row['addons'] = [x for x in row['objects'] if x['EventId'].startswith('KZWeaponSlash_')]
    row['original_count'] = len(row['objects']) - len(row['addons'])
    rows.append(row)

assert sum(len(row['addons']) for row in rows) == 66
(out/'Inventory.json').write_text(json.dumps({'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
print('SLASH_OUTER_AUDIT', [(Path(row['asset']).name, len(row['addons'])) for row in rows])
