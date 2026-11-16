"""Close a silent span inside a word: relay.py's mirror (it inserts, this cuts). The case: a section take split between two beats
inside a word, so one beat file ends on the word's first consonant burst and the next begins on the rest of the word; the splice puts
the beats' own silence between them (the gate's A7 reads it as a scrap before the word). The span (digital silence or near it) is cut
from the final with a 5-ms crossfade, and every beat after it moves earlier by its length (relay.shift_beats); run dj captions and sync_words after it, then
the gate. Refuses a span with sound in it (over -60 dB in any 5-ms frame).

  EDIT tools/sound/cutspan.py <video> <a> <b> [--dry]"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
from relay import shift_beats  # noqa: E402

FADE = 0.005


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
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
    i0, i1 = int(round(a.a * sr)), int(round(a.b * sr))
    L = G.frame_db(x[i0:i1].mean(1), sr, 0.005)
    if len(L) and L.max() > -60:
        raise SystemExit(f"{a.a:.3f}-{a.b:.3f} s has sound in it (loudest 5-ms frame {L.max():.1f} dB): nothing cut")
    n = int(FADE * sr)
    ramp = np.linspace(0, 1, n)[:, None]
    head, tail = x[:i0].copy(), x[i1:].copy()
    head[-n:] = head[-n:] * ramp[::-1] + tail[:n] * ramp      # a 5-ms crossfade over the join
    y = np.concatenate([head, tail[n:]])
    k0 = max(0, i0 - int(0.06 * sr))
    print(f"cut {a.a:.3f}-{a.b:.3f} s ({(i1 - i0) / sr * 1000:.0f} ms, loudest {L.max():.1f} dB); after, 5-ms frames from {k0 / sr:.3f} s: "
          + " ".join(f"{v:.0f}" for v in G.frame_db(y[k0:i0 + int(0.06 * sr)].mean(1), sr, 0.005)))
    if a.dry:
        return
    shutil.copy(final, final.with_name(final.stem + "_precut.wav"))
    sf.write(final, y, sr, subtype=sf.info(str(final)).subtype)
    shift_beats(Path(P["beats"]), a.a, -(i1 - i0) / sr, len(y) / sr)
    print(f"written {final} (backup {final.stem}_precut.wav); next: dj captions, sync_words, the gate")


if __name__ == "__main__":
    main()
