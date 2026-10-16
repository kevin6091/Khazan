"""Reuse the owned-process runner for this isolated, selected VFX change."""
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[2]
source = (root/'Scripts/Engineering/parry_task_20261012.py').read_text(encoding='utf-8')
source = source.replace('Khazan_ParryWork_20261012/Khazan','Khazan_SlamDistortWork_20261012/Khazan')
source = source.replace("OUT = MAIN / 'Metadata/Parry_20261012'", "OUT = MAIN / 'Metadata/PlayerSlamDistort_20261012'")
start = source.index('WRITE_DIRS = '); end = source.index('\ndef sha', start)
source = source[:start]+"WRITE_DIRS = ['Content/_Art/Player/Animation/InGame/DAS/FallAttack']"+source[end:]
source = source.replace("if project==MAIN:cmd+=['-ModuleWithSuffix=Khazan,2026101290']", "cmd+=['-MaxParallelActions=1']\n        if project==MAIN:cmd+=['-ModuleWithSuffix=Khazan,2026101296']")
source = source.replace("'-NoUBA','-NoXGE'", "'-NoUBA','-NoXGE'")
source = source.replace("'-NoHotReloadFromIDE','-NoUBA'", "'-NoHotReloadFromIDE','-NoHotReload','-NoUBTMakefiles','-NoUBA'")
source = source.replace("if project==MAIN:cmd+=['-ModuleWithSuffix=Khazan,2026101296']", "if project==MAIN:cmd+=['-ModuleWithSuffix='+module+',2026101296' for module in ['Khazan','Cog','CogCommon','CogDebug','CogDebugEditor','CogEngine','CogImgui','UnrealPSKPSA','RiderLink','ModelContextProtocol']]")
source = source.replace("if project==MAIN:cmd+=['-ModuleWithSuffix='", "if project==MAIN:cmd.remove('-NoHotReload')\n        if project==MAIN:cmd+=['-ModuleWithSuffix='")
source = source.replace("folder in ['Source','Config','Binaries']", "folder in ['Source','Config','Binaries']")
source = source.replace("KZ_PARRY_MODE=kind)", "KZ_PARRY_MODE=kind,KZ_SLAM_DISTORT_ONLY='1')")
source = source.replace("if kind!='audio':cmd+=['-nosound']", "if kind!='audio':cmd+=['-nosound']\n        if kind=='rhi':cmd+=['-UseFixedTimeStep','-FPS=60']")
# The original runner's author-only inventory is inapplicable to this task.
start=source.index('def parry_assets');end=source.index('\ndef hidden',start)
source=source[:start]+"def parry_assets(root): return {}\n"+source[end:]
exec(compile(source,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})
