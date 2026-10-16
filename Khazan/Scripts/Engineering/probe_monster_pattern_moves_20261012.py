"""Read only the serialized movement paths actually consumed by the two giant abilities."""
from pathlib import Path
import unreal,os,json
out=Path(os.environ['KZ_MONSTER_CONTACT_OUT']);rows=[]
for family in ['ApesStoneHandElite','Yetuga']:
    d=unreal.load_asset('/Game/Monsters/'+family+'/Data/DA_OriginalPatterns_'+family)
    for n in d.get_editor_property('Nodes'):
        for move in n.get_editor_property('PatternMoves'):
            curve=move.get_editor_property('OffsetCurve')
            samples=[curve.get_vector_value(t/20) for t in range(21)] if curve else []
            dest=move.get_editor_property('Destination')
            rows.append({'family':family,'node':str(n.get_editor_property('NodeId')),'window':str(move.get_editor_property('Window')),'destination':[dest.x,dest.y,dest.z],'offset_curve':curve.get_path_name() if curve else None,'max_abs_z':max([abs(v.z) for v in samples]+[0]),'source':str(move.get_editor_property('Source'))})
(out/'Moves.json').write_text(json.dumps({'status':'passed','asset_saves':0,'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
print('PATTERN_MOVES',len(rows),[(r['family'],r['node'],r['destination'][2],r['max_abs_z']) for r in rows if r['destination'][2]!=0 or r['max_abs_z']>0.0001])
