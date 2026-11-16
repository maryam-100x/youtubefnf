"""Cut a spoken phrase out of a finished narration (a hedge or a clause the creator wants gone after watching). Keeps the take the
creator heard: no re-voice, the words round the cut untouched.

The span [a, b) must start and end in quiet (the 10 ms round each edge under -45 dB: the pauses before and after the phrase), and the
voice must be unlocked for it (voice_lock.py unlock --why). The cut is a whole number of 60-fps frames, so later anchors stay on frames.
  - the narration loses the span (5-ms fades at the join; the old one kept as narration_precut_<a>.wav);
  - build/beats.json: every slot after `a` moves back by the cut;
  - build/captions/words.json: the phrase's words go, every later word moves back, the cues and chunks are regrouped exactly as dj captions
    groups them (dj.captions.group with config/tts.toml [captions]), the srt files are written and the narration signed again (no new Whisper
    pass: its word boxes change from pass to pass, and each pass brings new flags).
Then: script.md's line to the new words, motion/sync_words.py, the sound gate, voice_lock.py lock.

  EDIT tools/sound/cut_words.py <video> <a> <b> [--dry]"""
import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))   # tools/: the dj package
import gatelib as G  # noqa: E402

FPS = 60
FADE = 0.005
QUIET = -40.0   # an edge in a pause: room tone between words sits at about -43..-56 dB, speech over -30


def main():
    sys.path.insert(0, str(G.VOICE_TOOLS))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py, or unlocked for a reason
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("a", type=float)
    ap.add_argument("b", type=float)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    P = G.paths(a.video)
    final = Path(P["final"])
    x, sr = sf.read(final, always_2d=True)
    mono = x.mean(1)
    frames = int(round((a.b - a.a) * FPS))
    sec = frames / FPS
    i0 = int(round(a.a * sr))
    i1 = i0 + int(round(sec * sr))
    hop = int(0.01 * sr)

    def edge(i):
        seg = mono[max(0, i - hop // 2): i + hop // 2]
        return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12)

    e0, e1 = edge(i0), edge(i1)
    D = json.loads(Path(P["words"]).read_text(encoding="utf-8"))
    gone = [w for w in D["words"] if a.a <= w["start"] < a.a + sec]
    print(f"cut {frames} frames ({sec:.3f} s) at {i0 / sr:.3f}-{i1 / sr:.3f} s; edges {e0:.0f}/{e1:.0f} dB; the words cut: "
          f"\"{' '.join(w['w'] for w in gone)}\"")
    if e0 > QUIET or e1 > QUIET:
        raise SystemExit("an edge isn't quiet: nothing cut (put both ends in the pauses round the phrase)")
    # loudness alone isn't an edge (a 30-ms dip inside a word, before its closing hiss, reads as the pause after it: the cut would keep
    # the word's head and carry its hiss off with the moved phrase): the words round the cut are forced onto the audio by the speech
    # model, and an edge inside a kept word's span refuses
    sys.path.insert(0, str(G.VOICE_TOOLS))
    import ctcalign as CTC  # noqa: E402
    w0, w1 = max(0.0, a.a - 2.5), a.a + sec + 2.5
    near = [w for w in D["words"] if w0 <= w["start"] < w1]
    spans = CTC.align(mono[int(w0 * sr):int(w1 * sr)], sr, " ".join(w["w"] for w in near))
    for t_edge in (a.a, a.a + sec):
        for s_ in spans:
            if s_["start"] is None:
                continue
            ws, we = w0 + s_["start"], w0 + s_["end"]
            inside_cut = ws >= a.a - 0.01 and we <= a.a + sec + 0.01
            if not inside_cut and ws < t_edge < we:
                raise SystemExit(f"the edge at {t_edge:.3f} s cuts into \"{s_['w']}\" ({ws:.3f}-{we:.3f} s by the speech model): nothing cut")
    # what goes is what the speech model hears inside the cut, not where a caption box starts (it fails both ways: a word whose box
    # starts in the pause before the cut's end is kept as a phantom when its sound is cut; a word whose box starts inside a cut pause
    # while its sound starts after the cut would be dropped while it is still heard)
    gone_ids = {id(w) for w in gone}
    if len(spans) == len(near):
        for w, s_ in zip(near, spans):
            if s_["start"] is None:
                continue
            if w0 + s_["start"] >= a.a - 0.01 and w0 + s_["end"] <= a.a + sec + 0.01:
                gone_ids.add(id(w))
            else:
                gone_ids.discard(id(w))
    if gone_ids != {id(w) for w in gone}:
        gone = [w for w in D["words"] if id(w) in gone_ids]
        print(f"  by the speech model the words cut are: \"{' '.join(w['w'] for w in gone)}\"")
    if a.dry:
        return
    shutil.copy2(final, final.with_name(f"narration_precut_{a.a:.2f}.wav"))
    sub = sf.info(final).subtype
    n = int(FADE * sr)
    head, tail = x[:i0].copy(), x[i1:].copy()
    head[-n:] *= np.linspace(1.0, 0.0, n)[:, None]
    tail[:n] *= np.linspace(0.0, 1.0, n)[:, None]
    sf.write(final, np.concatenate([head, tail]), sr, subtype=sub)
    lo, d = a.a, -sec
    bp = Path(P["beats"])
    B = json.loads(bp.read_text(encoding="utf-8"))
    for bt in B["beats"]:
        for k in ("start_f", "end_f"):
            if isinstance(bt.get(k), int) and bt[k] > lo * FPS:
                bt[k] -= frames
        for k in ("start", "end", "voice_end"):
            if isinstance(bt.get(k), (int, float)) and bt[k] > lo:
                bt[k] = round(bt[k] + d, 4)
    if isinstance(B.get("duration"), (int, float)):
        B["duration"] = round(B["duration"] + d, 4)
    # the beat's text follows the cut (else build/beats.json keeps the cut sentence, and sync_words.py gives its words zero-length
    # slots, phantom anchors for the picture): the gone words leave the beat's voice text too, matched to its caption words
    import difflib
    touched = {w.get("beat") for w in gone}
    sb = dict(G.script_beats(P["script"])) if Path(P["script"]).exists() else {}
    for bt in B["beats"]:
        if bt.get("id") not in touched or not isinstance(bt.get("voice"), str):
            continue
        toks = bt["voice"].split()
        heard = [w for w in D["words"] if w.get("beat") == bt["id"]]
        sm = difflib.SequenceMatcher(a=[G.key(t) for t in toks], b=[G.key(h["w"]) for h in heard], autojunk=False)
        drop = set()
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                drop.update(i1 + k for k in range(i2 - i1) if id(heard[j1 + k]) in gone_ids)
            elif tag == "replace" and all(id(h) in gone_ids for h in heard[j1:j2]):
                drop.update(range(i1, i2))
        new = " ".join(t for k, t in enumerate(toks) if k not in drop)
        if sb.get(bt["id"]) and [G.key(t) for t in sb[bt["id"]].split()] != [G.key(t) for t in new.split()]:
            print(f"  {bt['id']}: script.md's line differs from what is left: set it to \"{new}\"")
        bt["voice"] = new
    bp.write_text(json.dumps(B, indent=1, ensure_ascii=False), encoding="utf-8")
    from dj.captions import PUNCT_BREAK, group, write_srt
    from dj.core import config_file, file_sig
    def moved(t):   # a time in the old narration -> the new one (inside the cut -> the join)
        return t if t <= lo else (round(lo, 4) if t < lo + sec else round(t + d, 4))
    words = []
    for w in D["words"]:
        if id(w) in gone_ids:
            continue
        w = dict(w)
        w["start"], w["end"] = moved(w["start"]), moved(w["end"])
        words.append(w)
    c = tomllib.loads(config_file().read_text(encoding="utf-8"))["captions"]   # dj's config (config/tts.toml) [captions]
    D["words"] = words
    D["cues"] = group(words, 99, c["max_chars"], 6.0, ".?!…")
    D["chunks"] = group(words, c["chunk_words"], c["chunk_chars"], 2.5, PUNCT_BREAK)
    D["narration_sig"] = file_sig(final)
    cp = Path(P["words"])
    cp.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
    write_srt(cp.parent / "captions.srt", D["cues"])
    write_srt(cp.parent / "chunks.srt", D["chunks"])
    print(f"narration {len(x) / sr - sec:.3f} s; {len(gone)} words cut, every later word and beat {d:+.3f} s; the captions regrouped and "
          f"the narration signed again. Next: script.md, sync_words.py, the sound gate, voice_lock.py lock")
    # the join read back by the speech model: what a listener hears there, for the operator to hold against the new line
    y, _ = sf.read(final, always_2d=True)
    ym = y.mean(1)
    j0, j1 = max(0.0, a.a - 2.0), a.a + 2.0
    heard = CTC.greedy(ym[int(j0 * sr):int(j1 * sr)], sr)
    print("  heard at the join:", CTC.greedy_text(heard) if hasattr(CTC, "greedy_text") else heard)


if __name__ == "__main__":
    main()
