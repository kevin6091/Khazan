"""Root-only offline intake of the already delivered ARCH-85 assets into VFX Work.

Default: prepare immutable backups and a CAS plan, with no Content writes.
--apply: copy only physical private packages. Main-backed read-only junctions
are verified in place and never written. No editor/process is launched.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import shutil
import subprocess

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
TASK = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
OUT = TASK / 'Authoring/ContentRebaseRevision'
REACTION = MAIN / 'Metadata/CombatReaction_20261008'
FAMILIES = ('Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite', 'ApesStoneHandElite', 'Yetuga')
DEFINITIONS = {'Content/Monsters/' + f + '/Data/DA_Character_' + f + '.uasset' for f in FAMILIES}


def sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.intake.tmp')
    assert not temp.exists(), str(temp)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def relative_path(relative):
    p = Path(relative)
    assert not p.is_absolute() and '..' not in p.parts and p.parts[0] == 'Content'
    assert p.suffix == '.uasset', relative
    return p


def private_target(relative):
    p = WORK / relative_path(relative)
    assert p.resolve() == p and p.resolve().is_relative_to(WORK.resolve()), 'Private physical destination required: ' + str(p)
    return p


def immutable(source, destination, expected):
    assert sha(source) == expected
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert destination.resolve() == destination and destination.resolve().is_relative_to(OUT.resolve())
    if destination.exists():
        assert sha(destination) == expected, 'Retained backup differs: ' + str(destination)
    else:
        shutil.copy2(source, destination)
    assert sha(destination) == expected


def input_paths():
    return [REACTION / n for n in ('FinalVerification.json', 'PreparedDelivery.json', 'DeliveryReceipt.json')] + [
        TASK / 'PreparedPlaybackPlan.json', TASK / 'Authoring/PrivateAuthoring.json',
        TASK / 'WorkBaseline.json',
        TASK / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json',
        MAIN / 'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json',
        WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources/ArtCandidateManifest.json']


def check_inputs(inputs):
    for path, expected in inputs.items():
        assert sha(path) == expected, 'Evidence changed: ' + path


def check_rows(plan, before):
    check_inputs(plan['inputs'])
    for r in plan['rows']:
        relative_path(r['relative'])
        assert sha(MAIN / r['relative']) == r['main_current_sha256'], 'Main Reaction CAS changed: ' + r['relative']
        p = WORK / r['relative']
        if r['mode'] == 'shared_readonly_current':
            assert p.resolve() == (MAIN / r['relative']).resolve(), 'Shared input identity changed'
            assert sha(p) == r['main_current_sha256']
        else:
            p = private_target(r['relative'])
            expected = r['private_before_sha256'] if before else r['main_current_sha256']
            assert sha(p) == expected, 'Private intake CAS changed: ' + r['relative']
    for relative, expected in plan['protected_private_sha256'].items():
        assert sha(private_target(relative)) == expected, 'Protected VFX candidate changed: ' + relative
    for relative, expected in plan['protected_main_sha256'].items():
        assert sha(MAIN / relative) == expected, 'Protected original Main VFX baseline changed: ' + relative


def prepare():
    assert MAIN.resolve() == MAIN and WORK.resolve() == WORK and MAIN != WORK
    assert not (OUT / 'IntakeApplied.json').exists(), 'Intake already applied; inspect its receipt instead'
    inputs = {str(p): sha(p) for p in input_paths()}
    assert all(inputs.values())
    final = read(REACTION / 'FinalVerification.json')
    prepared = read(REACTION / 'PreparedDelivery.json')
    delivered = read(REACTION / 'DeliveryReceipt.json')
    assert final['success'] and final['status'] == 'MainDeliveredAndFreshVerified' and final['delivered_files'] == 146
    assert delivered['complete'] and Path(prepared['main']).resolve() == MAIN
    assert {r['relative']: (r['before'], r['after']) for r in delivered['rows']} == {
        r['relative']: (r['before'], r['after']) for r in prepared['rows']}
    reaction = [r for r in prepared['rows'] if r['kind'] == 'asset']
    assert len(reaction) == 130 and len({r['relative'] for r in reaction}) == 130
    author = read(TASK / 'Authoring/PrivateAuthoring.json')
    playback = read(TASK / 'PreparedPlaybackPlan.json')
    assert author['status'] == 'passed' and author['plan_sha256'] == sha(TASK / 'PreparedPlaybackPlan.json')
    journal = {r['relative']: r for r in author['mutation_journal']}
    assert len(journal) == 499 and len(author['sequences']) == 487 and len(author['death_presentations']) == 6
    assert set(journal).intersection(r['relative'] for r in reaction) == DEFINITIONS
    rows = []
    for r in reaction:
        relative = r['relative']; relative_path(relative)
        assert sha(MAIN / relative) == r['after'], 'Current Main differs from delivered ARCH-85'
        p = WORK / relative
        shared = p.resolve() == (MAIN / relative).resolve()
        if shared:
            assert relative not in DEFINITIONS and sha(p) == r['after']
        else:
            private_target(relative)
        rows.append({'relative': relative, 'main_current_sha256': r['after'], 'private_before_sha256': sha(p),
                     'mode': 'shared_readonly_current' if shared else 'private_copy',
                     'definition_restore_required': relative in DEFINITIONS})
    protected_private = {r: j['saved_sha256'] for r, j in journal.items() if r not in DEFINITIONS}
    protected_main = {r: j['before_sha256'] for r, j in journal.items() if r not in DEFINITIONS}
    art = read(WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources/ArtCandidateManifest.json')
    assert len(art['assets']) == 457
    protected_private.update({r['relative_file']: r['native_sha256'] for r in art['assets']})
    protected_main.update({r['relative_file']: r['before_main_sha256'] for r in art['assets']})
    for r in DEFINITIONS:
        assert sha(private_target(r)) == journal[r]['saved_sha256'], 'Original VFX definition candidate drift'
        assert playback['definition_baseline'][r] == journal[r]['before_sha256']
    plan = {'schema': 'Khazan.MonsterVFX.ReactionContentIntake.v1', 'status': 'prepared',
            'utc': datetime.now(timezone.utc).isoformat(), 'main': str(MAIN), 'work': str(WORK),
            'inputs': inputs, 'rows': rows, 'protected_private_sha256': protected_private,
            'protected_main_sha256': protected_main, 'author_original_sha256': sha(TASK / 'Authoring/PrivateAuthoring.json'),
            'plan_original_sha256': sha(TASK / 'PreparedPlaybackPlan.json'),
            'author_original_journal': author['mutation_journal'],
            'counts': {'reaction_assets': 130, 'definitions_to_restore': 6,
                       'private_copy': sum(r['mode'] == 'private_copy' for r in rows),
                       'shared_readonly_current': sum(r['mode'] == 'shared_readonly_current' for r in rows)},
            'boundary': 'Main is read-only. Original author/plan/Apes/schema bytes are never revised. Only physical private packages copied.'}
    check_rows(plan, True)
    for p in input_paths():
        relative = p.relative_to(MAIN) if p.is_relative_to(MAIN) else Path('PrivateResources') / p.name
        immutable(p, OUT / 'BeforeReports' / relative, inputs[str(p)])
    for r in rows:
        if r['mode'] == 'private_copy' and r['private_before_sha256']:
            immutable(private_target(r['relative']), OUT / 'BeforePrivate' / r['relative'], r['private_before_sha256'])
        if r['relative'] in DEFINITIONS:
            immutable(MAIN / r['relative'], OUT / 'BeforeMain' / r['relative'], r['main_current_sha256'])
    check_rows(plan, True)
    destination = OUT / 'IntakePlan.json'
    if destination.exists():
        old = read(destination)
        assert {k: v for k, v in old.items() if k != 'utc'} == {k: v for k, v in plan.items() if k != 'utc'}, 'Prepared intake changed; do not replace it silently'
    else:
        write(destination, plan)
    print(json.dumps({'status': 'prepared', 'plan': str(destination), 'counts': plan['counts']}, ensure_ascii=False))


def assert_private_editor_closed():
    query = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor(?:-Cmd)?\\.exe$' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', query], check=True,
                         capture_output=True, text=True, encoding='utf-8').stdout.strip()
    rows = json.loads(raw) if raw else []
    if isinstance(rows, dict): rows = [rows]
    for row in rows:
        command = row.get('CommandLine')
        assert command is not None, 'Cannot establish editor ownership'
        assert str(WORK).lower() not in command.lower().replace('/', '\\'), 'Private editor still running: ' + str(row['ProcessId'])


def apply():
    plan = read(OUT / 'IntakePlan.json')
    assert plan['main'] == str(MAIN) and plan['work'] == str(WORK) and plan['status'] == 'prepared'
    assert not (OUT / 'IntakeApplied.json').exists(), 'Already applied'
    assert_private_editor_closed()
    check_rows(plan, True)
    staged = []
    try:
        for r in plan['rows']:
            if r['mode'] != 'private_copy': continue
            p = private_target(r['relative']); p.parent.mkdir(parents=True, exist_ok=True)
            if r['private_before_sha256']:
                assert sha(OUT / 'BeforePrivate' / r['relative']) == r['private_before_sha256'], 'Private rollback backup changed'
            temp = p.with_name(p.name + '.reaction-intake.tmp'); assert not temp.exists()
            shutil.copy2(MAIN / r['relative'], temp)
            assert temp.resolve() == temp and sha(temp) == r['main_current_sha256']
            staged.append((r, p, temp))
        check_rows(plan, True)
        for r, p, temp in staged:
            assert private_target(r['relative']) == p
            assert sha(p) == r['private_before_sha256'] and sha(MAIN / r['relative']) == r['main_current_sha256']
            os.replace(temp, p)
        check_rows(plan, False)
        write(OUT / 'IntakeApplied.json', {'schema': plan['schema'], 'status': 'passed',
              'utc': datetime.now(timezone.utc).isoformat(), 'plan_sha256': sha(OUT / 'IntakePlan.json'),
              'content_copies': len(staged), 'shared_readonly_current': plan['counts']['shared_readonly_current'],
              'main_mutations': 0, 'original_reports_unchanged': True, 'stage': 'ReactionAssetsStagedAwaitingDeathFieldRestore',
              'definitions_need_restore': sorted(DEFINITIONS),
              'boundary': 'Disk intake only; next fresh native-capable private process must restore six DeathPresentationMontage fields.'})
    except Exception:
        # CAS rollback only our own known output bytes, never unrelated changes.
        for r, p, temp in reversed(staged):
            if sha(p) == r['main_current_sha256'] and sha(p) != r['private_before_sha256']:
                assert private_target(r['relative']) == p
                backup = OUT / 'BeforePrivate' / r['relative']
                if r['private_before_sha256']:
                    assert sha(backup) == r['private_before_sha256']; shutil.copy2(backup, p)
                else:
                    private_target(r['relative']).unlink()
            if temp.exists():
                assert temp.resolve() == temp and temp.resolve().is_relative_to(WORK); temp.unlink()
        raise
    print(json.dumps({'status': 'passed', 'receipt': str(OUT / 'IntakeApplied.json'), 'content_copies': len(staged)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    apply() if args.apply else prepare()
