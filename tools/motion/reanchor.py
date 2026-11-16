"""Re-points a composition's word anchors after the script's words changed (a script rewritten with every point, beat number and
order kept, so each picture keeps its place in its sentence). For every w(beat, phrase [, off][, nth]) / we(...) call in the given
files (tsx with '...' strings, cue sheets with "..."):

  - the phrase is found in the OLD words (the words the edit was built on) -> its word index in that beat;
  - the beat's old words are aligned to its new words (difflib on normalised tokens) -> the same spot in the new text: the matched
    word, or for a rewritten stretch the word at the same share of that stretch;
  - if the old phrase still resolves there, it stays; else the call gets the shortest new phrase (1-4 words) from that spot that is
    unique in the beat (written the way the timeline's norm reads it: apostrophes out, so "theyre").

Every change is listed with the old and new words around it, and anchors whose spot moved to a reworded stretch are marked LOOK: read
those on stills (the words under the picture may have changed). --dry prints without writing.

  PIPE tools/motion/reanchor.py <old words.json> <new words.json> <file> [<file> ...] [--dry]"""
import argparse
import difflib
import json
import re
from pathlib import Path


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("’", "").replace("'", ""))


def beat_words(words):
    out = {}
    for i, x in enumerate(words):
        out.setdefault(x["beat"], []).append(i)
    return out


def find(words, idx, phrase, nth):
    """The global index of the nth match of phrase inside the beat's word indices, or None."""
    toks = [norm(t) for t in phrase.split() if norm(t)]
    seen = 0
    for j, gi in enumerate(idx):
        if all(j + k < len(idx) and norm(words[idx[j + k]]["w"]) == tk for k, tk in enumerate(toks)):
            if seen == nth:
                return j
            seen += 1
    return None


def mapping(old_toks, new_toks):
    """old position -> (new position, exact?) for one beat."""
    sm = difflib.SequenceMatcher(None, old_toks, new_toks, autojunk=False)
    m = {}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        for i in range(i1, i2):
            if tag == "equal":
                m[i] = (j1 + (i - i1), True)
            else:   # replaced or deleted: the same share of the new stretch (or the next new word)
                share = (i - i1) / max(1, i2 - i1)
                j = j1 + int(share * (j2 - j1)) if j2 > j1 else j1
                m[i] = (min(j, len(new_toks) - 1), False)
    return m


def unique_phrase(words, idx, j, ending=False):
    """The shortest run unique in the beat that starts at j (or, for an end anchor, ends at j)."""
    toks = [norm(words[g]["w"]) for g in idx]
    for n in range(1, 5):
        s0 = j - n + 1 if ending else j
        if s0 < 0 or s0 + n > len(toks):
            break
        cand = toks[s0:s0 + n]
        hits = sum(1 for s in range(len(toks) - n + 1) if toks[s:s + n] == cand)
        if hits == 1:
            return " ".join(re.sub(r"[^A-Za-z0-9 ]", "", words[g]["w"].replace("’", "").replace("'", "")) for g in idx[s0:s0 + n]), 0
    # no unique run: the first word with its nth
    first = toks[j]
    nth = sum(1 for s in range(j) if toks[s] == first)
    return re.sub(r"[^A-Za-z0-9]", "", words[idx[j]]["w"].replace("'", "")), nth


CALL = re.compile(r"\b(w|we)\(\s*(['\"])(S\w+)\2\s*,\s*(['\"])(.*?)\4")


def rest_args(src, pos):
    """The call's remaining top-level args after the phrase, and the index of its closing paren."""
    depth, k, args, cur = 0, pos, [], ""
    while k < len(src):
        c = src[k]
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                if cur.strip():
                    args.append(cur.strip())
                return args, k
            depth -= 1
        if c == "," and depth == 0:
            if cur.strip():
                args.append(cur.strip())
            cur = ""
        else:
            cur += c
        k += 1
    raise ValueError("unclosed call")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    OW = json.loads(Path(a.old).read_text(encoding="utf-8"))
    NW = json.loads(Path(a.new).read_text(encoding="utf-8"))
    ob, nb = beat_words(OW), beat_words(NW)
    maps = {b: mapping([norm(OW[g]["w"]) for g in ob[b]], [norm(NW[g]["w"]) for g in nb.get(b, [])]) for b in ob if b in nb}
    kept = changed = look = bad = 0
    for f in a.files:
        p = Path(f)
        src = p.read_text(encoding="utf-8")
        out, last = [], 0
        for m in CALL.finditer(src):
            fn, q, beat, q2, phrase = m.groups()
            args, close = rest_args(src, m.end())
            nth = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
            line = src.count("\n", 0, m.start()) + 1
            if beat not in ob or beat not in nb:
                print(f"BAD  {p.name}:{line} {beat} not in the old or new words")
                bad += 1
                continue
            j_old = find(OW, ob[beat], phrase, nth)
            if j_old is None:
                print(f"BAD  {p.name}:{line} {fn}('{beat}', '{phrase}') not in the OLD words: check by hand")
                bad += 1
                continue
            if fn == "we":   # an end anchor: map the phrase's last word
                j_old += len([t for t in phrase.split() if norm(t)]) - 1
            j_new, exact = maps[beat][j_old]
            still = find(NW, nb[beat], phrase, nth)
            n_toks = len([t for t in phrase.split() if norm(t)])
            if still is not None and (still if fn == "w" else still + n_toks - 1) == j_new:
                kept += 1
                continue
            new_phrase, new_nth = unique_phrase(NW, nb[beat], j_new, ending=(fn == "we"))
            ctx_o = " ".join(OW[g]["w"] for g in ob[beat][max(0, j_old - 3):j_old + 4])
            ctx_n = " ".join(NW[g]["w"] for g in nb[beat][max(0, j_new - 3):j_new + 4])
            tag = "MOVE" if exact else "LOOK"
            look += 0 if exact else 1
            changed += 1
            print(f"{tag} {p.name}:{line} {fn}('{beat}', '{phrase}'{', ' + str(nth) if nth else ''}) -> '{new_phrase}'"
                  f"{' nth ' + str(new_nth) if new_nth else ''}\n      old: {ctx_o}\n      new: {ctx_n}")
            # rewrite: the phrase literal, and the nth argument (added, changed or dropped)
            out.append(src[last:m.start(5)])
            out.append(new_phrase)
            seg_after = src[m.end(5):close]   # from the closing quote to before ')'
            parts = [x for x in args]
            if new_nth or (len(parts) > 1):
                off = parts[0] if parts else "0"
                seg_after = f"{q2}, {off}, {new_nth}" if new_nth else (f"{q2}, {off}" if off not in ("0", "0.0") else q2)
            out.append(seg_after)
            last = close
        out.append(src[last:])
        if not a.dry:
            p.write_text("".join(out), encoding="utf-8")
    print(f"\n{kept} kept, {changed} re-pointed ({look} to LOOK at on stills), {bad} need a hand")


if __name__ == "__main__":
    main()
