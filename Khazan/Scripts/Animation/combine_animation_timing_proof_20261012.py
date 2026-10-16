from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parents[2];O=P/'Metadata/AnimationTimingKnockback_20261012';W=P.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
def read(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
assert read('MergeAuthor01/Driver.json')['status']=='passed'
base=read('Author04/NativeAuthor.json');merge=read('MergeAuthor01/NativeAuthor.json');assert base['success'] and merge['success']
rows={r['asset']:r for r in base['sequences']};changes=[]
for r in merge['sequences']:
 old=rows[r['asset']];assert r['bone_key_hash_before']==old['bone_key_hash_before'],r['asset']
 changes.append({'asset':r['asset'],'previous_notify_count':len(old['notifies']),'current_notify_count':len(r['notifies']),'same_original_bone_keys':True})
 rows[r['asset']]=r
base['sequences']=[rows[r['asset']] for r in base['sequences']];base['merge_evidence']='MergeAuthor01/NativeAuthor.json; concurrent88 latest Main attack effects preserved'
dest=O/'AuthorFinal';dest.mkdir(exist_ok=True);(dest/'NativeAuthor.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files={}
for r in rows:
 rel='Content/'+r.removeprefix('/Game/')+'.uasset';files[rel]=hashlib.sha256((W/rel).read_bytes()).hexdigest()
(dest/'SelectedSequenceSHA.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf-8')
(O/'ConcurrentEffectsPreserved.json').write_text(json.dumps({'assets':changes,'count':len(changes),'original_bone_keys_unchanged':True},indent=2)+'\n',encoding='utf-8')
print('COMBINED_TIMING_PROOF',len(rows),'rebased',len(changes))
