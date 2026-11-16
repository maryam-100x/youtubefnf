"""After an upload: the video's build/ and old review versions are deleted for good; the final MP4 stays as the master copy.

Permanent, never the Recycle Bin or the Trash: old builds only take space, and emptying a bin by hand is a chore nobody does.
"""
import shutil
from pathlib import Path


def delete_for_good(paths):
    """Delete files/folders permanently (never the Recycle Bin). Returns True when every path is gone."""
    for p in map(Path, paths):
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        elif p.exists() or p.is_symlink():
            p.unlink()
    return not any(Path(p).exists() for p in paths)


def size_mb(p):
    p = Path(p)
    return (sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size) / 2 ** 20


def targets(ctx):
    """build/ and every review file except the final MP4(s)."""
    review = ctx.build.parent / "review"
    out = [ctx.build] if ctx.build.exists() else []
    if review.exists():
        out += [p for p in sorted(review.iterdir()) if not (p.suffix.lower() == ".mp4" and "FINAL" in p.name)]
    return out


def run(ctx):
    todo = targets(ctx)
    if not todo:
        print("  nothing to clean")
        return
    mb = sum(size_mb(p) for p in todo)
    if not delete_for_good(todo):
        raise RuntimeError("some items could not be deleted; check the folders")
    print(f"  {len(todo)} items, {mb:.0f} MB deleted for good (kept: the final MP4).")
