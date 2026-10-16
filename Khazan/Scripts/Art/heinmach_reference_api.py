"""Targeted editor reflection probe in the isolated project; no writes."""
from pathlib import Path
import json
import unreal

root=Path(unreal.Paths.project_dir()).resolve()
assert 'ArtStaging/HeinMachReference_20261006' in root.as_posix()
system=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers')
report={}
for name in ('EmitterHandles','emitter_handles'):
    try:
        handles=system.get_editor_property(name)
        report[name]=str(handles)[:2000]
        for handle in handles:
            for field in ('Name','VersionedInstance','Instance'):
                try:
                    value=handle.get_editor_property(field)
                    report[field]=str(value)[:500]
                    if field=='VersionedInstance':
                        emitter=value.get_editor_property('Emitter')
                        report['emitter']=emitter.get_path_name()
                        data=emitter.get_editor_property('VersionData')
                        report['VersionData']=str(data)[:1200]
                        report['ScalabilityOverrides']=str(data[0].get_editor_property('ScalabilityOverrides'))
                except Exception as error:report[field]=str(error)
    except Exception as error:report[name]=str(error)
for name in ('Source_Dust_0','Source_Flakes_Fast_Large_0'):
    emitter=unreal.load_object(None,system.get_path_name()+':'+name)
    row={'path':str(emitter)}
    if emitter:
        for field in ('VersionData','version_data','ScalabilityOverrides','scalability_overrides'):
            try:row[field]=str(emitter.get_editor_property(field))[:3000]
            except Exception as error:row[field]=str(error)
    report[name]=row
for name in ('NiagaraEmitterScalabilitySettingsOverride','NiagaraEmitterScalabilityOverrides','NiagaraEmitter','NiagaraSystem','NiagaraSimCache','NiagaraDataChannelLibrary','SystemLibrary'):
    cls=getattr(unreal,name,None)
    report[name]=str(getattr(cls,'__doc__',''))[:18000]
    if name=='NiagaraSimCache':report['SimCacheMethods']={n:str(getattr(cls,n).__doc__)[:5000] for n in dir(cls) if any(x in n for x in ('capture','num','read','write','begin'))}
(root/'Saved/ImportReports/HeinMachReference_20261006/Api.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('KZ_HEINMACH_REFERENCE_API_PASSED')
