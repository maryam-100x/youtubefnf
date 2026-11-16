"""Voice metrics: how a narration's words are shaped, measured the same way on real YouTubers and on the creator's scripts. Each
feature is per 1,000 words unless it says otherwise; the comparison prints where the scripts sit against the human corpus (median and
the middle half), worst gap first. tell_lint.py --style and pair_test.py --features use its features.

  PIPE tools/script/voice_metrics.py compare [--ours 12,13,...] [--groups talk,voice,tech,doc] [--table]
  PIPE tools/script/voice_metrics.py one <script.md | text file>

The human corpus is tools/script/human_corpus.py's (MEDIA/script/human_corpus/text/). The scripts: the newest Beats block of
videos/<id>*/script.md (script_lint's parser). "source_says" counts the niche's quoted sources (niche.json "source_names") saying
something."""
import argparse
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
from paths import VIDEOS_REPO  # noqa: E402
from script_lint import alt, niche_words  # noqa: E402

STOP = set("""a an the and or but so to of in on at for from by with as is are was were be been being it its this that these those they them their
there here he she his her him we our you your i me my not no do does did have has had will would can could should may might must if then than
too very just also even still more most some any all each every what which who when where why how up down out over into about after before""".split())


def words(t):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", t)


def sentences(t):
    t = re.sub(r"\s+", " ", t).strip()
    parts = re.split(r"(?<=[.!?])[\"”']?\s+(?=[\"“']?[A-Z0-9])", t)
    return [p.strip() for p in parts if len(words(p)) > 0]


def per_k(n, w):
    return 1000.0 * n / max(1, w)


def count(rx, t, flags=re.I):
    return len(re.findall(rx, t, flags))


# ---- the features --------------------------------------------------------------------------------------------------------------------
MARKERS = {   # how people talk while they think: discourse markers and fillers
    "so_open": r"(?:^|[.!?]\s+)so\b", "like_disc": r"(?:,\s*like,|^like,|[.!?]\s+like,|\blike,? you know\b|\band like\b|\bit'?s like\b|\bwas like\b|\bjust like that\b)",
    "basically": r"\bbasically\b", "actually": r"\bactually\b", "literally": r"\bliterally\b", "obviously": r"\bobviously\b",
    "honestly": r"\bhonestly\b", "really": r"\breally\b", "pretty_adv": r"\bpretty (?:much|good|big|cool|sure|crazy|insane|wild|bad|clear|obvious|close|hard|easy|fast|well|normal|weird|funny|similar|[a-z]+ly)\b",
    "kinda": r"\b(?:kinda|kind of|sort of|sorta)\b", "i_mean": r"\bi mean\b", "you_know": r"\byou know\b(?! (?:what|how|who|where|when|why|that|the|it|if|about))",
    "i_guess": r"\bi guess\b", "i_feel_like": r"\bi feel like\b", "right_q": r"\bright\?", "okay": r"\b(?:okay|ok|alright|all right)\b",
    "well_open": r"(?:^|[.!?]\s+)well,", "anyway": r"\banyways?\b", "just": r"\bjust\b", "even": r"\beven\b", "though": r"\bthough\b",
    "gonna": r"\b(?:gonna|wanna|gotta)\b", "now_disc": r"(?:^|[.!?]\s+)now,? ",
}
STANCE = {
    "i_think": r"\bi (?:think|thought|believe|bet|reckon|doubt)\b", "probably": r"\b(?:probably|maybe|perhaps)\b",
    "evaluative": r"\b(?:insane|crazy|cool|awesome|amazing|wild|sick|huge|massive|ridiculous|stupid|dumb|funny|hilarious|weird|nuts|absurd|"
                  r"incredible|impressive|beautiful|gorgeous|ugly|terrible|horrible|disgusting|epic|nice|sweet|brutal|wtf|lol|bro|dude|man,)\b",
    "love_hate": r"\b(?:love|loved|hate|hated|can'?t stand|obsessed|excited|hyped|worried|scared|disappointed)\b",
    "intensifier": r"\b(?:so|super|really|extremely|incredibly|insanely|ridiculously|absolutely|totally|completely)\s+(?:good|bad|big|cool|much|many|fast|slow|hard|easy|real|detailed|important|close|far|weird|funny|crazy|insane|small)\b",
}
VIEWER = {
    "i": r"\b(?:i|i'm|i've|i'd|i'll|me|my|myself)\b", "you": r"\b(?:you|you're|you've|you'd|you'll|your|yourself)\b",
    "we": r"\b(?:we|we're|we've|we'd|we'll|us|our)\b", "guys": r"\b(?:you guys|guys|y'all|folks|everyone|everybody)\b",
    "deixis": r"\b(?:look at|you can see|as you can see|right here|over here|check (?:this|it) out|take a look|notice how|see (?:this|that|how|here)|watch (?:this|how)|this (?:guy|one|part|shot|clip|right here))\b",
    "q": r"\?",
}
_SOURCES = alt([w.lower() for w in niche_words("source_names")])
EXPLAINER = {   # the textbook shape: naming and defining
    "called": r"\b(?:is called|are called|was called|it'?s called|that'?s called|they'?re called|called it|known as|stands for|short for|the word for|the term for)\b",
    "which_is": r"\b(?:which is|which means|that means|meaning|in other words|basically means|refers to|is when|that'?s when)\b",
    "attribution": r"\b(?:says|said|according to|reported|reports|told|claims|claimed|thinks|believes|explained)\b",
    "source_says": (rf"\b(?:{_SOURCES})\b[^.?!]{{0,30}}\b(?:says|said|thinks|calls|hasn'?t said|told|confirmed)\b" if _SOURCES else r"(?!x)x"),
    "hasnt_said": r"\bhas(?:n'?t| not) (?:said|confirmed|shown|announced|explained|revealed)\b",
}
LLM = {   # constructions that LLM prose leans on
    "reframe": r"\b(?:it|that|this|he|she|they|which)(?:'s| is| was|'re| are| were)(?: not|n'?t)\b[^.?!;]{1,60}[,;:—-]\s*(?:it|that|this|he|she|they)(?:'s| is| was|'re| are| were)\b"
               r"|\bnot (?:just|only|merely|simply)\b[^.?!]{1,50}\b(?:but|it'?s|it is|they'?re)\b"
               r"|\b(?:doesn'?t|don'?t|didn'?t) (?:make|mean|change)\b[^.?!]{1,40}[,;.]\s*(?:it|that)?\s*(?:makes|means|changes)\b",
    "pseudo_cleft": r"(?:^|[.!?]\s+)(?:what|where|why|how|all) [^.?!,]{2,50}\b(?:is|was|'s)\b (?!it\b)",
    "heres": r"\bhere'?s (?:what|the|why|how|where|a|one)\b",
    "colon": r":",
    "triplet": r"\b\w+(?: \w+){0,3}, \w+(?: \w+){0,3},? (?:and|or) \w+",
    "every_single": r"\b(?:every single|all of (?:it|that|them)|down to the|from [^.?!,]{1,25} to [^.?!,]{1,25}(?:,|\.| and))",
    "so_conclude": r"(?:^|[.!?]\s+)so (?:that'?s|this|it'?s|the|if|even|yes|basically|in the end|whatever|anyway)\b",
    "thats_why": r"\bthat'?s (?:why|what|how|the reason|exactly)\b",
}


def shape(text):
    """The rhythm: sentence lengths and openers."""
    ss = sentences(text)
    lens = [len(words(s)) for s in ss]
    if not lens:
        return {}
    mean = st.mean(lens)
    sd = st.pstdev(lens) if len(lens) > 1 else 0.0
    openers = Counter((words(s)[0].lower() if words(s) else "") for s in ss)
    n = len(ss)
    # how often a sentence's length is close to the one before (within 3 words): uniform rhythm
    close = sum(1 for a, b in zip(lens, lens[1:]) if abs(a - b) <= 3) / max(1, n - 1)
    return {"sentences": n, "wps": round(mean, 1), "wps_sd": round(sd, 1), "wps_cv": round(sd / mean, 2) if mean else 0,
            "short_share": round(sum(1 for x in lens if x <= 5) / n, 3), "long_share": round(sum(1 for x in lens if x >= 25) / n, 3),
            "even_rhythm": round(close, 3),
            "open_and": round(openers["and"] / n, 3), "open_but": round(openers["but"] / n, 3), "open_so": round(openers["so"] / n, 3),
            "open_i": round((openers["i"] + openers["i'm"] + openers["i've"] + openers["i'd"]) / n, 3),
            "open_it_that": round(sum(openers[k] for k in ("it", "it's", "that", "that's", "this", "there", "there's")) / n, 3),
            "open_the": round((openers["the"] + openers["a"]) / n, 3)}


def lexical(text):
    ws = [w.lower().replace("’", "'") for w in words(text)]
    n = len(ws)
    if n < 50:
        return {}
    win = 100
    mattr = st.mean(len(set(ws[i:i + win])) / win for i in range(0, max(1, n - win), 10)) if n > win else len(set(ws)) / n
    content = [w for w in ws if w not in STOP]
    contractions = sum(1 for w in ws if re.search(r"(n't|'re|'ve|'ll|'d|'m)$", w) or w in ("it's", "that's", "there's", "what's", "he's",
                                                                                        "she's", "let's", "here's", "who's", "where's"))
    numbers = len(re.findall(r"\b(?:\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fifteen|twenty|"
                             r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)\b", " ".join(ws)))
    return {"words": n, "mattr": round(mattr, 3), "word_len": round(st.mean(len(w) for w in ws), 2),
            "content_share": round(len(content) / n, 3), "contractions": round(per_k(contractions, n), 1), "numbers": round(per_k(numbers, n), 1)}


def features(text, punctuated=True):
    """Every feature of one text; the rhythm only where the text has real sentence ends (an old unpunctuated caption track is one
    run of words)."""
    text = text.replace("’", "'").replace("‘", "'")
    w = len(words(text))
    f = {}
    f.update(lexical(text))
    if punctuated:
        f.update(shape(text))
    low = text.lower()
    for table in (MARKERS, STANCE, VIEWER, EXPLAINER, LLM):
        for k, rx in table.items():
            f[k] = round(per_k(count(rx, low if k not in ("colon",) else text), w), 2)
    f["markers_all"] = round(sum(f[k] for k in MARKERS if k not in ("just", "even", "though")), 2)
    f["explainer_all"] = round(f["called"] + f["which_is"], 2)
    f["llm_all"] = round(f["reframe"] + f["pseudo_cleft"] + f["heres"] + f["so_conclude"], 2)
    return f


# ---- sources ---------------------------------------------------------------------------------------------------------------------------
def our_scripts(ids=None):
    import script_lint as L
    out = {}
    for p in sorted(VIDEOS_REPO.glob("*/script.md")) if VIDEOS_REPO.exists() else []:
        vid = p.parent.name
        if ids and not any(vid.startswith(i) for i in ids):
            continue
        lines, _ = L.load_lines(str(p))
        if not lines:
            continue
        text = " ".join(t for _, t, _ in lines)
        if len(words(text)) >= 120:
            out[vid] = text
    return out


def human(groups=None):
    import human_corpus as H
    out = {}
    for h, body in H.load():
        if groups and h.get("group") not in groups:
            continue
        out[f"{h['group']}:{h['channel']}:{h['id']}"] = (body, h.get("punctuated", True))
    return out


def compare(ours, hum, keys=None):
    hf = {k: features(*v) for k, v in hum.items()}
    of = {k: features(v) for k, v in ours.items()}
    if not hf or not of:
        print("nothing to compare: build the human corpus (tools/script/human_corpus.py) and write a script first")
        return hf, of
    keys = keys or [k for k in next(iter(hf.values())).keys() if k not in ("words", "sentences")]
    rows = []
    for k in keys:
        hv = sorted(x[k] for x in hf.values() if k in x)
        ov = [x[k] for x in of.values() if k in x]
        if len(hv) < 4 or not ov:
            continue
        q1, med, q3 = hv[len(hv) // 4], st.median(hv), hv[(3 * len(hv)) // 4]
        spread = max(q3 - q1, 1e-6)
        om = st.median(ov)
        rows.append((abs(om - med) / spread, k, med, q1, q3, om, sum(1 for x in ov if q1 <= x <= q3), len(ov)))
    rows.sort(reverse=True)
    print(f"{'feature':<16} {'humans: median [middle half]':>30} {'ours median':>12} {'ours inside':>12}  gap")
    for gap, k, med, q1, q3, om, inside, n in rows:
        print(f"{k:<16} {med:>12.2f} [{q1:>6.2f} - {q3:>6.2f}] {om:>12.2f} {inside:>8}/{n:<3}  {gap:5.1f}")
    return hf, of


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--ours", default="")
    c.add_argument("--groups", default="talk,voice,tech,doc")
    c.add_argument("--table", action="store_true", help="print every text's features too")
    o = sub.add_parser("one")
    o.add_argument("path")
    a = ap.parse_args()
    if a.cmd == "one":
        p = Path(a.path)
        import script_lint as L
        lines, raw = L.load_lines(str(p))
        text = " ".join(t for _, t, _ in lines)
        for k, v in features(text).items():
            print(f"{k:<16} {v}")
        return
    ours = our_scripts([x for x in a.ours.split(",") if x] or None)
    hum = human([g for g in a.groups.split(",") if g])
    print(f"humans: {len(hum)} texts, {sum(len(words(t)) for t, _ in hum.values())} words; ours: {len(ours)} scripts, "
          f"{sum(len(words(t)) for t in ours.values())} words\n")
    hf, of = compare(ours, hum)
    if a.table:
        for name, f in list(hf.items()) + list(of.items()):
            print(name[:40], {k: f.get(k) for k in ("wps", "wps_cv", "markers_all", "i", "you", "q", "explainer_all", "llm_all", "evaluative")})


# ---- one text against the human ranges (the check every new script gets) -----------------------------------------------------------
KEY = ["wps", "wps_sd", "wps_cv", "long_share", "short_share", "even_rhythm", "contractions", "numbers", "i", "you", "we", "q",
       "markers_all", "evaluative", "probably", "attribution", "explainer_all", "called", "even", "every_single", "triplet", "llm_all",
       "deixis", "open_the", "content_share", "word_len"]


def ranges(groups=("voice", "ref", "tech", "doc")):
    """Each feature's human spread over the punctuated texts of the chosen groups: (10th, 25th, 50th, 75th, 90th percentile)."""
    hum = human(list(groups))
    fs = [features(t, p) for t, p in hum.values() if p]
    out = {}
    for k in KEY:
        v = sorted(f[k] for f in fs if k in f)
        if len(v) >= 5:
            q = lambda x: v[min(len(v) - 1, int(round(x * (len(v) - 1))))]
            out[k] = (q(0.1), q(0.25), q(0.5), q(0.75), q(0.9))
    return out, len(fs)


def versus(text, groups=("voice", "ref", "tech", "doc")):
    rg, n = ranges(groups)
    f = features(text)
    rows = []
    for k in KEY:
        if k not in rg or k not in f:
            continue
        p10, p25, p50, p75, p90 = rg[k]
        v = f[k]
        flag = "LOW" if v < p10 else "high" if v > p90 else "low" if v < p25 else "HIGH" if v > p75 else ""
        flag = {"LOW": "LOW (under 9 in 10 humans)", "high": "HIGH (over 9 in 10 humans)", "low": "low", "HIGH": "high"}.get(flag, "")
        rows.append((k, v, p10, p50, p90, flag))
    print(f"against {n} human narrations (10th / median / 90th percentile)")
    for k, v, p10, p50, p90, flag in rows:
        print(f"  {k:<14} {v:>7.2f}   humans {p10:>6.2f} / {p50:>6.2f} / {p90:>6.2f}   {flag}")
    return f, rg


if __name__ == "__main__":
    main()
