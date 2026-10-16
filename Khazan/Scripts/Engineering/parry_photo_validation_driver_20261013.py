"""Actual native approved parry / camera / received-hit regression; no extra PIE request."""
from pathlib import Path
import json, os, unreal
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
# Compile the actual MI permutations before a sub-second success burst. A cold
# shader is not evidence that the particle's opacity is zero. Save no packages.
warm=[]
for path in unreal.EditorAssetLibrary.list_assets(BASE, recursive=False):
    asset=unreal.load_asset(path)
    if isinstance(asset, unreal.MaterialInterface):
        if isinstance(asset, unreal.Material):
            errors=list(unreal.MaterialEditingLibrary.recompile_material(asset))
            if errors:
                (OUT/'Driver.json').write_text(json.dumps(dict(status='failed',shader=path,errors=errors,saved_packages=0),indent=2),encoding='utf-8')
                unreal.SystemLibrary.quit_editor()
                raise RuntimeError((path,errors))
        stats=unreal.MaterialEditingLibrary.get_statistics(asset)
        warm.append(dict(path=path,pixel_instructions=stats.num_pixel_shader_instructions))
        assert stats.num_pixel_shader_instructions>0,path
    if isinstance(asset,unreal.Material) and asset.get_name()=='M_FM_fluid_A':
        t=unreal.AssetExportTask();t.object=asset;t.filename=str(OUT/'Fluid.t3d');t.exporter=unreal.ObjectExporterT3D();t.automated=True;t.prompt=False
        assert unreal.Exporter.run_asset_export_task(t)
(OUT/'ShaderWarmup.json').write_text(json.dumps(warm,indent=2),encoding='utf-8')
driver=ROOT/'Scripts/Engineering/monster_physics_validation_driver_20261013.py'
source=driver.read_text(encoding='utf-8')
source=source.replace("os.environ['KZ_MONSTER_PHYSICS_OUT']", "os.environ['KZ_PARRY_PHOTO_OUT']")
source=source.replace("os.environ['KZ_MONSTER_PHYSICS_TESTS'].split(',')", "['Khazan.Parry.PIE']")
source=source.replace("assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')", """# QA-only VRAM budget for this owned process; preserve bloom/material quality.
unreal.SystemLibrary.execute_console_command(None,'r.LumenScene.SurfaceCache.AtlasSize 2048')
unreal.SystemLibrary.execute_console_command(None,'r.Shadow.Virtual.MaxPhysicalPages 2048')
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')""")
if os.environ.get('KZ_PARRY_HEINMACH') == '1':
    source=source.replace(
        "assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/DevMap')",
        """# HeinMach needs its recorded 8192 atlas for an uncontaminated look review.
unreal.SystemLibrary.execute_console_command(None,'r.LumenScene.SurfaceCache.AtlasSize 8192')
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/Maps/L_HeinMach_Environment')
# Unsaved source-class seed if the environment map has no Swordsman to clone.
swordsman=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Bluprints/Monsters/BP_Monster_Swordsman')
assert swordsman
assert unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(swordsman,unreal.Vector(0,0,5000))""")
source=source.replace("if test.endswith('.PIE') or test.endswith('KnockbackPIE'):unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()", "# FWait owns the play request.")
# Capture is owned by the native test; direct output stays in this task's folder.
os.environ['KZ_PARRY_OUT']=os.environ['KZ_PARRY_PHOTO_OUT']
exec(compile(source,str(driver),'exec'),{'__file__':str(driver),'__name__':'__main__'})
