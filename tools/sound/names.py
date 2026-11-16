"""A6 of the sound gate: names said wrong (a foreign or made-up name the voice says its own way; foreign names are said the American
way). Before any voice, every proper noun in the script's VOICE lines that isn't plain English must have an entry in the shared table
tools/sound/names.json: its written spelling -> what the TTS is sent ("say": "Kovalchik", the span_takes --say respelling) or "as is"
(checked: the voice says it right). A name with no entry stops the voice step.

names.json starts empty ({"names": {}}) and grows with every video, shared by all of them; add, never delete without a reason:
  {"names": {"<spelling as in script.md>": {"say": "<respelling>" | "as is", "why": "<how it was checked>",
             "ipa": {"us": "<phonemes>", "native": "<phonemes>"}}}}      ("ipa" only for a respelled name the voice tools measure)
A several-word key covers its words where they stand together.

A proper noun: a word with a capital that isn't just a sentence's first letter (Kowalczyk, YouTube, McLaren), an acronym (NASA, MP3),
a word with letters and digits; a sentence's first word only when it has a capital inside or isn't plain English. Plain English: the
word (each part of a hyphenated one) is used in lower case somewhere in the creator's own VOICE lines (every videos/*/script.md),
so "New York", "Speed" or "Coca-Cola" pass and "Kowalczyk", "Gdansk" or "Everest" don't. A table entry of several words ("Hugo Boss",
"New Balance") covers them where they stand together. Possessives ("Netflix's") and plural acronyms ("CEOs") are their name.

  EDIT tools/sound/names.py <video> [--script S] [--table T] [--json out]
      [--list]   (every proper noun of the script and its entry, flagged or not)"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

TABLE = G.SOUND / "names.json"
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’&.-]*")


PLAIN = set("""january february march april may june july august september october november december monday tuesday wednesday thursday
friday saturday sunday us uk usa tv ok""".split())


def plain_corpus():
    """(lower-case words used in the creator's VOICE lines, words written with a capital inside a sentence anywhere in them)"""
    words, caps = set(PLAIN), set()
    for sp in G.VIDEOS.glob("*/script.md"):
        try:
            text = sp.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in G.BEAT_RE.finditer(text):
            line = m[2]
            for w in re.findall(r"[a-z][a-z'’]*", line):     # only words written in lower case
                words.add(w.replace("’", "'").strip("'"))
            toks, starts = tokens_starts(line)
            for i, tok in enumerate(toks):
                if i not in starts and tok[:1].isupper():
                    caps.add(base(tok).lower())
    return words, caps


def tokens_starts(text):
    """the line's words and the indices of those that open a sentence"""
    toks, starts, prev_end = [], set(), True
    for i, m in enumerate(WORD_RE.finditer(text)):
        toks.append(m.group(0))
        if prev_end:
            starts.add(i)
        tail = re.match(r"['\"”’).!?:]*", text[m.end():m.end() + 3]).group(0)
        prev_end = bool(re.search(r"[.!?]['\"”’)]*$", m.group(0) + tail))
    return toks, starts


def base(tok):
    t = tok.replace("’", "'").strip(".'-")
    t = re.sub(r"'s$", "", t)
    if re.fullmatch(r"[A-Z0-9]{2,}s", t):          # CEOs, GPUs
        t = t[:-1]
    return t


def load_table(path=TABLE):
    if not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8")).get("names", {})


def find(script_path, table, plain=None):
    """-> list of (beat, sentence-start?, token index, token, base, covered by)"""
    plain, caps = plain if plain is not None else plain_corpus()
    keys = sorted(((k, [base(t) for t in k.split()]) for k in table), key=lambda kv: -len(kv[1]))
    out = []
    for bid, text in G.script_beats(script_path):
        toks, starts = tokens_starts(text)
        covered = {}
        for k, kt in keys:
            for i in range(len(toks) - len(kt) + 1):
                if all(base(toks[i + j]).lower() == kt[j].lower() for j in range(len(kt))):
                    for j in range(len(kt)):
                        covered.setdefault(i + j, k)
        for i, tok in enumerate(toks):
            b = base(tok)
            if not b or b.isdigit() or re.fullmatch(r"(?i)i('[a-z]+)?", b) or not re.search(r"[A-Za-z]", b) or re.fullmatch(r"\d+(st|nd|rd|th)", b):
                continue
            has_cap = any(c.isupper() for c in b)
            inner_cap = any(c.isupper() for c in b[1:])
            alnum = bool(re.search(r"\d", b)) and bool(re.search(r"[A-Za-z]", b))
            if not (has_cap or alnum):
                continue
            if b.lower() in PLAIN:
                continue
            parts = [p for p in re.split(r"[-&.]", b.lower()) if p]
            is_plain = all(p in plain for p in parts) and not inner_cap and not alnum
            if is_plain:
                continue
            nxt_cap = i + 1 < len(toks) and toks[i + 1][:1].isupper()
            if i in starts and not inner_cap and not alnum and (b.lower() in plain or (b.lower() not in caps and not nxt_cap)):
                continue          # a sentence's first word that is English, or never written with a capital inside a sentence and not
                                  # opening a run of names ("Peace." passes; "Anna Kowalczyk", "Apple" (mid-sentence elsewhere) don't)
            out.append((bid, i in starts, i, tok, b, covered.get(i)))
    return out


def run(P, table_path=TABLE, quiet=False, listing=False):
    table = load_table(table_path)
    found = find(P["script"], table)
    # a run of uncovered names next to each other is one name ("Hugo Boss" without its entry); one flag per name, its beats listed
    groups, cur = [], []
    for item in found:
        bid, st, i, tok, b, cov = item
        if cov:
            continue
        if cur and cur[-1][0] == bid and cur[-1][2] == i - 1:
            cur.append(item)
        else:
            if cur:
                groups.append(cur)
            cur = [item]
    if cur:
        groups.append(cur)
    merged = {}
    for g in groups:
        name = " ".join(x[4] for x in g)
        m = merged.setdefault(name, {"beats": []})
        if g[0][0] not in m["beats"]:
            m["beats"].append(g[0][0])
    flags = [G.flag("A6", f"name:{name}", 0.0, name, f"{name!r} has no entry in names.json (beats {', '.join(m['beats'])}): add its voice "
                    f"spelling or \"as is\"", beats=m["beats"]) for name, m in merged.items()]
    res = {"check": "A6", "script": str(P["script"]), "table": str(table_path), "names": len({(b) for _, _, _, _, b, _ in found}),
           "flags": flags}
    if not quiet:
        print(f"A6 names: {res['names']} proper nouns in {Path(P['script']).name}; {len(flags)} with no entry in {Path(table_path).name}")
        for f in flags:
            print(f"  A6 {f['msg']}   [key {f['key']}]")
        if listing:
            done = set()
            for bid, st, i, tok, b, cov in found:
                if b in done:
                    continue
                done.add(b)
                e = table.get(cov) if cov else None
                print(f"   {b:24} {'-> ' + (e.get('say', '?') if e else 'NO ENTRY'):30} {cov or ''}")
    return res


def main():
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--script")
    ap.add_argument("--table", default=str(TABLE))
    ap.add_argument("--json")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    P = G.paths(a.video, script=a.script)
    res = run(P, table_path=a.table, listing=a.list)
    G.write_json(a.json, res)
    sys.exit(1 if res["flags"] else 0)


if __name__ == "__main__":
    main()
