"""qa_lit.py: a lit mark lights what the voice is saying at that moment (a light on one thing while the voice names another reads as
incoherent: the eye follows the light, the ear follows the words).

For every lit phrase anchored on a word in the narration (lit="..." litAt={w('S..', '...')}, or {text: '...', at: at(t0, 'S..', '...')}),
it takes the words spoken within +-WIN s of the light's start and fails when none of the lit phrase's content words is among them.
A heuristic (words compared by their first 4 letters, so spelling variants pass; synonyms still flag): a flag is fixed (move the light
to when its words are said, or light what is said then) or explained in the section's COHERENCE table.
Read by the gate (gate.py B17, `check(src_dir)`) and runnable alone:

  PIPE tools/motion/qa_lit.py --src tools/motion/src/<video src> [--section 3]   (--section: only body<section>.tsx)
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codefiles import code_files  # noqa: E402   with the subfolder files the film imports
WIN = 1.0
STOP = set('the a an of to and in on at for is it its by his her their our was were be been as or that this with from'.split())
NUMW = {'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower().replace('’', '').replace("'", ''))


WORDS = []   # the video's words.json, loaded by check()


def t_of(beat, phrase):
    toks = [norm(t) for t in phrase.split() if norm(t)]
    for i, x in enumerate(WORDS):
        if x['beat'] == beat and all(i + k < len(WORDS) and WORDS[i + k]['beat'] == beat and norm(WORDS[i + k]['w']) == tk
                                     for k, tk in enumerate(toks)):
            return x['start']
    return None


def stem(w):
    w = NUMW.get(w, w)
    return w[:4] if len(w) >= 4 and not w.isdigit() else w


def said(t):
    return {stem(norm(x['w'])) for x in WORDS if t - WIN <= x['start'] <= t + WIN}


PATS = [
    re.compile(r"""lit=["']([^"']+)["']\s+litAt=\{\s*w[e]?\(\s*['"](S\d+a?)['"]\s*,\s*['"]([^'"]+)['"]"""),
    re.compile(r"""text:\s*['"]([^'"]+)['"]\s*,\s*at:\s*at\(\s*t0\s*,\s*['"](S\d+a?)['"]\s*,\s*['"]([^'"]+)['"]"""),
]


def check(src_dir, section=None):
    """any video's lights (the gate's B17): its folder's body*.tsx and words.json -> (lights checked, flag lines)"""
    global WORDS
    src_dir = Path(src_dir)
    WORDS = json.loads((src_dir / 'words.json').read_text(encoding='utf-8'))
    # the body files, and the subfolder files the film imports (rebuilt shots in a subfolder carry their lights too)
    files = [src_dir / f'body{section}.tsx'] if section else sorted(src_dir.glob('body*.tsx')) + [
        f for f in code_files(src_dir) if f.parent != src_dir.resolve()]
    return scan_files(files, src_dir)


def scan_files(files, root=None):
    flags, n = [], 0
    for f in files:
        text = f.read_text(encoding='utf-8')
        label = f.resolve().relative_to(Path(root).resolve()).as_posix() if root else f.name
        for pat in PATS:
            for m in pat.finditer(text):
                lit, beat, phrase = m.group(1), m.group(2), m.group(3)
                t = t_of(beat, phrase)
                if t is None:
                    continue
                n += 1
                content = {stem(norm(x)) for x in re.split(r'[\s\-/]+', lit) if norm(x) not in STOP} - {''}
                if content and not (content & said(t)):
                    line = text.count('\n', 0, m.start()) + 1
                    heard = ' '.join(x['w'] for x in WORDS if t - WIN <= x['start'] <= t + WIN)
                    flags.append(f'{label}:{line}  lit "{lit}" at {beat} "{phrase}" ({t:.1f} s), heard: "{heard}"')
    return n, flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help="the video's src folder: tools/motion/src/<folder>")
    ap.add_argument('--section', help='only body<section>.tsx')
    a = ap.parse_args()
    n, flags = check(a.src, a.section)
    print(f'qa_lit: {n} anchored lights checked, {len(flags)} light words not being said')
    for f in flags:
        print('  ' + f)
    sys.exit(1 if flags else 0)


if __name__ == '__main__':
    main()
