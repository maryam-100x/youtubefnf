"""The blind test: can a judge tell our narration from real YouTubers'?

  PIPE tools/script/blind_test.py make <name> --ours <file[@label][#n]> ... --human <id[@label][#n]> ... [--per 2] [--words 190] [--seed 1]
  PIPE tools/script/blind_test.py score <name> <verdicts.json> [<verdicts.json> ...]

make: cuts passages of about --words words (whole sentences, from the middle 85% of each text, never the intro or the sign-off) from
our texts (a script.md's VOICE lines, or a plain text file) and from the human corpus (tools/script/human_corpus.py's ids), puts them
through one normalisation (numbers over ten as digits, "percent" as %, straight quotes: scripts spell numbers out for the voice,
captions don't), shuffles them, and writes MEDIA/script/blind/<name>/packet.md (what the judge reads: passages P1..Pn, no labels) and
MEDIA/script/blind_keys/<name>.json (what each one is; kept apart, the judge never sees it). The judge's brief is in packet.md's head: a
judge is a fresh agent with no tools, or a person. --split: one passage of ours per packet, with every human one.
score: reads one or more judges' answers (a JSON list of {"id": "P3", "verdict": "AI"|"HUMAN", "confidence": 50-100, "tells": "..."}) and
prints, per source kind, how often the judges called it AI and how sure they were, and for every passage of ours the tells they named.
Passing means our passages are called AI no more often than the human ones. Creators' words stay in the media root, never in git."""
import argparse
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
from paths import MEDIA  # noqa: E402

LAB = MEDIA / "script"
OUT = LAB / "blind"          # creators' words stay in the media root
KEYS = LAB / "blind_keys"    # apart from the packets, so a judge with file access can't stumble on them

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
                                     "sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000, "billion": 1_000_000_000}
NUMWORD = r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|" \
          r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)"
RUN = re.compile(rf"\b(?:a |an )?{NUMWORD}(?:(?:[- ]| and ){NUMWORD})*\b", re.I)


def topics():
    """The judges' line on what the videos are about: the niche from tools/script/niche.json when it is set."""
    from script_lint import NICHE
    niche = str(NICHE.get("niche") or "").strip()
    return "different topics" + (f", mostly {niche}" if niche else "")


def words_to_number(s):
    toks = re.split(r"[- ]+", s.lower().replace(" and ", " "))
    total, cur = 0, 0
    for i, t in enumerate(toks):
        if t in ("a", "an"):
            # "a hundred" is 100, but "a four hundred dollar" is 400: "a" counts only before a scale word
            if i + 1 < len(toks) and (toks[i + 1] in UNITS or toks[i + 1] in TENS):
                continue
            cur = 1
        elif t in UNITS:
            cur += UNITS[t]
        elif t in TENS:
            cur += TENS[t]
        elif t == "hundred":
            cur = max(cur, 1) * 100
        elif t in SCALES:
            total += max(cur, 1) * SCALES[t]
            cur = 0
        else:
            return None
    return total + cur


def fmt(n):
    return f"{n:,}" if n >= 1000 else str(n)


def normalise(text):
    """One style for every passage. Number words become digits from 11 up (and any with a scale word), as YouTube's captions write them;
    one to ten stay words; dollars and percent as signs."""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", ", ")

    def rep(m):
        s = m.group(0)
        n = words_to_number(s)
        if n is None:
            return s
        if s.strip().lower() in SCALES and re.search(r"\d\s*$", text[:m.start()]):
            return s   # "1.5 billion" stays as captions write it
        follows = text[m.end():m.end() + 9].lower()
        if n <= 10 and not re.search(r"hundred|thousand|million|billion", s, re.I) and not follows.startswith((" percent", " dollars")):
            return s
        lead = " " if s[:1] == " " else ""
        return lead + fmt(n)
    text = re.sub(r"(?i)\b(one|two|three|four|five|six|seven|eight|nine) and a half (million|billion)\b",
                  lambda m: f"{UNITS[m.group(1).lower()]}.5 {m.group(2).lower()}", text)
    text = re.sub(r"(?i)\b(one|two|three|four|five|six|seven|eight|nine) point (one|two|three|four|five|six|seven|eight|nine) (thousand|million|billion)\b",
                  lambda m: f"{UNITS[m.group(1).lower()]}.{UNITS[m.group(2).lower()]} {m.group(3).lower()}", text)   # "one point three million" -> "1.3 million"
    text = RUN.sub(rep, text)
    text = re.sub(r"\b(\d[\d,.]*) (?:dollars|bucks)\b", r"$\1", text)
    text = re.sub(r"\b(\d[\d,.]*) percent\b", r"\1%", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def declutter(text):
    """Speech-to-text noise off a human transcript, so a judge can't use it: fillers (uh, um), stutters (it's it's), masked swears,
    spaces before punctuation. The wording itself stays."""
    text = re.sub(r"\[\s*_+\s*\]", "", text)
    text = re.sub(r"(?i)(?:,\s*)?\b(?:uh+|um+|uhm|erm|mhm)\b,?\s*", " ", text)
    for _ in range(2):
        text = re.sub(r"(?i)\b(\w+(?:'\w+)?)(?:,?\s+\1\b)+", r"\1", text)
    text = re.sub(r"\s+([.,?!;:])", r"\1", text)
    text = re.sub(r"([.?!])\s*([a-z])", lambda m: m.group(1) + " " + m.group(2).upper(), text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[\"']?[A-Z0-9$])", text) if s.strip()]


AD = re.compile(r"sponsor|promo code|\.com/|patreon|use code|link in the description|subscribe|today's video is brought", re.I)


def passages(text, n, target, rng):
    ss = sentences(text)
    lo, hi = int(len(ss) * 0.08), int(len(ss) * 0.93)
    ss = ss[lo:hi]
    spans, i = [], 0
    while i < len(ss):
        j, w = i, 0
        while j < len(ss) and w < target:
            w += len(ss[j].split())
            j += 1
        if target * 0.8 <= w <= target * 1.35 and not AD.search(" ".join(ss[i:j])):
            spans.append((i, j))
        i = j
    rng.shuffle(spans)
    return [" ".join(ss[a:b]) for a, b in sorted(spans[:n])]


def load_ours(path):
    p = Path(path)
    if p.suffix == ".md":
        import script_lint as L
        lines, _ = L.load_lines(str(p))
        return " ".join(t for _, t, _ in lines)
    return p.read_text(encoding="utf-8")


BRIEF = """# Blind test {name}

You are judging transcripts of YouTube narration. They come from videos on {topics}. Some were written by an AI (a large language
model) for a channel; the others are transcripts of real human YouTubers talking or reading their own script. The share is unknown: it
can be anything from none to all. Every passage went through the same clean-up (numbers as digits, punctuation). Some human ones come
from speech-to-text and may contain a misheard word: do not use transcription slips as evidence either way.

For each passage decide AI or HUMAN from the wording alone. Do not use any tools or search; read and judge. Answer with a JSON list only:
[{{"id": "P1", "verdict": "AI", "confidence": 75, "tells": "the 1-3 phrases or habits that decided it"}}, ...]
Confidence is 50 (a coin flip) to 100 (certain).

"""


def make(name, ours, humans, per, target, seed, split=False):
    rng = random.Random(seed)
    import human_corpus as H
    corpus = {h["id"]: (h, body) for h, body in H.load()}
    items = []
    for spec in ours:
        spec, _, cnt = spec.partition("#")
        path, _, label = spec.rpartition("@") if "@" in spec else (spec, "", "")
        text = normalise(load_ours(path))
        if cnt == "para":   # every paragraph of a plain text file is one passage, as written
            chunks = [normalise(p) for p in load_ours(path).split("\n") if len(p.split()) > 40]
        else:
            chunks = passages(text, int(cnt or per), target, rng)
        for k, ptxt in enumerate(chunks):
            items.append({"kind": label or "ours", "source": Path(path).parent.name if path.endswith(".md") else Path(path).stem, "text": ptxt})
    for spec in humans:
        spec, _, cnt = spec.partition("#")
        vid, _, label = spec.rpartition("@") if "@" in spec else (spec, "", "")
        vid = vid[3:] if vid.startswith("yt:") else vid   # an id starting with "-" is passed as yt:-abc
        if vid not in corpus:
            print(f"no corpus text for {vid}")
            continue
        h, body = corpus[vid]
        whole = [normalise(declutter(body))] if cnt == "all" else None   # a Short: the whole script is one passage
        for ptxt in whole or passages(normalise(declutter(body)), int(cnt or per), target, rng):
            items.append({"kind": label or "human", "source": f"{h['channel']} ({vid})", "text": ptxt})
    rng.shuffle(items)
    if split:   # one passage of ours per packet, with every human one: no "same author four times" for the judge to latch onto
        ours_items = [it for it in items if it["kind"] != "human"]
        hum_items = [it for it in items if it["kind"] == "human"]
        for k, it in enumerate(ours_items, 1):
            pack = hum_items + [it]
            rng.shuffle(pack)
            write_packet(f"{name}_{k}", pack)
        return
    write_packet(name, items)


def write_packet(name, items):
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    lines = [BRIEF.format(name=name, topics=topics())]
    key = {}
    for k, it in enumerate(items, 1):
        pid = f"P{k}"
        lines.append(f"## {pid}\n{it['text']}\n")
        key[pid] = {"kind": it["kind"], "source": it["source"], "words": len(it["text"].split())}
    (d / "packet.md").write_text("\n".join(lines), encoding="utf-8")
    KEYS.mkdir(parents=True, exist_ok=True)
    (KEYS / f"{name}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    kinds = {}
    for v in key.values():
        kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
    print(f"{len(items)} passages -> {d / 'packet.md'}  ({kinds})")


def parse_verdicts(p):
    raw = Path(p).read_text(encoding="utf-8")
    m = re.search(r"\[.*\]", raw, re.S)
    return json.loads(m.group(0)) if m else []


def key_for(name, verdict_file):
    """The key of the packet a verdict file answers: <name>.json, or for split packets the <name>_<k>.json named in the file's name."""
    if (KEYS / f"{name}.json").exists():
        return json.loads((KEYS / f"{name}.json").read_text(encoding="utf-8"))
    m = re.search(re.escape(name) + r"_(\d+)", Path(verdict_file).name)
    return json.loads((KEYS / f"{name}_{m.group(1)}.json").read_text(encoding="utf-8")) if m else {}


def score(name, files):
    by_kind, notes = {}, []
    for f in files:
        key = key_for(name, f)
        for v in parse_verdicts(f):
            k = key.get(v.get("id"))
            if not k:
                continue
            ai = str(v.get("verdict", "")).upper().startswith("AI")
            conf = float(v.get("confidence", 50))
            p_ai = conf / 100 if ai else 1 - conf / 100   # the judge's probability that it's AI
            by_kind.setdefault(k["kind"], []).append((ai, p_ai))
            notes.append((k["kind"], v["id"], k["source"], "AI" if ai else "HUMAN", conf, v.get("tells", "")))
    print(f"{'kind':<14} {'judged':>6} {'called AI':>10} {'mean P(AI)':>11}")
    for kind, vs in sorted(by_kind.items()):
        n = len(vs)
        print(f"{kind:<14} {n:>6} {sum(a for a, _ in vs) / n:>9.0%} {st.mean(p for _, p in vs):>11.2f}")
    print()
    for kind, pid, src, verdict, conf, tells in sorted(notes):
        if kind != "human":
            print(f"{kind:<10} {pid:<4} {verdict:<5} {conf:>3.0f}  {src[:28]:<28} {tells[:160]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("name")
    m.add_argument("--ours", nargs="*", default=[])
    m.add_argument("--human", nargs="*", default=[])
    m.add_argument("--per", type=int, default=2)
    m.add_argument("--words", type=int, default=190)
    m.add_argument("--seed", type=int, default=1)
    m.add_argument("--split", action="store_true", help="one passage of ours per packet (<name>_1, _2, ...)")
    s = sub.add_parser("score")
    s.add_argument("name")
    s.add_argument("files", nargs="+")
    a = ap.parse_args()
    if a.cmd == "make":
        make(a.name, a.ours, a.human, a.per, a.words, a.seed, a.split)
    else:
        score(a.name, a.files)


if __name__ == "__main__":
    main()
