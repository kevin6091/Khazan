import json
from pathlib import Path
r=Path(__file__).resolve().parent
w=Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan/Saved')
a=json.loads((r/'BaselineIronPhysicsAudit.json').read_text(encoding='utf-8-sig'))
b=json.loads((w/'IronPhysicsAudit.json').read_text(encoding='utf-8-sig'))
def diff(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()|b.keys():
            if k not in a or k not in b: print(path+'/'+k,'added/removed')
            else: diff(a[k],b[k],path+'/'+k)
    elif a!=b: print(path,repr(a),repr(b))
for row in a['bodies']:
    other=next(x for x in b['bodies'] if x['asset']==row['asset'] and x['bone']==row['bone'])
    for field in ('geometry_bone_local_cm','body_settings','current_joint_profile','default_joint_profile'):
        diff(row[field],other[field],row['bone']+'/'+field)
