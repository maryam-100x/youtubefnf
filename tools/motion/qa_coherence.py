"""qa_coherence.py: every shot shows exactly what its words say, and plain number cards stay rare.

A shot that directly shows the words stays; a re-pick is the best of a few easy finds, never a picture that only vaguely fits. And a
number said on screen does not get the same card every time: variety, so the device never wears out.

What it fails:
  1. A shot in a section's body file with no row in <video>/rebuild/COHERENCE_<section>.md (the anchor as the code has it: S27 "The
     recipe", or S05 b0 for a beat's first word).
  2. A row whose verdict cell does not END in EXACT or KEPT (a fixed row reads "DEVICE -> EXACT"); a KEPT row needs its reason in the
     fix cell (the cell after the verdict).
  3. Film-wide: more than 12 plain number cards (NumberShot / BigNumber as a shot's own picture), or two of them less than 120 s apart.
     With --section, only the pairs touching that section fail; the film total is printed as information until every section is done.
It also prints how many shots each device carries and its closest pair, so a device leaning on too many lines shows up.

The video's src folder (tools/motion/src/<src>) holds words.json, the section body files body<section>.tsx and, when inserts shift the
timeline, one inserts*.json ([{"at": s, "dur": s}, ...]).

  PIPE tools/motion/qa_coherence.py <video> --src <src folder> [--section 13]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MOTION, video_dirs  # noqa: E402

NUMBER_CARDS = {'NumberShot', 'BigNumber'}
WRAPPERS = {'AbsoluteFill', 'Sequence', 'Series', 'Freeze', 'Loop'}
CAP, GAP = 12, 120.0

SRC = REB = None
SECTIONS, W = [], []


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower().replace('’', '').replace("'", ''))


def load(src, video):
    """the video's words (shifted by its inserts), its sections and its rebuild folder"""
    global SRC, REB, SECTIONS, W
    SRC = MOTION / 'src' / src
    REB = video_dirs(video)[0] / 'rebuild'
    SECTIONS = sorted(p.stem[4:] for p in SRC.glob('body*.tsx') if p.stem[4:])
    words = json.loads((SRC / 'words.json').read_text(encoding='utf-8'))
    ins_f = next(iter(sorted(SRC.glob('inserts*.json'))), None)
    ins = [x for x in json.loads(ins_f.read_text(encoding='utf-8')) if isinstance(x.get('at'), (int, float))] if ins_f else []

    def shift(t):
        return sum(x['dur'] for x in ins if t >= x['at'])

    W = [dict(x, start=x['start'] + shift(x['start'])) for x in words]


def t_of(beat, phrase):
    """The film time of a phrase in a beat (the timeline's w()), or of the beat's first word (b0); None if it isn't there."""
    if not phrase:
        return next((x['start'] for x in W if x['beat'] == beat), None)
    toks = [norm(t) for t in phrase.split() if norm(t)]
    for i, x in enumerate(W):
        if x['beat'] != beat:
            continue
        if all(i + k < len(W) and W[i + k]['beat'] == beat and norm(W[i + k]['w']) == tk for k, tk in enumerate(toks)):
            return x['start']
    return None


START = re.compile(r"(?:\bshot\(|\bexact\(|\{at:\s*)")
ANCHOR = re.compile(r"""\b(w|we|wa|b0)\(\s*['"](S\d+a?)['"](?:\s*,\s*(['"])(.*?)\3)?""")
TAG = re.compile(r"<([A-Z][A-Za-z0-9]*)")


def shots(section):
    """Every shot of a body file: (beat, phrase or '', component, film time)."""
    text = (SRC / f'body{section}.tsx').read_text(encoding='utf-8')
    starts = [m.end() for m in START.finditer(text)]
    out = []
    for k, s in enumerate(starts):
        a = ANCHOR.search(text, s, s + 120)
        if not a:
            continue
        body = text[a.end(): starts[k + 1] if k + 1 < len(starts) else len(text)]
        comp = next((m.group(1) for m in TAG.finditer(body) if m.group(1) not in WRAPPERS), '?')
        phrase = a.group(4) if a.group(1) != 'b0' else ''
        out.append((a.group(2), phrase or '', comp, t_of(a.group(2), phrase)))
    return out


ROW_ANCHOR = re.compile(r"""^(S\d+a?)\s+(?:["“'](.*?)["”']|b0\b)""")
VERDICT = re.compile(r"\b(EXACT|VAGUE|DEVICE|KEPT)\b")


def table(section):
    """The COHERENCE table's rows: {(beat, norm(phrase)): (final verdict, fix cell)}; None when the file is missing."""
    f = REB / f'COHERENCE_{section}.md'
    if not f.exists():
        return None
    rows = {}
    for line in f.read_text(encoding='utf-8').splitlines():
        if not line.lstrip().startswith('|'):
            continue
        cells = [c.strip().replace('`', '') for c in line.strip().strip('|').split('|')]
        key = None
        for c in cells:
            m = ROW_ANCHOR.match(c)
            if m:
                key = (m.group(1), norm(m.group(2) or ''))
                break
        if not key:
            continue
        vi = next((i for i, c in enumerate(cells) if VERDICT.search(c)), None)
        final = VERDICT.findall(cells[vi])[-1] if vi is not None else ''
        fix = cells[vi + 1] if vi is not None and vi + 1 < len(cells) else ''
        rows[key] = (final, fix)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--src', required=True, help='the video\'s src folder under tools/motion/src')
    ap.add_argument('--section')
    a = ap.parse_args()
    load(a.src, a.video)
    if a.section and a.section not in SECTIONS:
        ap.error(f'--section must be one of {SECTIONS}')
    fails = []
    film = []
    for sec in SECTIONS:
        film += [(t, sec, b, p, c) for (b, p, c, t) in shots(sec)]
    lost = [x for x in film if x[0] is None]
    film = sorted([x for x in film if x[0] is not None])
    for _, sec, b, p, _c in lost:
        fails.append(f'{sec}: anchor {b} "{p}" is not in words.json')

    for sec in ([a.section] if a.section else SECTIONS):
        sh = shots(sec)
        rows = table(sec)
        if rows is None:
            fails.append(f'{sec}: no rebuild/COHERENCE_{sec}.md')
            continue
        missing = sorted({f'{b} "{p}"' if p else f'{b} b0' for (b, p, _c, _t) in sh if (b, norm(p)) not in rows})
        open_ = [f'{b} "{p}"' if p else f'{b} b0' for (b, p), (v, fix) in rows.items() if v not in ('EXACT', 'KEPT')]
        bare = [f'{b} "{p}"' for (b, p), (v, fix) in rows.items() if v == 'KEPT' and len(fix) < 8]
        kept = sum(1 for v, _f in rows.values() if v == 'KEPT')
        print(f'{sec}: {len(sh)} shots, {len(rows)} rows, {kept} kept, {len(missing)} without a row, {len(open_)} open')
        for name, xs in (('no row', missing), ('open verdict', open_), ('KEPT without a reason', bare)):
            if xs:
                fails.append(f'{sec}: {name} ({len(xs)}): ' + ', '.join(xs[:12]) + (' ...' if len(xs) > 12 else ''))

    cards = [x for x in film if x[4] in NUMBER_CARDS]
    near = [(x, y) for x, y in zip(cards, cards[1:]) if y[0] - x[0] < GAP]
    if a.section:
        near = [(x, y) for x, y in near if a.section in (x[1], y[1])]
    print(f'film: {len(cards)} plain number cards (cap {CAP}), {len(near)} pairs under {GAP:.0f} s'
          + ('' if not a.section else f' touching {a.section}'))
    if len(cards) > CAP:
        (fails if not a.section else []).append(f'film: {len(cards)} plain number cards, cap {CAP}')
        if a.section:
            print(f'  (information until every section is done: {len(cards)} > {CAP})')
    for x, y in near[:15]:
        fails.append(f'number cards {y[0] - x[0]:.0f} s apart: {x[2]} "{x[3]}" ({x[1]}, {x[0]:.0f} s) and {y[2]} "{y[3]}" ({y[1]}, {y[0]:.0f} s)')

    use = {}
    for t, sec, b, p, c in film:
        use.setdefault(c, []).append(t)
    print('devices: ' + ' | '.join(f'{c} {len(ts)}' + (f' (closest {min(q - p for p, q in zip(ts, ts[1:])):.0f} s)' if len(ts) > 1 else '')
                                   for c, ts in sorted(use.items(), key=lambda kv: -len(kv[1]))[:16]))
    if fails:
        print('FAIL')
        for f in fails:
            print('  ' + f)
        sys.exit(1)
    print('PASS')


if __name__ == '__main__':
    main()
