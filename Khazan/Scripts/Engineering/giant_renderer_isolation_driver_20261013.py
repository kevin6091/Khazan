from pathlib import Path
import os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
out=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
(out/'GiantReviewCases.tsv').write_bytes((main/'Metadata/GiantVFX_20261013'/os.environ.get('KZ_GIANT_REVIEW_CASES','RendererIsolationCases.tsv')).read_bytes())
if os.environ.get('KZ_GIANT_HIDE_SHOCK_RENDERERS')=='1':
    # Controlled in-memory isolation before the native fixture spawns particles.
    # No asset save: this process must not become a delivered game change.
    import json, unreal
    fx=unreal.FXConverterUtilitiesLibrary
    author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
    hidden=unreal.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/M_KZGiant_TechnicalHidden')
    if not hidden:
        hidden=unreal.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/M_TechnicalHidden')
    assert hidden
    changed=[]
    for path in set(author['particles'].values()):
        p=unreal.load_asset(path)
        for e in fx.get_cascade_system_emitters(p):
            for li in range(len(p.get_editor_property('lod_distances'))):
                req=fx.get_lod_level_required_module(fx.get_cascade_emitter_lod_level(e,li))
                mat=req.get_editor_property('material')
                if mat and mat.get_name().startswith('KZ_FMI_MashRefractionShock_01_DepthFade_'):
                    changed.append(dict(required=req.get_path_name(),before=mat.get_path_name()))
                    req.set_editor_property('material',hidden)
    assert changed
    (out/'ShockRendererIsolation.json').write_text(json.dumps({'renderers':changed,'asset_saves':0},indent=2),encoding='utf-8')
source=(main/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace("Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]", "Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan_GiantVFXWork_20261013/Khazan')]")
if os.environ.get('KZ_GIANT_DEBUG_HOLD') == '1':
    # One owned diagnostic process only; no gameplay or saved map changes.
    source=source.replace('if elapsed<8:return', 'if elapsed<45:return')
old="buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"
new="""report['manifest_snapshot_module']=str(module)
candidates=[p for p in (ROOT/'Binaries/Win64').glob('UnrealEditor-Khazan*.dll') if kernel.GetModuleHandleW(p.name)]
assert len(candidates)==1, candidates
module=candidates[0]
report['manifest_module']=str(module)
report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
report['module_binding']='Actual loaded process module; manifest snapshot may change during other builds'
buffer=ctypes.create_unicode_buffer(32768);loaded=kernel.GetModuleHandleW(module.name)"""
assert source.count(old)==1
source=source.replace(old,new,1)
if os.environ.get('KZ_GIANT_SPARSE_FIXTURE')=='1':
    source=source.replace('START=time.monotonic();started=', "actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)\nfor actor in actors.get_all_level_actors():\n    if isinstance(actor,unreal.KZMonster):actors.destroy_actor(actor)\nreport['fixture']='Unsaved owned world; native test spawns saved giant BP; no map/asset save'\nSTART=time.monotonic();started=")
exec(compile(source,__file__,'exec'),globals())
if os.environ.get('KZ_GIANT_HIDE_SYSTEM') or os.environ.get('KZ_GIANT_HIDE_DECALS')=='1':
    # Controlled visual diagnosis in this unsaved process; preserve the asset.
    selected=os.environ.get('KZ_GIANT_HIDE_SYSTEM','')
    decal_mode=os.environ.get('KZ_GIANT_HIDE_DECALS')=='1'
    hidden=set()
    details={}
    def hide_selected(delta):
        for world in unreal.EditorLevelLibrary.get_pie_worlds(False):
            for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor):
                for component in actor.get_components_by_class(unreal.DecalComponent if decal_mode else unreal.ParticleSystemComponent):
                    template=component.get_editor_property('decal_material' if decal_mode else 'template')
                    if template and (decal_mode or selected=='*' or template.get_name()==selected):
                        component.set_visibility(False,True)
                        hidden.add(component.get_path_name())
                        details[component.get_path_name()]={'material_or_template':template.get_path_name(),'location':str(component.get_world_location()),'size':str(component.get_editor_property('decal_size')) if decal_mode else ''}
        if hidden:
            (out/'RendererHideDiagnostic.json').write_text(json.dumps({'selected':selected,'decals':decal_mode,'hidden':sorted(hidden),'details':details,'saved_assets':0}),encoding='utf-8')
    diagnostic_handle=unreal.register_slate_post_tick_callback(hide_selected)
