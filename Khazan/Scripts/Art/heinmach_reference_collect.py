"""Collect limited public official gameplay references without editing input photos."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'Saved/Tools/HeinMachReference_20261006'))
import yt_dlp
import imageio_ffmpeg

OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006/References'
OUT.mkdir(parents=True,exist_ok=True)
URL='https://www.youtube.com/watch?v=eu9rhfCqZTM'
report={'source':URL,'kind':'official public gameplay; same build as local game not verified',
        'timestamps_seconds':[90,260,421,600,780]}
try:
    options={'quiet':True,'no_warnings':True,'socket_timeout':15,'retries':1,
             'format':'best[height<=1080]/bestvideo[height<=1080]',
             'ffmpeg_location':imageio_ffmpeg.get_ffmpeg_exe(),
             'outtmpl':str(OUT/'OfficialFirst15Minutes.%(ext)s')}
    with yt_dlp.YoutubeDL(options) as ydl:
        info=ydl.extract_info(URL,download=True)
        report.update(title=info.get('title'),channel=info.get('channel'),
                      upload_date=info.get('upload_date'),duration=info.get('duration'),
                      file=ydl.prepare_filename(info))
    import subprocess
    report['frames']=[]
    for seconds in report['timestamps_seconds']:
        target=OUT/('Official_%04ds.png'%seconds)
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error',
                        '-ss',str(seconds),'-i',report['file'],'-frames:v','1','-y',str(target)],check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        report['frames'].append(str(target))
    report['passed']=True
except Exception as exc:
    report.update(passed=False,error=str(exc))
(OUT/'Collection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='file'},ensure_ascii=False),flush=True)
