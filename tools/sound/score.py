"""The score engine: a video's whole soundtrack, music and effects, from one cue list anchored to the narration's words. The picture's
own audio is not used (except where a cue list keeps a stretch of it on purpose).

Music cues are placed so that a chosen moment of the track (a downbeat, a section start, a drop) lands on an anchor word; each cue's
level is set from its own measured loudness to a target under the voice; under speech the music is ducked and its voice band (about
0.9-4.5 kHz) is carved. A cue's track is any audio file: one of the creator's own in MUSIC, or one rendered by tools/music.

Handoffs follow the sound standard (standard/SOUND_AND_VOICE.md): two different tracks never overlap by more than 0.1 s. Where one cue
hands to the next, the switch moves to the outgoing track's own downbeat (or beat) nearest the narration's pause; the outgoing cue plays
through that beat and cuts with a 45-ms fade, and the incoming cue starts 25 ms before its downbeat so its attack lands on the same
point. A cue marked `hold_in` (a chapter card) keeps its entry; the outgoing cue stops on its last beat before it. A beatless outgoing
cue (a pad) fades instead. Exits that aren't handoffs: "stop" (a hard out with a 60-ms fade on a word) or "fade".

A chapter card's music never jumps more than 6 dB (CARD_JUMP) over the bed before it.

Effects are placed by their impact (measured from the file: where it first reaches 6 dB under its peak, unless a cue list gives `sync`).
Effects that are almost all sub-bass get harmonics (150 Hz-2 kHz) so they still read on TV, laptop and phone speakers.

Where the bed's left and right cancel (it would vanish on a mono speaker), its stereo is narrowed there.

Checks printed after every mix: the handoffs, overlapping music, silences of 50 ms+ under -50 dBFS outside the designed ones, voice minus
music per cue during speech, effects per minute, effect impacts, mono correlation, and each hit's level above 400 Hz against the rest.

Every effect is a sound the creator rated (the rating lock: rating() below; tools/sound/palette.json holds the ratings): an unrated
sound is refused when the cue sheet builds it and again at the mix, unless it is marked Sfx(..., test=True), a sample for the creator's
ear, and the mix is made with --test-sounds (the pipeline's score step never passes it, so a test sound never reaches a delivery). A cut
of a rated file names it: Sfx(cut, ..., of=<the rated file>). Effects live in SFX.

  EDIT tools/sound/score.py <cue module.py> <out.wav|out.mp4> [--picture render.mkv] [--test-sounds] [--stems <dir>]"""
import importlib.util
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, SFX  # noqa: E402

SR = 48000
PRE = 0.025        # an entry on a downbeat starts this far before it (the attack is inside), with a 5-ms fade
CUT = 0.03         # an outgoing cue plays this far past its last beat, then fades over FADE
FADE = 0.045
FOUT_S, FIN_S, CARD_FIN = 1.2, 1.5, 0.8   # HANDOFF_STYLE "smooth" (no hard cuts): fade out, fade in, a 0.3-s low-level touch between


def load(path, ss=0.0, t=None):
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{max(0.0, ss):.4f}"] + (["-t", f"{t:.4f}"] if t else []) + ["-i", str(path)]
    cmd += ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    a = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()
    if ss < 0:  # a cue that starts before the track does: pad
        a = np.vstack([np.zeros((int(-ss * SR), 2), np.float32), a])
    return a


def kweight(x):
    """BS.1770 K-weighting (the shelf, then the RLB high-pass), as the loudness meters hear."""
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    """Integrated loudness (BS.1770 K-weighting, 400-ms blocks, absolute and relative gates)."""
    if len(x) < SR // 2:
        return -70.0
    k = kweight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([(k[i:i + blk] ** 2).mean(axis=0).sum() for i in range(0, len(k) - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[lk > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(g.mean() + 1e-12))


def rms_db(x):
    return 20 * np.log10(np.sqrt((np.asarray(x, np.float64) ** 2).mean()) + 1e-12) if len(x) else -120.0


class Film:
    """Word and beat times of the narration (the film's own JSON: [{w, start, end, beat}] and {beats: [{id, start, end}]})."""

    def __init__(self, words, beats):
        self.W = json.loads(Path(words).read_text(encoding="utf-8"))
        d = json.loads(Path(beats).read_text(encoding="utf-8"))
        self.B = {b["id"]: b for b in d["beats"]}
        self.duration = d["duration"]

    @staticmethod
    def _n(s):
        import re
        return re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "").replace("'", ""))

    def _find(self, beat, phrase, nth=0):
        toks = [self._n(t) for t in phrase.split() if self._n(t)]
        seen = 0
        for i in range(len(self.W)):
            if self.W[i]["beat"] != beat:
                continue
            if all(i + k < len(self.W) and self.W[i + k]["beat"] == beat and self._n(self.W[i + k]["w"]) == toks[k] for k in range(len(toks))):
                if seen == nth:
                    return i, i + len(toks) - 1
                seen += 1
        raise KeyError(f'"{phrase}" (#{nth}) is not in {beat}')

    def w(self, beat, phrase, nth=0):
        return self.W[self._find(beat, phrase, nth)[0]]["start"]

    def we(self, beat, phrase, nth=0):
        return self.W[self._find(beat, phrase, nth)[1]]["end"]

    def b(self, beat):
        return self.B[beat]["start"]

    def be(self, beat):
        return self.B[beat]["end"]

    def pause(self, t):
        """(end of the last word before t, start of the first word after t)."""
        ends = [x["end"] for x in self.W if x["end"] <= t + 0.02]
        starts = [x["start"] for x in self.W if x["start"] >= t - 0.02]
        return (max(ends) if ends else t), (min(starts) if starts else t)


@dataclass
class Cue:
    id: str
    path: str
    t0: float                 # film time the cue starts
    t1: float                 # film time the cue ends (a handoff moves it to the track's own beat nearby)
    src: float = 0.0          # track time at t0 (or set by align)
    align: tuple = None       # (track time, film time): that moment of the track lands on that film time
    under: float = 15.0       # dB under the voice (the cue's own loudness against the voice's)
    fin: float = 0.3          # fade in (s) for an entry that isn't on a downbeat
    exit: str = "fade"        # "fade" | "button" (a handoff: cut on the beat) | "stop"
    fout: float = 1.0         # fade length for "fade" (and for a beatless "button")
    auto: list = field(default_factory=list)   # [(film time, under)] level moves inside the cue (linear between points)
    duck: bool = True         # duck and carve under speech
    hold_in: bool = False     # the entry stays on its anchor (a chapter card); the cue before stops on its last beat before it
    note: str = ""


@dataclass
class Sfx:
    path: str
    t: float                  # film time of the effect's impact
    db: float = -18.0         # its peak, in dB relative to the voice's peak level (about); tuned per category
    sync: float = None        # where its impact sits in the file (s); None = measured (6 dB under its peak, 5-ms envelope)
    dur: float = None         # cut the effect after this long from its impact (a 0.15-s fade); None = the whole file
    note: str = ""
    harm: float = None        # its harmonics for small speakers, dB against its low band (see harmonize); None = SFX_HARMONICS_DB, sub-heavy files only
    test: bool = False        # a sample for the creator's ear: an unrated sound may play here only, and only in a mix made with --test-sounds
    of: str = None            # this file is a cut of that one (e.g. single keys cut out of a rated keyboard recording): the rating is that file's

    def __post_init__(self):
        # a sound the creator banned is refused by its file name, whichever path or palette name brought it
        for p in (self.path, self.of):
            name = Path(str(p)).name if p else None
            if name and name in PALETTE.get("_banned", {}):
                raise ValueError(f"{name} is banned: {str(PALETTE['_banned'][name].get('why', ''))[:120]}")
        # a sound the creator never rated is refused, so no untried library sound reaches a film. A new sound goes to the creator
        # first, as a sample (test=True, a mix made with --test-sounds) or a Sound Test round, and into palette.json after their yes.
        # a sound that stands for an action with a length (a count's ticks) is cut to that length: palette "needs_dur" refuses it
        # whole, so an effect never plays on past the action it stands for
        if self.dur is None:
            for nm, e in PALETTE.items():
                if isinstance(e, dict) and e.get("needs_dur") and str(e.get("file")) == str(self.path):
                    raise ValueError(f"pal('{nm}') must be cut to its action's length: Sfx(..., dur=<seconds from the impact to the "
                                     f"action's end>) ({e['needs_dur'][:110]})")
        label, ok, _ = rating(self.of or self.path, self.note)
        if not ok and not self.test and SFX_LOCK[0] == "refuse":
            raise ValueError(f"{Path(str(self.path)).name} is a sound the creator never rated ({label}; note: '{self.note[:60]}'). Use "
                             "the rated sound for the job (pal(name), a pack Keep in palette.json pack_jobs, a Sound Test fit), or play "
                             "it to the creator first: Sfx(..., test=True) in a sample mixed with --test-sounds, then their yes into "
                             "palette.json (tools/sound/sfx_verdict.py; the rating lock)")
        if not ok and not self.test:
            UNRATED.append((str(self.path), label, self.note))


# the house palette and the creator's ratings (built at setup from the house effects set, grown by sfx_verdict.py). Missing: every
# effect counts as unrated, so the lock refuses them all until the palette is in place
PALETTE_FILE = Path(__file__).with_name("palette.json")
PALETTE = json.loads(PALETTE_FILE.read_text(encoding="utf-8")) if PALETTE_FILE.exists() else {}
SFX_LOCK = ["refuse"]   # "record": a reader of old cue sheets (music_library.py, sfx_rated.py) lists unrated sounds in UNRATED instead
UNRATED = []
PACK = str(SFX / "pack").replace("\\", "/").lower() + "/"   # the house pack's files (palette.json pack_jobs)


def _slash(p):
    return str(p).replace("\\", "/")


def rating(path, note=""):
    """Where an effect comes from, by the creator's ratings: (label, rated, memey). Rated: a house sound (palette.json, pal(name)); the
    house pack's Keeps (palette.json pack_jobs, files in SFX/pack/; 'memey' = jokes only); a Sound Test fit (palette.json
    _sound_test_fits, by the sound's file name, in whichever folder it sits); the creator's picks in palette.json _creator_picks; and a
    clip's own sound (a bite or a clip's audio, outside every sound library, its note or name saying so: not an effect). Anything else is
    a library sound the creator never rated, refused by Sfx (the rating lock)."""
    p = _slash(path)
    pl = p.lower()
    for name, v in PALETTE.items():
        if isinstance(v, dict) and v.get("file") and _slash(v["file"]).lower() == pl:
            return f"house sound pal('{name}')", True, "meme" in json.dumps(v).lower()
    fname = Path(p).name
    if pl.startswith(PACK) or "/sfx/pack/" in pl:
        for job, lst in (PALETTE.get("pack_jobs") or {}).items():
            if job.startswith("_") or not isinstance(lst, list):
                continue
            for e in lst:
                if isinstance(e, list) and e and e[0] == fname:
                    notes = " / ".join(str(x) for x in e[1:2])
                    return f"house pack Keep ({job}: '{notes}')", True, ("meme" in job or any("meme" in str(x).lower() for x in e[1:]))
    fits = {str(k).lower(): v for k, v in (PALETTE.get("_sound_test_fits") or {}).items()}
    if fname.lower() in fits:
        return f"Sound Test fit {fname} ({str(fits[fname.lower()])[:50]})", True, False
    for e in PALETTE.get("_creator_picks") or []:
        if _slash(e.get("file", "")).lower() == pl:
            return f"the creator's pick ({e.get('why', '')[:50]})", True, False
    own = (any(k in (note or "").lower() for k in ("own sound", "own voice")) or fname.lower().startswith("bite_")
           or "/bites/" in pl or "clipaudio" in pl)
    if own and "/sfx/" not in pl:
        return "a clip's own sound", True, False
    return "library, not rated by the creator", False, False


def pal(name):
    """The house sound for a recurring action (one sound for one kind of action, everywhere), the creator's pick, from palette.json."""
    if name not in PALETTE or name.startswith("_") or name == "pending":
        raise KeyError(f"no house sound for '{name}' yet: it goes through the creator's Sound Test first")
    return PALETTE[name]["file"]


_grids, _pulse = {}, {}


def grid(path):
    if path not in _grids:
        p = Path(str(path) + ".grid.json")
        _grids[path] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"tempo": 0, "beats": [], "downbeats": []}
    return _grids[path]


def code_beds(folder, under=13.0, fout=0.3, last_fout=1.0):
    """The beds tools/music rendered for a video (`SYNTH tools/music/music.py render <film.py>`, by default into
    MEDIA/videos/<video>/build/music/), as music cues. Each plays at its own film time (its .wav.json: t0, t1) from its own start (it
    was written on the film's clock, so its track time 0 is film time t0, a downbeat), with no bed levelling (`level = 0.0`: it is
    written steady, and its designed moves, a pulse out before a drop, a pad down under a held breath, stay as written), `under` the
    sheet's UNDER, and a short fade at its end (the next bed begins there on its own first downbeat; the last bed fades over
    `last_fout`). Raises when two beds would play at once."""
    rows = []
    for meta in sorted(Path(folder).glob("bed_*.wav.json")):
        m = json.loads(meta.read_text(encoding="utf-8"))
        if "t0" in m and "t1" in m:
            rows.append((float(m["t0"]), float(m["t1"]), m, meta.with_suffix("")))
    if not rows:
        raise FileNotFoundError(f"no beds in {folder}: render them first (SYNTH tools/music/music.py render <film.py>)")
    rows.sort(key=lambda r: r[0])
    cues = []
    for i, (t0, t1, m, wav) in enumerate(rows):
        bid = m.get("bed", wav.stem[4:])
        c = Cue(f"M{bid}", str(wav), t0, t1, src=0.0, under=under, exit="fade", fout=last_fout if i == len(rows) - 1 else fout,
                note=f"code bed {bid} ({m.get('key', '')})")
        c.level = 0.0
        c.hits = {k: float(v[1]) for k, v in m.get("events", {}).items() if v[0] == "hit"}   # its own low hits, on their words
        cues.append(c)
    for a, b in zip(cues, cues[1:]):
        if b.t0 < a.t1 - 0.01:
            raise ValueError(f"beds {a.id} and {b.id} would play at once ({a.id} ends {a.t1:.2f}, {b.id} begins {b.t0:.2f}): a bed ends "
                             "where the next begins (standard/MUSIC.md)")
    return cues


def pulse(path, a, b, period):
    """Onset-envelope autocorrelation at the beat period over track time [a, b]: ~0.5+ clearly rhythmic, under 0.25 beatless."""
    import librosa
    if path not in _pulse:
        y, sr = librosa.load(str(path), sr=22050, mono=True)
        _pulse[path] = (librosa.onset.onset_strength(y=y, sr=sr, hop_length=256), sr)
    env, sr = _pulse[path]
    h = 256 / sr
    e = env[int(max(0, a) / h):int(max(0, b) / h)]
    if len(e) < 40 or period <= 0:
        return 0.0
    e = e - e.mean()
    lag = int(round(period / h))
    if lag >= len(e) - 5:
        return 0.0
    ac = np.correlate(e, e, "full")[len(e) - 1:]
    return float(ac[lag] / (ac[0] + 1e-9))


def src_of(c):
    return c.src if c.align is None else c.align[0] - (c.align[1] - c.t0)


def on_downbeat(c):
    """True when the cue's entry point is one of its track's downbeats (so it starts on the attack)."""
    d = np.array(grid(c.path)["downbeats"])
    return bool(len(d)) and float(np.min(np.abs(d - src_of(c)))) < 0.012


def plan_handoffs(mod):
    """Move every handoff between adjacent cues onto the outgoing track's own beat (the sound standard's handoff rules). Changes the cues in
    place; returns a report."""
    film, rep = mod.FILM, []
    cues = sorted(mod.CUES, key=lambda x: x.t0)
    for c in cues:
        c._entry = "beat" if on_downbeat(c) else "free"
        if c._entry == "free" and c.align is None and c.src < 1.0:  # a silent file head: start on the first sound
            head = load(c.path, c.src, 1.0).mean(axis=1)
            h = int(0.01 * SR)
            lv = [rms_db(head[k * h:(k + 1) * h]) for k in range(len(head) // h)]
            k = next((i for i, v in enumerate(lv) if v > -50), 0)
            if k >= 3:
                c.src += (k - 1) * 0.01
    mod._stopdowns, mod._handoffs = [], []
    for a, b in zip(cues, cues[1:]):
        if a.exit != "button" or abs(b.t0 - a.t1) > 0.05:
            continue
        T = a.t1
        g = grid(a.path)
        sa = src_of(a)
        period = 60 / g["tempo"] if g.get("tempo") else 0
        beats = a.t0 + (np.array(g["beats"]) - sa) if g["beats"] else np.array([])
        downs = a.t0 + (np.array(g["downbeats"]) - sa) if g["downbeats"] else np.array([])
        xa = sa + (T - a.t0)
        rhythmic = len(beats) and pulse(a.path, xa - 8, xa, period) >= 0.25
        if b.hold_in:
            lo, hi = T - 0.6, T - 0.005
            pick = lambda arr: arr[(arr >= lo) & (arr <= hi)]
            choose = lambda arr: float(arr.max())
        else:
            pe, ns = film.pause(T)
            lo, hi = max(T - 0.45, pe - 0.15), min(T + 0.30, ns + 0.25)
            if lo > hi:
                lo, hi = T - 0.2, T + 0.2
            pick = lambda arr: arr[(arr >= lo) & (arr <= hi) & (arr > a.t0 + 1.0)]
            choose = lambda arr: float(arr[np.argmin(np.abs(arr - T))])
        H, kind = None, "pad"
        if rhythmic:
            for arr, k in ((downs, "downbeat"), (beats, "beat")):
                cand = pick(arr) if len(arr) else arr
                if len(cand):
                    H, kind = choose(cand), k
                    break
            if H is None and not b.hold_in and period:  # a slow track with no beat inside the pause: the nearest beat within half a beat
                near = beats[(np.abs(beats - T) <= period / 2 + 0.05) & (beats > a.t0 + 1.0)]
                if len(near):
                    H, kind = float(near[np.argmin(np.abs(near - T))]), "beat (wide)"
            if H is None:
                kind = "no beat near"
        if getattr(mod, "HANDOFF_STYLE", "beat") == "smooth":  # the smooth style: no hard cuts; out to the beat, then in
            H = T if H is None else H
            a.t1, a._exit, a._fout = H, "smooth", (1.0 if b.hold_in else FOUT_S)
            if b.hold_in:
                b._entry = "card"
                mod._stopdowns.append((min(H, b.t0 - 0.6) + 0.1, b.t0 + 0.05))
            else:
                b.t0, b._entry = H, "smooth"
                mod._handoffs.append((a.id, b.id, H))
            rep.append((a.id, b.id, T, H, H - T, kind, b._entry))
            continue
        if H is None:  # a beatless outgoing cue (or no beat in reach): a short fade on the old time
            a._exit, a._fout = "pad", max(a.fout, 0.8)
            rep.append((a.id, b.id, T, T, 0.0, kind, b._entry))
            continue
        a.t1, a._exit = H, "beat"
        if b.hold_in:  # the stop before a chapter card is designed: listed with the designed silences
            mod._stopdowns.append((H + CUT + FADE - 0.05, b.t0 + 0.05))
        if not b.hold_in:  # the incoming cue starts on H (a src cue moves with it, so its downbeat lands on H; an aligned one stays on its word)
            b.t0 = H
        rep.append((a.id, b.id, T, H, H - T, kind, b._entry if not b.hold_in else "held"))
    # code beds (code_beds) switch exactly where one ends and the next begins, on the new bed's first downbeat: no beat to move to,
    # but the switch is a switch all the same, so the level rule at a switch (LEVEL_JUMP) and its report cover it
    for a, b in zip(cues, cues[1:]):
        if hasattr(a, "hits") and hasattr(b, "hits") and abs(b.t0 - a.t1) <= 0.05:
            mod._handoffs.append((a.id, b.id, b.t0))
            rep.append((a.id, b.id, a.t1, b.t0, 0.0, "code beds", getattr(b, "_entry", "free")))
    return rep


def effect_sync(a):
    """The impact: where the 5-ms RMS envelope first reaches 6 dB under its peak."""
    m = a.mean(axis=1)
    h = int(0.005 * SR)
    n = len(m) // h
    env = np.sqrt((m[:n * h].reshape(n, h) ** 2).mean(axis=1))
    return float(np.argmax(env >= env.max() * 10 ** (-6 / 20)) * h / SR)


def harmonize(a, rel_db):
    """Psychoacoustic bass for small speakers: the low band 3 dB down, plus its harmonics (150 Hz-2 kHz) at rel_db
    under the low band's level."""
    low = sosfiltfilt(butter(4, 150, "lowpass", fs=SR, output="sos"), a, axis=0)
    pk = np.abs(low).max() + 1e-9
    h = np.tanh(4.0 * low / pk) + 0.5 * np.abs(low) / pk
    h = sosfiltfilt(butter(2, [150, 2000], "bandpass", fs=SR, output="sos"), h, axis=0)
    g = 10 ** ((rms_db(low) - rms_db(h) + rel_db) / 20)
    return (a - low + low * 10 ** (-3 / 20) + h * g).astype(np.float32)


def low_share(a):
    m = a.mean(axis=1)
    s = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / SR)
    return float(s[f < 150].sum() / (s.sum() + 1e-12))


def mono_safe(x, win=1.0, hop=0.05):
    """Scale the side (L-R) down where the L/R correlation over `win` falls under 0.2 (to 0.1 of it at -0.5 and below), smoothed."""
    w, h = int(win * SR), int(hop * SR)
    n = max(1, (len(x) - w) // h)
    g = np.ones(n, np.float32)
    for i in range(n):
        l, r = x[i * h:i * h + w, 0], x[i * h:i * h + w, 1]
        if np.std(l) < 1e-6 or np.std(r) < 1e-6:
            continue
        c = float(np.corrcoef(l, r)[0, 1])
        g[i] = float(np.interp(c, [-0.5, 0.2], [0.1, 1.0]))
    k = int(0.5 / hop)
    g = np.convolve(np.pad(g, (k, k), mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    gs = np.interp(np.arange(len(x)), np.arange(n) * h + w // 2, g).astype(np.float32)
    mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
    return np.stack([mid + gs * side, mid - gs * side], axis=1).astype(np.float32)


def level_bed(seg, amount):
    """Even out a bed's own builds and drops, so a bed never suddenly gets loud (the music is ambience):
    rises over the track's median 2-s level are cut by `amount` of their size, dips lifted by half that (at most 12 dB considered)."""
    m = seg.mean(axis=1)
    h = int(0.1 * SR)
    n = len(m) // h
    if n < 30 or amount <= 0:
        return seg
    e = (m[:n * h].reshape(n, h) ** 2).mean(axis=1) + 1e-12
    d = 10 * np.log10(np.convolve(e, np.ones(20) / 20, "same") + 1e-12)
    live = d > d.max() - 40
    if live.sum() < 10:
        return seg
    dev = d - np.median(d[live])
    g_db = -amount * np.clip(dev, 0, None) + 0.5 * amount * np.clip(-dev, 0, 12) * live
    g_db = np.convolve(g_db, np.ones(10) / 10, "same")
    g = 10 ** (np.interp(np.arange(len(m)), np.arange(n) * h + h / 2, g_db) / 20)
    return (seg * g[:, None]).astype(np.float32)


def tame(x, over_db=4.0, ratio=4.0):
    """The music bus's transients held near its own level, so a bed's drum hits never fight the voice (a drum hit can stand ~10 dB
    over its bed): peaks more than `over_db` over the bed's running 1-s level are compressed `ratio`:1,
    instant attack (5-ms blocks), 120-ms release."""
    m = np.abs(x).max(axis=1)
    h = int(0.005 * SR)
    n = len(m) // h
    pk = m[:n * h].reshape(n, h).max(axis=1) + 1e-9
    ms = (x[:n * h].mean(axis=1).reshape(n, h) ** 2).mean(axis=1)
    ref = np.sqrt(np.convolve(ms, np.ones(200) / 200, "same")) + 1e-9
    gdb = -(1 - 1 / ratio) * 20 * np.log10(np.maximum(pk / (ref * 1.414 * 10 ** (over_db / 20)), 1.0))
    out, g, rel = np.empty(n), 0.0, np.exp(-1 / 24)
    for i in range(n):
        g = min(gdb[i], g * rel)
        out[i] = g
    gain = 10 ** (np.interp(np.arange(len(m)), np.arange(n) * h + h / 2, out) / 20)
    return (x * gain[:, None]).astype(np.float32)


def voice_activity(film, total, voice=None):
    """1 where a word is spoken (words padded 80/150 ms), smoothed to a 30-ms attack and a 250-ms release.
    With the voice itself, also 1 wherever it is speaking (10-ms RMS over -32 dBFS, padded the same), so a stretch the aligner squeezed
    into too few word times (a long number said fast leaves a 1-2 s hole in the word times) still holds the duck under live speech."""
    act = np.zeros(total, np.float32)
    for x in film.W:
        a, b = int((x["start"] - 0.08) * SR), int((x["end"] + 0.15) * SR)
        act[max(0, a):min(total, b)] = 1
    if voice is not None:
        hop = int(0.01 * SR)
        mono = voice[:total].mean(axis=1) if voice.ndim == 2 else voice[:total]
        m = len(mono) // hop
        db = 20 * np.log10(np.sqrt((mono[:m * hop].reshape(m, hop) ** 2).mean(axis=1)) + 1e-9)
        for i in np.nonzero(db > -32.0)[0]:
            act[max(0, i * hop - int(0.08 * SR)):min(total, (i + 1) * hop + int(0.15 * SR))] = 1
    env = np.zeros_like(act)
    up, down = np.exp(-1 / (0.03 * SR)), np.exp(-1 / (0.25 * SR))
    e = 0.0
    step = 480
    for i in range(0, total, step):
        tgt = act[i:i + step].max()
        c = up if tgt > e else down
        e = tgt + (e - tgt) * (c ** step)
        env[i:i + step] = e
    return env


def build(mod):
    film = mod.FILM
    total = int((mod.DURATION) * SR)
    voice = np.zeros((total, 2), np.float32)
    v = load(mod.VOICE)
    voice[:min(total, len(v))] = v[:total]
    if getattr(mod, "VOICE_COMP", None):  # dialogue peaks eased (3:1 over the voice's own level), so the final limiter barely touches a word
        voice = tame(voice, *mod.VOICE_COMP)
    v_l = lufs(voice)
    act = voice_activity(film, total, voice)
    music = np.zeros((total, 2), np.float32)
    xduck = np.zeros(total, np.float32)   # a cue's own extra duck under speech (Cue.duck_extra), dB
    report = []
    handoffs = plan_handoffs(mod)
    xf = getattr(mod, "HANDOFF", 0.1)  # a fading cue runs this far past its end, so a fade never leaves a hole
    for c in mod.CUES:
        src = src_of(c)
        exit_ = getattr(c, "_exit", c.exit)
        entry = getattr(c, "_entry", "free")
        pre = PRE if entry == "beat" else 0.15 if entry == "smooth" else 0.0
        t0, src0 = c.t0 - pre, src - pre
        if exit_ == "smooth":
            end = c.t1 + 0.15
        elif exit_ == "beat":
            end = c.t1 + CUT + FADE
        elif exit_ in ("fade", "pad", "button"):
            end = c.t1 + xf
        else:
            end = c.t1
        n = int((end - t0) * SR)
        seg = load(c.path, src0, end - t0 + 0.05)[:n]
        if len(seg) < n:
            seg = np.vstack([seg, np.zeros((n - len(seg), 2), np.float32)])
        # a cue may carry its own bed levelling (`level`) and an extra duck of its centre under speech (`duck_extra`), so one bed can
        # keep its own mix (e.g. LEVEL_BEDS 0 and DUCK_DB 7) inside a film mixed otherwise (0.6 and 5); getattr, so every other sheet
        # is unchanged
        lv = getattr(c, "level", None)
        seg = level_bed(seg, getattr(mod, "LEVEL_BEDS", 0.0) if lv is None else lv)
        base = (v_l - c.under) - lufs(seg)
        g = np.full(n, base, np.float32)
        if c.auto:  # level moves; an automation that starts at the entry holds from the (moved) entry
            pts = sorted(c.auto)
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            v0 = float(np.interp(t0, xs, ys)) if xs[0] <= t0 else (ys[0] if xs[0] - t0 < 1.0 else c.under)
            pts = [(t0, v0)] + [p for p in pts if p[0] > t0]
            tt = np.arange(n) / SR + t0
            g = base + c.under - np.interp(tt, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)
        lin = 10 ** (g / 20)
        smooth_mode = getattr(mod, "HANDOFF_STYLE", "beat") == "smooth"  # a downbeat entry that isn't a handoff keeps its own fade
        fin = {"beat": max(0.005, c.fin) if smooth_mode else 0.005, "smooth": FIN_S, "card": CARD_FIN}.get(entry, c.fin)
        if fin > 0:  # equal-power in
            m = min(n, max(1, int(fin * SR)))
            lin[:m] *= np.sin(np.linspace(0, np.pi / 2, m))
        if exit_ == "smooth":  # a fade to (just past) the switch point
            m = min(n, int(getattr(c, "_fout", FOUT_S) * SR))
            lin[n - m:] *= np.cos(np.linspace(0, np.pi / 2, m))
        elif exit_ == "beat":  # through the beat, then a 45-ms cut
            m = min(n, int(FADE * SR))
            lin[n - m:] *= np.linspace(1, 0, m)
        elif exit_ in ("fade", "pad", "button"):  # equal-power out, ending `xf` past t1
            fo = getattr(c, "_fout", c.fout)
            m = min(n, int((fo + xf) * SR))
            lin[n - m:] *= np.cos(np.linspace(0, np.pi / 2, m))
        elif exit_ == "stop":
            m = min(n, int(0.06 * SR))
            lin[n - m:] *= np.linspace(1, 0, m)
        seg = seg * lin[:, None]
        dx = getattr(c, "duck_extra", 0.0)
        if dx:  # its extra duck joins the bus duck below (after MUSIC_TAME, which reads the bed's centre), over the cue's own span
            xduck[max(0, int(c.t0 * SR)):max(0, int(c.t1 * SR))] = dx
        i0 = int(round(t0 * SR))
        if i0 < 0:  # a pre-roll before the film's first frame (a cue on a downbeat at 0.0): the part before 0 is dropped
            seg, i0 = seg[-i0:], 0
        k = max(0, min(len(seg), total - i0))
        music[i0:i0 + k] += seg[:k]
        report.append((c, src))
    if getattr(mod, "MONO_SAFE", True):  # where the bed's left and right cancel (it would vanish on a mono speaker), narrow it there
        music = mono_safe(music)
    if getattr(mod, "MUSIC_TAME", None):  # the bed's own spikes (drum hits) held near its level, so it can sit under a voice
        music = tame(music, *mod.MUSIC_TAME)
    # under speech: duck the bed, and carve its voice band further
    duck_db, carve_db = getattr(mod, "DUCK_DB", 6.0), getattr(mod, "CARVE_DB", 4.0)
    sos = butter(2, [900, 4500], btype="bandpass", fs=SR, output="sos")
    side_duck = getattr(mod, "SIDE_DUCK_DB", None)
    if side_duck is None:
        band = sosfiltfilt(sos, music, axis=0).astype(np.float32)
        keep = 1 - (1 - 10 ** (-carve_db / 20)) * act
        music = music - band * (1 - keep)[:, None]
        music *= (10 ** (-(duck_db + xduck) * act / 20))[:, None]
    else:  # the voice sits in the centre: carve and duck the bed's centre (mid), the sides less, so the music wraps around the voice
        mid, side = (music[:, 0] + music[:, 1]) / 2, (music[:, 0] - music[:, 1]) / 2
        band = sosfiltfilt(sos, mid).astype(np.float32)
        mid = mid - band * (1 - 10 ** (-carve_db / 20)) * act
        mid *= 10 ** (-(duck_db + xduck) * act / 20)
        side *= 10 ** (-side_duck * act / 20)
        music = np.stack([mid + side, mid - side], axis=1).astype(np.float32)
    # a new cue never arrives more than LEVEL_JUMP dB over the one before it (so the music never suddenly gets loud at a switch):
    # it starts at that ceiling and settles to its own level over 8 s
    lj, lvl_rep = getattr(mod, "LEVEL_JUMP", None), []
    if lj is not None:
        for aid, bid, H in getattr(mod, "_handoffs", []):
            jump = rms_db(music[int((H + 1.6) * SR):int((H + 4.6) * SR)]) - rms_db(music[int((H - 4.5) * SR):int((H - 1.4) * SR)])
            if jump > lj:
                g = 10 ** (-(jump - lj) / 20)
                a0, a1 = int((H - 0.2) * SR), int((H + 8.0) * SR)
                env = np.ones(total, np.float32)
                env[a0:a1] = np.linspace(g, 1.0, a1 - a0)
                music *= env[:, None]
            lvl_rep.append((aid, bid, H, jump, max(0.0, jump - lj)))
    mod._lvl_rep = lvl_rep
    # under speech the music stays at least GAP_MIN dB under the voice (so the voice never battles the music): 250-ms windows against
    # the voice's running 2-s median, cut fast (0.25 s) and released slowly (1 s)
    gm = getattr(mod, "GAP_MIN", None)
    if gm is not None:
        h = int(0.25 * SR)
        n = total // h
        pw = lambda x: 10 * np.log10((x[:n * h].mean(axis=1).reshape(n, h) ** 2).mean(axis=1) + 1e-12)
        vdb, mdb = pw(voice), pw(music)
        sp = act[:n * h].reshape(n, h).mean(axis=1) > 0.5
        vref = np.array([np.median(vdb[max(0, i - 4):i + 5][sp[max(0, i - 4):i + 5]]) if sp[i] else -120.0 for i in range(n)])
        cut = np.where(sp, np.clip(mdb - (vref - gm), 0, 12), 0.0)
        cut = np.array([cut[max(0, i - 2):i + 3].max() for i in range(n)])        # fast: catch the window and its neighbours
        cut = np.convolve(cut, np.ones(4) / 4, "same")                              # smooth over 1 s
        g = 10 ** (-np.interp(np.arange(total), np.arange(n) * h + h / 2, cut) / 20)
        music *= g[:, None].astype(np.float32)
        mod._gap_rep = (int((cut > 0.5).sum()), float(cut.max()), int(sp.sum()))
    # a chapter card never jumps more than CARD_JUMP dB over the bed before it (a card's music never arrives too suddenly): the card's lift
    # is lowered by the excess, and released over 3 s as the narration comes back
    cap, card_rep = getattr(mod, "CARD_JUMP", 6.0), []
    if cap is not None:
        for c in mod.CUES:
            if not c.hold_in:
                continue
            T = c.t0
            before = rms_db(music[int((T - 2.6) * SR):int((T - 0.7) * SR)])
            jump = rms_db(music[int((T + 0.05) * SR):int((T + 2.6) * SR)]) - before
            if jump > cap and before > -45:  # (after a silence there's no bed to match)
                g = 10 ** (-(jump - cap) / 20)
                a0, a1, a2 = int((T - 0.05) * SR), int((T + 2.7) * SR), int((T + 5.7) * SR)
                env = np.ones(total, np.float32)
                env[a0:a1] = g
                env[a1:a2] = np.linspace(g, 1.0, a2 - a1)
                music *= env[:, None]
            # the report says what was done: after a silence nothing is lowered (a card after the music has ended would otherwise
            # print a jump of ~190 dB "lowered" by ~184 dB, though the bed played at its level)
            card_rep.append((c.id, T, jump, max(0.0, jump - cap) if before > -45 else 0.0))
    mod._card_rep = card_rep
    # effects: by their impact; sub-heavy ones get harmonics for small speakers
    sfx = np.zeros((total, 2), np.float32)
    vpk = np.percentile(np.abs(voice).max(axis=1), 99.9)
    harm_db = getattr(mod, "SFX_HARMONICS_DB", -8.0)
    fxrep, cache = [], {}
    for s in mod.SFX:
        key = (s.path, s.harm)
        if key not in cache:
            a = load(s.path)
            ls = low_share(a)
            if s.harm is not None:
                a = harmonize(a, s.harm)
            elif harm_db is not None and ls > 0.8:
                a = harmonize(a, harm_db)
            cache[key] = (a, effect_sync(a), ls)
        a, auto_sync, ls = cache[key]
        sync = auto_sync if s.sync is None else s.sync
        a = a / (np.abs(a).max() + 1e-9) * vpk * 10 ** (s.db / 20)
        if s.dur is not None:
            k = int((sync + s.dur) * SR)
            a = a[:k].copy()
            f = min(len(a), int(0.15 * SR))
            a[len(a) - f:] *= np.linspace(1, 0, f)[:, None]
        i0 = int(round((s.t - sync) * SR))
        lo, hi = max(0, i0), min(total, i0 + len(a))
        if hi > lo:
            sfx[lo:hi] += a[lo - i0:hi - i0]
        fxrep.append((s, sync, ls))
    keep_pic = getattr(mod, "KEEP_PICTURE_AUDIO", None)  # [(t0, t1)]: stretches where the render's own audio stays
    extra = np.zeros((total, 2), np.float32)
    if keep_pic and getattr(mod, "PICTURE", None):
        pa = load(mod.PICTURE)
        for a0, a1 in keep_pic:
            i0, i1 = int(a0 * SR), min(total, int(a1 * SR), len(pa))
            extra[i0:i1] = pa[i0:i1]
    for kept in getattr(mod, "KEEP_MUSIC", []):  # earlier music kept as is: (path, src, t0, t1, under, fin, fout)
        path, src, t0, t1, under, fin, fout = kept
        n = int((t1 - t0) * SR)
        seg = load(path, src, t1 - t0 + 0.05)[:n]
        gain = 10 ** (((v_l - under) - lufs(seg)) / 20)
        lin = np.full(len(seg), gain, np.float32)
        if fin:
            m = int(fin * SR); lin[:m] *= np.linspace(0, 1, m)
        if fout:
            m = int(fout * SR); lin[-m:] *= np.linspace(1, 0, m)
        seg = seg * lin[:, None] * (10 ** (-5 * act[int(t0 * SR):int(t0 * SR) + len(seg)] / 20))[:, None]
        i0 = int(t0 * SR)
        music[i0:i0 + len(seg)] += seg
    mix = voice + music + sfx + extra
    return mix, voice, music, sfx, act, report, v_l, handoffs, fxrep


FX_LOUD_LU = -7.0   # no effect louder than this, over 1.5 s against the voice (passed mixes sit at -8 LU or quieter; booms at -2 to -4 hurt)


def fx_source(path, note="", of=None, test=False):
    """Where an effect comes from, by the creator's ratings (rating() above): (label, memey). Under the rating lock an unrated sound
    reaches a mix only as a sample for the creator's ear (test=True, --test-sounds)."""
    label, ok, memey = rating(of or path, note)
    if of:
        label = f"a cut of {Path(str(of)).name}: {label}"
    if test and not ok:
        label = f"TEST for the creator's ear: {label}"
    return label, memey


def fx_against_voice(voice, sfx, fxrep):
    """Effects sit under the voice and fit its mood (an effect much louder than everything else, or a memey sound under a serious
    narration, breaks the film): each effect's loudness over 1.5 s from its impact
    (K-weighted, the effects track there, so neighbours within 1.5 s count too) against the voice's integrated loudness, and its source.
    A real voice playing its own clip (a note with "own voice" or "own sound") is not an effect and isn't judged."""
    v_l = lufs(voice)
    k = kweight(sfx)
    n = int(1.5 * SR)
    loud, memey = [], []
    print(f"effects against the voice (1.5 s from the impact, LU over the voice's {v_l:.1f} LUFS; passed mixes sit at -8 or quieter, over "
          f"{FX_LOUD_LU:+.0f} hurts) and where each comes from:")
    for s, sync, ls in sorted(fxrep, key=lambda r: r[0].t):
        own = any(w in s.note.lower() for w in ("own voice", "own sound"))
        i = max(0, int(s.t * SR))
        seg = k[i:i + n]
        lu = (-0.691 + 10 * np.log10((seg ** 2).mean(axis=0).sum() + 1e-12) - v_l) if len(seg) else -70.0
        src, is_meme = fx_source(s.path, s.note, getattr(s, "of", None), getattr(s, "test", False))
        flags = []
        if lu > FX_LOUD_LU and not own:
            flags.append("LOUD")
            loud.append(round(s.t, 2))
        if is_meme and "joke" not in s.note.lower():
            flags.append("MEMEY outside a joke")
            memey.append(round(s.t, 2))
        print(f"  {s.t:8.2f} {Path(s.path).stem[:22]:22s} {lu:+6.1f} LU  {src}" + (f"  <- {', '.join(flags)}" if flags else ""))
    print(f"effects louder than {FX_LOUD_LU:+.0f} LU against the voice: {loud or 'none'}; memey effects outside a joke: {memey or 'none'}")


def checks(mod, mix, voice, music, sfx, act, report, handoffs, fxrep):
    print("\nhandoffs (old time -> on the outgoing track's beat):")
    for a, b, T, H, d, kind, entry in handoffs:
        print(f"  {a:5s}-> {b:5s} {T:8.2f} -> {H:8.2f} ({d:+.2f} s)  {kind:12s} entry: {entry}")
    print("\nchapter cards (the music's jump over the bed before; lowered by):")
    for cid, T, j, r in getattr(mod, "_card_rep", []):
        print(f"  {cid:5s} {T:8.2f}  jump {j:+5.1f} dB  lowered {r:4.1f} dB")
    if getattr(mod, "_gap_rep", None):
        k, mx, nsp = mod._gap_rep
        print(f"speech gap held at GAP_MIN: music lowered in {k} of {nsp} speech windows (250 ms), at most {mx:.1f} dB")
    print("level at each switch (the new cue over the old, 3 s each side; lowered at the switch by):")
    for aid, bid, H, j, r in getattr(mod, "_lvl_rep", []):
        print(f"  {aid:5s}-> {bid:5s} {H:8.2f}  {j:+5.1f} dB  lowered {r:4.1f} dB")
    print("\nmusic cues:")
    for c, src in report:
        i0, i1 = int(c.t0 * SR), int(c.t1 * SR)
        sp = act[i0:i1] > 0.5
        vm = None
        if sp.sum() > SR:
            vm = rms_db(voice[i0:i1][sp]) - rms_db(music[i0:i1][sp])
        print(f"  {c.id:5s} {c.t0:8.2f}-{c.t1:8.2f}  {Path(c.path).stem[:34]:34s} from {src:7.2f}  under {c.under:4.1f}  "
              f"voice-music {('%5.1f' % vm) if vm is not None else '  -  '} dB  {getattr(c, '_exit', c.exit)}")
    cues = sorted(report, key=lambda r: r[0].t0)
    def end(c):
        e = getattr(c, "_exit", c.exit)
        return c.t1 + (0.15 if e == "smooth" else CUT + FADE if e == "beat" else getattr(mod, "HANDOFF", 0.1) if e in ("fade", "pad", "button") else 0)
    def start(c):
        e = getattr(c, "_entry", "free")
        return c.t0 - (PRE if e == "beat" else 0.15 if e == "smooth" else 0)
    bad = [(a[0].id, b[0].id, round(end(a[0]) - start(b[0]), 3)) for a, b in zip(cues, cues[1:]) if end(a[0]) - start(b[0]) > 0.31
           and getattr(a[0], "_exit", a[0].exit) != "pad"]
    print("overlaps > 0.3 s (a smooth switch touches for 0.3 s at low level; pads excepted):", bad or "none")
    hop = int(0.05 * SR)
    m = np.abs(mix).max(axis=1)
    n = len(m) // hop
    quiet = (m[:n * hop].reshape(n, hop).max(axis=1) < 10 ** (-50 / 20))
    designed = list(getattr(mod, "SILENCES", [])) + list(getattr(mod, "_stopdowns", []))
    sil, run = [], None
    for i, q in enumerate(quiet):
        if q and run is None:
            run = i
        if not q and run is not None:
            sil.append((run * 0.05, i * 0.05)); run = None
    flagged = [s for s in sil if not any(a - 0.05 <= s[0] and s[1] <= b + 0.05 for a, b in designed)]
    print(f"silences (50 ms under -50 dBFS): {len(sil)}, outside the designed ones: {[(round(a, 2), round(b, 2)) for a, b in flagged][:20]}")
    print(f"effects: {len(mod.SFX)} ({len(mod.SFX) / (len(mix) / SR / 60):.1f} a minute)")
    # one sound per moment: a low hit a code bed plays on a word (tools/music) never shares its moment with an effect
    both = [(c.id, k, t, Path(s.path).stem, s.t) for c, _ in report for k, t in getattr(c, "hits", {}).items()
            for s in mod.SFX if abs(s.t - t) < 0.3]
    print("bed hits on an effect's moment (keep one of the two):", [(a, k, round(t, 2), f, round(st, 2)) for a, k, t, f, st in both]
          or "none")
    hp = butter(4, 400, "highpass", fs=SR, output="sos")
    rest = (mix - sfx).mean(axis=1)
    print("effects, impact and small speakers (the effect's level above 400 Hz minus the rest of the mix's, 200 ms from the impact):")
    for s, sync, ls in sorted(fxrep, key=lambda r: r[0].t):
        i = int(s.t * SR)
        e = sosfiltfilt(hp, sfx[i:i + SR // 5].mean(axis=1)) if i + SR // 5 < len(sfx) else np.zeros(1)
        r = sosfiltfilt(hp, rest[i:i + SR // 5]) if i + SR // 5 < len(rest) else np.zeros(1)
        print(f"  {s.t:8.2f} {Path(s.path).stem:13s} impact {sync:5.3f} s in the file  sub {ls:4.0%}  400Hz+ vs rest {rms_db(e) - rms_db(r):+6.1f} dB"
              f"  {s.note}")
    fx_against_voice(voice, sfx, fxrep)
    L, R = mix[:, 0], mix[:, 1]
    cs = []
    for k in range(len(L) // SR):
        l, r = L[k * SR:(k + 1) * SR], R[k * SR:(k + 1) * SR]
        if rms_db(l) > -60 and np.std(l) > 0 and np.std(r) > 0:
            cs.append((k, float(np.corrcoef(l, r)[0, 1])))
    neg = [k for k, v in cs if v < 0]
    print(f"mono: L/R correlation per second, median {np.median([v for _, v in cs]):.2f}; seconds under 0: {neg[:20]}")


def main():
    spec = importlib.util.spec_from_file_location("cues", sys.argv[1])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = sys.argv[2]
    # the rating lock at the mix as well (whatever the sheet did on import): every effect is one the creator rated, or a sample for the
    # creator's ear (test=True) in a mix made as a sample (--test-sounds); the pipeline's score step never passes it, so a test sound
    # can't reach a delivery
    bad = [s for s in mod.SFX if not rating(getattr(s, "of", None) or s.path, s.note)[1] and not getattr(s, "test", False)]
    if bad:
        raise SystemExit("sounds the creator never rated: " + "; ".join(f"{Path(str(s.path)).name} at {s.t:.2f} ({s.note[:50]})"
                                                                     for s in bad[:12])
                         + ". The rated sound for the job (pal(name), a pack Keep, a Sound Test fit), or a sample for the creator first "
                           "(test=True).")
    tests = [s for s in mod.SFX if getattr(s, "test", False)]
    if tests and "--test-sounds" not in sys.argv:
        raise SystemExit(f"{len(tests)} test sound(s) in the sheet ({', '.join(Path(str(s.path)).name for s in tests[:6])}): a mix with "
                         "them is a sample for the creator's ear, made with --test-sounds; a delivery has none")
    if tests:
        print("TEST SOUNDS, a sample for the creator's ear (never a delivery): " + "; ".join(f"{s.t:.2f} {Path(str(s.path)).name} ({s.note[:40]})"
                                                                            for s in tests))
    mix, voice, music, sfx, act, report, v_l, handoffs, fxrep = build(mod)
    checks(mod, mix, voice, music, sfx, act, report, handoffs, fxrep)
    if "--stems" in sys.argv:  # the music and effects alone, for checking transitions without the voice
        d = Path(sys.argv[sys.argv.index("--stems") + 1])
        d.mkdir(parents=True, exist_ok=True)
        for name, a in (("music", music), ("sfx", sfx)):
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                            str(d / f"{name}.wav")], input=a.astype(np.float32).tobytes(), check=True)
        (d / "cues.json").write_text(json.dumps([{"id": c.id, "t0": c.t0, "t1": c.t1, "src": src, "path": c.path,
                                                  "exit": getattr(c, "_exit", c.exit), "entry": getattr(c, "_entry", "free")}
                                                 for c, src in report]), encoding="utf-8")
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "mix.wav"
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-", str(raw)],
                       input=mix.astype(np.float32).tobytes(), check=True)
        target = float(getattr(mod, "MIX_LUFS", -14.0))  # a sheet may set its own (e.g. -16: the voice at -16 without the crunch)
        gdb = target - lufs(mix)
        ceil = float(getattr(mod, "MIX_CEIL", -2.0))  # e.g. -1.2: a safety net over the voice chain's -1.5 limiter, not a second limiter on it
        chain = (f"volume={gdb:.2f}dB,aresample={SR * 4},alimiter=limit={10 ** (ceil / 20):.4f}:attack=0.5:release=60:"
                 f"level=disabled:latency=1,aresample={SR}")
        if out.lower().endswith(".wav"):
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw), "-af", chain, "-c:a", "pcm_f32le", out], check=True)
        else:
            pic = sys.argv[sys.argv.index("--picture") + 1]
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", pic, "-i", str(raw), "-map", "0:v", "-map", "1:a",
                            "-af", chain, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)
    print(f"voice {v_l:.1f} LUFS; mix -> {getattr(mod, 'MIX_LUFS', -14.0)} LUFS: {out}")


if __name__ == "__main__":
    main()
