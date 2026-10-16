"""Private blood mesh presentation-unit adapter; other emitters stay world-sized."""
from pathlib import Path
import unreal as u
import json,os,re
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');work=Path(u.Paths.project_dir()).resolve();assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);fx=u.FXConverterUtilitiesLibrary
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
original=next(k for k in author['particles'] if k.endswith('FP_Boss_Yetuga_CloseGrab_Smash_01.FP_Boss_Yetuga_CloseGrab_Smash_01'));p=u.load_asset(author['particles'][original])
catalog=json.loads((main/'Metadata/GiantVFX_20261013/ParticleObjectCatalog.json').read_text(encoding='utf-8'))['FP_Boss_Yetuga_CloseGrab_Smash_01.t3d']
# TEMP presentation adapter: .01 reuses the project's documented imported
# giant mesh scale. CDO alone does not run Blueprint construction; it is not
# evidence of the live mesh scale or original VAT shader parity.
scale=u.Vector(.01,.01,.01)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();targets=[]
for e in fx.get_cascade_system_emitters(p):
    lod=fx.get_cascade_emitter_lod_level(e,0);typ=fx.get_lod_level_type_data_module(lod)
    if not isinstance(typ,u.ParticleModuleTypeDataMesh):continue
    m=typ.get_editor_property('mesh')
    if not m or m.get_name() not in ['T_SM_Blood03','T_SM_Blood05']:continue
    # The saved source catalog identifies the exact size module for this LOD.
    oldlod=lod.get_path_name().replace(p.get_path_name(),original,1);node=catalog[oldlod]
    references=' '.join(node['properties'])
    size_name=next(name for name,n in catalog.items() if n['class'].endswith('ParticleModuleSize') and (":"+n['name']+"'") in references)
    size=u.load_object(None,size_name.replace(original,p.get_path_name(),1));raw=size.get_editor_property('start_size');d=raw.get_editor_property('distribution')
    if isinstance(d,u.DistributionVectorConstant):
        before=d.get_editor_property('constant');d.set_editor_property('constant',before*scale.x)
    elif isinstance(d,u.DistributionVectorUniform):
        before=[str(d.get_editor_property(n)) for n in ['min','max']]
        for n in ['min','max']:d.set_editor_property(n,d.get_editor_property(n)*scale.x)
    else:raise AssertionError(d)
    targets.append({'emitter':e.get_name(),'distribution':d.get_path_name(),'before':str(before),'mesh':m.get_path_name(),'factor':scale.x,'source_status':'Existing imported monster presentation scale; TEMP mesh-unit adapter, original VAT shader remains unrecovered'})
assert targets;assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'GrabMeshUnits.json').write_text(json.dumps({'particle':p.get_path_name(),'targets':targets},indent=2),encoding='utf-8')
cases=[]
probe=json.loads((main/'Metadata/GiantVFX_20261013/Probe02/Probe.json').read_text(encoding='utf-8'))
for path,row in probe['sequences'].items():
    if any(e.get('effect',{}).get('particle')==original for e in row['events']):cases.append([path.split('.')[-1],'Yetuga','animation',path])
cases.append(['CloseGrab_Smash','Yetuga','particle',p.get_path_name()])
(main/'Metadata/GiantVFX_20261013/GrabAffectedCases.tsv').write_text('\n'.join('\t'.join(c) for c in cases),encoding='utf-8')
