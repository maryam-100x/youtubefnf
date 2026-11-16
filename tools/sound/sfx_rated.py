"""sfx_rated.py: every effect a cue sheet places, against the creator's ratings (the rating lock: score.rating(); the lock itself is in
score.py, which refuses an unrated sound when the sheet builds it and again at the mix, unless it is a sample for the creator's ear,
test=True).

This is the lock's reader and its proof: it lists each sound a sheet uses with where its rating comes from, and the ones the creator
never rated.
  - a sheet that still loads: imported with the lock set to record (score.SFX_LOCK), so every Sfx it builds is listed, refused ones too;
  - a sheet that can't load any more (its build files were cleaned up): read as text, every sound it names (quoted paths,
    LIB / "<job>/<file>" joins against the sheet's own Path(...) folders and the effect folders under SFX, pal("name")); --static
    forces this;
  - --frozen <cues_frozen.json>: the effects a mix really placed (the gate's frozen copy), each name found on disk.

  EDIT tools/sound/sfx_rated.py <cues.py> [more.py ...] [--static] [--frozen <json>]
  exit 1 when a sound is unrated (a test=True sample is listed, never counted)
"""
import argparse
import importlib.util
import io
import contextlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score  # noqa: E402

sys.path.insert(0, str(HERE.parent / "common"))
from paths import PUBLIC, SFX  # noqa: E402

# where effects live: the house library, the Sound Test rounds, the house pack, anything else under SFX, and the effects folders of the
# Remotion public dirs
ROOTS = [SFX / "lib", SFX / "taste", SFX / "pack", SFX] + sorted(PUBLIC.glob("*/sfx"))
ABS = r"(?:[A-Za-z]:)?/"   # an absolute path (Windows or macOS)


def by_import(sheet):
    """[(path, note, of, test)] of every Sfx the sheet builds, or None if it can't load"""
    score.SFX_LOCK[0] = "record"
    built = []
    real = score.Sfx.__post_init__

    def spy(self):
        try:
            real(self)
        except ValueError as e:   # a banned file: listed with the ban, the sheet read on
            built.append((str(self.path), f"BANNED: {e}"[:120], self.of, self.test))
            return
        built.append((str(self.path), self.note, self.of, self.test))
    score.Sfx.__post_init__ = spy
    try:
        sys.path.insert(0, str(Path(sheet).parent))
        spec = importlib.util.spec_from_file_location(f"cues_{Path(sheet).stem}", sheet)
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
    except BaseException as e:  # noqa: BLE001 (a sheet's SystemExit on a missing build file is the case this falls back from)
        return None, f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        score.Sfx.__post_init__ = real
        score.SFX_LOCK[0] = "refuse"
    return built, None


def by_text(sheet):
    """[(path, note, None, False)] of every sound the sheet's text names (it and the sibling sheets it imports from)"""
    txt = Path(sheet).read_text(encoding="utf-8")
    # the effects only: music beds (MUSIC, a Cue's track) are not effects
    folders = [Path(m) for m in re.findall(r"""Path\(\s*["'](""" + ABS + r"""[^"']+)["']\s*\)""", txt) if "/music" not in m.lower()] + ROOTS
    out = []
    for m in re.finditer(r"""pal\(\s*["']([a-z_]+)["']\s*\)""", txt):
        if m.group(1) in score.PALETTE and isinstance(score.PALETTE[m.group(1)], dict):
            out.append((score.PALETTE[m.group(1)]["file"], f"pal('{m.group(1)}')", None, False))
    for m in re.finditer(r"""["']([^"'\n]+\.(?:wav|mp3))["']""", txt):
        s = m.group(1)
        if "{" in s:
            continue
        if re.match(ABS, s):
            low = s.lower()
            if "/music" not in low and "/voice/" not in low and "/insert/" not in low and not (Path(s).exists() and Path(s).stat().st_size > 5e6):
                out.append((s, "a path in the sheet", None, False))
            continue
        hit = next((f / s for f in folders if (f / s).exists()), None)
        if hit and hit.stat().st_size > 5e6:   # a bed's edit (over 5 MB): music, not an effect
            continue
        if hit:
            out.append((str(hit).replace("\\", "/"), "a join in the sheet", None, False))
    return out


def by_frozen(path):
    """the effects a mix really placed, by file stem: [(path or stem, note, of, False)]"""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    stems = sorted({e[1] for e in d["effects"]})
    out = []
    for st in stems:
        hit = None
        for r in ROOTS:
            if not r.exists():
                continue
            hit = next((p for p in r.rglob(f"{st}.*") if p.suffix.lower() in (".wav", ".mp3")), None)
            if hit:
                break
        out.append((str(hit).replace("\\", "/") if hit else f"(not found) {st}", "placed in the frozen mix", None, False))
    return out


def report(title, rows):
    seen, bad = {}, []
    for p, note, of, test in rows:
        key = (p, of)
        if key in seen:
            continue
        label, ok, _ = score.rating(of or p, note)
        if of:
            label = f"a cut of {Path(of).name}: {label}"
        seen[key] = (label, ok, test)
        if not ok and not test:
            bad.append(p)
    print(f"\n{title}: {len(seen)} sounds")
    for (p, of), (label, ok, test) in sorted(seen.items(), key=lambda kv: (kv[1][1], kv[0][0])):
        mark = "TEST " if test and not ok else ("     " if ok else "NO   ")
        print(f"  {mark}{Path(p).name[:46]:46s} {label}")
    print(f"  unrated: {len(bad)}" + (f" ({', '.join(Path(b).name for b in bad)})" if bad else ""))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets", nargs="*")
    ap.add_argument("--static", action="store_true", help="read the sheets as text, never import them")
    ap.add_argument("--frozen", help="a gate's cues_frozen.json: the effects a mix placed")
    a = ap.parse_args()
    bad = []
    for sh in a.sheets:
        rows, why = (None, "--static") if a.static else by_import(sh)
        how = "imported"
        if rows is None or not rows:   # (a section sheet whose effects another sheet calls builds none on import)
            rows, how = by_text(sh), f"read as text ({why or 'it builds no Sfx on import'})"
        bad += report(f"{sh} [{how}]", rows)
    if a.frozen:
        bad += report(f"{a.frozen} [the effects the mix placed]", by_frozen(a.frozen))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
