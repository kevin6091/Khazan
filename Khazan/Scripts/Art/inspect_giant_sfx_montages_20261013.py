"""Read-only current giant montage links for the early-source SFX cases."""
import json
import os
from pathlib import Path
import unreal as u

out = Path(os.environ['KZ_AUDIO_OUTPUT']) / 'MontageLinks.json'
rows = []
for family in ('ApesStoneHandElite', 'Yetuga'):
    path = f'/Game/Monsters/{family}/Data/DA_OriginalPatterns_{family}'
    definition = u.EditorAssetLibrary.load_asset(path)
    assert definition, path
    for node in definition.get_editor_property('nodes'):
        name = str(node.get_editor_property('node_id'))
        if not any(word in name for word in ('TurnBackRun', 'Dodge', 'Roar', 'FastBall')):
            continue
        montage = node.get_editor_property('montage')
        rows.append({'family': family, 'node': name,
                     'montage': montage.get_path_name() if montage else None,
                     'section': str(node.get_editor_property('section_name'))})
    body = u.EditorAssetLibrary.load_asset(f'/Game/Monsters/{family}/Data/DA_Character_{family}')
    if body:
        hits = body.get_editor_property('hit_reactions')
        for category in ('short_hits', 'additive_hits', 'knockbacks', 'launches', 'shield_blocks'):
            for montage in hits.get_editor_property(category):
                if montage:
                    rows.append({'family': family, 'node': category, 'montage': montage.get_path_name(), 'section': None})
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
