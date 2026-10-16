"""Source recovery timing/meshes/LUTs, explicitly reconstructed native rendering."""
from pathlib import Path
import hashlib, json, os, re, runpy, traceback, uuid
import unreal as u

MAIN = Path(__file__).resolve().parents[2]
WORK = Path(u.Paths.project_dir()).resolve()
assert WORK == MAIN.parent.parent/'Khazan_HealVFXWork_20261013/Khazan'
OUT = Path(os.environ['KZ_HEAL_VFX_OUT'])
DATA = MAIN/'Metadata/HealVFX_20261013'
ROOT = '/Game/HealVFX'
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
KEEP = []
R = dict(status='running', saved=[], original_events=[], adapters=[], temporary_tuning={}, shaders=[])

def save(a):
    path=a.get_path_name().split('.')[0]
    file=WORK/('Content/'+path.removeprefix('/Game/')+'.uasset')
    assert file.resolve().is_relative_to(WORK), 'Borrowed package write forbidden'
    assert path.startswith(ROOT+'/') or path.endswith('/Heal/AM_DAS_Player_Heal')
    assert EAL.save_loaded_asset(a,only_if_is_dirty=False)
    R['saved'].append(path)

def make(name, cls, factory, sub=''):
    folder=ROOT+('/'+sub if sub else '')
    assert not EAL.does_asset_exist(folder+'/'+name), 'Preserve existing authored package'
    a=TOOLS.create_asset(name,folder,cls,factory);assert a;KEEP.append(a);return a

def imported(name, suffix, factory):
    file=next((DATA/'Payload').rglob(name+suffix))
    old=u.load_asset(ROOT+'/Source/'+name)
    if old:
        assert EAL.get_metadata_tag(old,'KZHealOriginalPayloadSHA256')==hashlib.sha256(file.read_bytes()).hexdigest()
        KEEP.append(old);return old
    task=u.AssetImportTask()
    for k,v in dict(filename=str(file),destination_path=ROOT+'/Source',destination_name=name,
                    automated=True,replace_existing=False,save=False,factory=factory).items():task.set_editor_property(k,v)
    TOOLS.import_asset_tasks([task]);a=u.load_asset(ROOT+'/Source/'+name);assert a
    EAL.set_metadata_tag(a,'KZHealOriginalPayloadSHA256',hashlib.sha256(file.read_bytes()).hexdigest())
    KEEP.append(a);return a

# Reuse the existing named-object serializer and Cascade factory; no new runtime authoring API.
prefix=(MAIN/'Scripts/Art/combat_effects_import.py').read_text(encoding='utf-8').split('\ntry:\n    main()')[0]
prefix=prefix.replace("path.startswith('/Game/_Art/Effects/')", "path.startswith('/Game/HealVFX/')")
H={};exec(compile(prefix,'<existing cascade definitions>','exec'),H)
H.update(ROOT=WORK,META=OUT,BASE=OUT,save=save,ROWS=[],LOOKUP={})
SERIAL=runpy.run_path(str(MAIN/'Scripts/Animation/setup_guard_20261002.py'))
SERIAL['import_guard_array'].__globals__['GUARD']='/Game/_Art/Player/Animation/InGame/DAS/Heal'

def node(mat, cls):return LIB.create_material_expression(mat,cls)
def link(a,p,b,q):assert LIB.connect_material_expressions(a,p,b,q)
def scalar(mat,name,value):
    a=node(mat,u.MaterialExpressionScalarParameter);a.set_editor_property('parameter_name',name);a.set_editor_property('default_value',value);return a
def custom(mat,inputs,code):
    a=node(mat,u.MaterialExpressionCustom);a.set_editor_property('code',code)
    a.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    values=[]
    for n in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',n);values.append(pin)
    a.set_editor_property('inputs',values);return a

def material(name, trail=False, sphere=False):
    old=u.load_asset(ROOT+'/Materials/'+name)
    if old:
        assert EAL.get_metadata_tag(old,'KZHealShaderBoundary').startswith('Native reconstruction;')
        KEEP.append(old);return old
    m=make(name,u.Material,u.MaterialFactoryNew(),'Materials')
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('two_sided',True)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    pc=node(m,u.MaterialExpressionParticleColor)
    edge=custom(m,['UV','Width'], 'float w=max(Width,1.25*max(length(ddx(UV)),length(ddy(UV)))); return smoothstep(0,w,UV.y)*smoothstep(0,w,1-UV.y);' if trail else 'float r=length((UV-float2(.5,.5))*2); return 1-smoothstep(.15,1,r);')
    width=scalar(m,'EdgeFeatherUV',.04);link(uv,'',edge,'UV');link(width,'',edge,'Width')
    mask=edge
    if trail:
        tex=node(m,u.MaterialExpressionTextureSampleParameter2D);tex.set_editor_property('parameter_name','Original_MainTex_G');tex.set_editor_property('texture',TRAIL)
        tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        pan=node(m,u.MaterialExpressionPanner);pan.set_editor_property('speed_x',.3);link(uv,'',pan,'Coordinate');link(pan,'',tex,'UVs')
        product=node(m,u.MaterialExpressionMultiply);link(tex,'G',product,'A');link(edge,'',product,'B');mask=product
    if sphere:
        fres=node(m,u.MaterialExpressionFresnel);fres.set_editor_property('exponent',3.0)
        power=node(m,u.MaterialExpressionMultiply);link(fres,'',power,'A');link(fres,'',power,'B');mask=power
    bounded=custom(m,['Mask','Alpha'],'return saturate(Mask)*saturate(Alpha);');link(mask,'',bounded,'Mask');link(pc,'A',bounded,'Alpha')
    fade=node(m,u.MaterialExpressionDepthFade);link(bounded,'',fade,'Opacity')
    link(scalar(m,'DepthFadeCM',8.0),'',fade,'FadeDistance')
    assert LIB.connect_material_property(fade,'',u.MaterialProperty.MP_OPACITY)
    tint=node(m,u.MaterialExpressionVectorParameter);tint.set_editor_property('parameter_name','RecoveryTint')
    tint.set_editor_property('default_value',u.LinearColor(1.0,.03,.008,1.0))
    col=node(m,u.MaterialExpressionMultiply);link(pc,'',col,'A');link(tint,'',col,'B')
    gain=node(m,u.MaterialExpressionMultiply);link(col,'',gain,'A');link(scalar(m,'EmissiveGain',8.0),'',gain,'B')
    assert LIB.connect_material_property(gain,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    errors=LIB.recompile_material(m);assert not errors, str(errors)
    EAL.set_metadata_tag(m,'KZHealShaderBoundary','Native reconstruction; original FT_Trail G density for mesh. Additive continuous alpha, bounded particle A, derivative feather, DepthFade. No original stripped graph parity claim.')
    save(m);R['shaders'].append(dict(path=m.get_path_name(),compile_errors=str(errors)))
    return m

def raw(values,channels=1,uniform=False):
    # Native lookup table + existing importer derives editable distributions.
    values=values if isinstance(values,list) else [values]
    count=len(values);flat=[]
    for v in values:flat.extend(v if isinstance(v,(list,tuple)) else [v])
    stride=channels*(2 if uniform else 1)
    return dict(Distribution=None,Table=dict(Op=2 if uniform else 1,EntryCount=count,EntryStride=stride,SubEntryStride=channels if uniform else 0,TimeScale=float(count-1) if count>1 else 0.0,TimeBias=0.0,Values=flat))

def source_curve(name,index):
    file=DATA/('Original/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/PC/Recovery/'+name+'.json')
    objects=json.loads(file.read_text(encoding='utf-8-sig'));obj=objects[index];lut=obj['Properties']['ShaderLUT']
    assert obj['Type']=='NiagaraDataInterfaceColorCurve'
    R.setdefault('curve_sources',[]).append(dict(file=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),export_index=index,field='Properties.ShaderLUT',samples=len(lut)//4,normalized_age_adapter='Samples assumed uniformly normalized over particle lifetime; original VM topology unavailable'))
    return [lut[i:i+4] for i in range(0,len(lut),4)]

class Graph:
    def __init__(self,name,source):
        self.name=name;self.source=source;self.package='KZHealNative/'+name
        self.data=[dict(Type='ParticleSystem',Name=name,Properties=dict(Emitters=[],bUseFixedRelativeBoundingBox=False))]
    def ref(self,i):return dict(ObjectPath=self.package+'.'+str(i))
    def add(self,typ,outer,props):
        i=len(self.data);self.data.append(dict(Type=typ,Name='O'+str(i),Outer=self.ref(outer),Properties=props));return i
    def external(self,obj):
        path=obj.get_path_name().split('.')[0];H['LOOKUP'][path]=dict(destination=path);return dict(ObjectPath=obj.get_path_name())
    def emitter(self,mat,lifetime,size,color,count=1,rate=0,spread=0,velocity=0,mesh=None,attract=False):
        i=self.add('ParticleSpriteEmitter',0,dict(EmitterName='Heal_'+str(len(self.data)),DetailModeBitmask=15,LODLevels=[]))
        self.data[0]['Properties']['Emitters'].append(self.ref(i))
        lod=self.add('ParticleLODLevel',i,dict(Level=0,bEnabled=True,Modules=[]))
        self.data[i]['Properties']['LODLevels']=[self.ref(lod)]
        req=self.add('ParticleModuleRequired',0,dict(Material=self.external(mat),bUseLocalSpace=True,EmitterDuration=lifetime,EmitterLoops=1,bKillOnDeactivate=False,bKillOnCompleted=False,bDurationRecalcEachLoop=False))
        spawn=self.add('ParticleModuleSpawn',0,dict(Rate=raw(rate),BurstList=[dict(Count=count,CountLow=-1,Time=0.0)] if count else []))
        props=self.data[lod]['Properties'];props.update(RequiredModule=self.ref(req),SpawnModule=self.ref(spawn))
        modules=[]
        def module(typ,pr):j=self.add(typ,0,pr);modules.append(self.ref(j));return j
        module('ParticleModuleLifetime',dict(LifeTime=raw(lifetime)))
        module('ParticleModuleSize',dict(StartSize=raw([size],3)))
        module('ParticleModuleLocation',dict(StartLocation=raw([[-spread,-spread,-spread,spread,spread,spread]],3,True)))
        module('ParticleModuleVelocity',dict(StartVelocity=raw([[-velocity,-velocity,-velocity,velocity,velocity,velocity]],3,True)))
        module('ParticleModuleColorOverLife',dict(ColorOverLife=raw([v[:3] for v in color],3),AlphaOverLife=raw([v[3] for v in color]),bClampAlpha=True))
        if attract:
            module('ParticleModuleAttractorPoint',dict(Position=raw([[0,0,0]],3),Range=raw(40.0),Strength=raw(65.0),StrengthByDistance=False,bAffectBaseVelocity=True))
        if mesh:
            typed=self.add('ParticleModuleTypeDataMesh',0,dict(Mesh=self.external(mesh),bOverrideMaterial=True,MeshAlignment='PSMA_MeshFaceCameraWithLockedAxis'))
            props['TypeDataModule']=self.ref(typed)
        props['Modules']=modules
    def build(self):
        file=OUT/(self.name+'.json');file.write_text(json.dumps(self.data,indent=2),encoding='utf-8')
        row=dict(source_package=self.package,source_type='ParticleSystem',source_json=str(file),source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),name=self.name,destination=ROOT+'/Particles/'+self.name)
        ps=H['cascade'](row);EAL.set_metadata_tag(ps,'KZHealOriginalSystem',self.source)
        EAL.set_metadata_tag(ps,'KZHealNativeAdapter','Original recovery mesh/LUT/timing contracts; rebuilt Cascade rendering, source Niagara VM/skin sampling/WPO not recovered. Spawn count, lifetime range, position/velocity are explicit artist TEMP.')
        save(ps);return ps

def effect_fields(effect,ps,event,bone,location=None):
    for k,v in dict(ParticleTemplate=ps,EventId=event,SourceSocket=bone,bAttached=True,bDestroyOnAnimEnd=True,bDestroyOnNotifyEndDeactived=True,
                    SourcePackage='BBQ/Content/_Kazan_/Design/Kazan/Skill/Common/Recovery/AC_Kazan_Recovery',SourceField='SourceEvents.json; native skin-bone rendering adapter').items():effect.set_editor_property(k,v)
    if location:effect.set_editor_property('RelativeLocation',u.Vector(*[location[k] for k in 'XYZ']))

def montage(core,burst,arm,finger,flash):
    m=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal');assert m
    before=[n.export_text() for n in u.AnimationLibrary.get_animation_notify_events(m)]
    slots=m.get_editor_property('slot_anim_tracks');segments=slots[0].get_editor_property('anim_track').get_editor_property('anim_segments')
    heal=next(s for s in segments if s.get_editor_property('anim_reference').get_name().endswith('Heal_01'))
    offset=heal.get_editor_property('start_pos');rate=heal.get_editor_property('anim_play_rate')*heal.get_editor_property('anim_reference').get_editor_property('rate_scale')
    assert abs(rate-1)<1e-6, 'Current heal mapping requires re-evaluation for nonunit rate'
    cls=u.load_class(None,'/Script/Khazan.KZAnimNotify_CombatEffect');events=json.loads((DATA/'SourceEvents.json').read_text())
    times={};plans=[];mes=u.load_asset('/Game/Player/Model/SK_Player')
    # Read the current skeleton independently; socket presence is checked before save.
    for e in events:
        i=e['index'];start=offset+e['time']/rate;end=offset+(e['time']+e['duration'])/rate
        if i==2:parts=[(core,'Bip001-L-Hand',e['properties']['ParticleInfo']['RelativeLocation'])]
        elif i==5:parts=[(burst,'FX-L-Finger32',None)]
        elif i==6:parts=[(arm,b,None) for b in ['Bip001-L-UpperArm','Bip001-L-Forearm','Bip001-L-Hand']]
        elif i==7:parts=[(finger,b,None) for b in ['Bip001-L-Finger01','Bip001-L-Finger1','Bip001-L-Finger2','Bip001-L-Finger3','Bip001-L-Finger4']]
        else:parts=[(flash,'Bip001-L-Hand',e['properties']['ParticleInfo']['RelativeLocation'])]
        for j,(ps,bone,loc) in enumerate(parts):
            plan=dict(id='KZHeal_'+str(i)+'_'+str(j),start=start,end=end,particle=ps.get_path_name(),socket=bone,original=e,location=loc)
            plans.append(plan)
            for ending,t in [(False,start),(True,end)]:times.setdefault(round(t,7),[]).append((ending,plan,ps))
    original=list(u.AnimationLibrary.get_animation_notify_events(m))
    u.AnimationLibrary.add_animation_notify_track(m,'KZHealVFX')
    for t,entries in sorted(times.items()):
        marker=u.AnimationLibrary.add_animation_notify_event(m,'KZHealVFX',t,cls);assert marker
        marker.set_editor_property('notify_name','KZCombatEffect');children=[]
        for ending,plan,ps in entries:
            child=u.new_object(cls,outer=marker);KEEP.append(child)
            effect_fields(child,ps,plan['id'],plan['socket'],plan['location'])
            for key,value in [('bEndEvent',ending),('WindowStartTime',plan['start']),('WindowEndTime',plan['end'])]:child.set_editor_property(key,value)
            child.set_editor_property('bDestroyOnNotifyEnd',plan['original']['index']==2)
            children.append(child)
        marker.set_editor_property('BatchedEffects',children)
    # add_animation_notify_event refreshes public caches but loses subframe LinkValue
    # on some branches; explicit serializer retains exact source-derived seconds.
    all_events=list(u.AnimationLibrary.get_animation_notify_events(m))
    SERIAL['import_guard_array'](m,'Notifies',[n.export_text() for n in all_events]);SERIAL['refresh_notifies'](m)
    after=[n.export_text() for n in u.AnimationLibrary.get_animation_notify_events(m)]
    assert all(x in after for x in before), 'Existing HP/audio/weapon/cancel notify changed'
    R['montage']=dict(path=m.get_path_name(),offset=offset,rate=rate,before=before,after=after,plans=plans)
    EAL.set_metadata_tag(m,'KZHealVFXSource','AC_Kazan_Recovery.Notifies indices2/5/6/7/10 + current Stow segment offset; original source times, current unit Heal rate. Gameplay HP timing unchanged.')
    save(m)

try:
    TRAIL=imported('FT_Trail','.png',u.TextureFactory());TRAIL.set_editor_property('srgb',False);save(TRAIL)
    SPHERE=imported('FS_Sphere','.pskx',u.PSKXFactory());save(SPHERE)
    RING=imported('FS_SmallRing_01','.pskx',u.PSKXFactory());save(RING)
    FINGER=imported('FS_BloodRing_01','.pskx',u.PSKXFactory());save(FINGER)
    GLOW=material('M_Heal_SoftGlow');FLOW=material('M_Heal_OriginalTrail',trail=True);FRES=material('M_Heal_CoreFresnel',sphere=True)
    corecurve=source_curve('FP_DrainCore',1);sparkcurve=source_curve('FP_DrainCore_Explo1',0);armcurve=source_curve('FP_KazanGhostHand_Init',0);fingercolor=source_curve('FP_KazanGhostHand_A_Finger_init',0)
    redcurve=source_curve('FP_DrainCore_Explo1',4)
    core=Graph('PS_Heal_DrainCore','FP_DrainCore')
    core.emitter(GLOW,.75,[1.2,1.2,1.2],corecurve,count=12,rate=40,spread=9,attract=True)
    core.emitter(FRES,.750875,[.12,.12,.12],corecurve,mesh=SPHERE)
    burst=Graph('PS_Heal_DrainBurst','FP_DrainCore_Explo1')
    burst.emitter(GLOW,.6,[1.8,1.8,1.8],sparkcurve,count=42,spread=3,velocity=32)
    burst.emitter(GLOW,.5,[22,22,22],redcurve,count=1)
    arm=Graph('PS_Heal_GhostArm','FP_KazanGhostHand_Init');arm.emitter(FLOW,.626166,[4,1,1],armcurve,mesh=RING)
    arm.emitter(GLOW,.55,[.8,.8,.8],redcurve,count=10,spread=5,velocity=5)
    finger=Graph('PS_Heal_GhostFinger','FP_KazanGhostHand_A_Finger_init');finger.emitter(FLOW,.626166,[5,5,5],fingercolor,mesh=FINGER)
    flash=Graph('PS_Heal_LightFlash','FP_DrainCore_Explo');flash.emitter(GLOW,.4,[16,16,16],redcurve,count=1)
    montage(core.build(),burst.build(),arm.build(),finger.build(),flash.build())
    R['temporary_tuning']=dict(source_vm_unavailable=True,shader=dict(edge_uv=.04,edge_min_pixels=1.25,depth_fade_cm=8,emissive_gain=8,trail_pan_cycles_sec=.3,tint=[1,.03,.008]),
       core=dict(sprite_size_cm=1.2,spawn_burst=12,rate_per_sec=40,spread_cm=9,point_strength=65,range_cm=40,sphere_scale=.12),
       burst=dict(count=42,sprite_cm=1.8,lifetime_s=.6,spread_cm=3,velocity_cm_sec=32,glow_cm=22),arm_motes=dict(count=10,spread_cm=5,velocity_cm_sec=5),flash=dict(size_cm=16,lifetime_s=.4))
    R['adapters']=['Cooked Niagara graph unavailable: source five event roles rebuilt with native Cascade factory.', 'Root-attached source skeletal-mesh DI filtered bones rendered as independently bone-attached source ring particles.', 'Source LUT sample RGBA retained; LUT time assumed normalized particle age. Shader rewritten locally with original FT_Trail G channel.', 'Original custom xxPointLight burst represented by finite soft glow; no light/shadow changes.']
    R['status']='passed'
except Exception:
    R['status']='failed';R['error']=traceback.format_exc();raise
finally:
    (OUT/'Author.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8')
print('HEAL_VFX_AUTHOR',R['status'],len(R['saved']),flush=True)
