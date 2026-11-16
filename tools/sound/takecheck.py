"""A5 of the sound gate: faults of the take itself, before anyone listens (a whispered or skipped word, a sentence too loud or too
quiet, a word cut short inside the take's own audio: a fault of the take is a new take, never a repair). Four parts:

  WORDS   Whisper's words (captions/words.json: in whisper mode dj keeps the script's spelling where the voice said the same word and
          writes what was heard where it didn't) against script.md's words, beat by beat, after normalising what isn't a different
          word: numbers (words or digits, "$40" = "forty dollars", "5 ,000" = "five thousand", "19th" = "nineteenth"), a roman
          numeral after a title word the creator lists in NUMERAL_AFTER ("Part II" = "Part 2"), gonna/going to, wanna/want to, case
          and punctuation. What is left is a missing, added or changed word: "fi" for "five", "double" for "doubled", a skipped
          "Which". 0 is the bar; a name the voice says on purpose another way is A6's table, not an allow. A word Whisper wrote with
          no length (start = end) had no sound of its own: flagged too.
  END     a phrase's last word (before a comma, a full stop or a pause of 0.15 s) that ends in a v or an f by how it's said ("5." is
          "five", "V." too; s, z and th ends read as cut on 12 clean words of an approved voice, so they aren't checked) must have it:
          20 ms or more of frication (10-ms frames over -45 dB centred at 2.5 kHz or higher) within 120 ms after its last vowel. A
          take's own "fi" for "five" has none, and Whisper still writes "5" there (small.en and its language model: WORDS can't hear
          it); A1 can't either, the raw take has no "v".
  LEVEL   each sentence's loudness (EBU R128, pyloudnorm) against the median of the 3 sentences either side: more than 2 LU off is
          flagged (re-voiced lines can come out 6-9.5 dB quiet).
  WORD    a content word (not in the function-word list) with 100 ms or more of sound (10-ms frames over -35 dB: Whisper's span is on
          the word, not in a pause) whose loud part (90th percentile) is 10 dB or more under its sentence's median word: whispered or
          swallowed.
What the measures can't judge: a sentence heard as "too loud" or "suddenly quiet" can sit within 1 LU of its neighbours (the voice's
delivery: the creator's ear decides, and a new take fixes it), and a whispered word can sit 7.2 dB under its sentence, inside the
spread of clean words on Whisper's spans (36 words 7 dB under in one approved voice), so the WORD part can't hold it at a bar that
stays quiet; it shows in WORDS when Whisper doesn't hear the word.

  EDIT tools/sound/takecheck.py <video> [--final F --words W --script S]
      [--beats-only S12,S20a]   (only these beats' words: a Whisper run on part of the voice)"""
import argparse
import difflib
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

LU_BAR = 2.0
WORD_BAR = -12.0     # an approved voice's quietest content word on Whisper's spans sat 10.6 dB under its sentence
FUNC = set("""a an the and or but so nor yet for of to in on at by with from into onto over under as than then that this these those it
its it's is are was were be been being am has have had do does did i you he she we they me him her us them my your his our their
there here which who whom whose what when where why how if not no just also even too very more most all any some each every one can
could would should will shall may might must won't don't didn't isn't aren't wasn't weren't can't couldn't wouldn't up out about
off like get gets got way i'm you're they're we're he's she's that's there's what's let's i'd you'd they'd we'd i've you've we've
they've i'll you'll we'll they'll""".split())

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ORD = {"first": "one", "second": "two", "third": "three", "fourth": "four", "fifth": "five", "sixth": "six", "seventh": "seven",
       "eighth": "eight", "ninth": "nine", "tenth": "ten", "eleventh": "eleven", "twelfth": "twelve", "thirteenth": "thirteen",
       "fourteenth": "fourteen", "fifteenth": "fifteen", "sixteenth": "sixteen", "seventeenth": "seventeen",
       "eighteenth": "eighteen", "nineteenth": "nineteen", "twentieth": "twenty", "thirtieth": "thirty"}
ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7"}
# title words (lower case) after which a roman numeral is said as a number ("part ii" = "part 2"): the creator's own, empty until filled
NUMERAL_AFTER = set()
SAME = {"gonna": ["going", "to"], "wanna": ["want", "to"], "gotta": ["got", "to"], "ok": ["okay"], "pc's": ["pcs"]}


def tokens(text):
    """a text or a word list -> normalised tokens: lower case, punctuation off, $N -> N dollar, 5 ,000 -> 5000, hyphens split,
    ordinals to cardinals ("19th" -> 19, "nineteenth" -> 19), number words to digits, a roman numeral after a NUMERAL_AFTER word
    to its digit"""
    if isinstance(text, (list, tuple)):
        text = " ".join(text)
    t = text.replace("’", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"(\d)\s*,\s*(\d{3})\b", r"\1\2", t)            # 5 ,000 / 1,045 -> 5000 / 1045
    t = re.sub(r"\b(\d{1,3})\s+(000)\b", r"\1\2", t)             # Whisper's "$20,000" kept as "20 000" by the captions -> 20000
    t = re.sub(r"\$\s*(\d+(?:\.\d+)?)", r"\1", t)                 # $40 -> 40 (dollar signs and words are Whisper's spelling)
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)                 # 19th -> 19
    # a number that opens a compound ("sixteen-year-olds") is its own number: "two sixteen-year-olds" is 2 and 16, not 216
    t = re.sub(r"\b([A-Za-z]+)(\s+)([A-Za-z]+)-([A-Za-z]+)",
               lambda m: (f"{m[1]}{m[2]}numbreak {m[3]}-{m[4]}" if m[1].lower() in NUMW and m[3].lower() in NUMW and m[4].lower() not in NUMW
                          else m[0]), t)
    t = re.sub(r"[-/]", " ", t)
    out = []
    for raw in t.split():
        w = re.sub(r"[^a-z0-9'.]", "", raw.lower()).strip(".'")
        if not w:
            continue
        if w == "numbreak":
            out.append("§")
            continue
        if w in ("dollar", "dollars"):       # "$1,200 to $1,800" against "twelve hundred to eighteen hundred dollars": Whisper's $;
            w = "§"                          # kept as a break between numbers until they're read, then dropped
        if not (w == "second" and out and (out[-1] in UNITS or out[-1] in TENS or re.fullmatch(r"\d+", out[-1]))):
            w = ORD.get(w, w)                # ...but "a nineteen-second clip" is a time, not 19 + 2
        out.extend(SAME.get(w, [w]))
        if re.search(r"[,;:!?]['\"”’)]*$|[a-z0-9]\.['\"”’)]*$", raw.lower()):
            out.append("§")                  # a comma or a full stop ends a number ("one, two, three" is three numbers)
    # a title's numeral: "part ii" -> "part 2" (NUMERAL_AFTER)
    for i in range(1, len(out)):
        if out[i - 1] in NUMERAL_AFTER and out[i] in ROMAN:
            out[i] = ROMAN[out[i]]
    # number words -> one digit token, the way English counts ("two hundred and ten" -> 210, "thirty five thousand" -> 35000,
    # "twelve hundred" -> 1200) and the way it reads digits in groups ("six forty-two" -> 642, not 6 + 42 = 48;
    # "Nine One Nine" -> 919; "one oh six point six" -> 106.6; "four-oh-two" -> 402; "fifteen and forty thousand" stays two numbers,
    # 15 and 40000: an "and" joins only after hundred or thousand)
    res, i = [], 0
    while i < len(out):
        if out[i] == "a" and i + 1 < len(out) and out[i + 1] in ("hundred",) + tuple(BIG):
            out[i] = "one"                    # "a hundred dollar one" = "$100 one"
        elif out[i] in ("hundred", "thousand") and not (res and NUM_RE.fullmatch(res[-1])):
            out.insert(i, "one")              # "the hundred dollar one" = "the $100 one"
        if out[i] in ("hundred",) + tuple(BIG) and res and NUM_RE.fullmatch(res[-1]):
            # a multiplier after digits ("5 thousand", "1.2 million"), and the count goes on from there ("5 thousand 200")
            v = float(res.pop()) * (100 if out[i] == "hundred" else BIG[out[i]])
            s, j, _ = _group(out, i + 1, start=v, last="big" if out[i] in BIG else "hundred")
            res.append(s)
            i = j
        elif out[i] in UNITS or out[i] in TENS:
            s, i = _reading(out, i)
            res.append(s)
        elif out[i] == "point" and res and re.fullmatch(r"\d+", res[-1]) and i + 1 < len(out) and \
                (UNITS.get(out[i + 1], 99) < 10 or out[i + 1] in OH):
            # digits then the decimals in words: the captions' "106 point six" for "one oh six point six"
            d, i = "", i + 1
            while i < len(out) and (UNITS.get(out[i], 99) < 10 or out[i] in OH):
                d += "0" if out[i] in OH else str(UNITS[out[i]])
                i += 1
            res[-1] += "." + d
        elif out[i] == "000" and any(NUM_RE.fullmatch(r) for r in res[-3:]):
            # the captions' "$20,000" split as "20", "dollars,", ",000,": the thousands group goes back on its number
            k = max(q for q in range(len(res) - 3, len(res)) if q >= 0 and NUM_RE.fullmatch(res[q]))
            if all(r == "§" for r in res[k + 1:]):
                res[k] = _fmt(float(res[k]) * 1000)
                i += 1
                continue
            res.append(out[i])
            i += 1
        else:
            res.append(out[i])
            i += 1
    return [r for r in res if r != "§"]


BIG = {"thousand": 1000, "million": 10 ** 6, "billion": 10 ** 9}
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
OH = ("oh", "o")
NUMW = set(UNITS) | set(TENS) | {"hundred"} | set(BIG)


def _fmt(v):
    return str(int(v)) if float(v) == int(v) else f"{v:g}"


def _group(out, j, start=0.0, last=None):
    """one number the way English counts, from out[j] -> (digits, index after it, its last kind). A unit after a unit, or a ten after
    a unit or a ten, is not counting ("nine one", "three fifty"): the group ends there and _reading reads the next one as more digits"""
    total, cur = (start, 0.0) if last == "big" else (0.0, start)
    while j < len(out):
        w = out[j]
        if w in UNITS:
            n = UNITS[w]
            if last == "unit" or (last == "tens" and (n >= 10 or cur % 10)):
                break
            cur += n
            last = "unit"
        elif w in TENS:
            if last in ("unit", "tens"):
                break
            cur += TENS[w]
            last = "tens"
        elif w == "hundred":
            if last not in ("unit", "tens"):
                break
            cur = (cur or 1) * 100
            last = "hundred"
        elif w in BIG:
            if last in (None, "and"):
                break
            total += (cur or 1) * BIG[w]
            cur = 0.0
            last = "big"
        elif w == "and" and last in ("hundred", "big") and j + 1 < len(out) and (out[j + 1] in UNITS or out[j + 1] in TENS):
            last = "and"
        else:
            break
        j += 1
    return _fmt(total + cur), j, last


def _reading(out, i):
    """a number from out[i]: one counted group, or several read as digits one after another ("nineteen eighty-four" 1984, "nine one
    nine" 919, "one oh six" 106), then "point" and its digits ("ninety-eight point three" 98.3) -> (token, index after it)"""
    groups, j, last = [], i, None
    while j < len(out):
        w = out[j]
        if w in OH:     # "oh" as a digit only between number words
            if groups and j + 1 < len(out) and (out[j + 1] in UNITS or out[j + 1] in TENS or out[j + 1] in OH):
                groups.append("0")
                last = "oh"
                j += 1
                continue
            break
        if (w in UNITS or w in TENS) and (not groups or last in ("unit", "tens", "oh")):
            s, j, last = _group(out, j)
            groups.append(s)
            continue
        break
    s = "".join(groups)
    if j + 1 < len(out) and out[j] == "point" and ((out[j + 1] in UNITS and UNITS[out[j + 1]] < 10) or out[j + 1] in OH):
        d, j = "", j + 1
        while j < len(out) and ((out[j] in UNITS and UNITS[out[j]] < 10) or out[j] in OH):
            d += "0" if out[j] in OH else str(UNITS[out[j]])
            j += 1
        s += "." + d
    return s, j


FRIC = ("ve", "v", "fe", "ff", "f")   # v and f only: s and z ends read as cut on clean words (12 in one approved voice), v/f never did
SAY_N = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
         19: "nineteen"}
SAY_T = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def spoken_form(word):
    """how a written word ends when said: digits and roman numerals as words ("5." -> five, "2026" -> twenty-six, "V." -> five)"""
    w = word.lower().strip('.,!?;:"\'”“)(’')
    w = re.sub(r"'s$", "s", w)
    if w in ("v", "vi", "iv", "iii", "ii"):
        w = ROMAN[w]
    w = w.replace(",", "").replace("$", "")
    if re.fullmatch(r"\d+(st|nd|rd|th)", w):
        return "th"                       # 12th = twelfth: not a v or f end
    if re.fullmatch(r"\d+", w):
        n = int(re.match(r"\d+", w).group(0))
        if n % 100 == 0:
            return "hundred" if n % 1000 else "thousand"
        n %= 100
        return SAY_N[n] if n < 20 else SAY_T[n // 10] + ("-" + SAY_N[n % 10] if n % 10 else "")
    return w


def load_names():
    p = G.SOUND / "names.json"
    if not p.exists():
        return {}
    import json
    return json.loads(p.read_text(encoding="utf-8")).get("names", {})


def name_heard(sa, ha, names):
    """Whisper's spelling of a name the table knows: the script's tokens hold a name (or its voice spelling) and what was heard is
    within 0.75 of it, letters only (dj's own same-word ratio: "Kowalski" heard "Kovalski"); a name the table respells is held
    against its voice spelling ("say") too, so a name heard far from its written form still counts"""
    if not sa or not ha:
        return False
    s, h = "".join(sa), "".join(ha)
    for name, e in names.items():
        forms = {G.key(name)} | ({G.key(e.get("say", ""))} if e.get("say") and e.get("say") != "as is" else set())
        if any(f and f in s for f in forms):
            return any(difflib.SequenceMatcher(a=f, b=h).ratio() >= 0.75 for f in forms | {s})
    return False


def compare(script_words, heard_words, names=None):
    """[(op, script tokens, heard tokens)] for every difference after normalising (a known name heard in a near spelling isn't one)"""
    a, b = tokens(script_words), tokens(heard_words)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    return [(op, a[i1:i2], b[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes()
            if op != "equal" and not (op == "replace" and names and name_heard(a[i1:i2], b[j1:j2], names))]


def sentences(W):
    out, cur = [], []
    for w in W:
        if cur and w["beat"] != cur[-1]["beat"]:
            out.append(cur)
            cur = []
        cur.append(w)
        if G.sentence_end(w["w"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def run(P, beats_only=None, quiet=False, parts=("WORDS", "END", "LEVEL", "WORD")):
    W = G.load_words(P["words"])
    beats = G.script_beats(P["script"])
    flags = []
    info = {}
    if "WORDS" in parts:
        heard_by = {}
        names = load_names()
        for w in W:
            heard_by.setdefault(w["beat"], []).append(w)
        nd = 0
        for bid, text in beats:
            if beats_only and bid not in beats_only:
                continue
            hw = heard_by.get(bid, [])
            for op, sa, ha in compare(text.split(), [w["w"] for w in hw], names):
                nd += 1
                # the time: the heard word nearest the difference (by position in the beat)
                t = hw[0]["start"] if hw else 0.0
                if ha:
                    hit = next((w for w in hw if tokens([w["w"]]) and tokens([w["w"]])[0] == ha[0]), None)
                    t = hit["start"] if hit else t
                what = {"replace": f"script {' '.join(sa)!r} -> heard {' '.join(ha)!r}", "delete": f"script {' '.join(sa)!r} not heard",
                        "insert": f"heard {' '.join(ha)!r}, not in the script"}[op]
                flags.append(G.flag("A5", f"words:{bid}:{'_'.join(sa) or '+'}>{'_'.join(ha) or '-'}", t, " ".join(sa or ha),
                                    f"{bid}: {what}", part="WORDS", beat=bid))
        info["word_differences"] = nd
        # a word Whisper wrote with no length had no sound of its own: Whisper filled it in from the words around it, so the compare above
        # reads it as heard (a final "it." at 525.52-525.52 that a splice took)
        for w in W:
            if (not beats_only or w["beat"] in beats_only) and w["end"] - w["start"] < 0.01:
                flags.append(G.flag("A5", f"nolength:{w['beat']}:{w['w']}", w["start"], w["w"],
                                    f"{w['beat']}: {w['w']!r} has no length in the words ({w['start']:.2f}-{w['end']:.2f} s): Whisper heard no "
                                    f"sound for it; listen whether it is said (a cut or a splice may have taken it)", part="WORDS", beat=w["beat"]))
        import json
        raw = json.loads(Path(P["words"]).read_text(encoding="utf-8"))
        mode = raw.get("mode") if isinstance(raw, dict) else None
        info["words_mode"] = mode
        if mode and not str(mode).startswith("whisper"):
            # "align"/"even" words are the script's own: nothing was heard, so nothing can differ
            flags.append(G.flag("A5", "words:mode", 0.0, "", f"{Path(P['words']).name} is in {mode!r} mode, not Whisper's: the words can't be "
                                f"held against the script (run dj captions in whisper mode)", part="WORDS", beat=""))
    if any(p_ in parts for p_ in ("LEVEL", "WORD", "END")):
        import pyloudnorm as pyln
        x, sr = G.load_mono(P["final"])
        S = [s for s in sentences(W) if not beats_only or s[0]["beat"] in beats_only]
        if "LEVEL" in parts and len(S) >= 3:
            meter = pyln.Meter(sr)
            L = []
            for s in S:
                a, b = s[0]["start"], s[-1]["end"]
                try:
                    L.append(meter.integrated_loudness(x[int(a * sr):int(b * sr)]) if b - a >= 0.5 else np.nan)
                except Exception:
                    L.append(np.nan)
            L = np.array(L, dtype=float)
            diffs = []
            for i, s in enumerate(S):
                nb = [L[j] for j in range(max(0, i - 3), min(len(S), i + 4)) if j != i and np.isfinite(L[j])]
                if not nb or not np.isfinite(L[i]):
                    continue
                d = float(L[i] - np.median(nb))
                diffs.append(abs(d))
                if abs(d) > LU_BAR:
                    flags.append(G.flag("A5", f"level:{s[0]['beat']}@{s[0]['start']:.1f}", s[0]["start"], s[0]["w"],
                                        f"{s[0]['beat']}: sentence {'louder' if d > 0 else 'quieter'} than its neighbours by {abs(d):.1f} LU "
                                        f"({L[i]:.1f} LUFS; \"{' '.join(w['w'] for w in s)[:50]}...\")", part="LEVEL", beat=s[0]["beat"]))
            info["sentence_lu_spread"] = {"n": len(diffs), "p90": round(float(np.percentile(diffs, 90)), 2) if diffs else None,
                                          "max": round(float(max(diffs)), 2) if diffs else None}
        if "END" in parts:
            info["end_checked"] = 0
            q = int(0.01 * sr)
            f = np.fft.rfftfreq(q, 1 / sr)
            for i, w in enumerate(W):
                if beats_only and w["beat"] not in beats_only:
                    continue
                said = spoken_form(w["w"])
                fric = next((e for e in FRIC if said.endswith(e)), None)
                if not fric:
                    continue
                nxt = W[i + 1] if i + 1 < len(W) else None
                if not (re.search(r"[.,!?;:]['\"”’)]*$", w["w"]) or nxt is None or nxt["start"] - w["end"] >= 0.15):
                    continue                     # inside a phrase the next word swallows it ("five and"): only a phrase's last word
                info["end_checked"] += 1
                # the word's last vowel: the last 10-ms frame over -30 dB centred under 1.5 kHz, from 0.3 s before its end to 0.15 s after
                t0, t1 = int((w["end"] - 0.3) * sr), int((w["end"] + 0.2) * sr)
                fr = [(k, x[k:k + q]) for k in range(t0, t1, q)]
                lv = [G.db(a) for _, a in fr]
                cen = [float((f * (np.abs(np.fft.rfft(a * np.hanning(q))) ** 2)).sum() /
                             ((np.abs(np.fft.rfft(a * np.hanning(q))) ** 2).sum() + 1e-20)) if len(a) == q else 0.0 for _, a in fr]
                # its vowel ends inside the word: by Whisper's end + 60 ms (later voiced frames are the next word or a hum after:
                # a final "expensive." can have voiced sound after its v)
                lim = (w["end"] + 0.06 - t0 / sr) / 0.01
                vow = lambda j: lv[j] > -30 and cen[j] < 1500   # noqa: E731
                last_v = max((j for j in range(len(fr)) if j <= lim and vow(j)), default=None)
                if last_v is None:
                    continue
                # two cases the +60 ms alone misreads: Whisper can end a word ("twenty-five,") 0.15 s inside its vowel, so the 120 ms
                # after +60 ms are still vowel and the -ve after them (-33 dB, centred 4-5 kHz) goes uncounted: the vowel's own unbroken
                # run is followed to its end (never into the next word); and an f before a voiced closure ("life" before "by"): the
                # +60 ms takes the b's closure for the vowel: the vowel's last frame before Whisper's end is a second anchor
                nxt_f = (nxt["start"] - 0.02 - t0 / sr) / 0.01
                while last_v + 1 < len(fr) and last_v + 1 < nxt_f and vow(last_v + 1):
                    last_v += 1
                anchors = {last_v}
                in_word = max((j for j in range(len(fr)) if j <= (w["end"] - t0 / sr) / 0.01 and vow(j)), default=None)
                if in_word is not None:
                    anchors.add(in_word)
                hiss = max(sum(1 for j in range(a0 + 1, min(len(fr), a0 + 13)) if lv[j] > -45 and cen[j] >= 2500) for a0 in anchors)
                if hiss < 2:
                    t = fr[last_v][0] / sr
                    flags.append(G.flag("A5", f"end:{G.wkey(w['w'], w['end'])}", t, w["w"],
                                        f"{w['beat']}: {w['w']!r} (said \"{said}\") ends on its vowel: no {fric!r} after it (under 20 ms of "
                                        f"frication over -45 dB in the 120 ms after) - the take says it cut short (\"fi\" for \"five\")",
                                        part="END", beat=w["beat"]))
        if "WORD" in parts:
            lf = G.frame_db(x, sr, 0.01)
            low = []
            for s in S:
                vals = []
                for w in s:
                    a = int(w["start"] / 0.01)
                    b = max(a + 1, int(round(w["end"] / 0.01)))
                    seg = lf[a:b]
                    vals.append((w, float(np.percentile(seg, 90)) if len(seg) else -120.0, int((seg > -35).sum())))
                good = [v for _, v, n in vals if n >= 10]
                if len(good) < 3:
                    continue
                ref = float(np.median(good))
                for w, v, n in vals:
                    k = G.key(w["w"].replace("’", "'"))
                    if n >= 10 and w["w"].lower().strip('.,!?;:"\'”“') not in FUNC and k not in FUNC:
                        low.append(v - ref)
                        if v - ref <= WORD_BAR:
                            flags.append(G.flag("A5", f"word:{G.wkey(w['w'], w['start'])}", w["start"], w["w"],
                                                f"{w['beat']}: {w['w']!r} {ref - v:.1f} dB under its sentence (whispered or swallowed?)",
                                                part="WORD", beat=w["beat"]))
            info["content_words_measured"] = len(low)
    flags.sort(key=lambda f: f["t"])
    res = {"check": "A5", "final": str(P["final"]), "flags": flags, **info}
    if not quiet:
        c = {p: (sum(1 for f in flags if f.get("part") == p) if p in parts else "-") for p in ("WORDS", "END", "LEVEL", "WORD")}
        print(f"A5 takes: {len(W)} words; WORDS {c.get('WORDS', 0)} differences from the script, END {c.get('END', 0)} phrase ends cut short "
              f"(of {info.get('end_checked')}), LEVEL {c.get('LEVEL', 0)} sentences "
              f"over {LU_BAR} LU (spread {info.get('sentence_lu_spread')}), WORD {c.get('WORD', 0)} words {abs(WORD_BAR):.0f} dB under")
        G.print_flags(res)
    return res


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--beats-only", help="comma list of beat ids")
    ap.add_argument("--parts", default="WORDS,END,LEVEL,WORD")
    a = ap.parse_args()
    res = run(G.paths_from(a), beats_only=set(a.beats_only.split(",")) if a.beats_only else None, parts=tuple(a.parts.split(",")))
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
