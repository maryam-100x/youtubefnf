"""Versions of ONE line for the creator to pick by ear: several audios of the same part with subtle changes (punctuation, wording,
context), never the same request five times, which repeats the same mistake five times. The ear judges the audio, not the measurements.

Each version is its own request in the narration's voice ([tts] config: model, stability, direction prefix, tempo) and its own file:
the line alone, as it is rated (independent voice lines); a copy in its place (a few seconds of the narration around it) goes to
in_context/. Versions differ on purpose: the wording or punctuation, the context the voice gets (the lines around it, none), or the line
read as the continuation of the sentence before it in one request and cut out (`lead`), so one mistake isn't repeated five times.

Processing (in this order, so no word end is repeated: atempo run on a take trimmed tight doubles a final "t"): 0.5 s of silence on
both sides, the [tts] tempo, then the edges trimmed against the take's own peak (clean_edges), levelled to the old line. A take the voice
service stopped mid-sound is made again.
Whisper only checks the words (a take with a wrong word is marked in the printout).

  cd tools && PIPE voice/voice_versions.py ../videos/<video> <spec.json>
spec.json: {"name": "intro", "span": [a, b], "versions": [{"text": "...", "prev": "...", "next": "...", "lead": "...", "trail": "..."}, ...]}
  lead / trail (optional): the sentence before / after, voiced in the same request and cut away
  span = the old line in build/voice/narration.wav, seconds (where its sound starts and dies).
Writes build/voice/versions/<name>/v<k>.wav (the take as it would go in) and <video dir>/voice_picks/<name>/<name>_<k>.wav (to rate)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, ffmpeg_bin, load_config, read_wav, write_wav  # noqa: E402
from dj.tts import all_tempo, elevenlabs, voiced_db  # noqa: E402
import subprocess  # noqa: E402
from voice_patch import rms, words_match as _words_match  # noqa: E402
import difflib  # noqa: E402
from rhotic import score as rhotic_score  # noqa: E402
import re  # noqa: E402


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}


def spell(n, ordinal=False):
    """1-99 in words (ending: Whisper writes "19th", "30 million"; the script says "nineteenth", "thirty million")."""
    w = ONES[n] if n < 20 else TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if not ordinal:
        return w
    last = w.split()[-1]
    o = ORD.get(last, (last[:-1] + "ieth") if last.endswith("y") else last + "th")
    return " ".join(w.split()[:-1] + [o])


def numbers_to_words(t):
    t = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", lambda m: spell(int(m.group(1)), True), t)
    return re.sub(r"\b(\d{1,2})\b", lambda m: spell(int(m.group(1))), t)


def words_match(cfg, wav, text):
    """voice_patch's word check, minus spelling: Whisper writes a name its own way ("Berger" for "Burger", "U.S." for "US",
    "Saint -Clair" for "Saint-Clair"); a heard word one or two letters off a capitalized word of the text counts as that word, hyphens
    and spaces around them don't count. Only wrong words make a take again (each retry is a paid request)."""
    score, heard, hw = _words_match(cfg, wav, text)
    k = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower().replace("u.s.", "us").replace("u .s.", "us").replace(" -", "").replace("- ", "").replace("-", "")).split()  # noqa: E731
    names = {re.sub(r"[^a-z0-9]", "", w.lower()) for w in text.split() if w[:1].isupper()}
    heard = re.sub(r"\bwant to\b", "wanna", re.sub(r"\bgoing to\b", "gonna", heard.lower())) if ("wanna" in text.lower() or "gonna" in text.lower()) else heard
    heard = numbers_to_words(heard)
    fixed = [next((n for n in names if difflib.SequenceMatcher(a=w, b=n).ratio() >= 0.8), w) for w in k(heard)]
    return max(score, difflib.SequenceMatcher(a=k(text), b=fixed).ratio()), heard, hw

H = int(0.01 * SR)


def levels(x):
    xf = x.astype(np.float64) / 32768
    return np.array([20 * np.log10(np.sqrt(np.mean(xf[i:i + H] ** 2)) + 1e-12) for i in range(0, max(len(xf) - H, 1), H)])


def cut_mid_sound(x):
    """The voice service sometimes stops a take while it still sounds (its last 50 ms still near speech level): such a take is made
    again rather than faded."""
    lv = levels(x)
    return bool(len(lv) > 3 and lv[-3:].max() > lv.max() - 45)


def at_level(x, ref_db, ceil_db=-1.5):
    """The take at the narration's own level: its voiced level (dj.tts.voiced_db) raised to the old line's and its peaks clamped at
    -1.5 dBFS by a lookahead limiter (ffmpeg alimiter, 4x oversampled, its delay compensated), as the pipeline's loudnorm did to every
    other line; the gain raised until it sits within 0.3 dB (the limiter takes back ~1 dB). Matching by RMS under a -1 dBFS peak cap
    puts new lines in 2-6 dB low: the voice's raw takes peak 4-6 dB higher than the narration."""
    ceil = 10 ** (ceil_db / 20)
    xf = x.astype(np.float64) / 32768
    gdb = float(np.clip(ref_db - voiced_db(x), -10, 10))
    for _ in range(4):
        r = subprocess.run([ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af",
                            f"aresample={SR * 4},alimiter=limit={ceil:.4f}:attack=5:release=50:level=disabled:latency=1,aresample={SR}",
                            "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"], input=(xf * 10 ** (gdb / 20)).astype(np.float32).tobytes(),
                           capture_output=True, check=True)
        y = np.frombuffer(r.stdout, np.float32).astype(np.float64)
        y = np.round(np.clip(np.pad(y, (0, max(0, len(xf) - len(y))))[:len(xf)] * 32768, -32768, 32767)).astype(np.int16)
        miss = ref_db - voiced_db(y)
        if abs(miss) < 0.3:
            break
        gdb = float(np.clip(gdb + miss, -12, 12))
    return y


def clean_edges(x, release=False):
    """The line from its first word to where its last word has died away, nothing more: breaths and similar noises go, carefully and
    subtly. The take splits at its silences (frames 50 dB under its own peak; gaps under 30 ms
    don't count); the stretches with speech in them (a frame within 25 dB of the peak) are the line, from the first to the last; a weaker
    stretch before or after them (a breath: unvoiced, steady, ~30 dB under the peak, after a gap) stays out, and each word keeps its
    own fade into the silence. Judged against the take's own peak (voice_patch's edges judge against its quietest frames, which
    pure-silence padding sets to -inf, so a soft word ending gets cut). Short fades at both ends."""
    lv = levels(x)
    pk = lv.max()
    on = lv > pk - 50
    runs, i = [], 0
    while i < len(lv):
        if on[i]:
            j = i
            while j + 1 < len(lv) and on[j + 1]:
                j += 1
            if runs and i - runs[-1][1] - 1 < 3:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j + 1
        else:
            i += 1
    speech = [r for r in runs if lv[r[0]:r[1] + 1].max() > pk - 25]
    first, last = speech[0][0], speech[-1][1]
    # a word ending in a stop (t, k, p, d) goes quiet for its closure, then releases a short puff (the "t" of "night": 80 ms at 40 dB
    # under the peak, 40 ms after the vowel). A puff that short and that close stays (a breath runs 150 ms or more); the same for a short
    # sound just before the first word. A release can run on into a breath (170 ms in all): the first 80 ms of a sound within 100 ms
    # after the last word stay (the stop's release), the rest goes, faded.
    # Only after a word that ends in a stop (release=True: the line ends in t, k, p, d or b, not "ng"); after any other word that sound is
    # the breath (a word like "happening", a 40-ms gap, then the breath)
    tail = False
    for r in runs:
        if release and 0 < r[0] - last <= 10:
            last, tail = min(r[1], r[0] + 7), True
        if r[1] - r[0] < 10 and 0 < first - r[1] <= 10:
            first = r[0]
    s0 = max(0, (first - 2) * H)
    y = x[s0:min(len(x), (last + 2) * H)].astype(np.float64)
    fi, fo = int(0.005 * SR), int((0.04 if tail else 0.015) * SR)
    y[:fi] *= np.linspace(0, 1, fi)
    y[-fo:] *= np.linspace(1, 0, fo)
    return np.round(y).astype(np.int16), s0


ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("spec")
ap.add_argument("--pre", type=float, default=2.5)
ap.add_argument("--post", type=float, default=1.5)
ap.add_argument("--seed", type=int, default=100, help="the first version's seed (the next ones count up): a new round, new seeds")
ap.add_argument("--reprocess", action="store_true", help="only cut, trim and level the takes already made (no voice requests)")
a = ap.parse_args()
__import__("voice_ready").require(a.video, __file__)  # stage 0 of the voice lock (standard/VOICE_LOCK.md): facts, cold read, bites, names stamped
cfg = load_config(None, video_config(a.video))
ctx = Ctx(a.video, cfg)
spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
name = spec["name"]
nar = read_wav(ctx.build / "voice" / "narration.wav")
work = ctx.build / "voice" / "versions" / name
work.mkdir(parents=True, exist_ok=True)
picks = Path(str(ctx.build.parent)) / "voice_picks" / name
picks.mkdir(parents=True, exist_ok=True)
tempo = float(cfg["tts"].get("tempo", 1.0))
s0, s1 = int(spec["span"][0] * SR), int(spec["span"][1] * SR)
old = nar[s0:s1]
pre, post = nar[max(0, s0 - int(a.pre * SR)):s0], nar[s1:s1 + int(a.post * SR)]
pad = np.zeros(int(0.5 * SR), np.int16)

def generate(k, v, seed, raw):
    tcfg = dict(cfg["tts"])
    tcfg["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "seed": seed}
    text = (v["lead"] + " " if v.get("lead") else "") + v["text"] + (v.get("trail_sep", " ") + v["trail"] if v.get("trail") else "")
    al, _ = elevenlabs(tcfg, text, v.get("prev"), v.get("next"), raw)
    if not al:
        raise SystemExit(f"v{k}: no timestamps from the voice")
    raw.with_suffix(".align.json").write_text(json.dumps(al), encoding="utf-8")


def process(v, raw):
    """The line out of the raw take, sped up with silence around it, trimmed to its words, levelled to the old line; and its words'
    times in the result (from the voice's own character timestamps, carried through the cut, the padding, the tempo and the trim: the
    edit's cuts are anchored to words, so a re-voiced line brings its own)."""
    x = read_wav(raw)
    lead, trail = v.get("lead"), v.get("trail")
    al = json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8"))
    i0 = len(lead) + 1 if lead else 0
    a_ = 0
    if lead or trail:  # cut the line out of the joined read, each cut at the quietest 10 ms of the pause around it
        st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
        i1 = i0 + len(v["text"]) - 1                 # the line's last character (i0: its first, after `lead` and its space)
        lv = levels(x)

        pk = lv.max()

        def pause_cut(t0, t1):
            """The middle of the longest silence (45 dB under the peak) between two sentences. The timestamps can lag the sound by up
            to ~0.4 s (the quietest frame of a narrow window can be the next sentence's first consonant, which then stays on the line's
            end), so the window reaches 0.4 s back; a sentence pause outlasts a stop's closure inside a word. No silence at all: the
            quietest frame."""
            f0, f1 = max(0, int((t0 - 0.4) / 0.01)), min(len(lv) - 1, int((t1 + 0.1) / 0.01))
            quiet = lv[f0:f1 + 1] < pk - 45
            runs, i = [], 0
            while i < len(quiet):
                if quiet[i]:
                    j = i
                    while j + 1 < len(quiet) and quiet[j + 1]:
                        j += 1
                    runs.append((j - i, i, j))
                    i = j + 1
                else:
                    i += 1
            if not runs:
                return (f0 + int(np.argmin(lv[f0:f1 + 1]))) * H
            _, i, j = max(runs)
            return (f0 + (i + j) // 2) * H
        a_ = pause_cut(en[i0 - 2], st[i0]) if lead else 0              # `lead`'s last character .. the line's first
        b_ = pause_cut(en[i1], st[i1 + 1 + len(v.get("trail_sep", " "))]) if trail else len(x)   # the line's last character .. the trail's first
        x = x[a_:b_]
    x = np.concatenate([pad, x, pad])
    if abs(tempo - 1.0) > 1e-3:
        x = all_tempo({"tempo": tempo}, [{"voice": v["text"]}], [x])[0]
    last = "".join(c for c in v["text"].split()[-1].lower() if c.isalpha())
    x, s_off = clean_edges(x, release=last[-1:] in ("t", "k", "p", "d", "b") and not last.endswith("ng"))
    leveled = at_level(x, voiced_db(old))
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    t_out = lambda t: max(0.0, min(len(x) / SR, ((t - a_ / SR) + len(pad) / SR) / tempo - s_off / SR))  # noqa: E731
    words, pos = [], 0
    for wd in v["text"].split(" "):
        if wd:
            c0, c1 = i0 + pos, i0 + pos + len(wd) - 1
            words.append({"w": wd, "start": round(t_out(st[c0]), 3), "end": round(t_out(en[c1]), 3)})
        pos += len(wd) + 1
    return leveled, words


for k, v in enumerate(spec["versions"], 1):
    raw = work / f"raw_v{k}.wav"
    for attempt in range(4):   # a take the service stopped mid-sound, or with a wrong word, is made again with a new seed
        if not raw.exists():
            generate(k, v, a.seed + k - 1 + 50 * attempt, raw)
        rh = rhotic_score(raw, json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8")))
        # --reprocess: the takes were screened when they were made (a 4th try is kept as it is), so no screen and no exit (one such
        # take would stop the re-cut of the lines after it)
        screen = not a.reprocess and attempt < 3
        if screen and not v.get("trail") and cut_mid_sound(read_wav(raw)):   # with a trail, the read ends on the trail (cut away)
            why = "the voice's audio stops mid-sound"
        elif screen and rh["median_dip"] < 250:
            # the American r screen (rhotic.py: takes heard as British dipped 103-236 Hz, an American one 290): a take under 250 Hz is
            # made again before anyone hears it
            why = f"British-leaning r's (median dip {rh['median_dip']} Hz)"
        else:
            x, wds = process(v, raw)
            write_wav(work / f"v{k}.wav", x)
            (work / f"v{k}.words.json").write_text(json.dumps(wds), encoding="utf-8")
            score, heard, _ = words_match(cfg, work / f"v{k}.wav", v["text"])
            if score >= 0.99 or attempt == 3 or a.reprocess:
                break
            why = f'heard "{heard}"'
        if a.reprocess:
            raise SystemExit(f"v{k}: {why} (--reprocess makes no new takes)")
        print(f"  v{k}: {why}; made again")
        n = 0
        while raw.with_name(f"raw_v{k}_try{n}.wav").exists():
            n += 1
        raw.rename(raw.with_name(f"raw_v{k}_try{n}.wav"))
        raw.with_suffix(".align.json").rename(raw.with_name(f"raw_v{k}_try{n}.align.json"))
    write_wav(picks / f"{name}_{k}.wav", x)   # what is rated: the line alone (independent voice lines)
    (picks / "in_context").mkdir(exist_ok=True)
    write_wav(picks / "in_context" / f"{name}_{k}.wav", np.concatenate([pre, x, post]))
    lead, trail = v.get("lead"), v.get("trail")
    how = ("inside the lines around it" if lead and trail else "joined to the line before" if lead else "joined to the line after" if trail
           else "no context" if not v.get("prev") and not v.get("next") else "with context")
    print(f"  v{k}: {len(x) / SR:.2f} s (old {len(old) / SR:.2f} s), {how}: \"{v['text']}\"  words {'ok' if score >= 0.99 else f'{score:.2f}: ' + heard}"
          f"  r-dip {rh['median_dip']} Hz")
print(f"-> {picks}")
