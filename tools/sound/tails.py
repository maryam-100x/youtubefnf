"""A1 of the sound gate: every word end in the finished voice against the same word in the raw takes (the chain's input), so a word
end the clean-up cut is found before anyone listens. How the two voices are compared:
  - the video's files from its video.toml (any of them can be given, to run on an old state);
  - the raw voice is lined up per speech run (a stretch over -35 dB), not only per word: the chain cuts and mutes only in pauses, so
    a run's offset holds for its words; a word's point is inside the word (a short word's middle), so the 250 ms before a short word
    (a pause the chain cut) never lines up the wrong sound;
  - the raw voice is levelled to the final per run (a raw file at another level compares the same);
  - lost = frames where the take sounds (over -48 dB) and the final is 6 dB or more under it, 15 ms at least: a tail an earlier
    --fix laid back, still there in the final, is not lost;
  - pass 2 judges the loudest burst after the word's end (a 10-ms click before a 50-ms -27 dB release is judged on the release; a
    breath after a release the final still has is not a lost release);
  - one flag per word, with its time and the word.

Passes: 1. a consonant's release lost after the word's closure dip (the d of "world", the g of "big"): the take sounds where the final is
6 dB or more under it, 15-60 ms, at -38 dB or louder, match >= 0.9; 2. a word ending in a stop by its spelling: its release
burst (10 dB over the 3 frames before, over -48 dB) up to 200 ms after the final dies, lost; 3. a word ending in a fricative or stop:
its high, noisy tail (10-ms frames over -45 dB, spectral centre over 3.5 kHz) silent in the final (the f of "itself", the t of "first").
--fix lays the lost part back from the take (levels only, no time moves; 5-ms crossfade in, 15/20-ms fade out) and rewrites the file
in place with a backup (<name>_pretails.wav). A loss with no room (the next sound moved up) can't be laid back: re-time or re-take.

  EDIT tools/sound/tails.py <video> [--final F --raw R --words W] [--fix]
      [--show 158.3]  (the aligned 5-ms frames of final and take around the word ending nearest that time, for a hand check)"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

H5 = 0.005
D = 6   # matched at sr/6 (8 kHz, block means), then refined at full rate
HISS = ("f", "s", "v", "z", "x", "ce", "se", "sh", "th", "t", "d", "k", "p", "g", "ch", "ge", "c", "que")
# a final c or que is a k ("disc", "music", "unique"): a stop end like t/d/k/p/g/b
STOP_END = ("t", "d", "k", "p", "g", "b", "c", "que")
PUNCT = '.,!?;:"\'”“)('


def ncc(hay, seg):
    """normalised cross-correlation of seg along hay (FFT; the sliding energy by cumulative sums)"""
    n = len(seg)
    L = 1 << int(np.ceil(np.log2(len(hay) + n)))
    c = np.fft.irfft(np.fft.rfft(hay, L) * np.conj(np.fft.rfft(seg, L)), L)[:len(hay) - n + 1]
    cs = np.concatenate([[0.0], np.cumsum(hay ** 2)])
    e = np.sqrt(np.maximum(cs[n:] - cs[:-n], 0)) * np.sqrt((seg ** 2).sum()) + 1e-12
    return c / e


def dec(a):
    m = len(a) // D
    return a[:m * D].reshape(m, D).mean(1)


def corr(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12)) if len(a) and len(a) == len(b) else 0.0


def first_under(levels, bar=-50.0, run=2):
    for i in range(len(levels) - run + 1):
        if (levels[i:i + run] < bar).all():
            return i
    return None


def centre(a, sr):
    S = np.abs(np.fft.rfft(a * np.hanning(len(a)))) + 1e-12
    fq = np.fft.rfftfreq(len(a), 1 / sr)
    return float((fq * S).sum() / S.sum())


def cache_file(final, raw):
    """the run offsets of a (final, raw) pair, kept beside the gate's reports (<dj>/pipeline/gate_sound/.align/) by both files' size
    and time: the alignment takes a minute and A1, A2 and a --show all need it"""
    try:
        f, r = Path(final), Path(raw)
        k = hashlib.sha1(f"{f.resolve()}|{f.stat().st_size}|{f.stat().st_mtime_ns}|{r.resolve()}|{r.stat().st_size}|{r.stat().st_mtime_ns}"
                         .encode()).hexdigest()[:16]
        dj = next((q for q in f.resolve().parents if (q / "build").is_dir()), None)
        base = (dj / "pipeline" / "gate_sound") if dj else f.resolve().parent
        return base / ".align" / f"{k}.json"
    except OSError:
        return None


class Align:
    """The final voice lined up with the raw takes: per speech run of the final, its offset into the raw (raw index = final index +
    off) and the raw's gain to the final's level. Shared by A1 (tails) and A2 (mutescan: was a mute's sound cut from the take?)."""

    def __init__(self, final, raw, words):
        x, self.sr = sf.read(str(final), always_2d=True)
        p, sr2 = sf.read(str(raw), always_2d=True)
        if self.sr != sr2:
            raise SystemExit(f"sample rates differ: final {self.sr}, raw {sr2}")
        self.x, self.p = x, p
        # mono: the channel itself, not a mean's copy (no extra copy of a long narration; the same values)
        self.fm = x[:, 0] if x.shape[1] == 1 else x.mean(1)
        self.pm = p[:, 0] if p.shape[1] == 1 else p.mean(1)
        self.W = G.load_words(words) if words else []
        self.unsure = []
        sr = self.sr
        self.runs = self.speech_runs()
        ck = cache_file(final, raw)
        if ck and ck.exists():
            self.anchors = [tuple(a) for a in json.loads(ck.read_text(encoding="utf-8"))]
        else:
            self.anchors = []
            off = 0
            for a, b in self.runs:
                seg = self.fm[a:b]
                k, sc = self.match(seg, a + off - int(0.5 * sr), b + off + int(4.0 * sr))
                if k is None or sc < 0.85:   # a run the chain didn't make (another take in the raw file): anywhere within 90 s
                    k2, sc2 = self.match(seg, a + off - int(90 * sr), b + off + int(90 * sr))
                    if k2 is not None and sc2 > sc:
                        k, sc = k2, sc2
                if k is not None and sc >= 0.85:
                    off = k - a
                    self.anchors.append((int(a), int(b), int(off), float(sc), float(G.db(seg) - G.db(self.pm[k:k + (b - a)]))))
                else:
                    self.anchors.append((int(a), int(b), None, float(sc), 0.0))
            if ck:
                ck.parent.mkdir(parents=True, exist_ok=True)
                ck.write_text(json.dumps(self.anchors), encoding="utf-8")
        self.starts = np.array([a for a, *_ in self.anchors]) if self.anchors else np.zeros(0)

    def lv(self, a):
        return G.frame_db(a, self.sr, H5)

    def speech_runs(self, bar=-35.0, hop=0.01, min_len=0.10):
        """stretches of 10-ms frames over `bar` (the chain never cuts or mutes inside one): [(a, b)] in samples"""
        lv = G.frame_db(self.fm, self.sr, hop)
        h = int(hop * self.sr)
        runs, i, n = [], 0, len(lv)
        while i < n:
            if lv[i] > bar:
                j = i
                while j < n and lv[j] > bar:
                    j += 1
                if (j - i) * hop >= min_len:
                    runs.append((i * h, j * h))
                i = j
            else:
                i += 1
        return runs

    def match(self, seg, lo, hi):
        """best normalised cross-correlation of seg inside the raw [lo:hi]: (start, score)"""
        pm = self.pm
        lo, hi = max(0, lo), min(len(pm), hi)
        if hi - lo < len(seg) or len(seg) < 4 * D:
            return None, 0.0
        r = ncc(dec(pm[lo:hi]), dec(seg))
        k = lo + int(np.argmax(r)) * D
        a, b = max(0, k - 4 * D), min(len(pm), k + 4 * D + len(seg))
        r2 = ncc(pm[a:b], seg)
        k2 = int(np.argmax(r2))
        return a + k2, float(r2[k2])

    def anchor_at(self, A, lo=None):
        """the matched run that holds sample A (or ends at most 0.12 s before it, not before `lo`)"""
        sr = self.sr
        i = int(np.searchsorted(self.starts, A, side="right")) - 1
        best = None
        for j in (i, i - 1, i + 1):
            if 0 <= j < len(self.anchors):
                a, b, off, sc, g = self.anchors[j]
                if off is None:
                    continue
                if a - int(0.05 * sr) <= A <= b + int(0.12 * sr) and (lo is None or b >= lo):
                    if best is None or abs(b - A) < abs(best[1] - A):
                        best = self.anchors[j]
        return best

    def locate(self, w, record=True):
        """(A, pa, gain dB, score) for a word: the final's point 0.1 s before its end (inside the word: a short word's middle) and the
        same point in the raw voice; None if the word is silent there or not found (listed in .unsure)"""
        sr, fm, pm = self.sr, self.fm, self.pm
        A = int(max(w["end"] - 0.1, w["start"] + 0.5 * (w["end"] - w["start"])) * sr)
        a = A - int(0.25 * sr)
        if a < 0 or A + int(0.5 * sr) > len(fm):
            return None
        seg = fm[a:A]
        if self.lv(seg).max() < -35:
            return None
        if self.lv(fm[A - int(0.03 * sr):A + int(0.01 * sr)]).max() < -38:
            # no sound at that point (a stop's closure, or Whisper's times in a pause: a short "and" can sound 5 ms after its
            # "end"): back to the word's last sounding 5 ms (over -35 dB), else it can't be held against the take
            h5 = int(H5 * sr)
            k = A
            while k - h5 > int((w["start"] + 0.01) * sr) and G.db(fm[k - h5:k]) <= -35:
                k -= h5
            if G.db(fm[k - h5:k]) <= -35:
                if record:
                    self.unsure.append((round(w["end"], 2), w["w"], "silent"))
                return None
            A = k
            a = A - int(0.25 * sr)
            if a < 0:
                return None
            seg = fm[a:A]
        # the word's own sound: never across a cut's digital silence before it (a short word right after a cut, 0.06 s over -35 dB
        # with no run of its own, would take the run before it, whose 0.25-s window holds mostly the word before and lines up
        # elsewhere: its decay would read as a 45-ms "lost" end, NO ROOM)
        own = max(a, int(w["start"] * sr))
        zs = np.flatnonzero(np.abs(fm[own:A]) > 1e-6)
        if len(zs):
            gaps = np.flatnonzero(np.diff(zs) > int(0.01 * sr))
            if len(gaps):
                own += int(zs[gaps[-1] + 1])
            elif zs[0] > int(0.01 * sr):
                own += int(zs[0])
        if own > a and A - own >= int(0.06 * sr):    # after a cut: the word is lined up on its own sound only
            a, seg = own, fm[own:A]
        an = self.anchor_at(A, lo=int(w["start"] * sr))
        if an is not None:
            off, g = an[2], an[4]
            v0 = max(a, an[0])          # checked on the word's own run only
            if A - v0 < int(0.03 * sr):
                v0 = max(0, A - int(0.03 * sr))
            k = v0 + off
            if 0 <= k and k + (A - v0) <= len(pm):
                sc = corr(fm[v0:A], pm[k:k + (A - v0)])
                if sc >= 0.8:           # a word the run didn't line up (a cut inside the run) is matched alone below
                    return A, A + off, g, sc
        base = an[2] if an else 0
        k, sc = self.match(seg, a + base - int(1.0 * sr), a + base + int(4.0 * sr))
        if k is None or sc < 0.8:
            k2, sc2 = self.match(seg, a - int(90 * sr), a + int(90 * sr))
            if k2 is not None and sc2 > sc:
                k, sc = k2, sc2
        if k is None or sc < 0.8:
            if record:
                self.unsure.append((round(w["end"], 2), w["w"], round(sc, 2)))
            return None
        return A, k + (A - a), G.db(seg) - G.db(pm[k:k + (A - a)]), sc

    def raw_at(self, s, near=None):
        """the raw sample that lines up with final sample s (the run that holds s or ends just before it), and the gain; None if unknown"""
        an = self.anchor_at(s if near is None else near)
        if an is None:
            return None
        return s + an[2], an[4]


class WinPair:
    """The final and the take (the layout) around one stretch, read in windows (a short --span through Align would read both whole
    narrations as float64, gigabytes for a long video): the speech run at or before t0 in the final is matched in the take near
    where the beats put it (build/beats.json against beats_laid.json, +-8 s; Align.match's two-step correlation), which gives the
    offset (take sample = final sample + off) and the gain."""

    def __init__(self, P, t0, t1=None, before=2.0, after=1.0):
        t1 = t0 if t1 is None else t1
        self.final, raw = Path(P["final"]), Path(P["raw"])
        info = sf.info(str(self.final))
        self.sr = sr = info.samplerate
        self.f0 = max(0, int((t0 - before) * sr))
        f1 = min(info.frames, int((t1 + after) * sr))
        self.fm = sf.read(str(self.final), start=self.f0, stop=f1, dtype="float64", always_2d=True)[0][:, 0]
        # the speech run at or before t0: 10-ms frames over -35 dB, 0.1 s or more
        lv = G.frame_db(self.fm, sr, 0.01)
        h = int(0.01 * sr)
        j = min(len(lv) - 1, int((t0 * sr - self.f0) / h))
        while True:          # the nearest run of 0.1 s or more at or before t0 (a word's last 50 ms after its closure is too short)
            while j > 0 and lv[j] <= -35:
                j -= 1
            b = j
            while j > 0 and lv[j - 1] > -35:
                j -= 1
            if (b - j + 1) * 0.01 >= 0.1:
                break
            if j <= 0:
                raise SystemExit(f"no speech run of 0.1 s at or before {t0:.3f} s in the final's window")
            j -= 1
        self.run = (self.f0 + j * h, self.f0 + (b + 1) * h)
        seg = self.fm[j * h:(b + 1) * h]
        est = self.raw_estimate(P, t0)
        self.p0 = max(0, int((est - before - 8.0) * sr))
        self.pm = sf.read(str(raw), start=self.p0, stop=int((est + (t1 - t0) + after + 8.0) * sr), dtype="float64",
                          always_2d=True)[0][:, 0]
        r = ncc(dec(self.pm), dec(seg))
        k = int(np.argmax(r)) * D
        lo, hi = max(0, k - 4 * D), min(len(self.pm), k + 4 * D + len(seg))
        r2 = ncc(self.pm[lo:hi], seg)
        k2 = int(np.argmax(r2))
        self.sc = float(r2[k2])
        if self.sc < 0.85:
            raise SystemExit(f"the final's run {self.run[0] / sr:.2f}-{self.run[1] / sr:.2f} s matches the take at {self.sc:.2f} only: "
                             "no offset to lay back by")
        self.off = (self.p0 + lo + k2) - self.run[0]
        self.g = float(G.db(seg) - G.db(self.pm[lo + k2:lo + k2 + len(seg)]))

    @staticmethod
    def raw_estimate(P, t):
        """where the beats put final time t in the take: its beat's start in beats_laid.json plus its time into the beat"""
        fb = json.loads(Path(P["beats"]).read_text(encoding="utf-8"))["beats"]
        lb = {b["id"]: b for b in json.loads((Path(P["beats"]).with_name("beats_laid.json")).read_text(encoding="utf-8"))["beats"]}
        b = next((b for b in fb if b["start"] <= t < b["end"]), None) or min(fb, key=lambda b: abs(b["start"] - t))
        return lb[b["id"]]["start"] + (t - b["start"]) if b["id"] in lb else t

    def f(self, a, b):
        return self.fm[a - self.f0:b - self.f0]

    def p(self, a, b):
        return self.pm[a - self.p0:b - self.p0]

    def show(self, t0, t1, label):
        sr, h = self.sr, int(H5 * self.sr)
        a = int(t0 * sr)
        n = int((t1 - t0) / H5)
        lf, lp = G.frame_db(self.f(a, a + n * h), sr, H5), G.frame_db(self.p(a + self.off, a + self.off + n * h), sr, H5) + self.g
        print(f"{label + ': ' if label else ''}final {t0:.3f}-{t1:.3f} s against the take at {(a + self.off) / sr:.3f} s (offset "
              f"{self.off / sr:+.3f} s, gain {self.g:+.1f} dB, match {self.sc:.3f}); 5-ms frames:")
        for i in range(min(len(lf), len(lp))):
            print(f"  {t0 + i * H5:8.3f}  final {lf[i]:6.1f}  raw {lp[i]:6.1f}  {'LOST' if lp[i] > -48 and lf[i] < lp[i] - 6 else ''}")

    def lay_back(self, t0, t1, fo_s=0.015):
        """lay_back()'s sum on the windows (levelled by the 0.25 s before t0, 5-ms crossfade in, fo_s fade out), written back into the
        file in place: only [t0 - 5 ms, t1) changes; the backup is a file copy"""
        sr = self.sr
        A = int(t0 * sr)
        step = int(H5 * sr)
        n = int(round((t1 - t0) / H5))
        pa = A + self.off
        a0 = A - int(0.25 * sr)
        gl = np.sqrt((self.f(a0, A) ** 2).mean() / ((self.p(pa - (A - a0), pa) ** 2).mean() + 1e-12))
        cf, fo = int(0.005 * sr), int(fo_s * sr)
        st, en = A - cf, A + n * step
        src = self.p(pa - cf, pa + n * step) * gl
        y = self.f(st, en).copy()
        w_in = np.ones(en - st)
        w_in[:cf] = np.linspace(0, 1, cf)
        w_out = np.ones(en - st)
        w_out[-fo:] = np.linspace(1, 0, fo)
        y = (y * (1 - w_in) + src * w_in) * w_out
        backup = self.final.with_name(self.final.stem + "_prespan.wav")
        shutil.copy2(self.final, backup)
        with sf.SoundFile(str(self.final), "r+") as fh:
            fh.seek(st)
            fh.write(y)        # the file's own subtype (PCM_16): the same float-to-int as sf.write
        return backup


def show(al, t):
    sr, h = al.sr, int(H5 * al.sr)
    w = min(al.W, key=lambda w: abs(w["end"] - t))
    L = al.locate(w, record=False)
    if not L:
        print(f"{w['w']!r} at {w['end']:.2f}: not found in the raw voice")
        return
    A, pa, g, sc = L
    N = int(0.35 * sr)
    lf, lp = al.lv(al.fm[A - 20 * h:A + N]), al.lv(al.pm[pa - 20 * h:pa + N]) + g
    print(f"{w['w']!r} end {w['end']:.3f} (A={A / sr:.3f}, raw {pa / sr:.3f}, gain {g:+.1f} dB, match {sc:.3f}); 5-ms frames from A-0.1 s:")
    for i in range(len(lf)):
        tt = (A + (i - 20) * h) / sr
        mark = " <- end" if abs(tt - w["end"]) < H5 / 2 + 1e-9 else ""
        print(f"  {tt:8.3f}  final {lf[i]:6.1f}  raw {lp[i]:6.1f}  {'LOST' if lp[i] > -48 and lf[i] < lp[i] - 6 else ''}{mark}")


def lay_back(al, y, A, pa, i0, i1, step, fo_s):
    """the take's [i0, i1) frames (of `step` samples from A / pa) into y, levelled, 5-ms crossfade in, fo_s fade out"""
    sr = al.sr
    a = A - int(0.25 * sr)
    k = pa - (A - a)
    gl = np.sqrt((al.fm[a:A] ** 2).mean() / ((al.pm[k:pa] ** 2).mean() + 1e-12))
    cf, fo = int(0.005 * sr), int(fo_s * sr)
    st, en = A + i0 * step - cf, A + i1 * step
    src = al.p[pa + i0 * step - cf:pa + i1 * step] * gl
    w_in = np.ones(en - st)
    w_in[:cf] = np.linspace(0, 1, cf)
    w_out = np.ones(en - st)
    w_out[-fo:] = np.linspace(1, 0, fo)
    y[st:en] = (y[st:en] * (1 - w_in)[:, None] + src * w_in[:, None]) * w_out[:, None]


def next_onset(al, W, wi, pa, step):
    """frames (of `step` samples) from the raw point pa to where the next word starts in the raw voice (its own run's offset: the
    chain may have moved it up in the final), 10 ms before it; a large number if unknown. So the loudest "burst" after a short
    "And"/"But" is never the next word's onset in the take"""
    if wi + 1 >= len(W):
        return 10 ** 6
    s = int(W[wi + 1]["start"] * al.sr)
    m = al.raw_at(s, near=s + int(0.03 * al.sr))
    if m is None:
        return 10 ** 6
    return max(0, (m[0] - pa) // step - max(1, int(0.01 * al.sr) // step))


def stop_burst(lp, lf, e0, e1):
    """Pass 2's release: the take's sound after a stop-ending word (5-ms levels from the word's end, e0..e1: up to 200 ms after the
    final dies and before the next word) cut into segments over -48 dB (one-frame dips joined). A segment is a release when it jumps
    out of quiet (its peak 10 dB over the 3 frames before it) and dies like one: under its running peak - 12 dB within 60 ms (two frames
    in a row; a voiced d's two pulses stay one release, e.g. -29, -34, -44, -38, -30 dB). A segment that holds within 12 dB of its peak
    for more than 60 ms after it is a breath, muted on purpose (inhales after a word: 75-150 ms at -28..-46 dB). A release is there when
    the final keeps its loudest frame within 3 dB and half its core (frames within 9 dB of the peak) within 6 dB (a release laid back
    by --fix); otherwise it is lost (the peak 5.7 dB down and the rest muted, or a -27 dB release 35 ms after a 10-ms click, all gone).
    -> (lost frames, i0, i1) of the release with the most lost frames, or None"""
    segs, i = [], e0
    while i < e1:
        if lp[i] > -48:
            j = i
            while j < e1 and (lp[j] > -48 or (j + 1 < e1 and lp[j + 1] > -48)):
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    best = None
    for a_, b_ in segs:
        pre = float(lp[max(0, a_ - 3):a_].min()) if a_ > 0 else -120.0
        pk, e = lp[a_], a_ + 1
        while e < min(b_, a_ + 12):
            pk = max(pk, lp[e])
            if lp[e] <= pk - 12 and (e + 1 >= b_ or lp[e + 1] <= pk - 12):
                break
            e += 1
        k = a_ + int(np.argmax(lp[a_:e]))
        if lp[k] - pre < 10:
            continue
        held = k + 1
        while held < len(lp) and held < k + 30 and lp[held] > lp[k] - 12 and lp[held] > -50:
            held += 1
        if held - k > 12:
            continue
        core = (lp[a_:e] >= lp[k] - 9)
        kept = (lf[a_:e] >= lp[a_:e] - 6)
        if lf[k] >= lp[k] - 3 and kept[core].mean() >= 0.5:
            continue
        r0 = max(0, a_ - 1)
        nl = int(((lp[r0:e] > -48) & (lf[r0:e] < lp[r0:e] - 6)).sum())
        if nl >= 3 and (best is None or nl > best[0]):
            best = (nl, r0, e)
    return best


ONLY_KEYS = None      # --fix --keys: lay back only these flags (so a muted inhale A1 reads as a lost hiss stays muted)


def keep_key(word, end):
    return ONLY_KEYS is None or G.wkey(word, end) in ONLY_KEYS


def scan(al, fix=False):
    """-> (cut, noroom, hiss, y): the lost word ends (dicts with t, word, wi, ms, loud, kind) and the voice with them laid back"""
    sr, fm, pm, W = al.sr, al.fm, al.pm, al.W
    h = int(H5 * sr)
    N = int(0.6 * sr)
    y = al.x.copy() if fix else al.x          # a check alone writes nothing: no copy of the narration
    cut, noroom, hiss = [], [], []
    for wi, w in enumerate(W):
        word = w["w"]
        L = al.locate(w)
        if not L:
            continue
        A, pa, g, sc = L
        lf, lp = al.lv(fm[A:A + N]), al.lv(pm[pa:pa + N]) + g
        lim = next_onset(al, W, wi, pa, h)               # nothing of the next word counts as this word's end
        f_end = first_under(lf)
        if f_end is None:                              # the final runs straight into the next word: nothing was cut here
            continue
        last = min(len(lf) - 2, int(round((w["end"] + 0.08 - (A / sr)) / H5)), lim)
        i0 = next((i for i in range(max(0, f_end - 6), last) if lp[i] > -45 and lf[i] < lp[i] - 6), None)
        ok = False
        if i0 is not None:
            pk, j = lp[i0], i0 + 1
            while j < min(len(lp) - 1, i0 + 20):
                pk = max(pk, lp[j])
                if (lp[j] < -50 and lp[j + 1] < -50) or (lp[j] <= lp[j - 1] and lp[j] < lp[j + 1] and lp[j] <= pk - 12):
                    break
                j += 1
            lost = j - i0
            ok = 3 <= lost <= 12 and sc >= 0.9 and lp[i0:j].max() >= -38
            if ok:
                f_end, p_end, kind = i0, j, "release"
        if not ok:
            stem = word.lower().strip(PUNCT)
            if sc < 0.9 or not stem or not stem.endswith(STOP_END) or stem.endswith("ng"):
                continue                                 # "-ng" is a nasal: no release ("singing.", "building.")

            best = stop_burst(lp, lf, max(3, f_end, int(round((w["end"] - 0.01 - A / sr) / H5))), min(len(lp) - 1, f_end + 40, lim))
            if best is None:
                continue
            f_end, p_end, kind = best[1], best[2], "stop burst"
            lost = p_end - f_end
        if (lf[f_end:p_end] > -60).sum() > 2 and lost <= 4:
            continue
        sl = slice(f_end, p_end)
        nlost = int(((lp[sl] > -48) & (lf[sl] < lp[sl] - 6)).sum())
        if nlost < 3:          # 10 ms or less: a fade's edge, or the sound is still there (laid back before)
            continue
        item = {"t": (A + f_end * h) / sr, "word": word, "wi": wi, "ms": nlost * 5, "loud": float(lp[sl].max()), "kind": kind}
        # no room: another sound sits in the final where the take's end was (the final 6 dB or more over the take, over -40 dB: the
        # next word moved up by a cut pause); the start of the lost end itself, still in the final, leaves room
        other = (lf[f_end:p_end + 2] > lp[f_end:p_end + 2] + 6) & (lf[f_end:p_end + 2] > -40)
        if other.sum() >= 2:
            noroom.append(item)
            continue
        cut.append(item)
        if fix and keep_key(word, W[wi]["end"]):   # the 15-ms fade out runs past the lost part, so all of it comes back
            lay_back(al, y, A, pa, f_end, min(p_end + 3, len(lp)), h, 0.015)

    # pass 3: the hiss of a fricative or stop end
    ym = y[:, 0] if y.shape[1] == 1 else y.mean(1)
    q = int(0.01 * sr)
    for wi, w in enumerate(W):
        word = w["w"]
        if not word.lower().strip(PUNCT).endswith(HISS):
            continue
        L = al.locate(w, record=False)
        if not L:
            continue
        A, pa, g, sc = L
        if sc < 0.9:
            continue
        n = int(0.45 * sr) // q
        if A + n * q > len(ym) or pa + n * q > len(pm):
            continue
        lf10 = [G.db(ym[A + i * q:A + (i + 1) * q]) for i in range(n)]
        lp10 = [G.db(pm[pa + i * q:pa + (i + 1) * q]) + g for i in range(n)]
        dead = next((i for i in range(n - 1) if lf10[i] < -50 and lf10[i + 1] < -50), None)
        if dead is None:
            continue
        lim = next_onset(al, W, wi, pa, q)
        runh = [i for i in range(dead, min(n, dead + 35, lim)) if lp10[i] > -45 and lf10[i] < -60 and centre(pm[pa + i * q:pa + (i + 1) * q], sr) > 3500]
        if not runh or runh[0] > dead + 15:
            continue
        i0 = i1 = runh[0]
        while i1 + 1 < min(n, lim) and i1 + 1 - i0 < 20 and lp10[i1 + 1] > -48 and lf10[i1 + 1] < -60 and centre(pm[pa + (i1 + 1) * q:pa + (i1 + 2) * q], sr) > 2500:
            i1 += 1
        if i1 - i0 < 1:
            continue
        t = (A + i0 * q) / sr
        if hiss and abs(hiss[-1]["t"] - t) < 0.015:     # "of it,": the same hiss found from the word before; it is the later word's
            hiss.pop()
        hiss.append({"t": t, "word": word, "wi": wi, "ms": (i1 - i0 + 1) * 10, "loud": float(max(lp10[i0:i1 + 1])), "kind": "hiss"})
        if fix and keep_key(word, W[wi]["end"]):
            lay_back(al, y, A, pa, i0 - 1, min(i1 + 3, n), q, 0.02)
    return cut, noroom, hiss, y


def run(P, fix=False, quiet=False, al=None):
    """A1 on the final voice; with fix, the lost parts laid back and the voice checked again (up to 3 rounds: a laid-back release can
    show the rest of a longer one), the old file kept once as <name>_pretails.wav"""
    al = al or Align(P["final"], P["raw"], P["words"])
    first, rounds, backup = None, 0, None
    while True:
        cut, noroom, hiss, y = scan(al, fix=fix)
        flags = make_flags(al, cut, noroom, hiss, fix)
        if first is None:
            first = flags
        rounds += 1
        if not (fix and (cut or hiss)) or rounds > 3:
            break
        info = sf.info(str(P["final"]))
        if backup is None:
            backup = P["final"].with_name(P["final"].stem + "_pretails.wav")
            shutil.copy2(P["final"], backup)
        sf.write(str(P["final"]), y, al.sr, subtype=info.subtype)
        al = Align(P["final"], P["raw"], P["words"])
    nanch = sum(1 for a in al.anchors if a[2] is not None)
    res = {"check": "A1", "final": str(P["final"]), "raw": str(P["raw"]), "words": len(al.W), "runs": len(al.anchors), "runs_matched": nanch,
           "unsure": al.unsure, "flags": flags if fix else first, "fixed": first if (fix and backup) else [], "rounds": rounds}
    if backup:
        res["backup"] = str(backup)
    if not quiet:
        if fix and backup:
            print(f"A1 tails --fix: {len(first)} lost word ends laid back in {rounds - 1} round(s) (backup {backup}); "
                  f"{len(flags)} still lost after it")
            G.print_flags({"flags": first})
            if flags:
                print("  still lost:")
                G.print_flags({"flags": flags})
        else:
            print(f"A1 tails: {len(al.W)} words, {nanch}/{len(al.anchors)} speech runs found in the raw voice, {len(al.unsure)} words not "
                  f"found (match < 0.8); {len(res['flags'])} lost word ends")
            G.print_flags(res)
        if al.unsure:
            print(f"  not found ({len(al.unsure)}):", al.unsure[:20], "..." if len(al.unsure) > 20 else "")
    return res


def make_flags(al, cut, noroom, hiss, fix):
    W = al.W
    byw = {}
    for kind, items in (("cut", cut), ("hiss", hiss), ("noroom", noroom)):
        for it in items:
            byw.setdefault(it["wi"], []).append((kind, it))
    flags = []
    for wi, items in sorted(byw.items()):
        word = items[0][1]["word"]
        parts = []
        for kind, it in items:
            if kind == "cut":
                parts.append(f"{it['kind']} lost: {it['ms']} ms of the take, loudest {it['loud']:.1f} dB")
            elif kind == "hiss":
                parts.append(f"end hiss lost: {it['ms']} ms of the take, loudest {it['loud']:.1f} dB")
            else:
                parts.append(f"{it['kind']} lost with NO ROOM to lay it back ({it['ms']} ms, {it['loud']:.1f} dB): re-time or re-take")
        flags.append(G.flag("A1", G.wkey(word, W[wi]["end"]), min(it["t"] for _, it in items), word, "word end cut: " + "; ".join(parts),
                            ms=max(it["ms"] for _, it in items), word_end=W[wi]["end"]))
    return flags


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, when="--fix")  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--fix", action="store_true", help="lay the lost parts back (in place, backup kept)")
    ap.add_argument("--show", type=float, help="print the aligned frames of the word ending nearest this time")
    ap.add_argument("--keys", help="with --fix: a comma list of the gate's A1 keys to lay back (the others are left as they are)")
    ap.add_argument("--span", nargs=2, type=float, metavar=("T0", "T1"), help="with --fix: lay back exactly these seconds of the final "
                    "from the take, by the speech run's own offset (5-ms crossfade in, 15-ms fade out): a release a chain fade took "
                    "that the scan's rules don't read; the frames printed before and after")
    a = ap.parse_args()
    global ONLY_KEYS
    if a.keys:
        ONLY_KEYS = set(a.keys.split(","))
    P = G.paths_from(a)
    if a.fix and a.span:
        wp = WinPair(P, a.span[0], a.span[1])
        wp.show(a.span[0] - 0.1, a.span[1] + 0.1, "before")
        backup = wp.lay_back(a.span[0], a.span[1])
        print(f"laid back {a.span[0]:.3f}-{a.span[1]:.3f} s from the take (offset {wp.off / wp.sr:+.3f} s, match {wp.sc:.3f}; "
              f"backup {backup.name}; only those samples written)")
        WinPair(P, a.span[0], a.span[1]).show(a.span[0] - 0.1, a.span[1] + 0.1, "after")
        return
    if a.show is not None:
        WinPair(P, a.show).show(a.show - 0.15, a.show + 0.35, "")
        return
    res = run(P, fix=a.fix)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
