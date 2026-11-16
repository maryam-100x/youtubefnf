"""Music written note by note, played by Surge XT, timed to the film's own clock.

Why: a finished track can only be cut to land at a turn; music written for the film puts its bars on the words, thins out under dense
lines, builds into a turn and drops far back under a voice. The sound comes from Surge XT's designed patches (surge.py); every bed is
measured against a bar (bands.py, judge.py), and the creator's ears give the verdict.

    Clock([(t0, t1, n_bars, beats_per_bar), ...])  bars laid between film times: each segment holds a whole number of bars, so its
                                                   first downbeat lands on its anchor (a word's onset)
    chord / bass_pc / voicing / close_voicings / lead   chord symbols, their tones, voice leading
    Track(name, patch, notes, ...)                 one instrument: notes (t, dur, midi, vel) on the film's clock, its own filters,
                                                   reverb, level and level points
    Rand(seed)                                     the seeded human variation: velocity spread and a few ms of timing nudge
    render_track / bus / render_bed                Surge -> per-track shaping -> mix -> bus (compressor, peak, limiter) -> one WAV
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .settings import SR, ensure_parent

# pedalboard, soundfile and Surge are imported where a render needs them, so the writing logic (and selftest) runs without them

# each part's RMS (dBFS over its sounding span) before the bus: the balance the patch picks were judged in (pick.py)
LEVELS = {"sub": -20.0, "drive": -22.0, "pad": -24.0, "pulse": -26.0, "drone": -30.0, "hit": -18.0, "keys": -26.0}
NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8,
        "A": 9, "A#": 10, "Bb": 10, "B": 11}
QUAL = {"": (0, 4, 7), "m": (0, 3, 7), "5": (0, 7), "sus2": (0, 2, 7), "sus4": (0, 5, 7), "m7": (0, 3, 7, 10),
        "maj7": (0, 4, 7, 11), "7": (0, 4, 7, 10), "madd9": (0, 3, 7, 14), "add9": (0, 4, 7, 14), "m9": (0, 3, 7, 10, 14),
        "dim": (0, 3, 6), "maj9": (0, 4, 7, 11, 14)}


def chord(sym: str) -> tuple[int, tuple[int, ...]]:
    """'Gm' -> (7, (0, 3, 7)); 'Eb/G' keeps its slash bass for bass_pc()."""
    s = sym.split("/")[0]
    root = s[:2] if len(s) > 1 and s[1] in "b#" else s[:1]
    return NOTE[root], QUAL[s[len(root):]]


def bass_pc(sym: str) -> int:
    if "/" in sym:
        return NOTE[sym.split("/")[1]]
    return chord(sym)[0]


def voicing(sym: str, low: int, high: int) -> list[int]:
    """The chord's tones in close position inside [low, high] (midi), lowest first, each pitch class once from the root up."""
    r, q = chord(sym)
    base = low + ((r - low) % 12)
    notes = [base + i for i in q]
    while notes[-1] > high and notes[0] - 12 >= low - 12:
        notes = [n - 12 for n in notes]
    return [n for n in notes if low - 12 <= n <= high]


def close_voicings(sym: str, low: int, high: int) -> list[list[int]]:
    """Every close-position voicing of the chord (each pitch class once, any inversion) inside [low, high]."""
    r, q = chord(sym)
    uniq = []
    for i in q:
        pc = (r + i) % 12
        if pc not in uniq:
            uniq.append(pc)
    res = []
    for p in range(low, high + 1):
        if p % 12 not in uniq:
            continue
        k = uniq.index(p % 12)
        v = [p]
        for j in range(1, len(uniq)):
            pc = uniq[(k + j) % len(uniq)]
            v.append(v[-1] + ((pc - v[-1]) % 12 or 12))
        if v[-1] <= high:
            res.append(v)
    return res


def lead(prev: list[int] | None, sym: str, low: int, high: int) -> list[int]:
    """Voice leading: the voicing of `sym` whose notes move least from `prev` (the first chord sits mid-range)."""
    cands = close_voicings(sym, low, high)
    if not cands:
        return voicing(sym, low, high)
    if not prev:
        mid = (low + high) / 2
        return min(cands, key=lambda v: abs(sum(v) / len(v) - mid))

    def cost(v):
        return sum(min(abs(a - b) for b in prev) for a in v) + sum(min(abs(a - b) for a in v) for b in prev)
    return min(cands, key=cost)


class Clock:
    """Bars between film times. segs: (t0, t1, n_bars, beats_per_bar). Each segment's bars share its span evenly, so every segment
    starts on a downbeat; the tempo of a segment is 60 * beats_per_bar * n_bars / (t1 - t0)."""

    def __init__(self, segs):
        self.segs = list(segs)
        self.bars = []
        for t0, t1, n, bpb in segs:
            L = (t1 - t0) / n
            self.bars += [(t0 + k * L, L, bpb) for k in range(n)]

    def __len__(self):
        return len(self.bars)

    def t(self, bar: float, beat: float = 0.0) -> float:
        """Film time of a bar (fractional bars allowed) plus beats; past the last bar it keeps the last bar's length."""
        i = int(bar)
        s, L, bpb = self.bars[min(i, len(self.bars) - 1)]
        if i >= len(self.bars):
            return s + L * (bar - len(self.bars) + 1) + beat * L / bpb
        return s + (bar - i) * L + beat * L / bpb

    def beat_len(self, bar: int) -> float:
        s, L, bpb = self.bars[bar]
        return L / bpb

    def bpm(self, bar: int) -> float:
        s, L, bpb = self.bars[bar]
        return 60.0 * bpb / L

    def end(self) -> float:
        s, L, _ = self.bars[-1]
        return s + L


@dataclass
class Track:
    name: str
    patch: str
    notes: list = field(default_factory=list)   # (t, dur, midi, vel), film seconds
    gain_db: float = 0.0
    hp: float = 0.0              # high-pass cutoff, Hz (0 = off)
    lp: float = 0.0              # low-pass cutoff, Hz (0 = off)
    reverb: float = 0.0          # wet level 0-1 (pedalboard Reverb, room `room`, damping 0.6, dry 1.0, width 1.0)
    room: float = 0.85
    auto: list = field(default_factory=list)    # (t, gain_db) points in film seconds, linear between: the level automation
    cc: list = field(default_factory=list)      # (t, controller, value) MIDI CCs (unused by the example beds)
    level: float | None = None   # the track's RMS (dBFS, over its sounding span) before gain_db: patches differ by 20 dB+
    transpose: int = 0           # semitones added to every note: some patches sound an octave or two off the written note


class Rand:
    """The seeded human variation: the same seed gives the same notes on every run (Surge's own LFOs may still differ)."""

    def __init__(self, seed: int):
        self.r = random.Random(seed)

    def vel(self, v: int, spread: int = 6) -> int:
        return max(1, min(127, v + self.r.randint(-spread, spread)))

    def nudge(self, t: float, ms: float = 4.0) -> float:
        return t + self.r.uniform(-ms, ms) / 1000.0


def _auto_gain(n: int, t0: float, pts) -> np.ndarray:
    if not pts:
        return np.ones(n, dtype=np.float32)
    ts = np.array([p[0] for p in pts]) - t0
    gs = np.array([p[1] for p in pts], dtype=float)
    x = np.arange(n) / SR
    return (10 ** (np.interp(x, ts, gs) / 20)).astype(np.float32)


def write_grid(clk: Clock, t0: float, out_wav: str | Path, mix: np.ndarray) -> dict:
    """The bed's exact bar grid (track time = film time - t0) as <wav>.grid.json: every beat, every downbeat, each bar's level.
    A mixer that places the bed (under_voice.py) or cuts it on a beat reads this instead of guessing the tempo."""
    beats, downs, bar_db = [], [], []
    for s, L, bpb in clk.bars:
        downs.append(round(s - t0, 4))
        beats += [round(s - t0 + k * L / bpb, 4) for k in range(bpb)]
        a, b = int((s - t0) * SR), int((s - t0 + L) * SR)
        m = mix[:, a:b].mean(0)
        bar_db.append(round(float(20 * np.log10(np.sqrt((m ** 2).mean()) + 1e-9)), 1) if b > a else -90.0)
    bpm = [60.0 * bpb / L for _, L, bpb in clk.bars]
    g = {"file": Path(str(out_wav)).name, "tempo": round(float(np.mean(bpm)), 2), "dur": round(mix.shape[1] / SR, 3),
         "beats": beats, "downbeats": downs, "bar_db": bar_db, "composed": True}
    Path(str(out_wav) + ".grid.json").write_text(json.dumps(g), encoding="utf-8")
    return g


def _sounding(notes, n: int, release: float = 0.3) -> np.ndarray:
    """A mask of the samples where the track sounds: every note from its start to its end + `release` (the union of the notes)."""
    m = np.zeros(n, bool)
    for t, d, _, _ in notes:
        m[max(0, int(t * SR)):min(n, int((t + d + release) * SR))] = True
    return m


def render_track(s, tr: Track, t0: float, t1: float, secs: float) -> np.ndarray:
    """One track from film time t0 for `secs`: Surge (its patch loaded fresh for every track), then the per-layer shaping in this
    order: high-pass, low-pass, reverb, level (RMS over the samples where its notes sound, set to tr.level), gain_db, level
    automation. A note that started before t0 keeps only its part after t0."""
    from pedalboard import HighpassFilter, LowpassFilter, Pedalboard, Reverb
    n = int(round(secs * SR))
    s.load(tr.patch)
    notes = [(max(0.0, t - t0), d - max(0.0, t0 - t), m + tr.transpose, v) for (t, d, m, v) in tr.notes if t0 - d < t < t0 + secs]
    cc = [(max(0.0, t - t0), c, v) for (t, c, v) in tr.cc]
    a = s.render(notes, secs, cc=cc)[:, :n]
    if a.shape[1] < n:
        a = np.pad(a, ((0, 0), (0, n - a.shape[1])))
    fx = []
    if tr.hp:
        fx.append(HighpassFilter(cutoff_frequency_hz=tr.hp))
    if tr.lp:
        fx.append(LowpassFilter(cutoff_frequency_hz=tr.lp))
    if tr.reverb:
        fx.append(Reverb(room_size=tr.room, damping=0.6, wet_level=tr.reverb, dry_level=1.0, width=1.0))
    if fx:
        a = Pedalboard(fx)(a, SR)
    if tr.level is not None and notes:
        # measured where the notes sound, never over the silence between them: two hits 20 s apart are each as loud as one hit
        on = _sounding(notes, n)
        seg = a[:, on] if on.any() else a
        rms = float(np.sqrt((seg ** 2).mean())) or 1e-9
        a = a * (10 ** (tr.level / 20) / rms)
    return (a * (10 ** (tr.gain_db / 20)) * _auto_gain(n, t0, tr.auto)).astype(np.float32)


def bus(mix: np.ndarray, comp: bool = True) -> np.ndarray:
    """The bed's bus: a gentle compressor (threshold -20 dB, 2:1, attack 30 ms, release 250 ms), the peak set to -3 dBFS (the mix
    under the voice sets the bed's real level later), a limiter at -1 dBFS (release 100 ms)."""
    from pedalboard import Compressor, Limiter, Pedalboard
    if comp:
        mix = Pedalboard([Compressor(threshold_db=-20, ratio=2.0, attack_ms=30, release_ms=250)])(mix, SR)
    peak = float(np.abs(mix).max()) or 1.0
    mix = mix * (10 ** (-3 / 20) / peak)
    return Pedalboard([Limiter(threshold_db=-1.0, release_ms=100)])(mix, SR)


def wrap_loop(mix: np.ndarray, n_main: int) -> np.ndarray:
    """A bed that loops (a Short plays on through its loop): the tail past the bed's end is laid over its start, so the reverb and the
    last chord ring into the first bar instead of being cut off at the loop point."""
    out = mix[:, :n_main].copy()
    tail = mix[:, n_main:]
    k = min(tail.shape[1], n_main)
    out[:, :k] += tail[:, :k]
    return out


def render_bed(tracks: list[Track], t0: float, t1: float, out_wav: str | Path, tail: float = 4.0, stems: Path | None = None,
               bus_comp: bool = True, clock: Clock | None = None, surge=None, loop: bool = False, info: dict | None = None
               ) -> np.ndarray:
    """Render every track from film time t0 to t1 (+ tail) through one Surge XT, mix, bus, write out_wav (48 kHz, 24-bit), its
    metadata (<wav>.json: its film span, its events, every track's patch and shaping) and, with a clock, its exact grid
    (<wav>.grid.json, the format tools/sound/grid.py writes and score.py reads). `stems` writes each track's WAV for mixdown.py.
    `loop`: the bed is exactly t1 - t0 long and its tail is laid over its start (a Short's bed). `info` goes into the metadata."""
    import soundfile as sf
    from .surge import Surge
    secs = (t1 - t0) + tail
    n = int(round(secs * SR))
    mix = np.zeros((2, n), dtype=np.float32)
    s = surge or Surge(sr=SR)
    for tr in tracks:
        a = render_track(s, tr, t0, t1, secs)
        if stems:
            stems = Path(stems)
            stems.mkdir(parents=True, exist_ok=True)
            sf.write(stems / f"{tr.name}.wav", a.T, SR, subtype="PCM_24")
        mix += a
    if loop:
        mix = wrap_loop(mix, int(round((t1 - t0) * SR)))
    mix = bus(mix, bus_comp)
    sf.write(str(ensure_parent(out_wav)), mix.T, SR, subtype="PCM_24")
    if clock is not None:
        write_grid(clock, t0, out_wav, mix)
    meta = {"t0": t0, "t1": t1, "sr": SR, "loop": loop, **(info or {}), "tracks": [t.name + ": " + t.patch for t in tracks],
            "shaping": [{"name": t.name, "patch": t.patch, "transpose": t.transpose, "hp": t.hp, "lp": t.lp, "reverb": t.reverb,
                         "room": t.room, "level": t.level, "gain_db": t.gain_db, "auto": t.auto, "notes": len(t.notes)}
                        for t in tracks]}
    Path(str(out_wav) + ".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return mix
