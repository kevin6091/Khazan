from pathlib import Path
import hashlib
import json
import urllib.request

root=Path(__file__).resolve().parents[2]
out=root/'Saved/ImportReports/GameplayAudio_20261011/Tools'
out.mkdir(parents=True,exist_ok=True)
url='https://api.github.com/repos/bnnm/wwiser/releases/latest'
request=urllib.request.Request(url,headers={'User-Agent':'Khazan-local-audio-audit'})
release=json.loads(urllib.request.urlopen(request,timeout=30).read())
asset=next(a for a in release['assets'] if a['name']=='wwiser.pyz')
target=out/asset['name']
if not target.exists():
    data=urllib.request.urlopen(urllib.request.Request(asset['browser_download_url'],headers={'User-Agent':'Khazan-local-audio-audit'}),timeout=30).read()
    target.write_bytes(data)
report={'repository':'bnnm/wwiser','release':release['tag_name'],'release_url':release['html_url'],
        'asset_url':asset['browser_download_url'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'use':'Saved-only source bank audit/TXTP rendering helper; no runtime plugin installed'}
(out/'Download.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('wwiser',release['tag_name'],target.stat().st_size,'bytes')
