import unreal
for direction in ['Front', 'Back']:
    m = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/BrutalAttack/AM_DAS_Brutal' + direction)
    print(direction, 'autoBlendOut', m.get_editor_property('enable_auto_blend_out'), 'seconds', m.get_play_length())
