"""Build tools/sound/palette.json (the house effects palette score.py's rating lock reads) from the house effects set.

The setup unpacks assets/house_sfx.zip into SFX/house/ (sfx/<job>.wav|mp3, manifest.json, README.txt); this writes one house sound
per job: pal('<job>') in a cue sheet then returns its file. Levels (db) are the effect's peak against the voice's peak as the cue
sheet places it; 'place' says where on the picture it goes. The creator's own verdicts change the palette later
(tools/sound/sfx_verdict.py): a job they reject is replaced, a new action goes through their Sound Test first.

    PIPE tools/sound/palette_from_manifest.py            # unpack (if needed) and write the palette
    PIPE tools/sound/palette_from_manifest.py --check    # every palette file exists and decodes
"""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFPROBE, REPO, SFX  # noqa: E402

HOUSE = SFX / "house"
ZIP = REPO / "assets" / "house_sfx.zip"
OUT = Path(__file__).with_name("palette.json")
# the palette names the tools and cue sheets call, where they differ from the file's job name
NAME = {"marker": "mark", "reveal_boom": "reveal"}
NEEDS_DUR = {
    "count_up": "the ticks end when the count lands: cut the file to the count's length, never the whole file under a short count",
    "typing_keyboard": "cut to the typing on screen",
    "writing": "cut to the stroke",
    "fast_forward": "cut to the skip",
}


def unpack():
    if (HOUSE / "manifest.json").exists():
        return
    HOUSE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(HOUSE)
    print(f"unpacked {ZIP.name} -> {HOUSE}")


def build():
    unpack()
    man = json.loads((HOUSE / "manifest.json").read_text(encoding="utf-8"))
    pal = {"_doc": "The house sounds: one sound per recurring action, across every video. Cue sheets take them with "
                   "score.pal(name). An action not here yet goes through the creator's Sound Test first; 'pending' names "
                   "the ones in a test now. db = the effect's peak against the voice's peak."}
    for e in man["effects"]:
        job = Path(e["file"]).stem
        name = NAME.get(job, job)
        v = {"file": (HOUSE / e["file"]).as_posix(), "db": e["db"], "job": e["job"], "use": e["place"]}
        if job in NEEDS_DUR:
            v["needs_dur"] = NEEDS_DUR[job]
        pal[name] = v
    pal["pending"] = []
    pal["pack_jobs"] = {}
    pal["_sound_test_fits"] = {}
    pal["_creator_picks"] = []
    pal["_banned"] = {}
    if OUT.exists():  # keep the creator's own ratings when the palette is rebuilt
        old = json.loads(OUT.read_text(encoding="utf-8"))
        for k in ("pack_jobs", "_sound_test_fits", "_creator_picks", "_banned", "pending"):
            if old.get(k):
                pal[k] = old[k]
        house = HOUSE.as_posix().lower()
        for k, v in old.items():
            # the creator's own sounds: a job they added, or a house job they replaced with a file outside the house set
            if isinstance(v, dict) and v.get("file") and (k not in pal or not str(v["file"]).replace("\\", "/").lower().startswith(house)):
                pal[k] = v
    OUT.write_text(json.dumps(pal, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{OUT}: {sum(1 for v in pal.values() if isinstance(v, dict) and 'file' in v)} house sounds")


def check():
    pal = json.loads(OUT.read_text(encoding="utf-8"))
    bad = 0
    for k, v in pal.items():
        if not (isinstance(v, dict) and v.get("file")):
            continue
        f = Path(v["file"])
        ok = f.exists() and subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                            str(f)], capture_output=True, text=True).stdout.strip() != ""
        print(f"{'ok ' if ok else 'BAD'} {k:16s} {f.name}")
        bad += not ok
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    check() if a.check else build()
