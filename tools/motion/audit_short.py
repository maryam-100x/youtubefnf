"""The clip audit for built Shorts (their <At from to> layout; pipe.py's audit needs a SHOTS list). Every video a Short plays, from its
start for as long as its range runs, against the clip's real length: a clip that runs out freezes on its last frame.

  PIPE tools/motion/audit_short.py <id> [<id> ...] [--cuts]

--cuts: also every play against its source's own cuts (ffmpeg scene > 0.08 at 320 px): a cut inside a play means the play shows two
shots, and a cut in its first or last 0.1 s is a sliver of the shot before or after (a flash). The detector also fires on fast motion,
camera flashes, smoke and 2D scrolling: look at the frames before moving a start.

Reads videos/<id>*/video.toml ([video] comp, src; [render] pub), bundles audit_at.tsx around src/<src>/<comp>.tsx with esbuild, runs
it with node, measures each clip with ffprobe (in the lean public dir, else PUBLIC) and prints every play that asks for more than the
clip holds (less one frame of 30 fps), and the components it could not look inside (hooks), to read by hand."""
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, FFPROBE, NODE, PUBLIC, VIDEOS_REPO  # noqa: E402

HERE = Path(__file__).resolve().parent
MOTION_PUB = PUBLIC


def clip_len(path, cache={}):
    if path not in cache:
        r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        cache[path] = float(r.stdout.strip() or "nan")
    return cache[path]


_cuts = {}


def source_cuts(path):
    if path not in _cuts:
        r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path), "-vf", "scale=320:-2,select='gt(scene,0.08)',showinfo", "-f", "null", "-"],
                           capture_output=True, text=True)
        _cuts[path] = [float(ln.split("pts_time:")[1].split()[0]) for ln in r.stderr.splitlines() if "pts_time:" in ln]
    return _cuts[path]


def audit(vid, cuts=False):
    folder = next(VIDEOS_REPO.glob(f"{vid}-*"))
    cfg = tomllib.loads((folder / "video.toml").read_text(encoding="utf-8"))
    comp, src = cfg["video"]["comp"], cfg["video"]["src"]
    pub = Path(cfg.get("render", {}).get("pub", MOTION_PUB))
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    tsx = (HERE / "audit_at.tsx").read_text(encoding="utf-8")
    tsx = tsx.replace("__COMP__", comp).replace("__MODULE__", f"../src/{src}/{comp}")
    (out / f"auditat_{comp}.tsx").write_text(tsx, encoding="utf-8")
    esb = HERE / "node_modules/.bin" / ("esbuild.cmd" if os.name == "nt" else "esbuild")
    subprocess.run([str(esb), f"out/auditat_{comp}.tsx", "--bundle", "--platform=node", f"--outfile=out/auditat_{comp}.cjs", "--loader:.json=json",
                    "--log-level=warning"], cwd=HERE, check=True, shell=os.name == "nt")
    rep = out / f"auditat_{comp}.json"
    r = subprocess.run([NODE, f"out/auditat_{comp}.cjs"], cwd=HERE, env={**os.environ, "PLAYS_JSON": str(rep)}, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    data = json.loads(rep.read_text(encoding="utf-8"))
    seen, bad = set(), 0
    print(f"== {vid} {comp}: {r.stdout.strip()}")
    for p in sorted(data["plays"], key=lambda p: p["at"]):
        key = (round(p["at"], 3), p["src"], round(p["from"], 3))
        if key in seen:
            continue
        seen.add(key)
        f = pub / p["src"]
        if not f.exists():
            f = MOTION_PUB / p["src"]
        n = clip_len(f)
        asks = p["from"] + p["len"] * p.get("rate", 1)
        if not asks <= n - 1 / 30:
            bad += 1
            print(f"OVER {p['at']:6.2f}s {p['comp']:8s} {p['src']} from {p['from']:.2f} for {p['len']:.2f} s asks {asks:.2f} of {n:.2f} s")
        if cuts and p["comp"] not in ("Blurred", "Back"):
            inside = [c for c in source_cuts(f) if p["from"] + 0.02 < c < asks - 0.02]
            if inside:
                print(f"CUT  {p['at']:6.2f}s {p['comp']:8s} {p['src']} {p['from']:.2f}-{asks:.2f}: its source cuts at "
                      f"{', '.join(f'{c:.2f}' for c in inside)} (first {inside[0] - p['from']:.2f} s, last {asks - inside[-1]:.2f} s)")
    for o in data["opaque"]:
        print(f"opaque {o['at']:6.2f}s {o['comp']} (uses hooks: read its clips by hand)")
    print(f"   {len(seen)} plays, {bad} over")
    return bad


if __name__ == "__main__":
    ids = [v for v in sys.argv[1:] if not v.startswith("--")]
    sys.exit(1 if sum(audit(v, cuts="--cuts" in sys.argv) for v in ids) else 0)
