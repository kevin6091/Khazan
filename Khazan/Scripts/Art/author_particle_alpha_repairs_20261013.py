"""Exact selected alpha repairs; original particle data/texture/RGB outputs retained."""
from pathlib import Path
import collections, hashlib, json, os, re
import unreal as u
MAIN=Path(os.environ['KZ_ALPHA_MAIN']); PROJECT=Path(u.Paths.project_dir()).resolve(); OUT=Path(os.environ['KZ_ALPHA_OUT'])
assert PROJECT==MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan'
plan=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text())
audit=json.loads((MAIN/'Metadata/ParticleAlpha_20261013/Audit02/Audit.json').read_text(encoding='utf-8'))
records={r['path']:r for r in audit['materials']}; LIB=u.MaterialEditingLibrary; EAL=u.EditorAssetLibrary
R={'status':'running','masters':[],'instances':[],'files':[],'source_particle_texture_animation_map_writes':0}
by=collections.defaultdict(list)
for row in plan['rows']:by[row['master']].append(row)

def save(asset):
    path=asset.get_path_name().split('.',1)[0]; file=PROJECT/('Content/'+path.removeprefix('/Game/')+'.uasset')
    assert path in plan['targets'] and file.resolve().is_relative_to(PROJECT)
    assert EAL.save_loaded_asset(asset,only_if_is_dirty=False)
    R['files'].append({'path':path,'relative':str(file.relative_to(PROJECT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    (OUT/'AlphaApplied.json').write_text(json.dumps(R,indent=2),encoding='utf-8')

def scalar(mat,name,value):
    node=LIB.create_material_expression(mat,u.MaterialExpressionScalarParameter,-200,600)
    node.set_editor_property('parameter_name',name);node.set_editor_property('default_value',value);return node

def custom(mat,names,code,description):
    node=LIB.create_material_expression(mat,u.MaterialExpressionCustom,700,600)
    inputs=[]
    for name in names:
        x=u.CustomInput();x.set_editor_property('input_name',name);inputs.append(x)
    node.set_editor_property('inputs',inputs);node.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    node.set_editor_property('code',code);node.set_editor_property('description',description);return node

def edge(mat,enabled,ellipse=False):
    uv=LIB.create_material_expression(mat,u.MaterialExpressionTextureCoordinate,100,600)
    width=scalar(mat,'KZAlphaEdgeFeatherUV',.03);pixels=scalar(mat,'KZAlphaEdgeSoftnessPixels',1.25)
    code='float2 d=min(UV,1.0-UV); float w=max(Width,max(fwidth(UV.x),fwidth(UV.y))*Pixels); float e=smoothstep(0.0,max(w,0.00001),min(d.x,d.y));'
    if ellipse:code+='float2 p=UV*2.0-1.0; e*=pow(saturate(1.0-dot(p,p)),2.0);'
    node=custom(mat,['UV','Width','Pixels','Enabled'],code+'return lerp(1.0,e,saturate(Enabled));','KZAlphaRepair20261013: inward card feather; TEMP .03 UV / minimum 1.25 pixels; untextured ellipse power2')
    for source,pin in ((uv,'UV'),(width,'Width'),(pixels,'Pixels'),(enabled,'Enabled')):assert LIB.connect_material_expressions(source,'',node,pin)
    return node

for path, rows in by.items():
    mat=u.load_asset(path); assert mat
    if EAL.get_metadata_tag(mat,'KZAlphaRepair20261013'):
        # Resume after a saved parent/partial instance batch; never append nodes twice.
        file=PROJECT/('Content/'+path.removeprefix('/Game/')+'.uasset')
        R['files'].append({'path':path,'relative':str(file.relative_to(PROJECT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
        for row in rows:
            parameter='KZAlphaFromRed_'+re.sub(r'\W','_',row['parameter'] or row['texture'].rsplit('/',1)[-1].split('.')[0])
            mi=u.load_asset(row['material']);LIB.set_material_instance_scalar_parameter_value(mi,parameter,1);LIB.set_material_instance_scalar_parameter_value(mi,'KZAlphaCardRepair',1)
            assert LIB.get_material_instance_scalar_parameter_value(mi,parameter)==1 and LIB.get_material_instance_scalar_parameter_value(mi,'KZAlphaCardRepair')==1
            save(mi);R['instances'].append({'path':row['material'],'red_density_parameter':parameter,'repair_enabled':1})
        R['masters'].append({'path':path,'resumed_saved_parent':True,'default_enable':0,'affected_instances':[r['material'] for r in rows]})
        continue
    nodes={n.get_name():n for n in LIB.get_material_expressions(mat)}
    original_opacity=LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY)
    original_output=LIB.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_OPACITY)
    original_emissive=LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert original_opacity and not any('KZAlphaRepair20261013' in str(n.get_editor_property('description')) for n in nodes.values() if isinstance(n,u.MaterialExpressionCustom))
    enabled=scalar(mat,'KZAlphaCardRepair',0)
    fixed={}; instance_parameters={}
    for row in rows:
        # One scalar controls the exact sampled texture's channel, default0 keeps
        # all other inherited instances on the existing source-A path.
        parameter='KZAlphaFromRed_'+re.sub(r'\W','_',row['parameter'] or row['texture'].rsplit('/',1)[-1].split('.')[0])
        if parameter not in fixed:fixed[parameter]=scalar(mat,parameter,0)
        instance_parameters[row['material']]=parameter
        for link in row['alpha_links']:
            key=(link['parent'],link['line'])
            if key in fixed:continue
            m=re.search(r'^([^=]+)=.*?:([^:\'"/]+)\'[\"]',link['line'])
            assert m,(path,link)
            pin,texture_name=m.group(1),m.group(2);texture=nodes[texture_name];parent=nodes[link['parent']]
            mask=custom(mat,['Red','OriginalAlpha','UseRed'],'return lerp(OriginalAlpha,saturate(Red),saturate(UseRed));','KZAlphaRepair20261013: sampled constant-A255 mask uses source R density only for selected instances')
            assert LIB.connect_material_expressions(texture,'R',mask,'Red')
            assert LIB.connect_material_expressions(texture,'A',mask,'OriginalAlpha')
            assert LIB.connect_material_expressions(fixed[parameter],'',mask,'UseRed')
            assert LIB.connect_material_expressions(mask,'',parent,pin)
            fixed[key]=mask
    # Keep source HDR RGB; bound only the particle Alpha channel before its mask.
    raw=(MAIN/'Metadata/ParticleAlpha_20261013/Audit02'/records[path]['export']).read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r','')
    alpha_names={n['name'] for r in rows for n in next(t['alpha_nodes'] for t in json.loads((MAIN/'Metadata/ParticleAlpha_20261013/MaterialTriage.json').read_text())['rows'] if t['path']==r['material'])}
    for parent,body in re.findall(r'Begin Object Name="([^"]+)"[^\n]*\n(.*?)End Object',text,re.S):
        if parent not in alpha_names:continue
        for line in body.splitlines():
            m=re.search(r'^\s*([^=]+)=.*?:([^:\'"/]+)\'[\"].*OutputIndex=4',line)
            if not m or m.group(2) not in nodes or not isinstance(nodes[m.group(2)],u.MaterialExpressionParticleColor):continue
            bound=custom(mat,['Alpha','Enabled'],'return lerp(Alpha,saturate(Alpha),saturate(Enabled));','KZAlphaRepair20261013: selected cards bound particle Alpha before spatial mask; HDR RGB unchanged')
            assert LIB.connect_material_expressions(nodes[m.group(2)],'A',bound,'Alpha')
            assert LIB.connect_material_expressions(enabled,'',bound,'Enabled')
            assert LIB.connect_material_expressions(bound,'',nodes[parent],m.group(1).strip())
    feather=edge(mat,enabled)
    mul=LIB.create_material_expression(mat,u.MaterialExpressionMultiply,1100,400)
    assert LIB.connect_material_expressions(original_opacity,original_output,mul,'A')
    assert LIB.connect_material_expressions(feather,'',mul,'B');assert LIB.connect_material_property(mul,'',u.MaterialProperty.MP_OPACITY)
    assert LIB.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)==original_emissive
    EAL.set_metadata_tag(mat,'KZAlphaRepair20261013','Instance-selective constant-A mask/R density + bound particle Alpha + inward .03UV/1.25px feather. Source texture/RGB/particle/animation preserved; TEMP visual adapter, not original shader parity.')
    errors=list(LIB.recompile_material(mat));assert not errors,errors;save(mat)
    R['masters'].append({'path':path,'emissive_output_retained':True,'default_enable':0,'affected_instances':list(instance_parameters)})
    for leaf,parameter in instance_parameters.items():
        mi=u.load_asset(leaf);assert isinstance(mi,u.MaterialInstanceConstant)
        # UE5.8 setter's C++ bResult remains false even after it sets the value.
        # Read the applied parameter instead of treating that return as success.
        LIB.set_material_instance_scalar_parameter_value(mi,parameter,1)
        LIB.set_material_instance_scalar_parameter_value(mi,'KZAlphaCardRepair',1)
        assert LIB.get_material_instance_scalar_parameter_value(mi,parameter)==1
        assert LIB.get_material_instance_scalar_parameter_value(mi,'KZAlphaCardRepair')==1
        LIB.update_material_instance(mi);save(mi)
        R['instances'].append({'path':leaf,'red_density_parameter':parameter,'repair_enabled':1})
    (OUT/'AlphaApplied.json').write_text(json.dumps(R,indent=2),encoding='utf-8')

mat=u.load_asset(plan['default_particle']);alpha_property=u.MaterialProperty.MP_OPACITY
original=LIB.get_material_property_input_node(mat,alpha_property)
if not original:alpha_property=u.MaterialProperty.MP_OPACITY_MASK;original=LIB.get_material_property_input_node(mat,alpha_property)
output=LIB.get_material_property_input_node_output_name(mat,alpha_property);assert original
enabled=scalar(mat,'KZAlphaCardRepair',1);mask=edge(mat,enabled,True)
saturate=LIB.create_material_expression(mat,u.MaterialExpressionSaturate,800,100)
assert LIB.connect_material_expressions(original,output,saturate,'')
mul=LIB.create_material_expression(mat,u.MaterialExpressionMultiply,1100,100)
assert LIB.connect_material_expressions(saturate,'',mul,'A');assert LIB.connect_material_expressions(mask,'',mul,'B')
assert LIB.connect_material_property(mul,'',alpha_property)
EAL.set_metadata_tag(mat,'KZAlphaRepair20261013','Untextured card had no spatial opacity. Soft elliptic alpha power2 + inward .03UV/1.25px feather, particle alpha bounded. Assistant TEMP visual repair; source particle RGB/geometry/lifetime unchanged.')
assert not list(LIB.recompile_material(mat));save(mat)
R['masters'].append({'path':plan['default_particle'],'untextured_spatial_alpha':True,'ellipse_power':2,'existing_alpha_property':str(alpha_property)})
R['status']='passed';(OUT/'AlphaApplied.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('ALPHA_REPAIRS_APPLIED masters',len(R['masters']),'instances',len(R['instances']),flush=True)
