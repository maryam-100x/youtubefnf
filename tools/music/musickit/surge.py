"""Surge XT as an offline instrument, driven from Python.

Surge XT (GPL-3, the Surge Synth Team) is hosted by Spotify's pedalboard. A Surge patch (.fxp) is loaded by writing its Surge chunk
(from the 'sub3' marker on) as the plugin's component state, wrapped the way JUCE hosts store VST3 state: "VC2!" + a 4-byte length +
an XML document whose <IComponent> holds the chunk in JUCE's own base64 (not RFC 4648). Surge applies a new state on its next audio
block, so one short silent render settles it. Then MIDI notes go in as mido messages with times in seconds; out comes (2, n) float32.

    from musickit.surge import Surge
    s = Surge("Pads/Verb Pad")       # a path under patches_factory or patches_3rdparty, without .fxp (or a full .fxp path)
    audio = s.render([(t, dur, midi_note, velocity), ...], seconds)

    SYNTH tools/music/music.py patches [substring]      lists the patches whose library path contains the substring

Paths: musickit/settings.py (surge_xt_dir in config/paths.toml). First start ~35 s and the first patch ~30 s more (Surge indexes its
library), then ~3 s a patch (measured on a laptop CPU).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from mido import Message
from pedalboard import load_plugin

from .settings import SR, surge_paths

_T = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"


def jenc(b: bytes) -> str:
    """JUCE's MemoryBlock::toBase64Encoding: '<size>.' then 6 bits at a time, lowest bit first."""
    n = len(b)
    nbits = n * 8
    out = []
    bit = 0
    while bit < nbits:
        v = 0
        for k in range(6):
            if bit >= nbits:
                break
            if b[bit >> 3] >> (bit & 7) & 1:
                v |= 1 << k
            bit += 1
        out.append(_T[v])
    return f"{n}." + "".join(out)


def jdec(s: str) -> bytes:
    """The inverse of jenc (handy to read a state pedalboard hands back)."""
    n, _, d = s.partition(".")
    n = int(n)
    out = bytearray(n)
    bit = 0
    for ch in d:
        v = _T.index(ch)
        for k in range(6):
            if bit >= n * 8:
                break
            if v >> k & 1:
                out[bit >> 3] |= 1 << (bit & 7)
            bit += 1
    return bytes(out)


@lru_cache(maxsize=1)
def _library() -> dict[str, Path]:
    """Every .fxp in the factory and third-party folders, keyed by its library path without .fxp, lower case."""
    _, data = surge_paths()
    lib = {}
    for base in (data / "patches_factory", data / "patches_3rdparty"):
        for f in sorted(base.rglob("*.fxp")):
            lib.setdefault(f.relative_to(base).as_posix()[:-4].lower(), f)
    return lib


def find_patch(name: str) -> Path:
    """'Pads/Sweet Pad' -> its .fxp (case-insensitive; a trailing part of the path is enough), or a full .fxp path as is."""
    p = Path(name)
    if p.suffix.lower() == ".fxp" and p.exists():
        return p
    want = name.replace("\\", "/").lower().rstrip("/")
    lib = _library()
    if want in lib:
        return lib[want]
    for rel, f in lib.items():
        if rel.endswith("/" + want):
            return f
    raise FileNotFoundError(f"no Surge patch {name!r}")


def list_patches(sub: str = "") -> list[str]:
    _, data = surge_paths()
    out = []
    for base in (data / "patches_factory", data / "patches_3rdparty"):
        for f in base.rglob("*.fxp"):
            rel = f.relative_to(base).as_posix()[:-4]
            if sub.lower() in rel.lower():
                out.append(rel)
    return sorted(out)


def chunk_of(fxp: Path) -> bytes:
    b = fxp.read_bytes()
    if b[:4] != b"CcnK" or b[16:20] != b"cjs3":
        raise ValueError(f"{fxp} is not a Surge .fxp")
    i = b.find(b"sub3")
    if i < 0:
        raise ValueError(f"{fxp}: no Surge chunk")
    return b[i:]


class Surge:
    """One Surge XT instance; one patch at a time."""

    def __init__(self, patch: str | None = None, sr: int = SR):
        vst3, data = surge_paths()
        os.environ.setdefault("SURGE_DATA_HOME", str(data))
        self.p = load_plugin(str(vst3))
        self.sr = sr
        self.patch = None
        if patch:
            self.load(patch)

    def load(self, patch: str) -> None:
        fxp = find_patch(patch)
        xml = ('<?xml version="1.0" encoding="UTF-8"?> <VST3PluginState><IComponent>'
               + jenc(chunk_of(fxp)) + "</IComponent></VST3PluginState>")
        body = xml.encode("utf-8") + b"\0"
        self.p.raw_state = b"VC2!" + len(body).to_bytes(4, "little") + body
        self.patch = patch
        # Surge loads a queued patch on its next block: one short silent render settles it
        self.p([], duration=0.25, sample_rate=self.sr, num_channels=2)

    def set(self, **params) -> None:
        """Change exposed plugin parameters by name (pedalboard's parameter names). The method's beds change none: every sound
        shaping step happens after Surge (filters, reverb, level in compose.render_track)."""
        for k, v in params.items():
            setattr(self.p, k, v)

    def render(self, notes, seconds: float, sr: int | None = None, cc=None) -> np.ndarray:
        """notes: (start s, length s, midi note, velocity 1-127); cc: (time s, controller, value). Returns (2, n) float32."""
        sr = sr or self.sr
        msgs = []
        last = float(seconds) - 0.005    # every note_off inside the buffer: a note left on would ring into the next patch's render
        for t0, ln, note, vel in notes:
            if not 0 <= int(note) <= 127 or t0 >= last:
                continue
            msgs.append(Message("note_on", note=int(note), velocity=int(vel), time=float(t0)))
            msgs.append(Message("note_off", note=int(note), velocity=0, time=min(float(t0 + ln), last)))
        for t, ctl, val in cc or []:
            msgs.append(Message("control_change", control=int(ctl), value=int(val), time=float(t)))
        msgs.sort(key=lambda m: m.time)
        a = self.p(msgs, duration=float(seconds), sample_rate=sr, num_channels=2, reset=False)
        return np.asarray(a, dtype=np.float32)


if __name__ == "__main__":
    import sys
    print("\n".join(list_patches(sys.argv[1] if len(sys.argv) > 1 else "")))
