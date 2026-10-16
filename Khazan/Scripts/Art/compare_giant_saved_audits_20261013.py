"""Exact raw-model/settings/event comparison before any Main delivery."""
from pathlib import Path
import json,re,sys
main=Path(__file__).resolve().parents[2];base=main/'Metadata/GiantVFX_20261013'
label=sys.argv[1];before=json.loads((base/'MainBeforeAudit01/SavedAudit.json').read_text(encoding='utf-8'));after=json.loads((base/label/'SavedAudit.json').read_text(encoding='utf-8'))
report={'status':'running','before':'MainBeforeAudit01','after':label,'sequence_count':len(after['sequences']),'differences':[]}
for path,record in before['sequences'].items():
    current=after['sequences'][path]
    for field in record:
        if record[field]!=current[field]:report['differences'].append({'asset':path,'field':field})
def core(text):
    text=re.sub(r',(?:SpawnEffect|FlightEffect|ImpactEffect)=(?:"[^\"]*"|None)','',text)
    text=text.replace("/Game/_Art/Effects/Shared/Meshes/MonsterApesYetuga/FS_Yetuga_Rock_01.FS_Yetuga_Rock_01","/Engine/BasicShapes/Sphere.Sphere")
    return text
for family,objects in before['objects'].items():
    if [core(x) for x in objects]!=[core(x) for x in after['objects'][family]]:report['differences'].append({'asset':family,'field':'original_object_gameplay_fields'})
report['null_render_bindings']=after['null_render_bindings']
report['status']='passed' if not report['differences'] and not report['null_render_bindings'] else 'failed'
(base/label/'Preservation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report));assert report['status']=='passed'
