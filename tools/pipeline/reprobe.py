"""reprobe.py: the gate's probe made incremental and shift-aware, so a small change (a cut of a fifth of a second) never voids a probe
of hours.

A full probe of a long video (~190,000 frames) takes 1.5-2 hours. Most rounds change a few shots, or move the timing, and the old probe
already holds every other frame. So after a full probe the gate keeps a snapshot (pipeline/gate/probe_state.json): every shot's signature
from the audit (what it builds, its length in frames: audit.tsx), and the hash of every code file the composition imports. The next gate
run plans:

  1. ALIGN   the old and the new shot lists by signature (difflib, in order): a matched shot draws the same picture, so its old probe lines
             are reused, moved by its own shift in frames (a cut, an insert, a bite trimmed: every shot after it shifts uniformly);
  2. CHANGED the new shots with no match (their code or their length changed: the seam of a timing change), and every shot that names a
             component declared in a changed file or in any file importing it (a design-system change reaches every receipt);
  3. PROBE   the changed shots whole, and the SENTINEL frames: every Nth frame of the film (default 12) checked against the reused lines;
             a reused shot whose sentinel frame differs (a change the plan couldn't see: an absolute-time effect, a media file's size) is
             probed whole too, in a second pass;
  4. SPLICE  the reused lines (moved) + the new lines -> probe.jsonl; the still pictures move with their frames, the changed ones go.
A probe-format change (gate.tsx), the composition root, or a change touching most shots plans a full probe instead. Every plan and
its result is logged (pipeline/gate/reprobe_plan.json), so a pass on a spliced probe is told from a full one.

  PIPE tools/pipeline/reprobe.py <video> plan            (what a gate run would probe, nothing run)
  PIPE tools/pipeline/reprobe.py <video> verify --ranges a-b,c-d   (probe those frames fresh into
        pipeline/gate/verify/ and compare them line by line with probe.jsonl: the proof that the spliced probe equals a full one)
  pipe.py <video> gate        runs it by itself when a snapshot exists (--full forces a full probe)
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import MOTION, NODE, RemotionJob, Video, after_remotion, find_video, say, temp_env  # noqa: E402

FPS = 60
SENTINEL = 12          # every Nth frame of the reused stretches is probed again and compared
MARGIN = 2             # frames of margin round a changed shot
FULL_SHARE = 0.6       # a plan that would probe this share of the film or more is a full probe
ROOTS = ("gate.tsx",)  # a change in these is a change of the probe itself: every line changes


# ------------------------------------------------------------------------------------------------------------------- the code's files
IMPORT = re.compile(r"""(?:from\s+|import\s*\(\s*|require\(\s*)['"](\.{1,2}/[^'"]+)['"]""")
DECL = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:const|let|var|function\*?|class|async\s+function)\s+([A-Za-z_$][\w$]*)", re.M)


def src_root(v):
    return Path(getattr(v, "src_root", MOTION / "src"))


def module_files(v):
    """{path: [paths it imports]} for the composition's module and everything it imports (relative imports, .ts/.tsx/.json), plus every
    file of the video's own folder (a subfolder's file comes in through the imports: src/<video>/fix1/; one nothing imports, a
    builder's preview root, changes no frame of the film)"""
    start = [v.src_dir / v.module] + sorted(v.src_dir.glob("*.ts*")) + sorted(v.src_dir.glob("*.json"))
    graph, todo = {}, list(start)
    while todo:
        f = todo.pop()
        if f in graph or not f.exists():
            continue
        deps = []
        if f.suffix in (".ts", ".tsx", ".mjs", ".js"):
            for m in IMPORT.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                base = (f.parent / m.group(1)).resolve()
                for c in (base, base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.tsx", base / "index.ts"):
                    if c.is_file():
                        deps.append(c)
                        todo.append(c)
                        break
        graph[f] = deps
    return graph


def file_hashes(v, graph):
    root = src_root(v)
    out = {}
    for f in graph:
        try:
            rel = f.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            rel = f.as_posix()
        out[rel] = hashlib.sha1(f.read_bytes()).hexdigest()[:16]
    return out


def strip_digits(n):
    return re.sub(r"\d+$", "", n)


# ------------------------------------------------------------------------------------------------- what each declaration names
IMPORT_STMT = re.compile(r"""^import\s+(?:type\s+)?(.+?)\s+from\s+['"](\.{1,2}/[^'"]+)['"]""", re.M | re.S)
TOP = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:declare\s+)?(?:const|let|var|function\*?|class|async\s+function|type|interface|enum)\s+([A-Za-z_$][\w$]*)", re.M)
STMT = re.compile(r"^(?:export|import|const|let|var|function|async|class|type|interface|enum|declare)\b", re.M)
IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def resolve(f, spec):
    base = (f.parent / spec).resolve()
    for c in (base, base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.tsx", base / "index.ts"):
        if c.is_file():
            return c
    return None


def declarations(f):
    """a module's top-level declarations: {name: (its code's hash, the identifiers it names)} and its imported bindings
    {local name: (the file, the name there or "*" for a whole module or a JSON file)}"""
    text = f.read_text(encoding="utf-8", errors="ignore")
    imports = {}
    for m in IMPORT_STMT.finditer(text):
        src = resolve(f, m.group(2))
        if src is None:
            continue
        spec = re.sub(r"\s+", " ", m.group(1)).strip()
        braces = re.search(r"\{(.*)\}", spec)
        head = spec[:braces.start()] if braces else spec
        for part in head.split(","):
            part = part.strip()
            if part.startswith("* as "):
                imports[part[5:].strip()] = (src, "*")
            elif part and IDENT.fullmatch(part):
                imports[part] = (src, "*" if src.suffix == ".json" else "default")
        if braces:
            for b in braces.group(1).split(","):
                b = b.strip().replace("type ", "")
                if not b:
                    continue
                name, _, local = b.partition(" as ")
                imports[(local or name).strip()] = (src, name.strip())
    starts = [(m.start(), m.group(1)) for m in TOP.finditer(text)]
    cuts = sorted({m.start() for m in STMT.finditer(text)} | {len(text)})
    out = {}
    for pos, name in starts:
        end = next((c for c in cuts if c > pos), len(text))
        code = text[pos:end]
        out[name] = (hashlib.sha1(re.sub(r"\s+", " ", code).encode()).hexdigest()[:12], sorted(set(IDENT.findall(code)) - {name}))
    return out, imports


def decl_graph(graph, rel):
    """for the snapshot: {file: {name: [hash, [[dep file, dep name], ...]]}}; a JSON file is one declaration "*" (its whole content)"""
    out = {}
    for f in graph:
        r = rel(f)
        if f.suffix == ".json":
            out[r] = {"*": [hashlib.sha1(f.read_bytes()).hexdigest()[:12], []]}
            continue
        if f.suffix not in (".ts", ".tsx"):
            continue
        decl, imports = declarations(f)
        d = {}
        for name, (h, ids) in decl.items():
            deps = []
            for i in ids:
                if i in decl:
                    deps.append([r, i])
                elif i in imports:
                    src, nm = imports[i]
                    deps.append([rel(src), nm])
            d[name] = [h, deps]
        out[r] = d
    return out


def reached_names(old_decls, new_decls):
    """the declarations whose code changed (or that are new), and every declaration that names one of them, all the way up; a
    declaration named through `import * as M` or a default import counts as the whole module. -> the names (digits stripped)"""
    changed = set()
    for f, d in new_decls.items():
        od = old_decls.get(f, {})
        for name, (h, _deps) in d.items():
            if od.get(name, [None])[0] != h:
                changed.add((f, name))
    rev = defaultdict(set)
    for f, d in new_decls.items():
        for name, (_h, deps) in d.items():
            for df, dn in deps:
                rev[(df, dn)].add((f, name))
                if dn in ("*", "default"):
                    for n2 in new_decls.get(df, {}):
                        rev[(df, n2)].add((f, name))
    hit, todo = set(), list(changed)
    while todo:
        x = todo.pop()
        if x in hit:
            continue
        hit.add(x)
        todo += list(rev.get(x, ()))
        if x[1] == "*" or x[1] == "default":
            pass
    # a whole module named through `*` changed when any of its declarations did
    for f, d in new_decls.items():
        if any((f, n) in hit for n in d):
            for (g, nm), users in list(rev.items()):
                if g == f and nm in ("*", "default"):
                    for u in users:
                        if u not in hit:
                            hit.add(u)
                            todo.append(u)
    while todo:
        x = todo.pop()
        for u in rev.get(x, ()):
            if u not in hit:
                hit.add(u)
                todo.append(u)
    return {strip_digits(n) for _f, n in hit}, sorted({f for f, _n in hit})



# ---------------------------------------------------------------------------------------------------------------------- the snapshot
def shot_table(v):
    """the audit's shots with their signatures (audit.tsx): [{"i", "at", "end", "sig", "names"}]"""
    import pipe
    return pipe.audit_report(v, tag="shots")["shots"]


def snapshot(v, total, shots=None):
    """what a probe (or a render) was made on: every shot's signature and place, every code file's hash, what each file declares and
    imports (so two snapshots can be compared without either tree on disk: the review reels between two renders)"""
    graph = module_files(v)
    shots = shots if shots is not None else shot_table(v)
    root = src_root(v)

    def rel(f):
        try:
            return f.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return f.as_posix()
    return {"at": time.strftime("%Y-%m-%d %H:%M"), "total": total,
            "shots": [{k: s[k] for k in ("at", "end", "sig", "form", "names", "nums") if k in s} for s in shots],
            "files": file_hashes(v, graph),
            "imports": {rel(f): [rel(x) for x in deps] for f, deps in graph.items()},
            "decl": {rel(f): sorted({strip_digits(n) for n in DECL.findall(f.read_text(encoding="utf-8", errors="ignore"))})
                     for f in graph if f.suffix in (".ts", ".tsx")},
            "decls": decl_graph(graph, rel)}


def snapshot_at(v, rev, total=None):
    """the snapshot of the code at a git revision: its tools/motion/src checked out under tools/motion/out/rev_<sha>/src (never
    the shared tree), the audit run there"""
    import subprocess
    import tarfile
    import io
    sha = subprocess.run(["git", "rev-parse", "--short=10", rev], cwd=str(MOTION), capture_output=True, text=True).stdout.strip()
    if not sha:
        raise SystemExit(f"no git revision {rev!r}")
    root = MOTION / "out" / f"rev_{sha}"
    if not (root / "src").exists():
        tar = subprocess.run(["git", "archive", "--format=tar", sha, "src"], cwd=str(MOTION), capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            t.extractall(root, filter="data")
    rv = at_root(v, root / "src")
    snap = snapshot(rv, total or v.frames())
    snap["rev"] = sha
    return snap


def at_root(v, root):
    """the video with its code read from another src root (a revision's checkout, a proof's copy)"""
    import copy
    rv = copy.copy(v)
    rv.src_root = Path(root)
    rv.pipe_dir = v.pipe_dir / "copies" / Path(root).parent.name   # its audit's files never overwrite the video's own (shots_<comp>.json)
    rv.pipe_dir.mkdir(parents=True, exist_ok=True)
    type(rv).src_dir = property(lambda self: Path(getattr(self, "src_root", MOTION / "src")) / self.src)
    return rv


def save_state(d, state):
    (d / "probe_state.json").write_text(json.dumps(state), encoding="utf-8")


def load_state(d):
    p = d / "probe_state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# -------------------------------------------------------------------------------------------------------------------------- the plan
def fr(t):
    """As the render places a frame (JS Math.round, x.5 up), never Python's banker's round (gate.fr)."""
    import math
    return int(math.floor(t * FPS + 0.5))


def plan(v, old, new, review=False):
    """old, new: snapshots. -> {"full": why or None, "map": [(old a, old b, shift)], "probe": [(a, b)] new frames, "why": {...}, "total"}"""
    total = new["total"]
    out = {"full": None, "map": [], "probe": [], "total": total, "why": {}}
    if not old or "imports" not in old and "files" not in old:
        out["full"] = "no snapshot of the last probe"
        return out
    files = new["files"]
    changed_files = sorted(k for k in set(files) | set(old["files"]) if files.get(k) != old["files"].get(k))
    out["why"]["changed_files"] = changed_files
    if any(Path(k).name in ROOTS for k in changed_files):
        out["full"] = f"the probe itself changed ({', '.join(k for k in changed_files if Path(k).name in ROOTS)})"
        return out
    # the names a change reaches: by declaration (a bite 14 frames shorter changes one data file, which the timing module imports,
    # which every body and graphics file imports, so a file-level closure reaches every shot; by declaration only the code that names
    # the changed data at render time is reached, and the timing shows in the shots' own places and lengths)
    if old.get("decls") and new.get("decls"):
        names, files_hit = reached_names(old["decls"], new["decls"])
        out["why"]["files_reached"] = files_hit
        out["why"]["names_reached"] = len(names)
        return finish_plan(out, old, new, names, review)
    importers = defaultdict(set)
    for f, deps in new.get("imports", {}).items():
        for dpath in deps:
            importers[dpath].add(f)
    hit, todo = set(), [k for k in changed_files if k in files]
    while todo:
        f = todo.pop()
        if f in hit:
            continue
        hit.add(f)
        todo += list(importers.get(f, ()))
    names = set()
    for f in hit:
        names |= set(new.get("decl", {}).get(f, []))
    out["why"]["files_reached"] = sorted(hit)
    return finish_plan(out, old, new, names, review)


NUM_TOL = 0.002   # a shot's numbers match within this (or 2e-4 of their size): a timing shift's float noise, never a moved box or a new time


def same_numbers(a, b):
    if a is None or b is None:
        return a == b
    return len(a) == len(b) and all(abs(x - y) <= max(NUM_TOL, 2e-4 * abs(x)) for x, y in zip(a, b))


def finish_plan(out, old, new, names, review=False):
    """align the shots by signature, mark the ones reached by `names`, and the stretches to probe. review=True (review_reels.py): by
    the shape alone, numbers and lengths aside (a shot whose voice moved by 0.1 s is not a new picture to look at)"""
    total = new["total"]
    new_shots = new["shots"]
    key = "form" if review and all("form" in s for s in old["shots"] + new_shots) else "sig"
    osig = [s[key] for s in old["shots"]]
    nsig = [s.get(key) for s in new_shots]
    sm = difflib.SequenceMatcher(None, osig, nsig, autojunk=False)
    matched = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            matched[b + k] = a + k
    reach = []
    probe = []
    out["shots"] = []   # [(new shot, its frames, why)]: "new" (no shape match), "changed" (its numbers), or the reached names it uses
    for j, s in enumerate(new_shots):
        f0, f1 = fr(s["at"]), fr(s["end"]) - 1
        used = {strip_digits(x) for x in s.get("names", [])}
        if j not in matched or (not review and not same_numbers(old["shots"][matched[j]].get("nums"), s.get("nums"))):
            probe.append((f0, f1))
            out["shots"].append((j, f0, f1, "new" if j not in matched else "changed"))
            continue
        if used & names:
            reach.append(j)
            probe.append((f0, f1))
            out["shots"].append((j, f0, f1, sorted(used & names)))
            continue
        o = old["shots"][matched[j]]
        out["map"].append((fr(o["at"]), fr(o["end"]) - 1, f0 - fr(o["at"])))
    out["why"]["unmatched_shots"] = len(new_shots) - len(matched)
    out["why"]["reached_by_files"] = len(reach)
    # the frames after the last shot (an end tail) and anything the shots don't cover: probed
    covered = merge([(a + sh, b + sh) for a, b, sh in out["map"]] + probe)
    gaps, pos = [], 0
    for a, b in covered:
        if a > pos:
            gaps.append((pos, a - 1))
        pos = max(pos, b + 1)
    if pos <= total - 1:
        gaps.append((pos, total - 1))
    out["probe"] = merge([(max(0, a - MARGIN), min(total - 1, b + MARGIN)) for a, b in probe + gaps])
    n_probe = sum(b - a + 1 for a, b in out["probe"])
    out["why"]["probe_frames"] = n_probe
    if n_probe >= FULL_SHARE * total:
        out["full"] = f"{n_probe} of {total} frames changed ({n_probe / total:.0%}): a full probe is as quick"
    return out


def window(p, last):
    """the plan cut to the new frames 0..last (a proof on part of a film): probe ranges and reused stretches clipped there"""
    q = dict(p)
    q["total"] = last + 1
    q["probe"] = [(a, min(b, last)) for a, b in p["probe"] if a <= last]
    q["map"] = [(a, min(b, last - sh), sh) for a, b, sh in p["map"] if a + sh <= last]
    return q


JOIN = 150   # frames: see incremental


def join_close(rs, gap):
    out = []
    for a, b in sorted(rs):
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def merge(rs):
    out = []
    for a, b in sorted(rs):
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


# ------------------------------------------------------------------------------------------------------------------ the probe's lines
FRAME_RE = re.compile(r'^(layout|refusal|kit3d)\|\{"frame":(\d+)')   # kit3d: Emblem3D's measured centre (qa_centred.py)
ABS_RE = re.compile(r'"abs":(\d+)')


def line_frame(ln):
    m = FRAME_RE.match(ln)
    if m:
        return int(m.group(2))
    if ln.startswith("clip|"):
        m = ABS_RE.search(ln)
        return int(m.group(1)) if m else None
    return None


def moved(ln, nf):
    """the line with its frame number set to nf (and a Short's <At> starts, `ats`, by the same shift)"""
    f = line_frame(ln)
    if ln.startswith(("layout|", "refusal|", "kit3d|")):
        ln = FRAME_RE.sub(lambda m: f'{m.group(1)}|{{"frame":{nf}', ln, count=1)
        if '"ats":[' in ln and nf != f:
            ln = re.sub(r'"ats":\[([^\]]*)\]', lambda m: '"ats":[' + ",".join(str(int(x) + nf - f) for x in m.group(1).split(",") if x) + "]", ln)
        return ln
    return ABS_RE.sub(f'"abs":{nf}', ln, count=1)


def reindex(lines_by_frame, mapping):
    """old frame -> new frame through the plan's map; lines of frames outside it are dropped"""
    out = {}
    for a, b, sh in mapping:
        for f in range(a, b + 1):
            ls = lines_by_frame.get(f)
            if ls is not None:
                out[f + sh] = [moved(ln, f + sh) if sh else ln for ln in ls]
    return out


def read_lines(path):
    """{frame: its lines}, [lines of no frame]. A frame drawn twice in one probe (a changed stretch and the sentinels' every 12th
    frame overlap) keeps one drawing: its first layout line, and each clip line once"""
    by = defaultdict(list)
    seen = defaultdict(set)
    other = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            f = line_frame(ln)
            if f is None:
                other.append(ln)
                continue
            kind = ln.split("|", 1)[0]
            if (kind == "layout" and "#layout" in seen[f]) or ln in seen[f]:
                continue
            seen[f].add(ln)
            if kind == "layout":
                seen[f].add("#layout")
            by[f].append(ln)
    return by, other


def norm(ln):
    """a line as compared: its JSON object (frame numbers set to 0)"""
    kind, _, body = ln.partition("|")
    try:
        o = json.loads(body)
    except ValueError:
        return ln
    o.pop("frame", None)
    o.pop("abs", None)
    o.pop("ats", None)
    return kind + json.dumps(o, sort_keys=True)


PX_TOL, OP_TOL = 0.25, 0.011   # what no gate check can tell apart: a box a quarter pixel off (rounding of a push's float noise), opacity 1%


def parsed(ln):
    kind, _, body = ln.partition("|")
    try:
        o = json.loads(body)
    except ValueError:
        return kind, None
    for k in ("frame", "abs", "ats"):
        o.pop(k, None)
    return kind, o


def close(x, y, tol):
    if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
        return abs(x - y) <= tol
    if isinstance(x, dict) and isinstance(y, dict):
        return x.keys() == y.keys() and all(close(x[k], y[k], OP_TOL if k in ("op", "br") else 1e-9 if k in ("c", "e", "pa", "rw") else tol)
                                            for k in x)
    if isinstance(x, list) and isinstance(y, list):
        return len(x) == len(y) and all(close(u, w, tol) for u, w in zip(x, y))
    return x == y


def same_frame(a, b, exact=False):
    """a frame's lines against another's: the same items in the same order, numbers within PX_TOL px (exact=True: byte for byte)"""
    if exact:
        return sorted(norm(x) for x in a) == sorted(norm(x) for x in b)
    pa, pb = sorted((parsed(x) for x in a), key=lambda k: k[0]), sorted((parsed(x) for x in b), key=lambda k: k[0])
    if len(pa) != len(pb):
        return False
    # clip lines of one frame come in any order: matched by their file and source second
    key = lambda kv: (kv[0], json.dumps({k: kv[1].get(k) for k in ("src", "s")}, sort_keys=True) if kv[0] == "clip" and kv[1] else "")
    pa, pb = sorted(pa, key=key), sorted(pb, key=key)
    return all(ka == kb and close(oa, ob, PX_TOL) for (ka, oa), (kb, ob) in zip(pa, pb))


# -------------------------------------------------------------------------------------------------------------------------- running
def run_probe(v, out, spans, entry=None):
    """gate_probe.mjs over spans [(a, b, every)] into out/probe.jsonl (the list goes in a file: it can be longer than a command line)"""
    import pipe
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    lst = out / "ranges.txt"
    lst.write_text(",".join(f"{a}-{b}:{n}" for a, b, n in spans), encoding="utf-8")
    env = {"QA_COMP": v.comp, "QA_PUBLIC": v.pub.as_posix(), **temp_env(), **({"QA_ENTRY": str(entry)} if entry else {})}
    with RemotionJob(f"gate reprobe {v.id} ({sum((b - a) // n + 1 for a, b, n in spans)} frames)", None):
        r = pipe.run_watched([NODE, "gate_probe.mjs", out, "0.25", f"@{lst}", "1"], MOTION, env, out / "probe.log", stall=300)
    after_remotion()
    if r.returncode != 0 or getattr(r, "stalled", False):
        raise SystemExit(f"reprobe: the probe failed{' (stalled)' if getattr(r, 'stalled', False) else ''}: {out / 'probe.log'}")
    return read_lines(out / "probe.jsonl")


def incremental(v, d, p, sentinel=SENTINEL, entry=None):
    """run the plan p: reindex the old probe, probe the changed spans + the sentinels, a second pass for reused shots whose sentinel
    differs, splice into d/probe.jsonl. -> a report dict"""
    t0 = time.time()
    old, other = read_lines(d / "probe.jsonl")
    reused = reindex(old, p["map"])
    total = p["total"]
    # stretches closer than JOIN frames are probed as one: each renderFrames call costs ~4 s of setup, the frames between them less
    # (measured: 28 stretches took 276 s for 6780 frames, 25 fps, against 41 fps in one stretch)
    p = dict(p, probe=join_close(p["probe"], JOIN))
    spans = [(a, b, 1) for a, b in p["probe"]]
    if sentinel:
        spans.append((0, total - 1, sentinel))
    new, _ = run_probe(v, d / "reprobe", spans, entry)
    probed = p["probe"]
    inside = lambda f: any(a <= f <= b for a, b in probed)
    # the sentinels: a reused frame whose fresh lines differ marks its stretch (the reused range it came from) for a whole probe
    bad = []
    checked = 0
    for f, ls in new.items():
        if inside(f) or f not in reused:
            continue
        checked += 1
        if not same_frame(ls, reused[f]):
            bad.append(f)
    extra = []
    if bad:
        for a, b, sh in p["map"]:
            if any(a + sh <= f <= b + sh for f in bad):
                extra.append((a + sh, b + sh))
        extra = join_close(merge(extra), JOIN)
        say(f"  sentinels: {len(bad)} of {checked} reused frames differ from the old probe -> {len(extra)} more stretches probed whole")
        new2, _ = run_probe(v, d / "reprobe2", [(a, b, 1) for a, b in extra], entry)
        new.update(new2)
        probed = merge(probed + extra)
    else:
        say(f"  sentinels: all {checked} reused frames equal the old probe")
    inside = lambda f: any(a <= f <= b for a, b in probed)
    final = {}
    for f in range(total):
        if inside(f):
            if f in new:
                final[f] = new[f]
        elif f in reused:
            final[f] = reused[f]
        elif f in new:
            final[f] = new[f]
    missing = [f for f in range(total) if f not in final]
    if missing:
        raise SystemExit(f"reprobe: {len(missing)} frames have no lines (first {missing[:5]}): run a full probe")
    tmp = d / "probe.jsonl.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        for ln in other:
            fh.write(ln + "\n")
        for f in range(total):
            for ln in final[f]:
                fh.write(ln + "\n")
    os.replace(tmp, d / "probe.jsonl")
    move_stills(d / "still", p["map"], probed)
    rep = {"at": time.strftime("%Y-%m-%d %H:%M"), "total": total, "probed": probed, "probed_frames": sum(b - a + 1 for a, b in probed),
           "reused_frames": total - sum(b - a + 1 for a, b in probed), "sentinel_every": sentinel, "sentinel_checked": checked,
           "sentinel_differ": len(bad), "minutes": round((time.time() - t0) / 60, 1), "why": p["why"]}
    (d / "reprobe_report.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    say(f"  probe: {rep['probed_frames']} frames probed, {rep['reused_frames']} reused (moved with the timing), {rep['minutes']} min")
    return rep


def move_stills(sd, mapping, probed):
    """the still pass's pictures (element-<frame>.jpeg) follow their frames; pictures of probed or dropped frames go"""
    if not sd.exists():
        return
    files = {int(m.group(1)): p for p in sd.glob("element-*.jp*g") if (m := re.search(r"(\d+)\.jpe?g$", p.name))}
    tmp = sd.parent / "still_moving"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    kept = 0
    for a, b, sh in mapping:
        for f in range(a, b + 1):
            p = files.get(f)
            nf = f + sh
            if p is not None and not any(x <= nf <= y for x, y in probed):
                os.replace(p, tmp / f"element-{nf}{p.suffix}")
                kept += 1
    for p in sd.glob("element-*.jp*g"):
        p.unlink()
    for p in tmp.iterdir():
        os.replace(p, sd / p.name)
    tmp.rmdir()
    say(f"  still pictures: {kept} kept and moved with their frames")


# --------------------------------------------------------------------------------------------------------- the change map for others
def changed_ranges(v, since="probe", version=None):
    """the new frame ranges whose shots changed since the last probe (or since the render's parts: their code snapshot), for
    `pipe.py render --changed` and the review reels"""
    d = v.pipe_dir / "gate"
    if since == "render":
        mf = v.render_dir / f"parts_v{version}" / "state.json"
        old = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else None
    else:
        old = load_state(d)
    total = v.frames()
    p = plan(v, old, snapshot(v, total))
    if p["full"]:
        return [(0, total - 1)]
    return p["probe"]


def verify(v, ranges, entry=None):
    """probe these frames fresh and compare them with probe.jsonl, frame by frame: the proof that a spliced probe equals a full one"""
    d = v.pipe_dir / "gate"
    spans = [tuple(int(x) for x in r.split("-")) for r in ranges.split(",")]
    fresh, _ = run_probe(v, d / "verify", [(a, b, 1) for a, b in spans], entry)
    cur, _ = read_lines(d / "probe.jsonl")
    n = diff = 0
    first = []
    for a, b in spans:
        for f in range(a, b + 1):
            if f not in fresh:
                continue
            n += 1
            if not same_frame(fresh[f], cur.get(f, [])):
                diff += 1
                if len(first) < 5:
                    first.append(f)
    say(f"verify: {n} frames probed fresh, {diff} differ from the spliced probe{' (first ' + str(first) + ')' if first else ''}")
    return n, diff, first


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("cmd", choices=["plan", "verify"])
    ap.add_argument("--ranges")
    a = ap.parse_args()
    v = Video(find_video(a.video))
    d = v.pipe_dir / "gate"
    if a.cmd == "plan":
        p = plan(v, load_state(d), snapshot(v, v.frames()))
        print(json.dumps({k: p[k] for k in ("full", "why")}, indent=1))
        print(f"probe {sum(b - a + 1 for a, b in p['probe'])} frames in {len(p['probe'])} stretches; reuse {len(p['map'])} shots")
    else:
        n, diff, _ = verify(v, a.ranges)
        sys.exit(1 if diff else 0)


if __name__ == "__main__":
    main()
