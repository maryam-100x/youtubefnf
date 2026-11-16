"""Bring an ElevenLabs take to video loudness without the squash. The raw takes arrive at about -25 LUFS with peaks 21-22 dB above
their loudness; one gain to -14 LUFS and a 9-ms look-ahead limiter shave up to 9-10 dB off every loud syllable, which sounds hot and
turned up. The voice-over way instead, in three gentle stages:
1. a compressor on the syllables (5-ms RMS detector, soft knee, 2.5:1 above the threshold, 5-ms attack, 120-ms release, in dB), which
   evens the loud syllables out by a few dB without touching the waveform's shape;
2. one gain to the loudness target (-14 LUFS by default);
3. a look-ahead peak limiter at the ceiling with a 60-ms release, left with the last few dB only.
Prints what each stage did (the compressor's and the limiter's gain reduction), so a version can be compared with the old chain.

  EDIT tools/sound/voice_level.py <in.wav> <out.wav> [--lufs -14] [--ceil -1.5]
      [--thresh-rel -2] [--ratio 2.5]   (threshold relative to the input's own loudness, in dB of the 5-ms RMS)
      [--chain mb]: chain D, the house narration chain (chosen by ear against four other chains, all from the same raw takes): only
      the vowel band (400-2500 Hz) held back on its loud moments (5-ms RMS, 4:1 above the take's own loudness, 2-ms attack, 60-ms
      release), the lows and consonants untouched, one gain to -16 LUFS, a light look-ahead limiter at -2 dBFS. dj tts runs it as its
      last step when the video's config says [audio] voice_chain = "multiband". Streamed in chunks; --whole runs it on the whole file
      at once (the reference for the streamed way's null test).
The raw takes must come in unlimited (raw_rebuild.py): a take that was already squashed stays squashed."""
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf


def smooth_db(gr, sr, att, rel):
    """one-pole attack/release smoothing of a gain-reduction curve in dB (gr <= 0: deeper = more reduction)"""
    a_att, a_rel = np.exp(-1.0 / (att * sr)), np.exp(-1.0 / (rel * sr))
    out = np.empty_like(gr)
    g = 0.0
    for i, v in enumerate(gr):  # attack when the reduction deepens, release when it eases
        c = a_att if v < g else a_rel
        g = c * g + (1 - c) * v
        out[i] = g
    return out


def compress(x, sr, thresh_db, ratio=2.5, knee=6.0, att=0.005, rel=0.12):
    m = x if x.ndim == 1 else x.mean(axis=1)
    n = max(1, int(0.005 * sr))
    c = np.cumsum(np.insert(m * m, 0, 0.0))
    rms = np.sqrt(np.maximum((c[n:] - c[:-n]) / n, 1e-12))
    rms = np.pad(rms, (n // 2, len(m) - len(rms) - n // 2), mode="edge")
    lv = 20 * np.log10(rms)
    over = lv - thresh_db
    gr = np.where(over <= -knee / 2, 0.0,
                  np.where(over >= knee / 2, -(1 - 1 / ratio) * over, -(1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    # decimate the detector for the smoother (1 kHz is plenty for 5-ms attack), then back to audio rate
    step = max(1, sr // 1000)
    g_s = smooth_db(gr[::step], sr / step, att, rel)
    g = np.interp(np.arange(len(m)), np.arange(0, len(m), step)[:len(g_s)], g_s)
    y = x * (10 ** (g / 20) if x.ndim == 1 else (10 ** (g / 20))[:, None])
    return y, g


def limit(x, sr, ceil_db=-1.5, look=0.005, rel=0.06):
    m = np.abs(x) if x.ndim == 1 else np.abs(x).max(axis=1)
    ceil = 10 ** (ceil_db / 20)
    need = np.minimum(1.0, ceil / np.maximum(m, 1e-9))
    w = 2 * int(look * sr) + 1
    p = w // 2
    need = np.lib.stride_tricks.sliding_window_view(np.pad(need, p, mode="edge"), w).min(axis=-1)  # the look-ahead: lowest gain near
    gd = 20 * np.log10(need)
    step = max(1, sr // 2000)
    g_s = smooth_db(gd[::step], sr / step, 0.0005, rel)
    g_s = np.minimum(g_s, gd[::step][:len(g_s)])  # never above what the peak needs
    g = np.interp(np.arange(len(m)), np.arange(0, len(m), step)[:len(g_s)], g_s)
    g = np.minimum(g, gd)
    y = x * (10 ** (g / 20) if x.ndim == 1 else (10 ** (g / 20))[:, None])
    return y, g


def level(x, sr, lufs=-14.0, ceil_db=-1.5, thresh_rel=-2.0, ratio=2.5, report=True):
    meter = pyln.Meter(sr)
    L0 = meter.integrated_loudness(x)
    x0 = x * 10 ** ((-20.0 - L0) / 20)  # to a working level first, so the threshold means the same on every take
    y, gc = compress(x0, sr, -20.0 + thresh_rel, ratio)
    L1 = meter.integrated_loudness(y)
    y = y * 10 ** ((lufs - L1) / 20)
    y, gl = limit(y, sr, ceil_db)
    if report:
        voiced = gc < -0.01
        print(f"  in {L0:.1f} LUFS -> {meter.integrated_loudness(y):.1f}; compressor: {100 * voiced.mean():.0f}% of the time, "
              f"median {np.median(gc[voiced]) if voiced.any() else 0:.1f} dB, deepest {gc.min():.1f} dB; limiter: "
              f"{100 * (gl < -0.1).mean():.1f}% of the time, p99 {np.percentile(gl, 1):.1f} dB, deepest {gl.min():.1f} dB; "
              f"peak/loudness {20 * np.log10(np.abs(y).max()) - meter.integrated_loudness(y):.1f} dB")
    return y


def level2(x, sr, lufs=-14.0, ceil_db=-1.5, thresh_rel=4.0, ratio=3.0, att=0.005, rel=0.10, lim_look=0.005, lim_rel=0.08, report=True):
    """the split chain: a compressor on the loud vowels (threshold thresh_rel dB over the take's loudness in 5-ms RMS), then one gain and
    a look-ahead limiter whose release (80 ms) is longer than a pitch period of the voice, so it never reshapes the waveform inside a
    vibration (a 9-ms one does: the crunch); the gain is refined until the output sits on the target"""
    meter = pyln.Meter(sr)
    x0 = x * 10 ** ((-20.0 - meter.integrated_loudness(x)) / 20)
    y0, gc = compress(x0, sr, -20.0 + thresh_rel, ratio, 6.0, att, rel)
    g = lufs - meter.integrated_loudness(y0)
    for _ in range(4):
        y, gl = limit(y0 * 10 ** (g / 20), sr, ceil_db, lim_look, lim_rel)
        L = meter.integrated_loudness(y)
        if abs(L - lufs) < 0.05:
            break
        g += lufs - L
    if report:
        on = gc < -0.5
        print(f"  -> {L:.1f} LUFS; compressor >0.5 dB {100 * on.mean():.0f}% of the time (median {np.median(gc[on]) if on.any() else 0:.1f}, "
              f"deepest {gc.min():.1f} dB); limiter >0.5 dB {100 * (gl < -0.5).mean():.1f}% (99.5th pct {np.percentile(gl, 0.5):.1f}, "
              f"deepest {gl.min():.1f} dB)")
    return y


def bands3(x, sr, lo=400, hi=2500, taps=2047):
    """linear-phase split that sums back exactly: low, mid (the vowel band, where the voice's peaks are), high"""
    from scipy.signal import firwin, fftconvolve
    hl = firwin(taps, lo, fs=sr)
    hh = firwin(taps, hi, fs=sr, pass_zero=False)
    d = taps // 2
    pad = np.pad(x, (d, d))
    low = fftconvolve(pad, hl, mode="valid")
    high = fftconvolve(pad, hh, mode="valid")
    return low, x - low - high, high


def level_mb(x, sr, lufs=-16.0, ceil_db=-1.5, mid_thresh_rel=3.0, ratio=4.0, att=0.002, rel=0.06, report=True):
    """the multiband way (chain D; the raw take sounds clean, while a full-band compressor makes it sound artificially gained up):
    only the vowel band (400-2500 Hz, where 90% of the voice's peaks are) is held back on its loud moments; the lows and the consonants
    and breaths above 2.5 kHz pass untouched, so nothing comes up that was quiet. Then one gain and a light final limiter."""
    meter = pyln.Meter(sr)
    x0 = x * 10 ** ((-20.0 - meter.integrated_loudness(x)) / 20)
    lo, mid, hi = bands3(x0, sr)
    m2, gm = compress(mid, sr, -20.0 + mid_thresh_rel, ratio, 6.0, att, rel)
    y0 = lo + m2 + hi
    g = lufs - meter.integrated_loudness(y0)
    for _ in range(4):
        y, gl = limit(y0 * 10 ** (g / 20), sr, ceil_db, 0.005, 0.04)
        L = meter.integrated_loudness(y)
        if abs(L - lufs) < 0.05:
            break
        g += lufs - L
    if report:
        on = gm < -0.5
        print(f"  -> {L:.1f} LUFS; vowel band held back >0.5 dB {100 * on.mean():.0f}% of the time (median {np.median(gm[on]) if on.any() else 0:.1f}, "
              f"deepest {gm.min():.1f} dB); final limiter >0.5 dB {100 * (gl < -0.5).mean():.1f}% (99.5th pct {np.percentile(gl, 0.5):.1f}, "
              f"deepest {gl.min():.1f} dB)")
    return y


class StreamLoudness:
    """BS.1770 integrated loudness exactly as pyloudnorm's Meter computes it (its K-weighting stages and passband gains, its 400-ms
    blocks every 100 ms with its own sample bounds, the same two gates), fed chunk by chunk: the filters carry their state, and each
    block's sum of squares comes from a running cumulative sum taken at the block bounds. Mono."""

    def __init__(self, sr, n_total):
        from scipy.signal import lfilter_zi
        meter = pyln.Meter(sr)
        self.sr = sr
        self.stages = [(f.b, f.a, f.passband_gain) for f in meter._filters.values()]
        self.zi = [lfilter_zi(b, a) * 0.0 for b, a, _ in self.stages]
        T_g, step = meter.block_size, 1.0 - meter.overlap
        T = n_total / sr
        nb = int(np.round(((T - T_g) / (T_g * step)))) + 1
        self.T_g = T_g
        self.l = [int(T_g * (j * step) * sr) for j in range(nb)]
        self.u = [min(n_total, int(T_g * (j * step + 1) * sr)) for j in range(nb)]
        self.need = np.array(sorted(set(self.l) | set(self.u)))
        self.cs = {0: 0.0}
        self.pos, self.acc = 0, 0.0

    def feed(self, x):
        from scipy.signal import lfilter
        y = x
        for k, (b, a, g) in enumerate(self.stages):
            y, self.zi[k] = lfilter(b, a, y, zi=self.zi[k])
            y = g * y
        c = self.acc + np.cumsum(np.square(y))
        for n_ in self.need[(self.need > self.pos) & (self.need <= self.pos + len(y))]:
            self.cs[int(n_)] = float(c[int(n_) - self.pos - 1])
        self.acc = float(c[-1]) if len(c) else self.acc
        self.pos += len(y)

    def lufs(self):
        z = np.array([(self.cs[u] - self.cs[l]) / (self.T_g * self.sr) for l, u in zip(self.l, self.u)])
        with np.errstate(divide="ignore"):
            lj = -0.691 + 10.0 * np.log10(z)
        gated = z[lj >= -70.0]
        if not len(gated):
            return float("-inf")
        gamma_r = -0.691 + 10.0 * np.log10(np.mean(gated)) - 10.0
        z2 = z[(lj > gamma_r) & (lj > -70.0)]
        with np.errstate(divide="ignore"):
            return float(-0.691 + 10.0 * np.log10(np.nan_to_num(np.mean(z2)) if len(z2) else 0.0))


class _Hist:
    """a fixed-bin histogram of gain values in dB (0.01 dB bins, -60..0): percentiles of a whole narration without keeping it"""

    def __init__(self):
        self.h = np.zeros(6001, np.int64)
        self.n, self.lo = 0, 0.0

    def add(self, v):
        if len(v):
            self.h += np.bincount(np.clip(np.round(-v * 100).astype(np.int64), 0, 6000), minlength=6001)
            self.n += len(v)
            self.lo = min(self.lo, float(v.min()))

    def pct(self, q, total=None):
        """the q-th percentile from the deepest end, of these values or of `total` samples of which the rest sit above the bins
        (np.percentile(g, q) of a gain curve whose other samples are near 0)"""
        tot = self.n if total is None else total
        if not self.n or not tot:
            return 0.0
        c = np.cumsum(self.h[::-1])            # from the deepest bin
        rank = q / 100 * tot
        if rank > c[-1]:
            return 0.0
        return -float((6000 - int(np.searchsorted(c, rank))) / 100)


def level_mb_stream(src, dst, lufs=-16.0, ceil_db=-1.5, mid_thresh_rel=3.0, ratio=4.0, att=0.002, rel=0.06, chunk_s=60.0, ctx_s=3.0,
                    report=True):
    """level_mb in chunks (the whole-file way peaks at about 18 GB of memory on a 53-min narration):
    the same chain, the same numbers, a chunk of chunk_s seconds at a time with ctx_s of real audio on each side (the 2047-tap band
    split needs 21 ms, the detectors' smoothers forget their start within ~0.3 s), every chunk's start on the detectors' decimation
    grid (48 and 24 samples at 48 kHz), the loudness of the whole measured as pyloudnorm measures it (StreamLoudness). The band-split
    and compressed voice is kept in a temporary float64 file beside dst for the gain loop's passes. Peak memory: a few hundred MB."""
    import os
    import tempfile
    info = sf.info(src)
    sr, n = info.samplerate, info.frames
    if info.channels != 1:
        raise SystemExit("level_mb_stream: mono only")
    C, X = int(chunk_s * sr), int(ctx_s * sr)
    grid = max(1, sr // 1000) * 2  # a multiple of both decimation steps (sr // 1000 and sr // 2000)

    def spans():
        for a in range(0, n, C):
            b = min(n, a + C)
            yield a, b, max(0, (a - X) // grid * grid), min(n, b + X)

    src_f = sf.SoundFile(src)

    def read(a, b):
        src_f.seek(a)
        return src_f.read(b - a, dtype="float64")

    meter_in = StreamLoudness(sr, n)
    for a, b, _, _ in spans():
        meter_in.feed(read(a, b))
    g0 = 10 ** ((-20.0 - meter_in.lufs()) / 20)
    fd, tmp_name = tempfile.mkstemp(prefix="vlevel_", suffix=".f64", dir=str(Path(dst).parent))
    os.close(fd)
    tmp = Path(tmp_name)
    y0_meter = StreamLoudness(sr, n)
    hist_m, on_m = _Hist(), 0
    with open(tmp, "wb") as fy:
        for a, b, a0, b0 in spans():
            x0 = read(a0, b0) * g0
            lo, mid, hi = bands3(x0, sr)
            m2, gm = compress(mid, sr, -20.0 + mid_thresh_rel, ratio, 6.0, att, rel)
            y0 = (lo + m2 + hi)[a - a0:b - a0]
            gm = gm[a - a0:b - a0]
            hist_m.add(gm[gm < -0.5])
            on_m += int((gm < -0.5).sum())
            y0_meter.feed(y0)
            fy.write(np.ascontiguousarray(y0, dtype=np.float64).tobytes())
    y0m = np.memmap(tmp, dtype=np.float64, mode="r", shape=(n,))
    g = lufs - y0_meter.lufs()
    out_tmp = Path(str(dst) + ".part.wav")
    try:
        for _ in range(4):
            meter = StreamLoudness(sr, n)
            hist_l, on_l = _Hist(), 0
            with sf.SoundFile(str(out_tmp), "w", samplerate=sr, channels=1, subtype="PCM_16") as fo:
                for a, b, a0, b0 in spans():
                    y, gl = limit(np.array(y0m[a0:b0]) * 10 ** (g / 20), sr, ceil_db, 0.005, 0.04)
                    y, gl = y[a - a0:b - a0], gl[a - a0:b - a0]
                    meter.feed(y)
                    hist_l.add(gl[gl < -0.05])
                    on_l += int((gl < -0.5).sum())
                    fo.write(y)
            L = meter.lufs()
            if abs(L - lufs) < 0.05:
                break
            g += lufs - L
        os.replace(out_tmp, dst)
    finally:
        del y0m
        for p in (tmp, out_tmp):
            try:
                Path(p).unlink()
            except OSError:
                pass
    src_f.close()
    if report:
        print(f"  -> {L:.1f} LUFS; vowel band held back >0.5 dB {100 * on_m / n:.0f}% of the time (median "
              f"{hist_m.pct(50):.1f}, deepest {hist_m.lo:.1f} dB); final limiter >0.5 dB {100 * on_l / n:.1f}% (99.5th pct "
              f"{hist_l.pct(0.5, n):.1f}, deepest {hist_l.lo:.1f} dB) [streamed, {chunk_s:.0f}-s chunks]")
    return L


def tp_limit(x, sr, ceil_db=-1.5, look=0.005, rel=0.06):
    """true-peak limiter: the peaks found on a 4x oversampled copy (the ones between samples too, as Auphonic's), the gain computed and
    smoothed at the audio rate (look-ahead, then a 60-ms release: never inside one vibration of the voice)"""
    from scipy.signal import resample_poly
    up = np.abs(resample_poly(x, 4, 1))
    n = len(x)
    pk = np.maximum(np.abs(x), up[: 4 * n].reshape(-1, 4).max(axis=1) if len(up) >= 4 * n else np.abs(x))
    ceil = 10 ** (ceil_db / 20)
    need = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    w = 2 * int(look * sr) + 1
    p = w // 2
    need = np.lib.stride_tricks.sliding_window_view(np.pad(need, p, mode="edge"), w).min(axis=-1)
    gd = 20 * np.log10(need)
    step = max(1, sr // 2000)
    g_s = smooth_db(gd[::step], sr / step, 0.0005, rel)
    g_s = np.minimum(g_s, gd[::step][:len(g_s)])
    g = np.minimum(np.interp(np.arange(n), np.arange(0, n, step)[:len(g_s)], g_s), gd)
    return x * 10 ** (g / 20), g


def level_par(x, sr, lufs=-16.0, ceil_db=-1.5, wet_db=-6.0, thresh_rel=-6.0, ratio=6.0, multiband=False, report=True):
    """parallel compression: the untouched voice plus a heavily compressed copy blended under it (wet_db below the dry), so the
    original's attacks stay and the body comes up from below; optionally after D's vowel-band control; then the true-peak limiter"""
    meter = pyln.Meter(sr)
    x0 = x * 10 ** ((-20.0 - meter.integrated_loudness(x)) / 20)
    if multiband:
        lo, mid, hi = bands3(x0, sr)
        mid, _ = compress(mid, sr, -20.0, 4.0, 6.0, 0.002, 0.06)
        x0 = lo + mid + hi
    wet, gw = compress(x0, sr, -20.0 + thresh_rel, ratio, 6.0, 0.003, 0.08)
    wet = wet * 10 ** ((meter.integrated_loudness(x0) - meter.integrated_loudness(wet)) / 20)  # level-matched, then set under the dry
    y0 = x0 + wet * 10 ** (wet_db / 20)
    g = lufs - meter.integrated_loudness(y0)
    for _ in range(4):
        y, gl = tp_limit(y0 * 10 ** (g / 20), sr, ceil_db)
        L = meter.integrated_loudness(y)
        if abs(L - lufs) < 0.05:
            break
        g += lufs - L
    if report:
        print(f"  -> {L:.1f} LUFS; final true-peak limiter >0.5 dB {100 * (gl < -0.5).mean():.1f}% (99.5th pct {np.percentile(gl, 0.5):.1f}, "
              f"deepest {gl.min():.1f} dB)")
    return y


def old_chain(x, sr, lufs=-14.0, ceil_db=-1.5):
    """the plain way, for comparison: one gain to the target, then the 9-ms look-ahead limiter (tts.lookahead_limit)"""
    meter = pyln.Meter(sr)
    y = x * 10 ** ((lufs - meter.integrated_loudness(x)) / 20)
    a = np.abs(y) if y.ndim == 1 else np.abs(y).max(axis=1)
    ceil = 10 ** (ceil_db / 20)
    g = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    w = 2 * int(0.004 * sr) + 1
    p = w // 2
    g = np.lib.stride_tricks.sliding_window_view(np.pad(g, p, mode="edge"), w).min(axis=-1)
    c = np.cumsum(np.insert(np.pad(g, p, mode="edge"), 0, 0.0))
    g = (c[w:] - c[:-w]) / w
    gd = 20 * np.log10(np.maximum(g, 1e-9))
    print(f"  old chain: limiter {100 * (gd < -0.1).mean():.1f}% of the time, p99 {np.percentile(gd, 1):.1f} dB, deepest {gd.min():.1f} dB")
    return y * (g if y.ndim == 1 else g[:, None])


def main():
    src, dst = sys.argv[1], sys.argv[2]
    a = sys.argv[3:]
    opt = lambda k, d: float(a[a.index(k) + 1]) if k in a else d  # noqa: E731
    chain = a[a.index("--chain") + 1] if "--chain" in a else "gentle"
    if chain == "mb" and "--whole" not in a:
        # D in chunks: the whole-file way peaks at about 18 GB on a 53-min narration; the same numbers (null test in
        # standard/VOICE_LOCK.md); --whole runs the whole-file way (the test's reference)
        level_mb_stream(src, dst, opt("--lufs", -16.0), opt("--ceil", -2.0), opt("--thresh-rel", 0.0), opt("--ratio", 4.0))
        print("->", dst)
        return
    x, sr = sf.read(src, dtype="float64")
    if chain == "mb":  # chain D: the vowel band held back on its loud moments, the rest untouched, a light final limiter
        y = level_mb(x, sr, opt("--lufs", -16.0), opt("--ceil", -2.0), opt("--thresh-rel", 0.0), opt("--ratio", 4.0))
    else:
        y = level(x, sr, opt("--lufs", -14.0), opt("--ceil", -1.5), opt("--thresh-rel", -2.0), opt("--ratio", 2.5))
    sf.write(dst, y, sr, subtype="PCM_16")
    print("->", dst)


if __name__ == "__main__":
    main()
