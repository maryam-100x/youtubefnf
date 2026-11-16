"""A10 of the sound gate: fragments, voiced sound that no word of the script covers (standard/VOICE_LOCK.md): a take's context tail
left in a splice, a doubled syllable (a second "-teenth" after a whole "sixteenth" at the join of two beats), a word's head at a join.
The other checks pass such a sound: A7 (scraps) wants a head shaped like the NEXT word, this is the tail of the word before;
qa_word_holes needs 0.4 s; Whisper's boxes say nothing is there.

How:
  1. where to listen: a window around every join (each beat's start in beats.json, the splices and lay-ins in voice_lock.json) and
     around every voiced run Whisper's word boxes leave uncovered (pitch present, 60 ms or more, peak -30 dB or louder);
  2. in each window the script's words are forced onto the audio by a CTC model (tools/voice/ctcalign.py), and the same model
     decodes the window freely;
  3. a FRAGMENT is a voiced run of 60 ms or more, 40 ms clear of every aligned word, where the free decoding hears letters: speech the
     script doesn't have (a context tail, a doubled syllable, a word's head at a join).
Fix: re-voice the line, or mute a pure fragment that sits in a pause (voice_layin.py keeps the time either way); allow only with the
proof in words (gate_allow.json), never by reasoning about word boxes (a flag is a fault until its own audio proves otherwise).

  EDIT tools/sound/fragments.py <video> [--final F --words W --beats B]
      [--span T0 T1] [--json out] [-v]     (--span: only windows inside it, e.g. a lay-in's changed span)"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "voice"))
import gatelib as G  # noqa: E402

MIN_VOICED = 0.06     # s: a fragment's voiced length (the spec's 60 ms; a doubled "-teenth" runs 125 ms)
LOUD = -30.0          # dB peak (10-ms RMS): speech; a breath or a creak sits under it
CLEAR = 0.04          # s an aligned word's edge may run into the run before it counts as that word's own sound
WHISPER_PAD = 0.03    # s around Whisper's boxes when looking for uncovered voiced runs
CONTEXT = 1.2         # s of audio on each side of a join or a candidate
MAX_WIN = 8.0         # s: a window no longer than this (the model reads it at once)
EDGE = 0.25           # s at a window's edges where nothing is judged (a word cut by the window is not a fragment)
HOP = 0.005
FUNCTION_INS = {"AND"}   # numbers said with an "and" ("a hundred and fifty") the written digits don't spell


def voicing(x, sr):
    """per 5-ms frame: level dB (10-ms RMS) and voiced (an F0 found)"""
    import parselmouth
    d = max(1, sr // 16000)
    y = x[::d].astype(np.float64)
    p = parselmouth.Sound(y, sampling_frequency=sr / d).to_pitch_ac(time_step=HOP, pitch_floor=60, pitch_ceiling=400)
    f0 = p.selected_array["frequency"]
    xs = p.xs()
    n = int(len(x) / sr / HOP)
    voiced = np.zeros(n, bool)
    idx = np.clip(np.round((xs - HOP / 2) / HOP).astype(int), 0, n - 1)
    voiced[idx[f0 > 0]] = True
    h = int(HOP * sr)
    m = len(x) // h
    e = (x[:m * h].reshape(m, h) ** 2).mean(1)
    e2 = np.convolve(e, [0.5, 0.5], mode="same")      # 10-ms RMS
    lev = 10 * np.log10(e2 + 1e-12)
    n = min(n, m)
    return lev[:n], voiced[:n]


def runs(mask, bridge=2):
    """[i, j) runs of True, gaps of `bridge` frames or fewer joined"""
    out, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while True:
            while j < n and mask[j]:
                j += 1
            k = j
            while k < n and not mask[k]:
                k += 1
            if k < n and k - j <= bridge:
                j = k
                continue
            break
        out.append((i, j))
        i = j
    return out


def voiced_runs(lev, voiced):
    """voiced runs of MIN_VOICED+ with a LOUD peak -> [(t0, t1, peak)]"""
    out = []
    for i, j in runs(voiced & (lev > LOUD - 15)):
        if (j - i) * HOP >= MIN_VOICED and lev[i:j].max() >= LOUD:
            out.append((i * HOP, j * HOP, float(lev[i:j].max())))
    return out


def box_mask(W, n, pad):
    """per 5-ms frame: inside a word box (padded)"""
    m = np.zeros(n, bool)
    for w in W:
        m[max(0, int((w["start"] - pad) / HOP)):max(0, min(n, int((w["end"] + pad) / HOP) + 1))] = True
    return m


def windows(P, W, vr, span, n):
    """the places to listen: joins and splices, and voiced runs Whisper's boxes leave uncovered -> [(t0, t1, why)], each MAX_WIN or
    shorter"""
    pts = []
    try:
        beats = json.loads(Path(P["beats"]).read_text(encoding="utf-8"))["beats"]
        for b in beats[1:]:
            pts.append((float(b["start"]), f"join {b['id']}"))
    except (OSError, KeyError, ValueError):
        pass
    lock = P["video_dir"] / "voice_lock.json"
    if lock.exists():
        for li in json.loads(lock.read_text(encoding="utf-8")).get("layins", []):
            pts += [(li["t0"], f"lay-in {li['beat']}"), (li["t1"], f"lay-in {li['beat']} end")]
    cov = box_mask(W, n, WHISPER_PAD)
    for t0, t1, _ in vr:
        free = int((~cov[int(t0 / HOP):int(t1 / HOP)]).sum()) * HOP
        if free >= MIN_VOICED:
            pts.append(((t0 + t1) / 2, "uncovered"))
    if span:
        pts = [p for p in pts if span[0] <= p[0] <= span[1]]
    pts.sort()
    out = []
    for t, why in pts:
        a, b = t - CONTEXT, t + CONTEXT
        if out and a <= out[-1][1] - EDGE * 2 and b - out[-1][0] <= MAX_WIN:
            out[-1] = (out[-1][0], max(out[-1][1], b), out[-1][2] + [why])
        else:
            out.append((a, b, [why]))
    return out


def snap(W, starts, a, b):
    """window edges moved into the gaps between the words, so the window holds whole words -> (a, b, words inside)"""
    import bisect
    i0 = bisect.bisect_left(starts, a)
    i1 = bisect.bisect_right(starts, b) - 1
    while i1 >= i0 and W[i1]["end"] > b:
        i1 -= 1
    if i1 < i0:
        return a, b, []
    a2 = (W[i0 - 1]["end"] + W[i0]["start"]) / 2 if i0 > 0 else max(0.0, W[i0]["start"] - 0.2)
    b2 = (W[i1]["end"] + W[i1 + 1]["start"]) / 2 if i1 + 1 < len(W) else W[i1]["end"] + 0.3
    return max(a2, W[i0]["start"] - 0.4), min(b2, W[i1]["end"] + 0.4), W[i0:i1 + 1]


def inserted(chars, text):
    """the letters the free decoding heard that the script's text doesn't have -> [[chars...]] clusters. A char-level diff of the
    decoding against the text as the model spells it; a replace counts only its excess letters. Counted: a whole extra word of 2+
    letters ("TEENTH" between SIXTEENTH and THE), or 4+ extra letters inside a word; never next to a word said letter by letter
    (an initialism, 'bee bee see'). In an approved voice, spelling variants inside words (NINETEEN-TH THE) are 2-3 letters."""
    import difflib
    import ctcalign as C
    ref, spl = [], []
    for tok, ws in C.words_of(text):
        for w in ws:
            ref.append(w)
            spl.append(C.spelled(tok))
    rs = "|".join(ref)
    rflag = []
    for w, f in zip(ref, spl):
        rflag += [f] * len(w) + [False]
    hs = "".join(c["c"] for c in chars)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, rs, hs, autojunk=False).get_opcodes():
        if op == "insert":
            k0, k1 = j1, j2
        elif op == "replace" and (j2 - j1) - (i2 - i1) >= 3:
            k0, k1 = j1 + (i2 - i1), j2
        else:
            continue
        if any(rflag[max(0, i1 - 2):min(len(rflag), i2 + 2)]):
            continue
        seg = [c for c in chars[k0:k1] if c["c"] != "|"]
        if len(seg) < 2 or "".join(c["c"] for c in seg) in FUNCTION_INS:
            continue
        # a whole word: bounded by word breaks (or the ends) in the decoding
        whole = (k0 == 0 or hs[k0 - 1] == "|" or hs[k0] == "|") and (k1 >= len(hs) or hs[k1] == "|" or hs[k1 - 1] == "|")
        if whole or len(seg) >= 4:
            out.append(seg)
    return out


def script_words(P, W):
    """the edit's words (keyed by the script's tokens: sync_words.py) when they belong to this narration, else Whisper's"""
    src = (P["cfg"].get("video") or {}).get("src")
    p = G.MOTION / "src" / (src or "_none_") / "words.json"
    if src and p.exists():
        S = G.load_words(p)
        if S and abs(S[-1]["end"] - W[-1]["end"]) < 1.0 and abs(len(S) - len(W)) <= max(20, len(W) // 50):
            return S
    return W


def run(P, quiet=False, verbose=False, span=None):
    import ctcalign as C
    x, sr = G.load_mono(P["final"])
    W = G.load_words(P["words"])
    S = script_words(P, W)
    lev, voiced = voicing(x, sr)
    vr = voiced_runs(lev, voiced)
    flags, seen, checked = [], set(), 0
    starts = [w["start"] for w in S]
    cpath = Path(P["out"]) / "a10_cache.json"
    try:
        cache = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
    except ValueError:
        cache = {}
    cov = box_mask(W, len(lev), WHISPER_PAD)
    for a, b, why in windows(P, W, vr, span, len(lev)):
        a, b, ws = snap(S, starts, a, b)
        if len(ws) < 2:
            continue
        seg = x[int(a * sr):int(b * sr)]
        text = " ".join(w["w"] for w in ws)
        hk = hashlib.sha1(seg.astype(np.float32).tobytes() + text.encode("utf-8")).hexdigest()
        if hk in cache:             # the same audio and words as a run before (a re-run, a lay-in's span): its decoding
            chars, em = cache[hk], None
        else:
            em = C.emissions(seg, sr)
            chars = C.greedy(seg, sr, em)
            cache[hk] = chars
        checked += 1
        clusters = inserted(chars, text)
        # a doubled syllable ("sixteenth teenth") diffs either copy as the extra one: the extra one is the copy Whisper's boxes leave
        # bare (Whisper hears the word once), so each cluster moves to the copy of its letters with the most uncovered sound
        hs = "".join(c["c"] for c in chars)
        bare = lambda q0, q1: float((~cov[int((a + q0) / HOP):int((a + q1) / HOP)]).mean()) if q1 > q0 else 0.0  # noqa: E731
        for k, cl in enumerate(clusters):
            pat = "".join(c["c"] for c in cl)
            best, j = (bare(cl[0]["t0"], cl[-1]["t1"]), cl), hs.find(pat)
            while j >= 0:
                alt = chars[j:j + len(pat)]
                if bare(alt[0]["t0"], alt[-1]["t1"]) > best[0] + 0.25:
                    best = (bare(alt[0]["t0"], alt[-1]["t1"]), alt)
                j = hs.find(pat, j + 1)
            clusters[k] = best[1]
        for cl in clusters:
            c0, c1 = a + cl[0]["t0"], a + cl[-1]["t1"]
            if c0 < a + EDGE or c1 > b - EDGE:
                continue
            m0, m1 = int((c0 - 0.04) / HOP), int((c1 + 0.04) / HOP)
            vv = [(i, j) for i, j in runs(voiced[m0:m1] & (lev[m0:m1] > LOUD - 15), bridge=1)]
            vlen = max(((j - i) * HOP for i, j in vv), default=0.0)
            pk = float(lev[m0:m1].max()) if m1 > m0 else -120.0
            heard = "".join(c["c"] for c in cl)
            if verbose:
                print(f"  {G.fmt_t(c0)} ({c0:.3f}-{c1:.3f}) heard {heard!r} not in the script; voiced {vlen * 1000:.0f} ms, peak {pk:.0f} dB"
                      f"  [{', '.join(why)}]\n      script: {text!r}\n      heard:  {C.greedy_text(chars)!r}")
            if vlen < MIN_VOICED or pk < LOUD:
                continue
            key = f"frag@{c0:.2f}"
            if any(abs(c0 - float(k.split('@')[1])) < 0.3 for k in seen):
                continue
            seen.add(key)
            before = [w for w in ws if w["end"] <= c0 + 0.1]
            after = [w for w in ws if w["start"] >= c1 - 0.1]
            ctx = f"{before[-1]['w'] if before else '^'} [{heard.lower()}] {after[0]['w'] if after else '$'}"
            flags.append(G.flag("A10", key, c0, ctx, f"a fragment: {heard!r} heard between the script's words ({ctx}), {vlen * 1000:.0f} ms "
                                f"voiced at {pk:.0f} dB: speech the script doesn't have (a context tail, a doubled syllable, a head at a "
                                f"join); re-voice the line, or mute it if it sits alone in a pause", ms=round(vlen * 1000), loud=round(pk, 1),
                                heard=heard, where=why))
    try:
        cpath.parent.mkdir(parents=True, exist_ok=True)
        cpath.write_text(json.dumps(cache), encoding="utf-8")
    except OSError:
        pass
    res = {"check": "A10", "final": str(P["final"]), "flags": flags, "windows": checked, "voiced_runs": len(vr)}
    if not quiet:
        print(f"A10 fragments: {checked} windows, {len(vr)} voiced runs; {len(flags)} fragments")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--span", nargs=2, type=float, help="only the windows inside these narration seconds")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    res = run(G.paths_from(a), verbose=a.v, span=a.span)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
