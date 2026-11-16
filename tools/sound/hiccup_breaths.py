"""The hiccup pass. The 0.25-s pause cap can cut through the middle of inhales the safe breath pass left (that pass mutes only
stretches at -24 dB or quieter, after a word's decay guard), so a gap keeps a breath's edges as short blips around a cut: hiccupped
breaths. This pass, on the final (capped) narration with its own word times: in every gap between words, from the end of the word's own
decay (its level falling to its valley, never before the spelling's tail guard) to the next word's onset minus a spelling-aware head
guard, everything is silenced with 15-ms fades, but only where the gap holds a blip (a 20-ms frame at -50 dB or louder after the decay).
The timing never moves (mute, not cut). A word's own s/sh/f/th/t/k/p sits inside its guard and is never taken for a breath.

  EDIT tools/sound/hiccup_breaths.py <in.wav> <words.json> <out.wav> [--report r.json]"""
import json, sys
import numpy as np, soundfile as sf

HOP = 0.01


def head_guard(w):
    w = w.lower().strip('"“”.,!?;:\'')
    if w[:2] in ("sh", "th", "ch") or w[:1] in ("s", "f", "h", "z", "x") or (w[:1] == "c" and w[1:2] in ("e", "i")):
        return 0.16
    if w[:1] in ("p", "t", "k", "c", "q", "b", "d", "g"):
        return 0.07
    return 0.04


def tail_guard(w):
    w = w.lower().strip('"“”.,!?;:\'')
    if w.isdigit():   # "5", "17": said as words ending voiced or in -ve/-s/-x, as breath_cut.py
        return 0.24
    # a voiced fricative end is a fricative too: a -ve still buzzes at -25..-33 dB past the 0.08-s voiced guard
    if w.endswith(("s", "sh", "ch", "f", "th", "x", "z", "ce", "se", "ve", "v", "fe")):
        return 0.22
    if w.endswith(("t", "k", "p", "ct", "ght", "te", "d", "b", "g")):   # a -d releases ~0.1 s after Whisper's end
        return 0.16
    return 0.08


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    src, words_p, out = sys.argv[1:4]
    rep = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    x, sr = sf.read(src, dtype="float64", always_2d=False)
    mono = x.mean(1) if x.ndim == 2 else x
    h = int(HOP * sr)
    n = len(mono) // h
    lv = 20 * np.log10(np.sqrt((mono[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
    W = json.load(open(words_p, encoding="utf-8"))
    W = sorted(W["words"] if isinstance(W, dict) else W, key=lambda w: w["start"])
    g = np.ones(len(mono))
    f = int(0.015 * sr)
    done = []
    for a, b in zip(W, W[1:]):
        gap = b["start"] - a["end"]
        if gap < 0.08:
            continue
        # the word's decay: from its tail guard on, follow the level down to its valley (rising again = the next sound has started)
        j = int((a["end"] + tail_guard(a["w"])) * 100)
        stop = int((b["start"] - head_guard(b["w"])) * 100)
        while j + 1 < stop and lv[j + 1] <= lv[j] + 0.5 and lv[j] > -60:
            j += 1
        # and on until the word has really died away (a -ve or an s buzzes with small rises, so the first rise can come inside the
        # word and a mute would start on sound): the mute starts only under -45 dB, else no mute
        while j < stop and lv[j] > -45:
            j += 1
        s0, s1 = j + 1, stop
        if s1 - s0 < 3:
            continue
        seg = lv[s0:s1]
        if not (seg > -50).any() and not ((seg > -70) & (seg < -1e2 + 1e9)).any():
            continue
        blips = int((seg > -50).sum())
        if blips == 0 or seg.max() > -28:   # louder than a breath at this level: speech the words list timed late, never touched
            continue
        t0, t1 = s0 * HOP, s1 * HOP
        i0, i1 = int(t0 * sr), int(t1 * sr)
        g[i0:i0 + f] = np.minimum(g[i0:i0 + f], np.linspace(1, 0, f))
        g[i0 + f:i1 - f] = 0
        g[i1 - f:i1] = np.minimum(g[i1 - f:i1], np.linspace(0, 1, f))
        done.append({"after": a["w"], "before": b["w"], "beat": a.get("beat"), "from": round(t0, 3), "to": round(t1, 3), "loudest": round(float(seg.max()), 1), "blips": blips})
    y = x * (g[:, None] if x.ndim == 2 else g)
    sf.write(out, y, sr, subtype="PCM_16")
    if rep:
        json.dump(done, open(rep, "w", encoding="utf-8"), indent=0)
    print(f"{len(done)} gaps cleaned ({sum(d['to'] - d['from'] for d in done):.1f} s silenced) -> {out}")
    for d in done[:6]:
        print("  ", d)


if __name__ == "__main__":
    main()
