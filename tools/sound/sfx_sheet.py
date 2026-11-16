"""Every effect on its frames, for the eye: does the picture show the action the sound stands for, at that moment? (An effect on a shot
that opens after its action, or a marking swoosh on words that only light, sounds wrong even when its level is right.) One row per
effect: the frame 0.12 s before its impact, at it and 0.2 s after, labelled with its time, its file and the cue sheet's note, plus its
loudness and source from score.py's check when a report is given. A filter for the eye, not the proof: read every row against its note
before the creator hears the mix.

  EDIT tools/sound/sfx_sheet.py <cues.py> <finished.mp4> <out.jpg>"""
import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

OFFS = (-0.12, 0.0, 0.2)
# the label fonts: Windows' Segoe UI, else macOS' Helvetica / Arial, else PIL's own (never a crash for a missing font)
FONTS = [("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
         ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttc"),
         ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
         ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf")]


def fonts():
    for reg, bold in FONTS:
        try:
            return ImageFont.truetype(reg, 15), ImageFont.truetype(bold, 16)
        except OSError:
            continue
    f = ImageFont.load_default()
    return f, f


def frame(video, t, w):
    cmd = [FFMPEG, "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "image2pipe",
           "-vcodec", "png", "-"]
    out = subprocess.run(cmd, capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(out)).convert("RGB") if out else None


def main():
    cues, video, out = sys.argv[1], sys.argv[2], sys.argv[3]
    spec = importlib.util.spec_from_file_location("cues", cues)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fx = sorted(mod.SFX, key=lambda s: s.t)
    probe = frame(video, 0.5, 320)
    vertical = probe is not None and probe.height > probe.width
    w = 150 if vertical else 320
    tiles = []
    for s in fx:
        ims = [frame(video, s.t + o, w) for o in OFFS]
        tiles.append((s, ims))
    th = max((im.height for _, ims in tiles for im in ims if im), default=180)
    label_w = 460
    W = label_w + 3 * (w + 6) + 6
    H = 40 + len(tiles) * (th + 8)
    sheet = Image.new("RGB", (W, H), (16, 18, 22))
    d = ImageDraw.Draw(sheet)
    font, bold = fonts()
    d.text((8, 8), f"{Path(cues).name} on {Path(video).name}: each effect at -0.12 s, its impact, +0.2 s (the picture shows its action)",
           fill=(255, 210, 31), font=bold)
    y = 40
    for s, ims in tiles:
        d.text((8, y + 2), f"{s.t:7.2f} s   db {s.db:+.0f}   {Path(s.path).name[:34]}", fill=(255, 255, 255), font=bold)
        for k, line in enumerate(textwrap.wrap(s.note or "(no note: say in three words what it stands for)", 56)[:5]):
            d.text((8, y + 24 + 18 * k), line, fill=(190, 196, 204), font=font)
        x = label_w
        for o, im in zip(OFFS, ims):
            if im:
                sheet.paste(im, (x, y))
            d.text((x + 4, y + 2), f"{o:+.2f}", fill=(255, 210, 31), font=font)
            x += w + 6
        y += th + 8
    sheet.save(out, quality=88)
    print(f"{len(tiles)} effects -> {out}")


if __name__ == "__main__":
    main()
