"""Was a name said the American way? (the voice lock's general name check; standard/VOICE_LOCK.md "Research").
A name respelled for the voice can still come out in its native language in some takes, and the ear hears it. A formant measure
(an r-coloured vowel: voiced F3 under 1750 Hz for 50 ms+) sorts such takes, but only for a name with an r. This one works for any
name with an entry in names.json "ipa":

  - a phoneme recognizer (facebook/wav2vec2-xlsr-53-espeak-cv-ft: CTC over 392 espeak phonemes from 53 languages, so it has the
    Spanish tap ɾ and the American ɹ, e and ə, a+ʝ and aɪ, o and oʊ as separate symbols; Apache-2.0; ~1.26 GB in the HF cache)
    reads the name's audio (its span from the CTC word aligner, ctcalign.py, padded 0.1 s);
  - competing hypotheses (GOP-SF, arXiv 2507.16838): the CTC loss of each American pronunciation against each native one over the
    same frames; margin = best native loss - best American loss (per frame of the span). Positive = American.
  - verdict: AMERICAN at margin >= US_MARGIN, NATIVE at <= -US_MARGIN, else UNSURE (autopick and voice_ready treat UNSURE as a fail).
    The free decoding (what the model heard) is printed as the reason.

names.json, per respelled name: "ipa": {"us": <pattern(s)>, "native": <pattern(s)>}: phonemes space-separated, from the model's own
symbols (an unknown symbol stops the check), "{a|b}" for each spot where either sound is fine. Write them as MINIMAL PAIRS: the two
patterns differ only in the sounds the ear judges (Maribel Ferrer: the r, ɹ against the tap ɾ or the trill r; the vowels around it
open in both, since a take with a plain vowel there can pass the ear while a vowel-strict pair calls it UNSURE).

  EDIT tools/voice/saycheck.py <wav> --name "Maribel Ferrer" --text "<what the wav says>"
  EDIT tools/voice/saycheck.py <wav> --name "Maribel Ferrer" --at <t0> <t1>
  EDIT tools/voice/saycheck.py --video <video> [--beats S12 S13] [--final F]
      (every respelled name with "ipa" in the narration, its span from the edit's words)"""
import argparse
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import TOOLS  # noqa: E402
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sound"))
NAMES = TOOLS / "sound" / "names.json"
MODEL = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
US_MARGIN = 0.05      # nats per frame; calibrated on six ear verdicts (standard/VOICE_LOCK.md, the proof)
PAD = 0.10


@lru_cache(maxsize=1)
def _model():
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import Wav2Vec2ForCTC
    torch.set_num_threads(int(__import__("os").environ.get("VOICE_TORCH_THREADS", "2")))   # 2: ctcalign.py's note
    m = Wav2Vec2ForCTC.from_pretrained(MODEL).eval()
    vocab = json.loads(Path(hf_hub_download(MODEL, "vocab.json")).read_text(encoding="utf-8"))
    return m, vocab, {i: s for s, i in vocab.items()}


def emissions(x, sr):
    import torch
    import torchaudio
    m, _, _ = _model()
    w = torch.tensor(np.asarray(x, dtype=np.float32))[None]
    if sr != 16000:
        w = torchaudio.functional.resample(w, sr, 16000)
    w = (w - w.mean()) / (w.std() + 1e-7)          # the feature extractor's normalisation
    with torch.inference_mode():
        lg = m(w).logits[0]
    return torch.log_softmax(lg, -1)


def heard(em):
    _, _, inv = _model()
    ids = em.argmax(-1).tolist()
    out, prev = [], None
    for k in ids:
        if k != prev and k != 0:
            out.append(inv[k])
        prev = k
    return " ".join(out)


def loss(em, phones):
    """CTC loss of a phoneme string over the frames, per frame"""
    import torch
    _, vocab, _ = _model()
    seq = phones.split()
    bad = [p for p in seq if p not in vocab]
    if bad:
        raise SystemExit(f"unknown phoneme(s) {bad} in {phones!r}: use the model's symbols (vocab.json)")
    tgt = torch.tensor([vocab[p] for p in seq])[None]
    T = em.shape[0]
    v = torch.nn.functional.ctc_loss(em[:, None, :], tgt, torch.tensor([T]), torch.tensor([len(seq)]), blank=0, reduction="sum",
                                     zero_infinity=True)
    return float(v) / T


def expand(pats):
    """"k {aɪ oʊ|a j o} p" -> every variant; a list of patterns -> all of theirs"""
    out = []
    for p in ([pats] if isinstance(pats, str) else pats):
        m = re.search(r"\{([^{}]*)\}", p)
        if not m:
            out.append(" ".join(p.split()))
            continue
        out += expand([p[:m.start()] + alt + p[m.end():] for alt in m[1].split("|")])
    return list(dict.fromkeys(out))


def judge(x, sr, t0, t1, ipa):
    """-> {"margin", "verdict", "us", "native", "heard"} for the name said in x[t0:t1]"""
    a, b = max(0, int((t0 - PAD) * sr)), min(len(x), int((t1 + PAD) * sr))
    em = emissions(x[a:b], sr)
    us = {p: loss(em, p) for p in expand(ipa["us"])}
    nat = {p: loss(em, p) for p in expand(ipa.get("native", ipa.get("wrong", [])))}
    m = min(nat.values()) - min(us.values())
    hi, lo = ipa.get("us_at", US_MARGIN), ipa.get("native_at", -US_MARGIN)   # a name's own calibration, when its contrast is subtle
    v = "AMERICAN" if m >= hi else ("NATIVE" if m <= lo else "UNSURE")
    return {"margin": round(m, 3), "verdict": v, "us": min(us, key=us.get), "native": min(nat, key=nat.get), "heard": heard(em),
            "t0": round(t0, 3), "t1": round(t1, 3)}


def entry(name):
    T = json.loads(NAMES.read_text(encoding="utf-8")).get("names", {})
    e = T.get(name)
    if not e or "ipa" not in e:
        raise SystemExit(f"names.json has no 'ipa' for {name!r}: add its American and native pronunciations first")
    return e["ipa"]


def span_in(x, sr, text, name):
    """the name's [t0, t1] in audio that says `text` (the CTC word aligner on the known words)"""
    import ctcalign as C
    al = C.align(x, sr, text)
    toks = name.split()
    keys = [re.sub(r"[^a-z]", "", re.sub(r"['’]s$", "", w["w"].lower())) for w in al]   # a possessive is its name ("Maribel's recipe")
    want = [re.sub(r"[^a-z]", "", t.lower()) for t in toks]
    out = []
    for i in range(len(keys) - len(want) + 1):
        if keys[i:i + len(want)] == want:
            out.append((al[i]["start"], al[i + len(want) - 1]["end"]))
    return out


def video_spans(video, beats=None, final=None, words=None):
    """[(beat, name, t0, t1)] for every name with 'ipa' said in the narration (the edit's words)"""
    import gatelib as G
    P = G.paths(video, final=final, words=words)
    src = (P["cfg"].get("video") or {}).get("src")
    wp = Path(words) if words else (TOOLS / "motion" / "src" / src / "words.json" if src else P["words"])
    W = G.load_words(wp)
    T = json.loads(NAMES.read_text(encoding="utf-8")).get("names", {})
    names = [n for n, e in T.items() if isinstance(e, dict) and "ipa" in e]
    out = []
    for n in names:
        toks = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in n.split()]
        for i in range(len(W) - len(toks) + 1):
            if all(re.sub(r"[^a-z0-9]", "", W[i + k]["w"].lower().replace("'s", "")) == toks[k] for k in range(len(toks))):
                if beats and W[i]["beat"] not in beats:
                    continue
                out.append((W[i]["beat"], n, W[i]["start"], W[i + len(toks) - 1]["end"]))
    return P, out


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav", nargs="?")
    ap.add_argument("--name")
    ap.add_argument("--text", help="what the wav says (the name found in it by the aligner)")
    ap.add_argument("--at", nargs=2, type=float)
    ap.add_argument("--video")
    ap.add_argument("--beats", nargs="*")
    ap.add_argument("--final")
    ap.add_argument("--words")
    ap.add_argument("--json")
    a = ap.parse_args()
    import soundfile as sf
    res = []
    if a.video:
        P, spans = video_spans(a.video, a.beats, a.final, a.words)
        x, sr = sf.read(str(P["final"]), dtype="float32", always_2d=True)
        x = x.mean(1)
        for beat, n, t0, t1 in spans:
            r = judge(x, sr, t0, t1, entry(n))
            res.append({"beat": beat, "name": n, **r})
    else:
        if not a.wav or not a.name:
            raise SystemExit("give a wav and --name (with --text or --at), or --video")
        x, sr = sf.read(a.wav, dtype="float32", always_2d=True)
        x = x.mean(1)
        spans = [tuple(a.at)] if a.at else span_in(x, sr, a.text, a.name)
        if not spans:
            raise SystemExit(f"{a.name!r} not found in the audio of {a.text!r}")
        for t0, t1 in spans:
            res.append({"name": a.name, **judge(x, sr, t0, t1, entry(a.name))})
    for r in res:
        print(f"{r.get('beat', '')} {r['name']} {r['t0']:.2f}-{r['t1']:.2f}: {r['verdict']} (margin {r['margin']:+.3f}; heard "
              f"{r['heard']!r}; closest American {r['us']!r}, native {r['native']!r})")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    sys.exit(0 if all(r["verdict"] == "AMERICAN" for r in res) else 1)


if __name__ == "__main__":
    main()
