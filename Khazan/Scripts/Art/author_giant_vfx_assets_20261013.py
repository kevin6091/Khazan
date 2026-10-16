"""Scoped world-unit flags and owned alpha-safe particle/material copies."""
from pathlib import Path
from collections import defaultdict
import unreal as u
import os, json, re, hashlib, ast

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve();assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish'
probe=json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
catalog=json.loads((main/'Metadata/GiantVFX_20261013/ParticleObjectCatalog.json').read_text(encoding='utf-8'))
alpha_plan=json.loads((main/'Metadata/ParticleAlpha_20261013/RepairPlan.json').read_text(encoding='utf-8'))
lib=u.MaterialEditingLibrary;tools=u.AssetToolsHelpers.get_asset_tools();eal=u.EditorAssetLibrary
report={'status':'running','particles':{},'materials':{},'changed_sequences':[],'definitions':[],
        'temporary_presentation':{'edge_feather_uv':.03,'edge_softness_pixels':1.25,'depth_fade_cm':12.0},'saved':[]}
rows_by_material={r['material']:r for r in alpha_plan['rows']}
by_master=defaultdict(list)
for row in alpha_plan['rows']:by_master[row['master']].append(row)
helper_source=(main/'Scripts/Art/author_particle_alpha_repairs_20261013.py').read_text(encoding='utf-8')
tree=ast.parse(helper_source);LIB=lib
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'scalar','custom','edge'}],type_ignores=[]),'<existing alpha graph helpers>','exec'),globals())
def save(asset):
    file=work/('Content/'+asset.get_path_name().split('.',1)[0].removeprefix('/Game/')+'.uasset')
    assert file.resolve().is_relative_to(work)
    assert eal.save_loaded_asset(asset,only_if_is_dirty=False)
    report['saved'].append(asset.get_path_name())
    (out/'Progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def duplicate(asset,folder):
    suffix=hashlib.sha256(asset.get_path_name().encode()).hexdigest()[:8]
    name='KZ_'+asset.get_name()+'_'+suffix
    assert not eal.does_asset_exist(folder+'/'+name),'Do not rerun a completed author batch'
    return tools.duplicate_asset(name,folder,asset)
masters={};materials={}
def owned_material(source):
    key=source.get_path_name().split('.',1)[0]
    if key in materials:return materials[key]
    if isinstance(source,u.MaterialInstanceConstant):
        parent=source.get_editor_property('parent');owned_parent=owned_material(parent)
        if owned_parent is parent:materials[key]=source;return source
        result=duplicate(source,root+'/Materials');lib.set_material_instance_parent(result,owned_parent)
        row=rows_by_material.get(key)
        if row:
            parameter='KZAlphaFromRed_'+re.sub(r'\W','_',row['parameter'] or row['texture'].rsplit('/',1)[-1].split('.')[0])
            lib.set_material_instance_scalar_parameter_value(result,parameter,1)
        lib.set_material_instance_scalar_parameter_value(result,'KZAlphaCardRepair',1)
        lib.update_material_instance(result);save(result);materials[key]=result
    elif isinstance(source,u.Material):
        original=lib.get_material_property_input_node(source,u.MaterialProperty.MP_OPACITY)
        if not original:materials[key]=source;return source # Opaque mesh shaders are preserved.
        result=duplicate(source,root+'/Materials');nodes={n.get_name():n for n in lib.get_material_expressions(result)}
        old_opacity=lib.get_material_property_input_node(result,u.MaterialProperty.MP_OPACITY)
        old_output=lib.get_material_property_input_node_output_name(result,u.MaterialProperty.MP_OPACITY)
        emissive=lib.get_material_property_input_node(result,u.MaterialProperty.MP_EMISSIVE_COLOR)
        enabled=scalar(result,'KZAlphaCardRepair',1)
        fixed={}
        if not eal.get_metadata_tag(source,'KZAlphaRepair20261013'):
            for row in by_master.get(key,[]):
                parameter='KZAlphaFromRed_'+re.sub(r'\W','_',row['parameter'] or row['texture'].rsplit('/',1)[-1].split('.')[0])
                switch=fixed.setdefault(parameter,scalar(result,parameter,1))
                for link in row['alpha_links']:
                    marker=(link['parent'],link['line'])
                    if marker in fixed:continue
                    m=re.search(r'^([^=]+)=.*?:([^:\'"/]+)\'[\"]',link['line']);assert m,link
                    pin,name=m.group(1),m.group(2)
                    mask=custom(result,['Red','OriginalAlpha','UseRed'],'return lerp(OriginalAlpha,saturate(Red),saturate(UseRed));','Giant owned mask: original constant-A255 uses R density')
                    assert lib.connect_material_expressions(nodes[name],'R',mask,'Red')
                    assert lib.connect_material_expressions(nodes[name],'A',mask,'OriginalAlpha')
                    assert lib.connect_material_expressions(switch,'',mask,'UseRed')
                    assert lib.connect_material_expressions(mask,'',nodes[link['parent']],pin)
                    fixed[marker]=mask
        feather=edge(result,enabled,key.endswith('/DefaultParticle'))
        fade=lib.create_material_expression(result,u.MaterialExpressionDepthFade)
        distance=scalar(result,'KZGiantDepthFadeCm',12.0)
        assert lib.connect_material_expressions(distance,'',fade,'FadeDistance')
        assert lib.connect_material_expressions(old_opacity,old_output,fade,'Opacity')
        multiply=lib.create_material_expression(result,u.MaterialExpressionMultiply)
        assert lib.connect_material_expressions(fade,'',multiply,'A')
        assert lib.connect_material_expressions(feather,'',multiply,'B')
        assert lib.connect_material_property(multiply,'',u.MaterialProperty.MP_OPACITY)
        assert lib.get_material_property_input_node(result,u.MaterialProperty.MP_EMISSIVE_COLOR)==emissive
        eal.set_metadata_tag(result,'KZGiantVFX20261013','Owned copy; original RGB preserved; constant-A mask repair, UV/pixel feather, 12cm TEMP depth fade. Not original shader parity.')
        errors=list(lib.recompile_material(result));assert not errors,errors
        save(result);materials[key]=result
    else:materials[key]=source
    report['materials'][key]=materials[key].get_path_name();return materials[key]

for original in probe['systems']:
    source=u.load_asset(original);system=duplicate(source,root+'/Particles')
    old_package=source.get_path_name();new_package=system.get_path_name()
    entry=catalog[source.get_name()+'.t3d']
    helpers=[]
    for object_path,data in entry.items():
        if data['class'] and data['class'].endswith('.ParticleModuleRequired'):
            required=u.load_object(None,object_path.replace(old_package,new_package,1));assert required
            material=required.get_editor_property('Material')
            if material:required.set_editor_property('Material',owned_material(material))
        if data['class'] and data['class'].endswith('.ParticleModuleTypeDataMesh'):
            mesh=u.load_object(None,object_path.replace(old_package,new_package,1))
            asset=mesh.get_editor_property('Mesh')
            if asset and asset.get_name()=='FS_axis':helpers.append(object_path)
    eal.set_metadata_tag(system,'KZGiantVFX20261013','Original emitter/module/timing/texture data retained; scoped material copies. World-cm units are selected on the actual consumer.')
    save(system);report['particles'][original]=system.get_path_name()
    if helpers:report.setdefault('helper_mesh_review',[]).append({'system':system.get_path_name(),'objects':helpers})

for asset in probe['sequences']:
    sequence=u.load_asset(asset);changed=False
    for event in u.AnimationLibrary.get_animation_notify_events(sequence):
        state=event.get_editor_property('notify_state_class')
        if state and state.get_class().get_name()=='KZAnimNotifyState_MonsterVisual':
            effect=state.get_editor_property('Effect')
            if not effect:continue
            ps=effect.get_editor_property('ParticleTemplate')
            if ps and ps.get_path_name() in report['particles']:
                effect.set_editor_property('ParticleTemplate',u.load_asset(report['particles'][ps.get_path_name()]))
                effect.set_editor_property('bUseWorldParticleUnits',True);changed=True
            routes=list(effect.get_editor_property('SurfaceRoutes'))
            for route in routes:
                ps=route.get_editor_property('ParticleTemplate')
                if ps and ps.get_path_name() in report['particles']:
                    route.set_editor_property('ParticleTemplate',u.load_asset(report['particles'][ps.get_path_name()]))
                    effect.set_editor_property('bUseWorldParticleUnits',True);changed=True
            if routes:effect.set_editor_property('SurfaceRoutes',routes)
    if changed:save(sequence);report['changed_sequences'].append(sequence.get_path_name())
report['status']='passed'
(out/'Author.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('GIANT_VFX_ASSETS_AUTHORED '+str(len(report['particles']))+' particles / '+str(len(report['changed_sequences']))+' clips')
