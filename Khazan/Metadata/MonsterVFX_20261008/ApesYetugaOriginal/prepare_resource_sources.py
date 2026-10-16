"""Targeted source-only CUE4Parse metadata closure. Does not import assets."""
from pathlib import Path
import importlib.util
import json
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PROVIDER=ROOT/'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.exe'

def main():
    spec=importlib.util.spec_from_file_location('apes_closure',OUT/'build_resource_closure.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    attempts=[]
    for i in range(1,6):
        m.main()
        missing=m.read(OUT/'MissingSourceRequests.json')
        if not missing:
            break
        previous_failed={p for a in attempts for p in a['failed']}
        requests=[p for p in missing if p not in previous_failed]
        if not requests:
            break
        name=f'MetadataRound{i}'
        m.write(name+'_Requests.json',requests)
        directory=OUT/'Source';directory.mkdir(exist_ok=True)
        with (OUT/(name+'.log')).open('w',encoding='utf-8') as log:
            result=subprocess.run([str(PROVIDER),'metadata',str(directory),str(OUT/(name+'_Requests.json'))],
                stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|0x4000)
        assert result.returncode==0,(name,result.returncode)
        rows=m.read(directory/'MetadataExtractionReport.json')
        m.write(name+'_Receipt.json',rows)
        failed=[r['source'] for r in rows if r['status']!='ok']
        attempts.append({'round':i,'requests':len(requests),'success':len(rows)-len(failed),'failed':failed})
    m.main()
    m.write('SourceExtractionSummary.json',{'scope':'metadata only, BelowNormal hidden CUE4Parse; no Content/native/editor/UI mutation',
        'attempts':attempts,'final_missing':m.read(OUT/'MissingSourceRequests.json')})
    print(json.dumps(attempts))

if __name__=='__main__':
    main()
