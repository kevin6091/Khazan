"""Clear only the optional player received-hit burst; keep other settings intact."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ['KZ_RECEIVED_HIT_OUT'])
MODE = os.environ.get('KZ_RECEIVED_HIT_MODE', 'verify')
PATH = '/Game/Data/Character/DA_CharacterDefinition_Player'
FILE = ROOT / 'Content/Data/Character/DA_CharacterDefinition_Player.uasset'
PROTECTED = [
    'Content/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.uasset',
    'Content/_Art/Effects/Combat/AttackContact/PP_Combat_HitBurst.uasset',
    'Content/_Art/Effects/Combat/Blood/FP_Monster_HitBloodReference.uasset',
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(asset, name):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(OUT / name)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    assert u.Exporter.run_asset_export_task(task), 'Definition text export failed'
    return Path(task.filename).read_text(encoding='utf-8-sig')


report = {'status': 'running', 'mode': MODE, 'asset': PATH,
          'changed_property': 'HitReactions.ImpactEffect', 'source_changes': 0}
try:
    protected = {p: sha(ROOT / p) for p in PROTECTED}
    asset = u.load_asset(PATH)
    assert asset, PATH
    settings = asset.get_editor_property('HitReactions')
    impact = settings.get_editor_property('ImpactEffect')
    report['before_effect'] = impact.get_path_name() if impact else None
    report['before_sha256'] = sha(FILE)
    if MODE == 'apply':
        assert impact and impact.get_path_name().endswith('/PP_Combat_HitBurst.PP_Combat_HitBurst'), report
        shutil.copy2(FILE, OUT / 'DA_CharacterDefinition_Player_Before.uasset')
        before = export(asset, 'Definition_Before.t3d')
        settings.set_editor_property('ImpactEffect', None)
        asset.set_editor_property('HitReactions', settings)
        assert asset.get_editor_property('HitReactions').get_editor_property('ImpactEffect') is None
        after = export(asset, 'Definition_After.t3d')
        # A None/default struct field is omitted by the UE text exporter.
        import re
        field = r',ImpactEffect="/Script/Engine\.ParticleSystem\x27' + re.escape(impact.get_path_name()) + r'\x27"'
        expected, count = re.subn(field, '', before)
        assert count == 1 and expected == after, 'Unrelated exported Definition fields changed'
        assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), 'Player Definition save failed'
        report['export_other_fields_unchanged'] = True
    else:
        assert impact is None, 'Saved player received-hit burst still configured'
    report['after_effect'] = asset.get_editor_property('HitReactions').get_editor_property('ImpactEffect')
    report['after_sha256'] = sha(FILE)
    report['protected_sha256'] = protected
    assert protected == {p: sha(ROOT / p) for p in PROTECTED}, 'Shared attack/parry assets changed'
    report['status'] = 'passed'
except Exception as exc:
    report['status'] = 'failed'
    report['error'] = str(exc)
    raise
finally:
    (OUT / 'Result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
