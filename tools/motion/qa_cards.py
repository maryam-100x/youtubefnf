"""qa_cards.py: text cards, counted. People watch to get instant visual feedback on what is being told, not to read: every line gets a
clip that shows it, or a built demonstration from real material (a split screen, a 3D graphic, a demonstration); a card (a page, a post,
a headline, a quote, a number on a card, a text block) only where the words are about that text itself and nothing visual shows it
better. Text is the last resort.

What it flags:
  CARD_REASON  a shot in the code whose picture is a card component (kit3's Page, Read, NumberBeside, BigNumber, TextBlock, Headline,
               Card, and the other card components: Rec, Receipt, PageShot, PageStage, QuoteCard, PostCard, NumberShot, ...) with no
               written reason in the comment above it: a line "card: <why the text itself is the point and no picture shows it better>"
  CARD_TIME    cards on more than 8% of the film's screen time (the shots the gate's probe saw: <video media dir>/pipeline/shots_<comp>.json)
  CARD_CLOSE   two card shots starting less than 20 s apart (the second one is flagged; a card with its written reason still counts here)
Read by the gate (gate.py B19 CARDS, every `pipe.py <video> gate`) and runnable alone:

  PIPE tools/motion/qa_cards.py <video> [--share 0.08] [--gap 20]
Exit 1 when anything is flagged."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
from codefiles import code_files  # noqa: E402   with the subfolder files the film imports
from paths import TOOLS  # noqa: E402
CARDS = {"Page", "PageStage", "Rec", "Receipt", "PageShot", "PageStack", "PageCrop", "PageRead", "Read", "QuoteCard", "QuoteShot",
         "QuoteLines", "QuoteLine", "QuoteTwo", "PostCard", "CodeQuote", "HeadShot", "NumberBeside", "BigNumber", "NumberShot",
         "NumberFrame", "LiveNumber", "CountOver", "TextBlock", "Headline", "Card", "TurnCard", "Lockup"}
ENTRY = re.compile(r"^\s*(?:shot|ft2?|page|parts)\(|\{at:\s*.+?,\s*el:")
SHARE, GAP = 0.08, 20.0


def code_cards(src_dir):
    """[(file, line, anchor text, components, reason)] for every shot entry of the composition's code that draws a card component"""
    out = []
    for f in code_files(src_dir):   # with the subfolder files the film imports
        lines = f.read_text(encoding="utf-8").splitlines()
        idx = [i for i, ln in enumerate(lines) if ENTRY.search(ln) and not ln.lstrip().startswith(("const ", "export const ", "function "))]
        for n, i in enumerate(idx):
            j = idx[n + 1] if n + 1 < len(idx) else min(len(lines), i + 40)
            body = "\n".join(lines[i:j])
            comps = [c for c in re.findall(r"<(\w+)", body) if c in CARDS]
            if not comps:
                continue
            k, com = i - 1, []
            while k >= 0 and lines[k].strip().startswith("//"):
                com.insert(0, lines[k].strip().lstrip("/ ").strip())
                k -= 1
            why = next((c.split(":", 1)[1].strip() for c in com if c.lower().startswith("card:")), "")
            out.append((f.relative_to(Path(src_dir).resolve()).as_posix(), i + 1, lines[i].strip()[:90], sorted(set(comps)), why))
    return out


def film_cards(shots_json):
    """[(at, end, components)] of the shots the probe saw drawing a card, and the film's length"""
    d = json.loads(Path(shots_json).read_text(encoding="utf-8"))
    cards = [(s["at"], s["end"], sorted(set(s.get("names", [])) & CARDS)) for s in d["shots"] if set(s.get("names", [])) & CARDS]
    return cards, float(d.get("seconds") or (d["shots"][-1]["end"] if d["shots"] else 0))


def check(src_dir, shots_json, share=SHARE, gap=GAP):
    """the flags as dicts: {check, key, t, what}"""
    flags = []
    for f, ln, anchor, comps, why in code_cards(src_dir):
        if not why:
            flags.append({"check": "CARD_REASON", "key": f"{f}:{ln}", "t": None,
                          "what": f"{f}:{ln} {anchor}: a card ({', '.join(comps)}) with no written reason ('// card: ...' above it): show it "
                                  "as a clip or a built demonstration, or write why the text itself is the point"})
    if shots_json and Path(shots_json).exists():
        cards, total = film_cards(shots_json)
        dur = sum(e - a for a, e, _ in cards)
        if total and dur / total > share:
            flags.append({"check": "CARD_TIME", "key": "film", "t": cards[0][0],
                          "what": f"cards hold {dur:.1f} s of {total:.1f} s ({dur / total:.0%}, over {share:.0%}): {len(cards)} card shots"})
        for (a0, _, c0), (a1, _, c1) in zip(cards, cards[1:]):
            if a1 - a0 < gap:
                flags.append({"check": "CARD_CLOSE", "key": f"{a1:.2f}", "t": a1,
                              "what": f"two cards {a1 - a0:.1f} s apart ({'/'.join(c0)} at {a0:.2f} s, {'/'.join(c1)} at {a1:.2f} s; under {gap:.0f} s)"})
    return flags


def gate_flags(v):
    """for gate.py (B19 CARDS): the flags as the gate's own dicts (at = frame)"""
    fps = getattr(v, "fps", None) or 60
    sj = v.pipe_dir / f"shots_{v.comp}.json"
    src = HERE / "src" / v.src
    out = []
    for fl in check(src, sj):
        at = int(round((fl["t"] or 0) * fps))
        out.append({"check": fl["check"], "key": fl["key"], "at": at, "to": at, "what": fl["what"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--share", type=float, default=SHARE)
    ap.add_argument("--gap", type=float, default=GAP)
    ap.add_argument("--src", help="the composition's src folder (default: video.toml's)")
    ap.add_argument("--shots", help="the probe's shots json (default: <video media dir>/pipeline/shots_<comp>.json)")
    a = ap.parse_args()
    sys.path.insert(0, str(TOOLS / "pipeline"))
    from common import Video, find_video   # noqa: E402
    v = Video(find_video(a.video))
    src = Path(a.src) if a.src else HERE / "src" / v.src
    sj = Path(a.shots) if a.shots else v.pipe_dir / f"shots_{v.comp}.json"
    cc = code_cards(src)
    flags = check(src, sj, a.share, a.gap)
    if sj.exists():
        cards, total = film_cards(sj)
        dur = sum(e - x for x, e, _ in cards)
        print(f"{v.slug}: {len(cards)} card shots on the film, {dur:.1f} s of {total:.1f} s ({dur / total:.1%}); {len(cc)} card entries in the "
              f"code, {sum(1 for c in cc if c[4])} with a written reason")
    else:
        print(f"{v.slug}: no probe shots file ({sj}); the code only: {len(cc)} card entries")
    for fl in flags:
        print(f"  {fl['check']:12s} {fl['what']}")
    print(f"{len(flags)} flag(s)")
    return 1 if flags else 0


if __name__ == "__main__":
    sys.exit(main())
