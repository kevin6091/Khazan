"""Read back owned fields and preserved data; save no gameplay packages."""
from pathlib import Path
import hashlib,json,os,re
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
out=Path(os.environ['KZ_HM_COLOUR_OUT']);lib=u.MaterialEditingLibrary
base=main/'Metadata/HeinMachColourVFX_20261015'
baseline=json.loads((base/'BaselineAudit02/Usage.json').read_text(encoding='utf-8'))
current=json.loads((base/'CandidateAudit03/Usage.json').read_text(encoding='utf-8'))
report={'status':'running','asset_saves':0,'maps':[],'definitions':[],'materials':[],'systems_unchanged':0}
for path in ('/Game/Maps/DevMap','/Game/Maps/L_HeinMach_Environment'):
    world=u.EditorLoadingAndSavingUtils.load_map(path);assert world
    actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    volumes=[actor for actor in actors if isinstance(actor,u.PostProcessVolume)]
    assert len(volumes)==1,(path,len(volumes))
    volume=volumes[0];settings=volume.get_editor_property('settings')
    assert volume.get_editor_property('enabled') and volume.get_editor_property('unbound')
    for name in ('local_exposure_highlight_contrast_scale','local_exposure_shadow_contrast_scale'):
        assert settings.get_editor_property(name)==1.,(path,name)
    for band in ('','_shadows','_midtones','_highlights'):
        for name in ('color_saturation','color_contrast','color_gamma','color_gain','color_offset'):
            assert not settings.get_editor_property('override_'+name+band),(path,name+band)
    assert not settings.get_editor_property('color_grading_lut'),path
    assert not settings.get_editor_property('weighted_blendables').get_editor_property('array'),path
    report['maps'].append({'map':path,'postprocess_count':len(volumes),'local_exposure_identity':True,
                          'colour_grade_overrides':False,'custom_blendables':0,
                          'exposure_bias_ev':settings.get_editor_property('auto_exposure_bias')})
    if path.endswith('L_HeinMach_Environment'):
        for actor in actors:
            for cls in (u.DirectionalLightComponent,u.SkyLightComponent):
                for light in actor.get_components_by_class(cls):
                    colour=light.get_editor_property('light_color')
                    expected=(205,225,255) if cls==u.DirectionalLightComponent else (195,218,255)
                    assert (colour.r,colour.g,colour.b)==expected
                    assert abs(light.get_editor_property('intensity')-(1800. if cls==u.DirectionalLightComponent else 8.))<.001
            for fog in actor.get_components_by_class(u.ExponentialHeightFogComponent):
                colour=fog.get_editor_property('volumetric_fog_emissive')
                assert abs(colour.r-.025)<.000001 and abs(colour.b-.06)<.000001
        assert abs(settings.get_editor_property('auto_exposure_bias')+1.1)<.000001
blood=u.load_asset('/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub');assert blood
for row in baseline['definitions']:
    obj=u.load_asset(row['asset']);settings=obj.get_editor_property('HitReactions')
    assert settings.get_editor_property('ImpactEffect')==blood,row['asset']
    strip=lambda text:re.sub(r'ImpactEffect=(?:"[^"]*"|None)','ImpactEffect=<owned>',text)
    assert strip(settings.export_text())==strip(row['HitReactions']),row['asset']
    report['definitions'].append({'asset':row['asset'],'impact':blood.get_path_name(),'other_hit_settings_preserved':True})
originals={row['material']:row for row in baseline['roots']}
for row in current['roots']:
    path=row['material']
    if not path.startswith('/Game/'):continue
    obj=u.load_asset(path);assert obj
    if 'MD_SURFACE' in row.get('material_domain',''):
        assert not obj.get_editor_property('bUseTranslucencyVertexFog'),path
    old=originals.get(path)
    if old:
        for name in ('blend_mode','shading_model','material_domain','disable_depth_test','translucency_pass'):
            if name in old:assert str(obj.get_editor_property(name))==old[name] if name!='disable_depth_test' else obj.get_editor_property(name)==old[name],(path,name)
        nodes=list(lib.get_material_expressions(obj))
        # Imported graphs can contain several nodes named Param. Compare the
        # full multiset, including class and default; a name-keyed dict loses
        # those nodes and can falsely compare a scalar to a vector.
        params=[]
        for node in nodes:
            if not isinstance(node,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):continue
            value=node.get_editor_property('default_value')
            params.append({'class':node.get_class().get_name(),'parameter_name':str(node.get_editor_property('parameter_name')),
                           'default_value':value.export_text() if hasattr(value,'export_text') else value})
        normalize=lambda items:sorted(json.dumps(item,sort_keys=True) for item in items)
        assert normalize(params)==normalize(old['parameters']),(path,'parameter multiset changed')
    emission=lib.get_material_property_input_node(obj,u.MaterialProperty.MP_EMISSIVE_COLOR)
    # Pure refraction/hidden roots have no authored colour output in the frozen
    # catalogue. Some engine load paths expose an implicit black default node.
    if row.get('emissive_node'):
        inverse=any(isinstance(node,u.MaterialExpressionEyeAdaptationInverse) for node in lib.get_material_expressions(obj))
        if not inverse:
            if isinstance(emission,u.MaterialExpressionConstant3Vector):
                value=emission.get_editor_property('constant')
                assert value.r==value.g==value.b==0.,(path,value.export_text())
            elif isinstance(emission,u.MaterialExpressionConstant):
                assert emission.get_editor_property('r')==0.,path
            else:raise AssertionError((path,'uncompensated nonzero output',emission.get_class().get_name()))
    report['materials'].append({'material':path,'fog_disabled':not obj.get_editor_property('bUseTranslucencyVertexFog'),
                              'depth_test_disabled':obj.get_editor_property('disable_depth_test')})
ground=u.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround');assert ground
parameters={str(node.get_editor_property('parameter_name')):node.get_editor_property('default_value')
            for node in lib.get_material_expressions(ground)
            if isinstance(node,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter))}
colour=parameters['BloodColor']
assert abs(colour.r-.08)<.000001 and abs(colour.g-.0016)<.000001 and abs(colour.b-.003)<.000001
assert abs(parameters['BloodShadowReadabilityEmission']-.04)<.000001
assert abs(parameters['BloodRoughness']-.38)<.000001 and parameters['BloodMetallic']==0.
report['blood_parameters']={key:value.export_text() if hasattr(value,'export_text') else value for key,value in parameters.items()}
for row in baseline['systems']:
    if not row['sha256']:continue
    file=root/('Content/'+row['asset'].removeprefix('/Game/')+'.uasset')
    assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256'],row['asset']
    report['systems_unchanged']+=1
report['status']='passed'
(out/'SavedVerification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('HEIN_COLOUR_SAVED_PASSED',len(report['definitions']),len(report['materials']),report['systems_unchanged'])
