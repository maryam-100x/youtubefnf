"""The human corpus: real YouTubers' words, to measure the creator's scripts against. The repo ships none: every creator builds their
own from their niche's real creators (the channels their viewers also watch, talking and reading their own scripts), so the bars the
script tools measure against are the niche's own.

  PIPE tools/script/human_corpus.py fetch <id> [<id> ...] --group <group> [--pause 6]
  PIPE tools/script/human_corpus.py clean
  PIPE tools/script/human_corpus.py list

Building it (the chat does this with the creator once, then adds to it):
  1. pick 15-30 videos of real creators in the niche (YouTube video ids), across the groups below, a few per channel
  2. fetch them group by group:   PIPE tools/script/human_corpus.py fetch abc123 def456 --group voice
  3. clean, then list:            PIPE tools/script/human_corpus.py clean  &&  PIPE tools/script/human_corpus.py list
  4. build the judge panel's calibration set from them (tools/script/judge_panel.py "calibration")
The groups (labels the other script tools' defaults use):
  talk    off-the-cuff talking to the camera      voice   a scripted voice-over read by its writer
  tech    technical explainers                    doc     documentary narration
  ref     the channels the creator wants to sound like        script   any other read script

fetch: captions only (never the video) with yt-dlp (the pipeline venv's), a spare account's cookies (MEDIA/secrets/yt_cookies.txt,
passed to yt-dlp only), slow (a few seconds between videos), and it stops at the first sign-in or bot prompt. The creator's own English
captions when there are any, else YouTube's auto captions (newer ones are punctuated). Files go to MEDIA/script/human_corpus/raw/
(creators' words stay in the media root, never in git).
clean: every raw caption file to plain text, one file per video in MEDIA/script/human_corpus/text/<id>.txt, with a header line
(channel, title, upload date, views, likes, caption kind, group). Rolling auto captions are de-duplicated; [Music], >> and the like go.
list: what is there, with word counts."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MEDIA, PY_PIPE, SECRETS, WINDOWS  # noqa: E402

ROOT = MEDIA / "script" / "human_corpus"
RAW, TEXT = ROOT / "raw", ROOT / "text"
YT = PY_PIPE.parent / ("yt-dlp.exe" if WINDOWS else "yt-dlp")
COOKIES = SECRETS / "yt_cookies.txt"   # passed to yt-dlp only; never opened here
STOP_WORDS = ("Sign in to confirm", "not a bot", "HTTP Error 429", "confirm your age")


def fetch(ids, group, pause=6.0):
    RAW.mkdir(parents=True, exist_ok=True)
    groups = json.loads((ROOT / "groups.json").read_text(encoding="utf-8")) if (ROOT / "groups.json").exists() else {}
    for k, vid in enumerate(ids):
        vid = vid.strip()
        if not vid:
            continue
        if list(RAW.glob(f"{vid}*.vtt")):
            print(f"{vid}: already here")
            groups.setdefault(vid, group)
            continue
        cmd = [str(YT), "--cookies", str(COOKIES), "--js-runtimes", "node", "--skip-download", "--write-subs", "--write-auto-subs",
               "--sub-langs", "en,en-US,en-GB,en-orig", "--sub-format", "vtt", "--write-info-json", "--no-write-comments",
               "-o", str(RAW / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={vid}"]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = r.stdout + r.stderr
        if any(s in out for s in STOP_WORDS):
            print(f"{vid}: STOP, YouTube asked for a sign-in or a bot check:\n{out[-600:]}")
            sys.exit(2)
        got = list(RAW.glob(f"{vid}*.vtt"))
        print(f"{vid}: {len(got)} caption file(s)" + ("" if got else f"  {out[-300:]}"))
        groups[vid] = group
        (ROOT / "groups.json").write_text(json.dumps(groups, indent=1), encoding="utf-8")
        if k < len(ids) - 1:
            time.sleep(pause)


def vtt_lines(p):
    """Cue texts in order, without timing tags; rolling auto captions repeat the line before, so repeats go."""
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if "-->" in ln or not ln.strip() or ln.startswith(("WEBVTT", "Kind:", "Language:", "NOTE", "STYLE")):
            continue
        t = re.sub(r"<[^>]+>", "", ln).replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&").replace("&nbsp;", " ").strip()
        if not t:
            continue
        if out and (t == out[-1] or out[-1].endswith(t)):
            continue
        if out and t.startswith(out[-1]):
            out[-1] = t
            continue
        out.append(t)
    return out


def clean_text(lines):
    t = " ".join(lines)
    t = re.sub(r"\[(music|applause|laughter|__|sound|silence|inaudible|laughs|cheering|noise)[^\]]*\]", " ", t, flags=re.I)
    t = re.sub(r"\((music|applause|laughs?|laughter)\)", " ", t, flags=re.I)
    t = re.sub(r"\[[^\]]{0,60}\]", " ", t)   # caption notes: [paid plug voice], [angelic choir]
    t = t.replace(">>", " ").replace("♪", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def pick_track(vid):
    """The best-punctuated English track: the creator's own captions when they exist, else YouTube's auto captions (newer ones are
    punctuated; older auto tracks are one run of words, kept for word counts only)."""
    info = RAW / f"{vid}.info.json"
    manual = set()
    if info.exists():
        d = json.loads(info.read_text(encoding="utf-8"))
        manual = set((d.get("subtitles") or {}).keys())
    best, best_score = None, -1.0
    for p in sorted(RAW.glob(f"{vid}.*.vtt")):
        lang = p.name[len(vid) + 1:-4]
        body = clean_text(vtt_lines(p))
        n = max(1, len(body.split()))
        score = len(re.findall(r"[.?!]", body)) / n + (0.01 if lang in manual else 0)
        if score > best_score:
            best, best_score = (p, "manual" if lang in manual else "auto"), score
    return best if best else (None, None)


def clean():
    TEXT.mkdir(parents=True, exist_ok=True)
    groups = json.loads((ROOT / "groups.json").read_text(encoding="utf-8")) if (ROOT / "groups.json").exists() else {}
    n = 0
    for info in sorted(RAW.glob("*.info.json")):
        vid = info.name.split(".")[0]
        track, kind = pick_track(vid)
        if not track:
            continue
        d = json.loads(info.read_text(encoding="utf-8"))
        body = clean_text(vtt_lines(track))
        punct = len(re.findall(r"[.?!]", body)) / max(1, len(body.split()))
        head = {"id": vid, "channel": d.get("channel"), "title": d.get("title"), "upload_date": d.get("upload_date"),
                "views": d.get("view_count"), "likes": d.get("like_count"), "duration": d.get("duration"), "captions": kind,
                "punctuated": punct > 0.03, "group": groups.get(vid, "")}
        (TEXT / f"{vid}.txt").write_text(json.dumps(head, ensure_ascii=False) + "\n" + body + "\n", encoding="utf-8")
        n += 1
    print(f"{n} texts in {TEXT}")


def load(group=None):
    """[(header dict, body)] of every cleaned text (optionally one group); empty until the corpus is built."""
    out = []
    for p in sorted(TEXT.glob("*.txt")) if TEXT.exists() else []:
        head, body = p.read_text(encoding="utf-8").split("\n", 1)
        h = json.loads(head)
        if group is None or h.get("group") == group:
            out.append((h, body.strip()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("ids", nargs="+")
    f.add_argument("--group", default="")
    f.add_argument("--pause", type=float, default=6.0)
    sub.add_parser("clean")
    sub.add_parser("list")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.ids, a.group, a.pause)
    elif a.cmd == "clean":
        clean()
    else:
        tot = 0
        for h, body in load():
            w = len(body.split())
            tot += w
            print(f"{h['id']}  {h['group']:<8} {h['captions']:<6} {w:>6} w  {h['upload_date']}  {str(h['channel'])[:22]:<22} {str(h['title'])[:60]}")
        print(f"total {tot} words")


if __name__ == "__main__":
    main()
