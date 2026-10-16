"""Own separate hidden processes; existing engine runner and cleanup are reused."""
from pathlib import Path
import sys
main=Path(__file__).resolve().parents[2]
s=(main/'Scripts/Engineering/monster_physics_task_20261013.py').read_text(encoding='utf-8')
s=s.replace("WORK = MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'","WORK = MAIN.parent.parent/'Khazan_PlayerSlashWork_20261013/Khazan'")
s=s.replace("OUT = MAIN/'Metadata/MonsterSecondaryPhysics_20261013'","OUT = MAIN/'Metadata/PlayerSlashAlignment_20261013'")
exec(compile(s,__file__,'exec'),{'__file__':__file__,'__name__':'__main__'})
