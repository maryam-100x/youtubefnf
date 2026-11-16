"""Word timings (align | whisper | even) -> captions.srt (long-form upload) + chunks.srt (1-3 word burn-in style).

  cd tools && PIPE -m dj captions ../videos/<video>     -> build/captions/words.json, captions.srt, chunks.srt

whisper (the default): faster-whisper hears the narration, its words are lined up with the script (the script's spelling where the
same word was said), and every place the voice said something else is reported in build/warnings.txt. Words Whisper spells wrong
although the voice said them right go in script.md's `## Caption fixes`."""
import difflib
import json
import os
import re
import subprocess
from pathlib import Path

from . import script
from .core import TOOLS, ffmpeg_bin, file_sig

PUNCT_BREAK = ",.?!…:;"


def words_even(beats):
    """Spread each beat's words over its voiced duration, weighted by character length. Always works."""
    out = []
    for b in beats:
        ws = b["voice"].split()
        wts = [len(w) + 1 for w in ws]
        t, span = b["start"], b["voice_end"] - b["start"]
        emph = b.get("emph") or [None] * len(ws)
        for w, wt, e in zip(ws, wts, emph):
            d = span * wt / sum(wts)
            out.append({"w": w, "start": round(t, 3), "end": round(t + d, 3), "beat": b["id"], "emph": e})
            t += d
    return out


def words_align(ctx, beats):
    """ElevenLabs character alignment -> words. Beats without alignment fall back to `even`."""
    out = []
    for b in beats:
        if not b.get("align") or not Path(b["align"]).exists():
            ctx.warn(f"{b['id']}: no character alignment, using even timing")
            out += words_even([b])
            continue
        al = json.loads(Path(b["align"]).read_text())
        cur = None
        for ch, s, e in zip(al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]):
            if ch.isspace():
                cur = None
                continue
            if cur is None:
                cur = {"w": "", "start": round(b["start"] + s, 3), "beat": b["id"]}
                out.append(cur)
            cur["w"] += ch
            cur["end"] = round(b["start"] + e, 3)
    return out


_WHISPER = {}


FILLER_PROMPT = "Umm, let me think like, hmm... Okay, here's what I'm, like, thinking."  # makes Whisper write fillers out


def heard_words(cfg, wav, prompt=None, repair=True):
    """faster-whisper word timestamps [{w, start, end}] (model cached per process). On Windows the CUDA DLLs come from the
    pip packages nvidia-cublas-cu12 / nvidia-cudnn-cu12; they go on PATH before ctranslate2 loads.
    Whisper leaves out "um"/"uh" by default (an "Umm" at a line's start is folded into the next word); prompt=FILLER_PROMPT
    writes them out (and may spell numbers differently, so use it only to find fillers)."""
    w = cfg["captions"]["whisper"]
    if "m" not in _WHISPER:
        if os.name == "nt":
            try:
                import nvidia
                for sub in ("cublas", "cudnn", "cuda_nvrtc"):
                    os.environ["PATH"] = os.path.join(nvidia.__path__[0], sub, "bin") + os.pathsep + os.environ["PATH"]
            except ImportError:
                pass
        from faster_whisper import WhisperModel
        _WHISPER["m"] = WhisperModel(w["model"], device=w["device"], compute_type=w["compute_type"])
    segs, _ = _WHISPER["m"].transcribe(str(wav), language=w.get("language", "en"), word_timestamps=True, initial_prompt=prompt)
    # tokens without a letter or digit aren't words: Whisper marks a trailing-off last word with a lone "-" (a caption would read
    # "cuz -"); but a "%" is the word "percent" (spoken_tokens)
    words = spoken_tokens([{"w": x.word.strip(), "start": float(x.start), "end": float(x.end)} for s in segs for x in s.words])
    return fill_gaps(cfg, wav, words, prompt) if repair else words


MAGNITUDE = {"thousand", "million", "billion", "trillion"}


def spoken_tokens(words):
    """Whisper writes said numbers as signs, so the words are lost to the script match ("about thirteen percent higher" comes out
    "13" "%", and a "%" dropped as a non-word leaves captions reading "about 13 higher" and the gate flagging 'percent' not heard;
    "three point nine million dollar deal" comes out "$3" ".9" "million" "deal"). Each such token becomes the
    words that were said, its span shared by length: "%" -> percent, "13%" -> 13 percent, ".9" -> point 9, "3.9" -> 3 point 9, and a
    "$" number gets its "dollars" after the number or its magnitude word (million, billion...) unless Whisper wrote it there.
    Tokens with no letter or digit left are dropped."""
    out = []
    for i, x in enumerate(words):
        t = x["w"]
        parts = []
        dollar = t.startswith("$") or t.startswith("-$")
        core = t.replace("$", "")
        m = re.fullmatch(r"([^\w.]*)(\d[\d,]*)?(?:\.(\d+))?(%?)([^\w%]*)", core)
        if m and (m[2] or m[3]) and (m[3] or m[4] or dollar):
            if m[2]:
                parts.append(m[1] + m[2])
            if m[3]:
                parts += ["point", m[3]]
            if m[4]:
                parts.append("percent")
            parts[-1] += m[5]
        elif core.strip(".,;:?!\"'") == "%":
            parts = ["percent" + core.split("%", 1)[1]]
        elif re.fullmatch(r",\d{3}(,\d{3})*[.,;:?!]*", t) and out and re.search(r"\d$", out[-1]["w"]):
            # Whisper splits "14,000" and "4,811" into "14" ",000" (the captions would read "fourteen ,000"): the group goes back
            # onto its number, whose span grows over it
            out[-1]["w"] += t
            out[-1]["end"] = x["end"]
            continue
        elif _key(t):
            parts = [t]
        if parts:
            lens = [len(p) + 1 for p in parts]
            a, d = x["start"], (x["end"] - x["start"]) / sum(lens)
            for p, n in zip(parts, lens):
                out.append({"w": p, "start": a, "end": a + d * n})
                a += d * n
        if dollar and parts:   # the "dollars" Whisper folded into the "$": after the number (its ".9" part), or its magnitude word
            j = i
            while j + 1 < len(words) and re.fullmatch(r"\.\d+", words[j + 1]["w"].strip()):
                j += 1
            if j + 1 < len(words) and _key(words[j + 1]["w"]) in MAGNITUDE:
                j += 1
            nxt = _key(words[j + 1]["w"]) if j + 1 < len(words) else ""
            if not nxt.startswith("dollar"):
                if j == i:
                    last = out[-1]
                    mid = (last["start"] + last["end"]) / 2
                    tail = re.search(r"[^\w%]*$", last["w"])[0]     # "$45." -> "45 dollars."
                    last["w"] = last["w"][:len(last["w"]) - len(tail)] if tail else last["w"]
                    out.append({"w": "dollars" + tail, "start": mid, "end": last["end"]})
                    last["end"] = mid
                else:
                    words[j] = {**words[j], "_dollars_after": True}
        if x.get("_dollars_after") and out:
            last = out[-1]
            mid = last["start"] + (last["end"] - last["start"]) * 0.55
            tail = re.search(r"[^\w%]*$", last["w"])[0]         # "$40" "billion," -> "40 billion dollars,"
            last["w"] = last["w"][:len(last["w"]) - len(tail)] if tail else last["w"]
            out.append({"w": "dollars" + tail, "start": mid, "end": last["end"]})
            last["end"] = mid
    return [{"w": o["w"], "start": round(o["start"], 3), "end": round(o["end"], 3)} for o in out]


def voiced_runs(wav, min_s=0.5, below_db=30.0, bridge_s=0.15):
    """Stretches of voice in a file: 10 ms frames within below_db of the loud level (95th percentile), gaps < bridge_s bridged."""
    import numpy as np
    raw = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    n = len(x) // 160
    if not n:
        return []
    db = 20 * np.log10(np.sqrt((x[: n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-9)
    on = db > np.percentile(db, 95) - below_db
    runs, a = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and a is None:
            a = i
        elif not v and a is not None:
            if runs and a / 100 - runs[-1][1] < bridge_s:
                runs[-1][1] = i / 100
            else:
                runs.append([a / 100, i / 100])
            a = None
    return [(a, b) for a, b in runs if b - a >= min_s]


def word_cap(w):
    """The longest a heard word plausibly lasts (s): ~0.3 s plus 70 ms a letter and 150 ms a digit, at most 1 s ("1999" said takes
    ~0.75 s, "personally" ~0.40 s; a skipped stretch shows up as one word stretched over it, e.g. "won't" lasting 1.1-4.5 s)."""
    t = w["w"]
    return min(0.3 + 0.07 * sum(c.isalpha() for c in t) + 0.15 * sum(c.isdigit() for c in t), 1.0)


def uncovered(runs, words, pad=0.12, min_s=0.3):
    """Parts of the voiced runs no heard word covers (word spans widened by pad, and none counted longer than word_cap: over a
    skipped stretch Whisper stretches one word across it, e.g. "won't" over 4.5 s): what Whisper skipped."""
    out = []
    spans = sorted((w["start"] - pad, min(w["end"], w["start"] + word_cap(w)) + pad) for w in words)
    for a, b in runs:
        t = a
        for s0, s1 in spans:
            if s1 <= t or s0 >= b:
                continue
            if s0 > t and s0 - t >= min_s:
                out.append((t, s0))
            t = max(t, s1)
        if b - t >= min_s:
            out.append((t, b))
    return out


def fill_gaps(cfg, wav, words, prompt=None, ctx_s=1.0):
    """Whisper sometimes skips a stretch near its 30 s windows (a few words missing, the words after them stacked at one time, so
    beats get cut in the wrong place). Voice no heard word covers is transcribed alone (with ctx_s of
    context either side) and its words inserted where they fall inside the gap."""
    import tempfile
    added = []
    for a, b in uncovered(voiced_runs(wav, min_s=0.3), words):
        t0 = max(a - ctx_s, 0.0)
        with tempfile.TemporaryDirectory() as d:
            clip = Path(d) / "gap.wav"
            subprocess.run([ffmpeg_bin(), "-v", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{b + ctx_s - t0:.3f}", "-i", str(wav),
                            "-ac", "1", "-ar", "48000", str(clip)], check=True)
            got = heard_words(cfg, clip, prompt, repair=False)
        got = [{"w": x["w"], "start": x["start"] + t0, "end": x["end"] + t0} for x in got]
        added += [x for x in got if a - 0.1 <= (x["start"] + x["end"]) / 2 <= b + 0.1]
    if not added:
        return words
    # the zero-length stack left where it skipped (a word of 0.02 s: kept beside the re-heard one, the captions would read it twice),
    # and any word the re-hearing heard again on the same spot
    keep = [w for w in words if not ((w["end"] - w["start"] <= 0.03 and any(x["start"] - 0.3 <= w["start"] <= x["end"] + 0.3 for x in added))
                                     or any(_key(x["w"]) == _key(w["w"]) and x["start"] - 0.1 <= w["end"] and w["start"] <= x["end"] + 0.1
                                            for x in added))]
    first = min(x["start"] for x in added)
    for w in keep:  # the word stretched over the skipped stretch ends where the re-heard words begin
        if w["start"] < first < w["end"]:
            w["end"] = first
    return sorted(keep + added, key=lambda w: w["start"])


def _key(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def heard_alone(cfg, wav, t0, t1):
    """The stretch t0..t1 of wav cut out and transcribed on its own -> heard words (times relative to t0). Whisper leaves phrases out
    of long transcripts; alone, the same stretch is heard in full."""
    import subprocess
    import tempfile

    from .core import ffmpeg_bin
    with tempfile.TemporaryDirectory() as d:
        clip = Path(d) / "alone.wav"
        subprocess.run([ffmpeg_bin(), "-y", "-v", "error", "-ss", f"{max(t0, 0):.3f}", "-to", f"{t1:.3f}", "-i", str(wav), str(clip)],
                       check=True)
        return heard_words(cfg, clip)


def said_after_all(cfg, wav, heard, j1, j2, script_words, ctx_words=3):
    """A phrase missing from the transcript where heard[j1:j2] stands: is it there when that stretch, with ctx_words heard words
    either side, is transcribed alone? (Whisper can squash a whole phrase into the timestamps of one word; one word of context
    isn't enough to hear it back, three is.) -> (start, end) of the phrase in the narration if heard, else None."""
    from .tts import skipped_phrases
    t0 = heard[max(j1 - ctx_words, 0)]["start"] - 0.05 if heard else 0.0
    t1 = heard[min(j2 + ctx_words - 1, len(heard) - 1)]["end"] + 0.05 if heard else 2.0
    alone = [h for h in heard_alone(cfg, wav, t0, t1) if _key(h["w"])]
    want = [_key(w) for w in script_words if _key(w)]
    got = [_key(h["w"]) for h in alone]
    if not want or skipped_phrases(want, got):
        return None
    hit = [b for b in difflib.SequenceMatcher(None, want, got, autojunk=False).get_matching_blocks() if b.size]
    if not hit:
        return None
    return t0 + alone[hit[0].b]["start"], t0 + alone[hit[-1].b + hit[-1].size - 1]["end"]


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
         "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
# every number word 0-99 as its digits ("thirteen" -> "13", "fortyfive" -> "45"), so "thirteen" said and "13" heard match
NUM = {**{w: str(i) for i, w in enumerate(_ONES)}, **{t: str(20 + 10 * i) for i, t in enumerate(_TENS)},
       **{t + o: str(20 + 10 * i + k) for i, t in enumerate(_TENS) for k, o in enumerate(_ONES[1:10], 1)}}


def _norm(w):
    """A word for comparing script and hearing: key, abbreviations, number words as digits, to/too/two as one."""
    k = _key(w)
    k = ABBR.get(k, k)
    k = NUM.get(k, k)
    return next((sorted(h)[0] for h in HOMOPHONES if k in h), k)


def script_heard_alone(cfg, wav, heard, j1, j2, script_ctx, c1, c2, ctx_words=4):
    """A small mismatch between the script and the long transcript (an extra "The", an extra "Of", "There's" heard as "Just"):
    the stretch around it transcribed alone. True if there the script's words c1..c2 of script_ctx are heard as written (and, for an
    extra heard word, the two script words around it are heard back to back): Whisper's long pass glitched, the audio is right."""
    if not heard:
        return False
    t0 = heard[max(j1 - ctx_words, 0)]["start"] - 0.05
    t1 = heard[min(j2 + ctx_words - 1, len(heard) - 1)]["end"] + 0.05
    alone = [_norm(h["w"]) for h in heard_alone(cfg, wav, t0, t1) if _norm(h["w"])]
    want = [_norm(w) for w in script_ctx]
    m = {}
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, want, alone, autojunk=False).get_opcodes():
        if op == "equal":
            m.update({a1 + k: b1 + k for k in range(a2 - a1)})
    if c2 > c1:
        return all(k in m for k in range(c1, c2)) and all(m[k + 1] == m[k] + 1 for k in range(c1, c2 - 1))
    return c1 - 1 in m and c1 in m and m[c1] == m[c1 - 1] + 1


def not_a_word(wav, start, end):
    """Is a short extra "word" Whisper heard really a word? Measured: the S-hiss of "Screenshot" heard as "The" (unvoiced, 98% of its
    energy above 3 kHz) and a 0.06 s onset heard as "Of" (a real "of" runs 0.1 s+). -> True for a hiss (>80% above 3 kHz) or < 0.08 s."""
    import numpy as np
    from .core import SR, read_wav
    if end - start < 0.08:
        return True
    x = read_wav(wav)
    x = (x.mean(1) if x.ndim > 1 else x).astype(np.float64)
    seg = x[int(start * SR):int(end * SR)]
    if len(seg) < 64:
        return True
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    return S[f > 3000].sum() / max(S[f > 80].sum(), 1e-12) > 0.8


def caption_fixes(text):
    """`## Caption fixes` in script.md: lines `- "heard" = "script"` for words the voice said right that Whisper writes otherwise
    (e.g. "Loki" = "lowkey", "Sersha" = "Saoirse"). -> {heard key: script key}."""
    m = re.search(r"^## Caption fixes\b[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return {_key(a): _key(b) for a, b in re.findall(r'^\s*-\s*"([^"]+)"\s*=\s*"([^"]*)"', m[1] if m else "", re.M)}


ABBR = {"mt": "mount", "vs": "versus", "dr": "doctor", "ft": "feat"}  # Whisper writes "Mt. Everest" for "Mount Everest"


HOMOPHONES = [{"to", "too", "two", "2"}, {"there", "their", "theyre"}, {"your", "youre"}, {"its", "it's"}]  # "down to" heard as "down too"


def _same_word(a, b):
    """Same spoken word, different spelling? ('Nguyen'/'Nguyenn', 'Saoirse'/'Sersha' no, '5km'/'5 km', 'Katherine'/'Catherine', 'Mt.'/'Mount',
    'to'/'too'/'two': the audio can't tell them apart, so the script's spelling stays)."""
    ka, kb = _key(a), _key(b)
    ka, kb = ABBR.get(ka, ka), ABBR.get(kb, kb)
    ka, kb = NUM.get(ka, ka), NUM.get(kb, kb)      # "thirteen" said, "13" heard
    return ka == kb or any(ka in h and kb in h for h in HOMOPHONES) or (min(len(ka), len(kb)) >= 4 and difflib.SequenceMatcher(a=ka, b=kb).ratio() >= 0.75)


def _match(sw, hw, loose=False):
    """How a script run and a heard run line up: 'same' (word for word), 'joined' (the same words split differently,
    '5 KM' heard as '5KM'; or one number said in words and written in digits, 'four thousand eight hundred and eleven' / '4,811';
    loose also accepts near-spellings, for timing only), or None."""
    if len(sw) == len(hw) and all(_same_word(a, b) for a, b in zip(sw, hw)):
        return "same"
    ka, kb = _key("".join(sw)), _key("".join(hw))
    if sw and hw and (ka == kb or (loose and _same_word(ka, kb)) or _uncontracted(sw, kb)):
        return "joined"
    nv = _numval(sw)
    if nv is not None and nv == _numval(hw):
        return "joined"
    return None


_SCALE = {"hundred": 100, "thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}


def _numval(words):
    """The value of a run of words that says one number, in words or digits ("four thousand eight hundred and eleven", "4,811",
    "eight and a half", "8 point 5", "three point nine million"), or None (without it Whisper's digits never match the script's
    number words, and the gate flags words that were said)."""
    ks = [k for k in (_key(w) for w in words) if k]
    total = cur = 0
    frac, got, i = 0.0, False, 0
    while i < len(ks):
        k = ks[i]
        if k == "and" and ks[i + 1:i + 3] == ["a", "half"] and got:
            frac, i = 0.5, i + 3
            continue
        if k == "and" and got:
            i += 1
            continue
        if k == "point" and got and i + 1 < len(ks):
            d = NUM.get(ks[i + 1], ks[i + 1])
            if not d.isdigit():
                return None
            frac, i = float("0." + d), i + 2
            continue
        v = NUM.get(k, k)
        if v.isdigit():
            cur, got = cur + int(v), True
        elif k in _SCALE and got:
            if _SCALE[k] == 100:
                cur *= 100
            else:
                total, cur = total + (cur + frac) * _SCALE[k], 0
                frac = 0.0
        else:
            return None
        i += 1
    return round(total + cur + frac, 6) if got else None


def _uncontracted(sw, heard_key):
    """The script's contraction, heard spelled out ("bridge's" -> "bridge is"): the same words, keep the script's spelling."""
    base = " ".join(sw).lower().replace("’", "'")
    reps = (("'s", " is"), ("'s", " has"), ("'re", " are"), ("'ll", " will"), ("'ve", " have"), ("'d", " would"), ("'d", " had"),
            ("n't", " not"), ("'m", " am"))
    return "'" in base and any(_key(base.replace(a, b)) == heard_key for a, b in reps)


def _spread(texts, a, z):
    """Share the span a..z between words by length -> [(start, end)]."""
    lens = [len(t) + 1 for t in texts]
    out, t = [], a
    for n in lens:
        d = (z - a) * n / sum(lens)
        out.append((t, t + d))
        t += d
    return out


def words_verified(ctx, beats, narration):
    """Captions 1:1 with the audio: Whisper's words, lined up with the script. Where they are the same word
    the script's spelling is kept (names, numbers); where the voice said something else, the caption shows what was said; words
    the voice skipped are left out. Every deviation is reported (build/warnings.txt), so the section can be re-rendered."""
    heard = heard_words(ctx.cfg, narration)
    script_words = [(b, i, w) for b in beats for i, w in enumerate(b["voice"].split())]
    sm = difflib.SequenceMatcher(a=[_key(w) for _, _, w in script_words], b=[_key(h["w"]) for h in heard], autojunk=False)
    beat_at = lambda t: next((b["id"] for b in beats if b["start"] <= t < b["end"]), beats[-1]["id"])
    sp = getattr(ctx, "video", None) and ctx.video / "script.md"
    fixes = caption_fixes(sp.read_text(encoding="utf-8")) if sp and sp.exists() else {}
    out, issues = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        sw, hw = script_words[i1:i2], heard[j1:j2]
        how = "same" if op == "equal" else _match([s[2] for s in sw], [h["w"] for h in hw]) if op == "replace" else None
        fix = fixes.get(_key("".join(h["w"] for h in hw))) if hw else None
        if not how and op == "insert" and (fix == "" or (len(hw) == 1 and hw[0]["end"] - hw[0]["start"] <= 0.15
                                                         and not_a_word(narration, hw[0]["start"], hw[0]["end"]))):
            continue  # a sound Whisper writes as a word, checked not to be one (## Caption fixes: "A" = ""; or measured: a hiss, a click)
        if not how and hw and fix and fix == _key("".join(s[2] for s in sw)):
            how = "joined"  # said right, spelled otherwise by Whisper (## Caption fixes)
        span = said_after_all(ctx.cfg, narration, heard, j1, j2, [s[2] for s in sw]) if not how and i2 - i1 >= 3 and len(hw) <= 1             else None
        if span:  # left out of the long transcript, heard when that stretch is transcribed alone: the script's words, at those times
            k = len(out)
            while k > 0 and out[k - 1]["start"] >= span[0] - 0.02:
                k -= 1
            if k < len(out):  # words Whisper timed inside the phrase (it squashed them together): just before it instead
                a = min(out[k - 1]["end"] if k else 0.0, span[0] - 0.05)
                for x, (t0, t1) in zip(out[k:], _spread([x["w"] for x in out[k:]], max(a, span[0] - 0.3 * (len(out) - k)), span[0])):
                    x["start"], x["end"] = t0, t1
            for (b, i, w), (t0, t1) in zip(sw, _spread([s[2] for s in sw], span[0], max(span[1], span[0] + 0.1))):
                out.append({"w": w, "start": t0, "end": t1, "beat": b["id"], "emph": (b.get("emph") or [None] * 999)[i]})
            continue
        if how:  # the script's spelling, the heard timing ("joined": the heard span shared by length)
            times = [(h["start"], h["end"]) for h in hw] if how == "same" else _spread([s[2] for s in sw], hw[0]["start"], hw[-1]["end"])
            for (b, i, w), (a, z) in zip(sw, times):
                out.append({"w": w, "start": a, "end": z, "beat": b["id"], "emph": (b.get("emph") or [None] * 999)[i]})
            continue
        if i2 - i1 <= 6 and j2 - j1 <= 6:  # a small mismatch: is it Whisper's long pass, or the voice? Heard alone decides
            lo, hi = max(i1 - 4, 0), min(i2 + 4, len(script_words))
            if script_heard_alone(ctx.cfg, narration, heard, j1, j2, [s[2] for s in script_words[lo:hi]], i1 - lo, i2 - lo):
                if sw:  # the script's words, over the heard span (or the gap between the neighbours)
                    a = hw[0]["start"] if hw else (out[-1]["end"] if out else 0.0)
                    z = hw[-1]["end"] if hw else (heard[j2]["start"] if j2 < len(heard) else a + 0.3 * len(sw))
                    for (b, i, w), (t0, t1) in zip(sw, _spread([s[2] for s in sw], a, max(z, a + 0.1))):
                        out.append({"w": w, "start": t0, "end": t1, "beat": b["id"], "emph": (b.get("emph") or [None] * 999)[i]})
                continue  # an extra heard word that isn't there alone: left out
        for h in hw:  # what was actually said
            out.append({"w": h["w"], "start": h["start"], "end": h["end"], "beat": beat_at(h["start"]), "emph": None})
        said, meant = " ".join(h["w"] for h in hw), " ".join(w for _, _, w in sw)
        issues.append(f"script '{meant}' -> voice said '{said}'" if hw else f"voice skipped '{meant}'")
    for msg in issues:
        ctx.warn(f"captions follow the audio: {msg}")
    for a, b in zip(out, out[1:]):  # script order; times never go backwards (a mistimed word would otherwise jump places)
        if b["start"] < a["start"]:
            b["start"] = a["end"]
            b["end"] = max(b["end"], b["start"] + 0.05)
    return [{**x, "start": round(x["start"], 3), "end": round(x["end"], 3)} for x in out]


def refine_onsets(words, wav, before=0.15, after=0.10, quiet_db=-25.0, loud_db=-12.0):
    """Whisper's word starts can be ~0.1 s off (a word after a pause heard 100 ms late puts a hero pop and its hit late against
    the voice). Where a word follows a pause, its start moves to where its sound begins: the frame after
    the last quiet frame (quiet_db under the speech median) before the first loud one (loud_db under), within -before..+after
    s of Whisper's start (5 ms frames). A word glued to the previous one (no quiet frame) keeps Whisper's time."""
    import numpy as np
    from .core import SR, read_wav
    x = read_wav(wav).astype(np.float64) / 32768
    hop = SR // 200
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    spans = [np.arange(int(w["start"] * 200), min(int(w["end"] * 200), n)) for w in words]
    ref = np.median(db[np.concatenate(spans)]) if words else 0  # speech median (dB)
    for k, w in enumerate(words):
        lo = max(int((w["start"] - before) * 200), int(words[k - 1]["start"] * 200) + 4 if k else 0, 1)
        hi = min(int((w["start"] + after) * 200), int(w["end"] * 200), n - 6)
        # every step from a quiet frame into sound that turns loud within 30 ms; the one nearest Whisper's start wins
        # (the window can reach back into the previous word, as with "at" before "30")
        steps = [j for j in range(lo, hi) if db[j - 1] < ref + quiet_db <= db[j] and (db[j:j + 6] > ref + loud_db).any()]
        if not steps:
            continue
        t = round(min(steps, key=lambda j: abs(j - w["start"] * 200)) / 200, 3)
        if t < w["end"] - 0.02:
            w["start"] = t
            if k and words[k - 1]["end"] > t:
                words[k - 1]["end"] = t
    return words


def beat_onsets(words, beats, wav, quiet_db=-25.0, loud_db=-12.0, reach=0.8):
    """A beat's first word can't start before its beat: the voice pipeline cuts beats at the pause before them (measured), so a
    first word Whisper timed earlier is squeezed onto the end of the previous word (its caption would show up to half a second
    early). Such a word moves to the first step from quiet into
    sound after the beat's start (within reach s); the previous word ends there at the latest. Levels as refine_onsets."""
    import numpy as np
    from .core import SR, read_wav
    x = read_wav(wav).astype(np.float64) / 32768
    hop = SR // 200
    n = len(x) // hop
    db = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-12)
    spans = [np.arange(int(w["start"] * 200), min(int(w["end"] * 200), n)) for w in words]
    ref = np.median(db[np.concatenate(spans)]) if words else 0
    for b in beats[1:]:
        k = next((i for i, w in enumerate(words) if w["beat"] == b["id"]), None)
        if k is None or words[k]["start"] >= b["start"] - 0.02:
            continue
        lo, hi = max(int(b["start"] * 200) - 10, 1), min(int((b["start"] + reach) * 200), n - 6)
        steps = [j for j in range(lo, hi) if db[j - 1] < ref + quiet_db <= db[j] and (db[j:j + 6] > ref + loud_db).any()]
        if not steps:
            continue
        t = round(steps[0] / 200, 3)
        w = words[k]
        w["end"] = round(max(w["end"], t + 0.06), 3)
        w["start"] = t
        if k and words[k - 1]["end"] > t:
            words[k - 1]["end"] = t
        for v in words[k + 1:]:  # words after it that Whisper also squeezed in keep their order
            if v["start"] >= w["end"]:
                break
            v["start"] = w["end"]
            v["end"] = round(max(v["end"], v["start"] + 0.05), 3)
    return words


def words_whisper(ctx, beats, narration):
    """faster-whisper word timestamps (CUDA on the PC), imported lazily. Whisper gives the timing only:
    the script's own words are matched to what it heard, so spelling always follows the script."""
    return snap_to_script(beats, heard_words(ctx.cfg, narration))


def snap_to_script(beats, heard):
    """Script words get the times of matching heard words (difflib); unmatched runs are spread evenly between
    their matched neighbours (never before the previous word: in continuous mode one section holds several beats)."""
    words = [{"w": w, "beat": b["id"], "lo": b["start"], "hi": b["voice_end"]} for b in beats for w in b["voice"].split()]
    sm = difflib.SequenceMatcher(a=[_key(x["w"]) for x in words], b=[_key(x["w"]) for x in heard], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():  # "'Cause" heard as "because", "5 KM" as "5KM" still give timing
        sw, hw = words[i1:i2], heard[j1:j2]
        how = "same" if op == "equal" else _match([x["w"] for x in sw], [h["w"] for h in hw], loose=True) if op == "replace" else None
        if how:
            times = [(h["start"], h["end"]) for h in hw] if how == "same" else _spread([x["w"] for x in sw], hw[0]["start"], hw[-1]["end"])
            for x, (a, z) in zip(sw, times):
                x.update(start=a, end=z)
    i = 0
    while i < len(words):
        if "start" in words[i]:
            i += 1
            continue
        j = i
        while j < len(words) and "start" not in words[j] and words[j]["beat"] == words[i]["beat"]:
            j += 1
        prev_end = words[i - 1]["end"] if i else words[i]["lo"]
        nxt = min(next((x["start"] for x in words[j:] if "start" in x), words[i]["hi"]), words[i]["hi"])
        a = max(prev_end, words[i]["lo"])
        span = max(nxt - a, 0.05 * (j - i))
        for k in range(i, j):
            words[k].update(start=a + span * (k - i) / (j - i), end=a + span * (k - i + 1) / (j - i))
        i = j
    return [{"w": x["w"], "start": round(x["start"], 3), "end": round(x["end"], 3), "beat": x["beat"]} for x in words]


def group(words, max_words, max_chars, max_dur, break_on):
    """Greedy grouping into cues; never crosses a beat; breaks after punctuation in `break_on`."""
    cues, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["beat"] != cur[-1]["beat"] or w["end"] - cur[0]["start"] > max_dur
                    or len(" ".join(x["w"] for x in cur + [w])) > max_chars):
            cues.append(cur)
            cur = []
        cur.append(w)
        if w["w"][-1] in break_on:
            cues.append(cur)
            cur = []
    if cur:
        cues.append(cur)
    out = [{"text": " ".join(x["w"] for x in c), "start": c[0]["start"], "end": c[-1]["end"], "beat": c[0]["beat"]}
           for c in cues]
    for a, b in zip(out, out[1:]):  # close small gaps so captions don't flicker; never overlap
        if b["start"] - a["end"] < 0.4:
            a["end"] = b["start"]
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, cues):
    lines = []
    for i, c in enumerate(cues, 1):
        lines += [str(i), f"{srt_time(c['start'])} --> {srt_time(c['end'])}", c["text"], ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def run(ctx, mode=None):
    __import__("sys").path.insert(0, str(TOOLS / "voice"))  # the voice lock (standard/VOICE_LOCK.md)
    __import__("voice_lock").guard_video(ctx.video, "dj captions")  # a locked narration is changed only by voice_layin.py
    _, timing, beats = script.load_beats(ctx)
    c = ctx.cfg["captions"]
    mode = mode or c["mode"]
    if mode == "whisper":
        try:
            words = refine_onsets(words_verified(ctx, beats, timing["narration"]), timing["narration"])
            words = beat_onsets(words, beats, timing["narration"])
        except ImportError:
            ctx.warn("faster-whisper not installed; using even timing")
            mode, words = "even", words_even(beats)
    elif mode == "align":
        words = words_align(ctx, beats)
    else:
        mode, words = "even", words_even(beats)
    cues = group(words, 99, c["max_chars"], 6.0, ".?!…")
    chunks = group(words, c["chunk_words"], c["chunk_chars"], 2.5, PUNCT_BREAK)
    write_srt(ctx.path("captions", "captions.srt"), cues)
    write_srt(ctx.path("captions", "chunks.srt"), chunks)
    ctx.save_json("captions/words.json", {"mode": mode, "words": words, "cues": cues, "chunks": chunks,
                                          "narration_sig": file_sig(timing["narration"])})
    print(f"  {mode}: {len(words)} words, {len(cues)} cues, {len(chunks)} chunks")
