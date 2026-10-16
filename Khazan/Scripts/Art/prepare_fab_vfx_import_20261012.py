"""Inventory the user-supplied VFX library; never overwrite project packages."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('C:/Users/user/Desktop/VFX')
META = ROOT / 'Metadata/FabVFX_20261012'
META.mkdir(parents=True, exist_ok=True)
PROJECTS = sorted(SOURCE.rglob('*.uproject'))
PACKS = [
    ('8bebe1ca-0d93-4495-8bed-c07851d92fe1', 'Action-RPG Essentials VFX Pack V2.0', None, None),
    ('d9a83197-8153-42cb-9dff-fca43c413b5d', 'Dynamic Impact and Collision Effects Pack', None, None),
    ('9d886fdb-8011-49e7-a10d-0d8897fe9dc2', 'Slash and Hit VFX', None, None),
    ('de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4', 'Unresolved Fab listing', None, None),
    ('83d31880-441c-424e-8d22-71d778cf2905', 'Cursed Magic Niagara', 'Unreal8/CursedMagicNiagara', 'Cursed_Magic'),
    ('ebcdf5fb-077c-46ac-be75-1393a7c699b6', 'Niagara VFX Bundle', 'Unreal8/Unreal8_Assets', 'NiagaraVFXBundle'),
    ('4ea54c1a-a334-4115-89ea-957aa6d3d4b0', 'ARPGVFXPack03', 'Unreal8/Unreal8_Assets', 'ARPGVFXPack03'),
]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write(name, data):
    (META / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    inventory = []
    source_index = {}
    projects = []
    for project in PROJECTS:
        config = json.loads(project.read_text(encoding='utf-8-sig'))
        content = project.parent / 'Content'
        files = sorted(p for p in content.rglob('*') if p.is_file() and p.suffix.lower() in ('.uasset', '.umap', '.uexp', '.ubulk', '.uptnl'))
        counts = Counter()
        sizes = Counter()
        for file in files:
            rel = file.relative_to(content).as_posix()
            counts[rel.split('/')[0]] += 1
            sizes[rel.split('/')[0]] += file.stat().st_size
            row = {'project': str(project), 'source': str(file), 'relative_path': rel, 'bytes': file.stat().st_size}
            if file.suffix.lower() in ('.uasset', '.umap'):
                row['package'] = '/Game/' + str(Path(rel).with_suffix('')).replace('\\', '/')
                source_index.setdefault(row['package'], []).append(row)
            inventory.append(row)
        projects.append({'project': str(project), 'engine_association': config.get('EngineAssociation'), 'plugins': config.get('Plugins', []), 'content_roots': [{'root': n, 'files': counts[n], 'bytes': sizes[n]} for n in sorted(counts)]})
    write('LocalInventory.json', {'projects': projects, 'files': inventory})
    write('SourcePackageIndex.json', source_index)
    mappings = []
    for guid, title, project_rel, folder in PACKS:
        status = 'matched_local' if folder else ('listing_unresolved' if title == 'Unresolved Fab listing' else 'not_found_in_supplied_library')
        pack = {'listing_id': guid, 'url': 'https://www.fab.com/listings/' + guid, 'title': title, 'status': status, 'source_project': str(SOURCE / project_rel) if project_rel else None, 'source_content_root': str(SOURCE / project_rel / 'Content' / folder) if folder else None, 'target_package_root': '/Game/' + folder if folder else None}
        if folder:
            chosen = [p for p in inventory if p['project'].startswith(str(SOURCE / project_rel)) and p['relative_path'].startswith(folder + '/')]
            pack.update(files=len(chosen), bytes=sum(p['bytes'] for p in chosen))
        mappings.append(pack)
    write('ListingMap.json', mappings)
    print(json.dumps({'projects': projects, 'mappings': mappings}, ensure_ascii=False), flush=True)
    guid = PACKS[3][0]
    responses = []
    for url in ['https://www.fab.com/listings/' + guid, 'https://www.fab.com/i/listings/' + guid]:
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/json'})
            with urllib.request.urlopen(request, timeout=20) as result:
                data = result.read()
                (META / ('UnresolvedListing.json' if '/i/' in url else 'UnresolvedListing.html')).write_bytes(data)
                responses.append({'url': url, 'status': result.status, 'bytes': len(data)})
        except Exception as error:
            responses.append({'url': url, 'error': str(error)})
    write('UnresolvedListingFetch.json', responses)
    print(json.dumps({'unresolved_listing_fetch': responses}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
