"""render_bench.py: which render settings are fastest at the same picture quality, measured on a real stretch of a video.

  PIPE tools/pipeline/render_bench.py <video> [--frames a-b] [--variants a,b,...] [--out dir] [--scale x]
        --frames: the film frames every variant renders (default: 600 frames from the middle of the video)

One lean bundle and one heavy.py render ticket for all variants; each variant renders the same frames through render_parts.mjs (the
renderer the line uses) and is timed; then every variant's picture is compared with a reference (PNG frames, x264 lossless) by SSIM and
PSNR (ffmpeg's ssim and psnr filters), so a faster setting is adopted only at the quality of the current one. Writes <out>/bench.json and
<out>/bench.md. Re-run it after a Remotion upgrade or on a new computer: the numbers are the computer's own."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG, MOTION, NODE, RemotionJob, Video, find_video, frame_count, say, temp_env  # noqa: E402
import heavy  # noqa: E402

BASE = {"crf": 16, "preset": "slow", "concurrency": 6, "imageFormat": "jpeg", "jpegQuality": 92, "parallel": "auto"}
VARIANTS = {
    "ref":         {"crf": 1, "preset": "ultrafast", "imageFormat": "png", "parallel": "force"},   # the quality reference (Remotion
    #                                                                     refuses CRF 0 for H.264: CRF 1 on PNG frames, as near lossless as it allows)
    "base":        {},                                                   # the CLI's settings (slow, crf 16, conc 6, jpeg 92)
    "par":         {"parallel": "force"},                               # encode while rendering (Remotion 4.0.534's decision)
    "par_fast":    {"parallel": "force", "preset": "veryfast"},
    "par_fast14":  {"parallel": "force", "preset": "veryfast", "crf": 14},
    "par_ufast12": {"parallel": "force", "preset": "ultrafast", "crf": 12},
    "par_fast_c8": {"parallel": "force", "preset": "veryfast", "concurrency": 8},
    "par_fast_c4": {"parallel": "force", "preset": "veryfast", "concurrency": 4},
    "par_c8":      {"parallel": "force", "concurrency": 8},
    # the second round (a first pass measures each once, in order, and later runs gain from a warm file cache): a warm-up, then repeats
    "warm":        {},
    "base2":       {},
    "par_fast_c8_2": {"parallel": "force", "preset": "veryfast", "concurrency": 8},
    "par_fast_c10": {"parallel": "force", "preset": "veryfast", "concurrency": 10},
    # the third round: the adopted settings against the base ones, interleaved, two runs each (other load moves single runs ~10%)
    "base_a":      {},
    "adopt_a":     {"parallel": "force", "preset": "veryfast", "crf": 14, "concurrency": 8},
    "base_b":      {},
    "adopt_b":     {"parallel": "force", "preset": "veryfast", "crf": 14, "concurrency": 8},
    "base_off":    {"parallel": "off"},                                   # the base settings as Remotion runs them under ~5.7 GB free (encode after)
}


def measure_quality(a, ref):
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-i", str(a), "-i", str(ref), "-lavfi", "[0:v][1:v]ssim;[0:v][1:v]psnr", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace").stderr
    ssim = re.search(r"SSIM .*All:([\d.]+)", r)
    psnr = re.search(r"PSNR .*average:([\d.inf]+)", r)
    return (float(ssim.group(1)) if ssim else None, float(psnr.group(1)) if psnr and psnr.group(1) != "inf" else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--frames", help="film frames a-b (default: 600 frames from the middle of the video)")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--out")
    ap.add_argument("--scale", type=float)
    a = ap.parse_args()
    v = Video(find_video(a.video))
    if not a.frames:
        mid = v.frames() // 2
        a.frames = f"{max(0, mid - 300)}-{mid + 299}"
    f0, f1 = (int(x) for x in a.frames.split("-"))
    out = Path(a.out) if a.out else v.pipe_dir / f"render_bench_{time.strftime('%m%d_%H%M')}"
    out.mkdir(parents=True, exist_ok=True)
    names = [n for n in a.variants.split(",") if n]
    if "ref" not in names and not (out / "ref.mkv").exists():
        names = ["ref"] + names
    bj = out / "bench.json"
    res = json.loads(bj.read_text(encoding="utf-8")) if bj.exists() else {}   # a second run renders only --variants, keeps the rest
    with RemotionJob(f"render bench {v.id} {a.frames}", None):
        import pipe
        bundle = pipe.lean_bundle(v)
        try:
            for name in names:
                cfg = {**BASE, **VARIANTS[name]}
                f = out / f"{name}.mkv"
                if f.exists():
                    f.unlink()
                job = {"serveUrl": bundle, "comp": v.comp, "scale": a.scale or v.scale, "gl": v.gl, "timeoutMs": 120000,
                       "parts": [{"i": 0, "f0": f0, "f1": f1, "file": str(f)}], **cfg}
                jf = out / f"{name}.job.json"
                jf.write_text(json.dumps(job), encoding="utf-8")
                ram0 = heavy.memory()[0]
                t = time.time()
                r = pipe.run_watched([NODE, "render_parts.mjs", jf], MOTION, temp_env(), out / f"{name}.log", stall=300)
                secs = time.time() - t
                log = r.stdout
                enc = re.search(r"^ENC (.*)$", log, re.M)
                done = re.search(r"^DONE 0 (\d+) ([\d.]+)$", log, re.M)
                n = frame_count(f) if f.exists() else None
                res[name] = {"cfg": cfg, "wall_s": round(secs, 1), "render_s": float(done.group(2)) if done else None,
                             "fps": round((f1 - f0 + 1) / float(done.group(2)), 2) if done else None, "frames": n,
                             "mb": round(f.stat().st_size / 1e6, 1) if f.exists() else None, "enc": json.loads(enc.group(1)) if enc else None,
                             "free_ram_gb_before": round(ram0, 1), "ok": bool(done) and n == f1 - f0 + 1}
                say(f"{name}: {res[name]}")
        finally:
            pipe.lean_clean(bundle)
    ref = out / "ref.mkv"
    names = [n for n in VARIANTS if n in res]
    for name in names:
        if name != "ref" and res.get(name, {}).get("ok") and ref.exists() and (out / f"{name}.mkv").exists():
            res[name]["ssim"], res[name]["psnr"] = measure_quality(out / f"{name}.mkv", ref)
            say(f"{name}: SSIM {res[name]['ssim']} PSNR {res[name]['psnr']} against the lossless PNG reference")
    (out / "bench.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    b = res.get("base", {})
    lines = [f"# Render benchmark {v.id} frames {a.frames} ({f1 - f0 + 1} frames, x{a.scale or v.scale}) {time.strftime('%Y-%m-%d %H:%M')}", "",
             "| variant | settings | render s | fps | speed vs base | MB | SSIM | PSNR dB | parallel encoding |", "|---|---|---|---|---|---|---|---|---|"]
    for name in names:
        x = res.get(name, {})
        c = x.get("cfg", {})
        sp = f"{b['render_s'] / x['render_s']:.2f}x" if b.get("render_s") and x.get("render_s") else ""
        lines.append(f"| {name} | {c.get('preset')} crf {c.get('crf')} conc {c.get('concurrency')} {c.get('imageFormat')} | {x.get('render_s')} | "
                     f"{x.get('fps')} | {sp} | {x.get('mb')} | {x.get('ssim', '')} | {x.get('psnr', '')} | {(x.get('enc') or {}).get('parallel')} |")
    (out / "bench.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
