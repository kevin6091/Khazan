"""Private disposable single-emitter fixtures; no production assets changed."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);fx=u.FXConverterUtilitiesLibrary
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
path=next(v for k,v in author['particles'].items() if 'Slashdust_HalfCircle_Left_01' in k)
source=u.load_asset(path);folder='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Diagnostics'
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
cases=[];report=[]
for index in range(len(fx.get_cascade_system_emitters(source))):
    dest=folder+'/DustEmitter'+str(index)
    assert not u.EditorAssetLibrary.does_asset_exist(dest)
    p=u.EditorAssetLibrary.duplicate_asset(path,dest)
    # PreSave normally restores the editor's transient solo snapshot. Clear it
    # for this disposable fixture so the deliberate enabled mask is persisted.
    u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+p.get_path_name()+'" SoloTracking ()')
    materials=[]
    for ei,e in enumerate(fx.get_cascade_system_emitters(p)):
        for li in range(len(p.get_editor_property('lod_distances'))):
            lod=fx.get_cascade_emitter_lod_level(e,li)
            u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+lod.get_path_name()+'" bEnabled '+('True' if ei==index else 'False'))
            if ei==index:
                m=fx.get_lod_level_required_module(lod).get_editor_property('material');materials.append(m.get_path_name() if m else None)
    assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
    cases.append(['DustEmitter'+str(index),'Yetuga','particle',p.get_path_name()])
    report.append({'index':index,'path':p.get_path_name(),'materials':materials})
(out/'RenderIsolation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(main/'Metadata/GiantVFX_20261013/RendererIsolationCases.tsv').write_text('\n'.join('\t'.join(c) for c in cases),encoding='utf-8')
