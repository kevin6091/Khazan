"""Narrow private finalization and saved readback; do not touch original textures or other VFX."""
from pathlib import Path
import os,json,traceback,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT'])
d={'status':'running','asset_saves':0,'materials':[]}
try:
    a=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodSheet');assert a
    if 'Khazan_GiantFallWork_20261011' in str(ROOT):
        unreal.MaterialEditingLibrary.set_material_usage(a,unreal.MaterialUsage.MATUSAGE_PARTICLE_SPRITES)
        unreal.MaterialEditingLibrary.recompile_material(a)
        assert unreal.EditorAssetLibrary.save_loaded_asset(a,only_if_is_dirty=False);d['asset_saves']+=1
        for mat_name,source_name,mask_name in [('M_Monster_HitBloodGround','FT_Decal_Blood_A_003','FT_Monster_HitBloodGroundMask'),('M_Monster_HitBloodSheet','FT_Decal_Blood_004','FT_Monster_HitBloodSheetMask')]:
            # Original source JSON SRGB=false; existing importer left SRGB=true. Keep original assets byte intact.
            original=unreal.load_asset('/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Decal/'+source_name)
            mask=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+mask_name)
            if not mask:mask=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(mask_name,'/Game/_Art/Effects/Combat/Blood',original)
            mask.set_editor_property('srgb',False)
            assert unreal.EditorAssetLibrary.save_loaded_asset(mask,only_if_is_dirty=False);d['asset_saves']+=1
            mat=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+mat_name)
            for n in unreal.MaterialEditingLibrary.get_material_expressions(mat):
                if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D):
                    n.set_editor_property('texture',mask);n.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            unreal.MaterialEditingLibrary.recompile_material(mat)
            assert unreal.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False);d['asset_saves']+=1
    for name in ['M_Monster_HitBloodGround','M_Monster_HitBloodSheet']:
        m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+name);assert m
        nodes=unreal.MaterialEditingLibrary.get_material_expressions(m)
        scalars={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in nodes if isinstance(n,unreal.MaterialExpressionScalarParameter)}
        textures=[n.get_editor_property('texture').get_path_name() for n in nodes if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D)]
        codes=[n.get_editor_property('code') for n in nodes if isinstance(n,unreal.MaterialExpressionCustom)]
        d['materials'].append({'asset':m.get_path_name(),'domain':str(m.get_editor_property('material_domain')),'scalars':scalars,'textures':textures,'code':codes,'decal_fade_node':any(isinstance(n,unreal.MaterialExpressionDecalLifetimeOpacity) for n in nodes)})
        assert 'Mask.a' not in '\n'.join(codes),'Opaque packed alpha cannot be a mask'
    assert d['materials'][0]['decal_fade_node']
    if ROOT.name=='Khazan' and 'Khazan_GiantFallWork_20261011' not in str(ROOT):
        for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
            c=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+family+'.BP_Monster_'+family+'_C');assert c
            a=unreal.get_default_object(c);assert a.get_editor_property('HitBloodDecalMaterial')
            assert a.get_editor_property('HitBloodEffect').get_name()=='FP_Monster_HitBloodReference',family
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'AssetReadback.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
