"""Lingo, measured: the words and phrases the niche's real YouTubers use far more than the creator's scripts do, and the reverse
(a script is more than what is said: it is also the lingo).

  PIPE tools/script/lingo_measure.py [--groups talk,voice,tech,ref] [--top 60] [--min 8]

Three sides: the human corpus (tools/script/human_corpus.py), the scripts (every videos/*/script.md's newest VOICE lines) and the
creator's own dictated words (MEDIA/script/lingo/corpus/CREATOR_dictated_.txt, written by lingo_corpus.py). For words and 2-3 word
phrases it ranks the log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi & Quinn 2008): a z-score per item, so a word
that is rare everywhere doesn't top the list by luck. Then the rates per 1,000 words of named families: slang and hype words,
fillers, how numbers, dates and people are said. Caveat: YouTube's auto captions write "going to" for "gonna" and drop most "um";
those two can't be compared."""
import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
from paths import MEDIA  # noqa: E402

CREATOR = MEDIA / "script" / "lingo" / "corpus" / "CREATOR_dictated_.txt"


def toks(t):
    t = t.lower().replace("’", "'")
    return re.findall(r"[a-z][a-z']*|\d[\d,.]*", t)


def grams(ws, n):
    return [" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)]


def logodds(a, b, prior, min_count):
    """z-scores of a vs b with the pooled counts as the prior (Monroe et al. 2008)."""
    na, nb, n0 = sum(a.values()), sum(b.values()), sum(prior.values())
    out = {}
    for w in set(a) | set(b):
        if a[w] + b[w] < min_count:
            continue
        p = prior[w] + 0.01
        la = math.log((a[w] + p) / (na + n0 - a[w] - p))
        lb = math.log((b[w] + p) / (nb + n0 - b[w] - p))
        var = 1 / (a[w] + p) + 1 / (b[w] + p)
        out[w] = (la - lb) / math.sqrt(var)
    return out


FAMILIES = {
    "hype/slang": r"\b(?:insane|crazy|wild|sick|nuts|massive|huge|cooked|cook|goated|peak|fire|banger|mid|cracked|stacked|bonkers|"
                  r"unreal|ridiculous|absurd|legendary|iconic|w|l|bro|dude|man,|guys|y'all|lowkey|highkey|ngl|lol|glazing|glaze|fumbled|"
                  r"based|hype|hyped|vibe|vibes)\b",
    "fillers/markers": r"\b(?:like|basically|literally|actually|honestly|obviously|pretty|kinda|kind of|sort of|i mean|you know|right|okay|ok|"
                       r"anyway|so yeah|yeah|well)\b",
    "hedges": r"\b(?:i think|i guess|i feel like|probably|maybe|i'm not sure|i don't know|apparently|seems like|looks like)\b",
    "rough numbers": r"\b(?:like|about|around|roughly|almost|nearly|over|more than|something like|close to)\s+(?:\d|a\s+(?:hundred|thousand|million|billion)|"
                     r"half|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)",
    "exact numbers": r"\b\d[\d,.]*\b|\b(?:eleven|twelve|thirteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)\b",
    "dates in full": r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(?:\d|first|second|third|"
                     r"[a-z]+teenth|[a-z]+tieth)|\bin (?:19|20)\d\d\b",
    "loose time": r"\b(?:back in|back then|a while ago|years ago|these days|right now|at this point|nowadays|by now|at the time)\b",
    "report-speak": r"\b(?:notably|it'?s worth noting|worth noting|additionally|furthermore|moreover|however|according to|reportedly|"
                    r"significant(?:ly)?|crucial|key|ultimately|essentially|in addition|as well as|respectively|approximately|"
                    r"which means|meaning|known as|called)\b",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--groups", default="talk,voice,tech,ref")
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--min", type=int, default=8)
    a = ap.parse_args()
    import human_corpus as H
    import voice_metrics as V
    groups = set(a.groups.split(","))
    hum = " ".join(b for h, b in H.load() if h.get("group") in groups)
    ours = " ".join(V.our_scripts().values())
    creator = CREATOR.read_text(encoding="utf-8") if CREATOR.exists() else ""
    sides = {"humans": toks(hum), "ours": toks(ours), "creator": toks(creator)}
    print("words: " + ", ".join(f"{k} {len(v):,}" for k, v in sides.items()))
    if not sides["humans"] or not sides["ours"]:
        print("needs the human corpus (tools/script/human_corpus.py) and at least one script")
        return
    for n in (1, 2, 3):
        c = {k: Counter(grams(v, n)) for k, v in sides.items()}
        prior = c["humans"] + c["ours"] + c["creator"]
        z = logodds(c["humans"], c["ours"], prior, a.min * (1 if n == 1 else 1))
        hi = sorted(z.items(), key=lambda kv: -kv[1])[:a.top]
        lo = sorted(z.items(), key=lambda kv: kv[1])[:a.top]
        per = lambda side, w: 1000 * c[side][w] / max(1, len(sides[side]))
        print(f"\n== {n}-grams HUMANS use far more (per 1,000 words: humans / ours / creator)")
        print("; ".join(f"{w} {per('humans', w):.2f}/{per('ours', w):.2f}/{per('creator', w):.2f}" for w, _ in hi))
        print(f"\n== {n}-grams WE use far more (humans / ours / creator)")
        print("; ".join(f"{w} {per('humans', w):.2f}/{per('ours', w):.2f}/{per('creator', w):.2f}" for w, _ in lo))
    print("\n== families per 1,000 words (humans / ours / creator)")
    for name, rx in FAMILIES.items():
        r = {k: 1000 * len(re.findall(rx, " ".join(v))) / max(1, len(v)) for k, v in sides.items()}
        print(f"{name:<16} {r['humans']:>6.1f} / {r['ours']:>6.1f} / {r['creator']:>6.1f}")


if __name__ == "__main__":
    main()
