import unreal, pathlib, json
result={}
for name in ['SkeletalMeshEditorSubsystem','SubobjectDataSubsystem','SubobjectDataBlueprintFunctionLibrary','BlueprintEditorLibrary','AnimationLibrary','AnimSequence','AnimDataController','Skeleton','SkeletalMeshComponent','EditorAssetLibrary']:
    cls=getattr(unreal,name,None)
    if cls:
        result[name]={n:getattr(cls,n).__doc__ for n in dir(cls) if any(k in n for k in ['skeleton','bone_track','create_animation','subobject','object_for_blueprint','attach_subobject','get_data','blueprint_from','leader_pose','get_num_bones','get_bone_names','ref_pose','preview_mesh','import_lod'])}
path=pathlib.Path(unreal.Paths.project_saved_dir())/'Extracted/HeinMachEnemies/UnrealImportAPI.json'
path.write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ENEMY_API_PROBE_SAVED')
