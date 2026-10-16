"""Reuse the validated Cascade importer for task-owned HeinMach fire packages."""
from pathlib import Path
import ast
import json
import traceback
import struct
import math
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
BASE=MAIN/'Saved/Extracted/HeinMachTutorialFires_20261006'
META=ROOT/'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
DEST='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires'
META.mkdir(parents=True,exist_ok=True)
all_rows=json.loads((BASE/'AssetManifest.json').read_text(encoding='utf-8'))

# Reuse existing, tested functions without invoking their combat-specific CLI.
# This is editor automation only; no new gameplay class or runtime helper.
script=MAIN/'Scripts/Art/combat_effects_import.py'
tree=ast.parse(script.read_text(encoding='utf-8'))
tree.body=[n for n in tree.body if not isinstance(n,ast.Try)]
g={'__file__':str(script)}
exec(compile(tree,str(script),'exec'),g)
for row in all_rows:
    row['source_json']=str(MAIN/row['source_json'])
    if row['source_package'].startswith('Engine/Content/'):
        row['destination']='/Engine/'+row['source_package'][len('Engine/Content/'):]
        row['reuse_existing']=True
g.update(ROOT=ROOT,BASE=BASE,META=META,ROWS=all_rows,LOOKUP={r['source_package']:r for r in all_rows},PHASE='dependencies')


def save(obj):
    assert obj.get_path_name().startswith(DEST+'/'),obj.get_path_name()
    assert unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False),obj


original_put=g['put']
code=ast.parse(script.read_text(encoding='utf-8'))
put_ast=next(n for n in code.body if isinstance(n,ast.FunctionDef) and n.name=='put')
# Retain exact-object SETNOPEC safeguards; authorize only this task's assets.
for n in ast.walk(put_ast):
    if isinstance(n,ast.Constant) and n.value=='/Game/_Art/Effects/':n.value=DEST+'/'
exec(compile(ast.fix_missing_locations(ast.Module(body=[put_ast],type_ignores=[])),str(script),'exec'),g)
g['save']=save


def parameters(original):
    cached=original.get('CachedExpressionData',original.get('Properties',{}).get('CachedExpressionData',{})).get('Parameters',{})
    return {values:dict(zip([p['Name'] for p in cached.get(entries,{}).get('ParameterInfos',[])],cached.get(values,[])))
            for entries,values in [('RuntimeEntries','ScalarValues'),('RuntimeEntries[1]','VectorValues'),('RuntimeEntries[2]','TextureValues')]}


g['parameters']=parameters
LIB=unreal.MaterialEditingLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()


def profile(row):
    # UE IESLoader.cpp samples H=y*360/256, V=x*180/256, then stores half.
    # Use original inline half bits, avoiding RGBE mantissa/alpha precision loss.
    original=g['source'](row)
    assert original['PixelFormat']=='PF_FloatRGBA' and original['SizeX']==256
    height=original['SizeY'];assert height in (1,256)
    raw=BASE/'OriginalRaw'/row['source_package']
    blob=raw.with_suffix('.uexp').read_bytes();header=raw.with_suffix('.uasset').read_bytes()
    count=256*height*8
    assert blob[-4:]==struct.pack('<I',0x9e2a83c1)
    signature=struct.pack('<III',0x48,count,count);hits=[];start=0
    while True:
        pos=blob.find(signature,start)
        if pos<0:break
        off=pos+20
        if blob[off+count:off+count+12]==struct.pack('<III',256,height,1):hits.append(off)
        start=pos+1
    assert len(hits)==1,(row['name'],hits)
    offset=hits[0]
    samples=list(struct.iter_unpack('<eeee',blob[offset:offset+count]))
    values=[v[0] for v in samples]
    assert all(math.isfinite(v) and 0<=v<=1 for v in values)
    ies=BASE/'IES'/(row['name']+'.ies');ies.parent.mkdir(exist_ok=True)
    # Normalization sentinel at 180 degrees is outside the runtime 256 texels.
    angles=[i*180/256 for i in range(256)]+[180]
    horizontal=[i*360/256 for i in range(256)]+[360] if height==256 else [0]
    rows=[values[y*256:(y+1)*256]+[1.0] for y in range(height)]
    if height==256:rows.append(rows[0])
    lines=['IESNA:LM-63-2002','[TEST] Original cooked HeinMach profile lookup','TILT=NONE',
           '1 1000 1 257 '+str(len(horizontal))+' 1 1 0 0 0','1 1 0',' '.join(map(str,angles)),' '.join(map(str,horizontal)),
           ' '.join(str(v) for r in rows for v in r)]
    ies.write_text('\n'.join(lines)+'\n',encoding='ascii')
    obj=g['payload'](row,[ies],unreal.TextureFactory(),force=True)
    assert isinstance(obj,unreal.TextureLightProfile),obj
    props=g['source'](row).get('Properties',{})
    for k in ('Brightness','TextureMultiplier'):
        if k in props:g['put'](obj,k,props[k])
    save(obj)
    g['REPORT']['assets'].append({'source':row['source_package'],'destination':row['destination'],'type':'TextureLightProfile','lookup_samples':len(values),'source_height':height,'original_brightness':props.get('Brightness'),'boundary':'Original inline red half values mapped to UE IES angular sampling; original LM-63 source unavailable.'})


def world_master(row):
    m=g['make'](row,unreal.Material,unreal.MaterialFactoryNew())
    LIB.delete_all_material_expressions(m)
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    defaults=parameters(g['source'](row))
    descendants=[r for r in all_rows if r['source_type']=='MaterialInstanceConstant' and '/World_Material/' in r['source_package']]
    for r in descendants:
        for k,slot in [('TextureParameterValues','TextureValues'),('ScalarParameterValues','ScalarValues'),('VectorParameterValues','VectorValues')]:
            for v in g['source'](r).get('Properties',{}).get(k,[]):defaults[slot].setdefault(v['ParameterInfo']['Name'],v['ParameterValue'])
    nodes={}
    for i,(name,value) in enumerate(defaults['TextureValues'].items()):
        tex=g['ref'](value)
        if not tex or not isinstance(tex,unreal.Texture2D):continue
        n=LIB.create_material_expression(m,unreal.MaterialExpressionTextureSampleParameter2D,-600,i*160)
        n.set_editor_property('parameter_name',name);n.set_editor_property('texture',tex);n.set_editor_property('sampler_type',g['sampler'](tex));nodes[name]=n
    print('World texture parameters',list(nodes))
    base=next((nodes[n] for n in ('Tex_D','BaseColor Texture','BaseColorTexture','BaseColorMap','BaseColor','Diffuse Texture','DiffuseTexture','Texture_D') if n in nodes),None)
    if base is None:base=next((v for k,v in nodes.items() if 'base' in k.lower() or 'diffuse' in k.lower()),None)
    assert base, list(nodes)
    LIB.connect_material_property(base,'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
    normal=nodes.get('Tex_N') or next((v for k,v in nodes.items() if 'normal' in k.lower()),None)
    packed=nodes.get('Tex_S') or next((v for k,v in nodes.items() if 'orm' in k.lower() or 'specular' in k.lower() or 'mask' in k.lower()),None)
    if normal:LIB.connect_material_property(normal,'RGB',unreal.MaterialProperty.MP_NORMAL)
    if packed:
        LIB.connect_material_property(packed,'R',unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
        LIB.connect_material_property(packed,'G',unreal.MaterialProperty.MP_ROUGHNESS)
        LIB.connect_material_property(packed,'B',unreal.MaterialProperty.MP_METALLIC)
    for slot,typ in [('ScalarValues',unreal.MaterialExpressionScalarParameter),('VectorValues',unreal.MaterialExpressionVectorParameter)]:
        for name,value in defaults[slot].items():
            n=LIB.create_material_expression(m,typ);n.set_editor_property('parameter_name',name)
            n.set_editor_property('default_value',value if slot=='ScalarValues' else unreal.LinearColor(value['R'],value['G'],value['B'],value.get('A',1)))
    unreal.EditorAssetLibrary.set_metadata_tag(m,'KZFXRecoveryBoundary','Native lit world surface, original texture parameters; packed AO R/Roughness G/Metal B. Proprietary source shading omitted.')
    LIB.recompile_material(m);save(m)


try:
    own=[r for r in all_rows if not r['reuse_existing']]
    g['ROWS']=[r for r in own if r['source_type']=='Texture2D']
    g['dependencies']()
    for r in own:
        if r['source_type']=='TextureLightProfile':profile(r)
    g['ROWS']=all_rows
    for r in own:
        if r['source_type']=='Material':
            world_master(r) if r['name']=='M_WorldProp' else g['master'](r)
    # Parent-first MI import. Parent may be another source instance.
    queue=[r for r in own if r['source_type']=='MaterialInstanceConstant']
    while queue:
        ready=[r for r in queue if unreal.load_asset(g['LOOKUP'][g['source'](r)['Properties']['Parent']['ObjectPath'].split('.')[0]]['destination'])]
        assert ready,[r['name'] for r in queue]
        for r in ready:g['instance'](r);queue.remove(r)
    g['ROWS']=[r for r in own if r['source_type']=='StaticMesh'];g['meshes']()
    g['ROWS']=all_rows
    for r in own:
        if r['source_type']=='ParticleSystem':g['cascade'](r)
    g['REPORT']['status']='completed';g['write']('NativeImport',g['REPORT'])
    print('KZ_HM_FIRES_IMPORT_PASSED')
except Exception:
    g['REPORT']['status']='failed';g['REPORT']['error']=traceback.format_exc();g['write']('NativeImport',g['REPORT']);raise
