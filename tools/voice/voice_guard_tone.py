"""The voice guard's ears, part 2: the tone of a narration, frame by frame, as numbers (the pipeline venv: parselmouth + numpy).
The tone faults a narration voice slips into (deep and close, as if leaning into the mic; whispery and mysterious; a tired or annoyed
whisper; quiet, swallowed words) are, in the sound: the pitch and its range, how much of the sound is voiced (a whisper has no pitch),
how clean the voicing is (CPP: cepstral peak prominence, low = breathy), the balance of the spectrum (a close, deep voice has more
energy under 300 Hz and less presence at 2-5 kHz) and the level against the narration's own.

Every 10 ms of a wav: level (dB), f0 (Praat, 60-400 Hz), harmonicity (Praat HNR), voicing strength (autocorrelation, dj/tts.py's
method), CPP (numpy cepstrum, 40-ms frames), band energies (0-150, 150-300, 300-600, 600-1200, 1200-2400, 2400-4800, 4800-10000 Hz, dB).
Speech frames = 20 dB over the file's quiet floor. `stats(fr, t0, t1)` sums any span up (medians over its speech frames); the CLI writes
the same per 2.0-s window (hop 0.5, the embedding grid) to <wav>.guard_tone.json.

  PIPE tools/voice/voice_guard_tone.py <wav or folder> [...] [--win 2.0] [--hop 0.5] [--force]
      (a folder = every .wav under it, e.g. <MEDIA>/voice/guard when building the guard's reference: voice_guard_calib.py)"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import parselmouth

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "common"))
from paths import FFMPEG  # noqa: E402

SR = 48000
HOP = 480            # 10 ms
WIN = 1920           # 40 ms
BANDS = [(0, 150), (150, 300), (300, 600), (600, 1200), (1200, 2400), (2400, 4800), (4800, 10000)]
VERSION = 3
CHUNK = 8000         # frames computed at a time (80 s of audio: ~0.3 GB per array instead of 4.6 GB for 54 minutes)


def load(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def frames(x):
    """Per 10-ms frame: level, f0, hnr, voicing, cpp, bands (n x 7, dB), plus the file's quiet floor and the speech mask."""
    n = max(1, (len(x) - WIN) // HOP + 1)
    # in blocks of frames (a 54-minute narration's frame matrix alone is 4.6 GB, too much for a 16-GB PC running other jobs); every
    # frame is computed exactly the same, only fewer at a time
    level, bands, cpp, voicing = np.zeros(n), np.zeros((n, len(BANDS))), np.zeros(n), np.zeros(n)
    f = np.fft.rfftfreq(WIN, 1 / SR)
    q = np.arange(WIN // 2) / SR
    lo, hi = int(SR / 400), int(SR / 60)
    qs = q[lo:hi]
    A = np.stack([qs, np.ones_like(qs)], 1)
    han = np.hanning(WIN)[None, :]
    for c0 in range(0, n, CHUNK):
        c1 = min(n, c0 + CHUNK)
        m_ = c1 - c0
        idx = np.arange(c0, c1)[:, None] * HOP + np.arange(WIN)[None, :]
        xi = x[idx]
        level[c0:c1] = 20 * np.log10(np.sqrt((xi ** 2).mean(1)) + 1e-9)
        spec = np.abs(np.fft.rfft(xi * han, axis=1)) ** 2
        bands[c0:c1] = np.stack([10 * np.log10(spec[:, (f >= blo) & (f < bhi)].sum(1) + 1e-12) for blo, bhi in BANDS], 1)
        # CPP: the cepstral peak in the pitch range over the line fitted to the cepstrum (Hillenbrand's measure, per frame)
        cep = np.abs(np.fft.irfft(np.log(spec + 1e-12), axis=1))[:, : WIN // 2]
        del spec
        cs = cep[:, lo:hi]
        coef = np.linalg.lstsq(A, cs.T, rcond=None)[0]           # a line per frame
        fit = (A @ coef).T
        cpp[c0:c1] = 20 * np.log10(np.maximum(cs.max(1), 1e-9)) - 20 * np.log10(np.maximum(fit[np.arange(m_), cs.argmax(1)], 1e-9))
        del cep, cs, fit
        # voicing strength: the normalised autocorrelation peak for 70-400 Hz (dj/tts.py voicing)
        s_ = xi - xi.mean(1, keepdims=True)
        ac = np.fft.irfft(np.abs(np.fft.rfft(s_, n=2 * WIN, axis=1)) ** 2, axis=1)[:, :WIN]
        voicing[c0:c1] = ac[:, SR // 400: SR // 70].max(1) / np.maximum(ac[:, 0], 1e-12)
        del ac, s_, xi, idx
    # Praat: pitch and harmonicity in 20-s blocks, sampled on the frame grid. Blocks, not the whole file: Praat's silence threshold is
    # relative to the sound's own peak, and in a narration that carries a clip's audio at full level in a hold beat, whole spoken words
    # come back unvoiced (f0 = 0 on a loud last word) when the file is analysed in one go
    t = (np.arange(n) * HOP + WIN / 2) / SR
    f0 = np.zeros(n)
    h = np.full(n, np.nan)
    block, pad = 20.0, 0.5
    b0 = 0.0
    while b0 < len(x) / SR:
        b1 = min(b0 + block, len(x) / SR)
        lo, hi = int(max(0.0, b0 - pad) * SR), int(min(len(x) / SR, b1 + pad) * SR)
        snd = parselmouth.Sound(x[lo:hi], SR)
        m = (t >= b0) & (t < b1)
        if (hi - lo) / SR >= 0.2 and m.any():
            tt = t[m] - lo / SR
            try:
                pitch = snd.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400)
                pf = pitch.selected_array["frequency"]
                v = np.interp(tt, pitch.xs(), np.where(np.isfinite(pf), pf, 0.0), left=0.0, right=0.0)
                f0[m] = np.where(v > 0, v, 0.0)
            except Exception:
                pass
            try:
                hnr = snd.to_harmonicity_cc(time_step=0.01, minimum_pitch=60)
                hv = hnr.values[0]
                h[m] = np.interp(tt, hnr.xs(), np.where(np.isfinite(hv) & (hv > -100), hv, np.nan), left=np.nan, right=np.nan)
            except Exception:
                pass
        b0 = b1
    floor = max(float(np.percentile(level, 5)), float(level.max()) - 70)
    speech = level > floor + 20
    return {"t": t, "level": level, "f0": f0, "hnr": h, "voicing": voicing, "cpp": cpp, "bands": bands, "floor": floor, "speech": speech,
            "seconds": len(x) / SR}


def stats(fr, t0, t1):
    """The tone of a span, as medians over its speech frames (None when it holds under 0.15 s of speech)."""
    m = fr["speech"] & (fr["t"] >= t0) & (fr["t"] < t1)
    if m.sum() < 15:
        return None
    f0 = fr["f0"][m]
    v = f0 > 0
    b = fr["bands"][m]
    tot = 10 * np.log10((10 ** (b / 10)).sum(1) + 1e-12)
    rel = b - tot[:, None]
    lev = fr["level"][m]
    out = {
        "n": int(m.sum()),
        "level": float(np.percentile(lev, 80)),                        # the span's body
        "f0": float(np.median(f0[v])) if v.sum() >= 5 else 0.0,
        "f0_range": float(np.percentile(f0[v], 90) - np.percentile(f0[v], 10)) if v.sum() >= 5 else 0.0,
        "voiced": float(v.mean()),                                      # share of speech frames with a pitch
        "voicing": float(np.median(fr["voicing"][m])),
        "cpp": float(np.median(fr["cpp"][m])),
        "hnr": float(np.nanmedian(fr["hnr"][m])) if np.isfinite(fr["hnr"][m]).any() else 0.0,
        "low": float(np.median(rel[:, 0:2].max(1))),                    # the strongest band under 300 Hz, dB under the frame's total
        "sub": float(np.median(rel[:, 0])),                             # under 150 Hz
        "presence": float(np.median(rel[:, 5])),                        # 2.4-4.8 kHz
        "air": float(np.median(rel[:, 6])),                             # 4.8-10 kHz
        "tilt": float(np.median((b[:, 0:3].max(1)) - (b[:, 4:6].max(1)))),  # lows over highs, dB
    }
    return {k: (round(x, 3) if isinstance(x, float) else x) for k, x in out.items()}


def windows(fr, win, hop):
    rows = []
    t = 0.0
    while t + 0.6 < fr["seconds"]:
        s = stats(fr, t, t + win)
        if s:
            s["t"] = round(t, 3)
            rows.append(s)
        t += hop
    return rows


def stamp(path):
    st = os.stat(path)
    return f"{st.st_size}-{int(st.st_mtime)}-v{VERSION}"


def wav_args(args):
    """The wavs named, a folder standing for every .wav under it (shells without globbing, e.g. PowerShell)."""
    out = []
    for w in map(Path, args):
        out += sorted(w.rglob("*.wav")) if w.is_dir() else [w]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="+", help="wav files or folders")
    ap.add_argument("--win", type=float, default=2.0)
    ap.add_argument("--hop", type=float, default=0.5)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for w in wav_args(a.wavs):
        out = w.with_name(w.name + ".guard_tone.json")
        if out.exists() and not a.force:
            try:
                d = json.loads(out.read_text(encoding="utf-8"))
                if d.get("stamp") == stamp(w) and d.get("win") == a.win and d.get("hop") == a.hop:
                    continue
            except Exception:
                pass
        fr = frames(load(w))
        rows = windows(fr, a.win, a.hop)
        out.write_text(json.dumps({"wav": str(w), "stamp": stamp(w), "win": a.win, "hop": a.hop, "seconds": round(fr["seconds"], 3),
                                   "floor": round(fr["floor"], 2), "rows": rows}), encoding="utf-8")
        print(f"{w.name}: {len(rows)} windows, {fr['seconds']:.1f} s, floor {fr['floor']:.0f} dB")


if __name__ == "__main__":
    sys.exit(main())
