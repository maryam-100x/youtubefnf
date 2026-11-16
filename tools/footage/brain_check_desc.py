"""Check a description file against its sheets' index before it is built in: every shot of the sheets described exactly once, every
field of DESCRIBE.md's schema present, box references ("b2", "f0") pointing at boxes that exist in that frame's detections, grid boxes
inside 0-1, flags from the known set, frame keys among the row's frames.

  EDIT tools/footage/brain_check_desc.py <key or CODE> <desc.json> [<desc.json> ...]
      [--sheets 12-22]   only the shots of those sheets (a part written by one of several describers)
A `ui` reading ({"frame": N, "read": "..."}) must name one of the shot's frames inside its span; `facts` need `via` and either fact ids
or a research file's line (`FILE:line`)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_detect  # noqa: E402
import brain_lib as B  # noqa: E402

FIELDS = ["id", "desc", "who", "what", "action", "setting", "time", "mood", "flags", "subject", "subject_boxes", "fit916", "text_from", "missed_cut"]
FLAGS = {"dark", "lowres", "upscaled", "letterbox", "ui", "text", "blocked", "blur", "wide", "quiet", "action", "short", "social", "tv", "cinematic",
         "fade_in", "fade_out", "flash_in"}
FILE_LINE = re.compile(r".+:\d+$")


def main():
    args = sys.argv[1:]
    rng = None
    if "--sheets" in args:
        i = args.index("--sheets")
        a, b = args[i + 1].split("-")
        rng = (int(a), int(b))
        args = args[:i] + args[i + 2:]
    key = args[0]
    files = args[1:]
    idx = json.loads((B.WORK / "sheets" / B.key_file(key) / "index.json").read_text(encoding="utf-8"))
    if rng:
        idx = idx[rng[0] - 1:rng[1]]
    rows = {r["id"]: (r, s["sheet"]) for s in idx for r in s["shots"]}
    recs = []
    for f in files:
        recs += json.loads(Path(f).read_text(encoding="utf-8"))
    seen, problems = {}, []
    for r in recs:
        sid = r.get("id")
        if sid not in rows:
            problems.append(f"{sid}: not a shot of these sheets")
            continue
        if sid in seen:
            problems.append(f"{sid}: described twice")
        seen[sid] = r
        for fld in FIELDS:
            if fld not in r:
                problems.append(f"{sid}: missing {fld}")
        bad = set(r.get("flags", [])) - FLAGS
        if bad:
            problems.append(f"{sid}: unknown flags {sorted(bad)}")
        if r.get("fit916") not in ("ok", "tight", "no"):
            problems.append(f"{sid}: fit916 {r.get('fit916')!r}")
        row = rows[sid][0]
        ui = r.get("ui")
        if ui is not None:
            if not (isinstance(ui, dict) and isinstance(ui.get("read"), str) and isinstance(ui.get("frame"), int)):
                problems.append(f"{sid}: ui {ui!r} (want {{\"frame\": N, \"read\": \"...\"}})")
            elif not row["f_in"] <= ui["frame"] <= row["f_out"]:
                problems.append(f"{sid}: ui frame {ui['frame']} outside the shot {row['f_in']}-{row['f_out']}")
        for fx in r.get("facts", []) or []:
            if not fx.get("via") or not (fx.get("ids") or FILE_LINE.match(str(fx.get("via", "")))):
                problems.append(f"{sid}: fact {fx}")
        for m in r.get("moments", []) or []:
            if not (isinstance(m.get("t"), (int, float)) and 0 <= m["t"] <= (row["f_out"] - row["f_in"] + 1) / 30 + 0.05):
                problems.append(f"{sid}: moment {m}")
        k = row.get("key", key)
        det = brain_detect.load_all(k)
        for fk, ref in (r.get("subject_boxes") or {}).items():
            if fk == "img":
                fnum = row["frames"][0]
            else:
                if not (fk.startswith("f") and fk[1:].isdigit()):
                    problems.append(f"{sid}: box key {fk!r}")
                    continue
                fnum = int(fk[1:])
                if fnum not in row["frames"]:
                    problems.append(f"{sid}: box key {fk} is not one of the row's frames {row['frames']}")
            d = det.get(f"{fnum:07d}", {})
            if isinstance(ref, str):
                n = int(ref[1:]) if ref[1:].isdigit() else -1
                pool = d.get("boxes", []) if ref.startswith("b") else d.get("faces", [])
                if n < 0 or n >= len(pool):
                    problems.append(f"{sid}: {fk} -> {ref} but that frame has {len(pool)} such boxes")
            elif isinstance(ref, list):
                if len(ref) != 4 or not all(isinstance(v, (int, float)) and -0.01 <= v <= 1.01 for v in ref) or ref[2] <= ref[0] or ref[3] <= ref[1]:
                    problems.append(f"{sid}: {fk} box {ref}")
            else:
                problems.append(f"{sid}: {fk} -> {ref!r}")
    missing = [sid for sid in rows if sid not in seen]
    print(f"{len(recs)} records for {len(rows)} shots; {len(missing)} shots not described; {len(problems)} problems")
    for m in missing[:20]:
        print("  missing", m, Path(rows[m][1]).name)
    for p in problems[:40]:
        print("  ", p)


if __name__ == "__main__":
    main()
