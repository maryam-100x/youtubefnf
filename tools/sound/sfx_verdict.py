"""sfx_verdict.py: the creator's verdict on a new sound, written where score.py reads it. New sounds are welcome, never forced, and only
the creator judges whether one is good.

A new sound reaches the creator first as a sample (Sfx(..., test=True), mixed with score.py --test-sounds) or a Sound Test round; only
when a moment needs a sound the rated set lacks, never to fill. A yes makes it rated (palette.json _creator_picks, so score.py lets it
into a film); a no bans it (palette.json _banned, refused by name from any path).

  PIPE tools/sound/sfx_verdict.py yes <file> --words "<the creator's words>" [--for "<what it is for>"]
  PIPE tools/sound/sfx_verdict.py no  <file> --words "<the creator's words>"
"""
import argparse
import json
import time
from pathlib import Path

PAL = Path(__file__).resolve().parent / "palette.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("verdict", choices=["yes", "no"])
    ap.add_argument("file")
    ap.add_argument("--words", required=True, help="the creator's words, verbatim")
    ap.add_argument("--for", dest="use", default="")
    a = ap.parse_args()
    f = Path(a.file)
    if not f.exists():
        raise SystemExit(f"no such file: {f}")
    if not PAL.exists():
        raise SystemExit(f"no {PAL} yet: the setup builds it from the house effects set")
    p = json.loads(PAL.read_text(encoding="utf-8"))
    path = str(f).replace("\\", "/")
    date = time.strftime("%Y-%m-%d")
    if a.verdict == "yes":
        if f.name in (p.get("_banned") or {}):
            raise SystemExit(f"{f.name} is banned: the creator's no stands; a new yes needs the creator to lift the ban first")
        picks = p.setdefault("_creator_picks", [])
        if any(e.get("file", "").lower() == path.lower() for e in picks):
            print(f"already the creator's pick: {path}")
            return
        picks.append({"file": path, "why": f'{date}: "{a.words}"' + (f" (for {a.use})" if a.use else "")})
    else:
        p.setdefault("_banned", {})[f.name] = {"was": path, "why": a.words, "date": date}
        p["_creator_picks"] = [e for e in p.get("_creator_picks") or [] if e.get("file", "").lower() != path.lower()]
    PAL.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{a.verdict}: {path}")


if __name__ == "__main__":
    main()
