"""Author a finite soft-air/shimmer success cue; original-game audio is untouched."""
from pathlib import Path
import json
import math
import random
import struct
import wave

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/BeastDodge_20261012/Feedback'
OUT.mkdir(parents=True, exist_ok=True)
# Assistant TEMP sound-design settings, not original timing/values.
settings = {'sample_rate_hz': 48000, 'duration_seconds': .18, 'peak_amplitude': .16,
    'attack_seconds': .012, 'noise_lowpass_hz': 2800, 'noise_highpass_hz': 500,
    'shimmer_start_hz': 2400, 'shimmer_end_hz': 1350, 'shimmer_fraction': .16,
    'tail_power': 2.8, 'noise_seed': 20261012}
rng = random.Random(settings['noise_seed'])
low, high_low = 0., 0.
a = 1 - math.exp(-2 * math.pi * settings['noise_lowpass_hz'] / settings['sample_rate_hz'])
b = 1 - math.exp(-2 * math.pi * settings['noise_highpass_hz'] / settings['sample_rate_hz'])
phase, samples = 0., []
count = round(settings['duration_seconds'] * settings['sample_rate_hz'])
for i in range(count):
    t = i / settings['sample_rate_hz']
    u = i / (count - 1)
    low += a * (rng.uniform(-1, 1) - low)
    high_low += b * (low - high_low)
    envelope = min(1., t / settings['attack_seconds']) * (1 - u) ** settings['tail_power']
    hz = settings['shimmer_start_hz'] * (1 - u) + settings['shimmer_end_hz'] * u
    phase += 2 * math.pi * hz / settings['sample_rate_hz']
    samples.append(envelope * (low - high_low + settings['shimmer_fraction'] * math.sin(phase)))
maximum = max(abs(v) for v in samples)
samples = [v * settings['peak_amplitude'] / maximum for v in samples]
file = OUT / 'Player_Dodge_Success.wav'
with wave.open(str(file), 'wb') as audio:
    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(settings['sample_rate_hz'])
    audio.writeframes(b''.join(struct.pack('<h', round(v * 32767)) for v in samples))
report = {'status': 'authored', 'file': str(file), 'origin': 'Assistant-authored signal, user-requested dodge-success SFX', 'settings': settings,
    'samples': len(samples), 'clipping_samples': sum(abs(v) >= 1 for v in samples), 'first_sample': samples[0], 'last_sample': samples[-1]}
(OUT / 'AudioSource.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'settings'}), flush=True)
