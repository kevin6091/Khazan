"""Attach field/projectile feedback to the existing four object definitions."""
from pathlib import Path
import json, os
import unreal as u

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve();assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
mapping=author['particles'];report={'definitions':[]}
def particle(name):
    key=next(k for k in mapping if k.split('.')[-1]==name);return u.load_asset(mapping[key])
for family in ['ApesStoneHandElite','Yetuga']:
    asset=u.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family)
    objects=list(asset.get_editor_property('PatternObjects'));before=[o.export_text() for o in objects]
    for obj in objects:
        name=str(obj.get_editor_property('Id'))
        if name=='COI_ApesStoneHand_E_FastBall_OBJ':
            rock=u.load_asset('/Game/_Art/Effects/Shared/Meshes/MonsterApesYetuga/FS_Yetuga_Rock_01')
            assert rock;obj.set_editor_property('StaticMesh',rock)
            obj.set_editor_property('SpawnEffect',particle('FP_Boss_Yetuga_Rock_dust_start_01'))
            obj.set_editor_property('FlightEffect',particle('FP_Boss_Yetuga_IceBreath_Mouth_Dust_02'))
            obj.set_editor_property('ImpactEffect',particle('FP_Boss_Yetuga_Rock_Explosion_01'))
        elif name=='COI_Yetuga_IceBreath_OBJ':
            obj.set_editor_property('FlightEffect',particle('FP_Boss_Yetuga_IceBreath_Mouth_Dust_02'))
        elif name=='COI_Yetuga_IceBreath_Field_OBJ':
            obj.set_editor_property('SpawnEffect',u.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/FP_Boss_Yetuga_IceBreath_explosion_01'))
            obj.set_editor_property('ImpactEffect',u.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/FP_Boss_Yetuga_IceBreath_Smash_04'))
        # Yetuga's rock uses its original Idle/Move/Impact source notifies.
    asset.set_editor_property('PatternObjects',objects)
    after=[o.export_text() for o in asset.get_editor_property('PatternObjects')]
    report['definitions'].append({'asset':asset.get_path_name(),'before':before,'after':after})
    assert u.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False)
(out/'ObjectBindings.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('GIANT_OBJECT_BINDINGS_SAVED: original field2 / rock source notifies / rough Apes rock')
