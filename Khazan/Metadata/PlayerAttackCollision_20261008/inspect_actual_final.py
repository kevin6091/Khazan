import json
print('ACTUAL_QA_STATE',json.dumps({k:v for k,v in ACTUAL_QA['s'].items() if k not in ('world','player','target','input','action','anim','attrs')},default=str))
if ACTUAL_QA['s'].get('player'):
 p=ACTUAL_QA['s']['player'];print('ANIM_SAME',p.get_editor_property('mesh').get_anim_instance()==ACTUAL_QA['s']['anim'],'ACTION',ACTUAL_QA['s']['action'],'INPUT',ACTUAL_QA['s']['input'])
