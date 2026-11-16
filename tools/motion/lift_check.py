"""kit3 Foot's `lift`, measured: the shadow curve against the CSS filter chain a lift is often written as, on real frames.
Editing venv:
  EDIT tools/motion/lift_check.py <frames dir> [--chrome <still.png> <source frame.png> ...]

The CSS chain `brightness(1.22) contrast(1.06) saturate(1.06)` DARKENS a dark shot: contrast pivots on mid-grey, so after the brightness
v -> 1.2932 v - 0.03, below v = 0.102 (26/255) the result is DARKER than the source and under 0.023 (6/255) it clips to black: the
darkest parts of a dark shot (exactly what a lift is for) go down. kit3's lift (tokens.ts `liftCurve`, drawn by an SVG
feComponentTransfer table in sRGB) is a shadow curve: v + LIFT_A * v * (1 - v)^LIFT_N per channel: 0 stays 0 (no crushed or lifted
black point), 1 stays 1 (no clipped highlight), the lift falls off fast above the shadows (+63% at 0.05, +6% at 0.2, 0 above 0.35), and it
rises everywhere (its slope never under 0.8: never below the source, no flat band).

For each clip's frames (<dir>/<clip>_NN.png, e.g. ffmpeg -vf fps=4): the source, the CSS chain ("old"), the curve ("new"): mean luma
(Rec. 709, 0-255), the 10th / 50th / 90th percentiles, the share of pixels the filter made darker, the share clipped at 0 and at 255,
and for each filter the mean absolute change. --chrome pairs: a Remotion still of the filter against the source frame it drew, to show
the emulation is Chrome's."""
import argparse
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

LIFT_A, LIFT_N = 1.3, 14         # kit3 tokens.ts LIFT (keep the two in step)


def lift_new(v):
    return np.clip(v + LIFT_A * v * (1 - v) ** LIFT_N, 0, 1)


def lift_old(rgb):
    v = np.clip(rgb * 1.22, 0, 1)                    # brightness(1.22)
    v = np.clip((v - 0.5) * 1.06 + 0.5, 0, 1)        # contrast(1.06)
    s = 1.06                                         # saturate(1.06): the Filter Effects matrix
    m = np.array([[0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s],
                  [0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s],
                  [0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s]])
    return np.clip(v @ m.T, 0, 1)


def luma(rgb):
    return (rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722) * 255


def stats(src, out=None):
    y = luma(out if out is not None else src)
    d = {"mean": y.mean(), "p10": np.percentile(y, 10), "p50": np.percentile(y, 50), "p90": np.percentile(y, 90),
         "black": (y < 0.5).mean() * 100, "white": (y > 254.5).mean() * 100}
    if out is not None:
        y0 = luma(src)
        d["darker"] = ((y - y0) < -0.5).mean() * 100
        d["dabs"] = np.abs(out - src).mean() * 255
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--chrome", nargs="*", default=[], help="pairs: <Chrome still> <source frame>")
    a = ap.parse_args()
    groups = defaultdict(list)
    for p in sorted(Path(a.dir).glob("*.png")):
        m = re.match(r"(.+)_\d+$", p.stem)
        if m and not p.stem.startswith("chrome_"):
            groups[m.group(1)].append(p)
    f = lambda d, k: f"{d[k]:6.1f}"
    print("clip            filter | mean    p10    p50    p90 | black%  white% | darker%  mean|change|")
    for clip, ps in groups.items():
        src = np.concatenate([np.asarray(Image.open(p).convert("RGB"), dtype=np.float64).reshape(-1, 3) / 255 for p in ps])
        for name, out in (("source", None), ("old", lift_old(src)), ("new", lift_new(src))):
            d = stats(src, out)
            extra = f" | {d['darker']:6.1f}  {d['dabs']:6.2f}" if out is not None else ""
            print(f"{clip:16s} {name:6s} | {f(d, 'mean')} {f(d, 'p10')} {f(d, 'p50')} {f(d, 'p90')} | {d['black']:5.2f}  {d['white']:5.2f}{extra}")
    for chrome, srcf in zip(a.chrome[::2], a.chrome[1::2]):
        c = np.asarray(Image.open(chrome).convert("RGB"), dtype=np.float64) / 255
        s = np.asarray(Image.open(srcf).convert("RGB").resize((c.shape[1], c.shape[0]), Image.LANCZOS), dtype=np.float64) / 255
        for name, fn in (("old", lift_old), ("new", lift_new)):
            e = fn(s)
            print(f"chrome {Path(chrome).name} vs the {name} emulation on {Path(srcf).name}: mean luma {luma(c).mean():.1f} vs {luma(e).mean():.1f}, "
                  f"mean |diff| {np.abs(c - e).mean() * 255:.2f}")


if __name__ == "__main__":
    main()
