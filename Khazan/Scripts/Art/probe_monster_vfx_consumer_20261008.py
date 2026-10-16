"""Read-only targeted saved consumer identities. Root launches the private commandlet."""
import hashlib
import json
import os
import traceback
from pathlib import Path
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
OUT=MAIN/'Saved/ImportReports/MonsterVFX_20261008/ConsumerProbe'
OUT.mkdir(parents=True,exist_ok=True)

def path(obj):
    return obj.get_path_name() if obj else None

def chain(material):
    rows=[];seen=set()
    while material and path(material) not in seen:
        seen.add(path(material));rows.append({'path':path(material),'class':material.get_class().get_name()})
        if not isinstance(material,unreal.MaterialInstance):break
        material=material.get_editor_property('parent')
    return rows

def mesh(component):
    asset=component.get_editor_property('skeletal_mesh_asset')
    return {'component':path(component),'skeletal_mesh':path(asset),
        'slots':[{'slot':i,'current':path(component.get_material(i)),'parent_chain':chain(component.get_material(i))}
                 for i in range(component.get_num_materials())],
        'asset_slots':[{'slot':i,'name':str(s.material_slot_name),'material':path(s.material_interface),
                        'parent_chain':chain(s.material_interface)}
                       for i,s in enumerate(asset.get_editor_property('materials'))] if asset else []}

def fields(state):
    effect=state.get_editor_property('Effect')
    data={'bone':str(state.get_editor_property('BoneName')),'vector_parameter':str(state.get_editor_property('VectorParameterName')),
        'scalar_curve':str(state.get_editor_property('ScalarCurveName')),'scalar_parameter':str(state.get_editor_property('ScalarParameterName')),
        'overrides':[{'source':path(r.source_material),'replacement':path(r.replacement_material),
                      'source_chain':chain(r.source_material),'replacement_chain':chain(r.replacement_material)}
                     for r in state.get_editor_property('MaterialOverrides')]}
    if effect:
        data['effect']={'event_id':str(effect.get_editor_property('EventId')),
            'particle':path(effect.get_editor_property('ParticleTemplate')),'decal':path(effect.get_editor_property('DecalMaterial')),
            'winter_only':effect.get_editor_property('bWinterOnly'),'floor':effect.get_editor_property('bSpawnOnFloor'),
            'conditional_hit':effect.get_editor_property('bOnAttackSuccessed'),'socket':str(effect.get_editor_property('SourceSocket')),
            # Custom PhysicalSurface entries cannot be pythonized as the engine enum.
            # Keep UE's reflected source text instead of guessing an enum member.
            'surface_routes':[{'route_export_text':r.export_text(),'particle':path(r.particle_template),'decal':path(r.decal_material),
                              'suppress_particle':r.get_editor_property('bSuppressParticle'),
                              'suppress_decal':r.get_editor_property('bSuppressDecal')}
                             for r in effect.get_editor_property('SurfaceRoutes')]}
    return data

result={'schema':'Khazan.MonsterVisual.SavedConsumerProbe.v1','pid':os.getpid(),'work':str(WORK),
        'asset_saves':0,'asset_mutations':0,'errors':[],'sequences':[]}
try:
    bp='/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite.BP_Monster_ApesStoneHandElite_C'
    cdo=unreal.get_default_object(unreal.load_class(None,bp))
    components=list(cdo.get_components_by_class(unreal.SkeletalMeshComponent))
    primary=cdo.get_editor_property('Mesh')
    if primary and primary not in components:components.insert(0,primary)
    result['cdo_meshes']=[mesh(c) for c in components]
    definition=unreal.load_asset('/Game/Monsters/ApesStoneHandElite/Data/DA_Character_ApesStoneHandElite')
    settings=definition.get_editor_property('MonsterStamina')
    result['victim_montages']=[]
    for name in ('BrutalFrontVictimMontage','BrutalBackVictimMontage'):
        montage=settings.get_editor_property(name)
        result['victim_montages'].append({'field':name,'path':path(montage),
            'slot_segments':[{'slot':str(slot.slot_name),'segments':[{'animation':path(s.anim_reference),
                'start':s.start_pos,'source_start':s.anim_start_time,'source_end':s.anim_end_time,'rate':s.anim_play_rate}
                for s in slot.anim_track.anim_segments]} for slot in montage.get_editor_property('SlotAnimTracks')]})
    assets=[
        '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Death/Death_Die_F',
        '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage/Damage_FinalBlow',
        '/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations/Locomotion/Locomotion_Stand_F_Composite',
        '/Game/_Art/Enemies/HeinMach/Humanoids/Swordsman/Animations/Locomotion/Locomotion_LockOnWalk_B_Composite']
    for name in ('Damage_Grapple_Atk_01','Damage_Grapple_Atk_02','Damage_Grapple_Atk_B_01','Damage_Grapple_Atk_B_02'):
        assets.append('/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage/'+name)
        assets.append('/Game/Monsters/ApesStoneHandElite/Animations/InGame/Damage/'+name)
    state_type=unreal.load_class(None,'/Script/Khazan.KZAnimNotifyState_MonsterVisual')
    for asset_path in assets:
        asset=unreal.load_asset(asset_path);rows=[]
        for event in unreal.AnimationLibrary.get_animation_notify_events(asset):
            state=event.notify_state_class
            if state and state.get_class()==state_type and not state.get_editor_property('bAnimationContextBoundary'):
                rows.append({'state':path(state),'duration':unreal.AnimationLibrary.get_anim_notify_event_duration(event),
                             'fields':fields(state)})
        result['sequences'].append({'asset':asset_path,'states':rows})
    result['status']='pass'
except Exception:
    result['status']='failed';result['errors'].append(traceback.format_exc())
finally:
    p=OUT/'SavedConsumerIdentities.json'
    p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    unreal.log('MonsterVFXConsumerProbe '+result['status']+' '+str(p))
    if result['status']!='pass':raise RuntimeError(result['errors'][-1])
