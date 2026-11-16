"""Narration: one WAV per beat (cached by text + engine settings), frame-aligned layout, two-pass loudnorm.

Engines: dummy (tone bursts, for tests) | command (any local CLI, e.g. tools/voice/voice_cli.py) | elevenlabs (the REST API with
timestamps: whole sections in one request, cut into beats at the pauses).

  cd tools && PIPE -m dj tts ../videos/<video>"""
import base64
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import numpy as np
from pathlib import Path

from . import script
from .core import SR, ff, loudness, read_wav, require_voice, to_wav, write_wav
from paths import MEDIA, PY_EDIT, SECRETS, TOOLS  # noqa: E402  (core put tools/common on the path)


def cache_key(tcfg, text):
    eng = tcfg["engine"]
    # lead_in only steers a cold request's start, so it stays out of the key: adding it re-voices nothing already approved; the
    # same for the warm-up (spoken before a first section by span_takes.py, the voice lock's generation; dj tts doesn't send it)
    settings = {"engine": eng, "text": text, "cfg": {k: v for k, v in tcfg.get(eng, {}).items() if k not in ("lead_in", "warmup")}}
    if eng == "dummy":
        settings["wpm"] = tcfg["wpm"]
    return hashlib.sha1(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:16]


def dummy(text, wpm, out):
    """Quiet voice-like tone bursts, one per word; duration = words / wpm."""
    words = text.split()
    dur = max(0.6, len(words) / wpm * 60)
    t = np.arange(int(dur * SR)) / SR
    env = np.zeros_like(t)
    lens = np.array([len(w) + 1 for w in words], float)
    edges = np.concatenate([[0], np.cumsum(lens) / lens.sum() * dur])
    for a, b in zip(edges[:-1], edges[1:]):
        i, j = int(a * SR), int((a + (b - a) * 0.8) * SR)
        env[i:j] = np.hanning(max(j - i, 2))[: j - i]
    sig = (np.sin(2 * np.pi * 170 * t) + 0.5 * np.sin(2 * np.pi * 340 * t) + 0.25 * np.sin(2 * np.pi * 510 * t)) * env
    write_wav(out, sig / 1.75 * 0.3 * 32767)


def command(tcfg, text, out):
    """Runs the configured template. {text} = the text, {txt} = path to a UTF-8 file with it,
    {voice} = [tts.command].voice, {wav} = output path. Any audio format ffmpeg reads is fine.
    A list template is an argv run without a shell (Windows and Linux; values need no quoting).
    A string template is a bash command line (Linux/WSL only; values are shell-quoted)."""
    c = tcfg["command"]
    txt, raw = out.with_suffix(".txt"), out.with_name(out.stem + "_raw.wav")
    txt.write_text(text, encoding="utf-8")
    vals = {"text": text, "txt": str(txt), "voice": str(c.get("voice", "")), "wav": str(raw)}
    tpl = c["template"]
    if isinstance(tpl, list):
        subprocess.run([str(a).format(**vals) for a in tpl], check=True)
    elif os.name == "nt":
        raise SystemExit('[tts.command] template: on Windows use the list form, e.g. ["python", "tts.py", "--txt", "{txt}", "--out", "{wav}"]')
    else:
        q = shlex.quote
        subprocess.run(tpl.format(**{k: q(v) for k, v in vals.items()}), shell=True, check=True, executable="/bin/bash")
    to_wav(raw, out)
    raw.unlink()


def speakable(tcfg, text):
    """[tts.pronounce] respellings (whole words), e.g. Saoirse = "Sersha": only the text the local engine speaks changes;
    captions, descriptions and the script keep the real spelling. Each entry is measured before it goes in."""
    for word, say in tcfg.get("pronounce", {}).items():
        text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", say, text)  # whole tokens, also ones ending in a symbol ("R18+")
    return text


NAMES = Path(__file__).resolve().parents[1] / "sound" / "names.json"   # the sound gate's names table: written spelling -> what the voice is sent


def voice_text(tcfg, text):
    """What ElevenLabs is sent: [tts.pronounce] plus every respelling in the shared names table (tools/sound/names.json, "say" other
    than "as is"), so every take gets them (a table applied by hand misses names, and those lines need re-voicing). The script, its
    captions and the words keep the real spelling (captions_fix.json maps what Whisper hears back)."""
    text = speakable(tcfg, text)
    try:
        names = json.loads(NAMES.read_text(encoding="utf-8")).get("names", {})
    except (OSError, ValueError):
        names = {}
    plain = set(tcfg.get("plain_names", []))   # names sent as written (a pronunciation dictionary serves them; span_takes --plain)
    for word, e in sorted(names.items(), key=lambda kv: -len(kv[0])):
        say = (e or {}).get("say", "as is")
        if say and say != "as is" and word not in plain:
            text = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", say, text)
    return text


def is_batch(tcfg):
    """A list template containing {manifest} = batch mode: one call renders every uncached beat (the model loads once)."""
    tpl = tcfg.get("command", {}).get("template")
    return isinstance(tpl, list) and any("{manifest}" in str(a) for a in tpl)


def command_batch(tcfg, items, retake=0):
    """items = [(text, out_wav)]. {manifest} = a UTF-8 JSON list of {"text", "txt", "wav"} (the engine writes each "wav"),
    {voice} = [tts.command].voice. Outputs are converted like single calls (any format ffmpeg reads). retake n > 0 adds
    "retake": n to each entry (voice_cli.py: another take of the same text)."""
    c = tcfg["command"]
    man = items[0][1].with_name("batch_manifest.json")
    entries, raws = [], []
    for item in items:
        text, out, n = (*item, retake) if len(item) == 2 else item  # (text, out) or (text, out, retake)
        txt, raw = out.with_suffix(".txt"), out.with_name(out.stem + "_raw.wav")
        txt.write_text(text, encoding="utf-8")
        entries.append({"text": text, "txt": str(txt), "wav": str(raw), **({"retake": n} if n else {})})
        raws.append(raw)
    man.write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8")
    vals = {"manifest": str(man), "voice": str(c.get("voice", ""))}
    subprocess.run([str(a).format(**vals) for a in c["template"]], check=True)
    for item, raw in zip(items, raws):
        to_wav(raw, item[1])
        raw.unlink()


def sections(texts, max_words):
    """Group consecutive beats into sections of <= max_words, preferring to break after a beat that ends a sentence
    (a beat that splits a sentence stays with its neighbour, so the sentence is spoken in one go). Sections come out about
    equal: a short last section is read slower and differently (a short line rendered on its own after a long section drags,
    word by word)."""
    ends = lambda j: re.search(r"[.?!…][\"')\]]*$", texts[j].strip())
    total = sum(len(t.split()) for t in texts)
    k = max(1, math.ceil(total / max_words))
    target = total / k
    groups, cur, n = [], [], 0
    for i, t in enumerate(texts):
        w = len(t.split())
        if cur and len(groups) < k - 1 and n >= 0.9 * target and ends(cur[-1]):
            groups.append(cur)
            cur, n = [], 0
        elif cur and n + w > max_words:
            stops = [k for k, j in enumerate(cur) if ends(j)]
            cut = stops[-1] + 1 if stops else len(cur)
            groups.append(cur[:cut])
            cur = cur[cut:]
            n = sum(len(texts[j].split()) for j in cur)
        cur.append(i)
        n += w
    return groups + ([cur] if cur else [])


def tighten_pauses(x, max_pause, keep=0.12, thr_db=-45.0):
    """Shorten silences longer than max_pause (s) to `keep` s (no dead air). Word-internal gaps are shorter."""
    hop = int(SR * 0.01)
    n = len(x) // hop
    if not max_pause or n == 0:
        return x
    xf = x.astype(np.float64) / 32768
    rms = 20 * np.log10(np.sqrt((xf[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    silent = rms < rms.max() + thr_db
    out, i = [], 0
    while i < n:
        j = i
        while j < n and silent[j] == silent[i]:
            j += 1
        seg = x[i * hop: j * hop]
        if silent[i] and (j - i) * 0.01 > max_pause and 0 < i and j < n:
            k = int(keep * SR / 2)
            seg = np.concatenate([seg[:k], seg[-k:]])
        out.append(seg)
        i = j
    return np.concatenate(out + [x[n * hop:]])


def voicing(xf, i, hop):
    """Pitch strength at 10 ms frame i: normalised autocorrelation peak for 70-400 Hz over 40 ms (voiced speech high, breath low)."""
    s = xf[i * hop: i * hop + int(0.04 * SR)]
    if len(s) < int(0.04 * SR):
        return 0.0
    s = s - s.mean()
    ac = np.correlate(s, s, "full")[len(s) - 1:]
    return float(ac[SR // 400: SR // 70].max() / ac[0]) if ac[0] > 0 else 0.0


def centroid(xf, i, hop):
    """Spectral centroid (Hz) of 10 ms frame i: an 's' hisses at 4-8 kHz, a breath sits lower."""
    s = xf[i * hop:(i + 1) * hop]
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s))))
    return float((sp * np.fft.rfftfreq(len(s), 1 / SR)).sum() / (sp.sum() + 1e-12))


def tighten_gaps(x, words, keep, quiet_db=-30.0, breath=(0.10, -3.0, 0.30), soft_db=-12.0, hiss_hz=3500, margin=0.03,
                 fade=0.01):
    """One flow (breaths out, no pauses). Between two words, 10 ms frames are quiet (quiet_db under the speech
    median), soft (under soft_db, little pitch, not hissy: breath noise right after a word), breath (an island between quiet
    frames at least breath[0] s long, never louder than breath[1] dB under speech, median pitch strength under breath[2]:
    measured in-breaths are 170-230 ms, -3..-15 dB, 0.18-0.24) or other. The longest stretch of those (with at
    least one quiet frame or 100 ms of soft ones) is cut down to keep["sentence"|"comma"|"word"] s; margin s stay next to
    each word, joins are crossfaded. Other sound (a word Whisper placed late: the "F" of "Follow" at +10 dB, an "s" tail)
    is never cut. words = [{w, start, end}] on x. -> (audio, [(t, removed_s)] in x's time, ascending)."""
    hop, xf = SR // 100, x.astype(np.float64) / 32768
    n = len(xf) // hop
    if n == 0 or len(words) < 2:
        return x, []
    db = 20 * np.log10(np.sqrt((xf[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    inside = np.concatenate([np.arange(int(w["start"] * 100), min(int(w["end"] * 100), n)) for w in words])
    ref = np.median(db[inside]) if len(inside) else db.max() - 18
    cuts = []
    for a, b in zip(words, words[1:]):
        lo, hi = max(int((a["end"] - 0.05) * 100), 0), min(int((b["start"] + 0.05) * 100), n)
        quiet = db[lo:hi] < ref + quiet_db
        a1, b0 = int(a["end"] * 100), int(b["start"] * 100)  # soft frames only strictly between the words
        soft = np.array([a1 <= lo + j < b0 and not quiet[j] and db[lo + j] < ref + soft_db and voicing(xf, lo + j, hop)
                         < breath[2] and centroid(xf, lo + j, hop) < hiss_hz for j in range(hi - lo)], dtype=bool)
        if not quiet.any() and soft.sum() < 10:
            continue
        ok = quiet | soft  # quiet, soft or breath
        q = np.flatnonzero(quiet)
        k = q[0] if len(q) else len(quiet)
        while len(q) and k < q[-1]:  # islands of sound between quiet frames
            if quiet[k]:
                k += 1
                continue
            e = k
            while not quiet[e]:
                e += 1
            fr = np.arange(lo + k, lo + e)
            if ((e - k) * 0.01 >= breath[0] and db[fr].max() <= ref + breath[1]
                    and np.median([voicing(xf, i, hop) for i in fr]) < breath[2]):
                ok[k:e] = True
            k = e
        best, cur = None, None  # longest run of ok frames with a quiet frame or 100 ms of soft ones in it
        for i in range(len(ok) + 1):
            if i < len(ok) and ok[i]:
                cur = i if cur is None else cur
                continue
            if cur is not None and (quiet[cur:i].any() or soft[cur:i].sum() >= 10):
                if best is None or i - cur > best[1] - best[0]:
                    best = (cur, i)
            cur = None
        if not best:
            continue
        f0, f1 = lo + best[0], lo + best[1]
        want = keep["sentence"] if a["w"][-1] in ".?!…" else keep["comma"] if a["w"][-1] in ",;:" else keep["word"]
        s, e = f0 * hop + int(margin * SR), f1 * hop - int(margin * SR)
        remove = (e - s) - max(int((want - 2 * margin) * SR), 0)
        if remove > 0.02 * SR:
            c0 = s + (e - s - remove) // 2
            cuts.append((c0, c0 + remove))
    return splice(x, cuts, fade), [(c0 / SR, (c1 - c0) / SR) for c0, c1 in cuts]


def trim_edges(x, keep=0.03, keep_end=0.12, rel_db=-40.0):
    """Drop a section's leading/trailing silence (the engine adds ~0.2-0.3 s each side). "Silence" is relative to the section's
    own level (its loud frames minus 40 dB), and more is kept after the last sound: a fixed -45 dBFS cut the soft end of a final
    word on a quiet take (a raw take at -28 LUFS lost its last word's tail)."""
    hop = SR // 100
    n = len(x) // hop
    if n == 0:
        return x
    xf = x[: n * hop].astype(np.float64).reshape(n, hop) / 32768
    db = 20 * np.log10(np.sqrt((xf ** 2).mean(1)) + 1e-12)
    loud = np.flatnonzero(db > np.percentile(db, 95) + rel_db)
    if not len(loud):
        return x
    return x[max(loud[0] * hop - int(keep * SR), 0):min((loud[-1] + 1) * hop + int(keep_end * SR), len(x))]


EDGE_HOP = SR // 200  # 5 ms frames for finding where a sound starts and ends


def frame_db(x, hop=EDGE_HOP):
    n = len(x) // hop
    xf = x[: n * hop].astype(np.float64).reshape(n, hop) / 32768
    return 20 * np.log10(np.sqrt((xf ** 2).mean(1)) + 1e-12)


def quiet_floor(db, span=70.0):
    """The level a recording is silent at: its quietest 5 % of frames, but never more than `span` dB under its loudest (digital
    zeros between beats would put the floor at -240 dB, and then nothing would count as quiet)."""
    return max(float(np.percentile(db, 5)), float(db.max()) - span)


def sound_start(x, t, lo, db=None, floor=None, over_db=8.0, reach=0.12):
    """The sample where the sound playing at t (s) began. ElevenLabs' character times run 30-60 ms BEHIND the audio (a word's
    first consonant rises from -62 dB 60 ms before its character time; a fixed cut at -30 ms takes that consonant off, "Right"
    sounds like "ight"). So: walk back 5 ms frames from t while they are louder than the floor + over_db, at most `reach` s
    and never before lo (s, the previous sound's end); if no quiet frame is met, the quietest frame on the way (words that run
    together, or an in-breath just before the word)."""
    db = frame_db(x) if db is None else db
    floor = quiet_floor(db) if floor is None else floor
    i = min(int(t * SR) // EDGE_HOP, len(db) - 1)
    stop = max(int(max(lo, t - reach) * SR) // EDGE_HOP, 0)
    k = i
    while k > stop and db[k - 1] > floor + over_db:
        k -= 1
    if k > stop or db[stop] <= floor + over_db:
        return max(k - 1, stop) * EDGE_HOP  # one quiet frame kept before the sound
    return (stop + int(np.argmin(db[stop:i + 1]))) * EDGE_HOP


def first_sound(db, floor, upto, over_db=8.0, hold=6):
    """A take's first sound, read from the audio: with a direction tag at the head of the request, ElevenLabs puts the first
    words' character times up to 0.9 s after the speech (a first word timed at 0.93 s, heard at 0.00 s; the error falls to the
    usual ~0.1 s within two words), past sound_start's reach, so a section's first beat lost its first consonant. The take starts in
    silence, so the first `hold` frames in a row over the floor + over_db before `upto` (frames) mark its first word; one quiet frame
    is kept before it."""
    run = 0
    for k in range(0, max(min(upto, len(db)), 0)):
        run = run + 1 if db[k] > floor + over_db else 0
        if run >= hold:
            return max(k - hold, 0) * EDGE_HOP
    return None


def sound_end(x, t, hi, db=None, floor=None, over_db=8.0, reach=0.25):
    """The sample where the sound playing at t (s) has died away (an "s" or a released "t" can ring past the last character's end
    time): walk forward while louder than the floor + over_db, at most `reach` s and never past hi (s, the next sound's start);
    else the quietest frame on the way."""
    db = frame_db(x) if db is None else db
    floor = quiet_floor(db) if floor is None else floor
    i = max(min(int(t * SR) // EDGE_HOP, len(db) - 1), 0)
    stop = min(int(min(hi, t + reach) * SR) // EDGE_HOP, len(db) - 1)
    k = i
    while k < stop and db[k] > floor + over_db:
        k += 1
    if k < stop or db[stop] <= floor + over_db:
        return min((k + 1) * EDGE_HOP, len(x))
    return min((i + int(np.argmin(db[i:stop + 1])) + 1) * EDGE_HOP, len(x))


def gap_between(db, floor, t_end, t_next, t_word=None, over_db=8.0, back=0.25, fwd=0.05):
    """The silence between two words that the timestamps put at t_end (the last word's end) and t_next (the next word's start), as
    sample positions (cut_end, cut_start). ElevenLabs' times can run up to 180 ms behind the audio (the first word of a beat,
    "Now", "So", "And", came out swallowed), so the real pause sat BEFORE the last word's end time
    and the cut landed inside the next word. So the pause is searched in [t_end - back, t_next + fwd]: the longest run of frames under
    floor + over_db; with none, the quietest frame. The previous beat ends at the run's start, the next begins at its end. t_word (the
    previous beat's last word's start time) bounds the search on the left, so a pause before that word is never taken for the gap."""
    a0 = min(t_end, t_next) - back
    if t_word is not None:
        a0 = max(a0, t_word)
    a = max(int(a0 * SR) // EDGE_HOP, 0)
    b = min(int((t_next + fwd) * SR) // EDGE_HOP, len(db) - 1)
    if b <= a:
        k = max(min(int(t_next * SR) // EDGE_HOP, len(db) - 1), 0)
        return k * EDGE_HOP, k * EDGE_HOP
    quiet = db[a:b + 1] <= floor + over_db
    best, k = None, 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if best is None or j - k > best[1] - best[0]:
                best = (k, j)
            k = j
        else:
            k += 1
    if best is None:
        m = a + int(np.argmin(db[a:b + 1]))
        return m * EDGE_HOP, m * EDGE_HOP
    return (a + best[0] + 1) * EDGE_HOP, (a + best[1] - 1) * EDGE_HOP  # one quiet frame kept on each side


def edge_faults(clip, near_db=30.0):
    """A beat that starts or ends in the middle of a sound (a clipped consonant): its first / last 5 ms of sound is within near_db
    of its loudest frame (a word begins and ends from near silence; a clipped consonant begins at ~9 dB under the peak). -> list of
    'start' / 'end'."""
    db = frame_db(clip)
    if not len(db) or db.max() < -80:
        return []
    on = np.flatnonzero(db > db.max() - 80)
    out = []
    if db[on[0]] > db.max() - near_db:
        out.append(f"start ({db[on[0]] - db.max():+.0f} dB)")
    if db[on[-1]] > db.max() - near_db:
        out.append(f"end ({db[on[-1]] - db.max():+.0f} dB)")
    return out


ENDS = re.compile(r"[A-Za-z']*[tdkp](?=[\s,.;:!?\"')]|$)")


def swallowed(x, al, below_db=28.0, look=0.12):
    """Words whose final t/d/k/p the voice barely released (a "But" at -46 dB of burst where the take's other t-words had a
    median of -12: the last consonant is barely heard). The burst = the most energy above 3 kHz in a 20 ms window
    within `look` s of the last letter's start time (ElevenLabs timestamps). -> [(word, s, dB under the take's median)]."""
    ch, st = "".join(al["characters"]), al["character_start_times_seconds"]
    return weak_endings(x, [(m.group(), st[m.end() - 1], st[m.end() - 1] + look) for m in ENDS.finditer(ch) if m.group()], below_db)


def weak_endings(x, items, below_db=28.0):
    xf = x.astype(np.float64) / 32768
    w = int(0.02 * SR)
    win = np.hanning(w)
    f = np.fft.rfftfreq(w, 1 / SR)

    def burst(t0, t1):
        best = -120.0
        for k in range(max(int((t1 - t0) / 0.01), 1)):
            a = max(int((t0 + 0.01 * k) * SR), 0)
            seg = xf[a:a + w]
            if len(seg) < w:
                break
            p = np.abs(np.fft.rfft(seg * win)) ** 2
            best = max(best, 10 * np.log10(p[f > 3000].sum() / w + 1e-12))
        return best

    found = [(word, t0, burst(t0, t1)) for word, t0, t1 in items]
    if len(found) < 4:
        return []
    med = float(np.median([b for _, _, b in found]))
    return [(word, round(t, 2), round(med - b, 1)) for word, t, b in found if med - b >= below_db]


def hum_tones(x, min_db=12.0, lo=80.0, hi=2000.0, n=16384, hop=4096):
    """Steady tones under the voice: [(Hz, dB over the local noise floor)] from the spectrum of the quiet frames (25 dB+ under the
    speech). A bad take can carry one at ~249 Hz, 26 dB over the floor, strongest at the end; it sounds like blowing into a bottle
    (clean takes: none over 4 dB). Up to 3 tones, strongest first."""
    xf = x.astype(np.float64) / 32768
    if len(xf) < n * 4:
        return []
    fr = np.lib.stride_tricks.sliding_window_view(xf, n)[::hop] * np.hanning(n)
    db = 10 * np.log10((fr ** 2).mean(1) + 1e-12)
    q = fr[(db < np.percentile(db, 90) - 25) & (db > np.percentile(db, 90) - 80)]
    if len(q) < 8:
        return []
    spec = 20 * np.log10(np.abs(np.fft.rfft(q, axis=1)).mean(0) + 1e-12)
    f = np.fft.rfftfreq(n, 1 / SR)
    idx = np.flatnonzero((f >= lo) & (f <= hi))
    half = int(40 / (f[1] - f[0]))  # the floor: the median over +-40 Hz
    floor = np.array([np.median(spec[max(i - half, 0):i + half + 1]) for i in idx])
    over = spec[idx] - floor
    peaks = [k for k in range(1, len(idx) - 1) if over[k] >= min_db and over[k] >= over[k - 1] and over[k] >= over[k + 1]]
    out = []
    for k in sorted(peaks, key=lambda k: -over[k]):
        if all(abs(f[idx[k]] - hz) > 15 for hz, _ in out):
            out.append((round(float(f[idx[k]]), 1), round(float(over[k]), 1)))
    return out[:3]


def tone_windows(x, lo=180.0, hi=2000.0, over_db=5.0, share=0.55, win_s=3.0, n=8192, hop=1024):
    """Steady tones UNDER the speech (hum_tones sees only quiet frames, and cut gaps leave few): per win_s window, the share of
    frames in which a frequency (+-1 bin of drift) is a sharp peak (>= over_db over the median of +-30 Hz). The voice's harmonics move with
    its pitch and stay under ~45% (measured: median 32%, p90 42%); an engine tone (246-252 Hz) ran 55-89%. lo=180 Hz keeps the voice's
    own fundamental (~110-140 Hz) out. -> [(start s, Hz, share)] for the windows at or over `share`."""
    xf = x.astype(np.float64).reshape(len(x), -1).mean(1) / 32768 if x.ndim > 1 else x.astype(np.float64) / 32768
    if len(xf) < n * 2:
        return []
    f = np.fft.rfftfreq(n, 1 / SR)
    band = np.flatnonzero((f >= lo) & (f <= hi))
    half = int(30 / (f[1] - f[0]))
    fps, out = SR / hop, []
    win = int(win_s * fps)
    chunk = win * 20
    for c0 in range(0, len(xf) - n, chunk * hop):
        seg = xf[c0:c0 + chunk * hop + n]
        if len(seg) < n * 2:
            break
        fr = np.lib.stride_tricks.sliding_window_view(seg, n)[::hop] * np.hanning(n)
        en = 10 * np.log10((fr ** 2).mean(1) + 1e-12)
        fr = fr[en > en.max() - 35]  # speech frames only (quiet ones are hum_tones' job; near-silence makes any line a "peak")
        if len(fr) < win:
            continue
        S = 20 * np.log10(np.abs(np.fft.rfft(fr, axis=1))[:, band] + 1e-12)
        pad = np.pad(S, ((0, 0), (half, half)), mode="edge")
        med = np.median(np.lib.stride_tricks.sliding_window_view(pad, 2 * half + 1, axis=1), axis=2)
        pk = (S - med >= over_db) & (S >= np.roll(S, 1, 1)) & (S >= np.roll(S, -1, 1))
        pk = pk | np.roll(pk, 1, 1) | np.roll(pk, -1, 1)
        for s0 in range(0, max(len(pk) - win + 1, 1), max(win // 2, 1)):
            sh = pk[s0:s0 + win].mean(0)
            k = int(np.argmax(sh))
            if sh[k] >= share:
                out.append((round(c0 / SR + s0 / fps, 2), round(float(f[band[k]]), 1), round(float(sh[k]), 2)))
    return out


def desteady(x, freqs, halfw=15.0, k=1.5, n=8192, hop=1024, win_s=3.0):
    """Take out only what stays constant: in the STFT bins within halfw Hz of each tone, subtract k x the magnitude's running median over
    win_s (the steady line), keeping the phase. The voice's harmonics move, so their running median is low and they stay (30 Hz
    notches cost the 150-300 Hz band 1.5-8 dB and thinned the voice; this: ~1 dB, the tone 8-11 dB over its surroundings -> ~0).
    k=1.5 measured best (k=2.5 over-subtracts: holes next to the line)."""
    xf = x.astype(np.float64)
    xp = np.pad(xf, (n, n))
    w = np.hanning(n)
    idx = np.arange(0, len(xp) - n, hop)
    F = np.fft.rfft(np.stack([xp[i:i + n] * w for i in idx]), axis=1)
    f = np.fft.rfftfreq(n, 1 / SR)
    band = np.flatnonzero(np.any([np.abs(f - hz) <= halfw for hz in freqs], axis=0))
    if len(band):
        M = np.abs(F[:, band])
        half = int(win_s * SR / hop / 2)
        med = np.stack([np.median(M[max(0, t - half):t + half + 1], axis=0) for t in range(len(M))])
        F[:, band] *= np.maximum(M - k * med, 0.01 * M) / np.maximum(M, 1e-9)  # at most -40 dB
    fr = np.fft.irfft(F, n, axis=1)
    y, norm = np.zeros(len(xp)), np.zeros(len(xp))
    for j, i in enumerate(idx):
        y[i:i + n] += fr[j] * w
        norm[i:i + n] += w * w
    return np.clip(np.round((y / np.maximum(norm, 1e-9))[n:n + len(xf)]), -32768, 32767).astype(np.int16)


def dehum(ctx, x, min_db=12.0, passes=3):
    """Remove steady tones under the voice (the "bottle" sound): hum_tones (quiet frames) and tone_windows (under the speech), then
    desteady around each. tone_windows reports only the strongest line per window, so a weaker neighbour (257.8 Hz next to 246 Hz)
    shows only after the first round: up to `passes` rounds of measure -> remove. -> (audio, [(Hz, dB or % of frames)])."""
    found, y = [], x
    for n in range(passes):
        tones = hum_tones(y, min_db) if n == 0 else []
        for _, hz, sh in tone_windows(y):
            if all(abs(hz - h) > 6 for h, _ in tones + found):
                tones.append((hz, round(sh * 100)))
        tones = [t for t in tones if all(abs(t[0] - h) > 6 for h, _ in found)][:4]
        if not tones:
            break
        y = desteady(y, [hz for hz, _ in tones])
        found += tones
    return y, found


def remap(t, removed):
    """A time in the audio before tighten_gaps -> the same moment after it."""
    return t - sum(d for c, d in removed if c < t)


NUMBER_WORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
                "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty",
                "seventy", "eighty", "ninety", "hundred", "thousand", "million", "and", "a"}


def skipped_phrases(want, got, min_words=3, spans=False):
    """Script phrases missing from what was heard: runs of >= min_words script words with nothing, or at most one word, heard in
    their place ("wind blows ripples over the water and bends" -> "winds"). Number words heard as digits are not a skip ("five
    hundred and fifty" -> "550"). want/got = normalised words. -> [missing phrase, ...] (spans=True: [(phrase, j1, j2), ...], the
    place in `got`)."""
    import difflib
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, want, got, autojunk=False).get_opcodes():
        if op in ("delete", "replace") and i2 - i1 >= min_words and j2 - j1 <= 1:
            if all(w in NUMBER_WORDS for w in want[i1:i2]) and all(g.isdigit() for g in got[j1:j2]):
                continue
            out.append((" ".join(want[i1:i2]), j1, j2) if spans else " ".join(want[i1:i2]))
    return out


def take_score(ctx, x, beats):
    """How good one take of a section is: the script heard word for word (Whisper, 0-1) x 100, minus 15 per skipped phrase (>= 3
    script words left out: a content error), 25 per filler that can't be cut without its word, 3 per filler that can, 2 per
    pause over 0.35 s. It picks what a careful listener would (the take that says every word, with no fillers and no long
    pause). -> (score, details)."""
    import difflib

    from .captions import _key, heard_words
    from .captions import said_after_all
    tmp = ctx.path("voice", "cache", "score_tmp.wav")
    write_wav(tmp, x)
    heard = heard_words(ctx.cfg, tmp)
    want = [_key(w) for b in beats for w in b["voice"].split() if _key(w)]
    got = [_key(h["w"]) for h in heard]  # heard_words keeps only tokens with a letter or digit, so got[j] = heard[j]
    ratio = difflib.SequenceMatcher(None, want, got, autojunk=False).ratio()
    # a phrase missing from the transcript counts only if it's still missing when its stretch is heard alone (Whisper drops phrases)
    skips = [ph for ph, j1, j2 in skipped_phrases(want, got, spans=True) if said_after_all(ctx.cfg, tmp, heard, j1, j2, ph.split()) is None]
    tmp.unlink()
    _, _, found, stuck = cut_fillers(ctx, x, beats)
    hop = SR // 100
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt(((x[: n * hop].astype(np.float64).reshape(n, hop) / 32768) ** 2).mean(1)) + 1e-12) if n else np.zeros(0)
    quiet = db < (np.percentile(db, 90) - 35 if n else 0)
    runs, i = 0, 0
    while i < n:
        j = i
        while j < n and quiet[j]:
            j += 1
        runs += (j - i) > 35 and 0 < i and j < n
        i = j + 1 if j == i else j
    # a steady tone under the voice (the "bottle" sound): dehum notches it later, but a clean take needs no notch
    tw = tone_windows(x)
    n_win = max(int(len(x) / SR / 1.5), 1)
    tone = min(len(tw) / n_win, 1.0)
    first_key = next((_key(w) for b in beats for w in b["voice"].split() if _key(w)), "")
    bad_start = bool(heard) and _key(heard[0]["w"]) != first_key  # a take that opens with another word (an added "But")
    score = ratio * 100 - 15 * len(skips) - 25 * len(stuck) - 3 * len(found) - 2 * runs - 30 * tone - 10 * bad_start
    return round(score, 2), {"match": round(ratio, 3), "skipped": skips, "fillers": found, "stuck": stuck, "long_pauses": int(runs),
                             "tone": round(tone, 2), "bad_start": bad_start}


def pick_takes(ctx, tcfg, groups, texts, wavs, beats):
    """[tts] takes > 1: render that many takes of each new section (one batch: the model loads once), score each (take_score) and keep
    the best as the section's cached file; <sec>.pick.json records the scores. Sections already picked are left alone."""
    n = int(tcfg.get("takes", 1))
    if n < 2:
        return
    off = int(tcfg.get("take_offset", 0))  # fresh seeds for a section re-done after its takes failed (--set tts.take_offset=3)
    todo = [(t, w.with_name(f"{w.stem}_t{k}.wav"), k + off) for t, w in zip(texts, wavs) if not w.exists() for k in range(n)
            if not w.with_name(f"{w.stem}_t{k}.wav").exists()]
    if todo:
        print(f"  {len(todo)} take(s) of {sum(not w.exists() for w in wavs)} section(s): command, batch")
        command_batch(tcfg, todo)
    for k, (g, w) in enumerate(zip(groups, wavs), 1):
        if w.exists():
            continue
        takes = [w.with_name(f"{w.stem}_t{j}.wav") for j in range(n)]
        scored = []
        for j, tw in enumerate(takes):
            x = tighten_pauses(read_wav(tw), tcfg.get("max_pause", 0))
            sc, det = take_score(ctx, x, [beats[i] for i in g])
            scored.append((sc, j, det))
        best = max(scored)
        tw = takes[best[1]]
        w.write_bytes(tw.read_bytes())
        w.with_suffix(".txt").write_text(texts[k - 1], encoding="utf-8")
        w.with_name(w.stem + ".pick.json").write_text(json.dumps({"picked": best[1], "seed_offset": off, "takes": [
            {"take": j, "score": sc, **det} for sc, j, det in sorted(scored, key=lambda s: s[1])]}, indent=1), encoding="utf-8")
        for t in takes:
            t.unlink()
            t.with_suffix(".txt").unlink(missing_ok=True)
        print(f"  section {k}: take {best[1]} of {n} kept (" + ", ".join(f"t{j} {sc:g}" for sc, j, _ in sorted(scored, key=lambda s: s[1])) + ")")


def section_groups(texts, breaks, max_words):
    """Beat indices per voice section: sections never cross a break (a chapter start, the beat after a HOLD), and inside each run
    sections() evens them out under max_words."""
    cuts = [0] + sorted(i for i in breaks if 0 < i < len(texts)) + [len(texts)]
    return [[a + i for i in g] for a, z in zip(cuts, cuts[1:]) for g in sections(texts[a:z], max_words)]


def continuous(ctx, tcfg, beats, say, cache, breaks=()):
    """Render sections in one go (tone and pace carry across beats), then cut them back into beats at the pause before each
    beat's first word (Whisper word times, matched to the script). Returns (clips, pads): pads = 0 inside a section.
    breaks = beat indices that start a new section (a chapter, or the beat after a HOLD)."""
    groups = section_groups([b["voice"] for b in beats], breaks, tcfg.get("section_words", 150))
    texts = [" ".join(say[i] for i in g) for g in groups]
    tail = None
    if texts and not re.search(r"[.?!…][\"')\]]*$", texts[-1].strip()):
        # An open loop line ("Tell me in the comments, 'cause") runs on into the first line, as the loop plays it, and the take is
        # cut after its last script word: ended there, the engine stops mid-word (with a final comma still 4 of 5 one-go takes
        # stopped mid-word).
        tail = say[0]
        texts[-1] = texts[-1].rstrip().rstrip(",") + ", " + tail
    wavs = [cache / f"sec_{cache_key(tcfg, t)}.wav" for t in texts]
    pick_takes(ctx, tcfg, groups, texts, wavs, beats)
    todo = [(t, w) for t, w in zip(texts, wavs) if not w.exists()]
    if todo:
        print(f"  {len(todo)} of {len(groups)} section(s): command, batch, continuous")
        command_batch(tcfg, todo)
    clips, pads, cut_s = [None] * len(beats), [0.0] * len(beats), 0.0
    retakes = tcfg.get("retakes", 0)
    for k, (g, text, wav) in enumerate(zip(groups, texts, wavs), 1):
        for n in range(retakes + 1):
            x = read_wav(wav)
            if tcfg.get("dehum", True):
                x, tones = dehum(ctx, x, tcfg.get("dehum_db", 12.0))
                if tones:
                    print(f"  section {k}: steady tone(s) notched: " + ", ".join(f"{hz:g} Hz ({d:g})" for hz, d in tones))
            x = tighten_pauses(x, tcfg.get("max_pause", 0))
            if tcfg.get("gaps"):
                x = trim_edges(x)
            bs = [beats[i] for i in g] + ([{"id": "_tail", "voice": beats[0]["voice"]}] if tail and k == len(groups) else [])
            parts, cut, stuck = split_section(ctx, tcfg, x, bs, tcfg.get("gaps"), tcfg.get("cut_fillers", False))
            if not stuck or n == retakes:
                break
            # a filler fused into a word can't be cut without the word ("Uh, b't the", the "but" 50 ms): new take
            print(f"  section {k}: {', '.join(stuck)} can't be cut cleanly -> retake {n + 1} of {retakes}")
            command_batch(tcfg, [(text, wav)], retake=n + 1)  # the accepted take replaces the cached one
        if stuck:
            ctx.warn(f"section {k}: filler(s) left in after {retakes} retake(s): {', '.join(stuck)} (listen, or edit the line)")
        if len(parts) > len(g):  # the loop tail goes; the cut sits in the pause after the last word, faded against a click
            parts, fl = parts[:len(g)], int(0.01 * SR)
            parts[-1] = parts[-1].copy()
            parts[-1][-fl:] = (parts[-1][-fl:] * np.linspace(1, 0, fl)).astype(parts[-1].dtype)
        for i, p in zip(g, parts):
            clips[i] = p
        cut_s += cut
        pads[g[-1]] = tcfg["gaps"]["sentence"] - 0.06 if tcfg.get("gaps") else tcfg["gap"]  # sections join like sentences
    print(f"  continuous: {len(beats)} beats in {len(groups)} section(s)" + (f", {cut_s:.2f} s of gaps cut" if cut_s else ""))
    return clips, pads


FILLERS = {"um", "umm", "uhm", "uh", "uhh", "erm", "er", "hmm", "hm", "mm", "mmm"}


def splice(x, cuts, fade=0.01):
    """Remove [(c0, c1)] sample ranges (ascending) from x, crossfading each join over `fade` s."""
    if not cuts:
        return x
    xf, fl = x.astype(np.float64) / 32768, int(fade * SR)
    ramp = np.sin(np.linspace(0, np.pi / 2, fl)) ** 2
    out, prev = [], 0
    for c0, c1 in cuts:  # keep x[prev:c0], then crossfade into x[c1:] over fl samples
        if c0 <= 0:  # a cut from the very start just drops it
            prev = c1
            continue
        c0, c1 = max(c0, prev + fl), max(c1, c0 + fl)
        out.append(xf[prev:c0 - fl])
        out.append(xf[c0 - fl:c0] * (1 - ramp) + xf[c1 - fl:c1] * ramp)
        prev = c1
    out.append(xf[prev:])
    return np.round(np.concatenate(out) * 32768).clip(-32768, 32767).astype(np.int16)


def cut_fillers(ctx, x, beats, margin=0.03):
    """Cut "um"/"uh"/"hmm" the voice added (not in the script) with the silence around them, so the next word follows the
    previous one with a short gap (a leading "um" goes entirely: the Short starts on its first word). A filler-aware Whisper
    pass finds them; afterwards every script word must still be heard, else the cuts are undone and the fillers come back as
    stuck. -> (audio, [(t, s)], found, stuck)."""
    from .captions import FILLER_PROMPT, _key, heard_words
    script_keys = {_key(w) for b in beats for w in b["voice"].split()}
    tmp = ctx.path("voice", "cache", "filler_tmp.wav")
    write_wav(tmp, x)
    heard = heard_words(ctx.cfg, tmp, FILLER_PROMPT)
    cuts, found = [], []
    for i, h in enumerate(heard):
        if _key(h["w"]) not in FILLERS or _key(h["w"]) in script_keys:
            continue
        a = heard[i - 1]["end"] + margin if i else 0.0
        z = heard[i + 1]["start"] - margin if i + 1 < len(heard) else len(x) / SR
        if z - a > 0.02:
            cuts.append((round(a * SR), round(z * SR)))
            found.append(f"{h['w']}@{h['start']:.2f}s")
    if not cuts:
        tmp.unlink()
        return x, [], [], []
    y = splice(x, cuts)
    before = heard_words(ctx.cfg, tmp)
    write_wav(tmp, y)
    after = heard_words(ctx.cfg, tmp)
    tmp.unlink()
    n = lambda hw: sum(_key(w["w"]) in script_keys for w in hw)
    if n(after) < n(before):
        print(f"  filler cut undone: {n(before) - n(after)} script word(s) would have gone with {', '.join(found)}")
        return x, [], [], found
    return y, [(c0 / SR, (c1 - c0) / SR) for c0, c1 in cuts], found, []


def quiet_cut(x, a, b, hop=SR // 100, pad=(0.05, 0.15), quiet_db=25.0):
    """Where to cut between a word Whisper ends at a and the next it starts at b (s): in the longest quiet run (quiet_db under
    the loudest 10 ms) of [a - pad[0], b + pad[1]], at the midpoint if it falls in that run (visual cuts sit mid-pause), else at
    the run's centre. Whisper's boundaries are tens of ms off: it can end one word and start the next at the same time while the
    real pause sits 30-110 ms later, and a cut at Whisper's time clips the last consonant. No quiet run: the quietest stretch (6 dB
    of the minimum), else the midpoint. -> sample."""
    mid = round((a + b) / 2 * SR)
    i0, i1 = max(int((min(a, b) - pad[0]) * 100), 0), min(int((max(a, b) + pad[1]) * 100), len(x) // hop)
    if i1 - i0 < 2:
        return mid
    xf = x[i0 * hop: i1 * hop].astype(np.float64)
    db = 10 * np.log10((xf.reshape(-1, hop) ** 2).mean(1) + 1e-12)
    def longest(mask):
        best, cur = None, None
        for i, q in enumerate(np.append(mask, False)):
            if q and cur is None:
                cur = i
            elif not q and cur is not None:
                best = (cur, i) if best is None or i - cur > best[1] - best[0] else best
                cur = None
        return best
    best = longest(db < db.max() - quiet_db)
    if best is None:  # no real pause (words run together): the quietest stretch, within 6 dB of the window's minimum (two words
        # joined by an 80 ms murmur at -36 dB: the midpoint cut 20 ms off the first word's last consonant)
        best = longest(db <= db.min() + 6.0)
        if best is None or best[1] - best[0] < 2:
            return mid
    if i0 + best[0] <= mid // hop < i0 + best[1]:
        return mid
    return (i0 + (best[0] + best[1]) // 2) * hop + hop // 2


def lead_cut(x, w0, w1, nxt):
    """Where to cut off a stray sound before a section's first script word: the quietest 10 ms after the middle of the stray sound and
    before the next word starts (+20 ms). Whisper times the two back to back (a blip heard as "of" 0.0-0.2, "Screenshot" 0.2-...: the
    voiced blip sat at 0.10, the S-hiss began at 0.20, the quiet dip between them at 0.15-0.2; a wider search cuts into the S)."""
    hop = SR // 100
    a, b = int((w0 + 0.6 * (w1 - w0)) * SR), int((nxt + 0.02) * SR)
    if b - a < hop:
        return 0
    xf = x[a:b].astype(np.float64) / 32768
    n = len(xf) // hop
    rms = np.sqrt((xf[: n * hop].reshape(n, hop) ** 2).mean(1)) if n else np.zeros(1)
    loud = np.sqrt(np.mean((x.astype(np.float64) / 32768) ** 2))
    if 20 * np.log10(rms.min() + 1e-12) > 20 * np.log10(loud + 1e-12) - 25:
        return 0  # no real pause between them: they may be one word Whisper split (a cut here takes half a word); leave it
    return a + int(np.argmin(rms)) * hop + hop // 2


def split_section(ctx, tcfg, x, beats, gaps=None, fillers=False):
    """One stretch of narration holding several beats -> one clip per beat, cut in the pause between each beat's last word and
    the next beat's first (quiet_cut; Whisper word times, matched to the script). fillers: cut_fillers first; gaps: tighten_gaps.
    -> (clips, seconds cut, fillers that couldn't be cut)."""
    from .captions import _key, heard_words, snap_to_script
    cut_s, stuck = 0.0, []
    if fillers:
        x, removed, found, stuck = cut_fillers(ctx, x, beats)
        if found:
            cut_s += sum(d for _, d in removed)
            print(f"  fillers cut: {', '.join(found)}")
    tmp = ctx.path("voice", "cache", "section_tmp.wav")
    write_wav(tmp, x)
    dur = len(x) / SR
    heard = heard_words(ctx.cfg, tmp)
    words = snap_to_script([{"id": b["id"], "voice": b["voice"], "start": 0.0, "voice_end": dur} for b in beats], heard)
    tmp.unlink()
    # a word the voice says before the section's first script word (a take that begins with an added "But"): cut off
    first_key = next((_key(w) for w in beats[0]["voice"].split() if _key(w)), "")
    k = next((i for i, h in enumerate(heard[:4]) if _key(h["w"]) == first_key), 0)
    # a real word only (>= 0.12 s): a 0.06 s "of" can be the onset of the first word ("Screenshot"), and cutting it leaves "Green Shot"
    lead = (heard[k - 1]["start"], heard[k - 1]["end"], heard[k]["start"]) if k > 0 and heard[k - 1]["end"] - heard[0]["start"] >= 0.12         else None
    if lead:
        print(f"  section starts with {' '.join(h['w'] for h in heard[:k])!r} before the script: cut")
    if gaps:  # breaths and dead air between words out (one flow); word times follow the cuts
        x, removed = tighten_gaps(x, words, gaps)
        words = [{**w, "start": remap(w["start"], removed), "end": remap(w["end"], removed)} for w in words]
        lead = lead and tuple(remap(t, removed) for t in lead)
        cut_s += sum(d for _, d in removed)
    first = {w["beat"]: w for w in reversed(words)}  # first word of each beat
    last = {w["beat"]: w for w in words}              # last word of each beat
    cuts = [lead_cut(x, *lead) if lead else 0]
    for a, b in zip(beats, beats[1:]):
        cuts.append(min(max(quiet_cut(x, last[a["id"]]["end"], first[b["id"]]["start"]), cuts[-1]), len(x)))
    cuts.append(len(x))
    return [x[cuts[k]:cuts[k + 1]] for k in range(len(beats))], cut_s, stuck


def syllables(text):
    """A rough syllable count of a script line (vowel groups; an ALL-CAPS abbreviation = one per letter, "FBI" 3; a year 4; "19th" 2).
    Only used for rates compared with each other (every sentence measured the same way)."""
    n = 0
    for w in text.split():
        t = w.strip(".,!?;:\"'()*")
        if re.fullmatch(r"[A-Z]{2,5}", t):
            n += len(t)
        elif re.fullmatch(r"\d{4}", t):
            n += 4
        elif re.fullmatch(r"\d+(st|nd|rd|th)", t):
            n += 2
        elif re.fullmatch(r"\d+", t):
            n += len(t)
        else:
            v = re.sub(r"[^a-z]", "", t.lower())
            k = len(re.findall(r"[aeiouy]+", v))
            if v.endswith("e") and k > 1 and not v.endswith(("le", "ee")):
                k -= 1
            n += max(k, 1)
    return n


def voiced_span(x, below_db=35.0):
    """Seconds from the first to the last 10 ms frame within below_db of the loudest (a clip's speech without its edge silence)."""
    n = len(x) // (SR // 100)
    if not n:
        return 0.0
    r = np.sqrt((x[: n * (SR // 100)].astype(np.float64).reshape(n, SR // 100) ** 2).mean(1)) + 1e-9
    on = np.flatnonzero(20 * np.log10(r / r.max()) > -below_db)
    return (on[-1] - on[0] + 1) / 100 if len(on) else 0.0


def close_gaps(x, over=0.16, keep=0.12, below_db=22.0):
    """Shorts talk without breaks (constant talking, no break between lines, and a hard word is no reason for a pause): every stretch
    quieter than
    below_db under the speech level (breaths count) that lasts longer than `over` s is cut to `keep` s from its middle, 5 ms fades.
    Word-internal closures (< 0.1 s) are untouched. -> (new samples, seconds removed)."""
    hop = SR // 100
    n = len(x) // hop
    if not n:
        return x, 0.0
    db = 20 * np.log10(np.sqrt((x[: n * hop].astype(np.float64).reshape(n, hop) ** 2).mean(1)) + 1e-9)
    speech = np.median(db[db > db.max() - 30]) if (db > db.max() - 30).any() else db.max()
    quiet = db < speech - below_db
    cuts, a = [], None
    for i, q in enumerate(list(quiet) + [False]):
        if q and a is None:
            a = i
        elif not q and a is not None:
            if a > 0 and i < n and (i - a) / 100 > over:  # inner gaps only (leading and trailing silence are trim_lead's and the layout's)
                mid, rm = (a + i) / 2 * hop, ((i - a) / 100 - keep) * SR
                cuts.append((int(mid - rm / 2), int(mid + rm / 2)))
            a = None
    if not cuts:
        return x, 0.0
    f = int(0.005 * SR)
    out, last = [], 0
    for c0, c1 in cuts:
        piece = x[last:c0].astype(np.float64)
        piece[-f:] *= np.linspace(1, 0, f)
        out.append(piece)
        last = c1
    out.append(x[last:].astype(np.float64))
    for k in range(1, len(out)):
        out[k][:f] *= np.linspace(0, 1, f)
    y = np.concatenate(out)
    return np.clip(np.round(y), -32768, 32767).astype(x.dtype), (len(x) - len(y)) / SR


def trim_lead(x, keep=0.02, below_db=35.0):
    """Silence before the first word out, keeping `keep` s, so the video says its first word at once (a take can begin with 0.4 s of
    room tone and a soft onset). The first 10 ms frame within below_db of the clip's loudest starts the voice."""
    n = len(x) // (SR // 100)
    if not n:
        return x
    r = np.sqrt((x[: n * (SR // 100)].astype(np.float64).reshape(n, SR // 100) ** 2).mean(1)) + 1e-9
    on = np.flatnonzero(20 * np.log10(r / r.max()) > -below_db)
    if not len(on):
        return x
    start = max(min(on[0] * (SR // 100) - int(keep * SR), sound_start(x, on[0] / 100, 0.0, reach=0.15)), 0)
    return x[start:]


def hook_tempo(ctx, tcfg, beats, clips):
    """Quick hooks: the first voiced beat, if it's spoken slower than [tts] hook_syl_s, is sped up to it with atempo (WSOLA:
    rubberband's phase vocoder makes the same speed-up sound robotic), at most hook_max_tempo. The rest of the take is untouched."""
    voiced = [i for i, b in enumerate(beats) if b.get("voice") and not b.get("hold")]
    if not tcfg.get("hook_syl_s", 0) or not voiced:
        return clips
    # [tts] tempo_all: every voiced beat at the hook's rate, each by its own factor; a beat already that fast is left alone. Applied
    # ONCE, to fresh takes: with tempo_share < 1 a beat never reaches the target, so a second pass speeds it again (rebuilding a
    # spliced narration_final would speed its old beats 2-4% on top); voice_patch.py gives its new takes their factor with beat_tempo
    # [tts] hook_like_rest: the hook gets the same share as the beats after it; with no tempo_all the rest keeps its own speed, so the
    # hook does too
    if tcfg.get("hook_like_rest", False) and not tcfg.get("tempo_all"):
        return clips
    out = list(clips)
    for k in (voiced if tcfg.get("tempo_all") else voiced[:1]):
        out[k] = beat_tempo(tcfg, beats[k]["voice"], clips[k], k == voiced[0], beats[k]["id"])
    return out


def beat_tempo(tcfg, text, x, hook, label):
    """One beat's speed-up under hook_tempo's rules (the hook or a later beat); the clip back, sped or as it was."""
    target, cap = tcfg.get("hook_syl_s", 0), tcfg.get("hook_max_tempo", 1.3)
    # [tts] tempo_share: the beats after the hook get this share of their speed-up (0.5: the rate halfway between the take's own and
    # the hook's); the hook keeps all of it, unless hook_like_rest
    share, like_rest = float(tcfg.get("tempo_share", 1.0)), bool(tcfg.get("hook_like_rest", False))
    dur = voiced_span(x)
    rate = syllables(text) / dur if dur else target
    if not target or rate >= target * 0.98:
        return x
    f = round(min(target / rate, cap), 3)
    if not hook or like_rest:
        f = round(1 + (f - 1) * share, 3)
        if f < 1.01:
            return x
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.wav", Path(d) / "b.wav"
        write_wav(a, x)
        ff(["-i", a, "-af", f"atempo={f}", "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", b])
        y = read_wav(b)
    print(f"  tempo ({label}): {rate:.1f} syl/s -> atempo {f} -> {rate * f:.1f} syl/s")
    return y


def all_tempo(tcfg, beats, clips):
    """[tts] tempo: one speed for every voiced beat (1.04x in the template), atempo (WSOLA) per beat; holds keep their length (the
    real voices in them are timed to it). Applied once, to freshly voiced takes: a narration_final (a splice of the pipeline's own)
    is built from the narration that already has it, and voice_patch.py speeds its new takes the same way before splicing."""
    f = float(tcfg.get("tempo", 1.0))
    if abs(f - 1.0) < 1e-3:
        return clips
    out = list(clips)
    for k, (b, c) in enumerate(zip(beats, clips)):
        if not b.get("voice") or b.get("hold") or not len(c):
            continue
        with tempfile.TemporaryDirectory() as d:
            a_, b_ = Path(d) / "a.wav", Path(d) / "b.wav"
            write_wav(a_, c)
            ff(["-i", a_, "-af", f"atempo={f}", "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", b_])
            out[k] = read_wav(b_)
    print(f"  tempo: every voiced beat at {f}x")
    return out


FINAL_EXT = (".wav", ".flac", ".mp3", ".m4a", ".aac")


def final_narration(ctx):
    """A polished narration (the creator's own edit, or a splice of the pipeline's): narration_final.<wav|flac|mp3|m4a|aac> next to
    the build folder (VIDEOS/<video>/) or in the script's folder."""
    name = ctx.cfg["tts"].get("final_name", "narration_final")
    return next((d / f"{name}{e}" for d in dict.fromkeys([ctx.build.parent, ctx.video]) for e in FINAL_EXT
                 if (d / f"{name}{e}").exists()), None)


def from_final(ctx, tcfg, beats, src):
    """Use the polished narration as it is (no tightening: a hand edit is final) and cut it into beats."""
    wav = ctx.path("voice", "cache", "final_48k.wav")
    to_wav(src, wav)
    x = read_wav(wav)
    if ctx.fmt == "short" and tcfg.get("final_close_gaps", False):  # the pipeline's spliced narrations (script CONFIG: tts.final_close_gaps=true); a hand-polished one stays as it is
        x, cut = close_gaps(x)
        if cut:
            print(f"  gaps closed: {cut:.2f} s")
    # the pipeline's own splice (voice_patch.py) knows its beat boundaries: cut exactly there (a Whisper split of a 20-min splice put 4
    # of 131 cuts inside a word); a hand edit has none and is cut by Whisper
    side = src.with_name(src.stem + ".beats.json")
    if side.exists():
        m = json.loads(side.read_text(encoding="utf-8"))
        if [r["id"] for r in m["beats"]] == [b["id"] for b in beats] and m.get("sr") == SR and abs(m["beats"][-1]["b"] - len(x)) <= 1:
            print(f"  {src.name}: a pipeline splice, cut at its own beat boundaries ({side.name})")
            return [x[r["a"]:r["b"]] for r in m["beats"]], [0.0] * len(beats)
        print(f"  {side.name} doesn't match the script's beats or the file: cutting by Whisper")
    clips, _, _ = split_section(ctx, tcfg, x, beats)
    print(f"  {src.name}: a hand-polished narration, {len(beats)} beats")
    return clips, [0.0] * len(beats)


ELEVENLABS_KEY_FILE = SECRETS / "elevenlabs_api_key.txt"  # outside the repo, in the media root's secrets/ (the setup has the creator paste it)


def elevenlabs_key():
    """The API key: the ELEVENLABS_API_KEY env var, else the key file outside the repo. Never printed, never committed."""
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key and ELEVENLABS_KEY_FILE.exists():  # the file may hold notes around the key: take the sk_ token
        found = re.findall(r"\bsk_[A-Za-z0-9]{20,}\b", ELEVENLABS_KEY_FILE.read_text(encoding="utf-8-sig", errors="replace"))
        key = found[0] if found else ""
    if not key:
        raise SystemExit(f"no ElevenLabs key: set ELEVENLABS_API_KEY or paste it into {ELEVENLABS_KEY_FILE} (never commit it)")
    return key


ELEVENLABS_USAGE = MEDIA / "voice" / "elevenlabs_usage.csv"  # every call: what it cost (no secrets)


def require_voice_tts(tcfg):
    """core.require_voice on a [tts] table alone (the voice tools pass tcfg around): stops with a clear message while the voice is unset."""
    require_voice({"tts": tcfg})


def elevenlabs(tcfg, text, prev, nxt, out, prev_ids=None):
    """POST /v1/text-to-speech/{voice_id}/with-timestamps -> (char alignment, request id). Writes `out` as 48 kHz mono 16-bit WAV
    (wav_48000 works on the Creator plan, tested). prev_ids: the request ids of the sections before (long videos), for continuity; otherwise
    previous/next text. Every call is logged to MEDIA/voice/elevenlabs_usage.csv with the character-cost header."""
    require_voice_tts({**tcfg, "engine": "elevenlabs"})
    key = elevenlabs_key()
    e = tcfg["elevenlabs"]
    fmt = e.get("output_format", "wav_48000")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{e['voice_id']}/with-timestamps?output_format={fmt}"
    # [tts.elevenlabs] prefix: a direction tag sent at the head of every request ("[flat, calm, even tone] [American accent] " in the
    # template); the model doesn't speak it, and its characters are cut from the timestamps below, so callers see their own text
    prefix = e.get("prefix", "")
    body = {"text": prefix + text, "model_id": e["model_id"], "voice_settings": e.get("voice_settings", {})}
    if prev_ids:
        body["previous_request_ids"] = list(prev_ids)[-3:]
    elif e.get("stitch", True):  # previous/next text give smoother prosody across beats
        body.update({k: v for k, v in (("previous_text", prev), ("next_text", nxt)) if v})
    # a request with nothing before it starts cold, low and breathy (a tired, whispery opening). Unspoken context lifts it: measured
    # on two opening lines, 3 seeds each, the first sentence's pitch 117 -> 125 Hz and its CPPS 8.70 -> 9.24
    if "previous_request_ids" not in body and "previous_text" not in body and e.get("lead_in"):
        body["previous_text"] = e["lead_in"]
    if "seed" in e:
        body["seed"] = e["seed"]
    # the voice lock's name tests (standard/VOICE_LOCK.md): both off unless [tts.elevenlabs] or a tool sets them
    if e.get("language_code"):            # forces the language of the model and its text normaliser (ISO 639-1)
        body["language_code"] = e["language_code"]
    if e.get("pronunciation_dictionaries"):   # [{"id", "version"}]: ElevenLabs' alias/phoneme rules, up to 3, applied in order
        body["pronunciation_dictionary_locators"] = [
            {"pronunciation_dictionary_id": d["id"], **({"version_id": d["version"]} if d.get("version") else {})}
            for d in e["pronunciation_dictionaries"][:3]]
    for attempt in range(5):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"xi-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                hdr = {k.lower(): v for k, v in r.headers.items()}
                resp = json.load(r)
            break
        except urllib.error.HTTPError as err:
            msg = err.read().decode(errors="replace")[:500]
            if err.code in (429, 500, 502, 503, 504) and attempt < 4:
                print(f"  ElevenLabs {err.code}, retrying in {3 * 2 ** attempt} s")
                time.sleep(3 * 2 ** attempt)
                continue
            raise SystemExit(f"ElevenLabs error {err.code}: {msg}")
    audio = base64.b64decode(resp["audio_base64"])
    if fmt.startswith("pcm_"):  # raw 16-bit little-endian mono at the rate in the format's name
        src = out.with_suffix(".src.pcm")
        src.write_bytes(audio)
        ff(["-f", "s16le", "-ar", int(fmt.split("_")[1]), "-ac", 1, "-i", src, "-ac", 1, "-ar", SR, "-c:a", "pcm_s16le", out])
    else:
        src = out.with_suffix(".src." + {"wav": "wav", "mp3": "mp3", "opus": "opus"}.get(fmt.split("_")[0], "bin"))
        src.write_bytes(audio)
        to_wav(src, out)
    src.unlink()
    ELEVENLABS_USAGE.parent.mkdir(parents=True, exist_ok=True)
    new = not ELEVENLABS_USAGE.exists()
    with open(ELEVENLABS_USAGE, "a", encoding="utf-8") as f:
        if new:
            f.write("time,model,voice_id,characters,character_cost,request_id,text_start\n")
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{e['model_id']},{e['voice_id']},{len(text)},{hdr.get('character-cost', '')},"
                f"{hdr.get('request-id', '')},\"{text[:40].replace(chr(34), chr(39))}\"\n")
    al = resp.get("alignment") or resp.get("normalized_alignment")
    if prefix and al and "".join(al["characters"][:len(prefix)]) == prefix:
        al = {k: v[len(prefix):] for k, v in al.items()}
    return al, hdr.get("request-id")


def continuous_elevenlabs(tcfg, beats, cache, breaks=()):
    """ElevenLabs in one go (per-beat requests joined with gaps give tone and speed jumps): one
    request per section (a whole Short; long videos: sections of section_words, each linked to the ones before by request id), cut back
    into beats at each beat's first and last character (the returned timestamps, no Whisper). A beat keeps its speech plus a gap by its
    last punctuation ([tts] gaps); pauses inside it longer than max_pause are tightened, except the pause a written "..." asks for
    (comic timing, kept up to 0.5 s). Returns (clips, pads)."""
    V = [voice_text(tcfg, b["voice"]) for b in beats]   # the respelled names go to the voice; the cut back into beats follows the same text
    groups = section_groups(V, breaks, tcfg.get("section_words", 150))
    gaps = tcfg.get("gaps") or {"sentence": 0.12, "comma": 0.07, "word": 0.04}
    clips, pads, prev_ids = [None] * len(beats), [0.0] * len(beats), []
    # a section linked only by request ids starts cold (breathy and tired at every section start). Each section after the first is
    # voiced with the `section_before` lines before it inside the same request (the lines-before way, standard/VOICE_LOCK.md), then those
    # lines are cut away; no previous_text, so the house lead_in opens it.
    before_n = int(tcfg.get("section_before", 2))
    for k, g in enumerate(groups, 1):
        if beats[g[0]]["id"] in set(tcfg.get("fresh_at", [])):
            prev_ids = []  # a fresh request: nothing before it carries over (fresh_at, above)
        parts = [V[i].strip() for i in g]
        text = " ".join(parts)
        lead = " ".join(V[i].strip() for i in range(max(0, g[0] - before_n), g[0])) if before_n and g[0] else ""
        sent = f"{lead} {text}" if lead else text
        key = cache_key(tcfg, sent)
        wav, aj = cache / f"sec_{key}.wav", cache / f"sec_{key}.align.json"
        if wav.exists() and aj.exists():
            meta = json.loads(aj.read_text(encoding="utf-8"))
            print(f"  section {k}: cached")
        else:
            al, rid = elevenlabs(tcfg, sent, None, None, wav, prev_ids=None if lead else prev_ids)
            meta = {"alignment": al, "request_id": rid, "text": sent, "lead": len(lead) + 1 if lead else 0}
            aj.write_text(json.dumps(meta), encoding="utf-8")
            print(f"  section {k}: {len(text)} characters (+{len(lead)} of the lines before, cut away), ElevenLabs "
                  f"{tcfg['elevenlabs']['model_id']}")
        if meta.get("request_id"):
            prev_ids.append(meta["request_id"])
        off = meta.get("lead", 0)   # where this section's own text starts in the request
        al = meta["alignment"]
        st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
        if "".join(al["characters"]) != sent:
            raise SystemExit(f"section {k}: the timestamps don't spell the text that was sent")
        x = read_wav(wav)
        for word, t, under in swallowed(x, al):
            print(f"  ! {word!r} at {t:.2f} s: its last consonant is {under:.0f} dB under the take's others (a re-take candidate)")
        xdb = frame_db(x)
        floor = quiet_floor(xdb)
        # the cuts between this section's beats: the real pause between each beat's last word and the next beat's first (gap_between)
        spans, pos = [], off
        for p in parts:
            spans.append((pos, pos + len(p)))
            pos += len(p) + 1
        def last_word_start(j):  # the previous beat's last word: its first letter's start time
            p = parts[j].rstrip()
            k = max(p.rfind(" "), 0)
            return st[spans[j][0] + (k + 1 if k else 0)]
        inner = [gap_between(xdb, floor, en[spans[j][1] - 1], st[spans[j + 1][0]], last_word_start(j)) for j in range(len(parts) - 1)]
        pos = off
        for j, (i, p) in enumerate(zip(g, parts)):
            a, b = pos, pos + len(p)  # this beat's characters
            pos = b + 1
            # the cut sits where the sound really starts / stops (the character times lag the audio)
            prev_end = en[a - 2] if (j or off) else 0.0
            nxt_start = st[pos] if j + 1 < len(parts) else len(x) / SR
            if j:
                s = inner[j - 1][1] / SR
            elif off:  # after the lines before (cut away): the real pause between their last word and this section's first
                lead_last = sent[:off - 1].rfind(" ") + 1   # the lines before: their last word's first character
                s = gap_between(xdb, floor, en[off - 2], st[off], st[lead_last])[1] / SR
            else:  # the section's first beat: where the take's sound starts (the tag's offset can put st[a] ~1 s late: first_sound)
                s0 = sound_start(x, st[a], prev_end, xdb, floor)
                f0 = first_sound(xdb, floor, int(st[a] * SR) // EDGE_HOP + 2)
                s = (min(s0, f0) if f0 is not None else s0) / SR
            e = (inner[j][0] / SR) if j + 1 < len(parts) else sound_end(x, en[b - 1], nxt_start, xdb, floor) / SR
            keep = []  # the pauses a written "..." asks for, as sample ranges inside this beat
            for m in re.finditer(r"\.\.\.|…", p):
                c0 = a + m.start() - 1
                while c0 > a and not p[c0 - a].isalnum():
                    c0 -= 1
                c1 = a + m.end()
                while c1 < b and not p[c1 - a].isalnum():
                    c1 += 1
                if c1 < b:
                    p0, p1 = en[c0], st[c1]
                    keep.append((int((p0 - s) * SR), int((min(p1, p0 + 0.5) - s) * SR), int((p1 - s) * SR)))
            seg, out, prev = x[int(s * SR): int(e * SR)], [], 0
            for k0, k1, k2 in keep:  # tighten around the kept pause, keep up to 0.5 s of it
                out += [tighten_pauses(seg[prev:k0], tcfg.get("max_pause", 0)), seg[k0:k1]]
                prev = k2
            seg = np.concatenate(out + [tighten_pauses(seg[prev:], tcfg.get("max_pause", 0))])
            fl = min(int(0.005 * SR), len(seg))
            seg = seg.copy()
            seg[:fl] = (seg[:fl] * np.linspace(0, 1, fl)).astype(seg.dtype)  # both cuts are in silence now: 5 ms against a click
            seg[-fl:] = (seg[-fl:] * np.linspace(1, 0, fl)).astype(seg.dtype)
            last = p.rstrip().rstrip("\"')")[-1:]
            gap = gaps["sentence"] if last in ".?!…" else gaps["comma"] if last in ",;:" else gaps["word"]
            clips[i] = np.concatenate([seg, np.zeros(int(gap * SR), np.int16)])
    print(f"  continuous: {len(beats)} beats in {len(groups)} ElevenLabs section(s)")
    return clips, pads


def clean_ends(x, merge=0.10, min_run=0.15, rel_db=-35.0, lead_words=True):
    """Mute lone sounds before a beat's first and after its last stretch of speech: a click or a stray consonant that a split or
    a splice left at the edge of a beat (an "ick" 1 s after the last word: the old take's final consonant that landed at the start of
    the next beat). Speech = voiced 10 ms frames (within 35 dB of the beat's peak) in runs of at least 0.15 s, with gaps under 0.10 s
    bridged; anything outside the first..last such run (plus 30/60 ms) is muted. lead_words=False: a short sound before the speech is
    muted even when it looks like a word ([tts] lead_click: a sound that is heard as a click)."""
    hop = SR // 100
    n = len(x) // hop
    if n < 5:
        return x
    xf = x[: n * hop].astype(np.float64).reshape(n, hop) / 32768
    db = 20 * np.log10(np.sqrt((xf ** 2).mean(1)) + 1e-12)
    on = db > db.max() + rel_db
    k = 0
    while k < n:  # bridge short gaps
        if not on[k]:
            j = k
            while j < n and not on[j]:
                j += 1
            if 0 < k and j < n and (j - k) * hop / SR < merge:
                on[k:j] = True
            k = j
        else:
            k += 1
    runs, k = [], 0
    while k < n:
        if on[k]:
            j = k
            while j < n and on[j]:
                j += 1
            if (j - k) * hop / SR >= min_run:
                runs.append((k, j))
            k = j
        else:
            k += 1
    if not runs:
        return x
    # a short word right next to the speech is a word, not a stray sound: a quick "And" before the next word (0.12 s, then a 0.11-s
    # gap) or a rising loop "that" falls under min_run and would be muted. So a shorter run stays when it is at least 50 ms long,
    # within 25 dB of the beat's peak and within 0.30 s of the speech; a lone click or a stray consonant a second away is still muted.
    allruns, k = [], 0
    while k < n:
        if on[k]:
            j = k
            while j < n and on[j]:
                j += 1
            allruns.append((k, j))
            k = j
        else:
            k += 1
    peak = db.max()
    word = lambda r: (r[1] - r[0]) * hop / SR >= 0.05 and db[r[0]:r[1]].max() >= peak - 25  # noqa: E731
    s0, s1 = runs[0][0], runs[-1][1]
    for r in reversed([r for r in allruns if r[1] <= s0] if lead_words else []):
        if (s0 - r[1]) * hop / SR <= 0.30 and word(r):
            s0 = r[0]
        else:
            break
    for r in [r for r in allruns if r[0] >= s1]:
        if (r[0] - s1) * hop / SR <= 0.30 and word(r):
            s1 = r[1]
        else:
            break
    runs = [(s0, runs[0][1])] + runs[1:-1] + [(runs[-1][0] if len(runs) > 1 else s0, s1)] if len(runs) > 1 else [(s0, s1)]
    edb = frame_db(x)  # from the speech runs out to where the sound really starts / dies (a fixed 30 ms clipped soft onsets)
    a = sound_start(x, runs[0][0] * hop / SR, 0.0, edb, reach=0.15)
    b = sound_end(x, runs[-1][1] * hop / SR, len(x) / SR, edb, reach=0.3)
    y = x.copy()
    y[:a] = 0
    y[b:] = 0
    f = int(0.005 * SR)
    if a > 0:
        y[a:a + f] = (y[a:a + f] * np.linspace(0, 1, len(y[a:a + f]))).astype(y.dtype)
    if b < len(y):
        y[max(b - f, 0):b] = (y[max(b - f, 0):b] * np.linspace(1, 0, len(y[max(b - f, 0):b]))).astype(y.dtype)
    return y


def tight_beats(tcfg, beats, clips):
    """Shorts talk without a break between sections: the voice runs on continuously through the whole Short (left alone, the beats
    keep 0.22-0.50 s of silence, a muted breath after each last word). Every voiced beat starts on its first sound and keeps only its punctuation gap after its last one ([tts]
    gaps, the same pause as between two sentences inside a beat). Only digital silence is cut (clean_ends' muted edges), never a sound."""
    gaps = tcfg.get("gaps") or {"sentence": 0.12, "comma": 0.07, "word": 0.04}
    voiced = [i for i, b in enumerate(beats) if b.get("voice") and not b.get("hold")]
    out, cut = list(clips), 0.0
    for i in voiced:
        c = clips[i]
        nz = np.flatnonzero(c)
        if not len(nz):
            continue
        last = beats[i]["voice"].rstrip().rstrip("\"')")[-1:]
        gap = 0.0 if i == voiced[-1] else gaps["sentence"] if last in ".?!…" else gaps["comma"] if last in ",;:" else gaps["word"]
        a = nz[0] if i != voiced[0] else 0  # the first beat's lead is trim_lead's
        b = min(len(c), nz[-1] + 1 + int(gap * SR))
        out[i] = np.concatenate([c[a:b], np.zeros(max(0, nz[-1] + 1 + int(gap * SR) - len(c)), c.dtype)])
        cut += (len(c) - len(out[i])) / SR
    print(f"  beats tightened: {cut:.2f} s of silence between sections cut")
    return out


def voiced_db(x, rel_db=-30.0):
    hop = SR // 100
    n = len(x) // hop
    if n == 0:
        return None
    xf = x[: n * hop].astype(np.float64).reshape(n, hop) / 32768
    r = np.sqrt((xf ** 2).mean(1))
    db = 20 * np.log10(r + 1e-12)
    v = r[db > db.max() + rel_db]
    return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-12) if len(v) else None


def lookahead_limit(xf, ceil=0.891 * 32767):
    """Peaks over the ceiling (-1 dBFS) brought under it by a look-ahead gain (the lowest gain needed in a 9-ms window, smoothed): the
    level stays and nothing is flattened. voice_patch.limit's method; level_beats needs it too (a hard clip at full scale leaves
    flat-topped words that are heard to peak)."""
    a = np.abs(xf) if xf.ndim == 1 else np.abs(xf).max(axis=1)
    g = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    w = 2 * int(0.004 * SR) + 1
    p = w // 2
    g = np.lib.stride_tricks.sliding_window_view(np.pad(g, p, mode="edge"), w).min(axis=-1)
    c = np.cumsum(np.insert(np.pad(g, p, mode="edge"), 0, 0.0))
    g = (c[w:] - c[:-w]) / w
    return xf * (g if xf.ndim == 1 else g[:, None])


def level_beats(clips, max_db=6.0):
    """Every beat at the same voiced level (the median of the beats): takes from different requests, or a patched line, came out
    up to 2.5 dB apart, and the loud ones sound almost piercing (the whole video should sit at one even level)."""
    levels = [voiced_db(c) if c is not None and len(c) and np.abs(c).max() > 0 else None for c in clips]
    have = [v for v in levels if v is not None]
    if len(have) < 2:
        return clips
    target = float(np.median(have))
    out = []
    for c, v in zip(clips, levels):
        if v is None:
            out.append(c)
            continue
        g = 10 ** (float(np.clip(target - v, -max_db, max_db)) / 20)
        y = c.astype(np.float64) * g
        if float(np.abs(y).max()) > 0.891 * 32767:  # never by clipping (lookahead_limit)
            y = lookahead_limit(y)
        out.append(np.clip(np.round(y), -32768, 32767).astype(np.int16))
    print("  beats levelled to %.1f dB (they ranged %.1f to %.1f)" % (target, min(have), max(have)))
    return out


def normalize(ctx, src, dst):
    """To the configured loudness (default -14 LUFS) with one gain, the peaks over the true-peak target (-1.5) caught by a look-ahead limit;
    [audio] loudnorm_dynamic = true is the old two-pass loudnorm (it flattened peaks, see below). [tts] deess > 0 runs ffmpeg's de-esser
    first (the 4-8 kHz "s" band is 5-10 dB stronger on lines that sound piercing than on a pleasant one)."""
    a = ctx.cfg["audio"]
    I, TP, LRA = a["loudness"], a["true_peak"], a["lra"]
    de = float(ctx.cfg["tts"].get("deess", 0) or 0)
    if de > 0:
        tmp = Path(str(dst) + ".deess.wav")
        ff(["-i", src, "-af", f"deesser=i={de}:m=0.5:f=0.5", "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", tmp])
        src = tmp
    if a.get("voice_chain") == "multiband":
        # the one-gain-and-9-ms-limiter way to -14 LUFS crunches an ElevenLabs voice (raw takes peak 21-22 dB over their loudness:
        # it sounds gained up and hurts the ears); the multiband chain D is the one picked by ear: tools/sound/voice_level.py
        # --chain mb, run in the editing venv (scipy, pyloudnorm). The narration must reach here unlimited (raw_rebuild.py, low working level)
        py = a.get("chain_python", str(PY_EDIT))
        tool = TOOLS / "sound" / "voice_level.py"
        subprocess.run([py, str(tool), str(src), str(dst), "--chain", "mb", "--lufs", str(I), "--ceil", str(TP)], check=True)
        return
    m = loudness(src, I, TP, LRA)
    if m["input_i"] in ("-inf", "inf"):
        ctx.warn("narration is silent; loudness normalization skipped")
        ff(["-i", src, "-c:a", "pcm_s16le", dst])
        return
    if not a.get("loudnorm_dynamic", False):
        # one gain to the target, then the look-ahead limit at the true-peak target. loudnorm's linear=true falls back to its dynamic
        # mode whenever the gain would push a peak past TP (any narration with a peak near full scale), and that mode's limiter
        # flattens the peaks (a long narration came out with 98 flat-topped words at -1.5 dBFS, heard as peaking)
        g = I - float(m["input_i"])
        x = lookahead_limit(read_wav(src).astype(np.float64) * 10 ** (g / 20), ceil=10 ** (TP / 20) * 32767)
        write_wav(dst, np.clip(np.round(x), -32768, 32767).astype(np.int16))
        print(f"  loudness {float(m['input_i']):.1f} -> {I} LUFS (one gain, {g:+.1f} dB; peaks over {TP} dBFS by a look-ahead limit)")
        return
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    ff(["-i", src, "-af", af, "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", dst])
    print(f"  loudness {float(m['input_i']):.1f} -> {I} LUFS")


def looping(ctx):
    """Shorts loop (the last sentence runs into the first): nothing may signal an ending."""
    return ctx.fmt == "short" and ctx.cfg["video"].get("short_loop", False)


def run(ctx):
    if not final_narration(ctx):  # the voice must be set in config/tts.toml (the dummy engine and a polished narration need none)
        require_voice(ctx.cfg)
    __import__("sys").path.insert(0, str(TOOLS / "voice"))  # the voice lock (standard/VOICE_LOCK.md)
    __import__("voice_lock").guard_video(ctx.video, "dj tts")  # a locked narration is changed only by voice_layin.py
    __import__("voice_ready").require(ctx.video, "dj tts")  # stage 0: facts, cold read, bites, names stamped on this script
    meta = script.load(ctx)
    for w in meta["warnings"]:
        ctx.warn(w)
    all_beats, tcfg = meta["beats"], ctx.cfg["tts"]
    # HOLD beats (a comedic pause: no voice, their own shots and sound) get silence; the voice is made for the others, and the voice
    # sections break at each hold (the voice stops there anyway) and, in long videos, at each chapter
    beats = [b for b in all_beats if not b.get("hold")]
    breaks = {i for i, b in enumerate(beats) if i and ((all_beats[all_beats.index(b) - 1].get("hold") and
                                                        not all_beats[all_beats.index(b) - 1].get("join")) or
                                                         (ctx.fmt != "short" and (b.get("vis") or {}).get("chapter")))}
    # [tts] fresh_at = ["S03"]: a new voice request starts at these beats, without a pause and not linked to the requests before
    # (a place name said early in a request can turn every line after it British, measured with rhotic.py, while the same lines voiced
    # on their own stay American: the fresh request keeps the accent of the line before from carrying over)
    fresh = set(ctx.cfg["tts"].get("fresh_at", []))
    breaks |= {i for i, b in enumerate(beats) if i and b["id"] in fresh}
    eng = tcfg["engine"]
    cache = ctx.path("voice", "cache", "x").parent
    say = [speakable(tcfg, b["voice"]) if eng == "command" else b["voice"] for b in beats]  # what the local engine is sent
    pads = None  # continuous mode: per-beat pauses come from the audio itself
    final = final_narration(ctx)
    if not final:   # a narration built from the generation has no patched beat (voice_patch's record; a stale one makes the voice
        (ctx.build / "voice" / "patch" / "used.json").unlink(missing_ok=True)   # guard flag beats a later run dropped as "a patch")
    if final:
        clips, pads = from_final(ctx, tcfg, beats, final)
        aligns, eng = [None] * len(beats), "final"
    elif eng == "command" and tcfg.get("mode") == "continuous":
        if not is_batch(tcfg):
            raise SystemExit("[tts] mode = \"continuous\" needs a batch template (a list with {manifest})")
        clips, pads = continuous(ctx, tcfg, beats, say, cache, breaks)
        aligns = [None] * len(beats)
    elif eng == "elevenlabs" and tcfg.get("mode") == "continuous":
        clips, pads = continuous_elevenlabs(tcfg, beats, cache, breaks)
        aligns = [None] * len(beats)
    elif eng == "command" and is_batch(tcfg):
        todo = {}
        for s in say:
            wav = cache / f"{cache_key(tcfg, s)}.wav"
            if not wav.exists():
                todo[wav] = s  # same text twice = one render (same cache key)
        if todo:
            print(f"  {len(todo)} beat(s): command, batch")
            command_batch(tcfg, [(text, wav) for wav, text in todo.items()])
    if pads is None:
        clips, aligns = [], []
    for i, b in enumerate(beats if pads is None else []):
        key = cache_key(tcfg, say[i])
        wav, aj = cache / f"{key}.wav", cache / f"{key}.align.json"
        if wav.exists():
            print(f"  {b['id']}: cached")
        else:
            print(f"  {b['id']}: {eng}")
            if eng == "dummy":
                dummy(b["voice"], tcfg["wpm"], wav)
            elif eng == "command":
                command(tcfg, say[i], wav)
            elif eng == "elevenlabs":
                prev = beats[i - 1]["voice"] if i else None
                nxt = beats[i + 1]["voice"] if i + 1 < len(beats) else None
                al, _ = elevenlabs(tcfg, voice_text(tcfg, b["voice"]), prev, nxt, wav)
                if al:
                    aj.write_text(json.dumps(al))
            else:
                raise SystemExit(f"unknown tts.engine '{eng}'")
        clips.append(read_wav(wav))
        aligns.append(str(aj) if aj.exists() else None)

    if len(beats) != len(all_beats):  # put the holds back: silence for their length, no gap after them
        by_id = {b["id"]: (c, a, (pads[i] if pads else None)) for i, (b, c, a) in enumerate(zip(beats, clips, aligns))}
        clips, aligns, new_pads = [], [], []
        for b in all_beats:
            if b.get("hold"):
                clips.append(np.zeros(int(round(b["hold"] * SR)), np.int16))
                aligns.append(None)
                new_pads.append(0.0)
            else:
                c, a, pd = by_id[b["id"]]
                clips.append(c)
                aligns.append(a)
                new_pads.append(tcfg["gap"] if pd is None else pd)
        pads = new_pads
    beats = all_beats

    ours = eng != "final" or tcfg.get("final_ours")  # tts.final_ours: narration_final is the pipeline's own splice (voice_patch), not a hand edit
    if ours and not final:  # a hand-polished narration is final; a narration_final (a pipeline splice) already runs at [tts] tempo
        # and the Shorts' speed: voice_patch gives its new takes both (a second hook_tempo pass would speed its old beats again)
        clips = hook_tempo(ctx, tcfg, beats, clips)
        clips = all_tempo(tcfg, beats, clips)
    if tcfg.get("clean_ends", True):
        click = set(tcfg.get("lead_click", []))  # beats whose short sound before the first word is heard as a click: muted
        clips = [clean_ends(c, lead_words=b["id"] not in click) if b.get("voice") and not b.get("hold") and len(c) else c
                 for b, c in zip(beats, clips)]
    if tcfg.get("level_beats", True):
        lev = level_beats([c if b.get("voice") and not b.get("hold") else None for b, c in zip(beats, clips)])
        clips = [lv if lv is not None else c for lv, c in zip(lev, clips)]  # holds keep their silence
    k0 = next((i for i, b in enumerate(beats) if b.get("voice") and not b.get("hold")), None)
    if k0 is not None:  # every video starts on its first word (the loop's first frame included)
        clips = clips[:k0] + [trim_lead(clips[k0])] + clips[k0 + 1:]
    if tcfg.get("tight_beats", ctx.fmt == "short"):
        clips = tight_beats(tcfg, beats, clips)
    if ours and tcfg.get("edge_check", True):  # no beat may start or end mid-sound (a clipped consonant never reaches the video)
        bad = [f"{b['id']} {', '.join(f)}" for b, c in zip(beats, clips) if b.get("voice") and not b.get("hold")
               for f in [edge_faults(c)] if f]
        if bad:
            raise SystemExit("beats cut mid-sound (a consonant clipped): " + "; ".join(bad) +
                             "\n  rebuild the narration from the takes (dj tts without narration_final, then voice_patch) or fix the cut")
    # Frame-aligned layout: each beat's slot = its audio + gap (tail for the last), rounded up to whole frames.
    spf = SR * ctx.fd[0] / ctx.fd[1]  # samples per frame
    out, start_f = [], 0
    for i, (b, clip) in enumerate(zip(beats, clips)):
        dur = len(clip) / SR
        tail = ctx.cfg["video"].get("loop_tail", 0.1) if looping(ctx) else tcfg["tail"]
        pad = tail if i == len(beats) - 1 else (pads[i] if pads else tcfg["gap"])
        n = ctx.frames(dur + pad)
        out.append({"id": b["id"], "voice": b["voice"], "start_f": start_f, "frames": n,
                    "start": round(ctx.sec(start_f), 4), "voice_end": round(ctx.sec(start_f) + dur, 4),
                    "end": round(ctx.sec(start_f + n), 4), "align": aligns[i]})
        start_f += n
    total = round(start_f * spf)
    nar = np.zeros(total, np.int16)
    for o, clip in zip(out, clips):
        s = round(o["start_f"] * spf)
        nar[s:s + len(clip)] = clip
    raw, norm = ctx.path("voice", "narration_raw.wav"), ctx.path("voice", "narration.wav")
    write_wav(raw, nar)
    normalize(ctx, raw, norm)
    nar = read_wav(norm)
    nar = np.pad(nar, (0, max(0, total - len(nar))))[:total]
    write_wav(norm, nar)
    for o in out:  # per-beat slices of the normalized narration, for the editor timeline
        a, b = round(o["start_f"] * spf), round((o["start_f"] + o["frames"]) * spf)
        o["wav"] = str(ctx.path("voice", f"{o['id']}.wav"))
        write_wav(o["wav"], nar[a:b])
    ctx.save_json("beats.json", {"engine": eng, "format": ctx.fmt, "fps": ctx.rate, "total_frames": start_f,
                                 "duration": round(ctx.sec(start_f), 3), "narration": str(norm), "beats": out})
    print(f"  narration {ctx.sec(start_f):.2f} s -> {norm}")
