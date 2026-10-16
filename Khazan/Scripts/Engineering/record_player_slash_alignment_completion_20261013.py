from pathlib import Path
import json,datetime
r=Path(__file__).resolve().parents[2];out=r/'Metadata/PlayerSlashAlignment_20261013'
j=json.loads((out/'FinalVerification.json').read_text(encoding='utf-8'));assert j['status']=='complete_requested_slash_scope'
d=json.loads((out/'FinalDomainNotes.json').read_text(encoding='utf-8'));stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
marker='<!-- PlayerSlashAlignment_20261013_complete -->'
written=[]
for rel,body in d.items():
 p=r/rel;current=p.read_text(encoding='utf-8')
 if marker in current:
  assert "\uc644\ub8cc" in current[current.rfind(marker)-8000:]
  written.append(rel);continue
 with p.open('a',encoding='utf-8') as f:f.write('\n\n'+body.replace('[[STAMP]]',stamp)+'\n'+marker+'\n')
 # Verify actual Korean Unicode survived UTF-8, not the earlier native ASCII pipe.
 actual=p.read_text(encoding='utf-8');tail=actual[actual.rfind('\n\n## '):]
 assert marker in tail and '\uc644\ub8cc' in tail,rel
 written.append(rel)
(out/'FinalDomainNotesApplied.json').write_text(json.dumps({'status':'passed','date':stamp,'files':written,'utf8_korean_verified':True},indent=2),encoding='utf-8')
print('DOMAIN_NOTES_APPENDED_UTF8',len(written))