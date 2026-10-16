from pathlib import Path
import json,os,re,unreal as u
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary
result={'status':'running','materials':[]}
guard=u.get_default_object(EAL.load_blueprint_class('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard'))
assert guard.get_editor_property('ParryImpactEffect').get_path_name()==BASE+'/PP_Player_Parry_Reference.PP_Player_Parry_Reference'
cam=u.get_default_object(guard.get_editor_property('ParryCameraShake'));assert cam
assert abs(cam.get_editor_property('oscillation_duration')-.35907653)<1e-6
assert abs(cam.get_editor_property('loc_oscillation').get_editor_property('y').get_editor_property('amplitude')+10)<1e-6
assert abs(cam.get_editor_property('fov_oscillation').get_editor_property('amplitude')-.3)<1e-6
assert u.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player').get_editor_property('HitReactions').get_editor_property('ImpactEffect') is None
for name in ['M_FM_fluid_A','M_FM_SubUV_color_A','M_FM_Subuv_Atlas_B','M_Base_SubUV','M_Parry_Distortion','M_Parry_Halo']:
    m=u.load_asset(BASE+'/'+name);assert m
    errors=list(LIB.recompile_material(m));assert not errors,errors
    stats=LIB.get_statistics(m)
    result['materials'].append({'path':m.get_path_name(),'errors':errors,'pixel_instructions':stats.num_pixel_shader_instructions})
    assert stats.num_pixel_shader_instructions>0
mi=u.load_asset(BASE+'/MI_Parry_PurpleHalo')
assert mi.get_editor_property('parent').get_path_name()==BASE+'/M_Parry_Halo.M_Parry_Halo'
dist=u.load_asset(BASE+'/M_Parry_Distortion')
assert dist.get_editor_property('refraction_method')==u.RefractionMode.RM_PIXEL_NORMAL_OFFSET
result['distortion_method']=str(dist.get_editor_property('refraction_method'))
result['halo_parent']=mi.get_editor_property('parent').get_path_name()
result['mi_shader_permutations']=[]
for path in EAL.list_assets(BASE,recursive=False):
    asset=u.load_asset(path)
    if isinstance(asset,u.MaterialInstanceConstant):
        stats=LIB.get_statistics(asset);assert stats.num_pixel_shader_instructions>0,path
        result['mi_shader_permutations'].append(dict(path=path,pixel_instructions=stats.num_pixel_shader_instructions))
result.update(status='passed',camera_duration=cam.get_editor_property('oscillation_duration'),player_received_hit=None,asset_saves=0)
(OUT/'Audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.SystemLibrary.quit_editor()
