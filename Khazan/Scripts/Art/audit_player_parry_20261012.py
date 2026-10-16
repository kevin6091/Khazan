"""Fresh saved readback, source timing/old-notify conservation and alpha wiring."""
from pathlib import Path
import json, os, re, traceback, unreal as u
MAIN=Path(os.environ['KZ_PARRY_MAIN']);OUT=Path(os.environ['KZ_PARRY_OUT']);ROOT=Path(u.Paths.project_dir()).resolve()
EAL=u.EditorAssetLibrary;AL=u.AnimationLibrary;LIB=u.MaterialEditingLibrary
A=json.loads((MAIN/'Metadata/Parry_20261012/Author01/Authoring.json').read_text())
R={'status':'running','project':str(ROOT),'asset_saves':0,'animations':[],'materials':[]}
def export(a,n):
    t=u.AssetExportTask();t.object=a;t.filename=str(OUT/(n+'.t3d'));t.automated=True;t.prompt=False
    assert u.Exporter.run_asset_export_task(t);return (OUT/(n+'.t3d')).read_text(encoding='utf-8-sig')
try:
    for r in A['animations']:
        a=u.load_asset(r['path']);m=a.controller.get_model_interface();assert m.get_number_of_frames()==22
        assert abs(a.get_play_length()-r['length'])<1e-6;assert a.get_editor_property('rate_scale')==1
        assert EAL.get_metadata_tag(a,'KZParrySourceComposite')==r['source']
        R['animations'].append({'path':a.get_path_name(),'frames':m.get_number_of_frames(),'length':a.get_play_length(),'source_contract':json.loads(EAL.get_metadata_tag(a,'KZParryTimingContract'))})
    guard=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Guard/AM_DAS_Player_Guard')
    txt=export(guard,'GuardSaved');sections=re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$',txt,re.M)
    before=(MAIN/'Metadata/Parry_20261012/Probe01/GuardMontageBefore.t3d').read_text(encoding='utf-8-sig')
    oldsections=re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$',before,re.M)
    assert len(oldsections)==5 and len(sections)==7
    # Section segment links are derived caches. PostEditChange relinks Suc_R
    # onto the preceding segment at its float boundary; its absolute clock,
    # name/next and all original playback segments must remain unchanged.
    def section_contract(s):
        return re.sub(r',?(?:SegmentIndex|SegmentBeginTime|SegmentLength)=[^,)]+|,?LinkedSequence="[^"]*"','',s)
    assert [section_contract(s) for s in sections[:5]]==[section_contract(s) for s in oldsections]
    oldsegments=re.findall(r'\(AnimReference=(.*?)\)(?=,|\))',before)
    newsegments=re.findall(r'\(AnimReference=(.*?)\)(?=,|\))',txt)
    assert len(oldsegments)==5 and newsegments[:5]==oldsegments,'Existing Guard playback changed'
    oldevents=re.findall(r'^\s*Notifies\(\d+\)=(.*)$',before,re.M)
    events=re.findall(r'^\s*Notifies\(\d+\)=(.*)$',txt,re.M)
    assert events[:len(oldevents)]==oldevents,'Existing Guard notify fields changed'
    R['existing_guard_sections_notifies_preserved']=True
    R['derived_section_cache_changes']=[{'before':a,'after':b} for a,b in zip(oldsections,sections[:5]) if a!=b]
    R['existing_playback_segments_preserved']=True
    bp=u.load_asset('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard');cdo=u.get_default_object(bp.generated_class())
    R['ability']={n:str(cdo.get_editor_property(n)) for n in ['ParryWindowSeconds','ParryStaminaDamageScale','ParryImpactEffect','ParryEffectSocket','ParryEffectDetachSeconds','ParrySound']}
    assert abs(cdo.get_editor_property('ParryWindowSeconds')-.146)<1e-6
    assert abs(cdo.get_editor_property('ParryStaminaDamageScale')-.5)<1e-6
    assert abs(cdo.get_editor_property('ParryEffectDetachSeconds')-.06)<1e-6
    assert str(cdo.get_editor_property('ParryEffectSocket'))=='Weapon_R'
    assert cdo.get_editor_property('ParrySound').get_path_name().startswith('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc.')
    for r in A['materials']:
        a=u.load_asset(r['path']);nodes=LIB.get_material_expressions(a)
        assert a.get_editor_property('blend_mode')==u.BlendMode.BLEND_TRANSLUCENT
        p=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParryEdgeFeatherUV')
        assert abs(p.get_editor_property('default_value')-.04)<1e-6
        px=next(n for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParryEdgeSoftnessPixels')
        assert abs(px.get_editor_property('default_value')-1.25)<1e-6
        edge=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and 'smooth particle boundary' in str(n.get_editor_property('description')))
        assert 'fwidth' in str(edge.get_editor_property('code')) and 'smoothstep' in str(edge.get_editor_property('code'))
        for n in nodes:
            if isinstance(n,u.MaterialExpressionComponentMask) and n.get_editor_property('a'):
                assert all(not n.get_editor_property(c) for c in 'rgb')
        alpha=LIB.get_material_property_input_node(a,u.MaterialProperty.MP_OPACITY)
        assert isinstance(alpha,u.MaterialExpressionMultiply)
        R['materials'].append({'path':a.get_path_name(),'blend':str(a.get_editor_property('blend_mode')),'alpha_node':alpha.get_path_name(),'feather_uv':p.get_editor_property('default_value'),'softness_pixels':px.get_editor_property('default_value')})
        export(a,a.get_name())
    R['source_material_overrides_preserved']=[]
    for name in ['FMI_fluid_A_133','FMI_fluid_A_11','FMI_fluid_A_13','FMI_fluid_A_15','FMI_Subuv_Atlas_B_01']:
        mi=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/'+name)
        overrides=mi.get_editor_property('base_property_overrides')
        folder='Fluid' if 'fluid' in name else 'SubUV'
        original=u.load_asset('/Game/_Art/Effects/Shared/Materials/'+folder+'/MI/'+name)
        assert overrides.export_text()==original.get_editor_property('base_property_overrides').export_text()
        R['source_material_overrides_preserved'].append({'path':mi.get_path_name(),'blend':str(overrides.get_editor_property('blend_mode')),'source':original.get_path_name()})
    spark=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/DefaultParticle')
    soft=next(n for n in LIB.get_material_expressions(spark) if isinstance(n,u.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='ParrySparkSoftnessPower')
    assert soft.get_editor_property('default_value')==2.0
    R['spark_softness_power']=2.0
    fluid=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/FM_fluid_A')
    assert not any('TEMP stripped-refraction' in str(n.get_editor_property('description')) for n in LIB.get_material_expressions(fluid) if isinstance(n,u.MaterialExpressionCustom))
    R['particle_export']='ParryParticleSaved.t3d';export(u.load_asset(A['particles'][0]['path']),'ParryParticleSaved')
    R['status']='passed'
except Exception:R['status']='failed';R['error']=traceback.format_exc();raise
finally:(OUT/'SavedAudit.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('PARRY_SAVED_AUDIT',R['status'],flush=True)
