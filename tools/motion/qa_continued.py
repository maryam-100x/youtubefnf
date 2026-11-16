"""Continued shots: two clips of one film that are two parts of the same camera shot of their source (standard/LONG_FORM.md: no "a later
part" span of a camera shot the video already shows). Builders who check their spans against each other for overlaps still leave pairs
that sit in one shot a second or two apart: an overlap check can't see them, only the source's own cuts can.

For every pair of clips the composition's code names, cut from the same source file less than --gap seconds apart:
  - a master listed in data/masters.json (by its "file": the official long sources the footage brain has cut into frame-accurate shots,
    KB/footage/brain/<code>.json): both in one shot = CONTINUED when that shot is 8 s or shorter (an edited shot) or the two are under
    3 s apart (inside a master's long takes, minutes long, two moments 10 s apart show other things). A scene-score scan can't stand in
    here: it misses fades and dissolves (two shots a fade to black apart read as one shot);
  - any other source: the source between them is scanned for a camera cut (ffmpeg's scene score over 0.25 at 480 px, as the prep
    scripts' check_cuts), under 3 s apart: none = CONTINUED.

A REASON (a pair of clearly different moments in a long take stays, its reason written where the check reads reasons): a pair is
printed as ALLOWED, not counted, when one of its two clips carries `continued: <the other clip's name> <why>` in the comment block right
above (or on) a code line that names it, or in the # comment on or right above its prep entry. The reason names its partner, so it
covers that one pair: a deliberate replay or an overlay lifted from the same seconds ("a deliberate replay of s12_close ..."), one take
played on across a cut ("plays on from c_s14_grab across the cut"), or two clearly different moments of one of a master's long takes
(what each shows). Two pieces the viewer sees as the same picture again get no reason: one of them changes (the earlier place in the
film keeps it).

  EDIT tools/motion/qa_continued.py "prep<id>*.py" --code "src/<video src>/*.tsx" [--gap 12]
  ... qa_continued.py "prep<id>*.py" --code "src/<video src>/Film.tsx"    one module: the film and every file it imports (a src folder
                                                                            can also hold a prototype that plays its own clips: not the film)"""
import argparse
import fnmatch
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import KB, FFMPEG  # noqa: E402


def load(prep):
    spec = importlib.util.spec_from_file_location(prep.stem, prep)
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    out = {}
    if not hasattr(P, "CLIPS"):                     # a prep that cuts no clips (one that renders stills only): nothing to pair
        return out
    for k, v in P.CLIPS.items():
        if isinstance(v[0], (int, float)):          # (in, out) of the prep's one source, SRC
            v = (getattr(P, "SRC"), *v)
        src = Path(str(v[0]))
        out[k] = (prep.stem, src if src.is_absolute() else Path(P.DL) / src, float(v[1]), float(v[2]))
    return out


BRAIN = KB / "footage" / "brain"
# data/masters.json (shared with qa_shots.py): {"<code>": {"file": "<the master's file name>", ...}}; a master's shots are in
# BRAIN/<code>.json. Read here as {file name, lowercase: code}
_mf = HERE / "data" / "masters.json"
MASTERS = ({str(v["file"]).lower(): k for k, v in json.loads(_mf.read_text(encoding="utf-8")).items() if isinstance(v, dict) and v.get("file")}
           if _mf.exists() else {})


def master_shots(key):
    """[(in, out)] in seconds, the footage brain's shots of one master: {"shots": [{"in", "out"}]} in seconds, or
    {"fps", "shots": [{"f_in", "f_out"}]} in frames"""
    d = json.loads((BRAIN / f"{key}.json").read_text(encoding="utf-8"))
    if d["shots"] and "f_in" in d["shots"][0]:
        fps = float(d.get("fps", 30))
        return [(s["f_in"] / fps, (s["f_out"] + 1) / fps) for s in d["shots"]]
    return [(float(s["in"]), float(s["out"])) for s in d["shots"]]


def shot_of(shots, t):
    return next((i for i, (a, b) in enumerate(shots) if a <= t < b), None)


REASON = "continued:"


def reasons(texts, preps, names):
    """clip name -> [its `continued:` reasons]: the // block right above (or on) every code line that names it, and the # comment on or
    right above its entry in its prep (the way qa_reused.py reads `named-moment:`)"""
    out = {}
    for t in texts.values():
        lines = t.splitlines()
        for i, ln in enumerate(lines):
            code = ln.split("//", 1)[0]
            hit = [n for n in re.findall(r"""['"`/]([A-Za-z0-9_\-]+)(?:\.mp4)?['"`]""", code) if n in names]
            if not hit:
                continue
            block = [ln.split("//", 1)[1]] if "//" in ln else []
            k = i - 1
            while k >= 0 and lines[k].strip().startswith("//"):
                block.insert(0, lines[k].strip()[2:])
                k -= 1
            text = " ".join(block)
            if REASON in text:
                for n in hit:
                    out.setdefault(n, []).append(text.split(REASON, 1)[1].strip())
    for pf in preps:
        last = ""
        for ln in pf.read_text(encoding="utf-8").splitlines():
            s = ln.strip()
            if s.startswith("#"):
                last = (last + " " + s.lstrip("# ")) if last else s.lstrip("# ")
                continue
            m = re.match(r'\s*"([A-Za-z0-9_\-]+)":\s*\(', ln)
            if m and m.group(1) in names:
                text = f"{last} {ln.split('#', 1)[1] if '#' in ln else ''}"
                if REASON in text:
                    out.setdefault(m.group(1), []).append(text.split(REASON, 1)[1].strip())
            last = ""
    return out


def allowed(why, k1, k2):
    """the reason that covers this pair: one of the two clips' `continued:` reasons naming the other"""
    for a, b in ((k1, k2), (k2, k1)):
        for r in why.get(a, []):
            if re.search(r"(?<![A-Za-z0-9_\-])" + re.escape(b) + r"(?![A-Za-z0-9_\-])", r):
                return f"{a}: {r}"
    return None


def cuts_between(src, b, a2):
    """camera cuts in the source from just before the first clip's end to just after the second's start"""
    t0 = max(0.0, b - 0.4)
    r = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-ss", f"{t0:.3f}", "-t", f"{a2 - t0 + 0.4:.3f}", "-i", str(src), "-an", "-vf",
                        "scale=480:-1,select='gt(scene,0.25)',showinfo", "-f", "null", "-"], capture_output=True, text=True)
    hits = [t0 + float(ln.split("pts_time:")[1].split()[0]) for ln in r.stderr.splitlines() if "pts_time:" in ln]
    return [h for h in hits if h - t0 > 0.05 and b - 0.06 <= h <= a2 + 0.06]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("preps", help="the prep files (a glob in tools/motion)")
    ap.add_argument("--code", required=True, help="the composition's files (a glob in tools/motion): only clips they name count")
    ap.add_argument("--gap", type=float, default=12.0)
    a = ap.parse_args()
    clips = {}
    preps = sorted(HERE.glob(a.preps))
    for p in preps:
        clips.update(load(p))
    sys.path.insert(0, str(HERE))
    from codefiles import code_files, module_files
    # 'src/<folder>/*.tsx' reads the subfolder files the film imports too (rebuilt shots in a subfolder);
    # one module file (no wildcard) reads that composition alone: it and every file it imports (the film without its prototype)
    head, _, tail = a.code.replace("\\", "/").rpartition("/")
    if "*" not in a.code and "?" not in a.code and (HERE / a.code).is_file():
        files = set(module_files(HERE / a.code, (".ts", ".tsx")))
    else:
        files = set(HERE.glob(a.code))
        if head and "*" not in head and (HERE / head).is_dir():
            files |= {f for f in code_files(HERE / head, (".ts", ".tsx")) if f.parent != (HERE / head).resolve() and fnmatch.fnmatch(f.name, tail)}
    texts = {p: p.read_text(encoding="utf-8") for p in sorted(files)}
    # a clip the code names on a code line (a name only in a comment plays nothing)
    code = "\n".join(ln.split("//", 1)[0] for t in texts.values() for ln in t.splitlines())
    used = {k: v for k, v in clips.items() if re.search(r"['\"`/]" + re.escape(k) + r"(?:\.mp4)?['\"`]", code)}
    why = reasons(texts, preps, set(used))
    # one source = one file, or every download of one online video (c48_launch_<id>.mp4 and <id>.mp4 from two builders can cut the same
    # shot). A sectioned download (yt-dlp --download-sections) starts its own time at the section's start, so a pair across two files of
    # one video is printed with "(copies)": read it by its frames. The id is the name's last 11 characters after an underscore or alone
    # (so files that only share a common name ending, like <person>_Video_Clip.mp4, do not read as copies of one video)
    def source_key(p):
        m = re.search(r"(?:^|_)([A-Za-z0-9_-]{11})\.mp4$", p.name)
        return ("yt:" + m.group(1)) if m else str(p).lower()
    by = {}
    for k, v in used.items():
        by.setdefault(source_key(v[1]), []).append(k)
    pairs = []
    for ks in by.values():
        ks.sort(key=lambda k: used[k][2])
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                x, y = used[ks[i]], used[ks[j]]
                if y[2] - x[3] > a.gap:
                    break
                pairs.append((ks[i], ks[j]))
    print(f"{len(used)} clips named, {len(pairs)} pairs of one source under {a.gap} s apart")
    bad = 0
    ok = 0
    shots = {}

    def flag(line, k1, k2):
        nonlocal bad, ok
        r = allowed(why, k1, k2)
        if r:
            ok += 1
            print(f"ALLOWED   {line.split(None, 1)[1]}\n          ({r[:300]})")
        else:
            bad += 1
            print(line)
    for k1, k2 in pairs:
        x, y = used[k1], used[k2]
        if x[1] != y[1]:
            # two downloads of one video: their times only line up when both start at the video's start, so they're read by frames
            if y[2] < x[3] + 3.0:
                flag(f"COPIES    {x[1].name} / {y[1].name}: {k1} ({x[0]}) {x[2]:.2f}-{x[3]:.2f} & {k2} ({y[0]}) {y[2]:.2f}-{y[3]:.2f}"
                     f" (two downloads of one video: read by their frames)", k1, k2)
            continue
        if y[2] < x[3] - 0.05:
            flag(f"OVERLAP   {x[1].name}: {k1} ({x[0]}) {x[2]:.2f}-{x[3]:.2f} & {k2} ({y[0]}) {y[2]:.2f}-{y[3]:.2f}", k1, k2)
            continue
        gap = y[2] - x[3]
        key = MASTERS.get(x[1].name.lower())
        if key:
            sh = shots.setdefault(key, master_shots(key))
            i, j = shot_of(sh, (x[2] + x[3]) / 2), shot_of(sh, (y[2] + y[3]) / 2)
            if i is not None and i == j and (sh[i][1] - sh[i][0] <= 8.0 or gap < 3.0):
                flag(f"CONTINUED {key} shot {sh[i][0]:.2f}-{sh[i][1]:.2f}: {k1} ({x[0]}) {x[2]:.2f}-{x[3]:.2f} & {k2} ({y[0]}) "
                     f"{y[2]:.2f}-{y[3]:.2f}", k1, k2)
            continue
        if gap < 3.0 and not cuts_between(x[1], x[3], y[2]):
            flag(f"CONTINUED {x[1].name}: {k1} ({x[0]}) {x[2]:.2f}-{x[3]:.2f} & {k2} ({y[0]}) {y[2]:.2f}-{y[3]:.2f}: no cut between", k1, k2)
    print(f"{bad} flag(s); {ok} allowed by a `continued:` reason")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
