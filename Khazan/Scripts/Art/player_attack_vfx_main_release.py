"""Release only clean prepared package loaders in the existing Main editor.

No save, reload, PIE, source mutation, compile, world change or native reload.
Run only after root has prepared the exact reviewed Source/Content delivery.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = MAIN / 'Saved/ImportReports/PlayerAttackVFX_20261008/MainDelivery'
PREPARED = OUT / 'Prepared.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
prepared_hash = sha(PREPARED)
plan = json.loads(PREPARED.read_text(encoding='utf-8'))
assert Path(unreal.Paths.project_dir()).resolve() == MAIN
assert plan['main'] == str(MAIN) and plan['editor_running'] is True
assert os.getpid() == plan['main_pid'], 'Preserve the current editor; prepared identity is stale'
assert plan['selected_package_count'] == len(plan['packages'])
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

def clean():
    assert editor.get_game_world() is None, 'PIE is active; preserve it'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Preserve unsaved content'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Preserve unsaved maps'
    world = editor.get_editor_world()
    assert world and world.get_path_name() == plan['world'], 'World differs from the prepared review'
    return world

world = clean()
actor_identities = {a.get_path_name(): a for a in actors.get_all_level_actors()}
selected_actors = {a.get_path_name() for a in actors.get_selected_level_actors()}
selected = {('/Game/' + r['file'].removeprefix('Content/').removesuffix('.uasset')): r
            for r in plan['files'] if r['file'].startswith('Content/')}
assert set(selected) == set(plan['packages'])
packages, absent = [], []
for path, row in selected.items():
    file = MAIN / row['file']
    assert sha(file) == row['before'], 'Selected Main bytes changed; preserve newer work'
    if row['before'] is None:
        object_path = path + '.' + path.rsplit('/', 1)[1]
        assert not file.exists() and unreal.find_object(None, object_path, follow_redirectors=False) is None
        absent.append(path)
        continue
    asset = unreal.load_asset(path)
    assert asset is not None, 'Existing selected asset must load before loader release'
    package = asset.get_outermost()
    assert package.get_name() == path and package != world.get_outermost()
    packages.append(package)
clean()
unreal.EditorLoadingAndSavingUtils.fully_load_packages(packages)
assert clean() == world
current_actors = {a.get_path_name(): a for a in actors.get_all_level_actors()}
assert current_actors == actor_identities
assert {a.get_path_name() for a in actors.get_selected_level_actors()} == selected_actors
assert sha(PREPARED) == prepared_hash
for row in selected.values():
    assert sha(MAIN / row['file']) == row['before'], 'Loader release changed selected package bytes'
result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), success=True,
    pid=os.getpid(), project=str(MAIN), world=world.get_path_name(), editor_running=True,
    pie=False, dirty_content=[], dirty_maps=[], prepared_sha256=prepared_hash,
    released_packages=sorted(selected), loaded_existing_packages=sorted(p.get_name() for p in packages),
    absent_new_packages=sorted(absent), package_saves=0, packages_reloaded=False,
    native_reload=False, editor_closed=False, world_and_actor_identities_preserved=True,
    method='UE5.8 EditorLoadingAndSavingUtils.fully_load_packages: FlushAsyncLoading and ResetLoaders only for exact existing selected packages; new absent packages are accounted without loading.')
(OUT / 'MainRelease.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('KZ_ATTACK_VFX_EXACT_LOADER_RELEASE', result['pid'], len(packages), 'existing', len(absent), 'new absent')
