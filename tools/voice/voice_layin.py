"""The lay-in: a fix to a locked voice laid into the old slot without moving time (standard/VOICE_LOCK.md stage 3; proven by laying a
re-voiced name into a rendered film with every anchor within 30 ms).

For one beat (or a piece of it, --from/--to), from takes already voiced the lines-before way (span_takes.py ... <beat> <beat> k0 k1:
the two script lines before the span voiced inside the same request, then cut away; build/voice/patch/<beat>_<k>.wav + .align.json):
  1. the old piece measured from the AUDIO: its words forced onto the narration by the CTC aligner (ctcalign.py), each edge snapped to
     the sound (onset: the dip before the word, then the first 10 ms 8 dB over it; end: the first 16 ms under -48 dB after the last
     frame over -30 dB); the slot = its first sound to the next sound after it;
  2. each take at the house tempo (1.04x, [tts] tempo, atempo as dj tts) and through chain D, the house narration chain
     (tools/sound/voice_level.py --chain mb --lufs -14 --ceil -1.5), its words forced onto it the same way (never ElevenLabs' times:
     they can run up to 0.5 s late), the piece cut from its first sound to its last, every pause inside a sentence cut to 0.12 s
     except the pauses that land an anchor;
  3. the anchors: every phrase the picture or the cue sheet hangs on inside the piece (w('S12', 'first heard'), at(t, 'S12',
     'October'), F.w("S12", ...) in tools/motion/src/<src>/*.tsx and the video's score/cues*.py) plus --anchor; the pause before each
     anchor is set so the anchor's first sound lands where it was; every anchor must land within 2 frames (fps from video.toml);
  4. each take measured clean or not: the accent guard (accent_take.py: a hard or maybe accent rejects), the name check (saycheck.py
     for every name with "ipa" in names.json: anything but AMERICAN rejects), the words (Whisper, asr_words.py, and the CTC letters,
     both against the script: a missing or extra word rejects); the pick = the clean take that fits the slot with the least anchor
     drift;
  5. --apply (refused if script.md changed while it ran): the narration rewritten in place (the old piece silenced, the new one at the
     old piece's loudness, 5-ms fades), a backup in build/voice/layin/<stamp>_<beat>/; the word files refreshed (sync_words.py:
     byte-identical, the time is kept) and the inserted copy rebuilt (--inserts, or video.toml [voice] inserts = "<script>"; then
     checked to hold the new piece); voice_lock.json re-stamped with the lay-in on record; the sound gate on the changed span only
     (A2 A3 A4 A7 A8 A10 A11).
Without --apply (the default) nothing is written but the previews: build/voice/layin/<beat>/preview_<k>.wav (3 s around, the new piece
laid in) and preview_old.wav.

--reworded (the beat's WORDS changed in script.md after the lock, e.g. a sentence cut from it): the whole beat's new words (the take,
voiced the lines-before way on the new script) go into the old slot from its first sound; the pauses inside the piece are the house's
(0.25 s after a sentence's end, 0.12 s inside one), and a pause set to land an anchor stays within them. An anchor the new words
still say keeps its time where the take allows (2 frames), else it is ANCHOR OFF; an anchor the new words no longer say is GONE.
Either one moves only with --skip-anchor (on record: the picture's owner re-anchors it; the picture's w()/at() read the new word
times, a GONE phrase has none). A take longer than the slot doesn't fit (time would move); a shorter one leaves a longer pause after
it: --apply prints the cut_pause.py call that closes it (the voice unlocked for it: time moves from there on, the shift on record).
--apply also writes the beat's new text into build/beats.json and its words, cues and chunks into build/captions/words.json, the
words forced onto the narration as laid (measure_words: ctcalign, then dj captions' refine_onsets, so a start moves to its sound only
after a pause; no Whisper pass), grouped by dj captions' own group(), the srt files and the narration's signature, then
sync_words.py. Of the clean takes that fit and land, the one with the lowest accent score (autopick's pick rule).

  EDIT tools/voice/voice_layin.py <video> <beat> <k> [<k> ...]
      [--from WORD --to WORD] [--anchor "phrase" ...] [--narration F] [--takes-dir D] [--inserts SCRIPT] [--no-checks] [--apply]
      [--reworded] [--skip-anchor "phrase" ...]"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import FFMPEG, MOTION, PY_EDIT, PY_PIPE, REPO, TOOLS  # noqa: E402
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sound"))
import ctcalign as C  # noqa: E402
import gatelib as G  # noqa: E402
import voice_lock as VL  # noqa: E402

ED = str(PY_EDIT)
GT = str(PY_PIPE)
VLEVEL = TOOLS / "sound" / "voice_level.py"
INNER = 0.12          # a pause inside a sentence
SENT = 0.25           # the pause between sentences (--reworded: a reworded beat's own sentence ends)
MAX_SET = 0.30        # s: the longest pause the lay-in may set to land an anchor
MIN_GAP_AFTER = 0.06  # s of silence kept before the next sound
SENT_END = re.compile(r"[.?!…][\"')\]”’]*$")


def house_cfg():
    """the dj config as the voice used it: config/tts.toml, else the example the setup copies it from"""
    import tomllib
    p = REPO / "config" / "tts.toml"
    p = p if p.exists() else REPO / "config" / "tts.example.toml"
    return tomllib.loads(p.read_text(encoding="utf-8"))


WIN_S = 15.0          # s of the narration read either side of the beat's words (the old piece, the next sound, the 6-s in-place window)


class WinArray:
    """A window of a long narration (mono, float64) indexed with the WHOLE file's sample numbers: x[a:b] for a, b inside the window;
    len(x) is where the window ends (the measures read "to the end" as far as the window). The lay-in's measures read only around
    their beat (a whole long narration as float64, three copies, runs to gigabytes)."""

    def __init__(self, path, t0, t1):
        info = sf.info(str(path))
        self.sr, self.n = info.samplerate, info.frames
        self.w0 = max(0, int(t0 * self.sr))
        self.w1 = min(self.n, int(t1 * self.sr))
        y, _ = sf.read(str(path), start=self.w0, stop=self.w1, dtype="float64", always_2d=True)
        self.win = y.mean(1)

    def __len__(self):
        return self.w1

    def __getitem__(self, s):
        if not isinstance(s, slice) or s.step not in (None, 1):
            raise TypeError("WinArray takes plain slices")
        a = 0 if s.start is None else (s.start if s.start >= 0 else self.w1 + s.start)
        b = self.w1 if s.stop is None else (s.stop if s.stop >= 0 else self.w1 + s.stop)
        a, b = max(a, 0), min(b, self.w1)
        if a < self.w0 or b > self.w1:
            raise IndexError(f"{a / self.sr:.2f}-{b / self.sr:.2f} s is outside the window read "
                             f"({self.w0 / self.sr:.2f}-{self.w1 / self.sr:.2f} s): raise WIN_S")
        return self.win[a - self.w0:b - self.w0]


# ---------------------------------------------------------------- measuring the sound (proven on re-voiced names in a rendered film)

def db_frames(x, sr, hop=0.002, win=0.004):
    h, w = int(hop * sr), int(win * sr)
    n = max(0, (len(x) - w) // h)
    if n == 0:
        return np.zeros(0), hop
    idx = np.arange(n)[:, None] * h + np.arange(w)[None, :]
    e = np.sqrt((x[idx] ** 2).mean(1))
    return 20 * np.log10(e + 1e-9), hop


def onset(x, sr, t_guess, back=0.22, fwd=0.06):
    """the first sound of a word whose alignment says t_guess: the quietest point before the guess (a pause, a closure, or the dip
    between two words said in one breath), then the first frame 8 dB over that dip (and over -50 dB) that stays there for 10 ms"""
    a = max(0, int((t_guess - back) * sr))
    d, hop = db_frames(x[a:int((t_guess + fwd) * sr)], sr, hop=0.002, win=0.010)
    g = min(len(d), int((back + 0.02) / hop))
    if not g:
        return t_guess
    m = int(np.argmin(d[:g]))
    thr = max(d[m] + 8, -50)
    run = int(0.010 / hop)
    i = next((k for k in range(m, len(d) - run) if (d[k:k + run] > thr).all()), m)
    return a / sr + i * hop


def offset_end(x, sr, w_start, next_start=None):
    """the end of a word (its aligned start w_start; the next word's aligned start, if the audio goes on): after the word's last frame
    over -30 dB, the first 16-ms run under -48 dB; with no such run before the next word, the quietest frame between them"""
    dur = len(x) / sr
    lim = dur if next_start is None else min(dur, onset(x, sr, next_start))
    a, b = int(max(0, w_start - 0.05) * sr), int(lim * sr)
    d, hop = db_frames(x[a:b], sr)
    loud = np.where(d > -30)[0]
    if not len(loud):
        return w_start + 0.2
    i0 = loud[-1] + 1
    need = int(0.016 / hop)
    for i in range(i0, len(d) - need + 1):
        if (d[i:i + need] < -48).all():
            return a / sr + i * hop + 0.004
    i = i0 + int(np.argmin(d[i0:])) if i0 < len(d) else len(d) - 1
    return a / sr + i * hop


def next_sound(x, sr, t, limit):
    d, hop = db_frames(x[int(t * sr):int(limit * sr)], sr)
    j = next((k for k in range(len(d)) if d[k] > -45), len(d) - 1)
    return t + max(0, j) * hop


def ramp_start(x, sr, t_next, t_floor):
    """the next sound's first sample: from where it passes -45 dB (next_sound) back over its rising onset in 1-ms steps to the first
    1 ms at -70 dB or under (the pause's silence), never before t_floor; the old slot is silenced only up to there (silencing up to
    t_next cut the first 1-2 ms of the next word's onset, -64 to -43 dB)"""
    h = max(1, int(0.001 * sr))
    i0 = int(t_next * sr)
    i, lo = i0, max(int(t_floor * sr), i0 - 20 * h)     # an onset ramp is a few ms; a pause that never falls to -70 dB keeps the old way
    while i - h >= lo and 20 * np.log10(np.sqrt(np.mean(x[i - h:i] ** 2)) + 1e-12) > -70:
        i -= h
    return i / sr if i - h >= lo or i == i0 else t_next


# ---------------------------------------------------------------- words

def key(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'").replace("'s", ""))


def names_table():
    return json.loads((TOOLS / "sound" / "names.json").read_text(encoding="utf-8")).get("names", {})


def script_text(P, beat):
    return dict(G.script_beats(P["script"]))[beat]


def map_said(script_toks, said_toks):
    """script token index -> said token index (the take spells the names table's respellings: 'Sersha Nwin' for 'Saoirse Nguyen')"""
    T = names_table()
    resp = {}
    for name, e in T.items():
        if isinstance(e, dict) and e.get("say") and e["say"] != "as is":
            resp[key(e["say"].replace(" ", ""))] = key(name.replace(" ", ""))
    a = [key(t) for t in script_toks]
    b = [key(t) for t in said_toks]
    out = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                out[i1 + k] = j1 + k
        elif op == "replace":       # a respelling of another length: spread the block
            for k in range(i2 - i1):
                out[i1 + k] = j1 + min(j2 - j1 - 1, int(k * (j2 - j1) / (i2 - i1)))
    return out


def anchors_in(P, beat):
    """the phrases the picture and the cue sheet hang on in this beat"""
    src = (P["cfg"].get("video") or {}).get("src")
    sys.path.append(str(MOTION))
    from codefiles import code_files   # with the subfolder files the film imports (a fix kept in src/<src>/fix1/)
    files = code_files(MOTION / "src" / src, (".ts", ".tsx")) if src else []
    files += list((P["video_dir"] / "score").glob("cues*.py"))
    pat = re.compile(r"""['"](S\d+[a-z]?)['"]\s*,\s*['"]([^'"]+)['"]""")
    out = []
    for f in files:
        try:
            for m in pat.finditer(f.read_text(encoding="utf-8", errors="replace")):
                if m[1] == beat and m[2] not in out:
                    out.append(m[2])
        except OSError:
            pass
    return out


def find_seq(keys, phrase_keys, start=0):
    for i in range(start, len(keys) - len(phrase_keys) + 1):
        if keys[i:i + len(phrase_keys)] == phrase_keys:
            return i
    return None


# ---------------------------------------------------------------- the old piece

def old_piece(x, sr, W, beat, frm, to):
    bw = [i for i, w in enumerate(W) if w["beat"] == beat]
    if not bw:
        raise SystemExit(f"{beat}: no words in the edit's words.json")
    keys = [key(W[i]["w"]) for i in bw]
    gi = bw[0] if not frm else bw[keys.index(key(frm))]
    gj = bw[-1] if not to else next(i for i in bw if i >= gi and key(W[i]["w"]) == key(to))
    lo, hi = max(0, gi - 1), min(len(W) - 1, gj + 1)
    a = max(0.0, W[lo]["start"] - 0.3)
    b = min(len(x) / sr, W[hi]["end"] + 0.4)
    al = C.align(x[int(a * sr):int(b * sr)], sr, " ".join(W[k]["w"] for k in range(lo, hi + 1)))
    if len(al) != hi - lo + 1:
        raise SystemExit(f"the aligner placed {len(al)} of {hi - lo + 1} words around {beat}")
    ctc = {lo + k: (a + w["start"], a + w["end"]) for k, w in enumerate(al)}
    on = {k: onset(x, sr, ctc[k][0]) for k in range(gi, gj + 1)}
    t_on = on[gi]
    t_off = offset_end(x, sr, ctc[gj][0], ctc[gj + 1][0] if gj + 1 in ctc and gj + 1 <= hi and gj < hi else None)
    nxt = ctc[gj + 1][0] + 0.15 if gj + 1 in ctc and gj < hi else len(x) / sr
    t_next = next_sound(x, sr, t_off, nxt) if t_off < nxt else t_off
    return {"gi": gi, "gj": gj, "t_on": t_on, "t_off": t_off, "t_next": t_next, "t_zero": ramp_start(x, sr, t_next, t_off),
            "on": on, "ctc": ctc, "words": [W[k]["w"] for k in range(gi, gj + 1)]}


# ---------------------------------------------------------------- a take

def take_audio(src, out_dir, tempo, k, beat):
    out_dir.mkdir(parents=True, exist_ok=True)
    t, d = out_dir / f"{beat}_{k}_T.wav", out_dir / f"{beat}_{k}_D.wav"
    if not d.exists() or d.stat().st_mtime < src.stat().st_mtime:
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-af", f"atempo={tempo}", "-ar", "48000", "-ac", "1",
                        "-c:a", "pcm_s16le", str(t)], check=True)
        subprocess.run([ED, str(VLEVEL), str(t), str(d), "--chain", "mb", "--lufs", "-14", "--ceil", "-1.5"], check=True,
                       capture_output=True)
    x, sr = sf.read(d, dtype="float64", always_2d=True)
    return x.mean(1), sr, d


def take_piece(x, sr, said_text, script_toks, piece_keys):
    """the take's words forced onto it; the piece from its first word's sound to its last's -> (piece, words rel. to its start)"""
    said_toks = said_text.split()
    al = C.align(x, sr, said_text)
    if len(al) != len(said_toks):
        raise ValueError(f"aligned {len(al)} of {len(said_toks)} words")
    m = map_said(script_toks, said_toks)
    skeys = [key(t) for t in script_toks]
    i0 = find_seq(skeys, piece_keys)
    if i0 is None:
        raise ValueError("the piece's words are not in the take")
    i1 = i0 + len(piece_keys) - 1
    s0, s1 = m[i0], m[i1]
    t0 = onset(x, sr, al[s0]["start"])
    t1 = offset_end(x, sr, al[s1]["start"], al[s1 + 1]["start"] if s1 + 1 < len(al) else None)
    words = []
    for k in range(i0, i1 + 1):
        j = m[k]
        words.append({"w": script_toks[k], "start": al[j]["start"] - t0, "end": al[j]["end"] - t0})
    take_words = [{"w": w["w"], "start": w["start"], "end": w["end"], "beat": "take"} for w in al]
    return x[int(t0 * sr):int(t1 * sr)].copy(), words, take_words


def pauses(piece, sr, words):
    """the pauses inside the piece: [s, e, word before, word after] (runs under -50 dB of 60 ms+, or a breath: a word gap of 100 ms+
    with nothing over -30 dB)"""
    d, hop = db_frames(piece, sr)
    cuts = []
    # `wi` is the word index: the closure block below reuses `i` and `j` as frame indices (a cut appended with a frame number as its
    # word index raises IndexError in --reworded and, in a plain lay-in, shifts the word times from the wrong word on)
    for wi, (a_, b_) in enumerate(zip(words, words[1:])):
        g0, g1 = a_["end"], b_["start"]
        if g1 - g0 < 0.04:
            continue
        lo, hi = int(max(0, g0 - 0.03) / hop), int(min(len(d) * hop, g1 + 0.03) / hop)
        seg = d[lo:hi]
        if not len(seg):
            continue
        q = seg < -50
        if q.sum() * hop < 0.06 and not (g1 - g0 >= 0.10 and seg.max() < -30):
            continue
        qi = np.where(q)[0]
        s_ = (lo + qi[0]) * hop if len(qi) else g0
        e_ = (lo + qi[-1] + 1) * hop if len(qi) else g1
        # a word-final stop keeps its release (cut, the word sounds very slightly cut off at its end): the /t/'s closure is a short
        # quiet run at the word's end and its burst a short sound after it; a cut from the first quiet frame takes the burst with the
        # pause. A closure-short first run (<= 120 ms, starting at the word's end) followed by a short sound (<= 80 ms, over -45 dB)
        # moves the cut's start after that sound. A breath (longer, quieter) still goes.
        if len(qi):
            cl, i, j = seg < -45, qi[0], qi[0]          # the closure: the first near-silent run of 20 ms+ (a -50 blip inside it stays in)
            while i < len(seg):
                if not cl[i]:
                    i += 1
                    continue
                j = i
                while j < len(seg) and cl[j]:
                    j += 1
                if (j - i) * hop >= 0.02:
                    break
                i = j
            if i < len(seg) and (lo + i) * hop <= g0 + 0.06 and (j - i) * hop <= 0.12 and j < len(seg):
                b0 = b1 = j
                while b1 is not None:
                    while b1 < len(seg) and seg[b1] > -50:     # a burst: until it is back under the quiet line
                        b1 += 1
                    if (b1 - b0) * hop > 0.08 or b1 >= len(seg):
                        b1 = None                              # a breath or the next word, not a release
                        break
                    nxt = np.where(seg[b1:b1 + int(0.06 / hop)] >= -45)[0]   # an aspirated /t/ releases twice (~45 ms apart)
                    if not len(nxt) or (b1 + nxt[0] - i) * hop > 0.16:
                        break
                    b0 = b1 = b1 + nxt[0]
                if b1 is not None and q[b1:].sum() * hop >= 0.06:
                    s_ = (lo + b1) * hop
        if seg.max() < -30 and g1 - g0 >= 0.10:
            s_, e_ = max(s_, g0), min(e_, g1) if e_ > g0 else g1
        if e_ - s_ > 0.03:
            cuts.append([s_, e_, wi, wi + 1])
    return cuts


def house_pause(words):
    """--reworded: a pause's house length by the word before it (index ia): SENT after a sentence's end, INNER inside one"""
    return lambda ia: SENT if SENT_END.search(words[ia]["w"]) else INNER


def assemble(piece, sr, words, cuts, setlen, default=None):
    """the piece with each pause cut to INNER (--reworded: default(ia), the house's) or setlen[word index after it]; word times moved
    with the cuts"""
    dflt = default or (lambda ia: INNER)
    out, pos, nw = [], 0.0, [dict(w) for w in words]
    for s_, e_, ia, ib in cuts:
        keep = setlen.get(ib, min(dflt(ia), e_ - s_))
        out.append(piece[int(pos * sr):int(s_ * sr)])
        out.append(np.zeros(int(round(keep * sr))))
        removed = (e_ - s_) - keep
        for w in nw[ib:]:
            w["start"] -= removed
            w["end"] -= removed
        pos = e_
    out.append(piece[int(pos * sr):])
    y = np.concatenate(out)
    f = int(0.005 * sr)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y, nw


def place(piece, sr, words, cuts, old_rel, anchors, reworded=False, tol=2.0 / 60):
    """set the pause before each anchor (left to right) so its first sound lands at old_rel[i] -> (y, words, drift {i: s}, sets).
    Each word's first sound is measured once, in the take as voiced (its own pauses around it, so the dip before it is clean); the
    cuts only move it by what they remove, so where it lands is arithmetic, not a second measurement (re-measured on the cut piece, a
    pause cut to 0 moves the dip the search starts from: a word came out 54 ms off its set). --reworded: every pause the house's
    (house_pause), and one set to land an anchor stays within it (a sentence's end INNER..SENT, inside one 0..INNER): no pause over the
    house's; an anchor the house's pauses can't land (within tol) leaves its pause as it was (an anchor the new words moved by 1.3 s
    would take its comma pause to 0 for nothing) and is ANCHOR OFF."""
    on = [onset(piece, sr, w["start"]) for w in words]
    setlen = {}
    dflt = house_pause(words) if reworded else (lambda ia: INNER)

    def removed_before(i):
        return sum((e_ - s_) - setlen.get(ib, min(dflt(ia), e_ - s_)) for s_, e_, ia, ib in cuts if ib <= i)

    for i in anchors:
        c = next((c for c in cuts if c[3] == i), None)
        if c is None:
            continue
        setlen[i] = 0.0
        land0 = on[i] - removed_before(i)            # with this pause at 0
        need = old_rel[i] - land0
        if not reworded:
            setlen[i] = float(np.clip(need, 0.0, MAX_SET))
            continue
        lo, hi = (INNER, SENT) if dflt(c[2]) == SENT else (0.0, INNER)
        if lo - tol <= need <= hi + tol:
            setlen[i] = float(np.clip(need, lo, hi))
        else:
            del setlen[i]          # out of the house's reach: the pause stays the house's, the anchor moves (ANCHOR OFF)
    y, nw = assemble(piece, sr, words, cuts, setlen, dflt)
    drift = {i: (on[i] - removed_before(i)) - old_rel[i] for i in anchors}
    return y, nw, drift, setlen


# ---------------------------------------------------------------- the checks of a take

def check_take(P, y, sr, words, text, work, k, take=None):
    """-> {"accent": ..., "names": [...], "words": [...], "clean": bool, "why": [...]}. The accent is judged on the whole take (the
    request: an accent lives in the whole request, and the guard's 2-s windows need more than a short piece), the names and the
    words on the piece that goes in."""
    import saycheck
    why, res = [], {}
    wav = work / f"piece_{k}.wav"
    sf.write(wav, np.clip(y, -1, 1), sr, subtype="PCM_16")
    # names
    T = names_table()
    res["names"] = []
    keys = [key(w["w"]) for w in words]
    for name, e in T.items():
        if not (isinstance(e, dict) and "ipa" in e):
            continue
        nk = [key(t) for t in name.split()]
        i = find_seq(keys, nk)
        while i is not None:
            # an all-capitals name (an abbreviation said as letters: LA) is that name only where the script writes it in capitals:
            # a Spanish "La" (said "la") would otherwise be judged as L.A. and reject every take
            if name.replace(".", "").replace("-", "").isupper() and not all(
                    re.sub(r"[^A-Za-z]", "", words[i + q]["w"]).isupper() for q in range(len(nk))):
                i = find_seq(keys, nk, i + 1)
                continue
            r = saycheck.judge(y, sr, words[i]["start"], words[i + len(nk) - 1]["end"], e["ipa"])
            res["names"].append({"name": name, **r})
            if r["verdict"] != "AMERICAN":
                why.append(f"{name} {r['verdict']} ({r['margin']:+.3f}, heard {r['heard']!r})")
            i = find_seq(keys, nk, i + 1)
    # words: the CTC letters and Whisper, each against the script
    chars = C.greedy(y, sr)
    ref = [w for _, ws in C.words_of(text) for w in ws]
    hyp = C.greedy_text(chars).split()
    res["ctc_heard"] = " ".join(hyp)
    missing_ctc = miss(ref, hyp)
    wj = work / f"piece_{k}.asr.json"
    r = subprocess.run([GT, str(HERE / "asr_words.py"), str(wav), "--json", str(wj)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode == 0 and wj.exists():
        wt = json.loads(wj.read_text(encoding="utf-8"))[str(wav)]["text"]
        res["whisper_heard"] = wt
        hyp_w = [w for _, ws in C.words_of(wt) for w in ws]
        missing_w = miss(ref, hyp_w)
    else:
        res["whisper_heard"] = None
        missing_w = []
        why.append("Whisper could not run")
    both = [m for m in missing_ctc if m in missing_w]
    res["missing"] = {"ctc": missing_ctc, "whisper": missing_w}
    if both:
        why.append(f"words missing (both ears): {' '.join(both)}")
    # (a take-level rule for short words swapped, "be" -> "do", was tried and measured: over 23 sections small.en flagged 4 takes and 3
    # were its own mishearings ("a hundred" -> "one hundred", "baked a" -> "bake the"), while medium.en on the take alone heard the real
    # misread right. The words are judged where the gate judges them instead: the chain's A5 right after its first captions pass, on the
    # laid narration in context (tools/sound/voice_chain.sh), stopping before the long passes)
    extra = extra_words(ref, hyp)
    if extra:
        res["extra"] = extra
        why.append(f"extra speech: {' '.join(extra)}")
    # accent: the whole take when there is one
    wjs = work / f"take_{k}.words.json"
    awav, aw = (take if take else (wav, [{"w": w["w"], "start": w["start"], "end": w["end"], "beat": "take"} for w in words]))
    wjs.write_text(json.dumps(aw), encoding="utf-8")
    r = subprocess.run([GT, str(HERE / "accent_take.py"), str(awav), "--words", str(wjs)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    try:
        acc = json.loads(r.stdout[r.stdout.index("{"):])
        res["accent"] = {"hard": acc["hard"], "soft": acc["soft"], "score": acc["accent_by_beat"].get("take")}
        if acc["hard"] or acc["soft"]:
            why.append("accent: " + "; ".join(f["msg"] for f in acc["hard"] + acc["soft"]))
    except (ValueError, KeyError):
        res["accent"] = None
        why.append("the accent guard could not run: " + (r.stderr or r.stdout)[-300:])
    res["why"], res["clean"] = why, not why
    return res


def miss(ref, hyp, short=False):
    """script words the hearer didn't hear (a fuzzy match: a spelling variant of the same sound counts as heard; a word the script
    joins with a hyphen counts as heard when the hearer wrote the two halves as one word: a hyphenated store name said right, e.g.
    "Mega-Mart", comes back "megamart" from both ears, and its first half alone falls under the match: every take would be rejected for it)"""
    out = []
    sm = difflib.SequenceMatcher(None, ref, hyp, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("delete", "replace"):
            cand = hyp[j1:j2]
            # the hearer's words around the gap too: a joined word can sit just beside the block
            near = hyp[max(0, j1 - 1):j2 + 1]
            for i in range(i1, i2):
                w = ref[i]
                if len(w) <= 2 and op == "replace" and not short:   # short=True: a short word replaced counts (the A5 ear below)
                    continue
                if any(difflib.SequenceMatcher(None, w, h).ratio() >= 0.6 for h in cand) or \
                        difflib.SequenceMatcher(None, w, "".join(cand)).ratio() >= 0.6:
                    continue
                # ...but never when the hearer's word is simply the neighbour (a short word really left out beside a long one:
                # "are" missing before "different" must stay missing)
                pairs = ([(ref[i - 1] + w, ref[i - 1])] if i > 0 else []) + ([(w + ref[i + 1], ref[i + 1])] if i + 1 < len(ref) else [])
                if any(difflib.SequenceMatcher(None, jw, h).ratio() >= 0.75 and difflib.SequenceMatcher(None, nb, h).ratio() < 0.9
                       for jw, nb in pairs for h in near):
                    continue
                out.append(w)
    return out


def extra_words(ref, hyp):
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if op == "insert":
            out += [h for h in hyp[j1:j2] if len(h) >= 3 and h not in ("AND", "THE")]
    return out


# ---------------------------------------------------------------- a reworded beat's words (--reworded --apply)

def measure_words(nar, t0, t1, text, work, tag):
    """the beat's new words timed on the narration as laid: the script's words forced onto t0..t1 (ctcalign.py), each start then moved
    to where its sound begins only where a pause comes before it, as dj captions times Whisper's words (refine_onsets: a word said in
    one breath with the one before keeps its aligned time). The anchors' onset search (onset(): the quietest point in the 220 ms
    before) finds the same dip for two words said in one breath: that way 8 of 66 words came out 10 ms long ("You've got",
    "and when") -> [{w, start, end}] in the narration's seconds"""
    sys.path.insert(0, str(TOOLS))
    from dj.captions import refine_onsets
    sr = sf.info(str(nar)).samplerate
    a = max(0.0, t0 - 0.05)
    xw, _ = sf.read(str(nar), start=int(a * sr), stop=int((t1 + 0.05) * sr), dtype="float64", always_2d=True)
    xw = xw.mean(1)
    toks = text.split()
    al = C.align(xw, sr, text)
    if len(al) != len(toks):
        raise SystemExit(f"the aligner placed {len(al)} of {len(toks)} new words: nothing rewritten")
    words = [{"w": toks[i], "start": float(al[i]["start"]), "end": float(al[i]["end"])} for i in range(len(toks))]
    wav = Path(work) / f"{tag}_laid.wav"
    sf.write(wav, np.clip(xw, -1, 1), sr, subtype="PCM_16")
    words = refine_onsets(words, wav)
    # the first word from the piece's own first sound (the lay-in cut the piece at its measured onset and laid it at t0; the aligner's
    # 20-ms frames put it 35-50 ms late), as dj captions' beat_onsets starts a beat's first word at its sound
    if abs(words[0]["start"] - (t0 - a)) <= 0.10:
        words[0]["start"] = t0 - a
    return [{"w": w["w"], "start": a + w["start"], "end": a + w["end"]} for w in words]


def reword_captions(P, beat, text, words_abs, nar):
    """the beat's new text in build/beats.json, and its words, cues and chunks in build/captions/words.json from the take's forced
    alignment (each word from its measured first sound to its aligned end; no Whisper pass: its boxes change from pass to pass and
    every pass brings new A3/A5 flags, standard/VOICE_LOCK.md), grouped by dj captions' own group() and settings; the srt files
    and the narration's signature rewritten the way dj captions (and cut_pause.py --words) leave them"""
    sys.path.insert(0, str(TOOLS))
    from dj.captions import PUNCT_BREAK, group, write_srt
    from dj.core import file_sig
    cc = house_cfg()["captions"]
    build = P["dj"] / "build"
    bp = build / "beats.json"
    B = json.loads(bp.read_text(encoding="utf-8"))
    bt = next(b for b in B["beats"] if b["id"] == beat)
    bt["voice"] = text
    bp.write_text(json.dumps(B, indent=1, ensure_ascii=False), encoding="utf-8")
    new = []
    for k, w in enumerate(words_abs):
        s = w["start"]
        e = max(w["end"], s + 0.05)
        if k + 1 < len(words_abs):
            e = min(e, words_abs[k + 1]["start"])
        new.append({"w": w["w"], "start": round(s, 3), "end": round(max(e, s + 0.01), 3), "beat": beat, "emph": None})
    cp = build / "captions" / "words.json"
    D = json.loads(cp.read_text(encoding="utf-8"))
    idx = [i for i, w in enumerate(D["words"]) if w["beat"] == beat]
    if not idx or idx != list(range(idx[0], idx[-1] + 1)):
        raise SystemExit(f"{beat}: its words in {cp} are missing or not in one run: nothing rewritten")
    D["words"][idx[0]:idx[-1] + 1] = new
    for name, args in (("cues", (99, cc["max_chars"], 6.0, ".?!…")),
                       ("chunks", (cc["chunk_words"], cc["chunk_chars"], 2.5, PUNCT_BREAK))):
        L_ = D[name]
        ci = [i for i, c in enumerate(L_) if c["beat"] == beat]
        g = group(new, *args)
        # the neighbours as group() leaves them: a cue runs on to the next one's start when the gap is under 0.4 s
        if ci[0] > 0 and g[0]["start"] - L_[ci[0] - 1]["end"] < 0.4:
            L_[ci[0] - 1]["end"] = g[0]["start"]
        if ci[-1] + 1 < len(L_) and L_[ci[-1] + 1]["start"] - g[-1]["end"] < 0.4:
            g[-1]["end"] = L_[ci[-1] + 1]["start"]
        L_[ci[0]:ci[-1] + 1] = g
    D["narration_sig"] = file_sig(nar)
    cp.write_text(json.dumps(D, indent=1, ensure_ascii=False), encoding="utf-8")
    write_srt(build / "captions" / "captions.srt", D["cues"])
    write_srt(build / "captions" / "chunks.srt", D["chunks"])
    print(f"  captions: {beat}'s {len(idx)} old words -> {len(new)} new ({new[0]['start']:.3f}-{new[-1]['end']:.3f}), its cues and chunks "
          f"regrouped, the srt files and the narration's signature rewritten; beats.json's text replaced")


# ---------------------------------------------------------------- main

def main():
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("beat")
    ap.add_argument("takes", nargs="+", type=int)
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--anchor", nargs="*", default=[], help="more phrases that must keep their time")
    ap.add_argument("--skip-anchor", nargs="*", default=[], help="phrases found in the picture or cues that may move (recorded in "
                    "the lay-in's entry for the picture's owner: the word lands earlier or later than its shot or mark)")
    ap.add_argument("--narration")
    ap.add_argument("--words", help="the edit's words.json (default tools/motion/src/<src>/words.json)")
    ap.add_argument("--takes-dir")
    ap.add_argument("--inserts")
    ap.add_argument("--no-checks", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--gap-after", type=float, help=f"s of silence kept before the next sound (default {MIN_GAP_AFTER}); a take's "
                    "own last word with its fade laid back can run a few ms over at 0.06, inaudible at 0.05")
    ap.add_argument("--no-span-gate", action="store_true", help="beats laid in one after another (a re-voiced section): "
                    "skip the gate on each changed span; the whole gate runs after the last one")
    ap.add_argument("--reworded", action="store_true", help="the beat's words changed in script.md: its whole new text goes into the "
                    "old slot (the docstring's --reworded)")
    a = ap.parse_args()
    if a.reworded and (a.frm or a.to):
        raise SystemExit("--reworded lays in the whole beat's new words: no --from/--to")
    P = G.paths(a.video, final=a.narration)
    h0 = VL.sha(P["script"])          # script.md as this run found it: a run whose script changed under it doesn't land
    cfg = P["cfg"]
    src = (cfg.get("video") or {}).get("src")
    fps = float((cfg.get("video") or {}).get("fps", 60))
    max_drift = 2.0 / fps
    tempo = float(house_cfg()["tts"].get("tempo", 1.0))
    m = re.search(r"^CONFIG:\s*tts\.tempo\s*=\s*([\d.]+)", P["script"].read_text(encoding="utf-8"), re.M)
    if m:
        tempo = float(m[1])
    wpath = Path(a.words) if a.words else (MOTION / "src" / src / "words.json" if src else P["words"])
    W = G.load_words(wpath)
    nar = Path(P["final"])
    # only the window around the beat (a whole long narration read as float64 peaks at ~5 GB a process, and two at once push the
    # memory to its limit): its words +-WIN_S, the absolute sample indices kept by WinArray
    bw = [w for w in W if w["beat"] == a.beat]
    if not bw:
        raise SystemExit(f"{a.beat}: no words in the edit's words.json")
    x = WinArray(nar, bw[0]["start"] - WIN_S, bw[-1]["end"] + WIN_S)
    sr = x.sr
    work = P["dj"] / "build" / "voice" / "layin" / a.beat
    work.mkdir(parents=True, exist_ok=True)
    old = old_piece(x, sr, W, a.beat, a.frm, a.to)
    pk = [key(w) for w in old["words"]]
    old_rel = {i: old["on"][old["gi"] + i] - old["t_on"] for i in range(len(pk))}
    text = script_text(P, a.beat)
    script_toks = text.split()
    nk = [key(t) for t in script_toks]
    if a.reworded and nk == pk:
        raise SystemExit(f"{a.beat}: script.md says the words the narration says: not reworded (drop --reworded)")
    # the anchors: phrases from the picture and the cue sheet, plus --anchor (--reworded: by the NEW words' index, each with the time
    # its phrase had in the old words; a phrase the new words don't say is GONE)
    anchors, gone, target = set(), [], dict(old_rel)
    phrases = anchors_in(P, a.beat) + list(a.anchor)
    skip = {key(p) for p in a.skip_anchor}
    if a.reworded:
        target = {}
    gone_open = []                    # GONE and not --skip-anchor'd: nothing can land it
    for ph in phrases:
        phk = [key(t) for t in ph.split() if key(t)]
        i = find_seq(pk, phk)
        j = find_seq(nk, phk) if a.reworded else None
        if a.reworded and i is not None and j is None and ph not in gone:
            gone.append(ph)           # on record skipped or not: the picture's owner re-anchors it
            if key(ph) not in skip:
                gone_open.append(ph)
        if key(ph) in skip:
            continue
        if not a.reworded:
            if i is not None and i > 0:
                anchors.add(i)
            continue
        if i is None or j is None:
            continue                  # not in the old words (another beat's phrase written alike), or GONE
        if i > 0 or j > 0:
            anchors.add(j)
            target[j] = old_rel[i]
    anchors = sorted(anchors)
    aw = script_toks if a.reworded else old["words"]      # the words the anchor indices point into
    room = old["t_next"] - old["t_on"] - (MIN_GAP_AFTER if a.gap_after is None else a.gap_after)
    print(f"{P['video']} {a.beat}: old piece {old['t_on']:.3f}-{old['t_off']:.3f} ({old['t_off'] - old['t_on']:.3f} s), next sound "
          f"{old['t_next']:.3f}, room {room:.3f} s; {len(pk)} words '{' '.join(old['words'][:4])} ... {old['words'][-1]}'")
    if a.reworded:
        print(f"  reworded: {len(nk)} new words '{' '.join(script_toks[:4])} ... {script_toks[-1]}' (pauses the house's: "
              f"{SENT} s between sentences, {INNER} s inside one)")
    print(f"  anchors (picture/cues/--anchor, landing within {max_drift * 1000:.0f} ms = 2 frames): " +
          (", ".join(f"{aw[i]!r} +{target[i]:.3f}" for i in anchors) or "none inside the piece") +
          (f"; GONE from the new words (their owner re-anchors; --skip-anchor each): {', '.join(map(repr, gone))}" if gone else "") +
          (f"; skipped (moves, on record): {', '.join(map(repr, a.skip_anchor))}" if a.skip_anchor else ""))
    if a.reworded:
        piece_text, piece_keys = text, nk
    else:
        i0 = find_seq(nk, pk)
        piece_text = " ".join(script_toks[i0:i0 + len(pk)]) if i0 is not None else " ".join(old["words"])
        piece_keys = pk
    tdir = Path(a.takes_dir) if a.takes_dir else P["dj"] / "build" / "voice" / "patch"
    rows = []
    for k in a.takes:
        src_wav = tdir / f"{a.beat}_{k}.wav"
        if not src_wav.exists():
            print(f"  take {k}: no {src_wav}")
            continue
        al = json.loads(src_wav.with_suffix(".align.json").read_text(encoding="utf-8"))
        said = "".join(al["characters"]).strip()
        xt, tsr, _ = take_audio(src_wav, work, tempo, k, a.beat)
        assert tsr == sr, (tsr, sr)
        try:
            piece, words, take_words = take_piece(xt, sr, said, script_toks, piece_keys)
        except (ValueError, StopIteration) as e:
            print(f"  take {k}: can't cut the piece ({e})")
            continue
        cuts = pauses(piece, sr, words)
        y, nw, drift, sets = place(piece, sr, words, cuts, target, anchors, reworded=a.reworded, tol=max_drift)
        L = len(y) / sr
        lo = G.db(x[int(old["t_on"] * sr):int(old["t_off"] * sr)])
        y = y * 10 ** ((lo - G.db(y)) / 20)
        fits = L <= room
        worst = max((abs(v) for v in drift.values()), default=0.0)
        if gone_open:
            worst = float("inf")          # a phrase the picture hangs on is no longer said: nothing lands it
        row = {"k": k, "len": L, "fits": fits, "drift": drift, "sets": sets, "worst": worst, "y": y, "words": nw}
        if a.reworded:
            row["gap_after"] = old["t_next"] - (old["t_on"] + L)   # the pause after the new piece, to the next sound
        print(f"  take {k}: {L:.3f} s ({'FITS' if fits else 'OVER by %.3f' % (L - room)}), anchors " +
              (", ".join(f"{aw[i]!r} {drift[i] * 1000:+.0f} ms" + (f" (pause set {sets[i]:.3f})" if i in sets else "")
                         for i in anchors) or "-") + ("" if worst <= max_drift else "  ANCHOR OFF") +
              (f"; pause after it {row['gap_after']:.3f} s (the old one {old['t_next'] - old['t_off']:.3f})" if a.reworded else ""))
        if not a.no_checks:
            row["checks"] = check_take(P, y, sr, nw, piece_text, work, k, take=(work / f"{a.beat}_{k}_D.wav", take_words))
            c = row["checks"]
            print(f"      {'CLEAN' if c['clean'] else 'REJECT: ' + '; '.join(c['why'])}")
            for n in c["names"]:
                print(f"      name {n['name']}: {n['verdict']} {n['margin']:+.3f} (heard {n['heard']!r})")
        rows.append(row)
        new = x.win.copy()           # the window only, as the narration will be there (absolute sample i is new[i - x.w0])
        w0 = x.w0
        new[int(old["t_on"] * sr) - w0:int(old["t_zero"] * sr) - w0] = 0      # the old piece out, the next word's onset kept
        new[int(old["t_on"] * sr) - w0:int(old["t_on"] * sr) - w0 + len(y)] += y
        s0, s1 = int((old["t_on"] - 3) * sr), int((old["t_next"] + 3) * sr)
        sf.write(work / f"preview_{k}.wav", np.clip(new[s0 - w0:s1 - w0], -1, 1), sr, subtype="PCM_16")
        if not a.no_checks:
            # the accent IN PLACE (the gate's A11: a take can pass alone and fail in the narration at the join into the next take):
            # the narration as it will be, 6 s around the piece, on the gate's own 0.5-s grid and the three offsets between
            g0 = max(0.0, np.floor((old["t_on"] - 6.0) / 0.5) * 0.5)
            g1 = min(len(x) / sr, old["t_next"] + 6.0)
            if int(g0 * sr) < w0 or int(g1 * sr) > x.w1:
                raise SystemExit("the in-place window runs outside the narration read: raise WIN_S")
            pw = work / f"place_{k}.wav"
            sf.write(pw, np.clip(new[int(g0 * sr) - w0:int(g1 * sr) - w0], -1, 1), sr, subtype="PCM_16")
            r = subprocess.run([GT, str(HERE / "accent_take.py"), str(pw), "--in-place", f"{old['t_on'] - g0:.3f}",
                                f"{old['t_on'] + len(y) / sr - g0:.3f}", "--grid-t0", f"{g0:.3f}"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            try:
                ip = json.loads(r.stdout[r.stdout.index("{"):])
                # autopick.in_place_rejects' rule (that module needs the pipeline venv): British on any offset, maybe on the gate's own
                why = [h["msg"] for h in ip["hard"]] + [s["msg"] for s in ip["soft"] if ip.get("gate") is None or s["offset"] == ip["gate"]]
                row["checks"]["in_place"] = {"hard": ip["hard"], "soft": ip["soft"], "gate": ip["gate"],
                                             "max": [o["max"] for o in ip["offsets"]]}
            except (ValueError, KeyError) as e:
                why = [f"the in-place accent could not run ({type(e).__name__}): " + (r.stderr or r.stdout)[-300:]]
            if why:
                row["checks"]["why"] = row["checks"]["why"] + ["accent in place: " + "; ".join(why)]
                row["checks"]["clean"] = False
            elif "in_place" in row["checks"]:
                # a beat too short for the guard alone (it needs 4 s or more) is judged where it sits instead
                short = [w for w in row["checks"]["why"] if "too short for the accent guard" in w]
                if short:
                    row["checks"]["why"] = [w for w in row["checks"]["why"] if w not in short]
                    row["checks"]["clean"] = not row["checks"]["why"]
                    print("      the piece is too short for the guard alone: its accent is the in-place verdict")
            print(f"      in place: {'clean' if not why else 'REJECT: ' + '; '.join(why)} (peaks by grid offset "
                  f"{row['checks'].get('in_place', {}).get('max')})")
    s0, s1 = int((old["t_on"] - 3) * sr), int((old["t_next"] + 3) * sr)
    sf.write(work / "preview_old.wav", np.clip(x[s0:s1], -1, 1), sr, subtype="PCM_16")
    ok = [r for r in rows if r["fits"] and r["worst"] <= max_drift and (a.no_checks or r["checks"]["clean"])]
    if a.reworded:     # every anchor landed or skipped on record: the clean take with the lowest accent score (autopick's rule)
        acc = lambda r: ((r.get("checks") or {}).get("accent") or {}).get("score")  # noqa: E731
        pick = min(ok, key=lambda r: (acc(r) if acc(r) is not None else 1.0, r["worst"])) if ok else None
    else:
        pick = min(ok, key=lambda r: (r["worst"], -(room - r["len"]))) if ok else None
    report = {"video": P["video"], "beat": a.beat, "narration": str(nar), "old": {k: v for k, v in old.items() if k not in ("on", "ctc")},
              "anchors": [aw[i] for i in anchors], "room": room,
              "takes": [{kk: vv for kk, vv in r.items() if kk not in ("y", "words")} for r in rows], "pick": pick["k"] if pick else None}
    if a.reworded:
        report["reworded"] = {"old_text": " ".join(old["words"]), "new_text": text, "gone": gone, "skipped": a.skip_anchor}
    (work / "layin_report.json").write_text(json.dumps(report, indent=1, default=float, ensure_ascii=False), encoding="utf-8")
    if not pick:
        print("NO TAKE: none is clean, fits the slot and lands its anchors; voice more takes (span_takes.py), reword the cue if the "
              "accent or a name keeps failing (standard/SOUND_AND_VOICE.md, the method step 4)" +
              ("; a phrase the picture hangs on is GONE from the new words: --skip-anchor it (on record for its owner)"
               if gone_open else ""))
        sys.exit(2)
    print(f"PICK: take {pick['k']} ({pick['len']:.3f} s of {room:.3f}, worst anchor {pick['worst'] * 1000:.0f} ms); previews in {work}")
    if not a.apply:
        return
    # ------------------------------------------------------------ apply
    if VL.sha(P["script"]) != h0:
        raise SystemExit("script.md changed during this run: nothing laid in (the takes were judged against the old words); run it again")
    y = pick["y"]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = P["dj"] / "build" / "voice" / "layin" / f"{stamp}_{a.beat}"
    bdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(nar, bdir / "narration.wav")
    sha_before = VL.sha(nar)
    i_on, span = int(round(old["t_on"] * sr)), int(round((old["t_zero"] - old["t_on"]) * sr))
    n_ = max(span, len(y))
    # only the slot is read and written back in place (the file's other samples are not touched, so not loaded)
    with sf.SoundFile(str(nar), "r+") as fh:
        if fh.subtype != "PCM_16" or fh.channels != 1:
            raise SystemExit(f"{nar}: {fh.subtype}, {fh.channels} channel(s); the lay-in writes mono PCM_16")
        fh.seek(i_on)
        out = fh.read(n_, dtype="int16", always_2d=True)[:, 0].astype(np.float64)
        out[:max(span, len(y))] = 0
        out[:len(y)] += y * 32768
        fh.seek(i_on)
        fh.write(np.clip(np.round(out), -32768, 32767).astype(np.int16))
    print(f"  narration.wav: {a.beat} take {pick['k']} laid in at {old['t_on']:.3f} (backup {bdir})")
    if a.reworded:     # the new words: the beat's text and its captions, as dj captions leaves them (no Whisper pass)
        b_ = P["dj"] / "build"
        for f in (b_ / "beats.json", b_ / "captions" / "words.json"):
            shutil.copy2(f, bdir / f.name)
        reword_captions(P, a.beat, text, measure_words(nar, old["t_on"], old["t_on"] + len(y) / sr, text, bdir, a.beat), nar)
    # the word files, the way the chain leaves them (the mix's staleness check reads their times against the narration's)
    if src:
        subprocess.run([GT, str(MOTION / "sync_words.py"), P["video"], src], cwd=REPO, check=True, capture_output=True)
    ins = a.inserts or (cfg.get("voice") or {}).get("inserts")
    if ins:
        ib = P["dj"] / "build" / "insert"
        for f in ("narration_ins.wav", "words_ins.json"):
            if (ib / f).exists():
                shutil.copy2(ib / f, bdir / f)
        subprocess.run([ED, ins], cwd=REPO, check=True, capture_output=True)
        WI = G.load_words(ib / "words_ins.json")
        w0 = next(w for w in G.load_words(wpath) if w["beat"] == a.beat) if a.reworded else W[old["gi"]]
        hit = next((w for w in WI if w["beat"] == a.beat and key(w["w"]) == key(w0["w"]) and
                    abs((w["end"] - w["start"]) - (w0["end"] - w0["start"])) < 1e-3), None)
        if hit is None:
            raise SystemExit("the inserted copy has no matching first word: check it before mixing")
        shift = hit["start"] - w0["start"]
        chk, _ = sf.read(ib / "narration_ins.wav", dtype="int16", always_2d=True)
        j = int(round((old["t_on"] + shift) * sr))
        gap = int(np.max(np.abs(chk[j:j + len(y), 0].astype(np.int64) - np.round(out[i_on:i_on + len(y)]).astype(np.int64))))
        print(f"  inserted copy rebuilt ({Path(ins).name}): shift {shift:+.3f} s, the piece there differs by {gap} at most")
        if gap > 2:
            raise SystemExit("the inserted copy does not hold the new piece: check before mixing")
    entry = {"beat": a.beat, "take": pick["k"], "t0": round(old["t_on"], 3), "t1": round(old["t_on"] + len(y) / sr, 3),
             "slot_end": round(old["t_next"], 3), "anchors_ms": {aw[i]: round(v * 1000) for i, v in pick["drift"].items()},
             "narration_before": sha_before, "backup": str(bdir), "skipped_anchors": a.skip_anchor}
    if a.reworded:
        # the join after the piece back to the old one's pause: its quiet measured as cut_pause.py measures it (10-ms frames under
        # -45 dB) on the narration before the lay-in; at most the house's SENT, so no pause runs over the house's
        t_end = old["t_on"] + len(y) / sr
        seg = x[int((old["t_off"] - 0.05) * sr):int((old["t_next"] + 0.1) * sr)]
        h_ = int(0.01 * sr)
        q_ = 20 * np.log10(np.sqrt((seg[:len(seg) // h_ * h_].reshape(-1, h_) ** 2).mean(1)) + 1e-12) < -45
        run_ = best_ = 0
        for v in q_:
            run_ = run_ + 1 if v else 0
            best_ = max(best_, run_)
        keep = min(SENT, best_ * 0.01)
        extra = pick["gap_after"] - (old["t_next"] - old["t_off"])
        entry["reworded"] = {"old_text": " ".join(old["words"]), "new_text": text, "gone": gone,
                             "pause_after": round(pick["gap_after"], 3), "old_pause_after": round(old["t_next"] - old["t_off"], 3),
                             "old_join_quiet": round(best_ * 0.01, 3)}
    if VL.locked(P["video"]):
        VL.record_layin(P["video"], entry)
        print("  voice_lock.json re-stamped with the lay-in on record")
    (bdir / "layin.json").write_text(json.dumps(entry, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.reworded:
        print(f"  the new piece ends at {t_end:.3f}, the next sound at {old['t_next']:.3f}: {pick['gap_after']:.3f} s of pause "
              f"(the old {old['t_next'] - old['t_off']:.3f}, its quiet {best_ * 0.01:.2f} s)" +
              (f"; {extra:.3f} s longer: close it with EDIT tools/sound/cut_pause.py {P['video']} {t_end - 0.03:.2f} --keep {keep:.2f} "
               f"--words (the voice unlocked for it; every later word moves back by the cut, on record), then sync_words.py"
               if extra > 1.0 / fps else " (no longer than the old: nothing to close)"))
    # the sound gate on the changed span only
    if a.no_span_gate:
        print("  the gate on the changed span skipped (--no-span-gate): run the whole gate after the last lay-in")
        return
    g = subprocess.run([ED, str(TOOLS / "sound" / "gate_sound.py"), P["video"], "--span", f"{old['t_on'] - 2:.2f}",
                        f"{old['t_next'] + 2:.2f}", "--only", "A2,A3,A4,A7,A8,A10,A11"], cwd=REPO, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(g.stdout[-2500:])
    sys.exit(0 if g.returncode == 0 else 3)


if __name__ == "__main__":
    main()
