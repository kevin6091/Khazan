from pathlib import Path
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
for cls in (unreal.TextureRenderTargetFormat,unreal.SceneCaptureSource,unreal.SceneCapturePrimitiveRenderMode,unreal.CollisionResponseType):
    print(cls.__name__,[n for n in dir(cls) if n.isupper()])
print('rt',[n for n in dir(unreal.RenderingLibrary) if 'render_target' in n])
