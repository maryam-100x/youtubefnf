"""A clip that opens or closes inside a fade or a dissolve: to the viewer a few frames of a picture fading in or out read as a flash
frame. The cut scans (a prep's scene score, the edge histogram jump) see hard cuts only; a dissolve or a fade changes the picture
smoothly over 0.3-0.8 s, so it needs its own test.

For each span the first and last WIN seconds are read against the span's own middle (30 fps frames at 96x54, grey):
  FADE      the mean brightness slides one way by 12% or more of the span's level and 20 grey levels or more inside the window
            (80% of the steps the same way)
            and faster than 3x the middle's own drift;
  DISSOLVE  some 0.3 s of the window changes the picture 2.2x faster than the span's own median motion (mean absolute pixel change
            per frame) and by more than 0.6 a frame, smoothly (no single frame over 6: not a cut). A brightness histogram barely moves
            when a logo fades over a dark skyline (0.04 against 0.008 a frame); the pixels do (1.05 against 0.35 a frame, 3.0x).
Use: as a module, scan(src, a, b) -> [(edge, kind, detail)]; or

  PIPE tools/motion/qa_fades.py tools/motion/prep<id>.py [--only name ...]   (every CLIPS span of a prep file: its CLIPS and DL)
  PIPE tools/motion/qa_fades.py --span <src> <a> <b>"""
import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

WIN = 0.6
FPS = 30


def frames(src, a, b):
    r = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(src), "-vf",
                        f"fps={FPS},scale=96:54,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.uint8)
    n = len(x) // (96 * 54)
    return x[:n * 96 * 54].reshape(n, 54, 96).astype(np.float64)


def hist_d(fr):
    H = np.stack([np.histogram(f, 32, (0, 256))[0] / f.size for f in fr])
    return np.abs(np.diff(H, axis=0)).sum(1) / 2


B_W, B_H, B_BLK, B_R = 192, 108, 12, 5   # the motion test's frame, block and search (px at 192x108)


def unexplained(f0, f1):
    """the share of a frame-to-frame change no motion explains: each 12-px block of the second frame takes its best shift (+-5 px) in the
    first; ~1.0 = no shift helps (a cross-fade, a fade, a light), low = the picture moved (a camera move, a person walking, a crane shot)"""
    pad = np.pad(f0, B_R, mode="edge")
    zero = best = 0.0
    for by in range(0, B_H - B_BLK + 1, B_BLK):
        for bx in range(0, B_W - B_BLK + 1, B_BLK):
            blk = f1[by:by + B_BLK, bx:bx + B_BLK]
            z = float(np.abs(blk - f0[by:by + B_BLK, bx:bx + B_BLK]).sum())
            m = z
            for dy in range(-B_R, B_R + 1):
                for dx in range(-B_R, B_R + 1):
                    s = float(np.abs(blk - pad[by + B_R + dy:by + B_R + dy + B_BLK, bx + B_R + dx:bx + B_R + dx + B_BLK]).sum())
                    if s < m:
                        m = s
            zero += z
            best += m
    return best / max(zero, 1e-6)


DISSOLVE_UNEXPLAINED = 0.8   # see confirm_dissolve
FADE_DARK, FADE_BRIGHT = 30, 225


def confirm_dissolve(src, a, b, edge):
    """A DISSOLVE candidate is kept only when motion doesn't explain its change: a take's own motion (a crane shot, a person walking,
    smoke, a camera turning) leaves an unexplained share of 0.24-1.00 (median 0.74), a real logo dissolve 1.00. Kept at >= 0.8: the
    real dissolves and most re-cut ones stay, about three in four by-design motions drop."""
    lo, hi = (max(0.0, a - 0.1), a + WIN + 0.1) if edge == "head" else (max(0.0, b - WIN - 0.1), b + 0.1)
    r = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-ss", f"{lo:.3f}", "-t", f"{hi - lo:.3f}", "-i", str(src), "-vf",
                        f"fps={FPS},scale={B_W}:{B_H},format=gray", "-f", "rawvideo", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.uint8)
    n = len(x) // (B_W * B_H)
    if n < 4:
        return True, None
    fr = x[:n * B_W * B_H].reshape(n, B_H, B_W).astype(np.float32)
    pix = np.abs(np.diff(fr, axis=0)).mean((1, 2))
    k = min(9, len(pix))
    run = np.convolve(pix, np.ones(k) / k, mode="valid")
    j = int(np.argmax(run))
    rs = [unexplained(fr[i], fr[i + 1]) for i in range(j, min(j + k, n - 1)) if pix[i] > 0.3]
    u = float(np.median(rs)) if rs else 1.0
    return u >= DISSOLVE_UNEXPLAINED, u


def confirm_fade(src, a, b, edge):
    """A FADE candidate is kept only when the picture goes to or comes from black or white within 0.6 s past the play's edge: a camera's
    own exposure change (turning into the sun, into shade, a lightning flash, a door opening) never reaches under ~49 grey, while a
    real fade to black or a logo's dissolve does"""
    lo, hi = (max(0.0, a - 0.6), a + 0.6) if edge == "head" else (max(0.0, b - 0.6), b + 0.6)
    L = frames(src, lo, hi).mean((1, 2))
    if not len(L):
        return True, None
    return bool(L.min() < FADE_DARK or L.max() > FADE_BRIGHT), (float(L.min()), float(L.max()))


def scan(src, a, b, confirm=True):
    """[(edge, kind, detail)]; confirm=False gives the raw candidates (before the motion and black-or-white tests)"""
    out = []
    for edge, kind, msg in scan_raw(src, a, b):
        if confirm and kind == "DISSOLVE":
            keep, u = confirm_dissolve(src, a, b, edge)
            if not keep:
                continue
            msg += f"; no motion explains it ({u:.2f} of the change left after each block's best shift)"
        elif confirm and kind == "FADE":
            keep, lum = confirm_fade(src, a, b, edge)
            if not keep:
                continue
            msg += f"; it reaches {'black' if lum and lum[0] < FADE_DARK else 'white'} within 0.6 s"
        out.append((edge, kind, msg))
    return out


def scan_raw(src, a, b):
    fr = frames(src, a, b)
    n, w = len(fr), int(WIN * FPS)
    if n < 6:   # a span too short to read (a play of a few frames gives an empty edge): no fade to judge
        return []
    if n < 3 * w:
        w = max(4, n // 3)
    L = fr.mean((1, 2))
    pix = np.abs(np.diff(fr, axis=0)).mean((1, 2))
    mid_pix = float(np.median(pix[w:n - w - 1])) if n > 2 * w + 2 else float(np.median(pix))
    mid_drift = float(np.median(np.abs(np.diff(L[w:n - w])))) if n > 2 * w + 1 else 0.0
    level = max(float(np.median(L)), 1.0)
    out = []
    for edge, sl, ds in (("head", slice(0, w), slice(0, w - 1)), ("tail", slice(n - w, n), slice(n - w, n - 1))):
        lw = L[sl]
        steps = np.diff(lw)
        same = max((steps > 0).mean(), (steps < 0).mean()) if len(steps) else 0
        slide = abs(lw[-1] - lw[0]) / level
        # and at least 20 grey levels in all (a logo glowing 11 -> 16 on black is the source's own animation; a fade to black is 122 -> 49)
        if slide >= 0.12 and abs(lw[-1] - lw[0]) >= 20 and same >= 0.8 and np.abs(steps).mean() > 3 * max(mid_drift, 0.05):
            out.append((edge, "FADE", f"brightness {lw[0]:.0f} -> {lw[-1]:.0f} over {WIN} s ({slide:.0%} of the span's level)"))
            continue
        pw = pix[ds][1:] if edge == "head" else pix[ds]     # the head's first step is fps's repeated frame
        k = 9
        if len(pw) >= k:
            run = np.convolve(pw, np.ones(k) / k, mode="valid")
            j = int(np.argmax(run))
            if run[j] > 2.2 * max(mid_pix, 0.05) and run[j] > 0.6 and float(pw[j:j + k].max()) < 6:
                out.append((edge, "DISSOLVE", f"0.3 s changing {run[j]:.2f} a frame, {run[j] / max(mid_pix, 0.05):.1f}x the span's own motion "
                                              f"({mid_pix:.2f}), smoothly: a dissolve or a fade-in at the clip's {edge}"))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prep", nargs="?")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--span", nargs=3)
    a = ap.parse_args()
    if a.span:
        src, t0, t1 = a.span[0], float(a.span[1]), float(a.span[2])
        hits = scan(src, t0, t1)
        print("\n".join(f"{e} {k}: {msg}" for e, k, msg in hits) or "clean")
        sys.exit(1 if hits else 0)
    if not a.prep:
        ap.error("give a prep file or --span")
    spec = importlib.util.spec_from_file_location("prep", a.prep)
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    bad = 0
    for name, (src, t0, t1, *_) in P.CLIPS.items():
        if a.only and name not in a.only:
            continue
        hits = scan(P.DL / src, t0, t1)
        bad += bool(hits)
        print(f"{'FLAG' if hits else 'ok  '} {name}: " + ("; ".join(f"{e} {k}: {msg}" for e, k, msg in hits) or "clean"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
