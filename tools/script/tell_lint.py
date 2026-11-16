"""Tell lint: the habits blind judges name on AI-written narration, counted per paragraph. Fix what it flags by rethinking the
sentence, never by swapping the flagged words (a swapped phrase becomes the next tell). It cannot make a passage pass: paragraphs with
no flags still score 0.55-0.65 with the judges when they carry no real person's opinion; the lint only removes the named giveaways.

  PIPE tools/script/tell_lint.py <script.md | text file> [--para]       # --para: every line one paragraph
  PIPE tools/script/tell_lint.py <file> --style [--per-para]            # the pair test's predictors against real creators
  PIPE tools/script/tell_lint.py --validate                             # against every passage the judge panel scored

The habits (each one named by judges on AI passages, with an example):
  gloss      a term or name explained in an add-on ("the co-op, that is a member-owned shop", "Acme, the company that owns Brightline")
  date_open  a sentence that opens on a date ("June 2016, the update ...", "So, March 2019.")
  stats      three or more numbers in one sentence (a stat ladder)
  colon      a colon set-up ("The catch was:", "What he found:")
  fragment   a short verbless restatement for effect ("Two hundred jars, over one summer.", "A record. From one kid.")
  bookend    the last sentence echoes the first (a callback closer)
  turn       a "from X to Y" / "X became Y" antithesis line
  triplet    a list of three for rhythm or as a joke ("a lawyer, a goat and ...")
  teaser     an ending that points ahead ("and that's when ...", "but that was only the start")
  no_person  no first person and no stance in the paragraph (nobody is in it: the judges' "no personal voice")
The niche's own glossed nouns come from tools/script/niche.json ("gloss_nouns")."""
import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from script_lint import alt, niche_words  # noqa: E402

MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_GLOSS_NICHE = alt(niche_words("gloss_nouns"))
RX = {
    "gloss": re.compile(r",\s+(?:that is|that's|which is|so|meaning|the|a|an|its|his|their)\s+(?:the\s+)?(?:company|studio|boss|tool|chat app|"
                        r"city|big|biggest|free|private|first|guy|people|site|store|forum|server|update|bank|thing|team|app|channel|shop"
                        + ("|" + _GLOSS_NICHE if _GLOSS_NICHE else "") + r")\b[^.?!]{0,60}(?:,|\.)", re.I),
    "gloss_means": re.compile(r"\b(?:\w+ )?means(?:,)? (?:you|that|he|it|a|the)\b|\bwhich means\b|\bthat is (?:a|the)\b", re.I),
    "date_open": re.compile(rf"(?:^|[.!?]\s+)(?:So,?\s+|And\s+|Then\s+|In\s+|By\s+|On\s+)?(?:(?:early|late|mid)\s+)?(?:{MONTH}(?:\s+\d{{1,2}}(?:st|nd|rd|th)?)?,?\s+\d{{4}}|"
                         rf"{MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?|\d{{4}}(?:'s)?)\b", re.I),
    "colon": re.compile(r"\b(?:the catch|the problem|the twist|what he found|the result|the promise|the reason|the answer|the deal|here's)\b[^.?!:]{0,20}:", re.I),
    "turn": re.compile(r"\bfrom [^.?!,]{3,40} to (?:one|a|an|the)\b[^.?!]{3,60}|\b(?:became|turned into) (?:one|a|an)\b[^.?!]{0,40}\balone\b", re.I),
    "teaser": re.compile(r"(?:and that's when|but that was only|little did|what (?:nobody|no one) knew|this was just the (?:start|beginning)|"
                         r"would change (?:everything|forever))[^.?!]*[.?!]?\s*$", re.I),
    "triplet": re.compile(r"\b\w+(?: \w+){0,2}, \w+(?: \w+){0,2},? and (?:a|an|the)?\s*\w+", re.I),
}
PERSON = re.compile(r"\b(?:I|I'm|I've|I'd|my|me|for me|in my opinion)\b|\bI (?:think|thought|loved|hated|remember|played|watched|tried)\b")
NUM = re.compile(r"\b\d[\d,.]*\b|\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|"
                 r"seventy|eighty|ninety|hundred|thousand|million|billion)\b", re.I)


def sentences(t):
    return [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s.strip()]


def content(s):
    return {w for w in re.findall(r"[a-z]{4,}", s.lower())} - {"that", "this", "with", "they", "them", "were", "have", "from", "just", "about", "there"}


def lint_para(p):
    ss = sentences(p)
    flags = {}
    for k in ("gloss", "gloss_means", "date_open", "colon", "turn", "triplet"):
        n = len(RX[k].findall(p))
        if n:
            flags[k.replace("gloss_means", "gloss")] = flags.get(k.replace("gloss_means", "gloss"), 0) + n
    stats = sum(1 for s in ss if len(NUM.findall(s)) >= 3)
    if stats:
        flags["stats"] = stats
    frag = sum(1 for s in ss if 1 < len(s.split()) <= 6 and not re.search(r"\b(?:is|was|are|were|had|has|did|got|went|said|says|came|made|took)\b", s, re.I))
    if frag:
        flags["fragment"] = frag
    if len(ss) >= 4 and len(content(ss[0]) & content(ss[-1])) >= 3:
        flags["bookend"] = 1
    if ss and RX["teaser"].search(ss[-1]):
        flags["teaser"] = 1
    if not PERSON.search(p):
        flags["no_person"] = 1
    return flags


def load_paras(path, para):
    p = Path(path)
    if p.suffix == ".md" and not para:
        import script_lint as L
        lines, _ = L.load_lines(str(p))
        return [f"[{b}] {t}" for b, t, _ in lines]
    return [x for x in p.read_text(encoding="utf-8").split("\n") if len(x.split()) > 20]


def validate():
    """Every passage of ours the judge panel scored (tools/script/judge_panel.py's sets): its flag count against the judges' P(AI)."""
    import judge_panel as J
    xs, ys = [], []
    by_flag = {}
    for d in sorted(J.ROOT.glob("*/pool.json")):
        name = d.parent.name
        pool = {it["iid"]: it for it in json.loads(d.read_text(encoding="utf-8"))}
        sc, _ = J.load_verdicts(name)
        per = {}
        for (iid, j), v in sc.items():
            if j.startswith("opus") or j == "sonnet":
                per.setdefault(iid, []).extend(v)
        for iid, v in per.items():
            it = pool[iid]
            if it["kind"].startswith("human") or it["kind"] in ("faceless",):
                continue
            f = lint_para(it["text"])
            xs.append(sum(f.values()))
            ys.append(st.mean(v))
            for k in f:
                by_flag.setdefault(k, []).append(st.mean(v))
            for k in ("_none",) if not f else ():
                by_flag.setdefault(k, []).append(st.mean(v))
    if len(xs) < 3:
        print(f"{len(xs)} judged passages of ours: score a judge panel set first (tools/script/judge_panel.py)")
        return
    print(f"{len(xs)} judged passages of ours (Claude judges): r(flag count, P(AI)) = {st.correlation(xs, ys):.2f}")
    base = st.mean(ys)
    for k, v in sorted(by_flag.items(), key=lambda kv: -st.mean(kv[1])):
        print(f"  {k:<10} on {len(v):>3} passages, their mean P(AI) {st.mean(v):.2f} (all: {base:.2f})")


STYLE = [   # the wording features that went with the pair test's judges catching an AI passage (same-content pairs)
    ("content_share", "content words share (lower = more glue words)", +1), ("mattr", "word variety (lower = words reused)", +1),
    ("word_len", "average word length", +1), ("just", '"just" per 1,000 words', -1), ("you", '"you" per 1,000 words', -1),
    ("wps", "words a sentence", -1), ("wps_sd", "sentence-length spread", -1), ("llm_all", "written constructions per 1,000", +1)]


def style(paras, groups=("voice", "talk"), per_para=False):
    """Each chunk of about 160 words against real creators' 160-word windows: the features that predict being caught, flagged when
    on the caught side of the human middle half."""
    import random
    import human_corpus as H
    import blind_test as B
    import voice_metrics as V
    rng = random.Random(1)
    wins = []
    for h, body in H.load():
        if h.get("group") in groups and h.get("punctuated", True):
            ss = B.sentences(B.normalise(B.declutter(body)))
            for _ in range(4):
                if len(ss) < 30:
                    break
                a, cur = rng.randrange(len(ss) - 25), []
                for s in ss[a:]:
                    cur.append(s)
                    if sum(len(x.split()) for x in cur) >= 160:
                        break
                wins.append(V.features(" ".join(cur)))
    if not wins:
        print(f"no human corpus texts in the groups {', '.join(groups)}: build the corpus first (tools/script/human_corpus.py)")
        return
    rng_ = {k: sorted(w.get(k, 0) for w in wins) for k, _, _ in STYLE}
    q = lambda k, p: rng_[k][int(p * (len(rng_[k]) - 1))]
    text = " ".join(re.sub(r"^\[\w+\]\s*", "", p) for p in paras)
    words = text.split()
    chunks = [" ".join(words[i:i + 160]) for i in range(0, len(words), 160) if len(words[i:i + 160]) > 80]
    if per_para:   # every paragraph on its own: the gaps an editor fixes, number by number
        for n, para in enumerate(paras, 1):
            f = V.features(re.sub(r"^\[\w+\]\s*", "", para))
            gaps = []
            for k, label, sign in STYLE:
                lo, hi, v = q(k, 0.25), q(k, 0.75), f.get(k, 0)
                if (sign > 0 and v > hi) or (sign < 0 and v < lo):
                    gaps.append(f"{k} {v:.2f} (humans {lo:.2f}-{hi:.2f})")
            print(f"paragraph {n}: " + ("; ".join(gaps) if gaps else "inside the human range on all eight"))
        return
    print(f"style against {len(wins)} windows of real creators ({', '.join(groups)}): human 25th-75th percentile; a flag = on the caught side")
    for k, label, sign in STYLE:
        vals = [V.features(c).get(k, 0) for c in chunks]
        lo, hi = q(k, 0.25), q(k, 0.75)
        bad = sum((v > hi) if sign > 0 else (v < lo) for v in vals)
        print(f"  {label:<44} ours median {st.median(vals):7.2f}   humans {lo:7.2f} - {hi:7.2f}   flagged {bad}/{len(vals)} chunks")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--para", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--style", action="store_true", help="the pair test's predictors, chunk by chunk, against real creators")
    ap.add_argument("--per-para", action="store_true", help="with --style: every paragraph's gaps, number by number")
    a = ap.parse_args()
    if a.validate:
        validate()
        return
    if not a.path:
        ap.error("a script.md or text file (or --validate)")
    if a.style:
        style(load_paras(a.path, a.para), per_para=a.per_para)
        return
    tot = 0
    for p in load_paras(a.path, a.para):
        f = lint_para(p)
        tot += sum(f.values())
        if f:
            print(f"{p[:70]:<70} {', '.join(f'{k} x{n}' if n > 1 else k for k, n in f.items())}")
    print(f"\n{tot} flags")


if __name__ == "__main__":
    main()
