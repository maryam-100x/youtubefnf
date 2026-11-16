"""Censor one spoken word: a risky word in the creator's own voice gets a bass-boost hit (never a beep) or is distorted past
recognition, never made loud. Two modes: a hit in the word's place (a sound file, `--sfx`), or `--distort`: the word itself
bass-boosted and clipped past recognition at the voice's own loudness. The voice says the word, so the line keeps its rhythm; then:
  - the word is muted in build/voice/narration.wav, from its onset (captions_fix.json's measured onset for it, else Whisper's start)
    to the first 80 ms of silence after it (10-ms RMS under -50 dBFS) or the next word's start, whichever is first; 4-ms ramps
  - the hit (default: the house bass drop, SFX/house/sfx/bass_drop.wav, or the creator's pick; any file with --sfx) starts on the onset, from its own
    first sound, at the voice's loudest momentary loudness of the two seconds before + REL dB (BS.1770 K-weighting, 400-ms windows;
    default -6: half as loud, so the hit never jumps out of the line); its tail ends 0.15 s into the next line, 80-ms fade
  - the uncensored voice stays in build/voice/narration_uncensored.wav: a re-run on the same take starts from it (censor.json keeps the
    censored file's sha1; a narration.wav that isn't it is a fresh take from `dj tts` and becomes the source). Before `dj captions` runs
    again, copy narration_uncensored.wav over narration.wav (Whisper can't hear a muted word). build/voice/censor.json records the run
The caption (a starred spelling such as D*MN) and the picture's cue come from captions_fix.json: an onset entry ({beat, w, start}) and
an `into` entry for the word. After `dj tts` or `dj captions` runs again, run this again.

  --distort: the word's span (the same onset and end) is replaced by itself through a +22 dB low shelf at 180 Hz, a hard clip, a 650 Hz
    low-pass, a second softer clip and a 1.4 kHz low-pass (the consonants and the vowel's upper formants gone, the rhythm kept), levelled
    to the voice's momentary loudness + REL (default 0: not louder than the voice)

  PIPE tools/sound/censor.py <video dir> <beat> <heard word> [--nth N] [--rel DB] [--sfx WAV | --distort]
  e.g. PIPE tools/sound/censor.py videos/012-city-at-night S03 damn. --distort"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MOTION, SFX as SFX_DIR, TOOLS  # noqa: E402

sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(MOTION))
from dj.core import Ctx, load_config  # noqa: E402
from onsets import apply_onsets  # noqa: E402

SR = 48000
SFX = SFX_DIR / "house" / "sfx" / "bass_drop.wav"  # the default hit: the house bass drop (any other with --sfx)


def sha1(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def read_wav(p):
    with wave.open(str(p)) as w:
        assert w.getsampwidth() == 2 and w.getframerate() == SR, f"{p}: expected 16-bit {SR} Hz"
        ch = w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32768
    return x.reshape(-1, ch), ch


def write_wav(p, x, ch):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 32767 / 32768) * 32768).astype(np.int16).tobytes())


def load_any(p):
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(p), "-f", "f64le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float64).copy()


def biquad(x, b, a):
    y, x1, x2, y1, y2 = np.zeros_like(x), 0.0, 0.0, 0.0, 0.0
    for i, v in enumerate(x):
        o = b[0] * v + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        x2, x1, y2, y1 = x1, v, y1, o
        y[i] = o
    return y


def low_shelf(f0, gain_db, s=1.0):  # RBJ cookbook
    A, w0 = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    al = np.sin(w0) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    c, q = np.cos(w0), 2 * np.sqrt(A) * al
    b = (A * ((A + 1) - (A - 1) * c + q), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - q))
    a0, a1, a2 = (A + 1) + (A - 1) * c + q, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - q
    return tuple(v / a0 for v in b), (1.0, a1 / a0, a2 / a0)


def low_pass(f0, q=0.707):  # RBJ cookbook
    w0 = 2 * np.pi * f0 / SR
    al, c = np.sin(w0) / (2 * q), np.cos(w0)
    a0 = 1 + al
    return ((1 - c) / 2 / a0, (1 - c) / a0, (1 - c) / 2 / a0), (1.0, -2 * c / a0, (1 - al) / a0)


def distort(x):
    """The word, bass-boosted and clipped past recognition (the bass-boosted sound, not its loudness)."""
    y = biquad(x, *low_shelf(180, 22))
    y = np.clip(y * 40 / (np.abs(y).max() + 1e-9), -1, 1)       # hard clip: the voice becomes a square-ish buzz
    y = biquad(biquad(y, *low_pass(650)), *low_pass(650))         # the consonants and the upper formants gone
    y = np.tanh(4 * y / (np.abs(y).max() + 1e-9))                 # a softer second clip: the boom's grit back
    y = biquad(y, *low_pass(1400))
    r = int(0.006 * SR)
    y[:r] *= np.linspace(0, 1, r)
    y[-r:] *= np.linspace(1, 0, r)
    return y


def k_weight(x):  # ITU-R BS.1770 at 48 kHz: the head's high shelf, then the RLB high-pass
    x = biquad(x, (1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585))
    return biquad(x, (1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621))


def max_momentary(x):
    """The loudest 400-ms window (100-ms hop), LUFS."""
    k, w, h = k_weight(x), int(0.4 * SR), int(0.1 * SR)
    ms = [np.mean(k[i:i + w] ** 2) for i in range(0, max(1, len(k) - w + 1), h)]
    return -0.691 + 10 * np.log10(max(ms) + 1e-12)


def phone_band(x):  # a phone speaker: little below ~300 Hz (two one-pole high-passes)
    a = np.exp(-2 * np.pi * 300 / SR)
    for _ in range(2):
        y = np.zeros_like(x)
        for i in range(1, len(x)):
            y[i] = a * (y[i - 1] + x[i] - x[i - 1])
        x = y
    return x


def rms10(x):
    h = int(0.01 * SR)
    n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("beat")
    ap.add_argument("word", help="the heard spelling in build/captions/words.json, e.g. damn.")
    ap.add_argument("--nth", type=int, default=0)
    ap.add_argument("--rel", type=float, default=None, help="loudness over the voice's, dB (a hit: -6, half as loud; --distort: 0)")
    ap.add_argument("--sfx", default=str(SFX), help="the hit's sound file (default SFX/house/sfx/bass_drop.wav)")
    ap.add_argument("--distort", action="store_true", help="the word itself bass-boosted and clipped past recognition (no hit)")
    a = ap.parse_args()
    rel = a.rel if a.rel is not None else (0.0 if a.distort else -6.0)
    ctx = Ctx(a.video, load_config())
    vdir, B = ctx.video, ctx.build
    words = json.loads((B / "captions/words.json").read_text(encoding="utf-8"))["words"]
    words = apply_onsets(words, vdir / "captions_fix.json")
    hits = [i for i, x in enumerate(words) if x["beat"] == a.beat and x["w"] == a.word]
    if a.nth >= len(hits):
        raise SystemExit(f"no {a.word!r} #{a.nth} in {a.beat}")
    i = hits[a.nth]
    t0 = words[i]["start"]
    nar, src, rec_f = B / "voice/narration.wav", B / "voice/narration_uncensored.wav", B / "voice/censor.json"
    last = json.loads(rec_f.read_text(encoding="utf-8")) if rec_f.exists() else {}
    if not (src.exists() and last.get("out_sha1") == sha1(nar)):  # narration.wav isn't our last output: a fresh take from dj tts, the source now
        shutil.copyfile(nar, src)
        print(f"  {nar.name}: a new take, kept as {src.name}")
    x, ch = read_wav(src)
    mono = x.mean(1)
    db = rms10(mono)
    # the word's end: the first 80 ms of silence after it, or the next word's start, whichever is first (30 ms is not enough: a
    # stop's own closure inside the word is silent too, and a mute would end inside the word)
    nxt = words[i + 1]["start"] if i + 1 < len(words) else len(db) / 100
    f = int((t0 + 0.1) * 100)
    while f + 8 < len(db) and f / 100 < nxt - 0.005 and not all(db[f:f + 8] < -50):
        f += 1
    t1 = min(f / 100, nxt - 0.005)
    g = f
    while g < len(db) and db[g] < -45:  # the next line's first sound
        g += 1
    t_next = g / 100
    s0, s1, r = int(round(t0 * SR)), int(round(t1 * SR)), int(0.004 * SR)
    voice_m = max_momentary(mono[max(0, s0 - 2 * SR):s0])
    if a.distort:
        proc = distort(mono[s0:s1].copy())
        pm = max_momentary(proc)
        gain = 10 ** ((voice_m + rel - pm) / 20)
        if np.abs(proc).max() * gain > 10 ** (-1 / 20):
            gain = 10 ** (-1 / 20) / np.abs(proc).max()
            print(f"  ! the distorted word capped at -1 dBFS peak (wanted {voice_m + rel - pm:+.1f} dB)")
        y = x.copy()
        y[s0:s1] = (proc * gain)[:, None]
        write_wav(nar, y, ch)
        ph_v, ph_h = max_momentary(phone_band(mono[max(0, s0 - 2 * SR):s0])), max_momentary(phone_band(proc * gain))
        rec = {"beat": a.beat, "word": a.word, "nth": a.nth, "mode": "distort", "t0": round(t0, 3), "t1": round(t1, 3),
               "gain_db": round(20 * np.log10(gain), 2), "voice_momentary_lufs": round(voice_m, 1),
               "word_momentary_lufs": round(pm + 20 * np.log10(gain), 1), "phone_band_voice_lufs": round(ph_v, 1),
               "phone_band_word_lufs": round(ph_h, 1), "out_sha1": sha1(nar)}
        rec_f.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        print(f"  distorted {a.word!r} in {a.beat}: {t0:.3f}-{t1:.3f} s at {rec['word_momentary_lufs']} LUFS momentary against the voice's "
              f"{rec['voice_momentary_lufs']} (phone band: {ph_h:.1f} against {ph_v:.1f})")
        return
    hit = load_any(a.sfx)
    lead = np.argmax(np.abs(hit) > 0.1 * np.abs(hit).max())  # from the hit's first sound (a downloaded file can open on silence)
    hit = hit[lead:]
    end = min(len(hit), int((t_next + 0.15 - t0) * SR))
    hit = hit[:end].copy()
    fo = min(int(0.08 * SR), end)
    hit[-fo:] *= np.linspace(1, 0, fo)
    hit_m = max_momentary(hit)
    gain = 10 ** ((voice_m + rel - hit_m) / 20)
    if np.abs(hit).max() * gain > 10 ** (-1 / 20):
        gain = 10 ** (-1 / 20) / np.abs(hit).max()
        print(f"  ! the hit capped at -1 dBFS peak (wanted {voice_m + rel - hit_m:+.1f} dB)")
    y = x.copy()
    y[s0 - r:s0] *= np.linspace(1, 0, r)[:, None]
    y[s0:s1] = 0
    y[s1:s1 + r] *= np.linspace(0, 1, r)[:, None]
    y[s0:s0 + len(hit)] += (hit * gain)[:len(y) - s0, None]
    write_wav(nar, y, ch)
    # the hit against the voice, full range and on a phone speaker (the word's own samples are zero under the hit by construction)
    ph_v = max_momentary(phone_band(mono[max(0, s0 - 2 * SR):s0]))
    ph_h = max_momentary(phone_band(hit * gain))
    rec = {"beat": a.beat, "word": a.word, "nth": a.nth, "mode": "hit", "t0": round(t0, 3), "t1": round(t1, 3), "next_sound": round(t_next, 3),
           "sfx": str(a.sfx), "hit_s": round(len(hit) / SR, 3), "gain_db": round(20 * np.log10(gain), 2),
           "voice_momentary_lufs": round(voice_m, 1), "hit_momentary_lufs": round(hit_m + 20 * np.log10(gain), 1),
           "phone_band_voice_lufs": round(ph_v, 1), "phone_band_hit_lufs": round(ph_h, 1), "out_sha1": sha1(nar)}
    rec_f.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(f"  censored {a.word!r} in {a.beat}: muted {t0:.3f}-{t1:.3f} s (the next sound at {t_next:.2f} s); the hit {len(hit) / SR:.2f} s at "
          f"{rec['hit_momentary_lufs']} LUFS momentary against the voice's {rec['voice_momentary_lufs']} (phone band: {ph_h:.1f} against {ph_v:.1f})")


if __name__ == "__main__":
    main()
