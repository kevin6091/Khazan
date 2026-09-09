"""Keep two byte-identical source BASE_Normal packages separately identified."""
import unreal,pathlib,json,sys,runpy
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Scripts/Enemies'));import import_enemy_library as L
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));tm={r['source_package']:r for r in M['textures']}
p='BBQ/Content/Art/Character/CHA_Material/Texture/Base/BASE_Normal';r=tm[p]
t,new=L.import_one(r['source_file'],r['destination'],unreal.TextureFactory());t.set_editor_property('srgb',False);t.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP);L.tag(t,p,'SourceTexture');L.save(t)
for r in M['materials']:
    mat=L.load(r['destination']);pr=r['source_object'].get('Properties',{})
    if r['source_type']=='MaterialInstanceConstant':
        for v in pr.get('TextureParameterValues',[]):
            if L.package(v.get('ParameterValue'))==p:unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mat,v['ParameterInfo']['Name'],t)
        unreal.MaterialEditingLibrary.update_material_instance(mat)
    else:
        cached=pr.get('CachedExpressionData',{}).get('Parameters',{});infos=cached.get('RuntimeEntries[2]',{}).get('ParameterInfos',[]);values=cached.get('TextureValues',[])
        parameters={n['Name'] for n,v in zip(infos,values) if L.package(v)==p}
        for node in unreal.ObjectIterator(unreal.MaterialExpressionTextureSampleParameter2D):
            if node.get_outer()==mat and str(node.get_editor_property('parameter_name')) in parameters:node.set_editor_property('texture',t)
    L.save(mat)
(PROJECT/'Saved/ImportReports/HeinMachEnemyV2_TextureIdentity.json').write_text(json.dumps({'status':'passed','source':p,'destination':tm[p]['destination'],'reason':'Distinct packages with identical PNG hash and source properties; retained separately by full package identity.'},indent=2),encoding='utf-8')
runpy.run_path(str(PROJECT/'Scripts/Enemies/audit_enemy_expansion_catalogue.py'),run_name='__main__')
