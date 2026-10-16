"""Private variants: preserve wine blood exposure and reject vertical receiver pixels."""
from pathlib import Path
import unreal, os, json, traceback
root=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(root)
out=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary
d={'status':'running','saved':[]}
def create(m,cls,**props):
    n=lib.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin):assert lib.connect_material_expressions(a,'',b,pin)
def save(m):
    lib.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    d['saved'].append(m.get_path_name())
try:
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodFluid');assert m
    nodes=lib.get_material_expressions(m)
    for n in nodes:
        if isinstance(n,unreal.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='BloodColor':
            # TEMP photo-based linear wine tint. Exposure conversion is engine-owned.
            n.set_editor_property('default_value',unreal.LinearColor(.12,.004,.009,1))
    color=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_BASE_COLOR);assert color
    assert not any(isinstance(n,unreal.MaterialExpressionEyeAdaptationInverse) for n in nodes)
    exposure=create(m,unreal.MaterialExpressionEyeAdaptationInverse)
    wire(color,exposure,'');assert lib.connect_material_property(exposure,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    save(m)
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround');assert m
    opacity=lib.get_material_property_input_node(m,unreal.MaterialProperty.MP_OPACITY);assert opacity
    inputs=list(opacity.get_editor_property('inputs'))
    assert 'Position' not in [str(i.get_editor_property('input_name')) for i in inputs]
    for name in ['Position','Walkable']:
        i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    opacity.set_editor_property('inputs',inputs)
    opacity.set_editor_property('code','float a=Channel<.5?Mask.r:(Channel<1.5?Mask.g:Mask.b);float3 n=normalize(cross(ddx(Position),ddy(Position)));return saturate(pow(saturate(a),Power)*Density)*Fade*step(Walkable,abs(n.z));')
    wire(create(m,unreal.MaterialExpressionWorldPosition),opacity,'Position')
    # Initialization only. The producer writes the actual CMC threshold before rendering.
    wire(create(m,unreal.MaterialExpressionScalarParameter,parameter_name='BloodWalkableFloorZ',default_value=0),opacity,'Walkable')
    save(m)
    d.update(status='passed',fluid_color_linear=[.12,.004,.009],exposure='Engine EyeAdaptationInverse full conversion (default Alpha=1)',surface_mask='Absolute rendered-depth WorldPosition derivatives; abs(normal.Z)>=existing CMC WalkableFloorZ; no new slope tuning',reference_status='photo-based tint, not original shader restoration')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(out/'SurfaceFinish.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
