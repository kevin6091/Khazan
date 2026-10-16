"""Read-only audit after the authorized Main restart; no compile/save/PIE."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
expected = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
assert root == expected, root
report = Path(globals().get('cloth_report_directory',
                          root / 'Metadata/PlayerParts_20261007/HairRefinement')).resolve()
assert report.is_relative_to(root / 'Metadata') and report != root / 'Metadata'
expected_dirty = tuple(globals().get('expected_dirty_content', ()))
assert len(expected_dirty) == len(set(expected_dirty))
assert all(isinstance(name, str) and name.startswith('/Game/') and '.' not in name for name in expected_dirty)
dirty_identities = {}


def check_dirty_content():
    current = {package.get_name(): package for package in
               unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    assert set(current) == set(expected_dirty), ('Dirty content changed; preserve it', sorted(current))
    for name, package in sorted(current.items()):
        asset = unreal.find_object(None, name + '.' + name.rsplit('/', 1)[1], follow_redirectors=False)
        assert isinstance(asset, unreal.AnimMontage) and asset.get_outermost() == package
        identity = (package, asset, asset.get_editor_property('skeleton'), asset.get_editor_property('preview_skeletal_mesh'))
        if name in dirty_identities:
            assert identity == dirty_identities[name], ('Dirty montage identity or preview references changed', name)
        else:
            dirty_identities[name] = identity
    return current
data = dict(pid=os.getpid(), project=str(root), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            blueprints=[], components=[], automatic_pie=False, compile_or_save=False)
try:
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert editor.get_game_world() is None
    check_dirty_content()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if 'expected_world' in globals():
        assert editor.get_editor_world().get_path_name() == expected_world
    base = '/Game/_Art/Player/Character/'
    paths = ['Bluprints/BP_Player', 'Bluprints/ABP_Player'] + ['Bluprints/Parts/ABP_Player_Original_' + part for part in ('Torso', 'Shoes', 'Leg', 'Hair', 'Arm')]
    for path in paths:
        asset = unreal.load_asset(base + path)
        status = asset.get_editor_property('status')
        assert status == unreal.BlueprintStatus.BS_UP_TO_DATE, (path, str(status))
        data['blueprints'].append(dict(path=asset.get_path_name(), status=str(status)))
    bp = unreal.load_asset(base + 'Bluprints/BP_Player')
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    functions = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    for handle in handles:
        subdata = functions.get_data(handle)
        obj = functions.get_associated_object(subdata)
        if not isinstance(obj, unreal.SkeletalMeshComponent):
            continue
        mesh = obj.get_editor_property('skeletal_mesh_asset')
        if not mesh or mesh.get_name() not in ['Player_Original_' + part for part in ('Torso', 'Shoes', 'Leg', 'Hair', 'Arm')]:
            continue
        part = mesh.get_name().removeprefix('Player_Original_')
        physics = obj.get_editor_property('physics_asset_override') or mesh.get_editor_property('physics_asset')
        parent_data = functions.get_data(functions.get_parent_handle(subdata))
        parent = functions.get_associated_object(parent_data)
        assert parent.get_name() == 'CharacterMesh0', (part, parent.get_name())
        assert physics.get_name() == 'Player_Original_' + part + '_PhysicsAsset'
        anim = obj.get_editor_property('anim_class')
        assert anim.get_name() == 'ABP_Player_Original_' + part + '_C'
        data['components'].append(dict(part=part, mesh=mesh.get_path_name(), physics=physics.get_path_name(), animation=anim.get_path_name(), parent=parent.get_name()))
    assert len(data['components']) == 5, data['components']
    manifest = json.loads((report / 'CandidateManifest.json').read_text(encoding='utf-8-sig'))
    target_packages = {'/Game/' + entry['path'].removeprefix('Content/').removesuffix('.uasset') for entry in manifest['packages']}
    assert not set(expected_dirty).intersection(target_packages), 'Dirty targets are never allowed'
    for entry in manifest['packages']:
        assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest().upper() == entry['preparedSha256']
    check_dirty_content()
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if 'expected_world' in globals():
        assert editor.get_editor_world().get_path_name() == expected_world
    data.update(success=True, dirty_content=len(expected_dirty), dirty_content_names=sorted(expected_dirty),
                unrelated_dirty_identities_preserved=True, dirty_map=0, game_world=False)
except Exception as error:
    data.update(success=False, error=repr(error))
    raise
finally:
    (report / 'MainReadyAudit.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Main hair read-only audit:', data.get('success'), os.getpid())
