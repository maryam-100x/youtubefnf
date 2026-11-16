"""Bar grids for music files: beats, downbeats (the beat-in-4 phase with the strongest low-band onsets) and each bar's loudness,
written next to each file as <file>.grid.json. The score engine (score.py) starts cues on a downbeat and moves each handoff onto the
outgoing track's own beat. Any track works: the creator's own files in MUSIC, or one rendered by tools/music.

  EDIT tools/sound/grid.py <file or folder> [...]      (a folder: every .wav in it)"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np


def grid(path):
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time", tightness=120)
    tempo = float(np.atleast_1d(tempo)[0])
    # low-band onsets (kick, bass) decide the bar phase
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    low = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[f < 200]), sr=sr)
    tl = librosa.times_like(low, sr=sr)
    strength = np.interp(beats, tl, low) if len(beats) else np.array([])
    phase = int(np.argmax([strength[p::4].mean() if len(strength[p::4]) else 0 for p in range(4)])) if len(strength) >= 8 else 0
    downs = beats[phase::4]
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    tr = librosa.times_like(rms, sr=sr, hop_length=512)
    bars = []
    for a, b in zip(downs, list(downs[1:]) + [len(y) / sr]):
        m = rms[(tr >= a) & (tr < b)]
        bars.append(round(float(20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-9)), 1) if len(m) else -90.0)
    out = {"file": Path(path).name, "tempo": round(tempo, 2), "dur": round(len(y) / sr, 3), "beats": [round(float(x), 3) for x in beats],
           "downbeats": [round(float(x), 3) for x in downs], "bar_db": bars}
    Path(str(path) + ".grid.json").write_text(json.dumps(out), encoding="utf-8")
    return out


def main():
    files = []
    for a in sys.argv[1:]:
        p = Path(a)
        files += sorted(p.glob("*.wav")) if p.is_dir() else [p]
    for p in files:
        g = grid(p)
        prof = "".join(str(int(np.clip((x - (max(g["bar_db"]) - 27)) / 3, 0, 9))) for x in g["bar_db"])
        print(f"{p.stem[:34]:34s} {g['tempo']:6.1f} bpm  first downbeat {g['downbeats'][0] if g['downbeats'] else 0:6.2f}  "
              f"bars {len(g['downbeats']):3d}  per-bar level: {prof}", flush=True)


if __name__ == "__main__":
    main()
