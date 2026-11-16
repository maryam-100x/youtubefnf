"""The music for a made-up two-minute film, "How bridges are built" (example/script.txt): four beds, one per chapter, written on the
narration's words. This file is the template: a video's music file (videos/<video>/score/music.py) is shaped like this one.

Every anchor is looked up in the word times by section and phrase (W.first, W.word, W.last_end), never typed in as a number, so
`music.py render <film.py>` after a new voice retimes every bed to it.

The keys walk up a fourth a chapter (A minor -> D minor -> G minor) and the end comes home to the open's key and chords. Each bed
ends exactly where the next begins (the next chapter's first word, its first downbeat): never two beds at once. A low hit on a
narration word is the cue sheet's statement drop (the house bass drop), never written into a bed: the bed only leaves it the room
(its pulse out just before the word). The one hit a bed plays itself is the close, on the last word's end.

  bed O, A minor, ~96 bpm: the open (S01-S03). The open's chords (Am | F | C | G) and a light pulse from frame 0; from "But a bridge"
        (S02) darker (Am | F | Dm | E), the pulse thins to eighths, the sub in; just before "holds its breath" the pulse and the pad
        out (the cue sheet's statement drop lands in that room), only a low drone under the held breath; from "So how" (S03) the
        pulse back over the open's chords, growing to the question.
  bed G, D minor, ~100 bpm: THE GROUND (S04-S06), from the first chapter card. A light pulse in eighths (Dm | Bb | F | C) and the
        pad fading in; from "But the river" (S06) uneasy (Dm | Bb | Gm | A), the pulse in sixteenths and the driving bass in.
  bed S, G minor, ~104 bpm: THE SPAN (S07-S09). A ticking clock of sixteenths (Gm | Eb | Cm | D); a drone from "Nobody on the crew"
        (S08); just before "locks into place" (S09, the cue sheet's statement drop) the clock and the sub out, the pad left ringing.
  bed E, A minor (home), ~94 bpm: THE TEST and the end (S10-S12). Lighter (C | G | Am | F), a calm pulse; from "And then the town"
        (S12) the open's chords come home, the last chord under the last word, a low hit on its end, ringing out with the end.

    SYNTH tools/music/music.py render tools/music/example/film.py [--words tools/music/example/words_voice2.json] [--stems] [--judge]
"""
from __future__ import annotations

from musickit.compose import LEVELS, Rand, Track
from musickit.writing import Bed, Words, arp16, clock, eighths, fit_bpm, held, prog, root, subs, tp, until

TITLE = "How bridges are built (a made-up example)"
DEFAULT_WORDS = "words.json"   # beside this file; --words overrides it
TAIL_S = 3.0          # the film runs this long after the last word (the end card): the last bed rings into it


def film_end(W: Words) -> float:
    return round(W.end() + TAIL_S, 3)


# ------------------------------------------------------------------------------------------------------------------------ bed O
def bed_o(W: Words) -> Bed:
    """The open: bright to S02, darker from S02, out before the held breath (the statement drop's room), a drone under it, the
    build over S03. It ends on the first chapter card's word, where bed G begins."""
    O0, O_DARK, O_TURN, O_END = 0.0, W.first("S02"), W.first("S03"), W.first("S04")
    O_HOLD, O_LAST = W.word("S02", "holds its breath"), W.last_end("S03")
    points = [O0, O_DARK, O_TURN, O_END]
    bpm = fit_bpm(points, 92, 100)
    clk, fb = clock(points, bpm)
    b_dark, b_turn, b_end = fb[1], fb[2], fb[3]
    rnd = Rand(101)
    open_prog = ["Am", "Am", "F", "F", "C", "C", "G", "G"]
    dark_prog = ["Am", "Am", "F", "F", "Dm", "Dm", "E", "E"]
    ch = prog(open_prog, b_dark) + prog(dark_prog, b_turn - b_dark) + prog(open_prog, b_end - b_turn + 1)
    pat_open = [0, None, 2, None, 1, None, 2, 3, 0, None, 2, None, 1, 2, None, 3]
    pat_dark = [0, None, 1, None, 2, None, 1, None]
    pat_turn = [0, 2, 1, 2, 3, 2, 1, 2, 0, 2, 1, 2, 3, 2, 1, 2]
    pulse = arp16(clk, range(0, b_dark), ch, 52, 71, rnd, pat_open, vel=(70, 48), grow=8)
    pulse += until(arp16(clk, range(b_dark, b_turn), ch, 45, 64, rnd, pat_dark, vel=(62, 44), steps=8, grow=6), O_HOLD)
    pulse += [n for n in arp16(clk, range(b_turn, b_end), ch, 50, 69, rnd, pat_turn, vel=(70, 48), grow=14) if n[0] < O_LAST + 0.4]
    sub = until(subs(clk, [(b, 1) for b in range(b_dark, b_turn)], ch, near=33), O_HOLD)
    sub += [s for s in subs(clk, [(b, 1) for b in range(b_turn + 1, b_end)], ch, near=33) if s[0] < O_LAST]
    pad = held(clk, [(b, 2) for b in range(0, b_dark, 2)], ch, 52, 71, vel=58)
    pad += until(held(clk, [(b, 2) for b in range(b_dark, b_turn, 2)], ch, 50, 69, vel=56), O_HOLD)
    pad += [n for n in held(clk, [(b, 2) for b in range(b_turn, b_end, 2)], ch, 52, 71, vel=58) if n[0] < O_LAST]
    drone = [(O_HOLD, O_TURN - O_HOLD + 0.6, 45, 64)]                        # a low A under the held breath, swelling from the word
    # no hit on "holds its breath": that is the cue sheet's statement drop, Sfx(pal("bass_drop"), FILM.w("S02", "holds its breath"))
    tracks = [
        Track("pulse", tp("pulse")[0], pulse, hp=100, lp=1500, reverb=0.2, level=LEVELS["pulse"], transpose=tp("pulse")[1]),
        Track("sub", tp("sub")[0], sub, lp=400, level=LEVELS["sub"], transpose=tp("sub")[1]),
        Track("pad", tp("pad")[0], pad, hp=150, lp=1700, reverb=0.4, level=LEVELS["pad"],
              auto=[(O_DARK, -2), (O_TURN, -2), (O_TURN + 0.3, -3), (O_END, -6)]),   # out by its notes, its tail ringing
        Track("drone", tp("drone")[0], drone, hp=50, lp=700, reverb=0.4, level=LEVELS["drone"] - 4),
    ]
    return Bed(clk, tracks, O0, O_END, bpm=bpm, key="A minor",
               anchors={"open": O0, "S02 'But a bridge'": O_DARK, "S03 'So how'": O_TURN, "S04 chapter card (bed G)": O_END},
               events={"drone under the held breath": ("drone", O_HOLD)})


# ------------------------------------------------------------------------------------------------------------------------ bed G
def bed_g(W: Words) -> Bed:
    """THE GROUND: a light pulse in eighths; uneasy and driving from 'But the river'."""
    t0, t_river, t_end = W.first("S04"), W.first("S06"), W.first("S07")
    points = [t0, t_river, t_end]
    bpm = fit_bpm(points, 96, 104)
    clk, fb = clock(points, bpm)
    b_river, b_end = fb[1], fb[2]
    rnd = Rand(202)
    ground = ["Dm", "Dm", "Bb", "Bb", "F", "F", "C", "C"]
    river = ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A"]
    ch = prog(ground, b_river) + prog(river, b_end - b_river + 1)
    pulse = arp16(clk, range(1, b_river), ch, 50, 69, rnd, [0, None, 2, None, 1, None, 2, None], vel=(60, 42), steps=8, grow=6)
    pulse += arp16(clk, range(b_river, b_end), ch, 48, 67, rnd, [0, 2, 1, 2, 0, 2, 1, 3] * 2, vel=(70, 50), grow=10)
    drive = eighths(clk, list(range(b_river, b_end)), ch, 38, rnd, vel=(82, 58))
    pad = held(clk, [(b, 2) for b in range(0, b_end, 2)], ch, 50, 67, vel=60)
    sub = subs(clk, [(b, 2) for b in range(2, b_end, 2)], ch, near=31, vel=84)
    tracks = [
        Track("pad", tp("pad")[0], pad, hp=150, lp=1600, reverb=0.4, level=LEVELS["pad"], auto=[(t0, -4), (t0 + 2.4, 0), (t_end, -6)]),
        Track("pulse", tp("pulse2")[0], pulse, hp=120, lp=2000, reverb=0.25, level=LEVELS["pulse"] - 1, transpose=tp("pulse2")[1]),
        Track("drive", tp("drive")[0], drive, lp=600, level=LEVELS["drive"], transpose=tp("drive")[1]),
        Track("sub", tp("subB")[0], sub, lp=350, level=LEVELS["sub"] - 2, transpose=tp("subB")[1]),
    ]
    return Bed(clk, tracks, t0, t_end, bpm=bpm, key="D minor",
               anchors={"S04 'The ground'": t0, "S06 'But the river'": t_river, "S07 (next bed)": t_end})


# ------------------------------------------------------------------------------------------------------------------------ bed S
def bed_s(W: Words) -> Bed:
    """THE SPAN: a ticking clock of sixteenths; a drone from 'Nobody'; the clock out before 'locks into place' (the statement drop's
    room: the cue sheet's bass drop lands on it)."""
    t0, t_meet, t_end = W.first("S07"), W.first("S08"), W.first("S10")
    t_nobody, t_lock = W.word("S08", "Nobody on the crew"), W.word("S09", "locks into place")
    points = [t0, t_meet, t_end]
    bpm = fit_bpm(points, 100, 108)
    clk, fb = clock(points, bpm)
    b_meet, b_end = fb[1], fb[2]
    rnd = Rand(303)
    span = ["Gm", "Gm", "Eb", "Eb", "Cm", "Cm", "D", "D"]
    ch = prog(span, b_end + 1)
    tick = until(arp16(clk, range(0, b_end), ch, 55, 74, rnd, [0, None, 0, None, 0, None, 0, 1] * 2, vel=(60, 40), gate=0.35,
                       grow=8), t_lock)
    pad = held(clk, [(b, 2) for b in range(0, b_end, 2)], ch, 50, 67, vel=58)
    sub = until(subs(clk, [(b, 2) for b in range(0, b_end, 2)], ch, near=31, vel=86), t_lock)
    drone = [(t_nobody, t_lock - t_nobody, 43, 70)]
    tracks = [
        Track("pad", tp("pad")[0], pad, hp=150, lp=1500, reverb=0.45, level=LEVELS["pad"] + 2, auto=[(t0, -3), (t0 + 2.5, 0), (t_end, -6)]),  # +2: the pad carries the bed after the drop
        Track("pulse", tp("pulse")[0], tick, hp=140, lp=1800, reverb=0.2, level=LEVELS["pulse"] - 2, transpose=tp("pulse")[1]),
        Track("sub", tp("subB")[0], sub, lp=350, level=LEVELS["sub"] - 1, transpose=tp("subB")[1]),   # (mixdown: every window over the bar)
        Track("drone", tp("drone")[0], drone, hp=60, lp=900, reverb=0.4, level=LEVELS["drone"]),
    ]
    return Bed(clk, tracks, t0, t_end, bpm=bpm, key="G minor",
               anchors={"S07 'The span'": t0, "S08 'The two halves'": t_meet, "S10 (next bed)": t_end},
               events={"drone on 'Nobody'": ("drone", t_nobody)})


# ------------------------------------------------------------------------------------------------------------------------ bed E
def bed_e(W: Words) -> Bed:
    """THE TEST and the end: lighter, then the open's chords home, the last chord ringing out."""
    t0, t_home, t_wordend = W.first("S10"), W.first("S12"), W.last_end("S12")
    end = film_end(W)
    points = [t0, t_home, t_wordend]
    bpm = fit_bpm(points, 90, 98)
    clk, fb = clock(points, bpm)
    b_home, b_end = fb[1], fb[2]
    rnd = Rand(404)
    light = ["C", "C", "G", "G", "Am", "Am", "F", "F"]
    home = ["Am", "Am", "F", "F", "C", "C", "G", "G"]
    ch = prog(light, b_home) + prog(home, b_end - b_home + 2)
    pulse = arp16(clk, range(1, b_home), ch, 52, 71, rnd, [0, None, 2, None, 1, None, 2, 3], vel=(62, 42), steps=8, grow=8)
    pulse += arp16(clk, range(b_home, b_end), ch, 52, 71, rnd, [0, None, 2, None, 1, None, 2, None], vel=(56, 38), steps=8)
    pad = held(clk, [(b, 2) for b in range(0, b_end, 2)], ch, 52, 71, vel=60)
    pad += [(t_wordend, end - t_wordend + 2.0, m, 58) for m in (57, 60, 64)]       # Am, ringing out with the end
    sub = subs(clk, [(b, 2) for b in range(2, b_end, 2)], ch, near=33, vel=86)
    sub += [(t_wordend, end - t_wordend, root("Am", 33), 84)]
    hit = [(t_wordend, 3.0, 45, 104)]
    tracks = [
        Track("pad", tp("pad")[0], pad, hp=150, lp=1700, reverb=0.45, level=LEVELS["pad"], auto=[(t0, -4), (t0 + 2.6, 0), (end, -8)]),
        Track("pulse", tp("pulse")[0], pulse, hp=110, lp=1500, reverb=0.25, level=LEVELS["pulse"] - 1, transpose=tp("pulse")[1]),
        Track("sub", tp("sub")[0], sub, lp=380, level=LEVELS["sub"], transpose=tp("sub")[1]),
        Track("hit", tp("hit")[0], hit, lp=900, reverb=0.25, level=LEVELS["hit"] - 4),
    ]
    return Bed(clk, tracks, t0, end, bpm=bpm, key="A minor (home)",
               anchors={"S10 'The test'": t0, "S12 'And then the town'": t_home, "the last word's end": t_wordend},
               events={"hit on the last word's end": ("hit", t_wordend)})


BEDS = {"O": bed_o, "G": bed_g, "S": bed_s, "E": bed_e}
