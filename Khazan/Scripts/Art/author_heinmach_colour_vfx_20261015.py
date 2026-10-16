"""Small isolated scene/exposure edits and reuse the exact saved Brutal hit burst."""
from pathlib import Path
import difflib,hashlib,json,os,traceback
import unreal as u

main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
assert root==main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=Path(os.environ['KZ_HM_COLOUR_OUT']);lib=u.MaterialEditingLibrary
usage=json.loads((main/'Metadata/HeinMachColourVFX_20261015/BaselineAudit02/Usage.json').read_text(encoding='utf-8'))
report={'status':'running','source_of_numbers':'TEMP visual tuning against saved original photos; not original lighting metadata',
        'saved':[],'changes':[],'exposure_roots':[],'hit_bindings':[]}
# All artistic values are owned by map Details or material parameters. Values
# below are TEMP visual candidates; one is the engine's identity compensation.
policy={'sun_lux':1600.0,'sky_intensity':2.3,'sun_colour_srgb':[218,234,255],
        'sky_colour_srgb':[215,228,255],'hein_exposure_bias_ev':-1.25,
        'blood_linear_rgb':[.18,.003,.008],'blood_roughness':.38,'blood_metallic':0.0,
        'blood_shadow_readability_emission':.3}
report['policy_TEMP']=policy

def package(obj):return obj.get_path_name().split('.')[0]
def file(path):return root/('Content/'+path.removeprefix('/Game/')+('.umap' if path.startswith('/Game/Maps/') else '.uasset'))
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def val(value):return value if value is None or isinstance(value,(bool,int,float,str)) else value.export_text() if hasattr(value,'export_text') else str(value)
def change(obj,name,value):
    before=val(obj.get_editor_property(name));obj.set_editor_property(name,value)
    report['changes'].append({'object':obj.get_path_name() if isinstance(obj,u.Object) else 'PostProcessSettings',
                              'field':name,'before':before,'after':val(obj.get_editor_property(name))})
def save(obj,before):
    path=package(obj)
    assert u.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False),path
    report['saved'].append({'asset':path,'before_sha256':before,'after_sha256':sha(path)})
def export(obj,name):
    task=u.AssetExportTask();task.object=obj;task.filename=str(out/name)
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    return Path(task.filename).read_text(encoding='utf-8-sig')
try:
    for level in ('DevMap','L_HeinMach_Environment'):
        path='/Game/Maps/'+level;before=sha(path)
        world=u.EditorLoadingAndSavingUtils.load_map(path);assert world,path
        actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
        pp=[actor for actor in actors if isinstance(actor,u.PostProcessVolume) and actor.get_actor_label().startswith('Art_NaturalLighting_')]
        assert len(pp)==1,(path,len(pp))
        settings=pp[0].get_editor_property('settings')
        # Local exposure was different in these two maps and modifies particles
        # after their emissive compensation. Identity keeps the common tonemap.
        for name in ('local_exposure_highlight_contrast_scale','local_exposure_shadow_contrast_scale'):
            change(settings,'override_'+name,True);change(settings,name,1.0)
        # No map-wide hue/saturation grade is introduced. The cold scene palette
        # is produced by scene lighting, so unlit feedback keeps its authored hue.
        for name in ('color_saturation','color_contrast','color_gamma','color_gain'):
            change(settings,'override_'+name,False)
        change(settings,'override_color_offset',False)
        if level!='DevMap':
            change(settings,'override_auto_exposure_bias',True)
            change(settings,'auto_exposure_bias',policy['hein_exposure_bias_ev'])
            for actor in actors:
                for component in actor.get_components_by_class(u.DirectionalLightComponent):
                    change(component,'intensity',policy['sun_lux'])
                    colour=policy['sun_colour_srgb'];change(component,'light_color',u.Color(r=colour[0],g=colour[1],b=colour[2],a=255))
                for component in actor.get_components_by_class(u.SkyLightComponent):
                    change(component,'intensity',policy['sky_intensity'])
                    colour=policy['sky_colour_srgb'];change(component,'light_color',u.Color(r=colour[0],g=colour[1],b=colour[2],a=255))
        pp[0].set_editor_property('settings',settings)
        assert u.EditorLoadingAndSavingUtils.save_map(world,path)
        report['saved'].append({'asset':path,'before_sha256':before,'after_sha256':sha(path)})
    for row in usage['roots']:
        path=row['material']
        if not path.startswith('/Game/') or 'MD_SURFACE' not in row.get('material_domain',''):continue
        if not row.get('emissive_node'):continue
        material=u.load_asset(path);assert material,path
        if path.endswith('M_KZGiant_TechnicalHidden'):continue
        emission=lib.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR)
        assert emission,path
        before=sha(path)
        changed=False
        if not row['eye_adaptation_inverse_count']:
            inverse=lib.create_material_expression(material,u.MaterialExpressionEyeAdaptationInverse)
            one=lib.create_material_expression(material,u.MaterialExpressionConstant);one.set_editor_property('r',1.0)
            inputs=list(lib.get_material_expression_input_names(inverse))
            assert lib.connect_material_expressions(emission,'',inverse,next(x for x in inputs if 'Light' in x))
            assert lib.connect_material_expressions(one,'',inverse,next(x for x in inputs if 'Alpha' in x))
            assert lib.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
            changed=True
        # Combat colour remains sharp in the level atmosphere. Weather materials
        # still participate in the scene fog; depth occlusion is never disabled.
        if path.startswith(('/Game/_Art/Effects/','/Game/VFX/')) and 'UNLIT' in row.get('shading_model',''):
            try:
                if material.get_editor_property('bUseTranslucencyVertexFog'):
                    change(material,'bUseTranslucencyVertexFog',False);changed=True
            except Exception:pass
        if changed:
            errors=list(lib.recompile_material(material));assert not errors,(path,errors)
            save(material,before)
        report['exposure_roots'].append({'material':path,'changed':changed,
            'policy':'EyeAdaptationInverse Alpha1, full engine exposure compensation; authored colour math retained'})
    path='/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodGround'
    material=u.load_asset(path);assert material;before=sha(path)
    nodes=list(lib.get_material_expressions(material))
    colour=next(x for x in nodes if isinstance(x,u.MaterialExpressionVectorParameter) and str(x.get_editor_property('parameter_name'))=='BloodColor')
    change(colour,'default_value',u.LinearColor(*policy['blood_linear_rgb'],1))
    for name,key in [('BloodRoughness','blood_roughness'),('BloodMetallic','blood_metallic')]:
        node=next(x for x in nodes if isinstance(x,u.MaterialExpressionScalarParameter) and str(x.get_editor_property('parameter_name'))==name)
        change(node,'default_value',policy[key])
    assert not lib.get_material_property_input_node(material,u.MaterialProperty.MP_EMISSIVE_COLOR)
    strength=lib.create_material_expression(material,u.MaterialExpressionScalarParameter)
    strength.set_editor_property('parameter_name','BloodShadowReadabilityEmission')
    strength.set_editor_property('default_value',policy['blood_shadow_readability_emission'])
    multiply=lib.create_material_expression(material,u.MaterialExpressionMultiply)
    assert lib.connect_material_expressions(colour,'RGB',multiply,'A')
    assert lib.connect_material_expressions(strength,'',multiply,'B')
    inverse=lib.create_material_expression(material,u.MaterialExpressionEyeAdaptationInverse)
    one=lib.create_material_expression(material,u.MaterialExpressionConstant);one.set_editor_property('r',1.0)
    inputs=list(lib.get_material_expression_input_names(inverse))
    assert lib.connect_material_expressions(multiply,'',inverse,next(x for x in inputs if 'Light' in x))
    assert lib.connect_material_expressions(one,'',inverse,next(x for x in inputs if 'Alpha' in x))
    assert lib.connect_material_property(inverse,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=list(lib.recompile_material(material));assert not errors,errors
    save(material,before)
    blood=u.load_asset('/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub');assert blood
    for row in usage['definitions']:
        path=row['asset'];obj=u.load_asset(path);assert obj;before=sha(path)
        old=export(obj,Path(path).name+'_Before.t3d')
        settings=obj.get_editor_property('HitReactions')
        settings.set_editor_property('ImpactEffect',blood);obj.set_editor_property('HitReactions',settings)
        new=export(obj,Path(path).name+'_After.t3d')
        diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),lineterm=''))
        changes=[x[1:].strip() for x in diff if x[:1] in ('+','-') and not x.startswith(('+++','---'))]
        assert all(x.startswith('HitReactions=') for x in changes),(path,changes)
        (out/(Path(path).name+'_Changes.patch')).write_text('\n'.join(diff),encoding='utf-8')
        save(obj,before)
        report['hit_bindings'].append({'definition':path,'particle':blood.get_path_name(),'source':'exact saved Brutal success-only Trail_Sub template, no PS duplication'})
    report['status']='candidate_saved'
except Exception:
    report['status']='failed';report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (out/'Author.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['status']=='candidate_saved',report.get('error')
print('HEIN_COLOUR_AUTHORED',len(report['saved']))
