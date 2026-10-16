import runpy, sys
script = 'C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Engineering/smooth_monster_combat_blendspaces_20261008.py'
previous = sys.argv
try:
    sys.argv = [script, 'workapply', 'C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan']
    runpy.run_path(script, run_name='__main__')
finally:
    sys.argv = previous
