"""Decode only the original HeinMach/Yetuga battle branch, including its loop."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / 'Metadata/YetugaBGM_20261015'
OUT = ROOT / 'Saved/ImportReports/YetugaBGM_20261015/Decoded'
OUT.mkdir(parents=True, exist_ok=True)
DECODER = Path('C:/Users/user/Downloads/63a7cbccd9fbaae9db45240069a49bd6a3a00b73/Output/.data/vgmstream-cli.exe')
RECIPE = TASK / 'Recipes/YetugaBattle_Sequence.txtp'
source = next((ROOT / 'Saved/ImportReports/GameplayAudio_20261011/BankRecipes08/txtp').glob(
    'bgm_boss_heinmach_pre_01*3911558329*3814669119*4005322201*{f1}*'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

metadata = subprocess.check_output([str(DECODER), '-m', str(RECIPE)], text=True)
(TASK / 'DecoderMetadata.txt').write_text(metadata, encoding='utf-8')
start = int(re.search(r'loop start: (\d+) samples', metadata)[1])
end = int(re.search(r'loop end: (\d+) samples', metadata)[1])
full = OUT / 'YetugaBattle_SourceSequence.wav'
# Ignore playback looping/fadeout: one source intro and exactly one loop cycle.
args = [str(DECODER), '-i', '-o', str(full), str(RECIPE)]
result = subprocess.run(args, capture_output=True, text=True)
(TASK / 'Decode.log').write_text(result.stdout + result.stderr, encoding='utf-8')
result.check_returncode()
rows = []
with wave.open(str(full), 'rb') as original:
    channels, width, rate = original.getnchannels(), original.getsampwidth(), original.getframerate()
    assert channels == 2 and width == 2 and rate == 48000
    assert original.getnframes() == end
    for name, begin, finish in [('Intro', 0, start), ('Loop', start, end)]:
        dest = OUT / ('YetugaBattle_' + name + '.wav')
        original.setpos(begin)
        with wave.open(str(dest), 'wb') as part:
            part.setnchannels(channels)
            part.setsampwidth(width)
            part.setframerate(rate)
            part.writeframes(original.readframes(finish - begin))
        rows.append(dict(kind=name, file=str(dest), start_sample=begin, end_sample=finish,
                         frames=finish-begin, seconds=(finish-begin)/rate,
                         sha256=sha(dest), asset='/Game/Audio/Original/Music/Yetuga/SW_YetugaBattle_' + name))
report = dict(
    source_debug_name=r'Music\boss\bgm_boss_yetuga_82_4on4.wav',
    source_media='BBQ/Content/WwiseAudio/Media/446487212.wem',
    extraction_report=str(TASK / 'Raw/AudioFileExtractionReport.json'),
    event_start='BBQ/Content/_Kazan_/Sound/Music/HeinMach/bgm_boss_heinmach_start',
    event_id=2887386748,
    music_graph_event_id=3379818559,
    gamesyncs={'3245971795': 3911558329, '3710226845': 3814669119, '4033804471': 4005322201},
    source_recipe=str(source), source_recipe_sha256=sha(source),
    native_recipe=str(RECIPE), native_recipe_sha256=sha(RECIPE),
    recipe_changes='Replace WEM path with fresh FModel archive export; remove forced group >1 to preserve full sequence.',
    music_playlist_node=302673256, first_segment=750444780, loop_segment=1069894324,
    source_gain_db=-3.5, gain_policy='Source recipe gain/automation baked once; no normalization or extra native gain.',
    sample_rate=rate, channels=channels, pcm_bits=width*8, loop_start_sample=start, loop_end_sample=end,
    full_decoded_sha256=sha(full), decode_args=args, waves=rows,
    fidelity_scope='Original audio/clip layering/trim/gain; native cue scheduling and global Wwise DSP/RTPC are not claimed sample-identical.')
(TASK / 'SourceMusic.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'prepared': True, 'sample_rate': rate, 'waves': rows}))
