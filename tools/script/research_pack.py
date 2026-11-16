"""The last step of a research pack: the interview questions go to the main chat, never to the creator from the researching chat or
agent, so the creator is asked once, by the chat that writes the script.

python -I tools/script/research_pack.py <research folder> [--write]

A chat or agent that only researches suggests questions in the folder's OPINIONS.md; the interview is the main chat's, asked with its
script draft.

Checks, each PASS or FAIL (exit 1 on any FAIL):
- OPINIONS.md exists (with --write it is made from the research files' "open / suggested interview questions" sections, every
  candidate listed by file, to be trimmed to the best 3-6) and carries the main chat's header ("The interview is the main chat's").
- OPINIONS.md holds 3-6 numbered questions (more = not trimmed yet; fewer = too few for a long video).
- No file in the folder says its questions were asked of the creator (a heading with "questions" and "asked", or "asked the creator").

The depth gate (research is viewed with a critical eye, never called complete over a pass that only scratched the surface):
- No file claims completeness ("researched whole", "researched everything", "fully researched", "exhaustive", "nothing left", "every
  detail covered" ...). Research is never called complete; it says how deep it went and what is still open.
- The folder (with `deep/`) holds a "Not researched yet" section with at least 5 items: the honest list of what wasn't reached.
- Items carry depth marks `[depth: deep | medium | shallow]` (the research item format: `### <year or title> ... [depth: ...]`); it
  prints the counts and FAILs when there are none or when over 40% are shallow.
- `CRITIC.md` exists: a fresh agent's critical read of the pack, written against the subject itself ("what would someone who lived
  through this say we missed?"), never against the pack's own list; each gap it names is researched or carried to "Not researched yet".
- With `--span 2010-2020`: items per year, FAIL for any year under `--min-per-year` (default 10) deep or medium items, so a quiet year
  can't hide.
Then it prints the one line the closing message follows.
"""
import re
import sys
from pathlib import Path

HEADER_OK = re.compile(r"interview is the main chat'?s", re.I)
Q_HEADING = re.compile(r"^#{2,4}\s.*\b(open questions|interview questions)\b", re.I)
ASKED = re.compile(r"^#{2,4}\s.*questions.*\basked\b|\basked (them|the creator)\b.*\?|questions asked (19|20)\d\d", re.I | re.M)
NUMBERED_Q = re.compile(r"^\s*\d+\.\s+(.+\?)\s*$")
CLAIM = re.compile(r"researched (whole|everything|in full|completely)|fully researched|research(ed)? (is )?complete|complete research|"
                   r"exhaustive(ly)? research|nothing (is )?left (out|to research)|every detail (is )?covered|covers? everything",
                   re.I)
NOTR = re.compile(r"^#{2,4}\s.*not researched", re.I)
DEPTH = re.compile(r"\[depth:\s*(deep|medium|shallow)[^\]]*\]", re.I)
ITEM_YEAR = re.compile(r"^###\s+(\d{4})\b.*\[depth:\s*(deep|medium|shallow)[^\]]*\]", re.I)


def candidates(md):
    """Numbered questions under an 'open / interview questions' heading, until the next heading."""
    out, on = [], False
    for line in md.splitlines():
        if line.startswith("#"):
            on = bool(Q_HEADING.match(line))
            continue
        m = NUMBERED_Q.match(line)
        if on and m:
            out.append(m.group(1).strip())
    return out


def opinions_from(folder, found):
    lines = [f"# The creator's opinions for \"{folder.name}\" (3-6 open questions; the answers rewritten clean in the script)",
             "",
             "Made by `tools/script/research_pack.py` from the research's suggested questions. **The interview is the main chat's** (it",
             "asks with its script draft); the researching chat trims this to the best 3-6 and never asks the creator itself. The answers go",
             "here verbatim.", ""]
    for name, qs in found.items():
        lines.append(f"From `{name}`:")
        lines += [f"{i}. {q}" for i, q in enumerate(qs, 1)]
        lines.append("")
    return "\n".join(lines)


def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__)
        return 2
    folder, write = Path(argv[0]), "--write" in argv
    if not folder.is_dir():
        print(f"FAIL  no folder {folder}")
        return 1
    files = {f.name: f.read_text(encoding="utf-8", errors="ignore") for f in sorted(folder.glob("*.md"))}
    found = {n: candidates(t) for n, t in files.items() if n != "OPINIONS.md"}
    found = {n: q for n, q in found.items() if q}
    fails = 0
    op = folder / "OPINIONS.md"
    if not op.exists() and write and found:
        op.write_text(opinions_from(folder, found), encoding="utf-8")
        files["OPINIONS.md"] = op.read_text(encoding="utf-8")
        print(f"WROTE {op} from {sum(map(len, found.values()))} suggested questions in {', '.join(found)}: trim it to the best 3-6")
    if "OPINIONS.md" not in files:
        print(f"FAIL  no OPINIONS.md ({sum(map(len, found.values()))} suggested questions in the files; --write makes it)")
        fails += 1
    else:
        t = files["OPINIONS.md"]
        if HEADER_OK.search(t):
            print("PASS  OPINIONS.md says the interview is the main chat's")
        else:
            print("FAIL  OPINIONS.md lacks the main chat's header (\"The interview is the main chat's\")")
            fails += 1
        n = sum(1 for line in t.splitlines() if NUMBERED_Q.match(line))
        if 3 <= n <= 6:
            print(f"PASS  OPINIONS.md holds {n} questions")
        else:
            print(f"FAIL  OPINIONS.md holds {n} questions: trim or add to 3-6")
            fails += 1
    for name, t in files.items():
        m = ASKED.search(t)
        if m:
            print(f"FAIL  {name} says questions were asked of the creator: \"{m.group(0).strip()[:90]}\" (they are the main chat's to ask)")
            fails += 1
    fails += depth_gate(folder, argv)
    print(f"Closing message: name {folder.as_posix()}/OPINIONS.md for the main chat and ask the creator none of its questions.")
    return 1 if fails else 0


def depth_gate(folder, argv):
    """No completeness claims, an honest not-researched list, depth marks, a critic's read, every year covered."""
    fails = 0
    texts = {f.relative_to(folder).as_posix(): f.read_text(encoding="utf-8", errors="ignore")
             for f in sorted(list(folder.glob("*.md")) + list(folder.glob("deep/*.md")))}
    for name, t in texts.items():
        if name in ("CRITIC.md", "deep/BRIEF_DEEP.md"):
            continue
        for line in t.splitlines():
            if line.lstrip().startswith(">") or line.count('"') >= 2 and CLAIM.search(line.split('"')[1] if '"' in line else ""):
                continue
            m = CLAIM.search(line)
            if m:
                print(f"FAIL  {name} claims completeness: \"{m.group(0)}\" (say how deep it went, never that it's whole)")
                fails += 1
                break
    notr = 0
    for t in texts.values():
        on = False
        for line in t.splitlines():
            if line.startswith("#"):
                on = bool(NOTR.match(line))
            elif on and line.lstrip().startswith(("-", "*")) or on and re.match(r"\s*\d+\.", line):
                notr += 1
    if notr >= 5:
        print(f"PASS  {notr} items under \"Not researched yet\"")
    else:
        print(f"FAIL  {notr} items under \"Not researched yet\" (at least 5: the honest list of what wasn't reached)")
        fails += 1
    marks = [m.group(1).lower() for t in texts.values() for m in DEPTH.finditer(t)]
    if not marks:
        print("FAIL  no depth marks ([depth: deep | medium | shallow] on every item)")
        fails += 1
    else:
        c = {k: marks.count(k) for k in ("deep", "medium", "shallow")}
        share = c["shallow"] / len(marks)
        line = f"{len(marks)} items: {c['deep']} deep, {c['medium']} medium, {c['shallow']} shallow ({share:.0%} shallow)"
        if share > 0.40:
            print(f"FAIL  {line}: over 40% shallow, dig the shallow ones or carry them to \"Not researched yet\"")
            fails += 1
        else:
            print(f"PASS  {line}")
    if (folder / "CRITIC.md").exists():
        print("PASS  CRITIC.md (a fresh agent's critical read) exists")
    else:
        print("FAIL  no CRITIC.md: a fresh agent reads the pack against the subject and names what's missing")
        fails += 1
    span = next((a.split("=", 1)[1] if "=" in a else argv[argv.index(a) + 1] for a in argv if a.startswith("--span")), None)
    if span:
        y0, y1 = (int(x) for x in span.split("-"))
        mpy = int(next((a.split("=", 1)[1] if "=" in a else argv[argv.index(a) + 1] for a in argv
                        if a.startswith("--min-per-year")), 10))
        per = {y: 0 for y in range(y0, y1 + 1)}
        for t in texts.values():
            for line in t.splitlines():
                m = ITEM_YEAR.match(line)
                if m and int(m.group(1)) in per and m.group(2).lower() != "shallow":
                    per[int(m.group(1))] += 1
        thin = {y: n for y, n in per.items() if n < mpy}
        print("      per year (deep+medium): " + ", ".join(f"{y} {n}" for y, n in per.items()))
        if thin:
            print(f"FAIL  thin years (under {mpy} deep or medium items): " + ", ".join(f"{y} ({n})" for y, n in thin.items()))
            fails += 1
        else:
            print(f"PASS  every year {y0}-{y1} has {mpy}+ deep or medium items")
    return fails


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
