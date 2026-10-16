"""Read original core-fire modules back from saved native packages; no saves."""
from pathlib import Path
import json
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
EX=MAIN/'Saved/Extracted/HeinMachTutorialFires_20261006'
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'
FX=unreal.FXConverterUtilitiesLibrary
report=[]

def index(ref):return int(ref['ObjectPath'].rsplit('.',1)[1])
def plain(v):
    if isinstance(v,(list,tuple,unreal.Array)):return [plain(x) for x in v]
    if hasattr(v,'export_text'):return v.export_text()
    if hasattr(v,'get_path_name'):return v.get_path_name()
    return str(v)

for row in json.loads((EX/'AssetManifest.json').read_text()):
    if row['source_type']!='ParticleSystem':continue
    source=json.loads((MAIN/row['source_json']).read_text(encoding='utf-8'))
    asset=unreal.load_asset(row['destination']);assert asset
    report.append({'asset':asset.get_path_name(),'source_emitters':[{'name':e.get('Properties',{}).get('EmitterName'), 'lods':[source[index(r)] for r in e.get('Properties',{}).get('LODLevels',[])]} for e in source if e['Type']=='ParticleSpriteEmitter']})
    for original in source:
        if original.get('Properties',{}).get('EmitterName')!='core_fire':continue
        emitter=next(e for e in FX.get_cascade_system_emitters(asset) if str(e.get_editor_property('emitter_name'))=='core_fire')
        lod=FX.get_cascade_emitter_lod_level(emitter,0)
        modules=[FX.get_lod_level_required_module(lod),FX.get_lod_level_spawn_module(lod)]+list(FX.get_lod_level_modules(lod))
        source_lod=source[index(original['Properties']['LODLevels'][0])]
        original_refs=[source_lod['Properties'][k] for k in ('RequiredModule','SpawnModule')]+source_lod['Properties']['Modules']
        for native,ref in zip(modules,original_refs):
            original_module=source[index(ref)]
            item={'asset':asset.get_path_name(),'native':native.get_path_name(),'original':original_module}
            item['readback']={}
            if original_module['Type']=='ParticleModuleSpawn':
                item['burst_readback']=[{'count':v.get_editor_property('count'),'count_low':v.get_editor_property('count_low'),'time':v.get_editor_property('time')} for v in native.get_editor_property('burst_list')]
            for key in original_module.get('Properties',{}):
                try:
                    val=native.get_editor_property(key);item['readback'][key]=plain(val)
                    if isinstance(original_module['Properties'][key],dict) and original_module['Properties'][key].get('Distribution'):
                        original_dist=source[index(original_module['Properties'][key]['Distribution'])]
                        dist=val.get_editor_property('distribution')
                        if dist:
                            item['distribution_readback']={}
                            for k in original_dist.get('Properties',{}):
                                try:item['distribution_readback'][k]=plain(dist.get_editor_property(k))
                                except Exception as e:item['distribution_readback'][k]={'error':str(e)}
                except Exception as e:item['readback'][key]={'error':str(e)}
            report.append(item)
        req=modules[0];mat=req.get_editor_property('material')
        item={'asset':asset.get_path_name(),'material':mat.get_path_name(),'effective_parameters':{}}
        for name in ('SubUV_U','SubUV_V','looping_speed','EMI_Pow','EMI_Str','OPA_Pow','OPA_Str','DepthFade','FireRadianceGain'):
            item['effective_parameters'][name]=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mat,name)
        for name in ('Tex_Emi','Tex_Opa'):
            t=unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,name)
            item['effective_parameters'][name]=t.get_path_name() if t else None
        report.append(item)
(OUT/'CoreModuleReadback.json').write_text(json.dumps(report,indent=2)+'\n')
print('KZ_HM_FIRES_INSPECT_PASSED',len(report))
