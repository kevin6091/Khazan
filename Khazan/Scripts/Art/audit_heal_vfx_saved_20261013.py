"""Fresh loaded recovery package audit; no shared package changes."""
from pathlib import Path
import os, json, re, unreal as u
MAIN=Path(__file__).resolve().parents[2]
PROJECT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_HEAL_VFX_OUT'])
R=dict(status='running',project=str(PROJECT),effects=[],particles=[],saved=0)
bp=u.load_asset('/Game/_Art/Player/Character/Bluprints/BP_Player')
mesh=u.get_default_object(bp.generated_class()).get_editor_property('Mesh')
m=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal')
events=u.AnimationLibrary.get_animation_notify_events(m)
R['notifies']=[e.export_text() for e in events]
expected=json.loads((MAIN/'Metadata/HealVFX_20261013/Author03/Author.json').read_text())['montage']['before']
assert all(e in R['notifies'] for e in expected), 'Existing HP/weapon/input/audio event preservation'
seen={}
for event in events:
    notify=event.get_editor_property('notify')
    if not notify or notify.get_class().get_name()!='KZAnimNotify_CombatEffect':continue
    for effect in [notify]+list(notify.get_editor_property('BatchedEffects')):
        ident=str(effect.get_editor_property('EventId'))
        if not ident.startswith('KZHeal_'):continue
        socket=str(effect.get_editor_property('SourceSocket'))
        present=mesh.does_socket_exist(socket)
        row=dict(id=ident,end=effect.get_editor_property('bEndEvent'),socket=socket,socket_exists=present,
                 template=effect.get_editor_property('ParticleTemplate').get_path_name(),start=effect.get_editor_property('WindowStartTime'),end_time=effect.get_editor_property('WindowEndTime'))
        R['effects'].append(row);seen.setdefault(ident,[]).append(row)
        assert present, 'Source socket/bone not in current skeleton: '+socket
assert len(seen)==11 and all(len(x)==2 and {r['end'] for r in x}=={False,True} for x in seen.values())
for name in ['PS_Heal_DrainCore','PS_Heal_DrainBurst','PS_Heal_GhostArm','PS_Heal_GhostFinger','PS_Heal_LightFlash']:
    ps=u.load_asset('/Game/HealVFX/Particles/'+name);assert ps
    emitters=u.FXConverterUtilitiesLibrary.get_cascade_system_emitters(ps)
    task=u.AssetExportTask();task.object=ps;task.filename=str(OUT/(name+'.t3d'));task.automated=True;task.prompt=False;task.exporter=u.ObjectExporterT3D()
    assert u.Exporter.run_asset_export_task(task)
    row=dict(path=ps.get_path_name(),emitters=len(emitters),required_materials=[])
    for e in emitters:
        lod=u.FXConverterUtilitiesLibrary.get_cascade_emitter_lod_level(e,0)
        req=u.FXConverterUtilitiesLibrary.get_lod_level_required_module(lod)
        mat=req.get_editor_property('material');assert mat
        row['required_materials'].append(mat.get_path_name())
    R['particles'].append(row)
for name in ['M_Heal_SoftGlow','M_Heal_OriginalTrail','M_Heal_CoreFresnel']:
    mat=u.load_asset('/Game/HealVFX/Materials/'+name);assert mat
    errors=u.MaterialEditingLibrary.recompile_material(mat);assert not errors
    assert mat.get_editor_property('blend_mode')==u.BlendMode.BLEND_ADDITIVE
    assert u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_OPACITY)
R['status']='passed'
(OUT/'SavedAudit.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('HEAL_VFX_SAVED',R['status'],len(seen),flush=True)
