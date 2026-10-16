"""Finish only the original untextured card; never repeat completed parent edits."""
from pathlib import Path
import ast, hashlib, json, os
import unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']);PROJECT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_ALPHA_OUT'])
assert PROJECT==MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
plan=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
LIB=u.MaterialEditingLibrary;EAL=u.EditorAssetLibrary;R={'status':'running','files':[],'masters':[]}
source=MAIN/'Scripts/Art/author_particle_alpha_repairs_20261013.py'
tree=ast.parse(source.read_text());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
exec(compile(ast.Module(body=defs,type_ignores=[]),str(source),'exec'),globals())
mat=u.load_asset(plan['default_particle']);assert not EAL.get_metadata_tag(mat,'KZAlphaRepair20261013')
prop=u.MaterialProperty.MP_OPACITY_MASK
original=LIB.get_material_property_input_node(mat,prop);assert original
output=LIB.get_material_property_input_node_output_name(mat,prop)
enable=scalar(mat,'KZAlphaCardRepair',1);mask=edge(mat,enable,True)
bound=LIB.create_material_expression(mat,u.MaterialExpressionSaturate,800,100)
assert LIB.connect_material_expressions(original,output,bound,'')
mul=LIB.create_material_expression(mat,u.MaterialExpressionMultiply,1100,100)
assert LIB.connect_material_expressions(bound,'',mul,'A');assert LIB.connect_material_expressions(mask,'',mul,'B')
assert LIB.connect_material_property(mul,'',prop)
assert not list(LIB.recompile_material(mat))
EAL.set_metadata_tag(mat,'KZAlphaRepair20261013','Untextured card lacked spatial alpha. Soft ellipse power2 and inward .03UV/1.25px edge; existing Masked blend retained. Assistant TEMP visual repair. Original RGB and particle data retained.')
save(mat);R['status']='passed';R['masters'].append({'path':plan['default_particle'],'property':str(prop),'blend_mode_preserved':True,'ellipse_power':2})
(OUT/'AlphaApplied.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('UNTEXTURED_SPATIAL_ALPHA_FIXED',flush=True)
