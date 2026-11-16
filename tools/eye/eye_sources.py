"""The reviewer's eye: the source bundle a rulebook is distilled from (no model). The creator's rules (rules/*.md), their casebooks
(cases/*.md: every past verdict on a craft, passed and flagged) and the craft standards (standard/*.md), in one file, optionally as
they were at a commit, so a rulebook made for a blind test sees nothing the creator said about the video under test.

  PIPE tools/eye/eye_sources.py --out <bundle.md> [--rev <commit>] [--max-rule N]
  e.g. a blind test on a video the creator has already reviewed: --rev <the last commit before the review began>
       and the production bundle, everything to date:  eye_sources.py --out VIDEOS/<video>/eye/sources.md

--rev reads every file as it was at that commit (rules added or amended later stay out); --max-rule drops the numbered rules above N
(a rule is a line "N. **..." and runs to the next numbered line or heading) in every rules file. Prints what went in."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import REPO  # noqa: E402

FOLDERS = ("rules", "cases", "standard")
RULE_LINE = re.compile(r"^(\d{1,4})\. \*\*")


def list_files(folder, rev):
    """The .md files of a repo folder, now or at a commit (repo-relative posix paths, sorted)."""
    if not rev:
        d = REPO / folder
        return sorted(p.relative_to(REPO).as_posix() for p in d.rglob("*.md")) if d.exists() else []
    r = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "--name-only", rev, folder], capture_output=True, text=True)
    return sorted(p for p in r.stdout.splitlines() if p.endswith(".md")) if r.returncode == 0 else []


def read_at(path, rev):
    if not rev:
        return (REPO / path).read_text(encoding="utf-8")
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{path}"], capture_output=True)
    return None if r.returncode else r.stdout.decode("utf-8")


def cut_rules(text, max_rule):
    """Drop the numbered rules above max_rule (a rule runs to the next numbered line or heading)."""
    if not max_rule:
        return text
    out, keep = [], True
    for ln in text.splitlines():
        if ln.startswith("#"):
            keep = True
        else:
            m = RULE_LINE.match(ln)
            if m:
                keep = int(m.group(1)) <= max_rule
        if keep:
            out.append(ln)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rev", default="")
    ap.add_argument("--max-rule", type=int, default=0)
    a = ap.parse_args()

    parts, found = [], []
    for folder in FOLDERS:
        for path in list_files(folder, a.rev):
            t = read_at(path, a.rev)
            if t is None:
                continue
            if folder == "rules":
                t = cut_rules(t, a.max_rule)
                found += [int(m.group(1)) for m in (RULE_LINE.match(ln) for ln in t.splitlines()) if m]
            parts.append((f"{path} @ {a.rev or 'HEAD'}" + (f" (rules up to {a.max_rule})" if folder == "rules" and a.max_rule else ""), t))
    if not parts:
        raise SystemExit(f"nothing to bundle: no .md files in {', '.join(FOLDERS)} under {REPO}" + (f" at {a.rev}" if a.rev else ""))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# Reviewer's eye source bundle (rev {a.rev or 'HEAD'}" + (f", rules up to {a.max_rule}" if a.max_rule else "") + ")\n\n")
        for title, body in parts:
            f.write(f"\n\n======================================== {title}\n\n{body}\n")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    print(f"  rules: {len(found)} numbered, highest {max(found) if found else '-'}")
    for title, body in parts:
        print(f"  {title}: {len(body) // 1024} KB")


if __name__ == "__main__":
    sys.exit(main())
