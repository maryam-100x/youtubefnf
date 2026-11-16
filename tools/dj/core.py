"""Shared helpers: config, per-video context, ffmpeg, WAV I/O, fonts, text drawing.

The config is config/tts.toml (the setup writes it from config/tts.example.toml, which shows every key). Without it the example is
read, so every command but the voice itself works on a fresh clone; the voice refuses to run until its voice is set (require_voice).
Paths come from tools/common/paths.py; the [paths] table only overrides them."""
import json
import math
import re
import shutil
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    import tomllib
except ImportError:  # Python 3.10
    import tomli as tomllib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FOOTAGE, KB, MEDIA, REPO, TOOLS, VIDEOS  # noqa: E402

SR = 48000  # project audio sample rate (mono 16-bit PCM for narration)
CONFIG = REPO / "config" / "tts.toml"
EXAMPLE = REPO / "config" / "tts.example.toml"
_NOTED = []


# ---------- config ----------
def config_file(path=None):
    """The config to read: an explicit path, else config/tts.toml, else the example (noted once on stderr)."""
    if path:
        return Path(path)
    if CONFIG.exists():
        return CONFIG
    if not _NOTED:
        _NOTED.append(1)
        print(f"  note: {CONFIG} not found, reading {EXAMPLE.name} (the setup writes tts.toml; the voice stays off until it does)",
              file=sys.stderr)
    return EXAMPLE


def path_defaults(cfg):
    """[paths] keys a config leaves out come from tools/common/paths.py (the media root and its folders)."""
    p = cfg.setdefault("paths", {})
    p.setdefault("assets", str(FOOTAGE))          # VIS paths resolve against this
    p.setdefault("out_root", str(VIDEOS))         # build output = <out_root>/<video>/build
    p.setdefault("fonts", str(MEDIA / "fonts"))   # Google Fonts are downloaded here once
    p.setdefault("kb", str(KB))
    p.setdefault("metrics", "metrics.csv")        # date, video, command, seconds (relative = under tools/)
    p.setdefault("ffmpeg", "" if FFMPEG == "ffmpeg" else FFMPEG)
    return cfg


def load_config(path=None, overrides=()):
    cfg = tomllib.loads(config_file(path).read_text(encoding="utf-8"))
    for ov in overrides:  # "section.key=value" (value parsed as TOML, else kept as string)
        key, _, val = ov.partition("=")
        try:
            val = tomllib.loads(f"v = {val}")["v"]
        except tomllib.TOMLDecodeError:
            pass
        d = cfg
        *parents, last = key.strip().split(".")
        for p in parents:
            d = d.setdefault(p, {})
        d[last] = val
    return path_defaults(cfg)


def unset(v):
    """A config value still at its template placeholder: empty, or written as <...>."""
    return not str(v or "").strip() or str(v).strip().startswith("<")


def require_voice(cfg):
    """Stops with a clear message when the voice engine has no voice yet (a fresh clone reads the example config)."""
    t = cfg.get("tts", {})
    eng = t.get("engine")
    if eng == "elevenlabs" and unset(t.get("elevenlabs", {}).get("voice_id")):
        raise SystemExit(f"the voice is not set: put your ElevenLabs voice id in {CONFIG} under [tts.elevenlabs] voice_id "
                         f"(copy {EXAMPLE.name} to tts.toml first; the setup does both), or run with --set tts.engine=dummy for a test")
    if eng == "command" and (not t.get("command", {}).get("template") or unset(t.get("command", {}).get("voice"))):
        raise SystemExit(f"the local voice engine is not set: [tts.command] template and voice in {CONFIG}")


def expand(p):
    p = Path(str(p)).expanduser()
    return p if p.is_absolute() else TOOLS / p


def apply_short_profile(cfg, script):
    """[tts.short] over [tts] for a Short (deep for tts.elevenlabs), then the script's own CONFIG: tts.* lines again, so they still
    win (a Short pinned to the long-form voice: CONFIG: tts.short_profile=false). Once per config dict."""
    t = cfg.get("tts", {})
    prof = t.get("short")
    if not prof or t.get("_short_applied") or t.get("short_profile") is False:
        return
    for k, v in prof.items():
        if isinstance(v, dict) and isinstance(t.get(k), dict):
            t[k] = {**t[k], **v}
        else:
            t[k] = v
    t["_short_applied"] = True
    lines = [ln.strip()[7:].strip() for ln in Path(script).read_text(encoding="utf-8").splitlines() if ln.strip().startswith("CONFIG:")] if Path(script).exists() else []
    again = load_config(None, [ln for ln in lines if ln.startswith("tts.")])  # the script's tts lines over a fresh base: copy just those keys
    for ln in lines:
        if not ln.startswith("tts."):
            continue
        *parents, last = ln.partition("=")[0].strip().split(".")
        src, dst = again, cfg
        for q in parents:
            src, dst = src[q], dst.setdefault(q, {})
        dst[last] = src[last]
    if t.get("short_profile") is False:  # pinned after all: undo by reloading the base tts table with the script's lines
        cfg["tts"] = again["tts"]


class Ctx:
    """Everything a command needs about one video: config, format, sizes, frame rate, folders."""

    def __init__(self, video_dir, cfg, fmt=None):
        self.video = Path(video_dir).resolve()
        if not (self.video / "script.md").exists():
            raise SystemExit(f"no script.md in {self.video}")
        self.slug, self.cfg = self.video.name, cfg
        v = cfg["video"]
        self.fmt = fmt or v.get("format") or ("short" if "short" in self.slug else "long")
        if self.fmt == "short":
            apply_short_profile(cfg, self.video / "script.md")
        res = v["short_resolution"] if self.fmt == "short" else v["long_resolution"]
        self.W, self.H = map(int, res.lower().split("x"))
        fps = float(v["fps"])
        # frame duration as a rational num/den seconds (30 -> 1/30, 29.97 -> 1001/30000)
        self.fd = (1, int(round(fps))) if abs(fps - round(fps)) < 1e-6 else (1001, int(round(fps * 1.001)) * 1000)
        self.rate = f"{self.fd[1]}/{self.fd[0]}"  # ffmpeg frame rate string
        out_root = cfg["paths"].get("out_root", "")
        if out_root and Path(out_root).expanduser().parent.exists():
            self.build = Path(out_root).expanduser() / self.slug / "build"
        else:  # no media root yet: the build goes next to the script
            self.build = self.video / "build"
        self.build.mkdir(parents=True, exist_ok=True)
        self.warned = set()

    def sec(self, frames):
        return frames * self.fd[0] / self.fd[1]

    def frames(self, sec):
        return math.ceil(sec * self.fd[1] / self.fd[0] - 1e-6)

    def path(self, *parts):
        p = self.build.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def warn(self, msg):
        if msg in self.warned:
            return
        self.warned.add(msg)
        print(f"  WARNING: {msg}")
        with open(self.path("warnings.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def resolve_asset(self, rel):
        """Asset paths in VIS are relative to paths.assets (or the video folder), or absolute."""
        if not rel:
            return None
        p = Path(rel).expanduser()
        cands = [p] if p.is_absolute() else [Path(self.cfg["paths"]["assets"]).expanduser() / rel, self.video / rel]
        return next((c for c in cands if c.exists()), None)

    def save_json(self, name, data):
        self.path(name).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")

    def load_json(self, name, hint):
        p = self.build / name
        if not p.exists():
            raise SystemExit(f"{p} missing: run `cd tools && PIPE -m dj {hint} ../videos/{self.slug}` first")
        return json.loads(p.read_text(encoding="utf-8"))


# ---------- ffmpeg ----------
_FF = None


def ffmpeg_bin(cfg=None):
    """ffmpeg from config, then PATH, then the imageio-ffmpeg bundled binary."""
    global _FF
    if cfg and cfg.get("paths", {}).get("ffmpeg"):
        _FF = cfg["paths"]["ffmpeg"]
    if not _FF:
        _FF = shutil.which(FFMPEG) or shutil.which("ffmpeg")
    if not _FF:
        try:
            import imageio_ffmpeg
            _FF = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            raise SystemExit("ffmpeg not found: install it (the setup does) or set ffmpeg in config/paths.toml") from None
    return _FF


FF_TIMEOUT = 1800  # s; the longest real call (a 25-min long-video render) takes a few minutes


def ff(args, log="error", cwd=None):
    """Run ffmpeg; returns stderr (use log='info' to read filter output such as loudnorm). cwd lets filters use relative paths
    (e.g. ass=captions/x.ass), which avoids escaping Windows drive letters inside filter strings."""
    cmd = [ffmpeg_bin(), "-hide_banner", "-nostdin", "-y", "-loglevel", log] + [str(a) for a in args]
    try:  # a stuck graph (e.g. an input seeked past its end under a looping image) must fail loudly, not hang for hours
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=FF_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffmpeg ran over {FF_TIMEOUT} s (stuck?): {' '.join(cmd)}") from None
    if r.returncode:
        raise RuntimeError(f"ffmpeg failed ({r.returncode}): {' '.join(cmd)}\n{r.stderr[-3000:]}")
    return r.stderr


def file_sig(path):
    """Content fingerprint (sha1) of a file: 'is this still the same narration?' without trusting file dates."""
    import hashlib
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def media_duration(path):
    """Duration in seconds, parsed from `ffmpeg -i` (no ffprobe needed)."""
    r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else None


def loudness(path, target=-14.0, tp=-1.5, lra=11.0):
    """Pass 1 of loudnorm: returns the measured JSON dict (input_i, input_tp, ...)."""
    err = ff(["-i", path, "-af", f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json", "-f", "null", "-"], log="info")
    return json.loads(err[err.rindex("{"):err.rindex("}") + 1])


def to_wav(src, dst):
    ff(["-i", src, "-ac", 1, "-ar", SR, "-c:a", "pcm_s16le", dst])


def read_wav(path):
    with wave.open(str(path)) as w:
        assert w.getnchannels() == 1 and w.getframerate() == SR and w.getsampwidth() == 2, f"{path}: expected 48k mono 16-bit"
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def write_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.asarray(samples, dtype=np.int16).tobytes())


# ---------- fonts and text ----------
_FONTS = {}
FALLBACK_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]


def font(cfg, role, size):
    """role = 'heavy' | 'caption' | 'body'. Google Fonts are downloaded once into paths.fonts."""
    fam = cfg["brand"]["fonts"][role]
    if fam not in _FONTS:
        d = expand(cfg["paths"]["fonts"])
        f = d / (re.sub(r"\W+", "_", fam) + ".ttf")
        if not f.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
                req = urllib.request.Request(f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}",
                                             headers={"User-Agent": "curl/8"})
                css = urllib.request.urlopen(req, timeout=20).read().decode()
                url = re.search(r"url\((https://[^)]+\.ttf)\)", css)[1]
                f.write_bytes(urllib.request.urlopen(url, timeout=30).read())
            except Exception as e:  # offline: fall back to a system font
                print(f"  WARNING: font {fam} not downloaded ({e}); using a fallback font")
                f = next((p for p in FALLBACK_FONTS if Path(p).exists()), None)
        _FONTS[fam] = f
    f = _FONTS[fam]
    return ImageFont.truetype(str(f), size) if f else ImageFont.load_default(size)


def rgb(hexstr, a=255):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def fit_font(cfg, role, lines, max_w, max_h, start):
    size = int(start)
    while True:
        f = font(cfg, role, size)
        w = max(f.getlength(ln) for ln in lines)
        if (w <= max_w and len(lines) * size * 1.12 <= max_h) or size <= 14:
            return f
        size = int(size * 0.93)


def draw_lines(img, lines, f, cx, cy, fills, stroke_fill=(0, 0, 0, 255), stroke_ratio=0.09, shadow=True, align="mm"):
    """Draw centered (or left/right anchored) lines with a thick outline and a soft drop shadow."""
    lh = f.size * 1.12
    stroke = max(2, int(f.size * stroke_ratio))
    y0 = cy - lh * (len(lines) - 1) / 2
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(sh)
        for i, ln in enumerate(lines):
            d.text((cx + stroke, y0 + i * lh + stroke), ln, font=f, fill=(0, 0, 0, 170), anchor=align,
                   stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        r = max(2, stroke)
        box = sh.getbbox()
        if box:  # blur only around the text (full-frame blurs are slow)
            box = (max(box[0] - 3 * r, 0), max(box[1] - 3 * r, 0), min(box[2] + 3 * r, img.width), min(box[3] + 3 * r, img.height))
            img.alpha_composite(sh.crop(box).filter(ImageFilter.GaussianBlur(r)), box[:2])
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        d.text((cx, y0 + i * lh), ln, font=f, fill=fills[min(i, len(fills) - 1)], anchor=align,
               stroke_width=stroke, stroke_fill=stroke_fill)
    return img
