"""Rebuild a spliced narration from the untouched ElevenLabs takes, slot by slot, at the same timing, so a narration that went through
a squashing chain (~9 dB off the loud vowels: it sounds artificially gained up) is brought to loudness from the clean raw takes through
chain D (voice_level.py --chain mb) instead. For every beat of narration_final.wav (+ .beats.json):
- a line from the first build: its section take (build/voice/cache) cut again with the build's own code (raw_cut.py), at [tts] tempo:
  it lands on its slot at 0 samples, waveform correlation ~0.9 (the rest is the old squash);
- a re-voiced line: each of its takes (build/voice/patch/<beat>_<k>.wav, raw 1.0x) through voice_patch.py's own steps (edges,
  tighten_pauses, tempo), without its limiter;
the candidate whose waveform matches the slot best is placed where it matches; one that only matches in two parts (a line voice_cut.py
shortened) is placed in two parts, split at the slot's longest pause. Each beat is set 14 dB under the slot's voiced level (the beats keep
their balance, the whole sits near -28 LUFS, nothing near full scale, nothing limited). A slot nothing matches keeps its old audio, turned
down the same (listed). Same length, same boundaries: the word timings and the picture stay valid. Then dj tts with [audio]
voice_chain = "multiband" brings it to loudness through D.

  EDIT tools/sound/raw_rebuild.py <video media folder> <spliced narration_final.wav> [--report report.tsv] [--min-corr 0.8]
      [--first-beats <beats.json>]
  (e.g. VIDEOS/012-city-at-night voice_backup/raw_rebuild/narration_final_before.wav: its .beats.json beside it; a relative narration
  path is read inside the video's media folder; writes <video media folder>/narration_final.wav and copies the .beats.json next to it)
  --first-beats  the beats.json of the first build, whose lines are re-cut from the section takes in build/voice/cache (default: the
                 video's build/beats.json; give a backup of the first build's when lines were re-voiced since)"""
import difflib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE.parent / "voice"))   # voice_patch.py
sys.path.insert(0, str(HERE.parent))             # tools/: the dj package
sys.path.insert(0, str(HERE))
from paths import VIDEOS_REPO  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.core import load_config, read_wav  # noqa: E402
from dj.tts import all_tempo, tighten_pauses  # noqa: E402
from raw_cut import cut_section  # noqa: E402
from voice_patch import edges  # noqa: E402

SR = 48000
DOWN_DB = 14.0


def xcorr(slot, c, max_lag):
    """best lag of c inside slot (|lag| <= max_lag samples) and the normalised waveform correlation over the overlap"""
    n = len(slot) + len(c)
    f = np.fft.irfft(np.fft.rfft(slot, n) * np.conj(np.fft.rfft(c, n)), n)
    pos, neg = min(max_lag, len(slot) - 1), min(max_lag, len(c) - 1)  # beyond these the circular result wraps into the other sign
    lags = np.concatenate([np.arange(0, pos + 1), np.arange(-neg, 0)])
    vals = np.concatenate([f[:pos + 1], f[n - neg:]])
    lag = int(lags[int(np.argmax(vals))])
    s0, s1 = max(0, lag), min(len(slot), lag + len(c))
    if s1 - s0 < SR // 20:
        return lag, -1.0
    u, v = slot[s0:s1], c[s0 - lag:s1 - lag]
    return lag, float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))


def place(slot_len, c, lag):
    out = np.zeros(slot_len)
    s0, s1 = max(0, lag), min(slot_len, lag + len(c))
    if s1 > s0:
        out[s0:s1] = c[s0 - lag:s1 - lag]
    return out


def rms_voiced(x):
    x = np.asarray(x, np.float64)
    h = SR // 200
    n = len(x) // h
    if n == 0:
        return 1e-9
    b = np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(axis=1))
    keep = b > b.max() * 10 ** (-30 / 20)
    return float(np.sqrt((b[keep] ** 2).mean())) if keep.any() else 1e-9


def longest_pause(x):
    h = SR // 200
    n = len(x) // h
    b = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(axis=1)) + 1e-9)
    quiet = b < b.max() - 40
    best, cur, start = (0, 0), 0, 0
    for i, q in enumerate(quiet):
        if q:
            if cur == 0:
                start = i
            cur += 1
            if cur > best[1] - best[0] and 0.2 * n < start < 0.8 * n:
                best = (start, start + cur)
        else:
            cur = 0
    return (best[0] + best[1]) // 2 * h if best[1] > best[0] else len(x) // 2


def pauses(x, n_max=8):
    """the middles of the slot's pauses (40 dB under its loudest 5-ms block, at least 60 ms), longest first"""
    h = SR // 200
    n = len(x) // h
    b = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(axis=1)) + 1e-9)
    quiet = b < b.max() - 40
    runs, start = [], None
    for i, q in enumerate(list(quiet) + [False]):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if i - start >= 12 and start > 0 and i < n:
                runs.append((i - start, (start + i) // 2 * h))
            start = None
    return [m for _, m in sorted(runs, reverse=True)[:n_max]]


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    root = Path(sys.argv[1])
    base = root / sys.argv[2] if not Path(sys.argv[2]).is_absolute() else Path(sys.argv[2])
    a = sys.argv[3:]
    min_corr = float(a[a.index("--min-corr") + 1]) if "--min-corr" in a else 0.8
    rep = Path(a[a.index("--report") + 1]) if "--report" in a else None
    video = VIDEOS_REPO / root.name
    cfg = load_config(None, video_config(str(video)))
    tcfg = cfg["tts"]
    tempo = float(tcfg.get("tempo", 1.0))
    y, sr = sf.read(base, dtype="int16")
    assert sr == SR and y.ndim == 1
    meta = json.loads(base.with_name(base.stem + ".beats.json").read_text(encoding="utf-8"))
    now_text = {b["id"]: b["voice"].strip() for b in json.loads((root / "build" / "beats.json").read_text(encoding="utf-8"))["beats"]
                if b.get("voice")}
    # the first build's lines, section by section, re-cut exactly (only lines whose text hasn't changed since)
    first = Path(a[a.index("--first-beats") + 1]) if "--first-beats" in a else root / "build" / "beats.json"
    v1 = json.loads(first.read_text(encoding="utf-8"))["beats"]
    v1_texts = [(b["id"], b["voice"].strip()) for b in v1 if b.get("voice") and not b.get("hold")]
    recut, fuzzy = {}, []
    for aj in sorted((root / "build" / "voice" / "cache").glob("sec_*.align.json")):
        m = json.loads(aj.read_text(encoding="utf-8"))
        t = m.get("text") or "".join(m["alignment"]["characters"])
        for i in range(len(v1_texts)):
            if not t.startswith(v1_texts[i][1]):
                continue
            j, acc = i, v1_texts[i][1]
            while acc != t and j + 1 < len(v1_texts) and t.startswith(acc + " " + v1_texts[j + 1][1]):
                j += 1
                acc = acc + " " + v1_texts[j][1]
            if acc == t:
                ids = [x[0] for x in v1_texts[i:j + 1]]
                clips = cut_section([x[1] for x in v1_texts[i:j + 1]], m, aj.with_name(aj.name.replace(".align.json", ".wav")), tcfg)
                clips = all_tempo({"tempo": tempo}, [{"voice": "x"}] * len(clips), clips)
                for bid, c, (_, txt) in zip(ids, clips, v1_texts[i:j + 1]):
                    recut[bid] = (c.astype(np.float64), txt)
                break
        else:
            fuzzy.append((t, m, aj))
    # sections voiced from an older wording of their lines (the script was touched up after the voice: "in the 1990s" -> "in the
    # nineties"): the lines' starts found in the section's own text by a fuzzy alignment, the section cut there with the build's code; whether a
    # cut really is that line's audio is decided below by the waveform match, as for every other candidate
    J, starts = "", []
    for bid, txt in v1_texts:
        starts.append((bid, len(J), txt))
        J += txt + " "
    for t, m, aj in fuzzy:
        sm = difflib.SequenceMatcher(None, J, t, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size >= 12]
        if not blocks or sum(b.size for b in blocks) < 0.6 * len(t):
            continue
        j0, j1 = blocks[0].a, blocks[-1].a + blocks[-1].size
        def to_t(pos):  # a position in J -> the same place in t, through the nearest matching block
            for b in blocks:
                if b.a <= pos < b.a + b.size:
                    return b.b + (pos - b.a)
            nb = min(blocks, key=lambda b: min(abs(pos - b.a), abs(pos - (b.a + b.size))))
            return nb.b + (0 if pos < nb.a else nb.size)
        inside = [(bid, p, txt) for bid, p, txt in starts if j0 - 3 <= p < j1 - 10]
        if not inside:
            continue
        cuts = sorted({0} | {to_t(p) for _, p, _ in inside[1:]})
        cuts = [c if c == 0 or t[c - 1] == " " else (t.rfind(" ", 0, c) + 1) for c in cuts]
        if len(set(cuts)) != len(cuts) or any(c <= 0 for c in cuts[1:]):
            continue
        parts = [t[c0:c1].strip() for c0, c1 in zip(cuts, cuts[1:] + [len(t)])]
        if " ".join(parts) != t or any(not q for q in parts):
            continue
        try:
            clips = cut_section(parts, m, aj.with_name(aj.name.replace(".align.json", ".wav")), tcfg)
        except Exception:
            continue
        clips = all_tempo({"tempo": tempo}, [{"voice": "x"}] * len(clips), clips)
        for (bid, _, txt), c in zip(inside, clips):
            if bid not in recut:
                recut[bid] = (c.astype(np.float64), txt)
    patch = root / "build" / "voice" / "patch"
    out = np.zeros(len(y), np.float64)
    rows, kept = [], []
    for bt in meta["beats"]:
        bid, s, e = bt["id"], bt["a"], bt["b"]
        slot = y[s:e].astype(np.float64)
        if not len(slot) or np.abs(slot).max() < 50:
            out[s:e] = slot * 10 ** (-DOWN_DB / 20)
            continue
        cands = []
        if bid in recut:  # the match below decides whether it is this slot's audio
            cands.append(("first build, re-cut", recut[bid][0]))
        for f in sorted(patch.glob(f"{bid}_*.wav")):
            k = f.stem[len(bid) + 1:]
            if k.isdigit():
                x = tighten_pauses(edges(read_wav(f)), tcfg.get("max_pause", 0))
                if abs(tempo - 1.0) > 1e-3:
                    x = all_tempo({"tempo": tempo}, [{"voice": "x"}], [x])[0]
                cands.append((f"take {k}", x.astype(np.float64)))
        best = None
        for name, c in cands:
            lag, r = xcorr(slot, c, int(0.4 * SR))
            if best is None or r > best[2]:
                best = (name, c, r, lag)
        if best and best[2] >= min_corr:
            name, c, r, lag = best
            new = place(len(slot), c, lag)
            how = f"{name}, lag {lag}"
        elif best:
            # a line voice_cut.py shortened (a window cut from the middle of it, e.g. a clause between two commas): the slot's
            # first second and last 2.5 s anchored in the take on their own, then the cut point found as the split where the two
            # alignments together fit the slot best, moved to the quietest 10 ms within 40 ms (voice_cut cut at a quiet point), joined
            # with a 10-ms crossfade (a split at the slot's longest pause instead can let the cut words back in); check every rebuilt
            # shortened line by transcript.
            name, c = best[0], best[1]
            head, tail = slot[: int(1.0 * SR)], slot[-int(2.5 * SR):]
            l1, _ = xcorr(head, c, len(c))
            l2, _ = xcorr(tail, c, len(c))
            l2 += len(slot) - len(tail)
            A1, A2 = place(len(slot), c, l1), place(len(slot), c, l2)
            def ferr(seg, ref):
                g = np.dot(seg, ref) / (np.dot(ref, ref) + 1e-12)
                return float(np.sum((seg - g * ref) ** 2))
            grid = range(int(0.5 * SR), len(slot) - int(1.0 * SR), int(0.005 * SR))
            p = min(grid, key=lambda q: ferr(slot[:q], A1[:q]) + ferr(slot[q:], A2[q:])) if len(grid) else len(slot) // 2
            p = min(range(max(480, p - int(0.04 * SR)), min(len(slot) - 480, p + int(0.04 * SR)), 96),
                    key=lambda q: float(np.sqrt(np.mean(slot[q:q + 480] ** 2))))
            ramp = np.linspace(0, 1, 480)
            cand = A1.copy()
            cand[p:] = A2[p:]
            cand[p - 240:p + 240] = A1[p - 240:p + 240] * (1 - ramp) + A2[p - 240:p + 240] * ramp
            r1 = float(np.dot(slot[:p], cand[:p]) / (np.linalg.norm(slot[:p]) * np.linalg.norm(cand[:p]) + 1e-9))
            r2 = float(np.dot(slot[p:], cand[p:]) / (np.linalg.norm(slot[p:]) * np.linalg.norm(cand[p:]) + 1e-9))
            r = min(r1, r2)
            new, how = (cand, f"{name}, cut window {(l1 - l2) / SR:.3f} s at {p / SR:.3f} s (CHECK BY TRANSCRIPT)") if r >= min_corr else (None, "KEPT")
        if new is None:
            out[s:e] = slot * 10 ** (-DOWN_DB / 20)
            kept.append(bid)
        else:
            out[s:e] = new * (rms_voiced(slot) / rms_voiced(new)) * 10 ** (-DOWN_DB / 20)
        rows.append((bid, how, r))
    peak = np.abs(out).max()
    if peak > 30000:
        out *= 30000 / peak
    dst = root / "narration_final.wav"
    sf.write(dst, np.round(out).astype(np.int16), SR, subtype="PCM_16")
    shutil.copy2(base.with_name(base.stem + ".beats.json"), root / "narration_final.beats.json")
    rs = [r for _, how, r in rows if how != "KEPT"]
    print(f"{len(rows)} beats: {len(rows) - len(kept)} from the raw takes (waveform corr median {np.median(rs):.3f}, lowest {min(rs):.3f}); "
          f"kept with their old audio: {kept}")
    print("->", dst)
    if rep:
        rep.write_text("beat\tsource\twave_corr\n" + "".join(f"{b}\t{h}\t{r:.3f}\n" for b, h, r in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
