"""Keep combat feedback colour out of native fog, preserving depth occlusion."""
from pathlib import Path
import hashlib,json,os
import unreal as u
main=Path(os.environ['KZ_HM_COLOUR_MAIN']);root=Path(u.Paths.project_dir()).resolve()
assert root==main.parent.parent/'Khazan_HeinColourVFXWork_20261015'/'Khazan'
out=Path(os.environ['KZ_HM_COLOUR_OUT'])
usage=json.loads((main/'Metadata/HeinMachColourVFX_20261015/BaselineAudit02/Usage.json').read_text(encoding='utf-8'))
rows=[]
for row in usage['roots']:
    path=row['material']
    if not path.startswith(('/Game/_Art/Effects/','/Game/VFX/')):continue
    if 'MD_SURFACE' not in row.get('material_domain','') or 'UNLIT' not in row.get('shading_model',''):continue
    if not row.get('emissive_node') or path.endswith('M_KZGiant_TechnicalHidden'):continue
    material=u.load_asset(path);assert material
    file=root/('Content/'+path.removeprefix('/Game/')+'.uasset')
    before=hashlib.sha256(file.read_bytes()).hexdigest()
    old=bool(material.get_editor_property('bUseTranslucencyVertexFog'))
    if old:
        material.set_editor_property('bUseTranslucencyVertexFog',False)
        errors=list(u.MaterialEditingLibrary.recompile_material(material));assert not errors,(path,errors)
        assert u.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
    rows.append({'asset':path,'changed':old,'before_sha256':before,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                 'depth_test_disabled':material.get_editor_property('disable_depth_test')})
(out/'FogIsolation.json').write_text(json.dumps({'status':'passed','asset_count':len(rows),'rows':rows},indent=2),encoding='utf-8')
print('COMBAT_FOG_ISOLATED',sum(row['changed'] for row in rows))
