"""Build the isolated HeinMach enemy art library in UnrealEditor-Cmd.

The source package is the identity. Existing project/player assets are never
loaded for editing. Re-execution reuses this library's already imported assets.
"""
import unreal, pathlib, json, traceback, re, struct

PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
MANIFEST=json.loads((META/'EnemyImportManifest.json').read_text(encoding='utf-8'))
DEST=MANIFEST['destination_root']
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_LibraryBuild.json'
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
EAL=unreal.EditorAssetLibrary
MEL=unreal.MaterialEditingLibrary

def save(asset):
    if not EAL.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Save failed '+asset.get_path_name())
def tag(asset,source,role):
    EAL.set_metadata_tag(asset,'OriginalPackage',source)
    EAL.set_metadata_tag(asset,'EnemyArtRole',role)
    EAL.set_metadata_tag(asset,'EnemySourceLevel','HeinMach_Spawn_Main01')
def load(path):
    obj=unreal.load_asset(path)
    if not obj:raise RuntimeError('Missing UE asset '+path)
    return obj
def assign_skeleton(mesh,skeleton):
    # UE 5.8 hides BlueprintSetter methods as Python property accessors.
    mesh.skeleton=skeleton
def package(v):
    if not v:return None
    return v.get('ObjectPath',v.get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/')
def asset_new(path,cls,factory):
    if EAL.does_asset_exist(path):return load(path),False
    folder,name=path.rsplit('/',1)
    obj=TOOLS.create_asset(name,folder,cls,factory)
    if not obj:raise RuntimeError('Create failed '+path)
    return obj,True
def import_one(source,destination,factory):
    if EAL.does_asset_exist(destination):return load(destination),False
    folder,name=destination.rsplit('/',1)
    task=unreal.AssetImportTask()
    for k,v in dict(filename=source,destination_path=folder,destination_name=name,automated=True,replace_existing=False,save=False,factory=factory).items():task.set_editor_property(k,v)
    TOOLS.import_asset_tasks([task])
    obj=unreal.load_asset(destination)
    if not obj:raise RuntimeError('Import failed '+source+' '+str(task.imported_object_paths))
    return obj,True
def expr(mat,cls,**props):
    node=MEL.create_material_expression(mat,cls)
    for k,v in props.items():node.set_editor_property(k,v)
    return node
def link(a,out,b,pin):
    if not MEL.connect_material_expressions(a,out,b,pin):raise RuntimeError('Material connection '+pin)
def output(node,out,prop):
    if not MEL.connect_material_property(node,out,prop):raise RuntimeError('Material output '+str(prop))

def textures(report):
    mapping={}
    for i,r in enumerate(MANIFEST['textures']):
        tex,created=import_one(r['source_file'],r['destination'],unreal.TextureFactory())
        p=r['properties']
        tex.set_editor_property('srgb',p.get('SRGB',True))
        comp=p.get('CompressionSettings','TC_Default').split('::')[-1]
        comp_map={'TC_Default':unreal.TextureCompressionSettings.TC_DEFAULT,'TC_Normalmap':unreal.TextureCompressionSettings.TC_NORMALMAP,'TC_Masks':unreal.TextureCompressionSettings.TC_MASKS,'TC_Grayscale':unreal.TextureCompressionSettings.TC_GRAYSCALE,'TC_Alpha':unreal.TextureCompressionSettings.TC_ALPHA,'TC_BC7':unreal.TextureCompressionSettings.TC_BC7,'TC_HDR':unreal.TextureCompressionSettings.TC_HDR}
        if comp in comp_map:tex.set_editor_property('compression_settings',comp_map[comp])
        if 'bFlipGreenChannel' in p:tex.set_editor_property('flip_green_channel',p['bFlipGreenChannel'])
        tag(tex,r['source_package'],'SourceTexture')
        save(tex);mapping[r['source_package']]=tex
        report['textures'].append({'source':r['source_package'],'asset':tex.get_path_name(),'created':created,'srgb':tex.get_editor_property('srgb'),'compression':str(tex.get_editor_property('compression_settings'))})
        if i%20==0:print('ENEMY_TEXTURE',i+1,'/',len(MANIFEST['textures']))
    return mapping

def materials(texmap,report):
    specs={r['source_package']:r for r in MANIFEST['materials']};mapping={}
    # Preserve every named source parameter as an editable parameter in each
    # replacement master. Only the documented adapter subset drives UE shading.
    scalars={};vectors={};textures_default={}
    for r in MANIFEST['materials']:
        p=r['source_object'].get('Properties',{})
        cached=p.get('CachedExpressionData',{}).get('Parameters',{})
        for kind,entry,target in [('ScalarValues','RuntimeEntries',scalars),('VectorValues','RuntimeEntries[1]',vectors)]:
            for info,value in zip(cached.get(entry,{}).get('ParameterInfos',[]),cached.get(kind,[])):
                target.setdefault(info['Name'],value)
        for info,value in zip(cached.get('RuntimeEntries[2]',{}).get('ParameterInfos',[]),cached.get('TextureValues',[])):
            key=package(value)
            if key in texmap:textures_default.setdefault(info['Name'],texmap[key])
        for x in p.get('ScalarParameterValues',[]):scalars.setdefault(x['ParameterInfo']['Name'],x['ParameterValue'])
        for x in p.get('VectorParameterValues',[]):vectors.setdefault(x['ParameterInfo']['Name'],x['ParameterValue'])
        for x in p.get('TextureParameterValues',[]):
            key=package(x.get('ParameterValue'))
            if key in texmap:textures_default.setdefault(x['ParameterInfo']['Name'],texmap[key])
    fallback=lambda suffix:next(tex for p,tex in texmap.items() if p.endswith('/'+suffix))
    textures_default.setdefault('Tex_D',fallback('BASE_Diffuse'))
    textures_default.setdefault('Tex_N',fallback('BASE_Normal'))
    textures_default.setdefault('Tex_S',fallback('BASE_SAPE'))
    textures_default.setdefault('Tex_E',fallback('BASE_Black'))
    def build(p):
        if p in mapping:return mapping[p]
        r=specs[p];source=r['source_object'];props=source.get('Properties',{})
        is_master=r['source_type']=='Material'
        cls=unreal.Material if is_master else unreal.MaterialInstanceConstant
        factory=unreal.MaterialFactoryNew() if is_master else unreal.MaterialInstanceConstantFactoryNew()
        mat,created=asset_new(r['destination'],cls,factory)
        if is_master and created:
            mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
            mat.set_editor_property('opacity_mask_clip_value',0.3333) # Source BASE_AllMaster_AK.BasePropertyOverrides value.
            MEL.set_material_usage(mat,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
            sd=dict(scalars);vd=dict(vectors);td=dict(textures_default)
            cached=props.get('CachedExpressionData',{}).get('Parameters',{})
            for kind,entry,target in [('ScalarValues','RuntimeEntries',sd),('VectorValues','RuntimeEntries[1]',vd)]:
                for info,value in zip(cached.get(entry,{}).get('ParameterInfos',[]),cached.get(kind,[])):target[info['Name']]=value
            for info,value in zip(cached.get('RuntimeEntries[2]',{}).get('ParameterInfos',[]),cached.get('TextureValues',[])):
                key=package(value)
                if key in texmap:td[info['Name']]=texmap[key]
            sn={k:expr(mat,unreal.MaterialExpressionScalarParameter,parameter_name=k,default_value=float(v)) for k,v in sd.items()}
            vn={k:expr(mat,unreal.MaterialExpressionVectorParameter,parameter_name=k,default_value=unreal.LinearColor(v['R'],v['G'],v['B'],v.get('A',1))) for k,v in vd.items()}
            tn={}
            for k,tex in td.items():
                n=expr(mat,unreal.MaterialExpressionTextureSampleParameter2D,parameter_name=k,texture=tex)
                comp=tex.get_editor_property('compression_settings')
                sampler=unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if comp==unreal.TextureCompressionSettings.TC_NORMALMAP else (unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if tex.get_editor_property('srgb') else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
                n.set_editor_property('sampler_type',sampler);tn[k]=n
            if 'Transparent' in source['Name']:
                mat.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
                mat.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
                output(vn['Color'],'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
                output(sn['Opacity'],'',unreal.MaterialProperty.MP_OPACITY)
            elif 'Eye' in source['Name']:
                # Pupil mask interpretation is a visual adapter, not recovered graph topology.
                lerp=expr(mat,unreal.MaterialExpressionLinearInterpolate)
                link(vn['EyeWhiteColor0'],'',lerp,'A');link(vn['Pupil_Circle0'],'',lerp,'B');link(tn['Tex_E'],'R',lerp,'Alpha')
                output(lerp,'',unreal.MaterialProperty.MP_BASE_COLOR)
                rough=expr(mat,unreal.MaterialExpressionScalarParameter,parameter_name='PreviewEyeRoughness',default_value=0.25)
                output(rough,'',unreal.MaterialProperty.MP_ROUGHNESS)
                output(expr(mat,unreal.MaterialExpressionConstant,r=1.0),'',unreal.MaterialProperty.MP_OPACITY_MASK)
            else:
                output(tn['Tex_D'],'RGB',unreal.MaterialProperty.MP_BASE_COLOR)
                output(tn['Tex_D'],'A',unreal.MaterialProperty.MP_OPACITY_MASK)
                output(tn['Tex_N'],'RGB',unreal.MaterialProperty.MP_NORMAL)
                # Explicit approximation reused from the established character adapter:
                # S.R = specular; 1-S.G = roughness. Original BBQ shader unavailable.
                inverse=expr(mat,unreal.MaterialExpressionOneMinus);link(tn['Tex_S'],'G',inverse,'None')
                output(inverse,'',unreal.MaterialProperty.MP_ROUGHNESS)
                output(tn['Tex_S'],'R',unreal.MaterialProperty.MP_SPECULAR)
            EAL.set_metadata_tag(mat,'ShaderFidelity','UE preview adapter; source cooked topology unavailable')
            MEL.recompile_material(mat)
        if not is_master:
            parent=package(props.get('Parent'))
            if parent not in specs:raise RuntimeError('Missing material parent '+str(parent))
            MEL.set_material_instance_parent(mat,build(parent))
            for x in props.get('ScalarParameterValues',[]):MEL.set_material_instance_scalar_parameter_value(mat,x['ParameterInfo']['Name'],float(x['ParameterValue']))
            for x in props.get('VectorParameterValues',[]):
                v=x['ParameterValue'];MEL.set_material_instance_vector_parameter_value(mat,x['ParameterInfo']['Name'],unreal.LinearColor(v['R'],v['G'],v['B'],v.get('A',1)))
            for x in props.get('TextureParameterValues',[]):
                key=package(x.get('ParameterValue'))
                if key in texmap:MEL.set_material_instance_texture_parameter_value(mat,x['ParameterInfo']['Name'],texmap[key])
            base=props.get('BasePropertyOverrides',{});ov=mat.get_editor_property('base_property_overrides')
            if 'BlendMode' in base:
                ov.set_editor_property('override_blend_mode',True);ov.set_editor_property('blend_mode',getattr(unreal.BlendMode,base['BlendMode'].upper()))
            if 'TwoSided' in base:
                ov.set_editor_property('override_two_sided',True);ov.set_editor_property('two_sided',base['TwoSided'])
            if 'OpacityMaskClipValue' in base:
                ov.set_editor_property('override_opacity_mask_clip_value',True);ov.set_editor_property('opacity_mask_clip_value',base['OpacityMaskClipValue'])
            mat.set_editor_property('base_property_overrides',ov)
            MEL.update_material_instance(mat)
        tag(mat,p,'ReconstructedMaterial')
        EAL.set_metadata_tag(mat,'OriginalPropertiesJSON',json.dumps(props,ensure_ascii=False))
        save(mat);mapping[p]=mat
        report['materials'].append({'source':p,'asset':mat.get_path_name(),'created':created})
        return mat
    for p in specs:build(p)
    hidden,new=asset_new(DEST+'/Shared/Materials/M_EN_InvisiblePoseCarrier',unreal.Material,unreal.MaterialFactoryNew())
    if new:
        hidden.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
        output(expr(hidden,unreal.MaterialExpressionConstant,r=0.0),'',unreal.MaterialProperty.MP_OPACITY_MASK)
        MEL.set_material_usage(hidden,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH);MEL.recompile_material(hidden);save(hidden)
    mapping[None]=hidden
    return mapping

def meshes(matmap,report):
    mapping={};factory_class=unreal.load_class(None,'/Script/UnrealPSKPSA.PSKFactory')
    if not factory_class:raise RuntimeError('Project PSK importer unavailable')
    ordered=sorted(MANIFEST['meshes'],key=lambda r:not r['carrier'])
    carrier_skeleton=None
    for r in ordered:
        # PSKFactory creates unreferenced material/skeleton companions in staging.
        staging=DEST+'/_ImportStaging/'+r['destination'].rsplit('/',1)[1]
        if EAL.does_asset_exist(r['destination']):mesh=load(r['destination']);created=False
        else:
            mesh,created=import_one(r['source_file'],staging,unreal.new_object(factory_class))
            save(mesh.get_editor_property('skeleton'))
            save(mesh)
            if not EAL.rename_asset(staging,r['destination']):raise RuntimeError('Mesh relocation failed')
            mesh=load(r['destination'])
        skel=mesh.get_editor_property('skeleton')
        if r['carrier']:
            target=DEST+'/Empire/Skeletons/SKEL_EN_EmpireHuman'
            if not skel and EAL.does_asset_exist(target):
                skel=load(target);assign_skeleton(mesh,skel)
            if skel.get_path_name().split('.')[0]!=target:
                if EAL.does_asset_exist(target):skel=load(target)
                else:
                    EAL.rename_asset(skel.get_path_name().split('.')[0],target);skel=load(target)
                assign_skeleton(mesh,skel)
            carrier_skeleton=skel;skel.set_skeleton_preview_mesh(mesh)
        elif '/Empire/Parts/' in r['destination']:
            assign_skeleton(mesh,carrier_skeleton);skel=carrier_skeleton
        else:
            target=r['destination'].rsplit('/',1)[0]+'/Skeletons/SKEL_EN_'+r['source_package'].rsplit('/',1)[1]
            if skel.get_path_name().split('.')[0]!=target:
                if EAL.does_asset_exist(target):skel=load(target)
                else:EAL.rename_asset(skel.get_path_name().split('.')[0],target);skel=load(target)
                assign_skeleton(mesh,skel)
        slots=list(mesh.get_editor_property('materials'))
        if len(slots)!=len(r['materials']):raise RuntimeError('Material slot count '+r['destination'])
        for i,(slot,p) in enumerate(zip(slots,r['materials'])):
            if p not in matmap:raise RuntimeError('Material missing '+str(p))
            slot.set_editor_property('material_interface',matmap[p])
            slot.set_editor_property('material_slot_name',r['source_slot_names'][i])
        mesh.set_editor_property('materials',slots)
        tag(mesh,r['source_package'],'HiddenPoseCarrier' if r['carrier'] else 'SkeletalMesh')
        EAL.set_metadata_tag(mesh,'SourceLODArchive',json.dumps(r['lod_files']))
        EAL.set_metadata_tag(mesh,'SourceMorphTargetNames',json.dumps(r['morph_targets']))
        tag(skel,r['source_skeleton'] or r['source_package'],'Skeleton')
        save(skel);save(mesh);mapping[r['source_package']]=mesh
        report['meshes'].append({'source':r['source_package'],'asset':mesh.get_path_name(),'skeleton':skel.get_path_name(),'slots':len(slots),'created':created})
        print('ENEMY_MESH',mesh.get_name())
    return mapping

def main():
    report={'status':'running','textures':[],'materials':[],'meshes':[]}
    try:
        texmap=textures(report);matmap=materials(texmap,report);meshes(matmap,report)
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:
        REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_LIBRARY_BUILD_PASSED')

if __name__=='__main__':main()
