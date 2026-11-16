"""Where things live. Every path comes from tools/common/paths.py (config/paths.toml), with environment variables as overrides.

    surge_xt_dir    (paths.toml) the folder the portable Surge XT build was unpacked into (it holds "Surge Synth Team/"), or the
                    "Surge Synth Team" folder itself. Default MEDIA/apps/surge-xt. The setup puts it there (tools/setup/surge.py).
    surge_xt_vst3   (paths.toml) the Surge XT VST3 plugin: the "Surge XT.vst3" bundle, or the module file inside it
    surge_xt_data   (paths.toml) Surge XT's data folder: the one that holds patches_factory/ and patches_3rdparty/
                    (both only when Surge XT is installed somewhere else, e.g. by its macOS installer)
    SURGE_XT_DIR / SURGE_XT_VST3 / SURGE_XT_DATA   the same as environment variables (they win over paths.toml)

Tested layout: the official portable Windows build of Surge XT 1.3.4, and on a Mac the same layout copied out of the official .dmg
(tools/setup/surge.py; Surge finds its library there through SURGE_DATA_HOME, set by musickit.surge). The installer locations below
are the ones Surge XT documents, for a Surge installed by hand.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
import paths as _paths  # noqa: E402

SR = 48000          # every render, stem and bed: 48 kHz, written as 24-bit WAV
MEDIA = _paths.MEDIA
MODELS = _paths.MODELS
VIDEOS = _paths.VIDEOS
MUSIC = _paths.MUSIC
REPO = _paths.REPO


def _cfg(key: str) -> str | None:
    return os.environ.get(key.upper()) or (str(_paths._cfg[key]) if _paths._cfg.get(key) else None)


def _portable(root: Path) -> tuple[Path, Path] | None:
    for base in (root / "Surge Synth Team", root):
        v, d = base / "Surge XT.vst3", base / "SurgeXTData"
        if v.exists() and d.exists():
            return v, d
    return None


def _installer_defaults() -> list[tuple[Path, Path]]:
    if sys.platform.startswith("win"):
        cf = Path(os.environ.get("CommonProgramFiles", r"C:\Program Files\Common Files"))
        pd = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        return [(cf / "VST3" / "Surge Synth Team" / "Surge XT.vst3", pd / "Surge XT"),
                (cf / "VST3" / "Surge XT.vst3", pd / "Surge XT")]
    if sys.platform == "darwin":
        return [(Path("/Library/Audio/Plug-Ins/VST3/Surge XT.vst3"), Path("/Library/Application Support/Surge XT")),
                (Path.home() / "Library/Audio/Plug-Ins/VST3/Surge XT.vst3", Path("/Library/Application Support/Surge XT"))]
    return [(Path("/usr/lib/vst3/Surge XT.vst3"), Path("/usr/share/surge-xt")),
            (Path("/usr/local/lib/vst3/Surge XT.vst3"), Path("/usr/local/share/surge-xt"))]


def plugin_module(vst3: Path) -> Path:
    """pedalboard can't scan the outer .vst3 bundle on Windows: it loads the module inside it (Contents/x86_64-win/Surge XT.vst3).
    Elsewhere the bundle is passed as is."""
    inner = vst3 / "Contents" / "x86_64-win" / vst3.name
    if vst3.is_dir() and inner.is_file():
        return inner
    return vst3


def surge_paths() -> tuple[Path, Path]:
    """(the plugin to load, the data folder). Raises with what to set when nothing is found."""
    v, d = _cfg("surge_xt_vst3"), _cfg("surge_xt_data")
    if v and d:
        return plugin_module(Path(v)), Path(d)
    cands = []
    p = _portable(Path(_cfg("surge_xt_dir") or _paths.APPS / "surge-xt"))
    if p:
        cands.append(p)
    cands += _installer_defaults()
    for vv, dd in cands:
        vv = Path(v) if v else vv
        dd = Path(d) if d else dd
        if vv.exists() and (dd / "patches_factory").exists():
            return plugin_module(vv), dd
    raise FileNotFoundError(
        "Surge XT not found. Unpack the portable build into MEDIA/apps/surge-xt, or set surge_xt_dir (or surge_xt_vst3 and "
        "surge_xt_data) in config/paths.toml (standard/MUSIC.md, the install).")


def ensure_parent(path) -> Path:
    """Create the folder a file will be written into."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def out_dir(arg=None) -> Path:
    """Where beds go: a video's to MEDIA/videos/<video>/build/music (music.py render), a test render's (the example) to MEDIA/tmp/music,
    never into MUSIC (the creator's own tracks)."""
    p = Path(arg or _paths.TMP / "music")
    p.mkdir(parents=True, exist_ok=True)
    return p
