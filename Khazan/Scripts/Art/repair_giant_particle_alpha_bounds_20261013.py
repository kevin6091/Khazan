"""Bound particle A before its source density mask; retain HDR RGB outputs."""
from pathlib import Path
import json, os, re
import unreal as u

main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path(u.Paths.project_dir()).resolve();assert work==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary
author=json.loads((main/'Metadata/GiantVFX_20261013/AssetAuthor02/Author.json').read_text(encoding='utf-8'))
audit=json.loads((main/'Metadata/ParticleAlpha_20261013/Audit02/Audit.json').read_text(encoding='utf-8'))
records={r['path']:r for r in audit['materials']}
triage=json.loads((main/'Metadata/ParticleAlpha_20261013/MaterialTriage.json').read_text())['rows']
report={'changed':[],'links':[]}
for source,dest in author['materials'].items():
    mat=u.load_asset(dest)
    if not isinstance(mat,u.Material) or source not in records:continue
    nodes={n.get_name():n for n in lib.get_material_expressions(mat)}
    emissive=lib.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)
    reachable={n['name'] for row in triage if row['master']==source for n in row['alpha_nodes']}
    file=main/'Metadata/ParticleAlpha_20261013/Audit02'/records[source]['export']
    raw=file.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r','')
    count=0
    for parent,body in re.findall(r'Begin Object Name="([^"]+)"[^\n]*\n(.*?)End Object',text,re.S):
        if parent not in reachable or parent not in nodes:continue
        for line in body.splitlines():
            m=re.search(r'^\s*([^=]+)=.*?:([^:\'"/]+)\'[\"].*OutputIndex=4',line)
            if not m or m.group(2) not in nodes or not isinstance(nodes[m.group(2)],u.MaterialExpressionParticleColor):continue
            bounded=lib.create_material_expression(mat,u.MaterialExpressionSaturate)
            bounded.set_editor_property('Desc','Giant VFX: bound particle alpha before original mask; keep original HDR RGB')
            assert lib.connect_material_expressions(nodes[m.group(2)],'A',bounded,'')
            pin=m.group(1).strip()
            if isinstance(nodes[parent],u.MaterialExpressionSaturate):continue # Already bounded before its mask.
            if pin=='Input':pin=''
            if isinstance(nodes[parent],u.MaterialExpressionCustom) and pin.startswith('Inputs('):
                index=int(pin.split('(',1)[1].split(')',1)[0])
                pin=str(nodes[parent].get_editor_property('inputs')[index].get_editor_property('input_name'))
            assert lib.connect_material_expressions(bounded,'',nodes[parent],pin),(dest,parent,pin)
            report['links'].append({'material':dest,'parent':parent,'pin':pin,'particle_color':m.group(2)});count+=1
    if count:
        assert lib.get_material_property_input_node(mat,u.MaterialProperty.MP_EMISSIVE_COLOR)==emissive
        assert not list(lib.recompile_material(mat))
        assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
        report['changed'].append(dest)
(out/'AlphaBound.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('GIANT_ALPHA_BOUND: '+str(len(report['changed']))+' materials, '+str(len(report['links']))+' links')
