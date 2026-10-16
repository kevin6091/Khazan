"""Resume Layers01 after the non-exported Python module class lookup failure."""
from pathlib import Path
import unreal as u
path=Path(__file__).with_name('correct_parry_photo_layers_20261013.py')
s=path.read_text(encoding='utf-8')
prefix=s.split("for name in ['MI_FMI_fluid_A_11'")[0]
suffix='changes=[]'+s.split('changes=[]',1)[1]
exec(compile(prefix+"\nm=u.load_asset(BASE+'/M_Parry_Distortion');assert m\n"+suffix,str(path),'exec'),globals())
