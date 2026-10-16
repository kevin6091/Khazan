from pathlib import Path
root=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source=root/'Scripts/Engineering/deliver_player_cloth_refinement.py'
exec(compile(source.read_text(encoding='utf-8-sig'),str(source),'exec'),{
    '__file__':str(source),'cloth_report_directory':root/'Metadata/PlayerParts_20261008/ShoulderSoftening',
    'cloth_targets':('Content/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset.uasset',),
    'cloth_required_validation_fields':('native_pie_passed','native_saved_reload_passed','stock_saved_reload_passed')})
