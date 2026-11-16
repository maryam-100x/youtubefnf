"""Two checks every chosen patch gets before it plays a part: its real octave, and the tones it adds.

1. Octave: some patches sound one or two octaves off the written note (a sub that plays an octave under, a pluck an octave over).
   The patch plays one written note; its sounding pitch is read as the lowest spectral peak within 14 dB of the strongest
   (20 Hz-5 kHz, the whole held note). pYIN's median is printed beside it as a cross-check; when the two disagree by 6 semitones or
   more the reading is marked "uncertain" (pYIN locks onto subharmonics near its floor for deep basses; a sequencer patch moves
   between octaves on its own): listen, or play another note.
2. Added tones: a bass or hit that adds a third, a tritone or a seventh to every note clashes with half the chords it plays under.
   The chroma (constant-Q, from C1) of the held note is read against the played pitch class; an interval other than the root and the
   fifth holding 12% or more of the chroma is named. A minor 2nd or major 7th next to the root is reported as "smear" (detune or a
   pitch glide), not as an added tone. A bass with a strong added third or tritone is refused.

    SYNTH tools/music/music.py check "<patch>" ["<patch>" ...] [--role bass] [--note 45] [--seconds 2.5] [--json out.json]
    roles set the default note and length: bass/sub/drive/hit 45 (A2: a patch an octave under still sounds at 55 Hz, where pitch and
    chroma read reliably; at 27 Hz they don't), pad/pulse/keys 57 (A3), drone 45 held 8 s (slow swells need the time)

It reproduced the recorded readings of every kit sound (standard/research/MUSIC_SOUNDS.md).
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from .settings import SR, ensure_parent
from .surge import Surge

NAMES = {1: "minor 2nd", 2: "major 2nd", 3: "minor 3rd", 4: "major 3rd", 5: "4th", 6: "tritone", 8: "minor 6th", 9: "major 6th",
         10: "minor 7th", 11: "major 7th"}
ROLE_NOTE = {"bass": 45, "sub": 45, "drive": 45, "hit": 45, "pad": 57, "pulse": 57, "keys": 57, "drone": 45}
ROLE_SECONDS = {"drone": 8.0}


def peak_pitch(m: np.ndarray, sr: int) -> float | None:
    """The lowest spectral peak within 14 dB of the strongest (20 Hz-5 kHz), as a MIDI number."""
    import librosa
    S = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    fr = np.fft.rfftfreq(len(m), 1 / sr)
    band = (fr >= 20) & (fr <= 5000)
    if not band.any() or S[band].max() <= 0:
        return None
    i = int(np.argmax(band & (S >= 0.2 * S[band].max())))
    return float(librosa.hz_to_midi(fr[i]))


def pyin_pitch(m: np.ndarray, sr: int) -> float | None:
    import librosa
    y = librosa.resample(m, orig_sr=sr, target_sr=22050)
    f0, voiced, _ = librosa.pyin(y, fmin=25.0, fmax=2000.0, sr=22050, frame_length=4096)
    f = f0[voiced & np.isfinite(f0)] if voiced is not None else np.array([])
    return float(librosa.hz_to_midi(np.median(f))) if len(f) >= 5 else None


def chroma_by_interval(m: np.ndarray, sr: int, note: int) -> dict:
    import librosa
    y = librosa.resample(m, orig_sr=sr, target_sr=22050)
    c = librosa.feature.chroma_cqt(y=y, sr=22050, fmin=librosa.note_to_hz("C1"), n_octaves=7).mean(1)
    c = c / (c.sum() + 1e-12)
    rel = {(pc - note) % 12: float(c[pc]) for pc in range(12)}
    return {iv: round(v, 3) for iv, v in sorted(rel.items(), key=lambda kv: -kv[1])}


def check(s: Surge, patch: str, note: int, seconds: float) -> dict:
    name, _, _ = patch.partition("@")
    s.load(name)
    a = s.render([(0.05, seconds, note, 100)], seconds + 1.0)
    m = a.mean(0)
    if np.abs(m).max() < 1e-4:
        return {"patch": patch, "silent": True}
    seg = m[int(0.15 * SR):int((0.05 + seconds) * SR)]
    pk, py = peak_pitch(seg, SR), pyin_pitch(seg, SR)
    off = None if pk is None else pk - note
    tones = chroma_by_interval(seg, SR, note)
    extra = {NAMES[iv]: v for iv, v in tones.items() if iv not in (0, 1, 7, 11) and v >= 0.12}
    smear = {NAMES[iv]: v for iv, v in tones.items() if iv in (1, 11) and v >= 0.12}
    return {"patch": patch, "written": note, "sounding_midi": None if pk is None else round(pk, 2),
            "pyin_midi": None if py is None else round(py, 2),
            "uncertain": bool(pk is not None and py is not None and abs(pk - py) >= 6),
            "offset_semitones": None if off is None else round(off, 2),
            "transpose_to_fix": None if off is None else int(-12 * round(off / 12)),
            "added_tones_12pct": extra, "smear_12pct": smear, "chroma_by_interval": tones}


def main():
    ap = argparse.ArgumentParser(prog="music.py check")
    ap.add_argument("patches", nargs="+")
    ap.add_argument("--note", type=int, default=None)
    ap.add_argument("--role", default="pad")
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    s = Surge()
    rows = []
    for p in a.patches:
        r = check(s, p, a.note if a.note is not None else ROLE_NOTE.get(a.role, 57),
                  a.seconds if a.seconds is not None else ROLE_SECONDS.get(a.role, 2.5))
        rows.append(r)
        if r.get("silent"):
            print(f"{p}: silent on this note")
            continue
        if r["offset_semitones"] is None:
            print(f"{p}: no pitch found on note {r['written']} (listen to it)")
            continue
        print(f"{p}: written {r['written']}, sounds {r['sounding_midi']} ({r['offset_semitones']:+.2f} st; pYIN {r['pyin_midi']}"
              f"{', UNCERTAIN' if r['uncertain'] else ''}) -> transpose {r['transpose_to_fix']:+d}; added tones >= 12%: "
              f"{r['added_tones_12pct'] or 'none'}{'; smear ' + str(r['smear_12pct']) if r['smear_12pct'] else ''}", flush=True)
    if a.json:
        with open(ensure_parent(a.json), "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
