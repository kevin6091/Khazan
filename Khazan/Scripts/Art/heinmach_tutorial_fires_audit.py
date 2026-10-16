"""Fresh saved-map verification against exact placement and preservation reports."""
from pathlib import Path
from collections import Counter
import json
import math
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachTutorialFires_20261006'
META=ROOT/'Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006'
placement=json.loads((OUT/'Placement.json').read_text(encoding='utf-8'))
baseline=json.loads((OUT/'BaselineScene.json').read_text())
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
actors={a.get_actor_label():a for a in sub.get_all_level_actors()}


def pose(a):
    v=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d();return [v.x,v.y,v.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]


errors=[]
for label,expected in baseline['poses'].items():
    a=actors.get(label)
    if not a or max(abs(x-y) for x,y in zip(pose(a),expected))>1e-6:errors.append({'kind':'existing_pose_changed','label':label})
for row in placement['placements']+placement['fixtures']:
    a=actors.get(row['label'])
    if not a:errors.append({'kind':'missing_actor','label':row['label']});continue
    if max(abs(x-y) for x,y in zip(pose(a),row['pose']))>1e-6:errors.append({'kind':'placement_changed','label':row['label']})
    assert 'KZHeinMachTutorialFire' in [str(v) for v in a.tags]
    if row.get('type')=='ParticleSystemComponent':
        c=a.get_component_by_class(unreal.ParticleSystemComponent)
        assert c.template.get_path_name()==row['asset'],row['label']
        assert c.get_editor_property('auto_activate'),row['label']
        ps={str(p.name):p for p in c.get_editor_property('instance_parameters')}
        for expected in row['instance_parameters']:
            if expected['ParamType']=='PSPT_None':continue
            p=ps[expected['Name']]
            if expected['ParamType']=='PSPT_Scalar':assert abs(p.scalar-expected['Scalar'])<1e-5,(row['label'],expected)
            if expected['ParamType']=='PSPT_Vector':assert max(abs(getattr(p.vector,k.lower())-expected['Vector'][k]) for k in 'XYZ')<1e-5,(row['label'],expected)
    elif row.get('type')=='PointLightComponent':
        c=a.get_component_by_class(unreal.PointLightComponent)
        assert abs(c.get_editor_property('intensity')-row['native_intensity'])<1e-5,row['label']
        assert abs(c.get_editor_property('attenuation_radius')-row['radius_cm'])<1e-5,row['label']
        if row['ies']:assert c.get_editor_property('ies_texture').get_path_name()==row['ies']
        color=row['source_properties'].get('LightColor')
        if color:
            actual=c.get_editor_property('light_color')
            assert all(getattr(actual,k.lower())==color[k] for k in 'RGB'),row['label']
    elif row.get('type')=='DecalComponent':
        c=a.get_component_by_class(unreal.DecalComponent);assert c.get_editor_property('decal_material').get_path_name()==row['asset']
    else:
        c=a.get_component_by_class(unreal.StaticMeshComponent);assert c.static_mesh.get_path_name()==row['mesh']
        assert all(c.get_material(i) for i in range(c.get_num_materials()))
for old in baseline['lights']:
    c=actors[old['label']].get_component_by_class(unreal.PointLightComponent)
    assert c.get_editor_property('intensity')==old['intensity'] and c.get_editor_property('attenuation_radius')==old['radius'],old
systems=[]
manifest=json.loads((META/'AssetManifest.json').read_text())
for row in manifest:
    if row['source_type']!='ParticleSystem':continue
    ps=unreal.load_asset(row['destination']);assert ps
    source=json.loads((MAIN/row['source_json']).read_text(encoding='utf-8'))
    original=next(o for o in source if o['Type']=='ParticleSystem')
    emitters=unreal.FXConverterUtilitiesLibrary.get_cascade_system_emitters(ps)
    assert len(emitters)==len(original['Properties']['Emitters'])
    for e in emitters:
        assert e.get_editor_property('detail_mode_bitmask') & (1<<3),'UE4 high must also enable UE5 Epic'
        lod=unreal.FXConverterUtilitiesLibrary.get_cascade_emitter_lod_level(e,0)
        req=unreal.FXConverterUtilitiesLibrary.get_lod_level_required_module(lod);assert req.get_editor_property('material')
    systems.append({'asset':ps.get_path_name(),'emitters':len(emitters)})
report={'passed':not errors,'errors':errors,'total_actors':len(actors),'preserved_actors':len(baseline['poses']),
        'new_actors':len(actors)-len(baseline['poses']),'particle_components':placement['counts']['ParticleSystemComponent'],
        'local_lights':placement['counts']['PointLightComponent'],'ground_burn_decals':placement['counts'].get('DecalComponent',0),'fixtures':len(placement['fixtures']),
        'source_inactive_lights_skipped':len(placement['skipped_inactive']),'systems':systems,
        'existing_source_lights_preserved':len(baseline['lights']),'player_start_preserved':{n:pose(actors[n]) for n in baseline['poses'] if 'PlayerStart' in n or 'TutorialStart' in n}}
label='MainSavedSceneAudit' if ROOT==MAIN else 'StageSavedSceneAudit'
(OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
(META/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'],errors
print('KZ_HM_FIRES_AUDIT_PASSED',json.dumps({k:v for k,v in report.items() if k not in ('systems','player_start_preserved')}))
