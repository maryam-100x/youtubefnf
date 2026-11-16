"""The voice lock's ear for words (standard/VOICE_LOCK.md "Research"): a CTC acoustic model that reads letters off the audio, used
three ways by the lock's tools:
  - align(x, sr, text)   the known words forced onto the audio (torchaudio.functional.forced_align): word start/end from the sound,
                         never ElevenLabs' character times (they can run up to 0.5 s late: a sentence's last word lands on the
                         breath after it) and never Whisper's (its word edges come from cross-attention: F1 64 at 50 ms against 80
                         for wav2vec2 alignment and 91 for MFA, arXiv 2509.09987);
  - greedy(x, sr)        free decoding: the letters the model hears, with their times (A10 asks: did it hear letters where the
                         script has none?);
  - words_of(text)       the script's words as the model spells them (numbers said out: "16th" -> SIXTEENTH, "2049" -> TWENTY
                         FORTY NINE, "$15" -> FIFTEEN DOLLARS).

The model: torchaudio's WAV2VEC2_ASR_LARGE_LV60K_960H (MIT; English letters + "'" + "|"; 20-ms frames; 1.18 GB in
~/.cache/torch/hub/checkpoints). torchaudio kept forced_align when it went to maintenance (2.10 release notes). MFA aligns closer
(18 ms mean on TIMIT against ~27-46 for CTC aligners, Aligner-SUPERB 2025-05) but needs conda + Kaldi; every edge the lock anchors is
also snapped to the measured onset (voice_layin.onset), so the CTC frame is only the guess the audio search starts from.

Runs in the editing venv (EDIT; torch on the CPU, 2 threads, since another job may be using the CPU)."""
import re
from functools import lru_cache

import numpy as np

FRAME = 0.02          # s per emission frame (16 kHz / 320)
SR16 = 16000

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
ABBR = {"dr": "doctor", "mr": "mister", "mrs": "missus", "vs": "versus", "jr": "junior", "sr": "senior", "etc": "et cetera", "&": "and",
        "approx": "approximately", "feat": "featuring"}
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}


@lru_cache(maxsize=1)
def _model():
    import os
    import torch
    import torchaudio
    # 2 threads (VOICE_TORCH_THREADS sets it): 4 with three autopicks at once put the CPU at 100%, and the CTC stage went from
    # 23-31 s to 36-53 s a take (oversubscribed); Whisper runs on the GPU instead, off the CPU
    torch.set_num_threads(int(os.environ.get("VOICE_TORCH_THREADS", "2")))
    b = torchaudio.pipelines.WAV2VEC2_ASR_LARGE_LV60K_960H
    m = b.get_model().eval()
    labels = b.get_labels()
    return m, labels, {c: i for i, c in enumerate(labels)}


def _int_words(n):
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    for div, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand"), (100, "hundred")):
        if n >= div:
            hi, lo = divmod(n, div)
            return _int_words(hi) + " " + name + ("" if lo == 0 else " " + _int_words(lo))
    return str(n)


def _year_words(n):
    """1990 -> nineteen ninety, 2014 -> twenty fourteen, 2001 -> two thousand one, 2000 -> two thousand"""
    if 2000 <= n <= 2009:
        return "two thousand" + ("" if n == 2000 else " " + ONES[n - 2000])
    hi, lo = divmod(n, 100)
    return _int_words(hi) + " " + ("hundred" if lo == 0 else (("oh " + ONES[lo]) if lo < 10 else _int_words(lo)))


def _ordinal(words):
    *head, last = words.split()
    if last in ORD:
        last = ORD[last]
    elif last.endswith("y"):
        last = last[:-1] + "ieth"
    else:
        last = last + "th"
    return " ".join(head + [last])


def say_token(tok):
    """one written token -> the words a voice says for it (lower case, spaces); letters only, so the model can spell them"""
    t = tok.replace("’", "'").strip()
    t = re.sub(r"^[\"(\[]+|[\"')\].,;:!?…]+$", "", t)
    if t.lower().rstrip(".") in ABBR:
        return ABBR[t.lower().rstrip(".")]
    m = re.fullmatch(r"([\d,.$%]+(?:st|nd|rd|th)?)'s", t)
    if m:                                            # 2017's, 7's: the number, then the possessive
        return say_token(m[1]) + "'s"
    m = re.fullmatch(r"\$([\d,]+(?:\.\d+)?)([kmb]|bn)?", t, re.I)
    if m:
        return say_token(m[1]) + ({"k": " thousand", "m": " million", "b": " billion", "bn": " billion"}.get((m[2] or "").lower(), "")) + " dollars"
    m = re.fullmatch(r"([\d,]+(?:\.\d+)?)%", t)
    if m:
        return say_token(m[1]) + " percent"
    m = re.fullmatch(r"(\d+)(st|nd|rd|th)", t, re.I)
    if m:
        return _ordinal(_int_words(int(m[1])))
    m = re.fullmatch(r"(\d+)s", t)
    if m and len(m[1]) == 4:
        y = _year_words(int(m[1]))          # 1990s -> nineteen nineties, 2000s -> two thousands
        return y[:-1] + "ies" if y.endswith("y") else y + "s"
    if re.fullmatch(r"\d{4}", t) and 1100 <= int(t) <= 2099:
        return _year_words(int(t))
    if re.fullmatch(r"\d{1,3}(,\d{3})+|\d+", t):
        return _int_words(int(t.replace(",", "")))
    m = re.fullmatch(r"(\d+)\.(\d+)", t)
    if m:
        return _int_words(int(m[1])) + " point " + " ".join(ONES[int(c)] for c in m[2])
    if re.fullmatch(r"[A-Z0-9]{2,5}", t) and not re.fullmatch(r"[IVX]+", t):   # FBI, MP3, MF: said letter by letter
        return " ".join(ONES[int(c)] if c.isdigit() else c.lower() for c in t)
    parts = re.split(r"[-/]", t)
    if len(parts) > 1:
        return " ".join(say_token(p) for p in parts if p)
    return re.sub(r"[^a-z']", "", t.lower())


def spelled(tok):
    """a token said letter by letter (FBI, TV, MP3, iOS): its letters' names ('eye', 'oh') aren't its letters, so the free decoding
    can't be held to them"""
    t = re.sub(r"[^A-Za-z0-9]", "", tok.replace("'s", ""))
    return bool(re.fullmatch(r"[A-Z0-9]{2,5}", t) and not re.fullmatch(r"[IVX]+|\d+", t)) or bool(
        re.fullmatch(r"[a-z]?[A-Z][A-Za-z]{0,3}", t) and sum(c.isupper() for c in t) >= 1 and len(t) <= 4 and not t.istitle())


def words_of(text):
    """the script's text -> [(written token, [model words])]"""
    out = []
    for tok in text.split():
        said = [w for w in say_token(tok).split() if re.sub(r"[^a-z]", "", w)]
        out.append((tok, [w.upper() for w in said]))
    return out


def emissions(x, sr):
    """log-probabilities (frames, labels) of mono float audio x"""
    import torch
    import torchaudio
    m, _, _ = _model()
    w = torch.tensor(np.asarray(x, dtype=np.float32))[None]
    if sr != SR16:
        w = torchaudio.functional.resample(w, sr, SR16)
    with torch.inference_mode():
        em, _ = m(w)
    return torch.log_softmax(em, dim=-1)[0].numpy()


def greedy(x, sr, em=None):
    """free decoding -> [{"c": letter, "t0", "t1"}] (word breaks as "|"), the letters' frames in seconds"""
    _, labels, _ = _model()
    em = emissions(x, sr) if em is None else em
    ids = em.argmax(1)
    out, prev = [], 0
    for i, k in enumerate(ids):
        if k != prev and k != 0:
            out.append({"c": labels[k], "t0": i * FRAME, "t1": (i + 1) * FRAME, "p": float(np.exp(em[i, k]))})
        elif k == prev and k != 0 and out:
            out[-1]["t1"] = (i + 1) * FRAME
        prev = k
    return out


def greedy_text(chars):
    return "".join(c["c"] for c in chars).replace("|", " ").strip()


def align(x, sr, text, em=None):
    """the script's text forced onto the audio -> [{"w": written token, "start", "end", "score"}] in seconds from x's start (a token
    said as several words, "16th" = SIXTEENTH, "2049" = TWENTY FORTY NINE, spans them all). Raises ValueError if the audio is too
    short for the letters."""
    import torch
    import torchaudio.functional as F
    _, labels, idx = _model()
    em = emissions(x, sr) if em is None else em
    toks = words_of(text)
    flat, owner = [], []
    for ti, (_, ws) in enumerate(toks):
        for w in ws:
            for c in w:
                if c in idx:
                    flat.append(idx[c])
                    owner.append(ti)
            flat.append(idx["|"])
            owner.append(-1)
    flat, owner = flat[:-1], owner[:-1]
    if not flat:
        return []
    if len(flat) > em.shape[0]:
        raise ValueError(f"{len(flat)} letters in {em.shape[0]} frames")
    al, sc = F.forced_align(torch.tensor(em)[None], torch.tensor([flat], dtype=torch.int32), blank=0)
    spans = F.merge_tokens(al[0], sc[0].exp())
    res = [{"w": tok, "start": None, "end": None, "p": []} for tok, _ in toks]
    for s, o in zip(spans, owner):
        if o < 0:
            continue
        r = res[o]
        r["start"] = s.start * FRAME if r["start"] is None else r["start"]
        r["end"] = s.end * FRAME
        r["p"].append(float(s.score))
    out = []
    for r in res:
        if r["start"] is None:
            continue
        out.append({"w": r["w"], "start": round(r["start"], 3), "end": round(r["end"], 3), "score": round(float(np.mean(r["p"])), 3)})
    return out
