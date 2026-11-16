"""How much of each clip's own picture the film keeps, and how it fills the screen. Every clip plays WHOLE and FILLS 1920x1080 at
full resolution: no zoom that shows nothing in particular, no crop that cuts off part of the source's own frame (its on-screen
overlays, a ticker, a picture-in-picture included), no crop but a letterbox's bars (from the 4K copy where one exists), no panel or inset shrinking
it onto a blurred ground; a 720p source upscaled to fill is fine.

For every clip of the given prep files (their CLIPS: source, span, filter):
  picture  the source's frame, or inside its letterbox bars (a full-width crop of 1.9:1 or wider, centred)
  kept     the crop's area / the picture's area
  zoom     the largest size it reaches on screen / the size of its whole picture filling the screen: 1.00 = whole and filling, 1.04 =
           whole with the house push; read from the composition itself (the body files' shots, bundled with esbuild, every el(dur)
           walked: kit3 Foot's push, and the width and push of any panel component listed in data/panel_scales.json)
Flags (exit 1), unless the clip's prep line says KEEP_CROP: why (a crop that frames what the words name, a built composite) or
KEEP_ZOOM: why (a push into what the words name: a price, a credit, a title):
  CROP   kept < 97% of the picture
  ZOOM   zoom > 1.06 (a crop or push into the picture)
  SMALL  zoom < 0.98 (a panel or inset: the clip doesn't fill the screen)
Notes: BARS (a 1080p letterboxed source, no 4K copy: 1.25x its pixels), UPSCALE (a source under 1080p filling the screen).
Clips used only inside other components (walls, grounds, cards) are measured at the clip itself.

  PIPE tools/motion/qa_kept_area.py <prep<id>.py> [...] --comp <src folder> [--all] [--no-shots]
  (--comp: the composition's src folder, whose body*.tsx files hold the shots and whose t<id>.ts is its timeline; --all prints every
  clip, not only the flagged; --no-shots measures the clips alone)"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFPROBE, NODE  # noqa: E402

HERE = Path(__file__).resolve().parent
CACHE = Path(tempfile.gettempdir()) / "qa_kept_area_probe.json"
BARS_OK = 1.31
# the creator's own panel components that show a clip smaller than the screen:
# {"<Component>": {"clip": "<prop naming the clip>", "w": "<width prop>", "w_default": px, "push": x}}   (the 1920 frame's scale on
# screen = width / 1920 x push), or with "push_prop": "<prop holding [from, to]>" and "push_default": [from, to] instead of "push",
# or {"clip": ..., "k": "<prop holding [from, to] scales>", "k_default": [from, to]} for an inset whose scale is given directly
_PS = HERE / "data" / "panel_scales.json"
PANELS = json.loads(_PS.read_text(encoding="utf-8")) if _PS.exists() else {}
FOOT_PUSH = [1.0, 1.03]   # kit3 Foot's default push (tokens.ts DS.PUSH)


def load_prep(p):
    spec = importlib.util.spec_from_file_location(Path(p).stem, p)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HERE))
    spec.loader.exec_module(m)
    lines = Path(p).read_text(encoding="utf-8").split("\n")
    keep = {}
    for ln in lines:
        mm = re.match(r'\s*"([A-Za-z0-9_]+)":\s*\(', ln)
        tag = "KEEP_CROP" if "KEEP_CROP" in ln else "KEEP_ZOOM" if "KEEP_ZOOM" in ln else None
        if mm and tag:
            keep[mm.group(1)] = tag + ": " + ln.split(tag, 1)[1].strip(" :")[:110]
    return m, keep


def probe(path, cache):
    k = str(path)
    if k not in cache:
        r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", k],
                           capture_output=True, text=True)
        try:
            s = json.loads(r.stdout)["streams"][0]
            cache[k] = [s["width"], s["height"]]
        except (KeyError, IndexError, ValueError):
            cache[k] = None
    return cache[k]


def crop_of(flt, sw, sh):
    m = re.search(r"crop=([^,:]+):([^,:]+)(?::([^,:]+):([^,:]+))?", flt or "")
    if not m:
        return sw, sh, 0, 0
    ev = lambda e: float(eval(e.replace("in_w", "iw").replace("in_h", "ih"), {}, {"iw": sw, "ih": sh}))  # noqa: E731
    cw, ch = ev(m.group(1)), ev(m.group(2))
    cx, cy = (ev(m.group(3)), ev(m.group(4))) if m.group(3) else ((sw - cw) / 2, (sh - ch) / 2)
    return cw, ch, cx, cy


def panel_scale(d, p):
    """the 1920 frame's scale on screen for one panel element, from its data/panel_scales.json entry"""
    if "k" in d:
        return max(p.get(d["k"]) or d.get("k_default", [1.0]))
    w = p.get(d.get("w", "w")) or d.get("w_default") or 1920
    push = max(p.get(d["push_prop"]) or d.get("push_default", [1.0])) if "push_prop" in d else d.get("push", 1.0)
    return w / 1920 * push


def shots_scales(comp):
    """{clip: [(film seconds, component, scale of the 1920 frame)]} from the composition's body files"""
    tmp = Path(tempfile.mkdtemp(prefix="qa_kept_"))
    src = (HERE / "src" / comp).as_posix()
    bodies = sorted(p.stem for p in (HERE / "src" / comp).glob("body*.tsx"))
    entry = ["import React from 'react';"]
    for b in bodies:
        entry.append(f"import * as {b} from 'M/{comp}/{b}';")
    entry.append("const all: any[] = [];")
    for b in bodies:
        entry.append(f"for (const v of Object.values({b})) if (Array.isArray(v)) (v as any[]).forEach((s: any) => s && typeof s.el === 'function' && all.push(s));")
    entry.append("""all.sort((a, b) => a.at - b.at);
const simple = (v: any): any => (v === null || v === undefined || typeof v === 'function' || React.isValidElement(v)) ? null
  : Array.isArray(v) ? v.map(simple) : typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, simple(x)])) : v;
const walk = (el: any, out: any[]) => {
  if (Array.isArray(el)) { el.forEach((x) => walk(x, out)); return; }
  if (!React.isValidElement(el)) return;
  const t: any = el.type, p: any = el.props || {};
  const name = typeof t === 'string' ? t : (t && (t.displayName || t.name)) || '';
  const props: any = {};
  for (const k of Object.keys(p)) if (k !== 'children') props[k] = simple(p[k]);
  out.push({name, props});
  for (const k of Object.keys(p)) { const v = p[k]; if (k === 'children' || React.isValidElement(v) || (Array.isArray(v) && v.some(React.isValidElement))) walk(v, out); }
};
const res = all.map((s, j) => { const e = j + 1 < all.length ? all[j + 1].at : s.at + 3; const out: any[] = [];
  try { walk(s.el(e - s.at), out); } catch (x) {} return {at: s.at, tree: out}; });
console.log(JSON.stringify(res));""")
    (tmp / "entry.tsx").write_text("\n".join(entry), encoding="utf-8")
    nm = (HERE / "node_modules").as_posix()
    (tmp / "build.mjs").write_text(f"""import * as esbuild from 'file:///{nm}/esbuild/lib/main.js';
import fs from 'fs';
const M = '{(HERE / "src").as_posix()}';
await esbuild.build({{entryPoints: ['{(tmp / "entry.tsx").as_posix()}'], bundle: true, platform: 'node', format: 'cjs',
  outfile: '{(tmp / "out.cjs").as_posix()}', jsx: 'automatic', nodePaths: ['{nm}'], logLevel: 'error',
  loader: {{'.png': 'empty', '.jpg': 'empty', '.mp3': 'empty', '.wav': 'empty', '.css': 'empty', '.ttf': 'empty', '.woff2': 'empty'}},
  plugins: [{{name: 'm', setup(b) {{
    b.onResolve({{filter: /^M\\//}}, (a) => {{ const p = M + a.path.slice(1); return {{path: fs.existsSync(p + '.tsx') ? p + '.tsx' : p + '.ts'}}; }});
    // words not yet in words.json (a re-take, a wording pass) give NaN instead of throwing: every other shot is still read
    b.onLoad({{filter: /[\\\\/]t\\d+\\w*\\.ts$/}}, (a) => ({{loader: 'ts', resolveDir: '{src}', contents: fs.readFileSync(a.path, 'utf8')
      .replace(/throw new Error\\(`[^`]*`\\);/g, 'return NaN;')}}));
  }}}}],
}});
""", encoding="utf-8")
    r = subprocess.run([NODE, str(tmp / "build.mjs")], capture_output=True, text=True, cwd=str(HERE))
    if r.returncode:
        print("shots: the bundle failed:", r.stderr[-800:])
        return {}
    r = subprocess.run([NODE, str(tmp / "out.cjs")], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(HERE))
    try:
        S = json.loads(r.stdout)
    except ValueError:
        print("shots: no output", r.stderr[-800:])
        return {}
    use = {}
    for s in S:
        for n in s["tree"]:
            p, nm_ = n["props"], n["name"]
            if nm_ == "Foot" and p.get("clip"):
                use.setdefault(p["clip"], []).append((s["at"], "Foot", max(p.get("push") or FOOT_PUSH)))
            elif nm_ in PANELS and p.get(PANELS[nm_].get("clip", "clip")):
                use.setdefault(p[PANELS[nm_].get("clip", "clip")], []).append((s["at"], nm_, panel_scale(PANELS[nm_], p)))
    return use


def fmt(t):
    return "--:--" if t is None or t != t else f"{int(t // 60)}:{t % 60:05.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preps", nargs="+")
    ap.add_argument("--comp", help="the composition's src folder (needed unless --no-shots)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--no-shots", action="store_true")
    a = ap.parse_args()
    if not a.no_shots and not a.comp:
        ap.error("--comp <src folder> (or --no-shots)")
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    use = {} if a.no_shots else shots_scales(a.comp)
    bad, rows = 0, []
    for pf in a.preps:
        m, keep = load_prep(pf)
        for name, (s, t0, t1, *pre) in m.CLIPS.items():
            flt = pre[0] if pre else ""
            try:
                path = m.src(s)
            except Exception:
                path = Path(s) if Path(s).is_absolute() else Path(getattr(m, "DL", HERE)) / s
            wh = probe(path, cache) if isinstance(flt, str) else None
            if not wh:
                rows.append((name, Path(pf).name, "no source / unread filter", "")); continue
            sw, sh = wh
            cw, ch, cx, cy = crop_of(flt, sw, sh)
            bars = bool(flt) and cw >= sw - 1 and abs(cx) < 1 and cw / ch >= 1.9 and abs(cy - (sh - ch) / 2) <= 8
            # a letterboxed source plays whole, bars kept: cutting the bars off and filling is a CROP
            pw, ph = sw, sh
            k = max(1920 / cw, 1080 / ch)
            base = max(1920 / pw, 1080 / ph)
            kept = (cw * ch) / (pw * ph)
            uses = use.get(name, [])
            shown = max([k * sc for _, _, sc in uses], default=None)
            small = min([k * sc for _, _, sc in uses], default=None)
            at = uses[0][0] if uses else None
            via = ",".join(sorted({u[1] for u in uses})) or ("-" if use else "")
            zoom = (shown if shown is not None else k) / base
            zmin = (small if small is not None else k) / base
            st = []
            if name in keep:
                st.append("KEPT " + keep[name])
            else:
                if kept < 0.97 and "composite" not in flt:
                    st.append("CROP")
                if zoom > 1.06:
                    st.append("ZOOM")
                if zmin < 0.98:
                    st.append("SMALL")
            notes = []
            if bars and sh <= 1080:
                notes.append("BARS (1080p, no 4K copy)")
            if sh < 1000 and not bars:
                notes.append("UPSCALE")
            flag = any(x in ("CROP", "ZOOM", "SMALL") for x in st)
            bad += flag
            if flag or a.all or name in keep:
                rows.append((name, Path(pf).name, f"{fmt(at)} {sw}x{sh} {(flt or '').split(',')[0][:24]:24s} kept {kept * 100:5.1f}%  "
                             f"zoom {zoom:.2f}" + (f" (min {zmin:.2f})" if zmin < zoom - 0.01 else ""), f"{via:12s} {' '.join(st + notes)}"))
    CACHE.write_text(json.dumps(cache))
    for r in rows:
        print(f"{r[0]:24s} {r[1]:18s} {r[2]}  {r[3]}")
    print(f"{bad} clip(s) flagged (CROP: kept < 97%, ZOOM: over 1.06x its whole picture filling the screen, SMALL: not filling it)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
