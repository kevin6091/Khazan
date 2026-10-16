from pathlib import Path
root = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source = root/'Scripts/Engineering/deliver_player_cloth_refinement.py'
scope = {'__file__':str(source),
         'cloth_report_directory':root/'Metadata/PlayerParts_20261008/WaistJitter',
         'cloth_targets':('Content/_Art/Player/Character/Meshs/Leg/Player_Original_Leg_RigidBody_PhysicsAsset.uasset',),
         'cloth_required_validation_fields':('native_pie_passed','native_saved_reload_passed','stock_saved_reload_passed')}
exec(compile(source.read_text(encoding='utf-8-sig'),str(source),'exec'),scope)
