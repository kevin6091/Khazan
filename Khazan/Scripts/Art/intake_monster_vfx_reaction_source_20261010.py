"""Guarded ARCH-85 source intake into the private ARCH-84 candidate only.

Preparation writes immutable Saved backups, normalized three-way output and
review diffs. Apply requires a separately reviewed, hash-bound four-file audit.
Main Source, Content, Config, binaries and original WorkBaseline are read only.
No editor, compiler, reload, package save or asset copy is performed here.
"""
from pathlib import Path
import argparse
import difflib
import json
import os
import shutil
import subprocess

import deliver_monster_vfx_main_20261008 as guard

MAIN, WORK, OUT = guard.MAIN, guard.WORK, guard.OUT
ROOT = OUT / 'MainRebase'
PREPARED = ROOT / 'Prepared.json'
REVIEW = ROOT / 'ManualMergeReview.json'
RECEIPT = ROOT / 'MainRebaseIntake.json'
BASELINE = OUT / 'WorkBaseline.json'
REACTION = MAIN / 'Metadata/CombatReaction_20261008/DeliveryReceipt.json'
PLAYBACK = OUT / 'PreparedPlaybackPlan.json'
INTERSECTIONS = {
    'Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.cpp',
    'Source/Khazan/Character/KZMonster.cpp',
    'Source/Khazan/Character/KZMonster.h',
    'Source/Khazan/Data/KZCharacterDefinitionData.h',
}
VFX = guard.SOURCE
REQUIRE_REVIEW = {
    'all_four_merge_diffs_manually_reviewed',
    'reaction_guard_hit_cancel_and_capsule_cleanup_preserved',
    'vfx_lifetime_death_and_material_receipts_preserved',
    'definition_reaction_settings_alignment_and_death_field_preserved',
    'no_unrelated_source_change',
}


def immutable_json(path, value):
    guard.require(not path.exists(), 'Immutable receipt already exists: ' + str(path))
    guard.write(path, value)


def inputs(root):
    result = guard.inventory(root, ('Source', 'Config'))
    result['Khazan.uproject'] = guard.sha(root / 'Khazan.uproject')
    guard.require(result['Khazan.uproject'], 'Missing project descriptor')
    return result


def source(values):
    return {p: h for p, h in values.items() if p.startswith('Source/')}


def changed(a, b):
    return {p for p in a.keys() | b.keys() if a.get(p) != b.get(p)}


def native(root):
    return {p.relative_to(root).as_posix(): guard.sha(p)
            for p in (root / 'Binaries/Win64').glob('UnrealEditor-Khazan*') if p.is_file()}


def selected_content_paths():
    playback, reaction = guard.load(PLAYBACK), guard.load(REACTION)
    return sorted(set(playback['asset_baseline']) | set(playback['definition_baseline']) |
                  {r['relative'] for r in reaction['rows'] if r['relative'].startswith('Content/')} |
                  {'Content/Data/Character/DA_CharacterDefinition_Player.uasset'})


def content(root, paths):
    # Existing private Content junctions are report-only readers. Every write
    # target in this helper is still checked by target() and confined to Saved
    # or the private physical Source tree; no junction destination is written.
    guard.require(all(p.startswith('Content/') and '\\' not in p and not Path(p).is_absolute() and
                      '..' not in Path(p).parts for p in paths), 'Invalid report-only Content path')
    return {p: guard.sha(root / p) for p in paths}


def check_original(expected):
    guard.require(guard.sha(BASELINE) == expected, 'Original WorkBaseline changed')
    baseline_source = source(guard.load(BASELINE)['main_sha256'])
    guard.require(len(baseline_source) == 96 and
                  guard.inventory(OUT / 'BaselineSource', ('Source',)) == baseline_source,
                  'Immutable original Source96 backup changed')
    return baseline_source


def backup(root, destination, values):
    for p, h in sorted(values.items()):
        guard.copy_immutable(guard.target(root, p), guard.target(destination, p), h)
    guard.require(inputs(destination) == values, 'Complete Source/Config/project backup differs')


def normalize(path):
    # Encoding/newline normalization is confined to the four merged outputs;
    # Main-only copies and all seven VFX-only files retain their exact bytes.
    text = path.read_text(encoding='utf-8-sig')
    return text if text.endswith('\n') else text + '\n'


def prepare():
    guard.require(not PREPARED.exists() and not RECEIPT.exists(), 'Intake is already prepared/applied')
    original_hash = guard.sha(BASELINE)
    old = check_original(original_hash)
    before_main, before_work = inputs(MAIN), inputs(WORK)
    main_source, private_source = source(before_main), source(before_work)
    guard.require({p: h for p, h in before_main.items() if not p.startswith('Source/')} ==
                  {p: h for p, h in before_work.items() if not p.startswith('Source/')},
                  'Main/private Config and project descriptor must already match; source intake will not rewrite them')
    reaction = guard.load(REACTION)
    reaction_rows = {r['relative']: r for r in reaction['rows'] if r['relative'].startswith('Source/')}
    guard.require(reaction.get('complete') is True and len(reaction_rows) == 16,
                  'Completed Reaction Source16 receipt required')
    for p, r in reaction_rows.items():
        guard.require(old.get(p) == r['before'] and main_source.get(p) == r['after'],
                      'Current Main no longer matches delivered Reaction: ' + p)
    reaction_changed, vfx_changed = changed(old, main_source), changed(old, private_source)
    guard.require(len(main_source) == 98 and len(private_source) == 99 and
                  reaction_changed == set(reaction_rows) and vfx_changed == VFX and
                  reaction_changed & vfx_changed == INTERSECTIONS,
                  'Unexpected source drift/count/intersection; do not overwrite it')
    reaction_only, vfx_only = reaction_changed - INTERSECTIONS, VFX - INTERSECTIONS
    guard.require(len(reaction_only) == 12 and len(vfx_only) == 7, 'Source scopes changed')
    content_paths = selected_content_paths()
    main_content, private_content = content(MAIN, content_paths), content(WORK, content_paths)
    native_main, native_work = native(MAIN), native(WORK)
    modules = guard.load(MAIN / 'Binaries/Win64/UnrealEditor.modules')
    guard.require(modules.get('Modules', {}).get('Khazan') == reaction['alias'],
                  'Main selected module no longer matches Reaction receipt')
    backup(MAIN, ROOT / 'BeforeMain', before_main)
    backup(WORK, ROOT / 'BeforePrivate', before_work)
    guard.copy_immutable(MAIN / 'Binaries/Win64/UnrealEditor.modules',
                         ROOT / 'BeforeMain/UnrealEditor.modules', guard.sha(MAIN / 'Binaries/Win64/UnrealEditor.modules'))
    stage, rows = ROOT / 'Merged', []
    expected_private = dict(private_source)
    for p in sorted(reaction_only | INTERSECTIONS):
        dest = guard.target(stage, p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        guard.require(not dest.exists(), 'Stale merge staging output: ' + p)
        if p in reaction_only:
            guard.copy_immutable(MAIN / p, dest, main_source[p])
            method = 'ExactCurrentMainCopy'
        else:
            paths = []
            for label, project in [('CurrentMain', MAIN), ('Original', OUT / 'BaselineSource'), ('PrivateVFX', WORK)]:
                temp = guard.target(ROOT / 'Normalized' / label, p)
                temp.parent.mkdir(parents=True, exist_ok=True)
                guard.require(not temp.exists(), 'Stale normalized merge input')
                temp.write_text(normalize(project / p), encoding='utf-8', newline='\n')
                paths.append(temp)
            merged = subprocess.run(['git', 'merge-file', '-p', '--diff3', *map(str, paths)],
                                    capture_output=True, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
            guard.require(merged.returncode == 0, 'Three-way merge conflict (manual intervention required): ' + p +
                          '\n' + merged.stderr.decode('utf-8', errors='replace'))
            text = merged.stdout.decode('utf-8')
            guard.require(not any(marker in text for marker in ('<<<<<<<', '=======', '>>>>>>>')), 'Merge marker remained')
            dest.write_text(text, encoding='utf-8', newline='\n')
            method = 'GitThreeWayNormalizedUTF8LF'
            for label, project in [('FromCurrentMain', MAIN), ('FromPrivateVFX', WORK)]:
                diff = '\n'.join(difflib.unified_diff(normalize(project / p).splitlines(), text.splitlines(),
                    fromfile=label + '/' + p, tofile='Merged/' + p, n=4, lineterm='')) + '\n'
                diff_path = guard.target(ROOT / 'ReviewDiffs' / label, p + '.diff')
                diff_path.parent.mkdir(parents=True, exist_ok=True)
                guard.require(not diff_path.exists(), 'Stale review diff')
                diff_path.write_text(diff, encoding='utf-8', newline='\n')
        after = guard.sha(dest)
        expected_private[p] = after
        rows.append({'file': p, 'method': method, 'original': old.get(p),
                     'main_before': main_source.get(p), 'private_before': private_source.get(p), 'after': after})
    guard.require(len(expected_private) == 101 and changed(main_source, expected_private) == VFX,
                  'Merged candidate must differ current Main in exactly VFX11')
    result = {'status': 'prepared_needs_manual_review', 'utc': guard.utc(), 'main': str(MAIN), 'work': str(WORK),
        'helper_sha256': guard.sha(Path(__file__)), 'original_baseline_sha256': original_hash,
        'reaction_receipt_sha256': guard.sha(REACTION), 'playback_report_sha256': guard.sha(PLAYBACK),
        'original_source_count': 96, 'main_source': main_source, 'private_source_before': private_source,
        'private_source_after': expected_private, 'main_inputs': before_main, 'private_inputs': before_work,
        'main_native_before': native_main, 'private_native_before': native_work,
        'main_selected_module': modules, 'main_module_manifest_sha256': guard.sha(MAIN / 'Binaries/Win64/UnrealEditor.modules'),
        'source_backup_root': str(ROOT / 'BeforeMain'), 'private_backup_root': str(ROOT / 'BeforePrivate'),
        'intersections': sorted(INTERSECTIONS), 'reaction_only': sorted(reaction_only), 'vfx_only': sorted(vfx_only),
        'rows': rows, 'main_content_report_only': main_content, 'private_content_report_only': private_content,
        'private_content_shared_report_only': {p: str((WORK / p).resolve()) for p in content_paths
            if (WORK / p).resolve() != WORK / p},
        'content_changed_since_original_authoring_baseline': {
            p: {'original': h, 'current_main': main_content[p], 'private': private_content[p]}
            for p, h in {**guard.load(PLAYBACK)['asset_baseline'], **guard.load(PLAYBACK)['definition_baseline']}.items()
            if main_content[p] != h},
        'asset_writes': 0, 'main_source_writes': 0, 'editor_or_build_control': False,
        'limitations': ['Source-only intake. Reaction Content dependencies and six Definition assets need separate typed authoring rebase.',
                        'Fresh native build and Monster/Player/Reaction regression proofs are required; old DLL proofs do not validate merged source.']}
    guard.require(inputs(MAIN) == before_main and inputs(WORK) == before_work and
                  native(MAIN) == native_main and native(WORK) == native_work and
                  content(MAIN, content_paths) == main_content and content(WORK, content_paths) == private_content,
                  'Inputs changed during preparation; prepared result cannot be applied')
    immutable_json(PREPARED, result)
    return result


def apply():
    guard.require(not RECEIPT.exists(), 'Immutable intake receipt already exists')
    plan, review = guard.load(PREPARED), guard.load(REVIEW)
    guard.require(plan['helper_sha256'] == guard.sha(Path(__file__)) and
                  review.get('status') == 'passed' and review.get('prepared_sha256') == guard.sha(PREPARED) and
                  set(review.get('checks', {})) == REQUIRE_REVIEW and all(review['checks'].values()) and
                  review.get('merged_sha256') == {r['file']: r['after'] for r in plan['rows'] if r['file'] in INTERSECTIONS},
                  'Exact reviewed four-file merge proof is missing or changed')
    check_original(plan['original_baseline_sha256'])
    guard.require(guard.sha(REACTION) == plan['reaction_receipt_sha256'] and
                  guard.sha(PLAYBACK) == plan['playback_report_sha256'], 'Evidence changed after preparation')
    paths = list(plan['main_content_report_only'])
    def preserved():
        return (inputs(MAIN) == plan['main_inputs'] and native(MAIN) == plan['main_native_before'] and
            guard.sha(MAIN / 'Binaries/Win64/UnrealEditor.modules') == plan['main_module_manifest_sha256'] and
            native(WORK) == plan['private_native_before'] and content(MAIN, paths) == plan['main_content_report_only'] and
            content(WORK, paths) == plan['private_content_report_only'])
    guard.require(preserved() and inputs(WORK) == plan['private_inputs'], 'Fresh Main/private inputs CAS failed')
    guard.require(inputs(ROOT / 'BeforeMain') == plan['main_inputs'] and
                  inputs(ROOT / 'BeforePrivate') == plan['private_inputs'], 'Complete immutable backups differ')
    replaced = []
    try:
        for row in plan['rows']:
            p = row['file']
            dest, staged = guard.target(WORK, p), guard.target(ROOT / 'Merged', p)
            guard.require(guard.sha(dest) == row['private_before'] and guard.sha(staged) == row['after'],
                          'Immediate private file/staging CAS failed: ' + p)
            guard.exclusive(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp = dest.with_name(dest.name + '.source-rebase.tmp')
            guard.require(not temp.exists(), 'Existing private staging file: ' + str(temp))
            shutil.copy2(staged, temp)
            guard.require(guard.sha(temp) == row['after'] and guard.sha(dest) == row['private_before'], 'Atomic copy CAS failed')
            os.replace(temp, dest)
            os.utime(dest, None)  # Force the next owned build to consume the changed source.
            replaced.append(row)
        expected_inputs = {**plan['private_inputs'], **plan['private_source_after']}
        guard.require(inputs(WORK) == expected_inputs and preserved(), 'Post-intake source or protected input mismatch')
        receipt = {**plan, 'status': 'passed', 'applied_utc': guard.utc(), 'prepared_sha256': guard.sha(PREPARED),
                   'manual_review_sha256': guard.sha(REVIEW), 'private_source_after': source(inputs(WORK)),
                   'main_source_after': source(inputs(MAIN)), 'private_source_writes': len(replaced),
                   'main_preserved': True, 'private_config_project_native_content_preserved': True,
                   'build_or_runtime_verified': False}
        immutable_json(RECEIPT, receipt)
        return receipt
    except Exception as error:
        rollback = []
        for row in reversed(replaced):
            dest = guard.target(WORK, row['file'])
            if guard.sha(dest) != row['after']:
                rollback.append({'file': row['file'], 'status': 'PreservedConcurrentEdit'})
                continue
            if row['private_before'] is None:
                dest.unlink()
            else:
                saved = guard.target(ROOT / 'BeforePrivate', row['file'])
                guard.require(guard.sha(saved) == row['private_before'], 'Rollback backup changed')
                temp = dest.with_name(dest.name + '.source-rebase-rollback.tmp')
                guard.require(not temp.exists(), 'Existing rollback staging')
                shutil.copy2(saved, temp)
                guard.require(guard.sha(dest) == row['after'], 'Concurrent private edit before rollback')
                os.replace(temp, dest)
            rollback.append({'file': row['file'], 'status': 'RestoredBefore'})
        immutable_json(ROOT / ('Failure_' + guard.utc().replace(':', '-') + '.json'),
                       {'utc': guard.utc(), 'error': str(error), 'rollback': rollback})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    result = apply() if args.apply else prepare()
    print(json.dumps({'status': result['status'], 'source_counts': {
        'main': len(result['main_source']), 'private_before': len(result['private_source_before']),
        'private_after': len(result['private_source_after'])}, 'private_source_writes': result.get('private_source_writes', 0),
        'receipt': str(RECEIPT if args.apply else PREPARED)}, ensure_ascii=False))
