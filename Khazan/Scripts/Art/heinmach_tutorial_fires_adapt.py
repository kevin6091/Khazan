"""Apply required UE4-to-UE5 Cascade compatibility to task-owned packages."""
from pathlib import Path
from functools import lru_cache
import json
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
EX=MAIN/'Saved/Extracted/HeinMachTutorialFires_20261006'
META=ROOT/'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
DEST='/Game/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires/'
report={'detail_mode':[],'fixed_arrays':[],
        'detail_mode_provenance':'UE5.8 ParticleEmitter.cpp::Serialize AddEpicDetailMode migration: enable Epic when original High bit is set. New editor-created packages do not run the legacy version migration.',
        'fixed_array_provenance':'Original FModel Properties.ParamModes and Properties.ParamModes[1]/[2]. SETNOPEC does not import indexed fixed-array field names; set complete reflected array and verify each element.'}

for row in json.loads((EX/'AssetManifest.json').read_text()):
    if row['source_type']!='ParticleSystem':continue
    asset=unreal.load_asset(row['destination']);assert asset and asset.get_path_name().startswith(DEST)
    data=json.loads((MAIN/row['source_json']).read_text(encoding='utf-8'))
    root_index=next(i for i,o in enumerate(data) if o['Type']=='ParticleSystem')
    @lru_cache(maxsize=None)
    def obj(i):
        if i==root_index:return asset
        original=data[i];outer=obj(int(original['Outer']['ObjectPath'].rsplit('.',1)[1]))
        name=original['Name']
        if len(outer.get_path_name())+len(name)+1>=240:name='E'+str(i)
        native=unreal.find_object(outer,name)
        assert native,(i,outer.get_path_name(),name)
        return native
    for i,original in enumerate(data):
        props=original.get('Properties',{});native=obj(i)
        if original['Type']=='ParticleSpriteEmitter' and 'DetailModeBitmask' in props:
            source=props['DetailModeBitmask'];adapted=source | ((1<<3) if source & (1<<2) else 0)
            native.set_editor_property('detail_mode_bitmask',adapted)
            assert native.get_editor_property('detail_mode_bitmask')==adapted
            report['detail_mode'].append({'asset':asset.get_path_name(),'export_index':i,'source':source,'native':adapted})
        if any(k.startswith('ParamModes[') for k in props):
            values=list(native.get_editor_property('param_modes'))
            for k,raw in props.items():
                if k=='ParamModes':index=0
                elif k.startswith('ParamModes['):index=int(k.split('[',1)[1].rstrip(']'))
                else:continue
                values[index]=getattr(unreal.DistributionParamMode,raw.rsplit('::',1)[-1].upper())
            native.set_editor_property('param_modes',values)
            assert list(native.get_editor_property('param_modes'))==values
            report['fixed_arrays'].append({'asset':asset.get_path_name(),'export_index':i,'source_properties':props,'native':[str(v) for v in values]})
    unreal.EditorAssetLibrary.set_metadata_tag(asset,'KZHMFireCompatibility','UE4 high detail propagated to UE5 Epic; complete original ParamModes fixed arrays restored.')
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
(META/'CascadeCompatibility.json').write_text(json.dumps(report,indent=2)+'\n')
print('KZ_HM_FIRES_ADAPT_PASSED',len(report['detail_mode']),len(report['fixed_arrays']))
