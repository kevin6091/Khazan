"""Root-launched six-field private Definition merge after the new native build.

Default probe changes only local struct copies. Apply with runpy init_globals
KZ_MONSTER_VFX_CONTENT_REBASE_MODE='apply' and the exact actually loaded DLL
SHA in KZ_MONSTER_VFX_CONTENT_REBASE_DLL_SHA256. Never edits Main assets,
original author499 journal/plan/Apes reports, sequences or death montages.
"""
from pathlib import Path
from datetime import datetime, timezone
import ast
import ctypes
import hashlib
import json
import os
import re
import traceback
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
EXPECTED = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
assert WORK == EXPECTED, 'Main/shared Definition merge blocked'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'Own PIE must be stopped'
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
TASK = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
OUT = TASK / 'Authoring/ContentRebaseRevision'
FINAL = TASK / 'Authoring/ContentRebaseRevision.json'
MODE = globals().get('KZ_MONSTER_VFX_CONTENT_REBASE_MODE', os.environ.get('KZ_MONSTER_VFX_CONTENT_REBASE_MODE', 'probe'))
assert MODE in ('probe', 'apply')
FAMILIES = {'Swordsman', 'SwordShield', 'HeavySwordsman', 'HalberdElite', 'ApesStoneHandElite', 'Yetuga'}


def sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.definition-rebase.tmp')
    assert not temp.exists(), str(temp)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def package_file(relative):
    p = WORK / relative
    assert relative.startswith('Content/') and Path(relative).suffix == '.uasset' and '..' not in Path(relative).parts
    assert p.resolve() == p and p.resolve().is_relative_to(WORK), 'Shared asset mutation blocked: ' + relative
    return p


def remove_death(text):
    return re.sub(r'(?:,)?DeathPresentationMontage=[^,)]+', '', text)


def loaded_module():
    manifest = WORK / 'Binaries/Win64/UnrealEditor.modules'
    alias = read(manifest)['Modules']['Khazan']
    expected = globals().get('KZ_MONSTER_VFX_CONTENT_REBASE_DLL_SHA256', os.environ.get('KZ_MONSTER_VFX_CONTENT_REBASE_DLL_SHA256'))
    if MODE == 'apply' or expected is not None:
        assert isinstance(expected, str) and re.fullmatch('[0-9a-fA-F]{64}', expected), 'Exact new native DLL SHA required'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    handle = kernel.GetModuleHandleW(alias); assert handle, 'Selected native module not actually loaded'
    buffer = ctypes.create_unicode_buffer(32768)
    count = kernel.GetModuleFileNameW(handle, buffer, len(buffer)); assert 0 < count < len(buffer)
    path = Path(buffer.value).resolve()
    assert path.is_relative_to(WORK / 'Binaries/Win64') and path == (WORK / 'Binaries/Win64' / alias).resolve()
    if expected is not None: assert sha(path) == expected.lower(), 'Loaded new native DLL SHA differs'
    assert unreal.load_class(None, '/Script/Khazan.KZHitReactionAbility'), 'Reaction native class missing'
    return {'path': str(path), 'sha256': sha(path), 'manifest_sha256': sha(manifest), 'selected': alias}


# Reuse the already exercised pure T3D exporter, without running its author.
source = MAIN / 'Scripts/Art/player_attack_vfx_author.py'
tree = ast.parse(source.read_text(encoding='utf-8-sig'))
functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'export']
assert len(functions) == 1
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), globals())


def main():
    intake_path = OUT / 'IntakeApplied.json'
    intake = read(intake_path); plan = read(OUT / 'IntakePlan.json')
    assert intake['status'] == 'passed' and intake['main_mutations'] == 0 and intake['original_reports_unchanged']
    assert intake['plan_sha256'] == sha(OUT / 'IntakePlan.json')
    assert plan['main'] == str(MAIN) and Path(plan['work']).resolve() == WORK
    for p, expected in plan['inputs'].items():
        assert sha(p) == expected, 'Original report/evidence changed: ' + p
    author_path = TASK / 'Authoring/PrivateAuthoring.json'
    author = read(author_path)
    assert author['status'] == 'passed' and author['mutation_journal'] == plan['author_original_journal']
    assert sha(author_path) == plan['author_original_sha256']
    assert author['plan_sha256'] == sha(TASK / 'PreparedPlaybackPlan.json') == plan['plan_original_sha256']
    deaths = author['death_presentations']; assert len(deaths) == 6 and {d['family'] for d in deaths} == FAMILIES
    intake_rows = {r['relative']: r for r in plan['rows']}
    definitions = {d['definition_relative'] for d in deaths}
    untouched = {r['relative']: r['saved_sha256'] for r in author['mutation_journal'] if r['relative'] not in definitions}
    assert len(untouched) == 493
    for r in plan['rows']:
        assert sha(WORK / r['relative']) == sha(MAIN / r['relative']) == r['main_current_sha256'], 'Reaction intake drift'
        if r['mode'] == 'shared_readonly_current':
            assert (WORK / r['relative']).resolve() == (MAIN / r['relative']).resolve()
        else:
            package_file(r['relative'])
    for relative, expected in plan['protected_private_sha256'].items():
        assert sha(package_file(relative)) == expected, 'Protected VFX candidate changed: ' + relative
    for relative, expected in plan['protected_main_sha256'].items():
        assert sha(MAIN / relative) == expected, 'Original Main VFX baseline changed: ' + relative
    if MODE == 'apply': assert not FINAL.exists(), 'Completed merge exists; do not reapply'
    report = {'schema': 'Khazan.MonsterVFX.ContentRebaseRevision.v1', 'status': 'running', 'mode': MODE,
              'project': str(WORK), 'pid': os.getpid(), 'utc': datetime.now(timezone.utc).isoformat(),
              'author_before_sha256': sha(author_path), 'original_baseline_sha256': sha(TASK / 'WorkBaseline.json'),
              'plan_sha256': sha(TASK / 'PreparedPlaybackPlan.json'),
              'source_schema_sha256': sha(MAIN / 'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json'),
              'contentintake': str(intake_path), 'contentintake_sha256': sha(intake_path),
              'loaded_module': loaded_module(), 'package_saves': 0, 'asset_mutations': 0, 'main_mutations': 0,
              'original_author_journal_preserved': False, 'original_reports_unchanged': False,
              'untouched493_sha_preserved': False, 'untouched493_sha256': untouched, 'rows': []}
    try:
        staged = []
        for d in deaths:
            relative = d['definition_relative']; r = intake_rows[relative]
            assert r['definition_restore_required'] and r['mode'] == 'private_copy'
            path = package_file(relative); assert sha(path) == r['main_current_sha256']
            main_backup = OUT / 'BeforeMain' / relative; private_backup = OUT / 'BeforePrivate' / relative
            assert sha(main_backup) == r['main_current_sha256'] and sha(private_backup) == d['definition_after_sha256']
            assert sha(package_file(d['montage_relative'])) == d['montage_after_sha256']
            definition = unreal.load_asset(d['definition']); montage = unreal.load_asset(d['montage']); assert definition and montage
            assert isinstance(montage, unreal.AnimMontage)
            original_settings = definition.get_editor_property('MonsterStamina'); before = original_settings.export_text()
            assert original_settings.get_editor_property('DeathPresentationMontage') is None, 'Unexpected current death pointer'
            # A standalone native struct keeps probe free of object property edits.
            settings = type(original_settings)(); settings.import_text(before)
            assert settings.export_text() == before, 'Native settings struct roundtrip differs'
            export_before = OUT / (d['family'] + '_Definition_MainBefore.t3d'); export(definition, export_before)
            settings.set_editor_property('DeathPresentationMontage', montage)
            after = settings.export_text()
            assert remove_death(before) == remove_death(after), 'Unrelated stamina/Brutal fields changed'
            assert settings.get_editor_property('DeathPresentationMontage') == montage
            row = {'relative': relative, 'family': d['family'], 'definition': d['definition'], 'montage': d['montage'],
                   'original_main_before_sha256': d['definition_before_sha256'], 'prior_private_sha256': d['definition_after_sha256'],
                   'main_before_sha256': r['main_current_sha256'], 'merged_after_sha256': None,
                   'settings_before': before, 'settings_after': after, 'all_other_definition_fields_preserved': False,
                   'main_backup_path': str(main_backup), 'private_backup_path': str(private_backup),
                   'before_export': str(export_before), 'before_export_sha256': sha(export_before)}
            staged.append((definition, settings, path, row)); report['rows'].append(row)
        assert len(staged) == 6
        if MODE == 'apply':
            for definition, settings, path, row in staged:
                assert sha(path) == row['main_before_sha256'] and sha(MAIN / row['relative']) == row['main_before_sha256']
                definition.set_editor_property('MonsterStamina', settings)
                export_after = OUT / (row['family'] + '_Definition_MergedAfter.t3d'); export(definition, export_after)
                assert remove_death(Path(row['before_export']).read_text(encoding='utf-8-sig')) == remove_death(export_after.read_text(encoding='utf-8-sig')), 'Other Definition fields changed'
                row.update(after_export=str(export_after), after_export_sha256=sha(export_after), all_other_definition_fields_preserved=True)
                assert unreal.EditorAssetLibrary.save_loaded_asset(definition, False)
                report['package_saves'] += 1; report['asset_mutations'] += 1
                row['merged_after_sha256'] = sha(path)
                assert definition.get_editor_property('MonsterStamina').export_text() == row['settings_after']
                write(OUT / 'ApplyProgress.json', report)
            assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
            assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        for relative, expected in untouched.items(): assert sha(package_file(relative)) == expected
        for relative, expected in plan['protected_private_sha256'].items(): assert sha(package_file(relative)) == expected
        for r in plan['rows']: assert sha(MAIN / r['relative']) == r['main_current_sha256'], 'Main changed during private merge'
        for p, expected in plan['inputs'].items(): assert sha(p) == expected
        assert read(author_path)['mutation_journal'] == plan['author_original_journal']
        report.update(status='passed', original_author_journal_preserved=True, original_reports_unchanged=True,
                      untouched493_sha_preserved=True, boundary='Only six DeathPresentationMontage assignments; actual current Reaction/Definition fields retained by full T3D comparison. Original author/plan unchanged.')
        write(FINAL if MODE == 'apply' else OUT / 'Probe.json', report)
    except Exception as error:
        report.update(status='failed', error=repr(error), traceback=traceback.format_exc(),
                      resume='Stop owned process; inspect CAS-backed ApplyProgress/Error and restore only private six known bytes before a fresh retry. No broad reauthor.')
        write(OUT / ('ApplyError.json' if MODE == 'apply' else 'ProbeError.json'), report)
        raise
    print(json.dumps({'status': report['status'], 'mode': MODE, 'package_saves': report['package_saves'],
                      'report': str(FINAL if MODE == 'apply' else OUT / 'Probe.json')}))


if __name__ == '__main__':
    main()
