"""The helpers a film's music file is written with (see example/film.py).

    Words(path)                   the narration's word times: W.first(section), W.last_end(section), W.word(section, "phrase"),
                                  W.word_end(section, "phrase") (the same words.json the cue sheet's Film reads)
    clock(points, bpm)            a Clock whose segments run between consecutive anchor times, each a whole number of bars at about
                                  `bpm`, so every anchor is a downbeat; also returns the first bar of each segment
    seg_bpms / fit_bpm            the tempo each segment really plays at; the written tempo (in a range) that moves them least
    prog(chords, n)               a progression repeated over n bars (one symbol per bar: write a chord twice to hold it two bars)
    arp16(...)                    the pulse: a pattern of chord-tone indices over 16 (or 8) steps a bar, voice-led, velocity growing
    eighths(...)                  the drive: the chord's bass note in eighths
    held(...)                     the pad: voice-led chords held over spans of bars
    subs(...)                     the sub: the chord's bass note held over spans of bars
    until(notes, t)               a layer stopped on a word (its notes end there, the reverb rings on): the room for a drop
    root(sym, near)               the chord's bass note nearest a MIDI note
    KIT, tp(key)                  the chosen sounds (SOUNDS.md) and their transpositions
    Bed                           what a bed function returns: its clock, tracks, film span and named anchors

The word-times file: a JSON list of {"w": word, "start": s, "end": s, "beat": section id}, sorted by start (or {"words": [...]}):
the video's tools/motion/src/<src>/words.json, written by the voice step from the finished narration.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .compose import Clock, Rand, Track, bass_pc, lead  # noqa: F401  (Rand and Track re-exported for film files)

# The sounds (SOUNDS.md has why each won). "@-12" in a name = play every note 12 semitones down.
KIT = {
    "pulse": "Plucks/Diamonds@-12",
    "pulse2": "John Valentine/Sequences/Crockett's Seq Filter Bass",
    "drive": "Basses/FM Bass 1",
    "pad": "Kyurumi/Pads/Neverending",
    "sub": "Vospi/Basses/Floored",
    "subB": "Vospi/Basses/I Can Kinda Be Chordish",
    "drone": "Xenofish/Pads/Fireflies",
    "hit": "A.Liv/Basses/Bonsai 808",
}
# patches that sound an octave under the written note are played +12 (measured: patch_check.py)
TRANSPOSE = {"sub": 12, "subB": 12}


def tp(key: str, kit: dict | None = None, transpose: dict | None = None) -> tuple[str, int]:
    """'Patch@-12' -> ('Patch', -12); else the TRANSPOSE table."""
    kit, transpose = kit or KIT, TRANSPOSE if transpose is None else transpose
    name, _, t = kit[key].partition("@")
    return name, int(t) if t else transpose.get(key, 0)


def _n(s: str) -> str:
    return "".join(c for c in s.lower().replace("’", "").replace("'", "") if c.isalnum())


class Words:
    """The narration's word times. Anchors are looked up by section and phrase, so a new voice reading the same script moves every
    anchor by itself: that is what makes one command retime all the music."""

    def __init__(self, src):
        W = json.loads(Path(src).read_text(encoding="utf-8")) if not isinstance(src, list) else src
        W = W["words"] if isinstance(W, dict) else W
        for x in W:
            if not {"w", "start", "end", "beat"} <= set(x):
                raise ValueError(f"a word needs w, start, end and beat: {x}")
        self.W = sorted(W, key=lambda x: x["start"])

    def first(self, beat: str) -> float:
        """The onset of a section's first word."""
        ts = [x["start"] for x in self.W if x["beat"] == beat]
        if not ts:
            raise KeyError(f"no section {beat!r} in the word times")
        return min(ts)

    def last_end(self, beat: str) -> float:
        """The end of a section's last word."""
        return max(x["end"] for x in self.W if x["beat"] == beat)

    def _find(self, beat: str, phrase: str, nth: int = 0) -> tuple[int, int]:
        toks = [_n(t) for t in phrase.split() if _n(t)]
        W, seen = self.W, 0
        for i, x in enumerate(W):
            if x["beat"] != beat:
                continue
            if all(i + k < len(W) and W[i + k]["beat"] == beat and _n(W[i + k]["w"]) == toks[k] for k in range(len(toks))):
                if seen == nth:
                    return i, i + len(toks) - 1
                seen += 1
        raise KeyError(f"{phrase!r} (#{nth}) not in {beat}")

    def word(self, beat: str, phrase: str, nth: int = 0) -> float:
        """The onset of the first word of `phrase` inside a section (punctuation and case ignored; `nth` = its nth time there)."""
        return self.W[self._find(beat, phrase, nth)[0]]["start"]

    def word_end(self, beat: str, phrase: str, nth: int = 0) -> float:
        """The end of the last word of `phrase` inside a section."""
        return self.W[self._find(beat, phrase, nth)[1]]["end"]

    def end(self) -> float:
        return max(x["end"] for x in self.W)


@dataclass
class Bed:
    clock: Clock
    tracks: list
    t0: float
    t1: float
    anchors: dict = field(default_factory=dict)   # name -> film time: the downbeats this bed promises (checked after rendering)
    events: dict = field(default_factory=dict)    # name -> (track name, film time): notes placed on a word (a hit), checked too
    bpm: float = 0.0                              # the tempo the bed was written at (each segment rounds to whole bars)
    key: str = ""
    note: str = ""
    loop: bool = False                            # a Short's bed: exactly t1 - t0 long, its tail laid over its start


def bars(t0: float, t1: float, bpm: float, bpb: int = 4) -> int:
    """How many whole bars of `bpm` fit best between two film times (at least one)."""
    return max(1, round((t1 - t0) / (bpb * 60 / bpm)))


def clock(points: list[float], bpm: float, bpb: int = 4) -> tuple[Clock, list[int]]:
    """Segments between consecutive anchor times, each a whole number of bars, so every anchor is a downbeat. Returns the clock and
    the first bar of each segment (plus the bar count at the end)."""
    segs, firsts, b = [], [], 0
    for t0, t1 in zip(points, points[1:]):
        n = bars(t0, t1, bpm, bpb)
        segs.append((t0, t1, n, bpb))
        firsts.append(b)
        b += n
    firsts.append(b)
    return Clock(segs), firsts


def seg_bpms(points: list[float], bpm: float, bpb: int = 4) -> list[float]:
    """The tempo each segment really plays at once its bars are rounded to whole bars."""
    return [60.0 * bpb * bars(t0, t1, bpm, bpb) / (t1 - t0) for t0, t1 in zip(points, points[1:])]


def fit_bpm(points: list[float], lo: float, hi: float, bpb: int = 4, step: float = 0.25) -> float:
    """The tempo fit (added in this package; the method itself picks a tempo by hand and rounds each segment to whole bars): scan
    [lo, hi] for the written tempo whose whole-bar rounding gives the smallest tempo change at the worst joint between segments
    (what a listener hears), then the smallest departure from the written tempo. Keep the range narrow (the mood's tempo +-4): it
    chooses within the feel, it doesn't choose the feel."""
    best, key = lo, None
    b = lo
    while b <= hi + 1e-9:
        s = seg_bpms(points, b, bpb)
        joint = max((abs(y / x - 1) for x, y in zip(s, s[1:])), default=0.0)
        k = (round(joint, 4), round(max(abs(x / b - 1) for x in s), 4), abs(b - (lo + hi) / 2))
        if key is None or k < key:
            best, key = b, k
        b += step
    return best


def root(sym: str, near: int) -> int:
    """The chord's bass pitch class as the MIDI note nearest `near` (within a tritone below, else above)."""
    pc = bass_pc(sym)
    n = near - ((near - pc) % 12)
    return n if near - n <= 6 else n + 12


def arp16(clk, bar_ids, chords, low, high, rnd, pattern, vel=(76, 50), gate=0.8, grow=10, steps=16):
    """The pulse. For each bar: the chord voice-led inside [low, high] (doubled an octave up when it has under 4 notes), `steps`
    notes a bar, pattern[k] = an index into that voicing or None for a rest; the first step of each beat at vel[0], the others at
    vel[1]; over the span the velocity rises by `grow` (from -grow/2 to +grow/2); every note nudged up to 3 ms and its velocity
    spread +-5 (rnd)."""
    out, prev = [], None
    bar_ids = list(bar_ids)
    for j, b in enumerate(bar_ids):
        v = lead(prev, chords[b], low, high)
        prev = v
        if len(v) < 4:
            v = v + [n + 12 for n in v]
        step = clk.beat_len(b) * 4 / steps
        lift = round(grow * j / max(1, len(bar_ids) - 1)) - grow // 2
        for k in range(steps):
            idx = pattern[k % len(pattern)]
            if idx is None:
                continue
            t = rnd.nudge(clk.t(b) + k * step, 3)
            out.append((t, step * gate, v[idx % len(v)], rnd.vel((vel[0] if k % max(1, steps // 4) == 0 else vel[1]) + lift, 5)))
    return out


def eighths(clk, bar_ids, chords, near, rnd, vel=(88, 64), gate=0.7):
    """The drive: the chord's bass note (nearest `near`) in eighths, on-beats louder, nudged 3 ms, velocity spread +-4."""
    out = []
    for b in bar_ids:
        r = root(chords[b], near)
        step = clk.beat_len(b) / 2
        for k in range(8):
            out.append((rnd.nudge(clk.t(b) + k * step, 3), step * gate, r, rnd.vel(vel[0] if k % 2 == 0 else vel[1], 4)))
    return out


def held(clk, spans, chords, low, high, vel=62):
    """The pad: for each (first bar, n bars) span, the chord of its first bar voice-led inside [low, high], held to the span's end
    (+50 ms so held chords join)."""
    out, prev = [], None
    for b, n in spans:
        t0, t1 = clk.t(b), clk.t(b + n)
        v = lead(prev, chords[b], low, high)
        prev = v
        out += [(t0, t1 - t0 + 0.05, m, vel) for m in v]
    return out


def subs(clk, spans, chords, near=33, vel=94):
    """The sub: one long bass note (the chord's root nearest `near`) per (first bar, n bars) span, released 20 ms early."""
    return [(clk.t(b), clk.t(b + n) - clk.t(b) - 0.02, root(chords[b], near), vel) for b, n in spans]


def until(notes, t: float, ring: float = 0.1) -> list:
    """The room before a word (a statement drop, a stop): the notes that start before t - 0.05, each ending by t + ring, so the
    layer stops on the word and only its reverb tail rings on (never a level dip to silence: the mix flags a silence)."""
    return [(s, min(d, t + ring - s), m, v) for s, d, m, v in notes if s < t - 0.05]


def prog(chords: list[str], n: int, start: int = 0) -> list[str]:
    """`chords` (one symbol per bar) repeated to fill n bars."""
    return [chords[(b - start) % len(chords)] for b in range(start, start + n)]
