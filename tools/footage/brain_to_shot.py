"""A brain hit as something an edit can use: a curate.py shot entry for a Short (src, t on the clean span's first frame, the 9:16
window cx/cy/h and cx1/cy1 when the subject moves, a `framed` note, `lift` for a dark shot) and, for long form, a CLIPS entry plus the
ffmpeg cut (a letterboxed master's picture filled to 16:9, -bf 0) and the Foot line (VideoCard for a source under 1080p).

  EDIT tools/footage/brain_to_shot.py A1@712.93 [--key reveal] [--at "lifts the lid"] [--dur 1.5] [--beat S07] [--name a1_lid_lift]
A unique prefix of an id works ("A1@712.9")."""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brain_lib as B  # noqa: E402


def fill(src):
    """The crop that fills 16:9 from a letterboxed master's picture (its full height, centred); "" for a full-frame one."""
    pic = B.pic_of(src)
    if tuple(pic) == B.FULL:
        return ""
    W, H = B.size(B.MASTERS[src]["file"])
    ph = int(round((pic[3] - pic[1]) * H))
    pw = int(round(ph * 16 / 9 / 2)) * 2
    return f"crop={pw}:{ph}:{(W - pw) // 2}:{int(round(pic[1] * H))},"


def find(idq):
    for p in sorted(B.BRAIN.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        hits = [r for r in d.get("shots", []) if r["id"] == idq]
        if hits:
            return hits[0]
    cands = []
    for p in sorted(B.BRAIN.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        cands += [r for r in d.get("shots", []) if r["id"].startswith(idq)]
    if len(cands) == 1:
        return cands[0]
    raise SystemExit(f"{len(cands)} records match {idq!r}: " + ", ".join(c["id"] for c in cands[:8]))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:28]


def rel_to(path, base):
    p = Path(path)
    try:
        return p.relative_to(base).as_posix()
    except ValueError:
        return p.as_posix()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--key", default="")
    ap.add_argument("--at", default="")
    ap.add_argument("--dur", type=float, default=0.0, help="the slot's length, to check the clean span covers it")
    ap.add_argument("--beat", default="S01")
    ap.add_argument("--name", default="")
    a = ap.parse_args()
    r = find(a.id)
    v = r.get("v", {})
    sub = r.get("subject", {}).get("label") or r.get("desc", "")[:40]
    key = a.key or slug(sub or r["id"])[:16]
    if r.get("kind") == "image":
        rel = rel_to(r["file"], B.MEDIA)      # the shot's `img` is relative to the media root
        shot = {"key": key, "at": a.at, "img": rel, "cx": v.get("cx", 0.5), "cy": v.get("cy", 0.5), "h": v.get("h", 1.0), "framed": f"{sub}: {r.get('desc', '')[:80]}"}
        print("# curate.py shot (a still):")
        print(json.dumps(shot, ensure_ascii=False))
        print(f"\n# long form: <Still src={{P + '{Path(rel).name}'}} ... /> from {r['file']}")
        return
    src = r["src"]
    clean_len = r["clean_out"] - r["clean_in"]
    t = B.t_for_frame(round(r["clean_in"] * r["fps"]), r["fps"])
    note = f"{sub}: {r.get('desc', '')[:90]}"
    if src in B.MASTERS:
        shot = {"key": key, "at": a.at, "src": src, "t": t, "cx": v.get("cx", 0.5), "cy": v.get("cy", 0.5), "h": v.get("h", 1.0)}
        if "cx1" in v:
            shot["cx1"], shot["cy1"] = v["cx1"], v["cy1"]
        if "dark" in r.get("flags", []):
            shot["lift"] = True
        shot["framed"] = note
        print(f"# curate.py shot ({src} {B.mmss(r['clean_in'])}-{B.mmss(r['clean_out'])}, clean {clean_len:.2f} s, fit {v.get('fit')}; "
              f"flags: {' '.join(r.get('flags', [])) or '-'}; used in: {','.join(r.get('used_in', [])) or '-'})")
        if a.dur and a.dur > clean_len:
            print(f"# WARNING: the slot ({a.dur:.2f} s) is longer than the clean span ({clean_len:.2f} s): the cut would run into the next shot")
        print(json.dumps(shot, ensure_ascii=False))
        name = a.name or f"{src.lower()}_{slug(sub)[:20]}"
        clips_dir = (B.PUBLIC / "<folder>" / "clips").as_posix()
        print("\n# long form: a CLIPS entry (a prep script's table) and the cut")
        print(f'    "{name}": ("{src}", {r["clean_in"]:.3f}, {r["clean_out"]:.3f}),   # {r.get("desc", "")[:80]}')
        print(f'ffmpeg -hide_banner -loglevel error -y -ss {t:.3f} -t {clean_len:.3f} -i "{r["file"]}" -an -vf "{fill(src)}scale=1920:1080:flags=lanczos,setsar=1" '
              f'-c:v libx264 -crf 15 -preset medium -pix_fmt yuv420p -g 15 -bf 0 "{clips_dir}/{name}.mp4"')
        print(f"{{at: w('{a.beat}', '{a.at or '...'}'), el: (d) => <Foot src={{C + '{name}.mp4'}} start={{0}} dur={{d}} />}},")
    else:
        # a library clip: already a file the edits read; the shot's span inside it
        rel = rel_to(r["file"], B.PUBLIC)
        print(f"# library clip {rel}: shot {B.mmss(r['clean_in'])}-{B.mmss(r['clean_out'])} (clean {clean_len:.2f} s, fit {v.get('fit')}; "
              f"flags: {' '.join(r.get('flags', [])) or '-'}; used in: {','.join(r.get('used_in', [])) or '-'})")
        if a.dur and a.dur > clean_len:
            print(f"# WARNING: the slot ({a.dur:.2f} s) is longer than the clean span ({clean_len:.2f} s)")
        comp = "VideoCard" if "lowres" in r.get("flags", []) else "Foot"
        print(f"{{at: w('{a.beat}', '{a.at or '...'}'), el: (d) => <{comp} src={{C + '{Path(rel).name}'}} start={{{r['clean_in']:.2f}}} dur={{d}} />}},   // {r.get('desc', '')[:80]}")
        print(f"# a Short needs a 16:9 file cut to 9:16 by hand (curate.py reads the masters only): window cx {v.get('cx')} cy {v.get('cy')} h {v.get('h')}")


if __name__ == "__main__":
    main()
