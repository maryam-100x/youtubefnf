"""Read an on-screen interface exactly: native-resolution crops of one frame of a brain master, for the description pass's `ui` field
(DESCRIBE.md). The sheets' 480-px tiles can't show a small icon or a digit; these crops are the file's own pixels.
Several describers can run it side by side: every ffmpeg call holds one lock (WORK/zoom/ffmpeg.lock), so one ffmpeg runs at a time
and the machine stays free for other jobs; `--lock CMD ...` runs any other command under the same lock.

  EDIT tools/footage/brain_zoom.py A1 41983          the four corners where an interface usually sits (top-left, top-right,
        bottom-left, bottom-right) in one image
  EDIT tools/footage/brain_zoom.py A1 41983 0.30 0.40 0.70 0.80     that region (fractions of the frame) at up to 1600 px wide
  EDIT tools/footage/brain_zoom.py A1 41983 full                     the whole frame at 1920x1080
  EDIT tools/footage/brain_zoom.py --lock ffmpeg ...                 a command under the lock
-> WORK/zoom/<KEY>_<FRAME>[_tag].jpg (printed). FRAME = the file's frame number (brain_lib.seek_time lands on it)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402
from sheetfont import font  # noqa: E402

OUT = B.WORK / "zoom"
LOCK = OUT / "ffmpeg.lock"


class Lock:
    """A directory lock: mkdir is atomic; a lock older than 15 minutes is a dead holder's."""

    def __enter__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while True:
            try:
                os.mkdir(LOCK)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(LOCK) > 900:
                        os.rmdir(LOCK)
                        continue
                except OSError:
                    pass
                if time.time() - t0 > 1800:
                    raise SystemExit("ffmpeg lock: waited 30 min")
                time.sleep(0.5)

    def __exit__(self, *a):
        try:
            os.rmdir(LOCK)
        except OSError:
            pass


def frame_png(key, f):
    """The frame as a lossless PNG at the file's own size (cached)."""
    src = OUT / f"_{B.key_file(key)}_{f}.png"
    if not src.exists():
        m = B.MASTERS[key]
        sp = B.WORK / "work" / f"{B.key_file(key)}_shots.json"     # the file's own rate, else 30
        fps = json.loads(sp.read_text(encoding="utf-8"))["fps"] if sp.exists() else 30.0
        with Lock():
            subprocess.run([B.FFMPEG, "-v", "error", "-y", "-ss", f"{B.seek_time(f, fps):.4f}", "-i", str(m["file"]), "-frames:v", "1", str(src)],
                           check=False)
    return src


def main():
    args = sys.argv[1:]
    if args and args[0] == "--lock":
        with Lock():
            sys.exit(subprocess.run(args[1:]).returncode)
    from PIL import Image, ImageDraw
    key, f = args[0], int(args[1])
    im = Image.open(frame_png(key, f)).convert("RGB")
    W, H = im.size
    fnt = font(22)
    rest = args[2:]
    kf = B.key_file(key)
    if rest == ["full"]:
        out = OUT / f"{kf}_{f}_full.jpg"
        im.resize((1920, 1080), Image.LANCZOS).save(out, quality=88)
    elif len(rest) == 4:
        x0, y0, x1, y1 = (float(v) for v in rest)
        c = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        if c.width > 1600:
            c = c.resize((1600, int(c.height * 1600 / c.width)), Image.LANCZOS)
        out = OUT / f"{kf}_{f}_{x0:.2f}_{y0:.2f}_{x1:.2f}_{y1:.2f}.jpg"
        c.save(out, quality=90)
    else:
        # the four corners where an on-screen interface usually sits (letterboxed sources keep their bars in the crop)
        regs = [("top-left", (0, 0, 0.26, 0.2)), ("top-right", (0.70, 0, 1, 0.3)), ("bottom-left", (0, 0.68, 0.3, 1)),
                ("bottom-right", (0.70, 0.70, 1, 1))]
        k = 0.75 * 3840 / W          # 4K pixels shown at 75%: a small icon is ~40 px, a digit ~30 px
        crops = []
        for n, (a, b, c, d) in regs:
            cr = im.crop((int(a * W), int(b * H), int(c * W), int(d * H)))
            crops.append((n, cr.resize((int(cr.width * k), int(cr.height * k)), Image.LANCZOS)))
        cw = max(c.width for _, c in crops)
        r0 = max(crops[0][1].height, crops[1][1].height)
        r1 = max(crops[2][1].height, crops[3][1].height)
        sheet = Image.new("RGB", (2 * cw + 12, r0 + r1 + 12), (255, 0, 255))
        dr = ImageDraw.Draw(sheet)
        for (n, c), (x, y) in zip(crops, [(0, 0), (cw + 12, 0), (0, r0 + 12), (cw + 12, r0 + 12)]):
            sheet.paste(c, (x, y))
            dr.text((x + 6, y + c.height - 28), f"{key} f{f} {n}", fill=(255, 255, 0), font=fnt)
        out = OUT / f"{kf}_{f}_ui.jpg"
        sheet.save(out, quality=90)
    print(out)


if __name__ == "__main__":
    main()
