"""The lingo corpus and its numbers: how real YouTubers, the creator and the creator's scripts phrase things.

  PIPE tools/script/lingo_corpus.py [--ours 12,13,...]

Inputs (all in the media root, never in git; the chat gathers them with the creator):
  MEDIA/script/lingo/*.vtt + *.info.json   YouTube captions of the niche's real creators (yt-dlp --write-subs --write-auto-subs
                                            --write-info-json --skip-download; rolling auto-captions are de-duplicated)
  MEDIA/script/lingo/transcripts/*.txt     plain transcripts of reference videos (e.g. a speech-to-text run), one per video, named
                                            by the creator; a leading time stamp on each line is dropped
  MEDIA/script/lingo/creator/*.md|*.txt    the creator's own words (messages, interview answers: how they talk), blocks of 40+ words
  videos/*/script.md                       the scripts' VOICE lines (every video, or --ours <ids>)
Writes MEDIA/script/lingo/corpus/<name>.txt (the creator's words as CREATOR_dictated_.txt, which lingo_measure.py reads) and prints a
comparison table: words per sentence, contractions per 100 words, I/you/we per 1,000, questions per 1,000, the most frequent sentence
openers, and "announcer" phrases (a line that announces the next line) per 1,000 words. Auto-captions have no punctuation, so
sentence numbers come only from sources that have it (the scripts, the creator's words, manual captions); the others report words
only."""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MEDIA, VIDEOS_REPO  # noqa: E402

L = MEDIA / "script" / "lingo"
OUT = L / "corpus"
CREATOR_NAME = "CREATOR (dictated)"   # its corpus file: CREATOR_dictated_.txt


def vtt_text(p):
    lines, last = [], ""
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if "-->" in ln or not ln.strip() or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        t = re.sub(r"<[^>]+>", "", ln).strip()
        if t and t != last:
            lines.append(t)
            last = t
    # rolling captions repeat the previous line as the first line of the next cue
    out = []
    for t in lines:
        if out and (t == out[-1] or out[-1].endswith(t)):
            continue
        out.append(t)
    return " ".join(out)


def sources(ours_ids=None):
    s = {}
    for info in L.glob("*.info.json") if L.exists() else []:
        vid = info.name.split(".")[0]
        d = json.loads(info.read_text(encoding="utf-8"))
        subs = sorted(L.glob(f"{vid}*.vtt"), key=lambda p: (".en.vtt" not in p.name, len(p.name)))
        if subs:
            s[f"{d.get('channel', vid)}"] = vtt_text(subs[0])
    for tr in sorted((L / "transcripts").glob("*.txt")) if (L / "transcripts").exists() else []:
        s[tr.stem] = re.sub(r"^\S+\s+", "", tr.read_text(encoding="utf-8"), flags=re.M).replace("\n", " ")
    said = []
    for f in sorted(list((L / "creator").glob("*.md")) + list((L / "creator").glob("*.txt"))) if (L / "creator").exists() else []:
        for block in re.split(r"^#.*$", f.read_text(encoding="utf-8"), flags=re.M):   # one block per heading; headings are no talk
            body = block.strip()
            if len(body.split()) > 40 and "http" not in body[:80]:
                said.append(body)
    if said:
        s[CREATOR_NAME] = " ".join(said)
    for p in sorted(VIDEOS_REPO.glob("*/script.md")) if VIDEOS_REPO.exists() else []:
        if ours_ids and not any(p.parent.name.startswith(i) for i in ours_ids):
            continue
        voice = re.findall(r"\] VOICE: (.*)", p.read_text(encoding="utf-8"))
        if voice:
            s[f"OURS {p.parent.name}"] = " ".join(voice)
    return s


ANNOUNCE = [r"here'?s the (crazy|wild|weird|funny|best|interesting) (part|thing)", r"this is where it gets", r"and that'?s (not|where)",
            r"(gets|got) (wild|crazy|interesting)", r"think about (that|what that means)", r"let that sink in", r"but here'?s the (thing|kicker|catch)",
            r"buckle up", r"and honestly", r"the (craziest|wildest|best) part", r"you won'?t believe", r"it'?s not just", r"not just .{1,30}, (it'?s|but)"]
CONTR = r"\b\w+'(s|re|ve|ll|d|t|m)\b"


def stats(name, t):
    w = re.findall(r"[A-Za-z']+", t)
    n = max(1, len(w))
    low = [x.lower() for x in w]
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", t) if len(x.split()) > 2]
    has_punct = len(sents) > n / 60
    openers = Counter(" ".join(x.lower().split()[:2]) for x in sents) if has_punct else Counter()
    ann = sum(len(re.findall(p, t, re.I)) for p in ANNOUNCE)
    return {
        "name": name, "words": n,
        "words/sentence": round(n / len(sents), 1) if has_punct else None,
        "contractions/100w": round(100 * len(re.findall(CONTR, t)) / n, 1),
        "I/1k": round(1000 * low.count("i") / n, 1), "you/1k": round(1000 * low.count("you") / n, 1),
        "we/1k": round(1000 * low.count("we") / n, 1),
        "questions/1k": round(1000 * t.count("?") / n, 1) if has_punct else None,
        "announcers/1k": round(1000 * ann / n, 2),
        "openers": ", ".join(f"{k} ({v})" for k, v in openers.most_common(8)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ours", default="", help="video ids whose scripts go in (default: every video)")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, t in sources([x for x in a.ours.split(",") if x] or None).items():
        (OUT / (re.sub(r"[^\w]+", "_", name) + ".txt")).write_text(t, encoding="utf-8")
        rows.append(stats(name, t))
    if not rows:
        print(f"no sources yet: put captions, transcripts or the creator's words in {L} (see the docstring)")
        return
    keys = ["name", "words", "words/sentence", "contractions/100w", "I/1k", "you/1k", "we/1k", "questions/1k", "announcers/1k"]
    print("| " + " | ".join(keys) + " |")
    print("|" + "---|" * len(keys))
    for r in rows:
        print("| " + " | ".join(str(r[k]) for k in keys) + " |")
    print()
    for r in rows:
        if r["openers"]:
            print(f"- {r['name']}: {r['openers']}")


if __name__ == "__main__":
    main()
