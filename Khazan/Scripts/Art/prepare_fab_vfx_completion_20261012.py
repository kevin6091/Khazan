"""Target the four newly supplied packs and back up the prior three for reorganization."""
from pathlib import Path
import json
import runpy
import shutil
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'Metadata/FabVFX_20261012'
META = ROOT / 'Metadata/FabVFX_20261012/Completion'
STAGE = ROOT / 'Saved/ArtStaging/FabVFX_Complete_20261012'
SOURCE = Path('C:/Users/user/Desktop/VFX/Assets')
SHA = runpy.run_path(str(ROOT / 'Scripts/Art/stage_fab_vfx_import_20261012.py'))['sha']
NEW = [
    ('8bebe1ca-0d93-4495-8bed-c07851d92fe1', 'Action-RPG Essentials VFX Pack V2.0', 'ARPGEssentials', '01_ARPGEssentials'),
    ('d9a83197-8153-42cb-9dff-fca43c413b5d', 'Dynamic Impact and Collision Effects Pack', 'DynamicCollisionVFX', '02_DynamicImpact'),
    ('9d886fdb-8011-49e7-a10d-0d8897fe9dc2', 'Slash and Hit VFX', 'SlashFX', '03_SlashHit'),
    ('de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4', 'Roar Spell VFX', 'Roar_Spell_VFX', '04_RoarSpell'),
]
FOLDERS = {'Cursed_Magic': '05_CursedMagic', 'NiagaraVFXBundle': '06_NiagaraBundle', 'ARPGVFXPack03': '07_ARPG03', 'Characters': '_Shared'}


def main():
    META.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    assert not (ROOT / 'Content/VFX').exists(), 'Existing VFX content requires a conflict-aware plan'
    old = json.loads((OLD / 'Delivery.json').read_text())['files']
    manifest = []
    for row in old:
        rel = row['relative_path']
        source = ROOT / 'Content' / rel
        checksum = SHA(source)
        assert checksum == row['sha256'], ('Prior pack edited; preserve and replan', source)
        backup = META / 'Before/Content' / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(source, backup)
        assert SHA(backup) == checksum
        manifest.append({'source': str(source), 'relative_path': rel, 'sha256': checksum, 'bytes': source.stat().st_size, 'prior_main': True, 'listing_id': row.get('listing_id')})
    listings = json.loads((OLD / 'ListingMap.json').read_text(encoding='utf-8'))
    for guid, title, folder, target in NEW:
        content = SOURCE / 'Content'
        roots = [content / folder]
        assert roots[0].is_dir(), roots[0]
        for extra in ('__ExternalActors__', '__ExternalObjects__'):
            candidate = content / extra / folder
            if candidate.is_dir():
                roots.append(candidate)
        chosen = []
        for candidate in roots:
            for file in sorted(candidate.rglob('*')):
                if file.is_file() and file.suffix.lower() in ('.uasset', '.umap', '.uexp', '.ubulk', '.uptnl'):
                    rel = file.relative_to(content).as_posix()
                    assert not (ROOT / 'Content' / rel).exists(), ('New source root collision', rel)
                    chosen.append({'source': str(file), 'relative_path': rel, 'sha256': SHA(file), 'bytes': file.stat().st_size, 'prior_main': False, 'listing_id': guid})
        assert chosen
        manifest.extend(chosen)
        pack = next(r for r in listings if r['listing_id'] == guid)
        pack.update(title=title, status='found_in_new_Assets_project', source_project=str(SOURCE), source_content_root=str(content / folder), original_package_root='/Game/' + folder, target_package_root='/Game/VFX/' + target, files=len(chosen), bytes=sum(r['bytes'] for r in chosen), engine_association='5.4')
        FOLDERS[folder] = target
    for pack in listings:
        if pack['listing_id'] not in {p[0] for p in NEW}:
            original = pack['target_package_root'].split('/')[-1]
            pack.update(original_package_root=pack['target_package_root'], target_package_root='/Game/VFX/' + FOLDERS[original])
    assert len({r['relative_path'].lower() for r in manifest}) == len(manifest)
    for row in manifest:
        target = STAGE / 'Content' / row['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            assert SHA(target) == row['sha256'], target
        else:
            shutil.copy2(row['source'], target)
    project = {'FileVersion': 3, 'EngineAssociation': '5.8', 'Plugins': [{'Name': p, 'Enabled': True} for p in ('PythonScriptPlugin', 'EditorScriptingUtilities', 'Niagara')]}
    (STAGE / 'FabVFXComplete.uproject').write_text(json.dumps(project, indent=2), encoding='utf-8')
    (META / 'InputManifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (META / 'ListingMap.json').write_text(json.dumps(listings, ensure_ascii=False, indent=2), encoding='utf-8')
    (META / 'FolderMap.json').write_text(json.dumps(FOLDERS, indent=2), encoding='utf-8')
    protected = {}
    for folder in ('Source', 'Config'):
        for file in (ROOT / folder).rglob('*'):
            if file.is_file():
                protected[file.relative_to(ROOT).as_posix()] = SHA(file)
    protected['Khazan.uproject'] = SHA(ROOT / 'Khazan.uproject')
    (META / 'ProtectedBefore.json').write_text(json.dumps(protected, indent=2), encoding='utf-8')
    print(json.dumps({'stage': str(STAGE), 'files': len(manifest), 'bytes': sum(r['bytes'] for r in manifest), 'prior_main_files_backed_up': len(old), 'new_files': len(manifest)-len(old), 'roots': dict(Counter(r['relative_path'].split('/')[0] for r in manifest))}), flush=True)


if __name__ == '__main__':
    main()
