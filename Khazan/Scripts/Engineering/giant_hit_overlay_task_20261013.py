from pathlib import Path
main=Path(__file__).resolve().parents[2]
s=(main/'Scripts/Engineering/monster_physics_task_20261013.py').read_text(encoding='utf-8')
s=s.replace("WORK = MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'","WORK = MAIN.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan'")
s=s.replace("OUT = MAIN/'Metadata/MonsterSecondaryPhysics_20261013'","OUT = MAIN/'Metadata/GiantHitOverlay_20261013'")
s=s.replace("'KhazanEditor','Win64','Development',","'KhazanEditor','Win64','Development','-ModuleWithSuffix=Khazan,8865',")
s=s.replace("if kind=='asset_editor':cmd+=['-NullRHI']","if kind=='asset_editor':cmd+=['-NullRHI','-UseFixedTimeStep','-FPS=60']")
exec(compile(s,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})