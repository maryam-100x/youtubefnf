// kit3 · Read: someone's words, or a headline, written out big on the one card. Use it when the words themselves are the point and the
// page can't be shown sharp at a readable size; when the page can, Page is the receipt (show the thing itself).
//
// By construction:
//  - the card fits its text: every line is measured in Archivo; the size is headline (84) when the whole text is 70 characters or less and
//    every line fits, title (52) otherwise; a line that doesn't fit at title size is refused (text running past its card, gate B13)
//  - the words show whole from the card's first frame; only the lit phrases turn to the accent on their words (a word-by-word reveal
//    implies the words on the card are read one by one). `reveal` (each word's time) is the one exception: only where the voice reads
//    exactly those words at that moment
//  - a lit phrase must be on the card (else its marker sound plays on nothing: gate B6 SYNC) and the lit phrases together stay under 60%
//    of the text (highlighting almost the whole text highlights nothing)
//  - whose and where on top (label, full ink), the opening quote mark hung in the margin so the lines align on the letters
// Props: d, lines (the text as it breaks), kicker (whose · where), lit? [{text, at}], quote? (true; false for a headline), size?, reveal?,
// at? (the card's entrance; default whole from the first frame), page? (the page itself, defocused, as the ground) / ground? / img?, start?,
// dim?, blur?, credit?, source?
import React from 'react';
import {interpolateColors} from 'remotion';
import {useT} from '../lib';
import {DS, TYPE, lightP, type} from './tokens';
import {textW, useFontsReady} from './measure';
import {Card, Split, Stage} from './stage';
import {Lit} from './text';

const MAX_W = 1640, PAD: [number, number] = [44, 56];

export const Read: React.FC<{d: number; lines: string[]; kicker: string; lit?: {text: string; at: number}[]; quote?: boolean;
  size?: 'headline' | 'title'; reveal?: number[]; at?: number; page?: string; ground?: string; img?: string; start?: number; dim?: number;
  blur?: number; credit?: string; source?: string}> = ({d, lines, kicker, lit = [], quote = true, size, reveal, at, page, ground, img, start, dim,
  blur, credit, source}) => {
  const t = useT();
  const fonts = useFontsReady();
  const stage = (fg: React.ReactNode) => (
    <Stage dur={d} ground={ground} img={page ?? img} start={start} dim={dim ?? (page ? 0.4 : 0.62)} blur={blur ?? (page ? 18 : 8)} credit={credit}
      source={source}>{fg}</Stage>
  );
  if (!fonts) return stage(null);
  const text = lines.join(' ');
  for (const l of lit) {
    if (!lines.some((ln) => ln.includes(l.text))) throw new Error(`kit3 Read: the lit phrase "${l.text}" is not on the card (its marker would light nothing)`);
  }
  const litChars = lit.reduce((a, l) => a + l.text.length, 0);
  if (lit.length && litChars / Math.max(1, text.length) >= 0.6) {
    throw new Error(`kit3 Read: ${Math.round(100 * litChars / text.length)}% of the card lit: show it plain`);
  }
  const fits = (k: 'headline' | 'title') => {
    const qw = quote ? textW('“', TYPE[k].fontSize, TYPE[k].fontWeight, TYPE[k].letterSpacing) : 0;
    const widest = Math.max(...lines.map((ln, i) => textW((i === lines.length - 1 && quote ? `${ln}”` : ln), TYPE[k].fontSize, TYPE[k].fontWeight,
      TYPE[k].letterSpacing)));
    return {ok: widest + qw <= MAX_W - 2 * PAD[1], qw, widest};
  };
  const sz: 'headline' | 'title' = size ?? (text.length <= 70 && fits('headline').ok ? 'headline' : 'title');
  const f = fits(sz);
  if (!f.ok) throw new Error(`kit3 Read: a line is ${Math.round(f.widest)} px at ${sz} size, past the card's ${MAX_W - 2 * PAD[1] - Math.round(f.qw)}: break it`);
  const kw = textW(kicker, TYPE.label.fontSize, TYPE.label.fontWeight);
  if (kw + f.qw > MAX_W - 2 * PAD[1]) throw new Error(`kit3 Read: the kicker "${kicker}" is wider than the card: shorten it`);
  const qw = f.qw;
  // each word's index across the lines (for `reveal`)
  let wi = 0;
  const parts = (ln: string): React.ReactNode[] => {
    const out: React.ReactNode[] = [];
    const words = (s: string, key: string, litAt?: number) => s.split(/(\s+)/).filter((x) => x.length).map((w, j) => {
      if (/^\s+$/.test(w)) return <span key={`${key}s${j}`}>{w}</span>;
      const at = reveal ? reveal[wi++] : undefined;
      const u = at === undefined ? 1 : lightP(t, at);
      const c = interpolateColors(u, [0, 1], [DS.INK3, DS.INK]);
      return litAt === undefined ? <span key={`${key}w${j}`} style={{color: c}}>{w}</span>
        : <Lit key={`${key}w${j}`} at={litAt} base={c}>{w}</Lit>;
    });
    let rest = ln, k = 0;
    for (;;) {
      const hits = lit.map((l) => ({l, i: rest.indexOf(l.text)})).filter((h) => h.i >= 0).sort((x, y) => x.i - y.i);
      if (!hits.length) break;
      const {l, i} = hits[0];
      if (i > 0) out.push(...words(rest.slice(0, i), `a${k++}`));
      out.push(...words(l.text, `l${k++}`, l.at));
      rest = rest.slice(i + l.text.length);
    }
    if (rest) out.push(...words(rest, `r${k++}`));
    return out;
  };
  return stage(
    <Split column>
      <Card pad={PAD} at={at} style={{width: 'auto', maxWidth: MAX_W}}>
        <div style={{...type('label'), marginBottom: DS.S.m, paddingLeft: qw, whiteSpace: 'nowrap'}}>{kicker}</div>
        <div style={{...type(sz), paddingLeft: qw}}>
          {lines.map((ln, i) => (
            <div key={i} style={{whiteSpace: 'nowrap', textIndent: i === 0 ? -qw : 0}}>
              {i === 0 && quote ? '“' : ''}{parts(ln)}{i === lines.length - 1 && quote ? '”' : ''}
            </div>
          ))}
        </div>
      </Card>
    </Split>,
  );
};
