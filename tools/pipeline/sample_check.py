"""Check C of the gate: a sample is compared with the version the creator watched before it goes to them. A sample can go out with a
fix that never landed (a prep step that kept the old crop sends the old picture as "fixed"), so every sample shows where its picture
and its sound differ from the old version, and each change the chat claims must be among them.

  PIPE tools/pipeline/sample_check.py <old.mp4> <old_at_s> <new.mp4> [--claim a-b ...]

The sample (new.mp4, from its 0) is lined up on the old file near old_at_s; picture at 60 frames a second (160x90 grey, so no frame lands between two of the other) and sound in
50-ms windows. Prints the spans that changed; a --claim span (seconds in the sample) with no change in it fails (exit 1)."""
import argparse
import subprocess
import sys

import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE  # noqa: E402


def frames(path, at, dur):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{at:.3f}", "-t", f"{dur:.3f}", "-i", path, "-an", "-vf", "fps=60,scale=160:90,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    n = len(raw) // (160 * 90)
    return np.frombuffer(raw[: n * 14400], dtype=np.uint8).reshape(n, 90, 160).astype(np.float32)


def sound(path, at, dur):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{at:.3f}", "-t", f"{dur:.3f}", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = len(x) // 800
    return x[: n * 800].reshape(n, 800)


def spans(mask, step):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j < len(mask) and mask[j]:
                j += 1
            out.append((round(i * step, 2), round(j * step, 2)))
            i = j
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("old")
    ap.add_argument("old_at", type=float)
    ap.add_argument("new")
    ap.add_argument("--claim", action="append", default=[], help="a-b seconds in the sample where a change was made")
    a = ap.parse_args()
    dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.new], capture_output=True, text=True).stdout.strip())
    # line the sample up on the old file first (a cut lands a few frames off where it was asked: every frame then looks "changed"):
    # the picture's offset within +-0.5 s that matches best, the sound's by its envelope's cross-correlation
    pad = 0.5
    fo, fn = frames(a.old, max(0.0, a.old_at - pad), dur + 2 * pad), frames(a.new, 0, dur)
    lead = round(min(pad, a.old_at) * 60)
    best = min(range(0, max(1, len(fo) - len(fn) + 1)), key=lambda k: float(np.median(np.abs((fo[k:k + len(fn)] - fo[k:k + len(fn)].mean()) - (fn[: len(fo) - k] - fn.mean())).mean(axis=(1, 2)))))
    fo = fo[best:]
    n = min(len(fo), len(fn))
    # another encode can shift the levels (a 4K BT.709 finish against a quick 1080p sample: +4.5 grey on every frame of the same picture):
    # the sample's brightness and contrast are matched to the old file's over the whole span, so only a real change stays
    a_, b_ = fo[:n].astype(np.float32), fn[:n].astype(np.float32)
    b_ = (b_ - b_.mean()) * (a_.std() / max(b_.std(), 1e-6)) + a_.mean()
    pd = np.abs(a_ - b_).mean(axis=(1, 2))
    so, sn = sound(a.old, max(0.0, a.old_at - pad), dur + 2 * pad), sound(a.new, 0, dur)
    eo, en = np.sqrt((so ** 2).mean(axis=1)), np.sqrt((sn ** 2).mean(axis=1))
    sb = min(range(0, max(1, len(eo) - len(en) + 1)), key=lambda k: float(np.abs(eo[k:k + len(en)] - en[: len(eo) - k]).mean()))
    so = so[sb:]
    m = min(len(so), len(sn))
    sd = 20 * np.log10(np.sqrt(((so[:m] - sn[:m]) ** 2).mean(axis=1)) + 1e-9)
    print(f"lined up: picture {(best - lead) / 60:+.3f} s, sound {(sb - round(min(pad, a.old_at) * 20)) / 20:+.2f} s against {a.old_at}")
    pic = spans(pd > 3.0, 1 / 60)   # a re-encode or another size moves a 160x90 grey frame by ~1; a real change by 5+
    snd = spans(sd > -30, 0.05)   # the same sound through another encode differs by ~-40 dB; a changed word or effect by -25 or more
    print(f"picture changed: {pic or 'nowhere'}")
    print(f"sound changed:   {snd or 'nowhere'}")
    bad = []
    for c in a.claim:
        x, y = (float(v) for v in c.split("-"))
        hit = any(s0 < y and s1 > x for s0, s1 in pic + snd)
        print(f"claim {c}: {'changed' if hit else 'NOTHING CHANGED: the fix did not land'}")
        if not hit:
            bad.append(c)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
