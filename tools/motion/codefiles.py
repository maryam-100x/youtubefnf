"""codefiles.py: a video's code files, its subfolders included, so the gate's checks read every file the film is built from (a check
that read only src/<src>/*.tsx would miss the `// subject:`, `// named-moment:` and `// repeat:` lines and the pictures of shots kept in
a subfolder).

The film's code is every file at the top of the video's src folder (as the checks always read it) and every file in a subfolder that
those files import, all the way down (rebuilt shots in a subfolder, placeholder words). A subfolder file nothing imports is not the
film: a builder's preview root stays out of the checks and out of the stamps, so editing it never voids a passed gate or a coherency
read.

  from codefiles import code_files
  code_files(src_dir)                         # the .tsx files
  code_files(src_dir, (".ts", ".tsx"))        # any suffixes; ".json" follows JSON imports too
Standard library only (the pipeline venv, the editing venv)."""
import re
from pathlib import Path

IMPORT = re.compile(r"""(?:\bfrom\s+|\bimport\s*\(\s*|\bimport\s+|\brequire\(\s*)['"](\.{1,2}/[^'"]+)['"]""")


def _target(f, spec):
    base = (f.parent / spec).resolve()
    if base.suffix in (".json", ".ts", ".tsx") and base.is_file():
        return base
    for c in (base.with_suffix(".tsx"), base.with_suffix(".ts"), base / "index.tsx", base / "index.ts"):
        if c.is_file():
            return c
    return None


def module_files(module, exts=(".tsx",)):
    """one composition's code (a src folder can hold the film and a passed prototype beside it, and a check over every top-level file
    would count the prototype's clips and pictures as the film's): the module file and every file it imports, all the way down, inside
    the module's own folder and its subfolders (the shared kits outside it name no film material) -> sorted"""
    m = Path(module).resolve()
    root = m.parent
    seen, todo = set(), [m]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        if f.suffix == ".json":
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for mm in IMPORT.finditer(text):
            t = _target(f, mm.group(1))
            if t is not None and (t.parent == root or root in t.parents) and t not in seen:
                todo.append(t)
    return sorted(p for p in seen if p.suffix in exts)


def code_files(src_dir, exts=(".tsx",)):
    """[top-level files with these suffixes, sorted] + [subfolder files they import (transitively) with these suffixes, sorted]"""
    src = Path(src_dir).resolve()
    if not src.is_dir():
        return []
    top = sorted(p for p in src.iterdir() if p.is_file() and p.suffix in (".ts", ".tsx", ".json"))
    seen, todo = set(), [p for p in top if p.suffix in (".ts", ".tsx")]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in IMPORT.finditer(text):
            t = _target(f, m.group(1))
            if t is None or src not in t.parents:
                continue
            if t.suffix == ".json":
                seen.add(t)
            elif t not in seen:
                todo.append(t)
    sub = sorted(p for p in seen if p.parent != src)
    return [p for p in top if p.suffix in exts] + [p for p in sub if p.suffix in exts]
