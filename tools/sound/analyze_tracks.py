"""Measure music tracks without listening: for each track, tempo and beat grid, key, the energy shape in 8-s steps (0-9, relative to the
track's loudest), section boundaries, onset rate (how busy), brightness, and how much energy sits in the voice's band (1-4 kHz: music
there fights the narration). Any local track works: the creator's own files in MUSIC, or one rendered by tools/music.

  EDIT tools/sound/analyze_tracks.py [<file or folder> ...] [--tags <tsv>] > report.txt
  (no argument: every track under MUSIC; writes MUSIC/analysis/<track>.json per track)
  --tags   a TSV `file<TAB>tags` (a file name, and words for its mood and style) kept in the analysis, for music_library.py"""
import argparse
import csv
import json
import sys
from pathlib import Path

import librosa
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MUSIC  # noqa: E402

OUT = MUSIC / "analysis"
AUDIO = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aif", ".aiff"}
KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_of(chroma):
    v = chroma.mean(axis=1)
    best = None
    for i in range(12):
        for prof, name in ((MAJ, "maj"), (MIN, "min")):
            r = np.corrcoef(v, np.roll(prof, i))[0, 1]
            if best is None or r > best[0]:
                best = (r, f"{KEYS[i]} {name}")
    return best[1], round(float(best[0]), 2)


def analyze(path, tags=""):
    path = Path(path)
    y, sr = librosa.load(str(path), sr=22050, mono=True)
    dur = len(y) / sr
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    tempo = float(np.atleast_1d(tempo)[0])
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
    # downbeat phase: the beat-in-4 phase with the strongest onsets
    bstr = np.interp(beats, librosa.times_like(onset_env, sr=sr), onset_env) if len(beats) else np.array([])
    phase = int(np.argmax([bstr[p::4].mean() if len(bstr[p::4]) else 0 for p in range(4)])) if len(bstr) >= 8 else 0
    downbeats = beats[phase::4] if len(beats) else beats
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    t = librosa.times_like(rms, sr=sr, hop_length=hop)
    db = 20 * np.log10(rms + 1e-9)
    mx = np.percentile(db, 99)
    prof = ""
    for a in np.arange(0, dur, 8.0):
        m = db[(t >= a) & (t < a + 8)]
        lvl = 0 if not len(m) else int(np.clip(round((np.mean(m) - (mx - 30)) / 3), 0, 9))
        prof += str(lvl)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)) ** 2
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    band = S[(f >= 1000) & (f <= 4000)].sum() / (S.sum() + 1e-12)
    cent = float(np.median(librosa.feature.spectral_centroid(S=np.sqrt(S), sr=sr)))
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key, conf = key_of(chroma)
    # section boundaries from MFCC+chroma novelty (about one per 20 s)
    feat = np.vstack([librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), chroma])
    feat = librosa.util.sync(feat, librosa.time_to_frames(beats, sr=sr)) if len(beats) > 16 else feat
    k = max(2, int(dur // 20))
    try:
        bounds = librosa.segment.agglomerative(feat, k)
        btimes = beats[np.clip(bounds, 0, len(beats) - 1)] if len(beats) > 16 else librosa.frames_to_time(bounds, sr=sr)
        btimes = sorted(round(float(x), 1) for x in btimes if x > 1.0)
    except Exception:
        btimes = []
    first = onset_env[: int(0.6 * sr / hop)]
    intro_hit = float(first.max() / (np.median(onset_env) + 1e-9)) if len(first) else 0.0
    res = {"file": str(path).replace("\\", "/"), "title": path.stem, "family": path.parent.name, "tempo_est": round(tempo, 1),
           "dur": round(dur, 1), "key": key, "key_conf": conf, "energy_8s": prof, "sections": btimes,
           "onsets_per_s": round(len(onsets) / dur, 2), "centroid_hz": int(cent), "voiceband_share": round(float(band), 3),
           "intro_hit": round(intro_hit, 1), "downbeats_first": [round(float(x), 2) for x in downbeats[:6]], "tags": tags}
    (OUT / f"{path.stem}.json").write_text(json.dumps(res), encoding="utf-8")
    return res


def tracks(args):
    out = []
    for a in args or [str(MUSIC)]:
        p = Path(a)
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.suffix.lower() in AUDIO and OUT not in f.parents)
        elif p.exists():
            out.append(p)
        else:
            print(f"not found: {p}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="tracks or folders (default: MUSIC)")
    ap.add_argument("--tags", help="a TSV `file<TAB>tags`")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    tags = {}
    if a.tags:
        with open(a.tags, encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="\t"):
                if len(row) >= 2:
                    tags[Path(row[0]).name.lower()] = row[1]
    print(f"{'family':10s} {'title':34s} {'est':>5s} {'key':7s} {'dur':>5s} {'on/s':>5s} {'voice%':>6s} {'hit':>4s}  energy (8 s steps)  sections")
    for p in tracks(a.paths):
        try:
            r = analyze(p, tags.get(p.name.lower(), ""))
        except Exception as e:
            print(f"{p.parent.name[:10]:10s} {p.stem[:34]:34s} ERROR {e}")
            continue
        print(f"{r['family'][:10]:10s} {r['title'][:34]:34s} {r['tempo_est']:5.0f} {r['key']:7s} {r['dur']:5.0f} "
              f"{r['onsets_per_s']:5.2f} {100 * r['voiceband_share']:6.1f} {r['intro_hit']:4.1f}  {r['energy_8s']:20s} {r['sections'][:8]}",
              flush=True)


if __name__ == "__main__":
    main()
