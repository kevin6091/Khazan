"""Read only the actual requested Niagara, mesh and current player notifies."""
from pathlib import Path
import json,os
import unreal as u
r=Path(u.Paths.project_dir()).resolve();assert r.name=='Khazan' and r.parent.name=='Khazan_PlayerSlashWork_20261013'
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
paths=['/Game/VFX/01_ARPGEssentials/KZ_Slash','/Game/VFX/01_ARPGEssentials/Meshes/SM_VFX_SlashRing_01']
for i,p in enumerate(paths):
 a=u.load_asset(p);assert a
 t=u.AssetExportTask();t.object=a;t.filename=str(out/('Asset_'+str(i)+'.t3d'));t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False
 assert u.Exporter.run_asset_export_task(t)
base=r/'Metadata/CombatImpactUpgrade_20261012/BindingsAuthored.json'
paths=sorted(set(x['asset'].split('.')[0] for x in json.loads(base.read_text(encoding='utf-8'))['player_effects']))
rows=[]
for p in paths:
 a=u.load_asset(p);assert a
 row={'asset':p,'notifies':[]}
 for e in u.AnimationLibrary.get_animation_notify_events(a):
  n=e.get_editor_property('Notify')
  if isinstance(n,u.KZAnimNotify_CombatEffect):
   for child in [n]+list(n.get_editor_property('BatchedEffects')):
    row['notifies'].append({'id':str(child.get_editor_property('EventId')),'end':bool(child.get_editor_property('bEndEvent')),'particle':str(child.get_editor_property('ParticleTemplate')),'niagara':str(child.get_editor_property('NiagaraTemplate')),'align':bool(child.get_editor_property('bAlignToWeaponSweep')),'near':str(child.get_editor_property('WeaponEdgeNearSocket')),'tip':str(child.get_editor_property('WeaponEdgeTipSocket')),'rotation':str(child.get_editor_property('RelativeRotation')),'location':str(child.get_editor_property('RelativeLocation'))})
 rows.append(row)
(out/'Probe.json').write_text(json.dumps({'status':'passed','rows':rows},indent=2),encoding='utf-8')
print('SLASH_SCOPED_PROBE_PASSED')
