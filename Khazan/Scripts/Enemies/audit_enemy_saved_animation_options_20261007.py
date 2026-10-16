"""Fresh-process readback of this task's scoped sequences, AI data and root sampling."""
from pathlib import Path
import json, math, os, unreal
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan')
OUT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/EnemyAnimationOrganization_20261007')
preflight = {r['old']: r for r in json.loads((OUT / 'Preflight.json').read_text(encoding='utf-8'))['rows']}
pairs = (WORK / 'Saved/EnemyAnimationOrganization/AssetPairs.tsv').read_text(encoding='utf-8').splitlines()
rows = []
for pair in pairs:
    current, old = pair.split('|')
    clip = unreal.load_asset(current)
    assert isinstance(clip, unreal.AnimSequence), current
    source = preflight[old]
    assert clip.get_editor_property('enable_root_motion') and clip.get_editor_property('force_root_lock'), current
    assert clip.get_editor_property('root_motion_root_lock') == unreal.RootMotionRootLock.ANIM_FIRST_FRAME, current
    assert clip.get_editor_property('rate_scale') == source['rate_scale'], current
    assert abs(clip.get_play_length() - source['length']) < 1.e-6, current
    diffs = []
    for fraction, original in zip([0., .5, 1.], source['root_extraction']):
        actual = unreal.AnimationLibrary.extract_root_track_transform(clip, fraction * source['length'])
        t = [actual.translation.x, actual.translation.y, actual.translation.z]
        q = [actual.rotation.x, actual.rotation.y, actual.rotation.z, actual.rotation.w]
        distance = math.sqrt(sum((a-b)**2 for a,b in zip(t, original['translation'])))
        qdot = min(1., abs(sum(a*b for a,b in zip(q, original['rotation']))))
        diffs.append(dict(fraction=fraction, translation_cm=distance, rotation_rad=2*math.acos(qdot)))
    rows.append(dict(asset=current, source_before=old, family=source['family'], category=source['category'], root=source['root'], length=source['length'], rate_scale=source['rate_scale'], sampling_differences=diffs))
families = []
for family, expected in [('Swordsman',5),('SwordShield',3),('HeavySwordsman',7),('HalberdElite',20)]:
    base = '/Game/Monsters/' + family
    bp = unreal.load_asset('/Game/Bluprints/Monsters/BP_Monster_' + family)
    cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(bp.get_path_name()))
    attacks = cdo.get_editor_property('AttackAbilities')
    assert len(attacks) == expected, (family, len(attacks))
    settings = cdo.get_editor_property('AISettings')
    interval = settings.get_editor_property('AttackIntervalSeconds')
    anim = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(base + '/Animations/ABP_' + family))
    assert anim.get_editor_property('RootMotionMode') == unreal.RootMotionMode.ROOT_MOTION_FROM_MONTAGES_ONLY, family
    used = set()
    for ability in attacks:
        definition = unreal.get_default_object(ability).get_editor_property('ComboDefinition')
        for node in definition.get_editor_property('Nodes'):
            montage = node.get_editor_property('Montage')
            for track in montage.get_editor_property('SlotAnimTracks'):
                for segment in track.get_editor_property('AnimTrack').get_editor_property('AnimSegments'):
                    used.add(segment.get_editor_property('AnimReference').get_path_name().split('.')[0])
    families.append(dict(family=family, attack_count=len(attacks), used_attack_clips=sorted(used), interval=[interval.x, interval.y], combo=settings.get_editor_property('ContinueComboChance'), chase_reaction=settings.get_editor_property('ChaseReactionSeconds')))
remaining = [old for old in (WORK/'Saved/EnemyAnimationOrganization/OldAssets.txt').read_text(encoding='utf-8').splitlines() if (WORK/('Content/'+old.removeprefix('/Game/')+'.uasset')).exists()]
assert not remaining, remaining
report = dict(pid=os.getpid(), project=str(WORK), status='ReadbackPassed', sequences=rows, families=families, remaining_old_packages=remaining)
(OUT/'SavedAnimationAudit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
worst = sorted([(d['translation_cm'], r['asset'], d['fraction']) for r in rows for d in r['sampling_differences']],reverse=True)[:12]
print(json.dumps(dict(sequences=len(rows), families=families, worst_sampling_differences=worst)))
