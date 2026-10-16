"""Correct fixed-array import and record exact original event fields, private only."""
from pathlib import Path
import json, os, re, unreal as u
MAIN=Path(__file__).resolve().parents[2];WORK=Path(u.Paths.project_dir()).resolve()
assert WORK==MAIN.parent.parent/'Khazan_HealVFXWork_20261013/Khazan'
OUT=Path(os.environ['KZ_HEAL_VFX_OUT']);EAL=u.EditorAssetLibrary
report=dict(status='running',mirror_arrays=[],saved=[],shader_errors=[])
for name,usage in [('M_Heal_SoftGlow',u.MaterialUsage.MATUSAGE_PARTICLE_SPRITES),
                   ('M_Heal_OriginalTrail',u.MaterialUsage.MATUSAGE_MESH_PARTICLES),
                   ('M_Heal_CoreFresnel',u.MaterialUsage.MATUSAGE_MESH_PARTICLES)]:
    mat=u.load_asset('/Game/HealVFX/Materials/'+name);assert mat
    u.MaterialEditingLibrary.set_material_usage(mat,usage)
    errors=u.MaterialEditingLibrary.recompile_material(mat);assert not errors
    assert EAL.save_loaded_asset(mat,only_if_is_dirty=False)
    report['saved'].append(mat.get_path_name())
for name in ['PS_Heal_DrainCore','PS_Heal_DrainBurst','PS_Heal_GhostArm','PS_Heal_GhostFinger','PS_Heal_LightFlash']:
    ps=u.load_asset('/Game/HealVFX/Particles/'+name);assert ps
    txt=(MAIN/'Metadata/HealVFX_20261013/Saved03'/(name+'.t3d')).read_text(encoding='utf-8-sig')
    for line in txt.splitlines():
        if 'Class=/Script/Engine.DistributionVectorUniform ' not in line:continue
        path=re.search(r'ExportPath="[^\']*\'([^\']+)\'"',line).group(1)
        obj=u.load_object(None,path);assert obj and path.startswith(ps.get_path_name()+':')
        flags=list(obj.get_editor_property('mirror_flags'));enum=type(flags[0])
        obj.set_editor_property('mirror_flags',[enum.EDVMF_DIFFERENT]*3)
        assert all(x==enum.EDVMF_DIFFERENT for x in obj.get_editor_property('mirror_flags'))
        report['mirror_arrays'].append(path)
    assert EAL.save_loaded_asset(ps,only_if_is_dirty=False);report['saved'].append(ps.get_path_name())
m=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal')
for event in u.AnimationLibrary.get_animation_notify_events(m):
    n=event.get_editor_property('notify')
    if not n or n.get_class().get_name()!='KZAnimNotify_CombatEffect':continue
    for c in n.get_editor_property('BatchedEffects'):
        ident=str(c.get_editor_property('EventId'))
        assert ident.startswith('KZHeal_')
        index=int(ident.split('_')[1])
        c.set_editor_property('SourceField','Notifies['+str(index)+'].NotifyStateClass -> ParticleInfo; native filtered-bone adapter')
assert EAL.save_loaded_asset(m,only_if_is_dirty=False);report['saved'].append(m.get_path_name())
report['status']='passed';(OUT/'Finalize.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEAL_VFX_FIXED_ARRAYS',len(report['mirror_arrays']),flush=True)
