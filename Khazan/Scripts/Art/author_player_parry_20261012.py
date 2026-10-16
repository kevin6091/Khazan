"""Append source-backed JustGuard motion and local feathered effects only."""
from pathlib import Path
import bisect, json, os, re, runpy, traceback, uuid
import unreal as u
MAIN=Path(os.environ['KZ_PARRY_MAIN']);ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT'])
assert ROOT==MAIN.parent.parent/'Khazan_ParryWork_20261012/Khazan'
GUARD='/Game/_Art/Player/Animation/InGame/DAS/Guard';FXROOT='/Game/_Art/Effects/Combat/GuardParry/PlayerParry'
EAL=u.EditorAssetLibrary;AL=u.AnimationLibrary;LIB=u.MaterialEditingLibrary;FX=u.FXConverterUtilitiesLibrary
HELP=runpy.run_path(str(MAIN/'Scripts/Animation/fix_das_composite_playback_60fps.py'),run_name='parry_pose_helpers')
SERIAL=runpy.run_path(str(MAIN/'Scripts/Animation/setup_guard_20261002.py'),run_name='parry_guard_serializer')
R={'status':'running','animations':[],'materials':[],'particles':[],'saved':[]}
KEEP=[];CLONED={}
def save(a):
    path=a.get_path_name().split('.')[0]
    assert path.startswith(GUARD+'/') or path.startswith(FXROOT+'/') or path=='/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard',path
    assert EAL.save_loaded_asset(a,only_if_is_dirty=False),path
    if path not in R['saved']:R['saved'].append(path)
def duplicate(src,dst):
    assert not EAL.does_asset_exist(dst),'Preserve already-authored candidate '+dst
    a=EAL.duplicate_asset(src,dst);assert a,dst;KEEP.append(a);return a
def interp(t,x,y):
    if t<=x[0]:return y[0]
    if t>=x[-1]:return y[-1]
    i=bisect.bisect_right(x,t);return y[i-1]+(y[i]-y[i-1])*(t-x[i-1])/(x[i]-x[i-1])
def motion(side):
    # Original DamageL uses sequence JustGuard_R; DamageR uses JustGuard_L.
    source_side='R' if side=='L' else 'L'
    src='/Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Combat/Defense/JustGuard/CA_P_Kazan_DualAxeSword_Def_JustGuard_'+source_side
    package='BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard/AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_'+side
    raw=MAIN/('Saved/Extracted/InGame_Playback_20261002/Metadata/'+package+'.json')
    props=json.loads(raw.read_text(encoding='utf-8-sig'))[0]['Properties'];curve=props['DilationCurve'];positions=curve['DilationAnimPositions']
    assert props.get('ApplyDilationCurveType')!='EApplyDilationCurveType::None'
    x=[float(p['T_Original']) for p in positions];y=[float(p['T_Dilation']) for p in positions]
    assert all(b>a for a,b in zip(y,y[1:]))
    frames=round(curve['DilationSequenceLength']*60);length=frames/60
    source=u.load_asset(src);assert abs(source.get_play_length()-.5)<1e-6
    seq=duplicate(src,GUARD+'/Player_Parry_'+side)
    names=list(source.controller.get_model_interface().get_bone_track_names())
    times=[interp(length*i/frames*curve['DilationSequenceLength']/length,y,x) for i in range(frames+1)]
    pos,rot,scale,check=HELP['sample_tracks'](source,names,frames,source.get_play_length(),times)
    controller=u.AnimationDataController.cast(seq.controller);controller.open_bracket('Bake original JustGuard Dilation once',False)
    try:
        controller.set_frame_rate(u.FrameRate(60,1),False);controller.set_number_of_frames(u.FrameNumber(frames),False)
        for i,n in enumerate(names):assert controller.set_bone_track_keys(str(n),pos[i],rot[i],scale[i],False)
    finally:controller.close_bracket(False)
    seq.set_editor_property('rate_scale',1.0)
    # Guard presentation stays on the existing grounded CMC, not a new root drive.
    seq.set_editor_property('enable_root_motion',False);seq.set_editor_property('force_root_lock',True)
    notifies=props['Notifies'];inputend=min(n['LinkValue'] for n in notifies if n['NotifyName']=='xxEnableCancelSK')
    mapped=interp(inputend,x,y)*length/curve['DilationSequenceLength']
    EAL.set_metadata_tag(seq,'KZParrySourceComposite',package)
    contract={'source':package,'source_duration':.5,'DilationSequenceLength':curve['DilationSequenceLength'],'frames':frames,'length':length,
              'input_end_raw':inputend,'input_end':mapped,'source_times':times,'root_rescaled':False,
              'root_lock_policy':'Guard CMC presentation, source topology/bone order preserved'}
    EAL.set_metadata_tag(seq,'KZParryTimingContract',json.dumps(contract));save(seq)
    verify=HELP['verify_replacement'](seq,seq.get_path_name(),names,frames,length,check,{})
    R['animations'].append({'path':seq.get_path_name(),**contract,'pose_verification':verify})
    return seq,mapped
def feather_master(a):
    nodes=list(LIB.get_material_expressions(a));blend=a.get_editor_property('blend_mode')
    prop=u.MaterialProperty.MP_OPACITY_MASK if blend==u.BlendMode.BLEND_MASKED else u.MaterialProperty.MP_OPACITY
    original=LIB.get_material_property_input_node(a,prop)
    output=LIB.get_material_property_input_node_output_name(a,prop)
    assert original,'Selected particle master must expose continuous opacity'
    if blend==u.BlendMode.BLEND_MASKED:
        # This local legacy fallback gets continuous alpha rather than clip edges.
        a.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    masks=[]
    for n in nodes:
        if isinstance(n,u.MaterialExpressionComponentMask) and n.get_editor_property('a'):
            before={c:n.get_editor_property(c) for c in 'rgba'}
            for c in 'rgba':n.set_editor_property(c,c=='a')
            masks.append({'node':n.get_name(),'before':before,'after':{c:n.get_editor_property(c) for c in 'rgba'}})
    uv=LIB.create_material_expression(a,u.MaterialExpressionTextureCoordinate,400,100)
    width=LIB.create_material_expression(a,u.MaterialExpressionScalarParameter,400,260)
    width.set_editor_property('parameter_name','ParryEdgeFeatherUV');width.set_editor_property('default_value',.04)
    custom=LIB.create_material_expression(a,u.MaterialExpressionCustom,650,130)
    ins=[]
    for n in ['UV','Width']:
        i=u.CustomInput();i.set_editor_property('input_name',n);ins.append(i)
    custom.set_editor_property('inputs',ins);custom.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    custom.set_editor_property('description','TEMP user requested smooth particle boundary; 4% inward UV feather')
    custom.set_editor_property('code','float2 d=min(UV,1.0-UV); return smoothstep(0.0,max(Width,0.00001),min(d.x,d.y));')
    assert LIB.connect_material_expressions(uv,'',custom,'UV');assert LIB.connect_material_expressions(width,'',custom,'Width')
    mul=LIB.create_material_expression(a,u.MaterialExpressionMultiply,870,100)
    assert LIB.connect_material_expressions(original,output,mul,'A');assert LIB.connect_material_expressions(custom,'',mul,'B')
    assert LIB.connect_material_property(mul,'',u.MaterialProperty.MP_OPACITY)
    errors=list(LIB.recompile_material(a));assert not errors,errors
    EAL.set_metadata_tag(a,'KZParryAlphaAdapter','Original masks/ParticleColor/depth fade preserved; A-only output and .04 TEMP inward UV edge feather; shared masters unchanged')
    R['materials'].append({'path':a.get_path_name(),'alpha_masks':masks,'feather_uv':.04,'source':'assistant temporary presentation tuning','compile_errors':errors})
def material(src):
    key=src.get_path_name()
    if key in CLONED:return CLONED[key]
    dst=FXROOT+'/Materials/'+src.get_name();a=duplicate(key.split('.')[0],dst);CLONED[key]=a
    if isinstance(a,u.MaterialInstanceConstant):
        a.set_editor_property('parent',material(src.get_editor_property('parent')))
        LIB.update_material_instance(a)
    else:
        assert isinstance(a,u.Material),a
        feather_master(a)
    save(a);return a
def particle():
    src='/Game/_Art/Effects/Combat/GuardParry/PP_AtkEx_JustGuard';a=duplicate(src,FXROOT+'/PP_Player_Parry_Success')
    count=0
    for emitter in FX.get_cascade_system_emitters(a):
        # Original selected effect has one LOD (LODDistances=[5000]).
        lod=FX.get_cascade_emitter_lod_level(emitter,0);required=FX.get_lod_level_required_module(lod)
        old=required.get_editor_property('material');assert old
        new=material(old);required.set_editor_property('material',new);count+=1
    EAL.set_metadata_tag(a,'KZParrySourceParticle',src)
    EAL.set_metadata_tag(a,'KZParryPresentationAdapter','Finite world-space weapon contact flash; full original emitter/distribution graph; local continuous alpha edge repair only')
    save(a);R['particles'].append({'path':a.get_path_name(),'source':src,'emitter_material_bindings':count})
    return a
def montage(sequences):
    m=u.load_asset(GUARD+'/AM_DAS_Player_Guard');assert m
    task=u.AssetExportTask();task.object=m;task.filename=str(OUT/'GuardBefore.t3d');task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    txt=(OUT/'GuardBefore.t3d').read_text(encoding='utf-8-sig')
    sections=re.findall(r'^\s*CompositeSections\(\d+\)=(.*)$',txt,re.M)
    events=[n.export_text() for n in AL.get_animation_notify_events(m)]
    slots=list(m.get_editor_property('slot_anim_tracks'));assert len(slots)==1
    slot=slots[0];track=slot.get_editor_property('anim_track');segments=list(track.get_editor_property('anim_segments'))
    assert len(sections)==5 and len(segments)==5,'Preserve an existing different montage'
    R['original_sections']=sections;R['original_notifies']=events;offset=m.get_play_length()
    for side,seq,timing in sequences:
        length=seq.get_play_length();index=len(segments);name='Parry_'+side
        segment=u.AnimSegment();segment.import_text('(AnimReference="/Script/Engine.AnimSequence\'%s\'",StartPos=%.9f,AnimStartTime=0,AnimEndTime=%.9f,AnimPlayRate=1,LoopingCount=1)'%(seq.get_path_name(),offset,length));segments.append(segment)
        sections.append('(SectionName="%s",NextSectionName="None",LinkValue=%.9f,LinkedMontage="/Script/Engine.AnimMontage\'%s\'",SlotIndex=0,SegmentIndex=%d,SegmentBeginTime=%.9f,SegmentLength=%.9f,LinkMethod=Absolute,CachedLinkMethod=Absolute)'%(name,offset,m.get_path_name(),index,offset,length))
        notify=u.new_object(u.AnimNotify_PlayMontageNotify,outer=m,name='InputEnd_'+name);notify.set_editor_property('notify_name','InputEnd')
        e=u.AnimNotifyEvent();e.import_text('(NotifyName="InputEnd",Notify="/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify\'%s\'",Guid=%s,MontageTickType=BranchingPoint,TrackIndex=0,LinkValue=%.9f,LinkedMontage="/Script/Engine.AnimMontage\'%s\'",SlotIndex=0,SegmentIndex=%d,SegmentBeginTime=%.9f,SegmentLength=%.9f)'%(notify.get_path_name(),uuid.uuid4().hex.upper(),offset+timing,m.get_path_name(),index,offset,length));events.append(e.export_text());offset+=length
    track.set_editor_property('anim_segments',segments);slot.set_editor_property('anim_track',track);m.set_editor_property('slot_anim_tracks',[slot])
    rate=m.controller.get_model_interface().get_frame_rate();m.controller.set_number_of_frames(u.FrameNumber(round(offset*rate.numerator/rate.denominator)),False)
    SERIAL['import_guard_array'](m,'CompositeSections',sections);SERIAL['import_guard_array'](m,'Notifies',events);SERIAL['refresh_notifies'](m);save(m)
    R['montage']={'path':m.get_path_name(),'segments':len(segments),'sections':sections,'notifies':events}
def main():
    seqs=[]
    for side in ['L','R']:
        seq,t=motion(side);seqs.append((side,seq,t))
    effect=particle();montage(seqs)
    bp=u.load_asset('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard');cdo=u.get_default_object(bp.generated_class())
    for name,value in [('ParryWindowSeconds',.146),('ParryStaminaDamageScale',.5),('ParryImpactEffect',effect),('ParryEffectSocket','Weapon_R'),
                       ('ParrySound',u.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc'))]:
        assert value is not None,name;cdo.set_editor_property(name,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    R['status']='passed';R['sound_source']='Original Play_PLYR_DualAxeSword_JustGuard_Suc via existing native audio cue; no audio asset rewritten'
try:main()
except Exception:R['status']='failed';R['error']=traceback.format_exc();raise
finally:(OUT/'Authoring.json').write_text(json.dumps(R,indent=2,default=str),encoding='utf-8')
print('PARRY_AUTHORING',R['status'],len(R['saved']),flush=True)
