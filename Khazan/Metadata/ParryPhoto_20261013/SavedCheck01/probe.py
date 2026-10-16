import os,json,unreal as u
from pathlib import Path
out=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
guard=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'))
r={'class':guard.get_class().get_path_name(),'effect':guard.get_editor_property('ParryImpactEffect').get_path_name(),'camera':guard.get_editor_property('ParryCameraShake').get_path_name()}
(out/'Config.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
