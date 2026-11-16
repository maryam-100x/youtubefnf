"""chapters.py: the upload pack's chapters from the film's final word times, never by hand (read by hand from the beats, they
go stale after every timing change).

  videos/<video>/chapters.json   [{"title": "What you need to know"}, {"title": "The price", "beat": "S004"}, ...]
                                 (the first chapter is 0:00 and needs no beat; every other one names the beat it opens on)
  PIPE tools/pipeline/chapters.py <video> [--write]

Each chapter's time is its beat's first word minus 0.5 s, floored to the second, on the film's own timing (the narration with the bites
laid in, build/insert/words_ins.json, when there is one). Refused, as YouTube refuses them: fewer than 3 chapters, the first not at 0:00,
one under 10 s, or out of order. --write puts the lines into post.md between `<!-- chapters -->` and `<!-- /chapters -->`, indented as
the line after the opening marker is. pipe.py finish runs it with --write when chapters.json exists, so the pack follows the timing."""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Video, find_video  # noqa: E402

LEAD = 0.5   # s before the chapter's first word
MIN_LEN = 10.0   # YouTube's shortest chapter


def stamp(t):
    t = int(t)
    h, m, s = t // 3600, t % 3600 // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def film_words(v):
    ins = v.dj / "build" / "insert" / "words_ins.json"
    p = ins if ins.exists() else v.words()
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    return d if isinstance(d, list) else d.get("words", [])


def compute(spec, words, end=None):
    """[(seconds, title)], or SystemExit naming what YouTube would refuse"""
    first = {}
    for w in words:
        b = w.get("beat")
        if b and b not in first:
            first[b] = float(w["start"])
    out, bad = [], []
    for i, c in enumerate(spec):
        if i == 0 and not c.get("beat"):
            out.append((0.0, c["title"]))
            continue
        if c.get("beat") not in first:
            bad.append(f"'{c['title']}': beat {c.get('beat')} is not in the film's words")
            continue
        out.append((0.0 if i == 0 else max(0.0, math.floor(first[c["beat"]] - LEAD)), c["title"]))
    if len(out) >= 1 and out[0][0] != 0.0:
        bad.append(f"the first chapter starts at {stamp(out[0][0])}, not 0:00")
    if len(out) < 3:
        bad.append(f"{len(out)} chapters: YouTube needs at least 3")
    for (a, ta), (b, tb) in zip(out, out[1:] + ([(end, None)] if end else [])):
        if b is not None and b - a < MIN_LEN:
            bad.append(f"'{ta}' is {b - a:.0f} s long (YouTube needs {MIN_LEN:.0f} s)" if b > a else f"'{ta}' and '{tb}' are out of order")
    if bad:
        raise SystemExit("chapters refused:\n  " + "\n  ".join(bad))
    return out


def write_post(post, chapters):
    s = post.read_text(encoding="utf-8")
    m = re.search(r"(<!-- chapters -->\n)(.*?)(\n?[ \t]*<!-- /chapters -->)", s, re.S)
    if not m:
        return False
    ind = re.match(r"[ \t]*", m.group(2)).group(0) if m.group(2) else ""
    body = "\n".join(f"{ind}{stamp(t)} {title}" for t, title in chapters)
    post.write_text(s[:m.start(2)] + body + s[m.end(2):], encoding="utf-8")
    return True


def run(v, write=False, say=print):
    spec_p = v.folder / "chapters.json"
    if not spec_p.exists():
        return None
    words = film_words(v)
    end = max((float(w["end"]) for w in words), default=None)
    ch = compute(json.loads(spec_p.read_text(encoding="utf-8")), words, end)
    for t, title in ch:
        say(f"  {stamp(t)} {title}")
    if write:
        post = v.folder / "post.md"
        if post.exists() and write_post(post, ch):
            say("chapters: written into post.md")
        else:
            say("chapters: post.md has no <!-- chapters --> ... <!-- /chapters --> block: put the lines above in by hand")
    return ch


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    v = Video(find_video(args[0]))
    if run(v, "--write" in sys.argv) is None:
        raise SystemExit(f"no {v.folder / 'chapters.json'}")
