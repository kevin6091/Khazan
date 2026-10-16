"""Read-only saved-asset comparison for the five player KZ_Slash montages."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert root == main
out = Path(os.environ['KZ_SLASH_OUT'])
out.mkdir(parents=True, exist_ok=True)
baseline = json.loads((main/'Metadata/PlayerSlashOuter_20261014/Audit01/Inventory.json').read_text(encoding='utf-8'))
receipt = json.loads((main/'Metadata/PlayerSlashOuter_20261014/MainApply/Receipt.json').read_text(encoding='utf-8'))

def value(obj, field):
    item = obj.get_editor_property(field)
    if isinstance(item, u.Object):
        return item.get_path_name()
    if field in ('RelativeLocation', 'Scale3D'):
        return [item.x, item.y, item.z]
    if field == 'RelativeRotation':
        return [item.pitch, item.yaw, item.roll]
    return str(item) if field.endswith('Socket') or field in ('EventId', 'SourceField') else item

fields = [key for key in baseline['rows'][0]['objects'][0] if key not in ('path', 'event_index')]
rows = []
ids = set()
original = 0
for old in baseline['rows']:
    package = old['asset']
    rel = 'Content/'+package.removeprefix('/Game/')+'.uasset'
    file = root/rel
    assert hashlib.sha256(file.read_bytes()).hexdigest() == receipt['targets'][rel]['after_sha256'], rel
    montage = u.load_asset(package)
    assert montage, package
    events = list(u.AnimationLibrary.get_animation_notify_events(montage))
    assert [e.export_text() for e in events] == old['event_clock_guid'], package
    fresh = []
    for index, event in enumerate(events):
        parent = event.get_editor_property('Notify')
        if not isinstance(parent, u.KZAnimNotify_CombatEffect):
            continue
        for obj in [parent]+list(parent.get_editor_property('BatchedEffects')):
            item = {'path':obj.get_path_name(),'event_index':index}
            item.update({field:value(obj,field) for field in fields})
            item['WeaponSlashOutwardOffsetCm'] = value(obj,'WeaponSlashOutwardOffsetCm')
            fresh.append(item)
    assert len(fresh) == len(old['objects']), package
    changed = 0
    for before, after in zip(old['objects'], fresh):
        assert before['path'] == after['path'] and before['event_index'] == after['event_index'], package
        slash = before['EventId'].startswith('KZWeaponSlash_')
        if not slash:
            original += 1
            assert all(before[field] == after[field] for field in fields), before['path']
            assert after['WeaponSlashOutwardOffsetCm'] == 0.0, before['path']
            continue
        ids.add(before['EventId'])
        allowed = {'WeaponEdgeNearSocket','WeaponEdgeTipSocket','Scale3D'}
        assert all(before[field] == after[field] for field in fields if field not in allowed), before['path']
        if before['EventId'].endswith('b7016da5'):
            assert all(before[field] == after[field] for field in fields), before['path']
            assert after['WeaponSlashOutwardOffsetCm'] == 0.0, before['path']
        else:
            assert after['WeaponEdgeNearSocket'] in ('FX_L_Axe_02','FX_R_Sword_02'), before['path']
            assert after['WeaponEdgeTipSocket'] in ('FX_L_Axe_01','FX_R_Sword_01'), before['path']
            assert after['WeaponSlashOutwardOffsetCm'] > 0.0, before['path']
            changed += 1
    rows.append({'asset':package,'total_effect_objects':len(fresh),
                 'original_effect_objects':old['original_count'],
                 'tuned_slash_objects':changed,
                 'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
assert len(ids) == 33 and original == 882 and sum(row['tuned_slash_objects'] for row in rows) == 64
result = {'status':'passed','saved_packages':len(rows),'slash_pairs':len(ids),
          'original_effect_objects_unchanged':original,'changed_slash_start_end_objects':64,
          'weak02_sequencer_objects_unchanged':2,'event_clock_guid_unchanged':True,
          'rows':rows}
(out/'SavedReadback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('SLASH_OUTER_SAVED_READBACK',len(rows),len(ids),original)
