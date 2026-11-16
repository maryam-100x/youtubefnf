"""Cut words out of a spliced narration (narration_final.wav + .beats.json) without re-voicing anything: a repeated phrase, a sentence
that goes, a joke that falls out. A cut is given in the OLD narration's seconds (build/beats.json and build/captions/words.json, the build
the splice kept its slots from: voice_patch.py --keep-old), as two windows: each edge of the cut lands on the quietest 10 ms inside its
window, so it never splits a sound. The piece between the edges goes, the two sides meet with a 10-ms crossfade, and the beat boundaries
after it move up.

  cd tools && PIPE voice/voice_cut.py ../videos/<video> S12:200.78-201.06:202.34-202.56 [S14:...] [--dry]
BEAT:a0-a1:b0-b1 = cut from the quietest point in [a0, a1] to the quietest point in [b0, b1] (old seconds, inside that beat's slot)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, load_config, read_wav, write_wav  # noqa: E402


def quietest(x, t0, t1):
    """The start of the quietest 10 ms in [t0, t1] (seconds into x), on a 2.5-ms grid."""
    best, bt = None, t0
    for t in np.arange(t0, max(t0 + 0.011, t1 - 0.01), 0.0025):
        seg = x[int(t * SR):int((t + 0.01) * SR)].astype(np.float64)
        e = float(np.mean(seg ** 2)) if len(seg) else 1e18
        if best is None or e < best:
            best, bt = e, t
    return bt + 0.005  # the middle of that 10 ms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("cuts", nargs="+")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    cfg = load_config(None, video_config(a.video))
    ctx = Ctx(a.video, cfg)
    dst = ctx.build.parent / "narration_final.wav"
    side = dst.with_name(dst.stem + ".beats.json")
    x = read_wav(dst)
    m = json.loads(side.read_text(encoding="utf-8"))
    old = {b["id"]: b for b in json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]}
    spf = SR * ctx.fd[0] / ctx.fd[1]
    cuts = []
    for c in a.cuts:
        bid, wa, wb = c.split(":")
        a0, a1 = map(float, wa.split("-"))
        b0, b1 = map(float, wb.split("-"))
        nb = next(r for r in m["beats"] if r["id"] == bid)
        off = nb["a"] / SR - round(old[bid]["start_f"] * spf) / SR  # old seconds -> seconds in the splice (the slot is kept as it was)
        e0 = quietest(x, a0 + off, a1 + off)
        e1 = quietest(x, b0 + off, b1 + off)
        i0, i1 = int(round(e0 * SR)), int(round(e1 * SR))
        assert nb["a"] <= i0 < i1 <= nb["b"], (bid, i0, i1, nb)
        cuts.append((bid, i0, i1))
        print(f"  {bid}: cut {e0 - off:.3f}-{e1 - off:.3f} old s ({(i1 - i0) / SR:.2f} s)")
    if a.dry:
        return
    xf = x.astype(np.float64)
    f = int(0.01 * SR)
    for bid, i0, i1 in sorted(cuts, key=lambda c: -c[1]):  # from the end, so the earlier positions stay valid
        head, tail = xf[:i0 + f // 2], xf[i1 - f // 2:]
        fade = np.linspace(1, 0, f)
        mid = head[-f:] * fade + tail[:f] * (1 - fade)
        xf = np.concatenate([head[:-f], mid, tail[f:]])
        n = i1 - i0
        for r in m["beats"]:
            if r["id"] == bid:
                r["b"] -= n
            elif r["a"] >= i1:
                r["a"] -= n
                r["b"] -= n
    assert m["beats"][-1]["b"] == len(xf), (m["beats"][-1]["b"], len(xf))
    write_wav(dst, np.clip(np.round(xf), -32768, 32767).astype(np.int16))
    side.write_text(json.dumps(m), encoding="utf-8")
    print(f"-> {dst} ({len(xf) / SR:.2f} s) + {side.name}")


if __name__ == "__main__":
    main()
