"""Compare lighting in transient PIE only. Original photos guide TEMP candidates."""
from pathlib import Path
import os
import unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN'])
os.environ.update(KZ_LOOK_OUT=os.environ['KZ_LOOKSPIN_OUT'],KZ_LOOK_MAIN=str(main),
                  KZ_LOOK_LEVEL='HeinMach',KZ_LOOK_MODE='capture')
source=(main/'Scripts/Art/scene_look_capture_20261012.py').read_text(encoding='utf-8')
old="unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename=\"'+str(target)+'\" -nosuffix')"
new="unreal.SystemLibrary.execute_console_command(WORLD,'KZ.QA.ColourShot \"'+str(target)+'\"')"
assert source.count(old)==1
source=source.replace(old,new)
exec(compile(source,__file__,'exec'),globals())
# All values here are TEMP look development, not original engine metadata.
POLICIES=[
 dict(name='Before',sun_lux=1800.,sky_intensity=8.,bias_ev=-1.1,sun_rgb=[205,225,255],sky_rgb=[195,218,255],fog_emissive=[.025,.04,.06]),
 dict(name='BlueA',sun_lux=1200.,sky_intensity=10.,bias_ev=-1.85,sun_rgb=[166,199,255],sky_rgb=[118,166,255],fog_emissive=[.012,.027,.055]),
 dict(name='BlueB',sun_lux=1000.,sky_intensity=10.,bias_ev=-2.15,sun_rgb=[150,186,255],sky_rgb=[108,157,255],fog_emissive=[.010,.024,.050]),
 dict(name='BlueC',sun_lux=800.,sky_intensity=12.,bias_ev=-1.85,sun_rgb=[166,199,255],sky_rgb=[128,176,255],fog_emissive=[.012,.027,.055]),
]
CAMERAS=[('ReferenceStart',[10494.534774,-6517.085901,-5174.297077],[-.266921,177.083725,0]),
         ('Entry',[12370.713034,12849.819799,312.732826],[0,-114.986206,0])]
VIEWS=[(p['name']+'_'+name,pos,rot) for p in POLICIES for name,pos,rot in CAMERAS]
report['lighting_trials_TEMP']=POLICIES
report['policy_scope']='Transient PIE only; asset saves zero. Same actual native viewport, camera, quality and settling.'
BASE_CONFIGURE=configure
def configure():
    p=POLICIES[INDEX//len(CAMERAS)]
    for actor in u.GameplayStatics.get_all_actors_of_class(WORLD,u.DirectionalLight):
        c=actor.get_component_by_class(u.DirectionalLightComponent)
        c.set_editor_property('intensity',p['sun_lux'])
        r,g,b=p['sun_rgb'];c.set_editor_property('light_color',u.Color(r=r,g=g,b=b,a=255))
    for actor in u.GameplayStatics.get_all_actors_of_class(WORLD,u.SkyLight):
        c=actor.get_component_by_class(u.SkyLightComponent)
        c.set_editor_property('intensity',p['sky_intensity'])
        r,g,b=p['sky_rgb'];c.set_editor_property('light_color',u.Color(r=r,g=g,b=b,a=255))
    for actor in u.GameplayStatics.get_all_actors_of_class(WORLD,u.PostProcessVolume):
        if actor.get_actor_label().startswith('Art_NaturalLighting_'):
            settings=actor.get_editor_property('settings')
            settings.set_editor_property('auto_exposure_bias',p['bias_ev'])
            actor.set_editor_property('settings',settings)
    for actor in u.GameplayStatics.get_all_actors_of_class(WORLD,u.ExponentialHeightFog):
        c=actor.get_component_by_class(u.ExponentialHeightFogComponent)
        r,g,b=p['fog_emissive'];c.set_editor_property('volumetric_fog_emissive',u.LinearColor(r=r,g=g,b=b,a=1))
    BASE_CONFIGURE()
