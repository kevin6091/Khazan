from pathlib import Path
path=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Scripts/Art/heinmach_snow_deep.py')
namespace={'__name__':'snow_task','__file__':str(path)}
exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),namespace)
namespace['unlocked_variants']()
