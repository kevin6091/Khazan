"""Root-operated, guarded Monster VFX delivery. Default is Saved-only preparation.

--apply is explicit. This helper never starts, closes, reloads, or saves an
editor. NativeCandidateIntegrity.json must bind the completed private author,
fresh saved readback, Monster real-RHI test, Player real-RHI regression, visual
review, latest successful build, and current resource manifests. Existing DLLs,
PDBs, patches, and aliases are retained; only a unique new alias is selected.
"""
from pathlib import Path
import argparse
import ctypes
import datetime as dt
import difflib
import hashlib
import json
import os
import re
import runpy
import shutil
import stat
import subprocess
import struct
import zipfile

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterVFXWork_20261008/Khazan'
OUT = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
RESOURCES = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Resources'
DELIVERY = OUT / 'MainDelivery'
PLAN = DELIVERY / 'Prepared.json'
RECEIPT = DELIVERY / 'Delivered.json'
SOURCE = {
    'Source/Khazan/Ability/KZActionAbility.cpp',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.h',
    'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp',
    'Source/Khazan/Animation/Notifies/KZAnimNotifyState_MonsterVisual.h',
    'Source/Khazan/Animation/Notifies/KZAnimNotifyState_MonsterVisual.cpp',
    'Source/Khazan/Character/KZMonster.h',
    'Source/Khazan/Character/KZMonster.cpp',
    'Source/Khazan/Data/KZCharacterDefinitionData.h',
    'Source/Khazan/Ability/MonsterAbility/KZExhaustionAbility.cpp',
    'Source/Khazan/Tests/KZCombatEffectPIETest.cpp',
    'Source/Khazan/Tests/KZMonsterVisualPIETest.cpp',
}
FAMILIES = {'Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite', 'ApesStoneHandElite', 'Yetuga'}
NO_EDITOR_WORLD = '<no-running-Main-editor>'
BUILD_ID = '55116800'
HASH = re.compile(r'^[0-9a-f]{64}$')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read(path):
    return Path(path).read_text(encoding='utf-8-sig')


def load(path):
    return json.loads(read(path))


def sha(path):
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def target(root, relative):
    """Only canonical, physical paths: a selected asset may not cross a junction."""
    require(isinstance(relative, str) and '\\' not in relative and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts and relative not in ('', '.'), 'Invalid relative path: ' + str(relative))
    root = root.resolve()
    lexical = Path(os.path.abspath(root / relative))
    require(lexical != root and lexical.is_relative_to(root), 'Path escapes project: ' + relative)
    for parent in [root] + list(reversed(lexical.parents[:len(lexical.relative_to(root).parts)-1])) + [lexical]:
        if parent.exists():
            require(not (parent.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT),
                    'Selected path crosses a symlink/junction: ' + str(parent))
    resolved = lexical.resolve()
    require(resolved == lexical and resolved.is_relative_to(root), 'Unexpected resolved path: ' + str(lexical))
    return lexical


def evidence_path(path):
    path = Path(path).resolve()
    require(path.is_file() and (path.is_relative_to(OUT.resolve()) or path.is_relative_to(RESOURCES.resolve())
                               or path.is_relative_to((MAIN / 'Metadata/MonsterVFX_20261008').resolve())
                               or path == (MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json').resolve()),
            'Evidence outside task reports or absent: ' + str(path))
    return path


def write(path, data, expected=None):
    path = target(path.parent, path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.monstervfx.tmp')
    require(not temporary.exists(), 'Existing receipt staging file: ' + str(temporary))
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if expected is not None:
        require(sha(path) == expected, 'Immediate JSON CAS failed: ' + str(path))
    os.replace(temporary, path)


def inventory(root, folders, excluded=()):
    excluded = set(excluded)
    return {p.relative_to(root).as_posix(): sha(p) for folder in folders for p in (root / folder).rglob('*')
            if p.is_file() and p.relative_to(root).as_posix() not in excluded}


def protected(selected):
    result = inventory(MAIN, ('Config', 'Content/Data', 'Content/Maps', 'Content/Monsters',
                             'Content/_Art/Enemies', 'Content/_Art/Player', 'Content/_Art/Effects'), selected)
    result['Khazan.uproject'] = sha(MAIN / 'Khazan.uproject')
    return result


def native_inventory():
    return {p.name: sha(p) for p in (MAIN / 'Binaries/Win64').glob('UnrealEditor-Khazan*') if p.is_file()}


def copy_immutable(src, dest, expected):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        require(sha(dest) == expected, 'Immutable staging/backup differs: ' + str(dest))
    else:
        shutil.copy2(src, dest)
    require(sha(dest) == expected, 'Staging/backup hash differs: ' + str(dest))


def census():
    command = '[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); $rows=@(Get-CimInstance Win32_Process -Filter "Name=\'UnrealEditor.exe\' OR Name=\'UnrealEditor-Cmd.exe\'" | Select-Object ProcessId,Name,ExecutablePath,CommandLine); ConvertTo-Json -InputObject $rows -Depth 3 -Compress'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
        capture_output=True, text=True, encoding='utf-8', errors='replace', check=True,
        creationflags=subprocess.CREATE_NO_WINDOW)
    rows = json.loads(result.stdout or '[]')
    require(isinstance(rows, list), 'Unexpected editor census')
    main, private, unknown = [], [], []
    for row in rows:
        args = [a or b for a, b in re.findall(r'"([^"]*)"|([^\s"]+)', row.get('CommandLine') or '')]
        projects = [p for p in args if p.lower().endswith('.uproject')]
        if not projects or any(not Path(p).is_absolute() for p in projects):
            unknown.append(row)
        elif any(Path(p).resolve() == (MAIN / 'Khazan.uproject').resolve() for p in projects):
            main.append(row)
        elif any(Path(p).resolve() == (WORK / 'Khazan.uproject').resolve() for p in projects):
            private.append(row)
    return {'utc': utc(), 'editors': rows, 'main_project_editors': main, 'private_project_editors': private,
            'unclassified_editors': unknown, 'method': 'Read-only Win32_Process, exact absolute uproject argument'}


def census_gate(value, main_pid):
    require(not value['unclassified_editors'] and not value['private_project_editors'],
            'Unknown or task-private editor still running; preserve it and wait')
    require({r['ProcessId'] for r in value['main_project_editors']} == ({main_pid} if main_pid else set()),
            'Main editor identity changed or closed mode has a running Main editor')


def latest(folder):
    header = evidence_path(folder / 'Latest.json')
    value = load(header)
    attempt = Path(value['attempt']).resolve()
    require(attempt.is_relative_to(folder.resolve()) and value.get('exit_code') == 0,
            'Latest attempt is not a successful task-owned result: ' + str(folder))
    return attempt, header


def proof_evidence(proof):
    result = {}
    for key, value in proof.get('evidence', {}).items():
        path, expected = (value['path'], value['sha256']) if isinstance(value, dict) else (key, value)
        path = evidence_path(path)
        require(HASH.fullmatch(expected or '') and sha(path) == expected, 'Root evidence hash mismatch: ' + str(path))
        result[str(path)] = expected
    require(result, 'Root integrity needs frozen evidence')
    return result


def runtime_gate(folder, test, author_path, build_exit, evidence):
    attempt, header = latest(folder)
    paths = [header] + [evidence_path(attempt / n) for n in ('Launch.json', 'Exit.json', 'Driver.json', 'PrivatePIE.log')]
    launch, exit_info, driver = [load(p) for p in paths[1:4]]
    log = read(paths[4])
    require(exit_info.get('exit_code') == 0 and exit_info['pid'] == launch['pid'] and launch.get('test') == test,
            'Runtime result identity/exit mismatch: ' + test)
    require(str(WORK / 'Khazan.uproject') in launch['args'] and not any('-nullrhi' in a.lower() for a in launch['args']),
            'Real-RHI private uproject launch required: ' + test)
    require(driver.get('status') == 'passed' and driver.get('test') == test and driver.get('package_saves') == 0
            and Path(driver['project']).resolve() == WORK.resolve() and driver.get('verification') == 'private_candidate',
            'Fresh private runtime driver did not pass: ' + test)
    complete = re.findall(r'Test Completed\. Result=\{([^}]+)\}[^\n]*Path=\{' + re.escape(test) + r'\}', log)
    require(complete and complete[-1] == 'Success' and 'Success' in driver.get('native_completion', ''),
            'Exact native test Success missing: ' + test)
    require(driver.get('material_compile_failures') == [] and 'Failed to compile Material' not in log
            and 'Default Material will be used in game' not in log, 'Real-RHI shader/default-material fallback unresolved')
    require(str(WORK / 'Binaries/Win64/UnrealEditor-Khazan.dll').replace('\\', '/') in log.replace('\\', '/')
            and 'InternalLoadLibrary' in log, 'Actual private DLL load not evidenced')
    require(paths[1].stat().st_mtime >= author_path.stat().st_mtime and paths[1].stat().st_mtime >= build_exit.stat().st_mtime,
            'Runtime launch predates authoring/native build')
    require(driver.get('captures'), 'Actual-character RHI captures absent: ' + test)
    for p in paths:
        require(str(p) in evidence and evidence[str(p)] == sha(p), 'Root proof does not bind current RHI attempt: ' + str(p))


def inputs(args):
    proof_path = evidence_path(args.proof)
    proof = load(proof_path)
    require(proof.get('status') == 'passed' and proof.get('checks') and all(v is True for v in proof['checks'].values())
            and proof['checks'].get('png_visual_review') is True,
            'Root NativeCandidateIntegrity checks are not all passed')
    evidence = proof_evidence(proof)
    evidence[str(proof_path)] = sha(proof_path)
    fixed = [OUT / 'WorkBaseline.json', OUT / 'PreparedPlaybackPlan.json', OUT / 'Authoring/PrivateAuthoring.json',
             OUT / 'Authoring/SavedReadback.json', RESOURCES / 'ArtCandidateManifest.json', RESOURCES / 'FinalResourceAudit.json',
             RESOURCES / 'ExecutionRadiusRevision.json']
    for p in fixed[1:]:
        require(str(p.resolve()) in evidence and evidence[str(p.resolve())] == sha(p), 'Root proof must bind ' + str(p))
    baseline, playback, author, saved, art, resource_audit, radius_revision = [load(p) for p in fixed]
    shared = shared_effects_rebase_revision()
    verify_saved_shared_revision(shared, saved)
    material_revision = shared['visual_revision'] if shared else visual_material_repair_revision()
    verify_saved_visual_revision(material_revision, saved)
    if material_revision:
        require(proof.get('visual_material_repair_revision_sha256') == material_revision['sha256']
                and evidence.get(str(material_revision['file'].resolve())) == material_revision['sha256']
                and fixed[3].stat().st_mtime >= material_revision['file'].stat().st_mtime,
                'Root proof/fresh saved readback must bind the exact visual material repair')
        for receipt in material_revision['receipts']:
            require(evidence.get(str(Path(receipt['path']).resolve())) == receipt['sha256'],
                    'Root proof must bind actual material component receipt')
    if shared:
        require(proof.get('shared_effects_rebase_revision_sha256') == shared['sha256']
                and evidence.get(str(shared['file'].resolve())) == shared['sha256']
                and evidence.get(str(shared['external_file'].resolve())) == shared['external_sha256']
                and fixed[3].stat().st_mtime >= shared['file'].stat().st_mtime,
                'Root proof/fresh saved readback must bind the exact shared dependency intake')
    victim = victim_decal_revision_rows(author, playback)
    verify_saved_victim_revision(victim, saved)
    if victim:
        require(str(victim['file'].resolve()) in evidence
                and evidence[str(victim['file'].resolve())] == victim['sha256']
                and proof.get('victim_decal_policy_revision_sha256') == victim['sha256']
                and fixed[3].stat().st_mtime >= victim['file'].stat().st_mtime,
                'Root proof/fresh saved readback must bind the exact victim revision')
    content_revision_file = OUT / 'Authoring/ContentRebaseRevision.json'
    if content_revision_file.exists():
        require(str(content_revision_file.resolve()) in evidence and evidence[str(content_revision_file.resolve())] == sha(content_revision_file),
                'Root proof must bind the exact six-definition content rebase')
        content_revision = load(content_revision_file)
        intake_file = evidence_path(content_revision['contentintake'])
        require(str(intake_file) in evidence and evidence[str(intake_file)] == content_revision['contentintake_sha256'] == sha(intake_file),
                'Root proof must bind the exact guarded content intake')
        rebased_definition_rows(author, playback, victim['sequences'] if victim else None)
        require(saved.get('content_rebase_revision_sha256') == sha(content_revision_file),
                'Fresh saved readback must verify the merged definitions')
    original_source = {p: h for p, h in baseline['main_sha256'].items() if p.startswith('Source/')}
    require(len(original_source) == 96 and inventory(OUT / 'BaselineSource', ('Source',)) == original_source,
            'Immutable original Main Source96 snapshot/backup changed')
    baseline_source = original_source
    source_intake_path = None
    if proof.get('main_rebase_intake'):
        intake_path = evidence_path(proof['main_rebase_intake'])
        source_intake_path = intake_path
        require(str(intake_path) in evidence, 'Explicit rebase intake must be bound by root integrity')
        intake = load(intake_path)
        require(intake.get('status') == 'passed' and intake.get('original_baseline_sha256') == sha(fixed[0]),
                'Rebase intake must retain and identify the immutable original baseline')
        baseline_source = intake['main_source']
        require(baseline_source and all(p.startswith('Source/') and HASH.fullmatch(h) for p, h in baseline_source.items()),
                'Invalid exact rebased Main source snapshot')
        backup_root = Path(intake['source_backup_root']).resolve()
        require(backup_root.is_relative_to(OUT.resolve()) and inventory(backup_root, ('Source',)) == baseline_source,
                'Explicit rebased Main source backup missing/changed')
    require(inventory(MAIN, ('Source',)) == baseline_source,
            'Main full Source changed; root must integrate/rebuild/reverify against an explicit new intake')
    require(author.get('status') == 'passed' and Path(author['project']).resolve() == WORK.resolve()
            and author.get('plan_sha256') == sha(fixed[1]), 'Private authoring is absent/stale/failed')
    require(not playback.get('blockers') and Path(playback['work']).resolve() == WORK.resolve(), 'Unresolved playback blockers')
    require(saved.get('status') == 'passed' and saved.get('all_checks_passed') is True
            and saved.get('all_selected_bytes_unchanged') is True and saved.get('asset_saves') == 0
            and saved.get('asset_mutations') == 0 and saved.get('mode') == 'private_read_only'
            and saved.get('plan_sha256') == sha(fixed[1]) and Path(saved['project']).resolve() == WORK.resolve(),
            'Fresh private saved readback did not pass')
    expected_events = {e['event_id'] for e in playback['events'] + playback.get('lifetime_sentinels', [])}
    binding_path = OUT / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json'
    if binding_path.exists():
        require(str(binding_path.resolve()) in evidence and evidence[str(binding_path.resolve())] == sha(binding_path),
                'Root proof must bind the current Apes material revision')
        binding = load(binding_path)
        require(binding.get('status') == 'passed' and binding.get('mode') == 'apply'
                and binding['plan_after_sha256'] == sha(fixed[1]) and binding['author_after_sha256'] == sha(fixed[2])
                and binding['original_main_before_journal_preserved'] and binding['source_schema_unchanged']
                and binding['asset_saves'] == 2 and binding['asset_mutations'] == 5,
                'Current exact five-state/two-package Apes revision is stale or failed')
    require(len(author['events']) == len(saved['events']) == len(expected_events)
            and {e['event_id'] for e in author['events']} == {e['event_id'] for e in saved['events']} == expected_events
            and all(e['fields_and_timing_equal'] for e in saved['events']), 'Exact authored/saved event coverage mismatch')
    require(saved['selected_asset_sha_before'] == saved['selected_asset_sha_after'], 'Saved audit mutated selected packages')
    require(len(art['assets']) == 457 and resource_audit.get('passed') is True
            and art.get('unexpected_reused_asset_changes') == [] and resource_audit['native_candidate_count'] == 457,
            'Current Art457/resource audit not passed')
    require(radius_revision.get('status') == 'passed' and len(radius_revision.get('materials', [])) == 2
            and radius_revision['native_adapter_map_before_sha256'] == radius_revision['native_adapter_map_after_sha256']
            and radius_revision['native_adapter_map_after_sha256'] == sha(RESOURCES / 'NativeAdapterMap.json'),
            'Immutable two-master raw-radius correction/adapter identity must pass')
    art_by_file = {a['relative_file']: a for a in art['assets']}
    require(all(art_by_file[m['relative_file']]['native_sha256'] == m['after_sha256']
                for m in radius_revision['materials']), 'Original radius revision master bytes changed')
    light_path = RESOURCES / 'LightUsageRevision.json'
    if light_path.exists():
        require(str(light_path.resolve()) in evidence and evidence[str(light_path.resolve())] == sha(light_path),
                'Root proof must bind the current light usage revision')
        light = load(light_path)
        require(light.get('status') == 'passed' and len(light.get('materials', [])) == 1
                and light['materials'][0]['relative_file'] == 'Content/_Art/Effects/Monsters/Light/M_MonsterLightOnly.uasset'
                and light['materials'][0]['usage_after'] is True
                and light['materials'][0]['after_sha256'] == art_by_file[light['materials'][0]['relative_file']]['native_sha256']
                and light['all_457_candidate_hashes_checked'] is True
                and light['execution_radius_revision_sha256'] == sha(fixed[6])
                and light['native_adapter_map_before_sha256'] == light['native_adapter_map_after_sha256']
                    == radius_revision['native_adapter_map_after_sha256']
                and light['art_candidate_manifest_before_sha256'] == radius_revision['art_candidate_manifest_sha256']
                and light['final_resource_audit_before_sha256'] == radius_revision['final_resource_audit_sha256']
                and light['art_candidate_manifest_sha256'] == sha(fixed[4])
                and light['final_resource_audit_sha256'] == sha(fixed[5])
                and light['radius_material_sha256_unchanged'] == {m['relative_file']: m['after_sha256'] for m in radius_revision['materials']},
                'Radius -> one-light usage revision -> current candidate integrity chain must pass')
    else:
        require(radius_revision['art_candidate_manifest_sha256'] == sha(fixed[4])
                and radius_revision['final_resource_audit_sha256'] == sha(fixed[5]),
                'Two-master raw-radius correction/current candidate bindings must pass')
    build_attempt, build_header = latest(OUT / 'Build')
    require(Path(proof['build_attempt']).resolve() == build_attempt, 'Root proof is not for latest successful build')
    build_paths = [build_header] + [evidence_path(build_attempt / n) for n in ('Exit.json', 'Launch.json', 'PrivateBuild.log')]
    build = load(build_paths[1])
    require(build.get('exit_code') == 0 and build.get('private_inputs_unchanged') is True and build.get('main_inputs_unchanged') is True
            and re.search(rb'(?m)^Result:\s*Succeeded\s*$', Path(build_paths[3]).read_bytes()), 'Latest cold build failed/changed inputs')
    for p in build_paths[1:]:
        require(str(p) in evidence and evidence[str(p)] == sha(p), 'Root proof does not bind latest build evidence')
    if source_intake_path:
        require(build_paths[2].stat().st_mtime >= source_intake_path.stat().st_mtime, 'Native build predates source intake')
    for root, field in ((MAIN, 'main_inputs'), (WORK, 'private_inputs')):
        current = inventory(root, ('Source', 'Config'))
        current['Khazan.uproject'] = sha(root / 'Khazan.uproject')
        require(current == build[field], 'Compiled full Source/Config/project changed: ' + str(root))
    private_source = {p: h for p, h in build['private_inputs'].items() if p.startswith('Source/')}
    if source_intake_path:
        verify_player_polish_source_intake(source_intake_path, private_source)
    changed = {p for p in set(private_source) | set(baseline_source) if private_source.get(p) != baseline_source.get(p)}
    require(changed == SOURCE, 'Only exact eleven task Source changes are allowed')
    require(set(build['native']) == {'UnrealEditor-Khazan.dll', 'UnrealEditor-Khazan.pdb', 'UnrealEditor.modules'}
            and proof['native'] == build['native'] and all(sha(WORK / 'Binaries/Win64' / n) == h for n, h in build['native'].items()),
            'Root/native/latest-build bytes mismatch')
    runtime_gate(OUT / 'PrivateMonsterRuntimePIE', 'Khazan.MonsterVisual.PIE', fixed[2], build_paths[1], evidence)
    runtime_gate(OUT / 'PrivatePlayerRegression', 'Khazan.CombatEffect.PIE', fixed[2], build_paths[1], evidence)
    for revision_file in [p for p in (content_revision_file, victim['file'] if victim else None,
                                    shared['file'] if shared else None, source_intake_path,
                                    material_revision['file'] if material_revision else None) if p and p.exists()]:
        for name in ('PrivateMonsterRuntimePIE', 'PrivatePlayerRegression', 'PrivateRimQA', 'PrivateYetugaQA'):
            attempt, _ = latest(OUT / name)
            require((attempt / 'Launch.json').stat().st_mtime >= revision_file.stat().st_mtime,
                    'Runtime launch predates exact asset revision: ' + name)
    visual = proof.get('visual_review') or {}
    if victim:
        require(visual.get('victim_decal_policy_revision_sha256') == victim['sha256'],
                'Actual PNG review belongs to a candidate before the victim revision')
    if shared:
        require(visual.get('shared_effects_rebase_revision_sha256') == shared['sha256'],
                'Actual PNG review belongs to a candidate before the shared dependency intake')
    if material_revision:
        require(visual.get('visual_material_repair_revision_sha256') == material_revision['sha256'],
                'Actual PNG review predates the exact visual material repair')
    monster_attempt, _ = latest(OUT / 'PrivateMonsterRuntimePIE')
    player_attempt, _ = latest(OUT / 'PrivatePlayerRegression')
    require(visual.get('status') == 'passed' and visual.get('visual_review_passed') is True
            and visual.get('art_candidate_manifest_sha256') == sha(fixed[4])
            and visual.get('authoring_sha256') == sha(fixed[2]) and visual.get('plan_sha256') == sha(fixed[1])
            and visual.get('monster_runtime_driver_sha256') == sha(monster_attempt / 'Driver.json')
            and visual.get('player_runtime_driver_sha256') == sha(player_attempt / 'Driver.json'),
            'Root visual review must bind actual current Art/author/plan/both RHI drivers')
    reviewed = visual.get('reviewed_images', [])
    require(reviewed and all(isinstance(r, dict) and {'path', 'sha256'} <= set(r) for r in reviewed), 'Reviewed PNG evidence missing')
    image_roots = set()
    for r in reviewed:
        image = evidence_path(r['path'])
        require(image.suffix.lower() == '.png' and sha(image) == r['sha256'], 'Reviewed PNG changed/missing')
        owner = next((a for a in (monster_attempt, player_attempt) if image.is_relative_to(a)), None)
        require(owner is not None, 'Reviewed image is outside current private RHI attempts')
        image_roots.add(owner); evidence[str(image)] = r['sha256']
    require(image_roots == {monster_attempt, player_attempt}, 'Review must include current Monster and Player PNGs')
    supplemental_attempts = {}
    for name in ('PrivateRimQA', 'PrivateYetugaQA'):
        attempt, header = latest(OUT / name)
        for p in [header] + [evidence_path(attempt / n) for n in ('Driver.json', 'Exit.json', 'Launch.json', 'PrivatePIE.log')]:
            require(str(p) in evidence and evidence[str(p)] == sha(p), 'Root must bind actual supplemental QA: ' + str(p))
        driver = load(attempt / 'Driver.json')
        require(driver['status'] == 'passed' and load(attempt / 'Exit.json')['exit_code'] == 0
                and driver['package_saves'] == driver['asset_mutations'] == 0
                and not driver.get('material_compile_failures') and driver['captures'], 'Supplemental QA failed: ' + name)
        require(driver['loaded_native_module']['sha256'] == build['native']['UnrealEditor-Khazan.dll']
                and driver['loaded_native_module']['manifest_sha256'] == build['native']['UnrealEditor.modules'],
                'Supplemental QA belongs to a different native build')
        require(visual['supplemental_driver_sha256'][name] == sha(attempt / 'Driver.json'), 'Supplemental visual binding changed')
        supplemental_attempts[name] = attempt
    supplemental_owners = set()
    for row in visual['reviewed_supplemental_images']:
        image = evidence_path(row['path'])
        require(image.suffix.lower() == '.png' and sha(image) == row['sha256'], 'Supplemental reviewed PNG changed')
        owner = next((n for n, a in supplemental_attempts.items() if image.is_relative_to(a)), None)
        require(owner is not None, 'Supplemental PNG outside current owned QA attempts')
        supplemental_owners.add(owner); evidence[str(image)] = row['sha256']
    require(supplemental_owners == set(supplemental_attempts), 'Both targeted Rim and Yetuga PNG reviews required')
    for p in fixed + [build_header]:
        evidence[str(p.resolve())] = sha(p)
    return baseline_source, private_source, playback, author, saved, art, evidence, build['native']


def visual_material_repair_revision(delivered=False):
    """Revalidate exact author receipts/current bytes; original manifests stay frozen."""
    file = OUT / 'Authoring/VisualMaterialRepairRevision.json'
    if not file.exists():
        return None
    revision = load(file)
    mirror = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json'
    require(sha(file) == sha(mirror), 'Visual material revision mirrors differ')
    receipts = revision.get('authoring_receipts', [])
    require(len(receipts) == 2 and len({r['path'] for r in receipts}) == 2,
            'Exact two material component receipts required')
    for row in receipts:
        require(sha(evidence_path(row['path'])) == row['sha256'], 'Material author receipt changed')
    decal = next((r for r in receipts if load(r['path']).get('schema') == 'Khazan.MonsterVFX.DecalMaterialVisualRepair.v1'), None)
    wpo = next((r for r in receipts if load(r['path']).get('schema') == 'Khazan.MonsterVFX.Roar02MaterialVisualRepair.v1'), None)
    require(decal and wpo, 'Decal2/Roar02 component identity missing')
    assembler = MAIN / 'Scripts/Art/finalize_monster_vfx_visual_material_revision_20261010.py'
    A = runpy.run_path(str(assembler), run_name='visual_material_revision_readonly_assembler')
    expected = A['assemble'](decal['path'], decal['sha256'], wpo['path'], wpo['sha256'], delivered=delivered)
    require({k: v for k, v in revision.items() if k != 'utc'} == {k: v for k, v in expected.items() if k != 'utc'},
            'Joint material revision differs from exact original/receipt/backup/source/native proof')
    rows = {r['relative']: r for r in revision['rows']}
    require(len(rows) == 3 and len([r for r in rows.values() if r['kind'] == 'OriginalArtOverride']) == 2
            and len([r for r in rows.values() if r['kind'] == 'ReusedMaterialDependency']) == 1,
            'Only exact two own Art masters and one reused dependency are permitted')
    return {'file': file, 'sha256': sha(file), 'report': revision, 'rows': rows,
            'receipts': receipts, 'decal': load(decal['path']), 'wpo': load(wpo['path']),
            'art_after_sha256': revision['art_after_sha256'], 'reuse_after_sha256': revision['reuse_after_sha256']}


def verify_saved_visual_revision(visual, saved):
    if not visual:
        require('visual_material_repair_revision_sha256' not in saved, 'Unexpected saved visual repair marker')
        return
    expected = {p: r['after_sha256'] for p, r in visual['rows'].items()}
    rows = {r['relative']: r for r in saved.get('visual_material_repair_readbacks', [])}
    require(saved.get('visual_material_repair_revision_sha256') == visual['sha256']
            and saved.get('visual_material_repair_sha_before') == saved.get('visual_material_repair_sha_after') == expected
            and saved.get('visual_material_repair_bytes_unchanged') is True
            and len(rows) == len(saved.get('visual_material_repair_readbacks', [])) == 3 and set(rows) == set(expected)
            and all(r.get('fields_and_links_equal') is True and r['sha256'] == expected[p] for p, r in rows.items())
            and saved['asset_saves'] == saved['asset_mutations'] == 0,
            'Fresh saved readback must prove exact three repaired materials without mutation')
    for relative, row in rows.items():
        code = visual['decal']['hlsl'] if visual['rows'][relative]['kind'] == 'OriginalArtOverride' else visual['wpo']['hlsl']
        require(row.get('custom_code_sha256') == hashlib.sha256(code.encode('utf-8')).hexdigest(),
                'Saved repaired shader code differs: ' + relative)


def shared_effects_rebase_revision(delivered=False):
    """Validate the separate shared dependency intake; the 457 delta is immutable."""
    file = OUT / 'Authoring/SharedEffectsRebaseRevision.json'
    external_file = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json'
    if not file.exists() and not external_file.exists():
        return None
    require(file.is_file() and external_file.is_file(), 'External shared changes require their explicit intake receipt')
    revision, external = load(file), load(external_file)
    require(revision.get('schema') == 'Khazan.MonsterVFX.SharedEffectsRebaseRevision.v1'
            and revision.get('status') == 'passed' and revision.get('mode') == 'apply'
            and revision['main_mutations'] == revision['package_saves'] == revision['new_native_resources'] == 0
            and revision['content_scope'] == revision['content_files_copied'] == 14
            and revision['main_source_config_uproject_unchanged'] is True
            and revision['original_reports_unchanged'] is True
            and revision['fresh_monster_vfx_saved_and_runtime_validation_required'] is True
            and revision['main_input_before_sha256'] == revision['main_input_after_sha256'],
            'Invalid bounded shared dependency intake receipt')
    mirror = WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json'
    require(sha(mirror) == sha(file), 'Shared intake Main/private receipt mirrors differ')
    ext = revision['external_delivery']
    require(Path(ext['path']).resolve() == external_file.resolve() and ext['sha256'] == sha(external_file)
            and ext['status'] == external['status'] == 'SelectedPolishDeliveredFreshMainValidationPending'
            and ext['fresh_Main_actual_RHI_and_saved_audits_required'] is True
            and external['fresh_Main_actual_RHI_and_saved_audits_required'] is True,
            'External delivery identity/pending fresh validation boundary changed')
    external_dir = external_file.parent
    prepared_file, approval_file = external_dir / 'Prepared.json', external_dir / 'RootApproval.json'
    prepared, approval = load(prepared_file), load(approval_file)
    frozen = prepared['frozen_manifest']
    frozen_file = target(external_dir.parent, frozen['path'])
    require(ext['prepared_sha256'] == external['prepared_sha256'] == sha(prepared_file)
            and ext['approval_sha256'] == external['approval_sha256'] == sha(approval_file)
            and approval['approved'] is True and approval['prepared_sha256'] == sha(prepared_file)
            and frozen['sha256'] == sha(frozen_file), 'External frozen staging/approval chain changed')
    immutable_paths = [OUT / 'WorkBaseline.json'] + [RESOURCES / name for name in
        ('ArtCandidateManifest.json', 'UnionAssetManifest.json', 'FinalResourceAudit.json', 'NativeAdapterMap.json',
         'ExecutionRadiusRevision.json', 'LightUsageRevision.json')] + [external_file, prepared_file, approval_file, frozen_file]
    immutable = {str(p): sha(p) for p in immutable_paths}
    require(revision['immutable_report_sha256'] == immutable
            and all(HASH.fullmatch(h or '') for h in immutable.values()), 'Original resource/external evidence changed')
    baseline = {p: h for p, h in load(OUT / 'WorkBaseline.json')['main_sha256'].items()
                if p.startswith('Content/_Art/Effects/')}
    require(len(baseline) == 2034, 'Original shared Effects baseline scope changed')
    external_rows = {r['file']: r for r in external['files'] if r['file'].startswith('Content/')}
    rows = {r['relative']: r for r in revision['rows']}
    require(len(rows) == len(revision['rows']) == len(external_rows) == 14 and set(rows) == set(external_rows)
            and len(external['files']) == 17 and prepared['files'] == external['files'], 'Shared intake exceeds exact external Art14')
    art = load(RESOURCES / 'ArtCandidateManifest.json')
    art_rows = {r['relative_file']: r for r in art['assets']}
    require(len(art_rows) == len(art['assets']) == 457 and not set(rows) & set(art_rows),
            'Shared intake overlaps or changes the original 457 Art delta')
    union = {r['destination']: r for r in load(RESOURCES / 'UnionAssetManifest.json')}
    for relative, row in rows.items():
        original = baseline.get(relative)
        expected = external_rows[relative]
        source = union.get('/Game/' + relative.removeprefix('Content/').removesuffix('.uasset'))
        require(original and row['prior_private_sha256'] == row['original_main_before_sha256']
                == row['backup_sha256'] == row['external_selected_before_sha256'] == expected['before'] == original
                and row['main_before_sha256'] == row['after_sha256'] == row['external_selected_after_sha256'] == expected['after']
                and HASH.fullmatch(row['after_sha256']) and row['after_sha256'] != original,
                'Shared original/external byte provenance differs: ' + relative)
        require(source and source['reused_native'] is True and row['reused_native'] is True
                and all(row[k] == source[k] for k in ('source_package', 'source_json', 'source_sha256'))
                and sha(target(MAIN, row['source_json'])) == row['source_sha256'], 'Shared original metadata differs: ' + relative)
        backup = target(OUT / 'Authoring/SharedEffectsRebaseRevision/ImmutableBeforePrivate', relative)
        require(Path(row['backup_path']).resolve() == backup and sha(backup) == original, 'Shared original backup changed: ' + relative)
    after = dict(baseline, **{p: r['after_sha256'] for p, r in rows.items()})
    audit = revision['reuse_audit']
    require(audit['count'] == 2034 and audit['intentional_updates'] == 14 and audit['unchanged_count'] == 2020
            and audit['main_after_sha256'] == audit['private_after_sha256'] == after,
            'Shared 2034 receipt does not equal exact14 plus unchanged2020')
    visual = visual_material_repair_revision(delivered=delivered)
    actual_after = visual['reuse_after_sha256'] if visual else after
    require(all(sha(target(WORK, p)) == h for p, h in actual_after.items())
            and all(sha(target(MAIN, p)) == h for p, h in (actual_after if delivered else after).items()),
            'Current Main/private shared bytes differ from exact historical14 plus bounded visual repair')
    original_art = {p: r['native_sha256'] for p, r in art_rows.items()}
    require(revision['art457']['count'] == 457 and revision['art457']['hashes_unchanged'] is True
            and revision['art457']['main_before_cas_unchanged'] is True
            and revision['art457']['original_sha256'] == original_art
            and all(sha(target(WORK, p)) == h for p, h in (visual['art_after_sha256'] if visual else original_art).items())
            and all(sha(target(MAIN, p)) == ((visual['art_after_sha256'][p] if visual else r['native_sha256'])
                    if delivered else r['before_main_sha256']) for p, r in art_rows.items()),
            'Original 457 history/current bounded overrides/Main CAS changed')
    return {'file': file, 'sha256': sha(file), 'report': revision, 'external_file': external_file,
            'external_sha256': sha(external_file), 'rows': rows, 'after_sha256': actual_after,
            'visual_revision': visual}


def verify_saved_shared_revision(shared, saved):
    if not shared:
        require('shared_effects_rebase_revision_sha256' not in saved, 'Unexpected shared saved marker')
        return
    require(saved.get('shared_effects_rebase_revision_sha256') == shared['sha256']
            and saved.get('shared_dependency_bytes_unchanged') is True
            and saved.get('shared_dependency_sha_before') == saved.get('shared_dependency_sha_after') == shared['after_sha256']
            and saved['asset_saves'] == saved['asset_mutations'] == 0,
            'Fresh saved readback does not bind exact current shared2034 dependency bytes')


def verify_player_polish_source_intake(file, private_source):
    """Bind the exact semantic Source intake without declaring external QA complete."""
    if Path(file).resolve() != (OUT / 'MainRebase/PlayerPolishSourceIntake.json').resolve():
        return
    intake = load(file)
    require(intake.get('schema') == 'Khazan.MonsterVFX.PlayerPolishSourceIntake.v1'
            and intake.get('status') == 'passed' and intake['original_baseline_sha256'] == sha(OUT / 'WorkBaseline.json')
            and intake['main_source_writes'] == intake['asset_writes'] == 0 and intake['private_source_writes'] == 4
            and intake['editor_or_build_control'] is False and intake['build_or_runtime_verified_after_intake'] is False
            and intake['original_intake_receipts_preserved'] is True
            and intake['private_config_project_preserved'] is True and intake['main_inputs_preserved'] is True
            and all(intake['manual_review'].values()), 'Invalid pending-verification PlayerPolish source intake')
    prior = intake['prior_main_rebase_intake']
    require(Path(prior['path']).resolve() == (OUT / 'MainRebase/BrutalInputSourceIntake.json').resolve()
            and sha(evidence_path(prior['path'])) == prior['sha256'], 'Prior source intake changed')
    main_source = intake['main_source']
    require(len(main_source) == 98 and len(private_source) == 101 and intake['private_source_after'] == private_source
            and {p for p in set(main_source) | set(private_source) if main_source.get(p) != private_source.get(p)} == SOURCE,
            'PlayerPolish merged Source no longer preserves exact task delta11')
    for field, hashes in (('source_backup_root', main_source), ('private_backup_root', intake['private_source_before'])):
        root = Path(intake[field]).resolve()
        require(root.is_relative_to((OUT / 'MainRebase/PlayerPolish').resolve())
                and inventory(root, ('Source',)) == hashes, 'PlayerPolish full Source backup changed')
    ext = intake['raw_source3_delivery']
    external_file = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json'
    external = load(external_file)
    original_rows = [r for r in external['files'] if r['file'].startswith('Source/')]
    require(Path(ext['path']).resolve() == external_file.resolve() and ext['sha256'] == sha(external_file)
            and ext['status'] == external['status'] == 'SelectedPolishDeliveredFreshMainValidationPending'
            and ext['fresh_main_final_verification_pending'] is True and ext['rows'] == original_rows
            and ext['prepared_sha256'] == external['prepared_sha256'] and len(original_rows) == 3
            and all(main_source[r['file']] == r['after'] for r in original_rows), 'External raw Source3 intake binding changed')
    rows = {r['file']: r for r in intake['rows']}
    require(len(rows) == len(intake['rows']) == 4 and set(rows) == {
        'Source/Khazan/Ability/KZActionAbility.h', 'Source/Khazan/Ability/KZActionAbility.cpp',
        'Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp', 'Source/Khazan/Tests/KZCombatEffectPIETest.cpp'}
            and all(r['main_sha256'] == main_source[p] and r['private_before_sha256'] == intake['private_source_before'][p]
                    and r['private_after_sha256'] == private_source[p] for p, r in rows.items())
            and private_source['Source/Khazan/Ability/KZActionAbility.h'] == main_source['Source/Khazan/Ability/KZActionAbility.h'],
            'Exact Source4 merge/header reuse receipt changed')
    schema = intake['source_schema_unchanged']
    require(Path(schema['path']).resolve() == (MAIN / 'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json').resolve()
            and sha(schema['path']) == schema['sha256'], 'Current runtime serialized schema changed')


def original_author_rows(author, playback):
    """Validate the immutable 499-package journal before considering any revision."""
    expected_sequences = {e['asset'] for e in playback['events'] + playback.get('lifetime_sentinels', [])}
    require(len(author['sequences']) == 487 and {s['path'] for s in author['sequences']} == expected_sequences,
            'Original exact sequence scope differs from the plan')
    rows = {}
    for s in author['sequences']:
        relative = s['relative']
        require(relative == 'Content/' + s['path'].removeprefix('/Game/') + '.uasset'
                and relative in playback['asset_baseline'] and 'Animations' in Path(relative).parts
                and (relative.startswith('Content/_Art/Enemies/') or relative.startswith('Content/Monsters/')),
                'Unapproved original sequence destination')
        require(s['before_sha256'] == playback['asset_baseline'][relative], 'Original sequence baseline differs from plan')
        rows[relative] = (s['before_sha256'], s['after_sha256'])
    deaths = author['death_presentations']
    require(len(deaths) == 6 and {d['family'] for d in deaths} == FAMILIES, 'Original death scope differs')
    expected_death = {f'Content/Monsters/{f}/{tail}' for f in FAMILIES for tail in
                      (f'Data/DA_Character_{f}.uasset', f'Animations/AM_DeathPresentation_{f}.uasset')}
    death_rows = {}
    for d in deaths:
        require(d['existing_settings_preserved'] and d['definition_all_other_fields_preserved'],
                'Original death author changed unrelated settings')
        death_rows[d['definition_relative']] = (d['definition_before_sha256'], d['definition_after_sha256'])
        death_rows[d['montage_relative']] = (None, d['montage_after_sha256'])
    require(set(death_rows) == expected_death, 'Unapproved original death scope')
    rows.update(death_rows)
    journal = {j['relative']: j for j in author['mutation_journal']}
    require(len(rows) == len(journal) == len(author['mutation_journal']) == 499 and set(journal) == set(rows),
            'Original mutation journal differs from exact 499 whitelist')
    for relative, (before, after) in rows.items():
        j = journal[relative]
        require(j['path'] == '/Game/' + relative.removeprefix('Content/').removesuffix('.uasset')
                and j['before_sha256'] == before and j['saved_sha256'] == after and HASH.fullmatch(after),
                'Original journal saved/before/path mismatch: ' + relative)
        if before is not None:
            require(j['backup_sha256'] == before and sha(evidence_path(j['backup_path'])) == before,
                    'Original Main package backup changed: ' + relative)
    return rows


def rebased_definition_rows(author, playback, victim_sequences=None, verify_current=True):
    file = OUT / 'Authoring/ContentRebaseRevision.json'
    if not file.exists():
        return {}
    revision = load(file)
    require(revision.get('status') == 'passed' and revision.get('mode') == 'apply'
            and revision['author_before_sha256'] == sha(OUT / 'Authoring/PrivateAuthoring.json')
            and revision['original_baseline_sha256'] == sha(OUT / 'WorkBaseline.json')
            and revision['plan_sha256'] == sha(OUT / 'PreparedPlaybackPlan.json')
            and revision['original_author_journal_preserved'] and revision['original_reports_unchanged']
            and revision['untouched493_sha_preserved'] and revision['main_mutations'] == 0
            and revision['package_saves'] == revision['asset_mutations'] == 6,
            'Invalid six-definition rebase receipt')
    rows = {r['relative']: r for r in revision['rows']}
    original = {d['definition_relative']: d for d in author['death_presentations']}
    require(len(rows) == 6 and set(rows) == set(original), 'Definition rebase exceeds the exact six original consumers')
    for relative, row in rows.items():
        old = original[relative]
        require(row['original_main_before_sha256'] == old['definition_before_sha256']
                and row['prior_private_sha256'] == old['definition_after_sha256']
                and row['all_other_definition_fields_preserved'], 'Rebase does not preserve original definition provenance')
        require(sha(evidence_path(row['main_backup_path'])) == row['main_before_sha256']
                and sha(evidence_path(row['private_backup_path'])) == row['prior_private_sha256'],
                'Definition rebase exact before backups changed')
        if verify_current:
            require(sha(target(WORK, relative)) == row['merged_after_sha256'], 'Merged private definition changed')
    original_after = {j['relative']: j['saved_sha256'] for j in author['mutation_journal'] if j['relative'] not in rows}
    require(len(original_after) == 493 and revision['untouched493_sha256'] == original_after,
            'Immutable rebase untouched493 table differs from the original journal')
    if verify_current:
        overrides = victim_sequences or {}
        require(set(overrides) <= set(original_after)
                and all(sha(target(WORK, p)) == (overrides[p]['after_sha256'] if p in overrides else h)
                        for p, h in original_after.items()),
                'One of the other 493 packages differs beyond the explicit victim revision')
    return rows


def victim_decal_revision_rows(author, playback, verify_current=True):
    """One disclosed bool revision; original plan/author/rebase receipts stay immutable."""
    original = original_author_rows(author, playback)
    file = OUT / 'Authoring/VictimDecalPolicyRevision.json'
    if not file.exists():
        return None
    revision = load(file)
    require(revision.get('schema') == 'Khazan.MonsterVFX.VictimDecalPolicyRevision.v1'
            and revision.get('status') == 'passed' and revision.get('mode') == 'apply'
            and Path(revision['project']).resolve() == WORK.resolve()
            and revision['original_author_sha256'] == sha(OUT / 'Authoring/PrivateAuthoring.json')
                == 'fe268dad08bd3e34b33671be6307e641a7b95bf1c318e08ad6a4ef0c928e80c0'
            and revision['original_plan_sha256'] == sha(OUT / 'PreparedPlaybackPlan.json')
                == 'aee394cf819993a74d7113b7b778638f69e5365faa46b585999dc36a15861bca'
            and revision['expected43'] == revision['asset_mutations'] == 43
            and revision['expected_sequence_count'] == revision['package_saves'] == revision['asset_saves'] == 26
            and revision['main_mutations'] == 0 and revision['unchanged_author_asset_count'] == 473
            and all(revision[k] is True for k in ('other_author_assets_unchanged', 'original_reports_unchanged',
                    'original_author_journal_preserved', 'only43_subobject_bool_changes', 'fresh_saved_audit_required')),
            'Victim Decal revision contract is absent, failed, or stale')
    probe_file = evidence_path(OUT / 'Authoring/VictimDecalPolicyRevision/Probe.json')
    probe = load(probe_file)
    require(revision['script_sha256'] == sha(MAIN / 'Scripts/Art/monster_vfx_victim_decal_policy_revision_20261010.py')
            and sha(probe_file) == revision['probe_sha256'] and probe.get('status') == 'passed'
            and probe.get('mode') == 'probe' and probe.get('transient_only_probe') is True
            and probe['script_sha256'] == revision['script_sha256']
            and probe['immutable_report_sha256'] == revision['immutable_report_sha256']
            and probe['selected499_before_sha256'] == revision['selected499_before_sha256']
            and probe['loaded_native_module']['sha256'] == revision['loaded_native_module']['sha256']
            and sha(evidence_path(OUT / 'Authoring/VictimDecalPolicyRevision/Applied.json')) == sha(file)
            and sha(WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json') == sha(file),
            'Victim apply/probe/script/private-mirror provenance differs')
    immutable = [OUT / 'PreparedPlaybackPlan.json', OUT / 'Authoring/PrivateAuthoring.json',
        OUT / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json', OUT / 'Authoring/ContentRebaseRevision.json',
        OUT / 'Authoring/ContentRebaseRevision/IntakePlan.json', OUT / 'Authoring/ContentRebaseRevision/IntakeApplied.json',
        WORK / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json',
        WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/PrivateAuthoring.json',
        WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/ApesCurrentMaterialBindingRevision.json']
    immutable += [MAIN / ('Scripts/Art/' + n) for n in ('player_attack_vfx_author.py',
                  'monster_vfx_author_20261008.py', 'prepare_monster_vfx_plan_20261008.py')]
    expected_immutable = {str(p): sha(p) for p in immutable}
    expected_immutable.update(playback['source_inputs'])
    require(revision['immutable_report_sha256'] == expected_immutable
            and all(HASH.fullmatch(h or '') and sha(p) == h for p, h in expected_immutable.items()),
            'Original receipts/helpers/source inputs changed after victim revision')
    planned = {e['event_id']: e for e in playback['events'] if e.get('effect_fields', {}).get('bOnAttackSuccessed') is True}
    ids_sha = hashlib.sha256(json.dumps(sorted(planned), separators=(',', ':')).encode()).hexdigest()
    require(len(planned) == 43 and revision['target_event_ids_sha256'] == ids_sha
            == 'c0e8384053dc16c8752b6aaac6c2073d579aaa6e74baa7caa1760673b7ae4068'
            and all(e['category'] in ('Damage', 'Death') and e['notify_type'] == 'xxAnimNotifyState_Decal'
                    and 'DecalLifeSpan' in e['effect_fields'] for e in planned.values()),
            'Victim revision exceeds the original exact 43 Damage/Death Decal windows')
    events = {e['event_id']: e for e in revision['events']}
    original_events = {e['event_id']: e for e in author['events']}
    require(len(events) == len(revision['events']) == 43 and set(events) == set(planned), 'Victim event whitelist differs')
    f32 = lambda v: struct.unpack('f', struct.pack('f', v))[0]
    for event_id, row in events.items():
        old, plan = original_events[event_id], planned[event_id]
        require(old['effect_fields'] == plan['effect_fields'] and old['state_fields'] == plan['state_fields']
                and row['asset'] == old['asset'] and row['guid'] == old['guid']
                and row['before_effect_fields'] == old['effect_fields']
                and row['after_effect_fields'] == dict(old['effect_fields'], bOnAttackSuccessed=False)
                and row['before_effect_readback'] == old['effect_readback']
                and row['after_effect_readback'] == dict(old['effect_readback'], bOnAttackSuccessed=False)
                and row['before_effect_field'] == {'bOnAttackSuccessed': True}
                and row['after_effect_field'] == {'bOnAttackSuccessed': False}
                and row['state_fields'] == old['state_fields']
                and row['before_state_readback'] == row['after_state_readback'] == old['state_readback']
                and row['all_other_effect_fields_unchanged'] is True and row['state_fields_timing_guid_unchanged'] is True,
                'Victim revision changes other fields/source evidence: ' + event_id)
        timing = row['before_notify_event_readback']
        require(timing == row['after_notify_event_readback'] and timing['guid'] == old['guid']
                and timing['trigger'] == old['start_time'] and timing['duration'] == f32(old['end_time'] - old['start_time'])
                and timing['end_link_value'] == f32(round(old['end_time'], 6))
                and row['effect_path'].startswith(old['asset'] + '.'), 'Victim notify identity/timing changed: ' + event_id)
    source_rows = {e['event_id']: e for e in revision['source_absent_field_evidence43']}
    require(len(source_rows) == len(revision['source_absent_field_evidence43']) == 43 and set(source_rows) == set(planned),
            'Exact source-absent/CDO-unknown evidence missing')
    for event_id, event in planned.items():
        source, row = event['source'], source_rows[event_id]
        if 'source_file' in source:
            path = MAIN / source['source_file']; payload = path.read_bytes()
            require(row['source_file'] == str(path), 'Source JSON path changed')
        else:
            path = MAIN / source['source_zip']
            require(row['source_zip'] == str(path) and row['source_zip_sha256'] == sha(path)
                    and row['source_zip_entry'] == source['source_zip_entry'], 'Source ZIP identity changed')
            with zipfile.ZipFile(path) as archive:
                payload = archive.read(source['source_zip_entry'])
        raw = json.loads(payload); exports = raw if isinstance(raw, list) else raw['Exports']
        index = int(source['raw_notify']['NotifyStateClass']['ObjectPath'].rsplit('.', 1)[1]); entry = exports[index]
        require(hashlib.sha256(payload).hexdigest() == source['source_sha256'] == row['source_sha256']
                and row['asset'] == event['asset'] and row['source_package'] == source['source_package']
                and row['source_export_index'] == index and row['source_export_name'] == entry['Name']
                and row['source_notify_field'] == source['field'] and entry['Type'] == 'xxAnimNotifyState_Decal'
                and entry['Properties'] == source['properties'] and 'bOnAttackSuccessed' not in entry['Properties']
                and row['raw_property_keys'] == sorted(entry['Properties'])
                and row['serialized_bOnAttackSuccessed_present'] is False
                and row['original_cdo_condition'].startswith('Unknown:'), 'Original source-absent evidence changed: ' + event_id)
    sequences = {r['relative']: r for r in revision['sequences']}
    authored = {s['relative']: s for s in author['sequences']}
    wanted = {authored_path['relative'] for authored_path in author['sequences']
              if authored_path['path'] in {e['asset'] for e in planned.values()}}
    require(len(sequences) == len(revision['sequences']) == 26 and set(sequences) == wanted, 'Victim sequence scope differs')
    for relative, row in sequences.items():
        old = authored[relative]; count = sum(e['asset'] == old['path'] for e in planned.values())
        require(row['asset'] == row['path'] == old['path'] and row['prior_private_sha256'] == row['backup_sha256'] == old['after_sha256']
                and HASH.fullmatch(row['after_sha256']) and row['after_sha256'] != old['after_sha256']
                and sha(evidence_path(row['backup_path'])) == old['after_sha256']
                and row['raw_pose_curves_settings_notifies_unchanged'] is True and row['other_state_fields_preserved'] is True
                and row['revised_effect_count'] == count, 'Victim package provenance/preservation differs: ' + relative)
        texts = []
        for name in ('before_export', 'after_export', 'after_saved_export'):
            path = evidence_path(row[name + '_path'])
            require(sha(path) == row[name + '_sha256'], 'Victim exact export changed: ' + str(path))
            texts.append(read(path))
        require(texts[1] == texts[2], 'Save changed victim serialized fields')
        before_lines, after_lines = texts[0].splitlines(), texts[1].splitlines(); deleted, inserted = [], []
        for tag, i, j, k, l in difflib.SequenceMatcher(None, before_lines, after_lines, autojunk=False).get_opcodes():
            if tag != 'equal':
                deleted.extend(before_lines[i:j]); inserted.extend(after_lines[k:l])
        require(len(deleted) == count and all(v.strip() == 'bOnAttackSuccessed=True' for v in deleted)
                and len(inserted) <= count and all(v.strip() == 'bOnAttackSuccessed=False' for v in inserted)
                and row['exact_guard_only_serialized_diff'] == {'removed_true_lines': count, 'inserted_false_lines': len(inserted),
                    'only_exact_guard_property_changed': True, 'default_false_may_be_omitted_by_exporter': True},
                'Victim T3D contains changes beyond the exact guard property: ' + relative)
    rebased = rebased_definition_rows(author, playback, sequences, verify_current=False)
    expected_before = {j['path']: j['saved_sha256'] for j in author['mutation_journal']}
    expected_before.update({r['definition']: r['merged_after_sha256'] for r in rebased.values()})
    expected_after = dict(expected_before, **{r['asset']: r['after_sha256'] for r in sequences.values()})
    require(revision['selected499_before_sha256'] == expected_before and revision['selected499_after_sha256'] == expected_after,
            'Victim selected499 receipt differs from original author plus exact revisions')
    if verify_current:
        require(all(sha(target(WORK, 'Content/' + p.removeprefix('/Game/') + '.uasset')) == h
                    for p, h in expected_after.items()), 'Current private selected499 differs from victim/rebase receipts')
        rebased_definition_rows(author, playback, sequences)
    return {'file': file, 'sha256': sha(file), 'report': revision, 'events': events, 'sequences': sequences}


def verify_saved_victim_revision(victim, saved):
    if victim is None:
        require('victim_decal_policy_revision_sha256' not in saved, 'Unexpected victim saved marker')
        return
    require(saved.get('victim_decal_policy_revision_sha256') == victim['sha256']
            and saved.get('victim_decal_policy_verified_event_count') == 43
            and saved.get('victim_decal_policy_verified_sequence_count') == 26, 'Fresh saved victim revision marker/count missing')
    events = {e['event_id']: e for e in saved['events'] if e.get('victim_decal_policy_verified') is True}
    require(len(events) == 43 and set(events) == set(victim['events'])
            and all(e.get('bOnAttackSuccessed') is False and e.get('original_bOnAttackSuccessed') is True
                    and e['fields_and_timing_equal'] is True for e in events.values()), 'Fresh exact43 bool readbacks missing')
    sequences = {s['relative']: s for s in saved['sequences']}
    require(all(sequences[p]['sha256'] == r['after_sha256'] for p, r in victim['sequences'].items())
            and saved['selected_asset_sha_before'] == saved['selected_asset_sha_after']
                == victim['report']['selected499_after_sha256'], 'Fresh saved selected499/sequence26 hashes differ')


def selected_rows(baseline_source, private_source, playback, author, saved, art, verify_current=True, delivered=False):
    rows = [{'file': p, 'before': baseline_source.get(p), 'after': private_source[p], 'kind': 'Source'} for p in sorted(SOURCE)]
    expected_author = original_author_rows(author, playback)
    victim = victim_decal_revision_rows(author, playback)
    verify_saved_victim_revision(victim, saved)
    expected_sequences = {e['asset'] for e in playback['events'] + playback.get('lifetime_sentinels', [])}
    require({s['path'] for s in author['sequences']} == expected_sequences
            and {s['path'] for s in saved['sequences']} == expected_sequences, 'Author/saved exact sequence scope differs')
    expected_death = {f'Content/Monsters/{f}/{tail}' for f in FAMILIES for tail in
                      (f'Data/DA_Character_{f}.uasset', f'Animations/AM_DeathPresentation_{f}.uasset')}
    sequence_rows = {}
    for s in author['sequences']:
        relative = s['relative']
        require(relative == 'Content/' + s['path'].removeprefix('/Game/') + '.uasset'
                and relative in playback['asset_baseline'] and 'Animations' in Path(relative).parts
                and (relative.startswith('Content/_Art/Enemies/') or relative.startswith('Content/Monsters/')),
                'Unapproved sequence destination')
        require(s['before_sha256'] == playback['asset_baseline'][relative], 'Sequence baseline differs from plan')
        sequence_rows[relative] = (s['before_sha256'], s['after_sha256'])
    death_rows = {}
    require(len(author['death_presentations']) == len(saved['death_presentations']) == 6
            and {d['family'] for d in author['death_presentations']} == FAMILIES, 'Exactly six family death presentations required')
    for d in author['death_presentations']:
        require(d['existing_settings_preserved'] and d['definition_all_other_fields_preserved'], 'Death author changed unrelated settings')
        death_rows[d['definition_relative']] = (d['definition_before_sha256'], d['definition_after_sha256'])
        death_rows[d['montage_relative']] = (None, d['montage_after_sha256'])
    require(set(death_rows) == expected_death, 'Unapproved death definition/montage scope')
    require(expected_author == {**sequence_rows, **death_rows}, 'Original selected row declarations differ')
    rebased = rebased_definition_rows(author, playback, victim['sequences'] if victim else None)
    for relative, (before, after) in expected_author.items():
        revised = rebased.get(relative)
        victim_sequence = victim['sequences'].get(relative) if victim else None
        rows.append({'file': relative, 'before': revised['main_before_sha256'] if revised else before,
                     'after': (revised['merged_after_sha256'] if revised else
                               victim_sequence['after_sha256'] if victim_sequence else after), 'kind': 'Authoring'})
    material_revision = visual_material_repair_revision(delivered=delivered)
    verify_saved_visual_revision(material_revision, saved)
    for a in art['assets']:
        relative = a['relative_file']
        require(relative.startswith('Content/_Art/Effects/') and relative.endswith('.uasset')
                and Path(a['file']).resolve() == target(WORK, relative) and a['source_package'] and HASH.fullmatch(a['source_sha256']),
                'Invalid exact Art candidate provenance/path')
        revised = material_revision['rows'].get(relative) if material_revision else None
        rows.append({'file': relative, 'before': a['before_main_sha256'],
                     'after': revised['after_sha256'] if revised else a['native_sha256'], 'kind': 'Art',
                     'source_package': a['source_package'], 'source_sha256': a['source_sha256']})
    if material_revision:
        dependency = next(r for r in material_revision['rows'].values() if r['kind'] == 'ReusedMaterialDependency')
        rows.append({'file': dependency['relative'], 'before': dependency['before_main_sha256'],
                     'after': dependency['after_sha256'], 'kind': 'ReusedMaterialDependency',
                     'source_sha256': dependency['source_sha256']})
    require(len(rows) == len({r['file'] for r in rows}), 'Selected destinations collide')
    require(len(rows) == (968 if material_revision else 967), 'Exact selected Source11/Author499/Art457/dependency scope differs')
    for r in rows:
        require(HASH.fullmatch(r['after']), 'Invalid selected candidate SHA')
        if verify_current:
            require(sha(target(WORK, r['file'])) == r['after'] and sha(target(MAIN, r['file'])) == r['after' if delivered else 'before'],
                    'Current Main/private selected CAS mismatch: ' + r['file'])
    return rows


def prepare(args):
    require(not PLAN.exists() and not RECEIPT.exists(), 'Retain prior preparation/delivery; do not overwrite it')
    require(args.main_pid >= 0 and (args.main_pid > 0 or args.world == NO_EDITOR_WORLD), 'Closed editor/world identity mismatch')
    initial = census(); census_gate(initial, args.main_pid)
    baseline, private, playback, author, saved, art, evidence, native = inputs(args)
    rows = selected_rows(baseline, private, playback, author, saved, art)
    for r in rows:
        copy_immutable(target(WORK, r['file']), target(DELIVERY / 'Prepared', r['file']), r['after'])
        if r['before'] is not None:
            copy_immutable(target(MAIN, r['file']), target(DELIVERY / 'Before', r['file']), r['before'])
    manifest = target(MAIN, 'Binaries/Win64/UnrealEditor.modules')
    modules, private_modules = load(manifest), load(WORK / 'Binaries/Win64/UnrealEditor.modules')
    require(modules['BuildId'] == private_modules['BuildId'] == BUILD_ID
            and private_modules['Modules']['Khazan'] == 'UnrealEditor-Khazan.dll', 'Installed-engine/private modules mismatch')
    alias = 'UnrealEditor-KhazanMonsterVFX20261008'; suffix = 0
    while any((MAIN / 'Binaries/Win64' / (alias + ext)).exists() for ext in ('.dll', '.pdb')):
        suffix += 1; alias = 'UnrealEditor-KhazanMonsterVFX20261008_' + str(suffix)
    native_rows = []
    for extension in ('.dll', '.pdb'):
        source = 'Binaries/Win64/UnrealEditor-Khazan' + extension
        expected = native['UnrealEditor-Khazan' + extension]
        copy_immutable(target(WORK, source), target(DELIVERY / 'Prepared', source), expected)
        native_rows.append({'source': source, 'destination': 'Binaries/Win64/' + alias + extension, 'sha256': expected})
    copy_immutable(manifest, target(DELIVERY / 'Before', 'Binaries/Win64/UnrealEditor.modules'), sha(manifest))
    result = {'utc': utc(), 'status': 'PreparedOnly', 'main': str(MAIN), 'work': str(WORK), 'main_pid': args.main_pid,
        'world': args.world, 'process_census': initial, 'files': rows, 'source_whitelist': sorted(SOURCE),
        'packages': sorted('/Game/' + r['file'].removeprefix('Content/').removesuffix('.uasset') for r in rows if r['file'].startswith('Content/')),
        'art_candidate_count': 457, 'author_sequence_count': len(author['sequences']), 'author_event_count': len(author['events']),
        'native_files': native_rows, 'module': alias + '.dll', 'BuildId': BUILD_ID, 'modules_before': modules,
        'private_modules_sha256': native['UnrealEditor.modules'],
        'modules_before_sha256': sha(manifest), 'preserved_native': native_inventory(), 'evidence': evidence,
        'main_source_before': baseline, 'private_source': private, 'private_config': inventory(WORK, ('Config',)),
        'private_project_sha256': sha(WORK / 'Khazan.uproject'), 'protected_main': protected({r['file'] for r in rows}),
        'helper_sha256': sha(__file__), 'fresh_Main_verification_required': True}
    material_revision = visual_material_repair_revision()
    if material_revision:
        result['visual_material_repair_revision_sha256'] = material_revision['sha256']
        result['reused_material_dependency_count'] = 1
    write(PLAN, result); check(result)
    return result


def check(plan, delivered=False):
    shared_effects_rebase_revision(delivered=delivered)
    material_revision = visual_material_repair_revision(delivered=delivered)
    if material_revision:
        require(plan.get('visual_material_repair_revision_sha256') == material_revision['sha256']
                and plan.get('reused_material_dependency_count') == 1, 'Prepared visual material revision identity differs')
    require(plan['main'] == str(MAIN) and plan['work'] == str(WORK) and plan['source_whitelist'] == sorted(SOURCE)
            and plan['art_candidate_count'] == 457 and plan['BuildId'] == BUILD_ID and plan['helper_sha256'] == sha(__file__),
            'Prepared identity/helper/whitelist mismatch')
    require(len(plan['files']) == len({r['file'] for r in plan['files']}), 'Prepared duplicate destinations')
    require({r['file'] for r in plan['files'] if r['kind'] == 'Source'} == SOURCE
            and len([r for r in plan['files'] if r['kind'] == 'Art']) == 457
            and len([r for r in plan['files'] if r['kind'] == 'ReusedMaterialDependency']) == (1 if material_revision else 0)
            and len(plan['files']) == (968 if material_revision else 967), 'Prepared exact Source/Art/dependency scope mismatch')
    expected_rows = selected_rows(plan['main_source_before'], plan['private_source'], load(OUT / 'PreparedPlaybackPlan.json'),
                                 load(OUT / 'Authoring/PrivateAuthoring.json'), load(OUT / 'Authoring/SavedReadback.json'),
                                 load(RESOURCES / 'ArtCandidateManifest.json'), verify_current=False, delivered=delivered)
    require(plan['files'] == expected_rows and plan['packages'] == sorted('/Game/' + r['file'].removeprefix('Content/').removesuffix('.uasset')
            for r in expected_rows if r['file'].startswith('Content/')), 'Prepared file/package whitelist differs from actual frozen journals')
    require(re.fullmatch(r'UnrealEditor-KhazanMonsterVFX20261008(?:_\d+)?\.dll', plan['module'])
            and {r['source'] for r in plan['native_files']} == {'Binaries/Win64/UnrealEditor-Khazan.dll', 'Binaries/Win64/UnrealEditor-Khazan.pdb'}
            and len(plan['native_files']) == 2, 'Invalid unique native alias scope')
    for r in plan['native_files']:
        expected_name = Path(plan['module']).stem + Path(r['source']).suffix
        require(r['destination'] == 'Binaries/Win64/' + expected_name, 'Native alias destination mismatch')
    require(inventory(MAIN, ('Source',)) == plan['private_source' if delivered else 'main_source_before']
            and inventory(WORK, ('Source',)) == plan['private_source'], 'Main/private full Source CAS failed')
    require(inventory(WORK, ('Config',)) == plan['private_config'] and sha(WORK / 'Khazan.uproject') == plan['private_project_sha256'],
            'Verified private Config/project changed')
    require(sha(WORK / 'Binaries/Win64/UnrealEditor.modules') == plan['private_modules_sha256'], 'Verified private module manifest changed')
    require(protected({r['file'] for r in plan['files']}) == plan['protected_main'], 'Unselected protected Main content/Config/project changed')
    for path, expected in plan['evidence'].items():
        require(sha(evidence_path(path)) == expected, 'Frozen proof/evidence changed: ' + path)
    for r in plan['files']:
        require(sha(target(WORK, r['file'])) == r['after'] and sha(target(DELIVERY / 'Prepared', r['file'])) == r['after']
                and sha(target(MAIN, r['file'])) == r['after' if delivered else 'before'], 'Selected/staged CAS failed: ' + r['file'])
        if r['before'] is not None:
            require(sha(target(DELIVERY / 'Before', r['file'])) == r['before'], 'Immutable backup changed')
    for name, expected in plan['preserved_native'].items():
        require(sha(MAIN / 'Binaries/Win64' / name) == expected, 'Existing canonical/alias/patch changed: ' + name)
    for r in plan['native_files']:
        require(sha(target(WORK, r['source'])) == r['sha256'] and sha(target(DELIVERY / 'Prepared', r['source'])) == r['sha256'],
                'Compiled/prepared native binary changed')
        require(sha(target(MAIN, r['destination'])) == (r['sha256'] if delivered else None), 'Unique alias changed/exists')


def exclusive(path):
    if not path.exists():
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p)
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x80000000, 0, None, 3, 0x80, None)
    require(handle not in (None, ctypes.c_void_p(-1).value), 'Selected package/file still loaded or locked: ' + str(path))
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel.CloseHandle(handle)


def release_gate(args, plan):
    if not plan['main_pid']:
        census_gate(census(), 0)
        return None
    release_path = evidence_path(args.release)
    release = load(release_path)
    require(release.get('success') is True and release.get('pid') == plan['main_pid']
            and Path(release['project']).resolve() == MAIN.resolve() and release.get('world') == plan['world'], 'Main release identity mismatch')
    require(release.get('pie') is False and release.get('dirty_content') == [] and release.get('dirty_maps') == []
            and len(release['released_packages']) == len(plan['packages']) and set(release['released_packages']) == set(plan['packages'])
            and release.get('prepared_sha256') == sha(PLAN), 'Exact clean selected-package release proof required')
    stamp = dt.datetime.fromisoformat(release['utc'].replace('Z', '+00:00'))
    age = (dt.datetime.now(dt.timezone.utc) - stamp).total_seconds()
    require(stamp.tzinfo is not None and stamp >= dt.datetime.fromisoformat(plan['utc']) and 0 <= age <= 300, 'Main package release proof is stale')
    census_gate(census(), plan['main_pid'])
    return sha(release_path)


def apply(args):
    require(not RECEIPT.exists(), 'Delivery already recorded')
    plan = load(PLAN); check(plan)
    release_hash = release_gate(args, plan)
    manifest = target(MAIN, 'Binaries/Win64/UnrealEditor.modules')
    require(sha(manifest) == plan['modules_before_sha256'], 'Current Main module selection changed; preserve it')
    for r in plan['files']:
        exclusive(target(MAIN, r['file']))
    replaced, module_after = [], None
    try:
        for r in plan['native_files']:
            dest = target(MAIN, r['destination'])
            require(not dest.exists(), 'Never overwrite an existing native alias')
            shutil.copy2(target(DELIVERY / 'Prepared', r['source']), dest)
            require(sha(dest) == r['sha256'], 'Alias copy mismatch')
        census_gate(census(), plan['main_pid'])
        for r in plan['files']:
            dest = target(MAIN, r['file']); exclusive(dest)
            require(sha(dest) == r['before'], 'Concurrent selected Main edit: ' + r['file'])
            dest.parent.mkdir(parents=True, exist_ok=True)
            temporary = dest.with_name(dest.name + '.monstervfx-delivery.tmp')
            require(not temporary.exists(), 'Existing product staging file')
            shutil.copy2(target(DELIVERY / 'Prepared', r['file']), temporary)
            require(sha(temporary) == r['after'] and sha(dest) == r['before'], 'Immediate selected file CAS failed')
            exclusive(dest); os.replace(temporary, dest); replaced.append(r)
        check(plan, delivered=True)
        census_gate(census(), plan['main_pid'])
        require(sha(manifest) == plan['modules_before_sha256'], 'Module selection changed during delivery')
        modules = load(manifest); modules['Modules']['Khazan'] = plan['module']
        write(manifest, modules, expected=plan['modules_before_sha256']); module_after = sha(manifest)
        check(plan, delivered=True)
        require(load(manifest)['Modules']['Khazan'] == plan['module'] and sha(manifest) == module_after, 'Published module selection changed')
        result = {'utc': utc(), 'status': 'SourceContentAndNativeAliasDelivered', 'files': plan['files'], 'module': plan['module'],
            'native_files': plan['native_files'], 'module_manifest_sha256': module_after, 'prepared_sha256': sha(PLAN),
            'release_sha256': release_hash, 'BuildId': BUILD_ID, 'full_source_matches': True, 'protected_unchanged': True,
            'existing_native_preserved': True, 'existing_editor_closed': False, 'existing_editor_reloaded': False,
            'existing_editor_assets_saved': False, 'fresh_Main_verification_required': True, 'final_process_census': census()}
        if plan.get('visual_material_repair_revision_sha256'):
            result['visual_material_repair_revision_sha256'] = plan['visual_material_repair_revision_sha256']
            result['reused_material_dependency_count'] = 1
        write(RECEIPT, result)
        return result
    except Exception as error:
        rollback = []
        if module_after and sha(manifest) == module_after:
            temporary = manifest.with_name('UnrealEditor.modules.monstervfx-rollback.tmp')
            require(not temporary.exists(), 'Existing module rollback staging')
            shutil.copy2(target(DELIVERY / 'Before', 'Binaries/Win64/UnrealEditor.modules'), temporary)
            require(sha(manifest) == module_after and sha(temporary) == plan['modules_before_sha256'], 'Module rollback CAS failed')
            os.replace(temporary, manifest)
        for r in reversed(replaced):
            dest = target(MAIN, r['file'])
            if sha(dest) != r['after']:
                rollback.append({'file': r['file'], 'status': 'PreservedConcurrentEdit'}); continue
            try:
                exclusive(dest)
                if r['before'] is None:
                    dest.unlink()
                else:
                    backup = target(DELIVERY / 'Before', r['file'])
                    require(sha(backup) == r['before'], 'Rollback backup changed')
                    temporary = dest.with_name(dest.name + '.monstervfx-rollback.tmp')
                    require(not temporary.exists(), 'Existing selected rollback staging')
                    shutil.copy2(backup, temporary)
                    require(sha(dest) == r['after'], 'Concurrent edit before rollback')
                    os.replace(temporary, dest)
                rollback.append({'file': r['file'], 'status': 'RestoredBaseline'})
            except Exception as failure:
                rollback.append({'file': r['file'], 'status': 'RollbackFailed', 'error': str(failure)})
        write(DELIVERY / ('Failure_' + dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json'),
              {'utc': utc(), 'error': str(error), 'rollback': rollback, 'unique_alias_retained_for_audit': True})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare', action='store_true', help='Default: only Saved staging/backups')
    mode.add_argument('--apply', action='store_true', help='Root-only explicit Main delivery')
    parser.add_argument('--proof', default=str(OUT / 'NativeCandidateIntegrity.json'))
    parser.add_argument('--main-pid', type=int, default=0)
    parser.add_argument('--world', default=NO_EDITOR_WORLD)
    parser.add_argument('--release', default=str(DELIVERY / 'MainRelease.json'))
    args = parser.parse_args()
    result = apply(args) if args.apply else prepare(args)
    print(json.dumps({k: result[k] for k in ('status', 'module')}, ensure_ascii=False))
