"""Fresh selected-asset parameter preservation and saved scene policy checks; no saves."""
from pathlib import Path
import json,os,traceback,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_LOOK_MAIN']);OUT=Path(os.environ['KZ_LOOK_OUT'])
BASE=MAIN/'Metadata/SceneLook_20261012';lib=unreal.MaterialEditingLibrary
before='BeforeParameters' in OUT.name
report={'success':False,'asset_saves':0,'materials':{},'mismatches':[],'scenes':[],'before':before}
targets=json.loads((BASE/'MaskBaseline.json').read_text())['targets']
try:
    for row in targets:
        m=unreal.load_asset(row['material']);assert m
        report['materials'][row['material']]={
            'scalars':{str(k):lib.get_material_instance_scalar_parameter_value(m,k) for k in lib.get_scalar_parameter_names(m)},
            'vectors':{str(k):lib.get_material_instance_vector_parameter_value(m,k).export_text() for k in lib.get_vector_parameter_names(m)},
            'textures':{str(k):str(lib.get_material_instance_texture_parameter_value(m,k).get_path_name()) if lib.get_material_instance_texture_parameter_value(m,k) else None for k in lib.get_texture_parameter_names(m)},
            'overrides':m.get_editor_property('base_property_overrides').export_text(),'parent':m.get_editor_property('parent').get_path_name()}
    if not before:
        old=json.loads((BASE/'MainBeforeParameters01/SavedAudit.json').read_text())['materials']
        leaves={r['material'] for r in json.loads((BASE/'FoliageFinish03/FoliageFinish.json').read_text())['leaf_changes']}
        for path,new in report['materials'].items():
            prev=old[path]
            for group in ['scalars','vectors','textures']:
                for key in set(prev[group])|set(new[group]):
                    if prev[group].get(key)!=new[group].get(key):
                        if path in leaves and group=='scalars' and key=='UseEmissiveColorTexture' and new[group][key]==0.0:continue
                        report['mismatches'].append({'material':path,'group':group,'field':key,'before':prev[group].get(key),'after':new[group].get(key)})
            if new['overrides']!=prev['overrides']:report['mismatches'].append({'material':path,'field':'base_property_overrides'})
        root=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/SceneLook/M_HM_PBR_Masked');assert root
        node=lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_OPACITY_MASK);assert node
        report['opacity_mask_node']=node.get_name()
        report['root_custom_masks']=[n.get_editor_property('code') for n in lib.get_material_expressions(root) if isinstance(n,unreal.MaterialExpressionCustom)]
        assert 'return dot(Value, float4(ChannelRGB.rgb, ChannelA));' in report['root_custom_masks']
        for level,author_name,baseline_name in [('DevMap','DevAuthor02','DevBefore01'),('HeinMach','HeinAuthor03','HeinBefore01')]:
            package='/Game/Maps/'+('DevMap' if level=='DevMap' else 'L_HeinMach_Environment')
            w=unreal.EditorLoadingAndSavingUtils.load_map(package);assert w
            actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors();by={a.get_actor_label():a for a in actors}
            original=json.loads((BASE/baseline_name/'SavedScene.json').read_text())
            assert len(actors)==original['actors']+1,(level,len(actors),original['actors'])
            max_error=0.0
            for label,prev in original['poses'].items():
                a=by[label];p,r,s=a.get_actor_location(),a.get_actor_rotation(),a.get_actor_scale3d()
                now=[p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
                # Quaternions may round equivalent 180/-180 angles on save. Compare wrapped deltas.
                errors=[abs(x-y) if i not in [3,4,5] else abs((x-y+180.0)%360.0-180.0) for i,(x,y) in enumerate(zip(now,prev[1:]))]
                max_error=max(max_error,max(errors))
                assert max(errors)<0.001,(label,errors)
            pp=[a for a in actors if isinstance(a,unreal.PostProcessVolume)]
            assert len(pp)==1 and pp[0].get_actor_label()=='Art_NaturalLighting_'+level
            settings=pp[0].get_editor_property('settings')
            expected=json.loads((BASE/author_name/'Authoring.json').read_text())['pp_fields']
            for key,value in expected.items():assert abs(settings.get_editor_property(key)-value)<0.00001,(level,key)
            blendables=settings.get_editor_property('weighted_blendables').get_editor_property('array');assert not blendables
            report['scenes'].append({'level':level,'actor_count':len(actors),'protected_poses':len(original['poses']),'max_pose_error':max_error,'postprocess':pp[0].get_actor_label(),'custom_blendables':0,'saved_settings_match':True})
        assert not report['mismatches'],report['mismatches'][:5]
    report['success']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
report['dirty_content']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(OUT/'SavedAudit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
