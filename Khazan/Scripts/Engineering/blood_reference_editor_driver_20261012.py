"""Reuse the existing native proof driver with an explicit owned review map."""
from pathlib import Path
import os
root=Path(__file__).resolve().parents[2]
source=(root/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py').read_text(encoding='utf-8')
source=source.replace("load_level('/Game/Maps/DevMap')","load_level("+repr(os.environ.get('KZ_BLOOD_REFERENCE_MAP','/Game/Maps/DevMap'))+")")
if os.environ.get('KZ_BLOOD_REFERENCE_DEBUG_DELAY'):
    source=source.replace('if elapsed<8:return','if elapsed<'+str(float(os.environ['KZ_BLOOD_REFERENCE_DEBUG_DELAY']))+':return')
if os.environ.get('KZ_BLOOD_REFERENCE_SMALL_SHADOW_POOL')=='1':
    source=source.replace("unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')","unreal.SystemLibrary.execute_console_command(None,'r.Shadow.Virtual.MaxPhysicalPages 256');unreal.SystemLibrary.execute_console_command(None,'t.MaxFPS 60')")
exec(compile(source,'existing_monster_presentation_native_driver','exec'))
