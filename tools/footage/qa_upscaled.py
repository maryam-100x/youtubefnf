"""YouTube's AI-upscaled copies, so no AI-upscaled picture (and its artifacts) reaches an edit. YouTube offers an AI-upscaled ladder above
an old upload's real resolution: those formats' ids end in "-sr" (248-sr, 399-sr) and their note says "AI-upscaled"; the native ladder
(136/247/398 ...) stops at the real upload height. A download taken as "best" from such a video is YouTube's AI upscale (an upload that
is native 720p is offered at 1080p only as -sr).

For every source file of the given prep files (their CLIPS, resolved by the prep's own src()), a YouTube id in its name (the stem's last
11 characters after "_" or ".", or yt-dlp's "[id]") is looked up once with yt-dlp -J (a spare account's cookies, node; cached in
PUBLIC/upscaled_cache.json); the file's height (ffprobe) above the top NATIVE height is an AI upscale. Prints each one with the clips cut
from it and the native download command; exit 1 if any. A sign-in or bot prompt stops the sweep (no retries).

  PIPE tools/footage/qa_upscaled.py <prep files, globs work> [--cookies PATH] [--refresh]
  The fix: download the native copy (-f "bv*[format_id!*=-sr]+ba/b"), re-point the clips (same timing; any pixel crop scaled by
  native/old height), re-cut with the prep's --check. A file rebuilt from the native upload by a classic resampler (lanczos to the old
  size) carries NATIVE_TAG in its comment tag (ffmpeg -metadata comment="...") and is not flagged."""
import argparse
import glob
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFPROBE, PUBLIC, SECRETS  # noqa: E402

CACHE = PUBLIC / "upscaled_cache.json"
COOKIES = str(SECRETS / "yt_cookies.txt")     # a spare account's cookie export; passed as a path only, never opened here
NATIVE_TAG = "rebuilt from YouTube's native upload"
TAIL = re.compile(r"(?:^|[_.])([A-Za-z0-9_-]{11})$")
BRACKET = re.compile(r"\[([A-Za-z0-9_-]{11})\]")
BOT = ("Sign in to confirm", "not a bot", "unusual traffic", "confirm you")


SECTION = re.compile(r"(?:^|[_.])([A-Za-z0-9_-]{11})_\d+(?:\.\d+)?-\d+(?:\.\d+)?$")   # <id>_<from>-<to>: a section download


def yt_id(stem):
    m = BRACKET.search(stem) or SECTION.search(stem) or TAIL.search(stem)
    if not m:
        return None
    c = m.group(1)
    if re.fullmatch(r"[a-z_]+", c) or re.fullmatch(r"[A-Z_]+", c) or re.fullmatch(r"[0-9_]+", c):
        return None                     # a word, not a random id
    return c


def height(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    try:
        return int(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return None


def native_tag(p):
    """a file rebuilt from the native upload says so in its comment tag"""
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format_tags=comment", "-of", "default=nw=1:nk=1", str(p)],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return NATIVE_TAG in r.stdout


def lookup(vid, cookies):
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--cookies", cookies, "--js-runtimes", "node", "-J", "--skip-download",
                        "--no-warnings", "--sleep-requests", "1", f"https://www.youtube.com/watch?v={vid}"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if any(b in r.stderr for b in BOT):
        raise SystemExit(f"YouTube asked for a sign-in or bot check at {vid}: stopped (a new cookie export is the creator's job; no retries)")
    if r.returncode:
        return {"error": (r.stderr.strip().splitlines() or ["?"])[-1][:200]}
    j = json.loads(r.stdout)
    vids = [f for f in j.get("formats", []) if f.get("vcodec") not in (None, "none") and f.get("height")]
    sr = [f for f in vids if str(f.get("format_id", "")).endswith("-sr") or "upscal" in str(f.get("format_note", "")).lower()]
    native = [f for f in vids if f not in sr]
    return {"title": j.get("title", "")[:90], "native_top": max((f["height"] for f in native), default=None),
            "sr_top": max((f["height"] for f in sr), default=None), "checked": time.strftime("%Y-%m-%d %H:%M")}


def sources(preps):
    out = {}                            # path -> [(prep, clip)]
    for p in preps:
        spec = importlib.util.spec_from_file_location(Path(p).stem, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        res = getattr(m, "src", None)
        bases = [getattr(m, k) for k in ("DL", "V", "SRC", "BASE") if isinstance(getattr(m, k, None), (str, Path))]
        for name, (s, *_rest) in m.CLIPS.items():
            cands = []
            if res:                     # a prep's src() takes a clip name or a source name
                for arg in (name, s):
                    try:
                        cands.append(Path(res(arg)))
                    except Exception:
                        pass
            cands += [Path(s)] + [Path(b) / s for b in bases]
            f = next((c for c in cands if c.is_file()), cands[0] if cands else Path(s))
            out.setdefault(str(f), []).append((Path(p).stem, name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preps", nargs="+")
    ap.add_argument("--cookies", default=COOKIES)
    ap.add_argument("--refresh", action="store_true", help="look every id up again (the cache otherwise keeps a lookup)")
    a = ap.parse_args()
    preps = sorted({q for p in a.preps for q in glob.glob(p)})
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    srcs = sources(preps)
    ids = {}
    for f in srcs:
        v = yt_id(Path(f).stem)
        if v:
            ids.setdefault(v, []).append(f)
    print(f"{len(srcs)} source files in {len(preps)} prep files; {len(ids)} YouTube ids")
    todo = [v for v in ids if a.refresh or v not in cache or "error" in cache[v]]
    for k, v in enumerate(todo):
        cache[v] = lookup(v, a.cookies)
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
        print(f"  looked up {k + 1}/{len(todo)} {v}: {cache[v].get('native_top', cache[v].get('error'))}", flush=True)
        time.sleep(3)
    bad, unknown = [], []
    for v, files in sorted(ids.items()):
        c = cache.get(v, {})
        if "error" in c or c.get("native_top") is None:
            unknown.append((v, c.get("error", "no native format")))
            continue
        for f in files:
            h = height(f)
            if h and h > c["native_top"] and not native_tag(f):   # tagged: the native upload scaled by a classic resampler
                bad.append((v, f, h, c))
    for v, f, h, c in bad:
        clips = srcs[f]
        print(f"\nAI-UPSCALED {v} ({c['title']}): {Path(f).name} is {h}p, the upload is {c['native_top']}p native "
              f"(YouTube's -sr ladder to {c['sr_top']}p)")
        print(f"  clips ({len(clips)}): " + ", ".join(f"{n} ({p})" for p, n in clips))
        print(f"  native: python -m yt_dlp --cookies <spare cookies> --js-runtimes node -f \"bv*[format_id!*=-sr]+ba/b\" "
              f"-o \"{Path(f).with_name(Path(f).stem + '_native')}.%(ext)s\" https://www.youtube.com/watch?v={v}")
    for v, e in unknown:
        print(f"UNKNOWN {v}: {e} ({', '.join(Path(f).name for f in ids[v])})")
    print(f"\n{len(bad)} AI-upscaled source file(s), {len(unknown)} id(s) not resolved, of {len(ids)}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
