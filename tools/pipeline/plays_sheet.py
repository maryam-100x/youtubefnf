"""Every clip play of a composition as three frames (first, middle, last) on sheets for the eye, with its shot, time, source and in-point;
plays whose frames are black or a card on black are listed apart. Why: a play can show a rating card for over a second; the edge scan
passes it (no cut near its edges) and the proof stills may never look at that shot. One look at every play's frames catches an
in-point that lands on a rating card, black, an end card or a logo nobody meant.

  PIPE tools/pipeline/pipe.py <video> plays [--version N]   (the usual way: a fresh audit report, then the sheets in pipeline/plays_v<N>/)
  PIPE tools/pipeline/plays_sheet.py <audit json> <out dir> [--pub <dir>]
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, PUBLIC  # noqa: E402

W, H = 200, 112
VIDEO = ("mp4", "mkv", "mov", "webm")


def _frame(f, t):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(f), "-frames:v", "1", "-vf", f"scale={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if len(raw) < W * H * 3:
        return Image.new("RGB", (W, H), (90, 0, 0))   # red: the frame could not be read
    return Image.frombytes("RGB", (W, H), raw[: W * H * 3])


def make_sheets(plays, roots, out, per=44, cols=4):
    """plays: the audit report's plays ({shot, at, src, from, len}); roots: folders to find each src in, first match wins.
    Writes out/plays_NN.jpg; returns [(shot, at, src, in, [luma first, mid, last], [dark share first, mid, last])] of the dark ones."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    plays = [p for p in plays if p["src"].rsplit(".", 1)[-1].lower() in VIDEO]
    flags = []
    for k in range(0, len(plays), per):
        chunk = plays[k: k + per]
        rows = -(-len(chunk) // cols)
        sheet = Image.new("RGB", (cols * (3 * W + 12), rows * (H + 18)), (24, 24, 24))
        dr = ImageDraw.Draw(sheet)
        for i, p in enumerate(chunk):
            f = next((Path(r) / p["src"] for r in roots if (Path(r) / p["src"]).exists()), Path(roots[-1]) / p["src"])
            a, n = float(p["from"]), float(p["len"])
            ims = [_frame(f, a + 0.05), _frame(f, a + n / 2), _frame(f, a + n - 0.06)]
            grey = [im.convert("L") for im in ims]
            lum = [ImageStat.Stat(g).mean[0] for g in grey]
            dark = [sum(g.histogram()[:24]) / (W * H) for g in grey]   # share of pixels darker than 24
            x0, y0 = (i % cols) * (3 * W + 12), (i // cols) * (H + 18)
            for j, im in enumerate(ims):
                sheet.paste(im, (x0 + j * W, y0 + 18))
            bad = any(v < 18 for v in lum) or any(d > 0.8 for d in dark)
            if bad:
                flags.append((p["shot"], round(float(p["at"]), 2), p["src"], a, [round(v) for v in lum], [round(d, 2) for d in dark]))
            mm, ss = divmod(float(p["at"]), 60)
            dr.text((x0 + 3, y0 + 3), f"#{p['shot']} {int(mm)}:{ss:05.2f} {Path(p['src']).stem[:30]} @{a:.2f}+{n:.2f}",
                    fill=(255, 90, 90) if bad else (230, 230, 230))
        sheet.save(out / f"plays_{k // per + 1:02d}.jpg", quality=85)
    return flags


def report(flags, out):
    lines = [f"{len(flags)} play(s) with a black or card-on-black frame (each one looked at: a logo or a night shot may be meant):"]
    lines += [f"  shot {s} at {t:.2f}: {src} @{a:.2f}  luma {l}  dark {d}" for s, t, src, a, l, d in flags]
    (Path(out) / "flags.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    pub = args[args.index("--pub") + 1] if "--pub" in args else None
    pos = [x for i, x in enumerate(args) if not x.startswith("--") and (i == 0 or args[i - 1] != "--pub")]
    rep = json.load(open(pos[0], encoding="utf-8"))
    roots = ([pub] if pub else []) + [str(PUBLIC)]
    fl = make_sheets(rep["plays"], roots, pos[1])
    print(report(fl, pos[1]))
