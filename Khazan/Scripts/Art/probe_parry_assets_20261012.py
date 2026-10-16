"""Read selected current assets in a task-owned editor; never save packages."""
from pathlib import Path
import json, os, re, unreal
OUT=Path(os.environ['KZ_PARRY_OUT']);EAL=unreal.EditorAssetLibrary;LIB=unreal.MaterialEditingLibrary
R={'status':'running','asset_saves':0,'animations':[],'materials':[]}
def export(obj,name):
    p=OUT/(name+'.t3d');t=unreal.AssetExportTask();t.object=obj;t.filename=str(p)
    t.automated=True;t.prompt=False;t.replace_identical=False
    assert unreal.Exporter.run_asset_export_task(t),name
    return p.read_text(encoding='utf-8-sig')
for side in ['L','R']:
    a=unreal.load_asset('/Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Combat/Defense/JustGuard/CA_P_Kazan_DualAxeSword_Def_JustGuard_'+side)
    assert a
    model=a.controller.get_model_interface()
    R['animations'].append({'path':a.get_path_name(),'seconds':a.get_play_length(),'frames':model.get_number_of_frames(),
                           'metadata':{str(k):str(v) for k,v in EAL.get_metadata_tag_values(a).items()}})
effect=unreal.load_asset('/Game/_Art/Effects/Combat/GuardParry/PP_AtkEx_JustGuard');assert effect
txt=export(effect,'OriginalJustGuardNative')
paths=sorted(set(re.findall(r'Material="[^\']*\'([^\']+)\'"',txt)))
for path in paths:
    mat=unreal.load_asset(path)
    if not mat:continue
    row={'path':path,'class':mat.get_class().get_name()}
    if isinstance(mat,unreal.MaterialInstanceConstant):
        row['parent']=mat.get_editor_property('parent').get_path_name()
        row['scalars']=str(mat.get_editor_property('scalar_parameter_values'))
        row['textures']=[{'name':str(x.get_editor_property('parameter_info').get_editor_property('name')),
                         'path':x.get_editor_property('parameter_value').get_path_name()} for x in mat.get_editor_property('texture_parameter_values') if x.get_editor_property('parameter_value')]
        parent=mat.get_editor_property('parent')
        while isinstance(parent,unreal.MaterialInstanceConstant):parent=parent.get_editor_property('parent')
        export(parent,parent.get_name())
    export(mat,mat.get_name());R['materials'].append(row)
montage=unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Guard/AM_DAS_Player_Guard')
R['guard_montage_export']='GuardMontageBefore.t3d';export(montage,'GuardMontageBefore')
R['guard_start_length']=unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Guard/Player_Guard_Start').get_play_length()
R['status']='passed';(OUT/'Readback.json').write_text(json.dumps(R,indent=2,default=str),encoding='utf-8')
print('PARRY_ASSET_PROBE',len(paths),R['guard_start_length'],flush=True)
