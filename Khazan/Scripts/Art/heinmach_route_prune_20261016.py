"""Map-local inventory and pruning. Shared Content resources are never deleted."""
from pathlib import Path
import array, collections, hashlib, json, math, os, re, time, traceback
import unreal as u

MAIN=Path(os.environ['KZ_PRUNE_MAIN'])
OUT=Path(os.environ['KZ_PRUNE_OUT'])
TASK=MAIN/'Metadata/HeinMachRoutePrune_20261016'
MODE=os.environ['KZ_PRUNE_MODE']
MAP='/Game/Maps/L_HeinMach_Environment'
world=u.EditorLoadingAndSavingUtils.load_map(MAP)
assert world
actorsys=u.get_editor_subsystem(u.EditorActorSubsystem)
actors=list(actorsys.get_all_level_actors())

def write(name,data):
    (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def vec(v):return [v.x,v.y,v.z]
def path(o):return o.get_path_name() if o else None
def prop(o,k,default=None):
    try:return o.get_editor_property(k)
    except Exception:return default

def inventory():
    rows=[]
    for a in actors:
        center,extent=a.get_actor_bounds(False,True)
        row=dict(name=a.get_name(),label=a.get_actor_label(),cls=path(a.get_class()),
            folder=str(a.get_folder_path()),pose=a.get_actor_transform().export_text(),
            location=vec(a.get_actor_location()),bounds=[vec(center),vec(extent)],
            hidden=prop(a,'hidden',False),tags=[str(t) for t in prop(a,'tags',[])],
            parent=path(a.get_attach_parent_actor()),actor_collision_enabled=a.get_actor_enable_collision(),components=[])
        for c in a.get_components_by_class(u.SceneComponent):
            item=dict(name=c.get_name(),cls=path(c.get_class()),location=vec(c.get_world_location()),
                      visible=prop(c,'visible'),hidden=prop(c,'hidden_in_game'))
            if isinstance(c,u.PrimitiveComponent):
                bc,be,br=u.SystemLibrary.get_component_bounds(c)
                item.update(bounds=[vec(bc),vec(be)],collision=str(c.get_collision_enabled()),
                    cast_shadow=prop(c,'cast_shadow'),render_main=prop(c,'render_in_main_pass'))
                body=prop(c,'body_instance')
                item['authored_collision']={key:str(prop(body,key)) for key in ['collision_enabled','collision_profile_name']}
            if isinstance(c,u.StaticMeshComponent):
                item.update(mesh=path(c.static_mesh),materials=[path(c.get_material(i)) for i in range(c.get_num_materials())])
            if isinstance(c,u.InstancedStaticMeshComponent):
                item['instances']=[c.get_instance_transform(i,True).export_text() for i in range(c.get_instance_count())]
                if c.static_mesh:
                    low,high=c.static_mesh.get_bounding_box().min,c.static_mesh.get_bounding_box().max
                    item['mesh_local_bounds']=[vec(low),vec(high)]
            if isinstance(c,u.LightComponentBase):
                item['light']={k:str(prop(c,k)) for k in ['intensity','light_color','attenuation_radius',
                    'indirect_lighting_intensity','volumetric_scattering_intensity','cast_shadows','mobility']}
            if isinstance(c,u.CameraComponent):item['fov']=c.field_of_view
            if isinstance(c,u.PostProcessComponent):item['settings']=str(prop(c,'settings'))
            row['components'].append(item)
        if isinstance(a,u.PostProcessVolume):row['postprocess']=a.get_editor_property('settings').export_text()
        rows.append(row)
    write('Inventory.json',dict(map=MAP,actor_count=len(rows),actors=rows,asset_saves=0,
        classes=dict(collections.Counter(r['cls'] for r in rows))))
    u.log('KZ_PRUNE_INVENTORY_SUCCESS '+str(len(rows)))

def probe():
    """Record actual opaque/masked scene depth; do not infer visibility from distance."""
    plan=json.loads((TASK/'Plan.json').read_text(encoding='utf-8'))
    ignore=[a for a in actors if a.get_actor_label().startswith('BP_Monster')]
    capture=actorsys.spawn_actor_from_class(u.SceneCapture2D,u.Vector(),u.Rotator(),True)
    sc=capture.get_component_by_class(u.SceneCaptureComponent2D)
    resolution=256
    rt=u.RenderingLibrary.create_render_target2d(world,resolution,resolution,u.TextureRenderTargetFormat.RTF_RGBA32F)
    sc.texture_target=rt;sc.capture_source=u.SceneCaptureSource.SCS_SCENE_DEPTH
    sc.fov_angle=90;sc.capture_every_frame=False;sc.capture_on_movement=False
    sc.set_editor_property('always_persist_rendering_state',True)
    sc.set_editor_property('LODDistanceFactor',1)
    for a in ignore+[a for a in actors if prop(a,'hidden',False) or prop(a,'is_editor_only_actor',False)]:
        sc.hide_actor_components(a)
    for a in actors:
        for c in a.get_components_by_class(u.PrimitiveComponent):
            if prop(c,'hidden_in_game',False):sc.hide_component(c)
    u.SystemLibrary.execute_console_command(world,'t.MaxFPS 30')
    state=dict(start=time.monotonic(),phase='warm',next=time.monotonic()+15,index=0,views=[],anchors=[])
    rotations=[(0,0),(0,90),(0,180),(0,-90),(90,0),(-90,0)]
    def finish(error=None):
        state['success']=error is None;state['error']=error;state['asset_saves']=0
        state['resolution']=resolution
        write('DepthViews.json',state)
        if error:u.log_error(error)
        u.unregister_slate_post_tick_callback(handle[0])
        actorsys.destroy_actor(capture)
        u.SystemLibrary.quit_editor()
    def tick(delta):
        try:
            now=time.monotonic()
            if now-state['start']>1200:finish('Depth probe timeout');return
            if now<state['next']:return
            if state['phase']=='warm':
                audio=[]
                for a in actors:
                    for c in a.get_components_by_class(u.AudioComponent):
                        sound=prop(c,'sound')
                        attenuation=prop(c,'attenuation_settings') or (prop(sound,'attenuation_settings') if sound else None)
                        settings=prop(c,'attenuation_overrides') if prop(c,'override_attenuation',False) else (prop(attenuation,'attenuation') if attenuation else None)
                        if settings is None and sound and prop(sound,'override_attenuation',False):settings=prop(sound,'attenuation_overrides')
                        audio.append(dict(actor=a.get_name(),label=a.get_actor_label(),sound=path(sound),
                            attenuation=path(attenuation),settings=settings.export_text() if settings else None,
                            cached_max_distance=prop(sound,'max_distance') if sound else None))
                write('AudioInfluence.json',audio)
                for anchor in plan['camera_anchors']:
                    p=u.Vector(*anchor['position'])
                    # Authored gameplay coordinates are already below the cave ceiling.
                    # A high downward ray can incorrectly choose the roof as the floor.
                    hit=u.SystemLibrary.line_trace_single_by_profile(world,p+u.Vector(0,0,50),p-u.Vector(0,0,2300),
                        'Pawn',True,ignore,u.DrawDebugTrace.NONE,True)
                    floor=None
                    if hit:
                        values=u.get_default_object(u.GameplayStatics).call_method('BreakHitResult',args=(hit,))
                        if values[0]:floor=vec(values[5])
                    # Survey above the actual floor; original authored coordinates remain untouched.
                    eye=[p.x,p.y,(floor[2] if floor else p.z)+300]
                    row=dict(anchor,eye=eye,floor=floor)
                    state['anchors'].append(row)
                    if anchor['kind']=='authored_gameplay':
                        for ox,oy in [(400,0),(-400,0),(0,400),(0,-400)]:
                            state['anchors'].append(dict(row,name=anchor['name']+'_orbit_'+str(ox)+'_'+str(oy),
                                eye=[eye[0]+ox,eye[1]+oy,eye[2]],kind='QA_camera_orbit_offset'))
                write('Cameras.json',state['anchors'])
                state['phase']='set'
            if state['phase']=='set':
                index=state['index'];anchor=state['anchors'][index//6]
                pitch,yaw=rotations[index%6];rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=0)
                capture.set_actor_location(u.Vector(*anchor['eye']),False,False)
                capture.set_actor_rotation(rotation,False)
                sc.capture_scene()
                state['current']=dict(index=index,anchor=anchor['name'],eye=anchor['eye'],rotation=[pitch,yaw,0],
                    forward=vec(u.MathLibrary.get_forward_vector(rotation)),right=vec(u.MathLibrary.get_right_vector(rotation)),
                    up=vec(u.MathLibrary.get_up_vector(rotation)))
                state['phase']='read';state['next']=now+.12;return
            if state['phase']=='read':
                samples=u.RenderingLibrary.read_render_target_raw(world,rt,False)
                assert samples is not None and len(samples)==resolution*resolution,(type(samples),len(samples) if samples else None)
                depths=array.array('f',(v.r for v in samples))
                filename='Depth_'+str(state['index']).zfill(4)+'.f32'
                with (OUT/filename).open('wb') as f:depths.tofile(f)
                row=state['current'];row.update(file=filename,minimum=min(depths),maximum=max(depths))
                state['views'].append(row);state['index']+=1
                if state['index']%12==0:
                    write('Progress.json',dict(views=state['index'],total=len(state['anchors'])*6,elapsed=now-state['start']))
                    u.log('KZ_PRUNE_DEPTH '+str(state['index']))
                if state['index']==len(state['anchors'])*6:finish();return
                state['phase']='set';state['next']=now
        except Exception:finish(traceback.format_exc())
    handle=[u.register_slate_post_tick_callback(tick)]

def apply_selected(target_actors, destroy):
    selected=json.loads((TASK/'Selection.json').read_text(encoding='utf-8'))
    byname={a.get_name():a for a in target_actors}
    grouped=collections.defaultdict(list);removed=[];empty=[];instance_count=0
    for e in selected['deleted']:
        assert e['actor'] in byname,e['actor']
        if e['kind']=='instance':grouped[(e['actor'],e['component'])].append(e['index'])
    for (name,component),indices in grouped.items():
        a=byname[name]
        c=next(c for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==component)
        before=c.get_instance_count()
        assert c.remove_instances(sorted(indices,reverse=True)),(name,component)
        assert c.get_instance_count()==before-len(indices)
        instance_count+=len(indices)
    for name in sorted({name for name,component in grouped}):
        a=byname[name];parts=a.get_components_by_class(u.InstancedStaticMeshComponent)
        if parts and all(c.get_instance_count()==0 for c in parts):
            destroy(a);empty.append(name)
    for e in selected['deleted']:
        if e['kind']=='actor':destroy(byname[e['actor']]);removed.append(e['actor'])
    return dict(removed_actors=removed,empty_instance_actors=empty,removed_instances=instance_count)

def protected_contract():
    result={}
    for a in actorsys.get_all_level_actors():
        if a.get_actor_label()=='HM_Yetuga_EntrancePortal':
            result['portal']={k:path(prop(a,k)) for k in ['exit_point','arena_music']}
            result['portal'].update({k:prop(a,k) for k in ['fade_out_seconds','black_hold_seconds','fade_in_seconds']})
            entry=prop(a,'entry_volume');effect=prop(a,'portal_effect')
            result['portal'].update(entry_extent=vec(entry.get_unscaled_box_extent()),
                entry_collision=str(entry.get_collision_enabled()),effect=path(prop(effect,'asset')),
                effect_relative=effect.get_relative_transform().export_text())
        if isinstance(a,u.ExponentialHeightFog):
            fog=a.get_component_by_class(u.ExponentialHeightFogComponent)
            result['fog']={k:str(prop(fog,k)) for k in ['fog_density','fog_height_falloff',
                'fog_inscattering_luminance','start_distance','fog_cutoff_distance','volumetric_fog',
                'volumetric_fog_emissive','volumetric_fog_albedo','volumetric_fog_extinction_scale',
                'volumetric_fog_distance','volumetric_fog_scattering_distribution']}
        if isinstance(a,u.RecastNavMesh):
            result['navigation']={k:str(prop(a,k)) for k in ['runtime_generation','agent_radius','agent_height','cell_size','cell_height']}
    return result

def scene_checks():
    cameras=json.loads((TASK/'Depth03/Cameras.json').read_text(encoding='utf-8'))
    current=list(actorsys.get_all_level_actors());ignore=[a for a in current if isinstance(a,u.Character)]
    floors=[];projections=[];projected={};authored={}
    for c in cameras:
        if c['kind']=='QA_camera_orbit_offset':continue
        p=u.Vector(*c['position'])
        hit=u.SystemLibrary.line_trace_single_by_profile(world,p+u.Vector(0,0,50),p-u.Vector(0,0,2300),
            'Pawn',True,ignore,u.DrawDebugTrace.NONE,True)
        values=u.get_default_object(u.GameplayStatics).call_method('BreakHitResult',args=(hit,)) if hit else None
        floor=vec(values[5]) if values and values[0] else None
        floors.append(dict(name=c['name'],label=c['label'],floor=floor))
        if c['kind']!='authored_gameplay':continue
        authored[c['name']]=c
        # QA query envelope only, reusing the existing playability checker units.
        value=u.NavigationSystemV1.project_point_to_navigation(world,p,None,None,u.Vector(500,500,1000))
        ok,location=(bool(value[0]),value[1]) if isinstance(value,tuple) else (value is not None,value)
        projections.append(dict(name=c['name'],projected=ok,location=vec(location) if ok else None))
        if ok:projected[c['name']]=location
    start=next(k for k,v in authored.items() if v['label']=='PlayerStart')
    arrival=next(k for k,v in authored.items() if v['label']=='HM_Yetuga_ArenaArrival')
    pairs=[(arrival if c['label']=='BP_Monster_Yetuga' else start,name) for name,c in authored.items()
        if name not in [start,arrival]]
    paths=[]
    for first,last in pairs:
        route=u.NavigationSystemV1.find_path_to_location_synchronously(world,projected[first],projected[last]) if first in projected and last in projected else None
        valid=bool(route and route.is_valid());partial=bool(route.is_partial()) if route else None
        paths.append(dict(start=first,end=last,valid=valid,partial=partial,
            length=route.get_path_length() if valid else None))
    return dict(floors=floors,projections=projections,paths=paths,contract=protected_contract())

def compare_scene(before,after):
    errors=[]
    old={x['name']:x for x in before['floors']}
    for x in after['floors']:
        b=old[x['name']]['floor'];a=x['floor']
        if b is not None and (a is None or math.dist(a,b)>.1):errors.append('Floor changed: '+x['name'])
    old={x['name']:x for x in before['projections']}
    for x in after['projections']:
        if old[x['name']]['projected'] and not x['projected']:errors.append('Nav projection lost: '+x['name'])
    old={(x['start'],x['end']):x for x in before['paths']}
    for x in after['paths']:
        b=old[(x['start'],x['end'])]
        if b['valid'] and not b['partial'] and (not x['valid'] or x['partial']):errors.append('Nav route lost: '+x['end'])
    # Python's struct repr embeds process-local addresses; only compare serialized values.
    normalized=lambda x:re.sub(r'0x[0-9a-fA-F]+','<memory>',json.dumps(x,sort_keys=True))
    if normalized(before['contract'])!=normalized(after['contract']):errors.append('Portal/fog/navigation settings changed')
    return errors

def author_or_verify():
    author=MODE=='author'
    project=Path(u.Paths.project_dir()).resolve();mapfile=project/'Content/Maps/L_HeinMach_Environment.umap'
    baseline=json.loads((TASK/'Baseline.json').read_text(encoding='utf-8'))
    def digest():
        with mapfile.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
    initial_sha=digest()
    if author:
        assert project==Path(baseline['work']).resolve(),'Authoring must target the isolated map'
        assert initial_sha==baseline['map_sha'],'Refuse to overwrite a changed work map'
        review=json.loads((TASK/'VisualReview.json').read_text(encoding='utf-8'))
        assert review['accepted'] and review['selection_sha']==hashlib.sha256((TASK/'Selection.json').read_bytes()).hexdigest()
    state=dict(start=time.monotonic(),phase='before' if author else 'verify',stable=0,
        next=time.monotonic()+15,asset_saves=0,before_sha=initial_sha,project=str(project))
    def finish(error=None):
        state['success']=error is None;state['error']=error;state['after_sha']=digest()
        write('Author.json' if author else 'SceneVerification.json',state)
        if error:u.log_error(error)
        u.unregister_slate_post_tick_callback(handle[0]);u.SystemLibrary.quit_editor()
    def tick(delta):
        try:
            now=time.monotonic()
            if now-state['start']>600:finish('Scene/nav timeout; no completion claimed');return
            if now<state['next']:return
            state['next']=now+.5
            state['stable']=0 if u.NavigationSystemV1.is_navigation_being_built_or_locked(world) else state['stable']+1
            if state['stable']<8:return
            checks=scene_checks()
            if state['phase']=='before':
                state['before']=checks;write('BeforeChecks.json',checks)
                state['applied']=apply_selected(actorsys.get_all_level_actors(),actorsys.destroy_actor)
                u.SystemLibrary.execute_console_command(world,'RebuildNavigation')
                state.update(phase='after',stable=0,next=now+15);return
            state['after']=checks
            reference=state['before'] if author else json.loads((TASK/'Author01/Author.json').read_text(encoding='utf-8'))['after']
            state['regressions']=compare_scene(reference,checks)
            assert not state['regressions'],state['regressions']
            if author:
                assert u.EditorLoadingAndSavingUtils.save_map(world,MAP)
                state['asset_saves']=1
            # Read actual remaining level state, never the pre-deletion cached array.
            global actors
            actors=list(actorsys.get_all_level_actors());inventory()
            finish()
        except Exception:finish(traceback.format_exc())
    handle=[u.register_slate_post_tick_callback(tick)]

def capture():
    """Before/after real game viewport in one disposable PIE session; asset saves zero."""
    cameras=json.loads((TASK/'Depth03/Cameras.json').read_text(encoding='utf-8'))
    views=[]
    for c in cameras:
        if c['kind']!='authored_gameplay':continue
        # Two talkers share the same small area; keep both in the depth survey.
        if any(v['label']==c['label'] for v in views):continue
        for yaw in [0,90,180,-90]:views.append(dict(label=c['label'],eye=c['eye'],rotation=[-5,yaw,0]))
    quality={f'sg.{key}Quality':3 for key in ['ViewDistance','AntiAliasing','Shadow','GlobalIllumination',
        'Reflection','PostProcess','Texture','Effects','Foliage','Shading','Landscape']}
    quality.update({'sg.ResolutionQuality':100,'r.ScreenPercentage':100,'t.MaxFPS':30})
    for key,value in quality.items():u.SystemLibrary.execute_console_command(world,key+' '+str(value))
    u.SystemLibrary.execute_console_command(world,'DisableAllScreenMessages')
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
    state=dict(start=time.monotonic(),phase='init',index=0,pass_name='Before',views=[],quality=quality,asset_saves=0)
    refs={}
    def finish(error=None):
        state['success']=error is None;state['error']=error
        write('Comparison.json',state)
        if error:u.log_error(error)
        u.unregister_slate_post_tick_callback(handle[0])
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
        u.SystemLibrary.quit_editor()
    def configure():
        v=views[state['index']];camera=refs['camera'];p,y,r=v['rotation']
        camera.set_world_location(u.Vector(*v['eye']),False,False)
        camera.set_world_rotation(u.Rotator(pitch=p,yaw=y,roll=r),False,False)
        state['frame']=0;state['settled']=time.monotonic();state['phase']='view'
    def tick(delta):
        try:
            now=time.monotonic()
            if now-state['start']>1200:finish('Viewport comparison timeout');return
            if state['phase']=='init':
                game=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
                if not game:return
                pc=u.GameplayStatics.get_player_controller(game,0);pawn=u.GameplayStatics.get_player_pawn(game,0)
                if not pc or not pawn:return
                refs.update(game=game,pc=pc,pawn=pawn)
                pc.set_ignore_look_input(True);pc.set_ignore_move_input(True);pc.disable_input(pc);pawn.disable_input(pc)
                camera=next(c for c in pawn.get_components_by_class(u.CameraComponent) if c.is_active())
                camera.detach_from_component(u.DetachmentRule.KEEP_WORLD,u.DetachmentRule.KEEP_WORLD,u.DetachmentRule.KEEP_WORLD)
                camera.set_editor_property('use_pawn_control_rotation',False);camera.set_field_of_view(90)
                refs['camera']=camera
                for a in u.GameplayStatics.get_all_actors_of_class(game,u.Character):
                    a.set_actor_hidden_in_game(True)
                    a.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
                    controller=a.get_controller()
                    if isinstance(controller,u.AIController):
                        controller.stop_movement()
                        brain=controller.get_component_by_class(u.BrainComponent)
                        if brain:brain.stop_logic('Level visibility QA')
                u.WidgetLayoutLibrary.remove_all_widgets(game)
                state['phase']='warm';state['warm_until']=now+12;return
            if state['phase']=='warm':
                if now<state['warm_until']:return
                # Freeze simulation almost completely while camera/render ticks continue.
                u.GameplayStatics.set_global_time_dilation(refs['game'],.0001)
                configure();return
            if state['phase']=='view':
                state['frame']+=1
                if state['frame']==50 and now-state['settled']<2:state['frame']-=1;return
                if state['frame']==50:
                    filename=state['pass_name']+'_'+str(state['index']).zfill(3)+'.png'
                    pcm=u.GameplayStatics.get_player_camera_manager(refs['game'],0)
                    state['views'].append(dict(views[state['index']],pass_name=state['pass_name'],file=filename,
                        actual_eye=vec(pcm.get_camera_location()),actual_rotation=pcm.get_camera_rotation().export_text()))
                    u.SystemLibrary.execute_console_command(refs['game'],'Shot filename="'+str(OUT/filename)+'" -nosuffix')
                if state['frame']<56:return
                state['index']+=1
                write('Progress.json',dict(pass_name=state['pass_name'],views=state['index'],total=len(views)))
                if state['index']<len(views):configure();return
                if state['pass_name']=='Before':
                    target=list(u.GameplayStatics.get_all_actors_of_class(refs['game'],u.Actor))
                    state['applied']=apply_selected(target,lambda a:a.destroy_actor())
                    state['pass_name']='After';state['index']=0;state['phase']='warm';state['warm_until']=now+12
                else:finish()
        except Exception:finish(traceback.format_exc())
    handle=[u.register_slate_post_tick_callback(tick)]

try:
    if MODE=='inventory':inventory()
    elif MODE=='probe':probe()
    elif MODE=='capture':capture()
    elif MODE in ['author','verify_scene']:author_or_verify()
    else:raise RuntimeError('Mode not yet implemented: '+MODE)
except Exception:
    write('Failure.json',dict(error=traceback.format_exc()))
    if MODE in ['probe','capture','author','verify_scene']:u.SystemLibrary.quit_editor()
    raise
