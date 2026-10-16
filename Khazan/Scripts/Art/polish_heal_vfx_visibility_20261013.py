"""Local VFX exposure response and original renderer mesh pivot; no map lighting edits."""
from pathlib import Path
import json, os, unreal as u
MAIN=Path(__file__).resolve().parents[2];WORK=Path(u.Paths.project_dir()).resolve()
assert WORK==MAIN.parent.parent/'Khazan_HealVFXWork_20261013/Khazan'
OUT=Path(os.environ['KZ_HEAL_VFX_OUT']);L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
report=dict(status='running',materials=[],source_pivot={},saved=[])
for name in ['M_Heal_SoftGlow','M_Heal_OriginalTrail','M_Heal_CoreFresnel']:
    m=u.load_asset('/Game/HealVFX/Materials/'+name);assert m
    assert not E.get_metadata_tag(m,'KZHealExposureCompensation'), 'Preserve completed polish'
    previous=L.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
    output=L.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
    inverse=L.create_material_expression(m,u.MaterialExpressionEyeAdaptationInverse)
    amount=L.create_material_expression(m,u.MaterialExpressionScalarParameter)
    amount.set_editor_property('parameter_name','ExposureCompensation');amount.set_editor_property('default_value',1.0)
    assert L.connect_material_expressions(previous,output,inverse,'LightValueInput')
    assert L.connect_material_expressions(amount,'',inverse,'AlphaInput')
    assert L.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=L.recompile_material(m);assert not errors
    E.set_metadata_tag(m,'KZHealExposureCompensation','TEMP display adapter: Alpha=1 cancels scene auto-exposure on this effect emissive only. Native source Niagara/material graph unavailable. No level light/exposure changes.')
    assert E.save_loaded_asset(m,only_if_is_dirty=False)
    report['materials'].append(dict(path=m.get_path_name(),errors=str(errors),amount=1.0));report['saved'].append(m.get_path_name())
ps=u.load_asset('/Game/HealVFX/Particles/PS_Heal_GhostArm')
emitter=u.FXConverterUtilitiesLibrary.get_cascade_system_emitters(ps)[0]
lod=u.FXConverterUtilitiesLibrary.get_cascade_emitter_lod_level(emitter,0)
required=u.FXConverterUtilitiesLibrary.get_lod_level_required_module(lod)
required.set_editor_property('emitter_origin',u.Vector(0,3,0))
assert E.save_loaded_asset(ps,only_if_is_dirty=False)
report['source_pivot']=dict(original_file='Metadata/HealVFX_20261013/Original/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/PC/Recovery/FP_KazanGhostHand_Init.json',export_index=174,field='Properties.Meshes[0].PivotOffset',raw=[0,3,0],units='mesh centimetres',adapter='ParticleModuleRequired.EmitterOrigin on the corresponding source small-ring emitter',particle_scale=[4,1,1])
report['saved'].append(ps.get_path_name());report['status']='passed'
(OUT/'Polish.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAL_VFX_EXPOSURE_POLISH',report['status'],flush=True)
