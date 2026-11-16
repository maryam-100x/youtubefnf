"""The fallback music library: every track a video's final cue sheet plays, read the way score.py reads it (the cue module's CUES, so
cues built by a helper are seen), with its tempo (the .grid.json), its tags and measures (MUSIC/analysis/*.json, from
analyze_tracks.py), where it played (which part of the track, how far under the voice) and the creator's verdicts; then the tracks in
MUSIC that were never in a final video. Writes KB/MUSIC_USED.md, which the chat reads first when it picks music: tracks that worked
in a final video are kept and reused, rotated, beside new music.

    EDIT tools/sound/music_library.py

Optional data, KB/music_library.json (every key may be left out):
  "final":     {video folder: cue sheet file name}  the sheet a video went out with, where it isn't its newest non-prototype sheet
  "state":     {video folder: words}                a note shown with the video (e.g. "the approved prototype")
  "benchmark": {video folder: words}                a video that is a benchmark, shown with it
  "verdicts":  {track name: [verdict, words]}       the creator's verdict on a track ("yes", "pick", "part" or "no") and the
                                                    creator's words; a "no" is never picked again"""
import glob
import importlib.util
import io
import json
import contextlib
import re
import sys
from pathlib import Path

SOUND = Path(__file__).resolve().parent
sys.path.insert(0, str(SOUND))
import score  # noqa: E402

sys.path.insert(0, str(SOUND.parent / "common"))
from paths import KB, MUSIC, VIDEOS_REPO  # noqa: E402

score.SFX_LOCK[0] = "record"   # this reads past sheets for their music: an effect the rating lock refuses must not hide the tracks

DATA = KB / "music_library.json"
_d = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {}
FINAL = _d.get("final") or {}
STATE = _d.get("state") or {}
BENCH = _d.get("benchmark") or {}
VERDICT = {k: tuple(v) for k, v in (_d.get("verdicts") or {}).items()}


def final_sheet(folder):
    sheets = sorted((folder / "score").glob("*.py"))
    if not sheets:
        return None
    if folder.name in FINAL and (folder / "score" / FINAL[folder.name]).exists():
        return folder / "score" / FINAL[folder.name]
    keep = [s for s in sheets if not s.stem.endswith("p") or len(sheets) == 1]
    return max(keep or sheets, key=lambda p: p.stat().st_mtime)


def load(sheet):
    spec = importlib.util.spec_from_file_location(f"cues_{sheet.stem}", sheet)
    mod = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod


def song_of(path):
    return Path(path).stem


analysis = {}
for f in glob.glob(str(MUSIC / "analysis" / "*.json")):
    d = json.loads(Path(f).read_text(encoding="utf-8"))
    analysis[d.get("title", "").lower()] = d


def info(path):
    g = Path(str(path) + ".grid.json")
    tempo = json.loads(g.read_text(encoding="utf-8")).get("tempo") if g.exists() else None
    name = song_of(path).lower()
    a = analysis.get(name) or analysis.get(name.split(" - ")[0], {})
    return tempo or a.get("tempo_est"), a.get("tags") or "", a.get("energy_8s")


def mmss(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


def main():
    used, problems = {}, []
    folders = sorted(p for p in VIDEOS_REPO.iterdir() if p.is_dir() and not p.name.startswith("_")) if VIDEOS_REPO.exists() else []
    for folder in folders:
        sheet = final_sheet(folder)
        if not sheet:
            continue
        try:
            mod = load(sheet)
        except Exception as e:                                           # a cue sheet whose words or voice moved since: its track names only
            text = sheet.read_text(encoding="utf-8", errors="replace")
            names = set(re.findall(r'T\("([^"]+)"\)', text))
            found = []
            for n in sorted(names):
                hit = next(iter(sorted(MUSIC.rglob(f"{n}*.wav"))), None)
                if hit:
                    used.setdefault(song_of(hit), {"path": hit, "uses": []})["uses"].append((folder.name, sheet.name, None, None, None, None))
                    found.append(n)
            problems.append(f"{folder.name}/{sheet.name} ({type(e).__name__}: its words moved since delivery): "
                            + (f"track names read from the file ({len(found)})" if found else "no track names found"))
            continue
        for c in getattr(mod, "CUES", []):
            p = Path(c.path)
            if p.suffix.lower() != ".wav" or "music" not in p.as_posix().lower():
                continue
            src = c.src if c.align is None else c.align[0] - (c.align[1] - c.t0)
            used.setdefault(song_of(p), {"path": p, "uses": []})["uses"].append(
                (folder.name, sheet.name, c.t0, c.t1, src, c.under))

    lines = ["# The music library: tracks that worked, to rotate", "",
             "*Built by `tools/sound/music_library.py` from every video's final cue sheet (read the way score.py reads it), the tracks' "
             "beat grids and their analysis (`tools/sound/analyze_tracks.py`). Tracks that end up in a final video are kept and can be "
             "reused: a fallback library of always-working music, rotated, beside new music.*", "",
             "**How to pick:** look here first, then a new track (the creator's own in MUSIC, or one rendered by tools/music) where the "
             "video wants a new feel (variety across videos is good). No track twice inside one video; preferably none of the last "
             "video's tracks; a track the creator said no to is never picked again; Shorts: no one track under all of them. The \"from\" "
             "column is the part of the track that sat under the voice: a good place to start it again. Files: MUSIC, never deleted.", "",
             "## In the creator's videos", "",
             "| Track | Tempo | Tags | Where it played (video, film time, from the track's second, dB under the voice) | The creator's word |",
             "|---|---|---|---|---|"]
    for name in sorted(used, key=str.lower):
        u = used[name]
        tempo, tags, _ = info(u["path"])
        where = []
        for v, s, t0, t1, src, under in sorted(u["uses"], key=lambda x: (x[0], x[2] or 0)):
            tag = (f" ({STATE[v]})" if v in STATE else "") + (f" [{BENCH[v]}]" if v in BENCH else "")
            where.append(f"{v[:3]}{tag} (named in {s}; its cue sheet no longer loads)" if t0 is None else
                         f"{v[:3]} {mmss(t0)}-{mmss(t1)} from {src:.1f} s, {under:.1f} dB{tag}")
        word = VERDICT.get(name, ("", ""))[1]
        lines.append(f"| {name} | {tempo:.0f} |" if tempo else f"| {name} | ? |")
        lines[-1] += f" {tags} | {'; '.join(where)} | {word} |"
    lines += ["", "## In MUSIC, never in a final video (candidates: tracks passed over, beds tried and dropped)", "",
              "| Track | Tempo | Tags | The creator's word |", "|---|---|---|---|"]
    for p in sorted((q for q in MUSIC.rglob("*.wav") if "analysis" not in q.parts), key=lambda x: song_of(x).lower()):
        name = song_of(p)
        if name in used:
            continue
        tempo, tags, _ = info(p)
        word = VERDICT.get(name, ("", ""))[1]
        lines.append(f"| {name} | {f'{tempo:.0f}' if tempo else '?'} | {tags} | {word} |")
    no = [k for k, (v, _) in VERDICT.items() if v == "no"]
    lines += ["", f"**Never again (the creator's no):** {', '.join(no) or 'none yet'}.", ""]
    if problems:
        lines += ["*Cue sheets that didn't load (their words or voice moved since; their tracks are missing above):* " + "; ".join(problems), ""]
    KB.mkdir(parents=True, exist_ok=True)
    (KB / "MUSIC_USED.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(used)} tracks in videos, {len(problems)} cue sheet(s) not loaded -> {KB / 'MUSIC_USED.md'}")
    for p in problems:
        print("  not loaded:", p)


if __name__ == "__main__":
    main()
