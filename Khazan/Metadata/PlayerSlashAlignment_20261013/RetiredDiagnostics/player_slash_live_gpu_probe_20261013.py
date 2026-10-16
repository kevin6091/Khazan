import re
_gpu_seen=set()
def inspect_gpu():
    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:return
    player=unreal.GameplayStatics.get_player_character(world,0)
    if not player:return
    for c in player.get_editor_property('mesh').get_children_components(True):
        if not isinstance(c,unreal.NiagaraComponent) or not c.is_active() or not c.is_visible():continue
        key=c.get_path_name()
        if key in _gpu_seen:continue
        if len(_gpu_seen)>=4:return
        _gpu_seen.add(key);rows={'component':key,'transform':{f:str(c.get_editor_property(f)) for f in ['relative_location','relative_rotation','relative_scale3d']},'curves':{}}
        for label in ['CurveRotation','CurveScale']:
            di=unreal.NiagaraFunctionLibrary.get_data_interface(unreal.NiagaraDataInterfaceCurve,c,'User.'+label)
            task=unreal.AssetExportTask();task.object=di;task.filename=str(OUT/('Live_%02d_%s.t3d'%(len(_gpu_seen),label)));task.automated=True;task.prompt=False;task.exporter=unreal.ObjectExporterT3D()
            rows['curves'][label]={'object':di.get_path_name() if di else None,'exported':bool(di and unreal.Exporter.run_asset_export_task(task))}
        params=unreal.NiagaraSimCacheCreateParameters()
        ok,cache=unreal.NiagaraSimCacheFunctionLibrary.capture_niagara_sim_cache_immediate(None,params,c,False)
        rows['capture_ok']=ok
        rows['emitters']={}
        if ok:
            for emitter in cache.get_emitter_names():
                rows['emitters'][str(emitter)]={'positions':list(map(str,cache.read_position_attribute('Position',emitter,False,0))),'orientations':list(map(str,cache.read_quat_attribute('MeshOrientation',emitter,False,0))),'scales':list(map(str,cache.read_vector_attribute('Scale',emitter,0)))}
        (OUT/('LiveGPU_%02d.json'%len(_gpu_seen))).write_text(json.dumps(rows,indent=2),encoding='utf-8')
