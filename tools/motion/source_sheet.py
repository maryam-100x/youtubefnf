"""A whole source on contact sheets at 1 fps, each frame marked fresh or used: every candidate source is scanned WHOLE first, and its best
moments for the line go on the options board (options_board.py), so the pick is made from everything the source holds.

Every second of the source becomes a 256x144 thumbnail with its time under it; a frame that a past video's clip already played
(qa_reused.py's fingerprints: the 9x8 dhash within --bits of a frame of an old clip, PUBLIC/reused_cache.json) gets a red frame and the
old video's folder; a frame inside a span this video already cut (its prep manifests, --manifests, by source file name and time) gets an
orange frame and the clip's name; fresh frames stay plain. Pages of 60 s (10 x 6) go to <out>_p<NN>.jpg and the status of every second
to <out>.json ({t: "fresh" | "used:<video>/<clip>" | "own:<clip>" | "flat"}), so a board can be built from fresh moments only.

  PIPE tools/motion/source_sheet.py <source video> <out prefix> --clips PUBLIC/<video>/clips [--manifests <prep>_clips.json ...]
      [--vf crop=...] [--from s] [--to s] [--bits 6] [--label "the source's launch clip (2024)"]
A letterboxed source gets its crop in --vf (the old clips were cut filled, so the bars would change its fingerprint)."""
import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import FFMPEG  # noqa: E402

sys.path.insert(0, str(HERE))
import qa_reused  # noqa: E402

TW, TH, COLS, ROWS = 256, 144, 10, 6
GW, GH = qa_reused.W, qa_reused.H


def own_spans(src, manifests):
    """[(t0, t1, clip)] of every clip this video already cut from this source file (its prep manifests {name: [source, in, out, ...]},
    or the preps' CLIPS)"""
    return [(a, b, name) for name, s, a, b in qa_reused.manifest_spans(manifests) if Path(s).name == src.name.lower()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--vf", default="")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=0.0)
    ap.add_argument("--bits", type=int, default=6)
    ap.add_argument("--label", default="")
    ap.add_argument("--clips", required=True, help="this video's own clips folder (PUBLIC/<video>/clips): never counted as a past video")
    ap.add_argument("--manifests", nargs="*", default=[], help="this video's prep manifests (<prep>_clips.json): its own spans")
    a = ap.parse_args()
    src, out = Path(a.video), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pre = (a.vf + ",") if a.vf else ""
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-threads", "3", "-ss", f"{a.t0:.3f}", "-i", str(src)]
    cmd += (["-t", f"{a.t1 - a.t0:.3f}"] if a.t1 else []) + ["-an", "-vf", pre + f"fps=1,scale={TW}:{TH}:flags=area", "-pix_fmt", "rgb24",
                                                            "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    n = len(raw) // (TW * TH * 3)
    frames = [np.frombuffer(raw[i * TW * TH * 3:(i + 1) * TW * TH * 3], np.uint8).reshape(TH, TW, 3) for i in range(n)]
    cache = json.loads(qa_reused.CACHE.read_text(encoding="utf-8")) if qa_reused.CACHE.exists() else {}
    clips = Path(a.clips)
    others = sorted(p for p in qa_reused.MEDIA.glob("*/clips/*.mp4") if p.parent.parent.resolve() != clips.parent.resolve())
    olds, bits_old, idx, _ = qa_reused.old_array(cache, others)
    spans = own_spans(src, sorted({f for m in a.manifests for f in (glob.glob(m) or [m])}))
    status = {}
    for i, fr in enumerate(frames):
        t = a.t0 + i
        g = np.asarray(Image.fromarray(fr).convert("L").resize((GW, GH), Image.BOX), np.uint8)
        h, fl = qa_reused.dhash_arr(g)
        st = "fresh"
        if fl:
            st = "flat"
        elif bits_old is not None:
            d = qa_reused.dist(bits_old, h)   # the old hashes as bytes [n x 8]
            j = int(d.argmin())
            if d[j] <= a.bits:
                st = f"used:{olds[idx[j]].parent.parent.name}/{olds[idx[j]].stem}"
        hit = [c for s0, s1, c in spans if s0 - 0.5 <= t <= s1 + 0.5]
        if st in ("fresh", "flat") and hit:
            st = f"own:{hit[0]}"
        status[f"{t:.0f}"] = st
    font = ImageFont.load_default()
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):   # Windows, macOS, Linux names (Pillow matches the file name exactly)
        try:
            font = ImageFont.truetype(name, 15)
            break
        except OSError:
            continue
    per = COLS * ROWS
    pages = (len(frames) + per - 1) // per
    for p in range(pages):
        sheet = Image.new("RGB", (COLS * TW, ROWS * (TH + 20) + 26), "white")
        d = ImageDraw.Draw(sheet)
        d.text((6, 4), f"{src.name}  {a.label}  p{p + 1}/{pages}   red = a past video played it, orange = this video already cut it",
               fill="black", font=font)
        for k in range(per):
            i = p * per + k
            if i >= len(frames):
                break
            x, y = (k % COLS) * TW, 26 + (k // COLS) * (TH + 20)
            sheet.paste(Image.fromarray(frames[i]), (x, y))
            t = a.t0 + i
            st = status[f"{t:.0f}"]
            col = "black"
            if st.startswith("used:"):
                col = (220, 0, 0)
                d.rectangle([x + 1, y + 1, x + TW - 2, y + TH - 2], outline=col, width=5)
            elif st.startswith("own:"):
                col = (240, 130, 0)
                d.rectangle([x + 1, y + 1, x + TW - 2, y + TH - 2], outline=col, width=5)
            tag = st.split(":", 1)[1].split("/")[0][:14] if ":" in st else ""
            d.text((x + 3, y + TH + 2), f"{int(t // 60)}:{t % 60:04.1f} {tag}", fill=col, font=font)
        sheet.save(f"{out}_p{p + 1:02d}.jpg", quality=82)
    out.with_suffix(".json").write_text(json.dumps({"source": str(src), "vf": a.vf, "status": status}, indent=0), encoding="utf-8")
    used = sum(v.startswith("used:") for v in status.values())
    own = sum(v.startswith("own:") for v in status.values())
    print(f"{src.name}: {len(frames)} s on {pages} page(s) -> {out}_pNN.jpg; {used} s used by past videos, {own} s cut by this video, "
          f"{len(frames) - used - own} s fresh or flat")


if __name__ == "__main__":
    main()
