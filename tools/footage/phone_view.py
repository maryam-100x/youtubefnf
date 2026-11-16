"""A Short's frame as an iPhone shows it, with the real YouTube UI on top: the check every Short's text passes before delivery, so no
text sits behind the app's own buttons and labels.

Measured on two screenshots of Shorts playing in the YouTube app (iPhone, 1179x2556): YouTube scales the 1080x1920 frame by 1.204 to
fill the screen from its very top down to the nav bar (y 2313) and crops ~50 px off each side. In frame pixels that puts the status bar
(clock, signal, battery) over y 0-148, the search/menu icons over x>=808, y 180-231, the like/comment/save/share/remix column over x>=900
from y ~1040 down, and the channel name and title over y>=1645 (x<=760). Text near the top ends up behind the status bar. Rule: no text
above y 260.

The UI layer is the pixels that are white in both screenshots (the parts that don't change between Shorts) plus the nav bar; it is
built once from the creator's own two screenshots and kept outside the repo (MEDIA/ui/phone_ui_iphone.png: the nav bar carries the
account's picture).

  PIPE tools/footage/phone_view.py <video.mp4> <seconds> <out.png>     # one frame
  PIPE tools/footage/phone_view.py <frame.png> - <out.png>
  PIPE tools/footage/phone_view.py --build-ui <shot1.png> <shot2.png>   # build the UI layer from two 1179x2556 screenshots (the second
                                                                        # one with a dark picture behind the status bar)"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, MEDIA  # noqa: E402

UI = MEDIA / "ui" / "phone_ui_iphone.png"
SW, SH = 1179, 2556            # the screen
SCALE = 1.204                  # frame px -> screen px (the 300-px title bar ended at screen row 361; the frame's bottom at the nav, 2313)
NAV = 2313                     # the nav bar's top row on the screen
TEXT_TOP = 260                 # frame px: no text above this (status bar 0-148, search/menu icons 180-231)
SAFE_RIGHT = 900               # frame px: the like/comment column starts here (from y ~1040 down)
BOTTOM_UI = 1645               # frame px: the channel name and title start here


def build_ui(a_path, b_path):
    a = np.asarray(Image.open(a_path).convert("RGB")).astype(int)
    b = np.asarray(Image.open(b_path).convert("RGB")).astype(int)
    assert a.shape[:2] == b.shape[:2] == (SH, SW), "expects two 1179x2556 screenshots"

    def white(x):
        return (x.min(2) > 205) & (x.max(2) - x.min(2) < 40)

    zone = np.zeros((SH, SW), bool)
    zone[150:300, 880:] = True      # search / menu icons
    zone[1200:NAV, 1000:] = True    # like / comment / save / share / remix / the sound button
    m = white(a) & white(b) & zone  # the parts that are the same in both: UI, not picture
    m[:119] = white(b)[:119]        # the status bar from the second shot (a dark picture behind it there)
    m[NAV:] = True                  # the nav bar is opaque UI
    out = np.zeros((SH, SW, 4), np.uint8)
    out[..., :3] = np.where(m[..., None], a, 0)
    out[..., 3] = m * 255
    # the nav bar keeps its own colours; the glyphs elsewhere are drawn white
    out[:NAV, :, :3][m[:NAV]] = 255
    UI.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out, "RGBA").save(UI)
    print(f"UI layer -> {UI} ({int(m[:NAV].sum())} glyph pixels above the nav bar)")


def frame_of(src, t):
    if str(src).lower().endswith((".png", ".jpg", ".jpeg")):
        return Image.open(src).convert("RGB")
    raw = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return Image.frombytes("RGB", (1080, 1920), raw)


def phone(img, guides=True):
    if not UI.exists():
        raise SystemExit(f"no UI layer at {UI}: build it once with --build-ui <shot1.png> <shot2.png>")
    w, h = round(1080 * SCALE), round(1920 * SCALE)
    big = img.resize((w, h), Image.LANCZOS)
    x0 = (w - SW) // 2
    screen = Image.new("RGB", (SW, SH), (0, 0, 0))
    screen.paste(big.crop((x0, 0, x0 + SW, min(h, NAV))), (0, 0))
    screen.paste(Image.open(UI), (0, 0), Image.open(UI))
    if guides:
        d = ImageDraw.Draw(screen)
        y = round(TEXT_TOP * SCALE)
        d.line([(0, y), (SW, y)], fill=(255, 40, 40), width=2)  # text below this line
        xr = round(SAFE_RIGHT * SCALE) - x0
        d.line([(xr, round(1040 * SCALE)), (xr, NAV)], fill=(255, 40, 40), width=2)
        yb = round(BOTTOM_UI * SCALE)
        d.line([(0, yb), (round(760 * SCALE) - x0, yb)], fill=(255, 40, 40), width=2)
    return screen


if __name__ == "__main__":
    if sys.argv[1] == "--build-ui":
        build_ui(sys.argv[2], sys.argv[3])
    else:
        phone(frame_of(sys.argv[1], sys.argv[2])).save(sys.argv[3])
        print(sys.argv[3])
