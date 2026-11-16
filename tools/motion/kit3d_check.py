"""kit3d's determinism check (standard/3D.md section 7): the same frame drawn twice by different routes must match.

Each still from kit3d_proof.mjs was rendered alone in a fresh tab (renderStill); each clip was rendered by six tabs in parallel
(renderMedia, concurrency 6), every tab with its own WebGL context, its own asset loads and its own frame order. If any pose, light,
sweep or grain depended on state (a clock, a previous frame, the order of frames), the clip's frame N would differ from the still of
frame N. Here both are decoded and compared: PSNR in dB over the whole frame and the largest local difference (|a - b| averaged
over 8x8 blocks, 0-255), each against the CODEC FLOOR: the same still sent through the clip's own path (JPEG q92 frames, x264 CRF 16, yuv420p) and compared back. A deterministic frame differs
from its still only as much as the codec does; anything a tab drew differently (a pose, a colour, a missing texture) shows as a block
far above the floor. Verdict: SAME when the worst block is within 12 of the floor's worst block, else DIFF with where it is.
(The kind of fault it catches: a colour changed in place that the 3D renderer never saw, so a pin stays ink in the clip while its
still shows it in the brand colour.)

  PIPE tools/motion/kit3d_check.py <the proof's folder, e.g. MEDIA/videos/kit3d/run1>
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

root = Path(sys.argv[1])
proof = json.loads((root / 'proof.json').read_text(encoding='utf-8'))
rows = []
for st in proof['stills']:
    clip = root / 'clips' / f"{st['comp']}.mp4"
    if not clip.exists():
        continue
    # the clip's frame N, decoded exactly (select by frame number, no seek rounding)
    raw = subprocess.run([FFMPEG, '-v', 'error', '-i', str(clip), '-vf', f"select=eq(n\\,{st['frame']})", '-vframes', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    a = np.asarray(Image.open(st['file']).convert('RGB')).astype(np.float32)
    h, w = a.shape[:2]
    b = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)
    # the codec floor: the still through the clip's path
    tmp = root / '_floor'
    tmp.mkdir(exist_ok=True)
    Image.fromarray(a.astype(np.uint8)).save(tmp / 'f.jpg', quality=92)
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', str(tmp / 'f.jpg'), '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                    str(tmp / 'f.mp4')], check=True)
    c = np.frombuffer(subprocess.run([FFMPEG, '-v', 'error', '-i', str(tmp / 'f.mp4'), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                     capture_output=True, check=True).stdout, np.uint8).reshape(h, w, 3).astype(np.float32)

    def measure(x, y):
        mse = float(((x - y) ** 2).mean())
        d = np.abs(x - y).mean(axis=2)
        bl = d[: h // 8 * 8, : w // 8 * 8].reshape(h // 8, 8, w // 8, 8).mean(axis=(1, 3))
        by, bx = np.unravel_index(int(bl.argmax()), bl.shape)
        return (99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)), float(bl.max()), (int(bx * 8), int(by * 8))

    psnr, bmax, where = measure(a, b)
    fpsnr, fmax, _ = measure(a, c)
    same = bmax <= fmax + 12
    rows.append({'comp': st['comp'], 'frame': st['frame'], 'psnr_db': round(psnr, 2), 'floor_psnr_db': round(fpsnr, 2),
                 'block_max': round(bmax, 1), 'floor_block_max': round(fmax, 1), 'worst_at': where, 'same': same})
    print(f"{st['comp']:15s} f{st['frame']:<4d} PSNR {psnr:6.2f} dB (codec floor {fpsnr:6.2f})  worst 8x8 block {bmax:5.1f} "
          f"(floor {fmax:5.1f}) at {where}  {'SAME' if same else 'DIFF'}")
(root / 'check.json').write_text(json.dumps(rows, indent=1), encoding='utf-8')
shutil.rmtree(root / '_floor', ignore_errors=True)
print(f"{sum(r['same'] for r in rows)} of {len(rows)} frames the same as their stills (within the codec)")
