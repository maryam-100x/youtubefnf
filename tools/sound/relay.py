"""Lay a lost word end back WITH room: the sound gate's A1 "NO ROOM" (tails.py: the take's release sits where the final now has the next
word, because the chain cut the pause the release sat in). The take's span, lined up by tails' own Align (raw index = final index +
the run's offset, levelled by the run's gain), is inserted into the final right before the next word, which moves later by the span's
length: every later word moves, so run dj captions and sync_words after it, then the gate.

The case it is for: the take says a word with a released stop (a "t" ending on a 30-ms burst), then a pause; a pause cut joined the next
word onto the stop's closure and took the burst with it, so tails --fix can't lay it back in place: there is no room left.

  EDIT tools/sound/relay.py <video> --word-end 131.54 --take 131.630 131.715 --at 131.605 [--dry]
  --word-end  the word's end in the final (the gate's key, e.g. but@131.54): picks the speech run whose offset lines the take up
  --take      the span to lay back, in the final's time as tails --show prints it (the aligned take)
  --at        where it goes in the final: the quiet just before the next word's onset (5-ms fades at both joins)"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
from tails import Align  # noqa: E402

FADE = 0.005


def lv(a, sr):
    return G.frame_db(a, sr, 0.005)


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--word-end", type=float, required=True)
    ap.add_argument("--take", type=float, nargs=2, required=True)
    ap.add_argument("--at", type=float, required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    P = G.paths(a.video)
    al = Align(P["final"], P["raw"], P["words"])
    sr = al.sr
    # the word lined up the way tails --show does it (its own match, not only the run's)
    w = min(al.W, key=lambda q: abs(q["end"] - a.word_end))
    L = al.locate(w, record=False)
    if not L:
        raise SystemExit(f"{w['w']!r} at {w['end']:.2f}: not found in the take: nothing laid back")
    A, pa, gain, sc = L
    off = pa - A
    print(f"{w['w']!r} end {w['end']:.3f}: lined up with the take (match {sc:.3f}, offset {off / sr:+.3f} s, gain {gain:+.1f} dB)")
    t0, t1 = int(round(a.take[0] * sr)), int(round(a.take[1] * sr))
    seg = al.p[t0 + off:t1 + off] * (10 ** (gain / 20))
    n = int(FADE * sr)
    ramp = np.linspace(0, 1, n)[:, None]
    seg = seg.copy()
    seg[:n] *= ramp
    seg[-n:] *= ramp[::-1]
    i = int(round(a.at * sr))
    x = al.x
    print(f"take span {a.take[0]:.3f}-{a.take[1]:.3f} s (raw {(t0 + off) / sr:.3f}-{(t1 + off) / sr:.3f} s, gain {gain:+.1f} dB): "
          f"{(t1 - t0) / sr * 1000:.0f} ms, loudest {G.db(seg.mean(1)):.1f} dB rms; into the final at {a.at:.3f} s "
          f"(the final there: {lv(x[i - n:i + n].mean(1), sr).round(1).tolist()} dB)")
    y = np.concatenate([x[:i], seg, x[i:]])
    k0 = max(0, i - int(0.06 * sr))
    k1 = i + len(seg) + int(0.06 * sr)
    L = lv(y[k0:k1].mean(1), sr)
    print("after, 5-ms frames from", f"{k0 / sr:.3f} s:", " ".join(f"{v:.0f}" for v in L))
    print(f"every word after {a.at:.3f} s moves {len(seg) / sr * 1000:.0f} ms later; {len(x) / sr:.3f} -> {len(y) / sr:.3f} s")
    if a.dry:
        return
    final = Path(P["final"])
    shutil.copy(final, final.with_name(final.stem + "_prerelay.wav"))
    sf.write(final, y, sr, subtype=sf.info(str(final)).subtype)
    print(f"written {final} (backup {final.stem}_prerelay.wav)")
    shift_beats(Path(P["beats"]), a.at, len(seg) / sr, len(y) / sr)
    print("next: dj captions, sync_words, the gate")


def shift_beats(path, at, dt, dur):
    """dj's beat slots moved with the insert, as close_gaps.py moves them with its cuts (else beats.json comes out short by the insert,
    and the film's length and every slot after the insert stay where they were)"""
    import json
    B = json.loads(path.read_text(encoding="utf-8"))
    shutil.copy(path, path.with_name(path.stem + "_prerelay.json"))
    num, den = (int(v) for v in str(B.get("fps", "60/1")).split("/")) if "/" in str(B.get("fps", "60")) else (int(B.get("fps", 60)), 1)
    fps = num / den
    for b in B["beats"]:
        for k in ("start", "voice_end", "end"):
            if b.get(k) is not None and b[k] > at:
                b[k] = round(b[k] + dt, 4)
    for i, b in enumerate(B["beats"]):
        b["start_f"] = round(b["start"] * fps)
        nxt = B["beats"][i + 1]["start"] if i + 1 < len(B["beats"]) else dur
        b["frames"] = round(nxt * fps) - b["start_f"]
    B["duration"] = round(dur, 4)
    B["total_frames"] = round(dur * fps)
    path.write_text(json.dumps(B, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"beats moved after {at:.3f} s by {dt * 1000:.0f} ms: {path} (backup {path.stem}_prerelay.json); duration {dur:.3f} s")


if __name__ == "__main__":
    main()
