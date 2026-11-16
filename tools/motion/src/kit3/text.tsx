// kit3 · text in the type scale, each kind in its one place (text sits where its kind always sits, never where it merely fits).
//
//   Kicker / Headline / Label / TextBlock   text blocks landing on their words (sentence case, no tracked caps)
//   Lit     words of a sentence turning to the accent on `at` (the words the voice names)
//   Tag     a name on a chip; `lit` 0..1 turns it to the accent. A name is NOT a mark: it may sit on a playing clip. The chip marks
//           itself data-gate="name" (the gate's B4 lets names sit on pictures; B14 reads them as a row's name lines)
//   Stamp   a passage's headline claim over footage on its word: straight, centred on y 532, fitted to 1600 px (never past the content box
//           with the push), lead in the accent, lands in 0.16 s from 1.15x as the footage dims to 50% (data-gate="stamp"; its words out
//           of the captions there: text shows once)
//   TypedLine  a date typing itself in the opening's place (top centre, y 178, display size), its keys pulled in so it is whole 0.3 s
//           before the cut by construction (fitKeys), its size brought down so the longest line fits 1600 px. Props: lines, keys, d (the
//           shot's length), y?, size?
import React from 'react';
import {AbsoluteFill, interpolate, interpolateColors} from 'remotion';
import {clamp, useT} from '../lib';
import {EASE} from '../house/motion';
import {DS, TYPE, enterP, enterStyle, lightP, type} from './tokens';
import {textW, useFontsReady} from './measure';
import {fitKeys} from './layout';

export const Lit: React.FC<{at?: number; children: React.ReactNode; base?: string}> = ({at, children, base = DS.INK}) => {
  const t = useT();
  const u = at === undefined ? 1 : lightP(t, at);
  return <span style={{color: interpolateColors(u, [0, 1], [base, DS.ACCENT])}}>{children}</span>;
};
export const Kicker: React.FC<{children: React.ReactNode; at?: number; tone?: 'ink' | 'muted'}> = ({children, at, tone = 'muted'}) => {
  const t = useT();
  return <div style={{...type('label', tone === 'ink' ? DS.INK : DS.INK2), ...enterStyle(enterP(t, at, DS.DUR.text))}}>{children}</div>;
};
export const Headline: React.FC<{children: React.ReactNode; at?: number; size?: 'display' | 'headline' | 'title'; color?: string;
  w?: number; align?: 'left' | 'center'}> = ({children, at, size = 'headline', color, w, align = 'left'}) => {
  const t = useT();
  return <div style={{...type(size, color), maxWidth: w, textAlign: align, ...enterStyle(enterP(t, at, DS.DUR.text))}}>{children}</div>;
};
export const Label: React.FC<{children: React.ReactNode; at?: number; tone?: 'ink' | 'muted' | 'accent'; weight?: number;
  w?: number; align?: 'left' | 'center'}> = ({children, at, tone = 'ink', weight, w, align = 'left'}) => {
  const t = useT();
  const c = tone === 'muted' ? DS.INK2 : tone === 'accent' ? DS.ACCENT : DS.INK;
  return <div style={{...type('label', c, weight), maxWidth: w, textAlign: align, ...enterStyle(enterP(t, at, DS.DUR.text))}}>{children}</div>;
};
export const TextBlock: React.FC<{kicker?: string; title: React.ReactNode; sub?: React.ReactNode; size?: 'display' | 'headline' | 'title';
  at?: number; w?: number; align?: 'left' | 'center'}> = ({kicker, title, sub, size = 'headline', at, w = 820, align = 'left'}) => {
  const st = (i: number) => (at === undefined ? undefined : at + i * DS.DUR.stagger);
  return (
    <div style={{width: w, textAlign: align, flex: 'none'}}>
      {kicker ? <div style={{marginBottom: DS.S.s}}><Kicker at={st(0)}>{kicker}</Kicker></div> : null}
      <Headline at={st(1)} size={size} align={align}>{title}</Headline>
      {sub ? <div style={{marginTop: DS.S.m}}><Label at={st(2)} tone="muted" align={align}>{sub}</Label></div> : null}
    </div>
  );
};

export const Tag: React.FC<{children: React.ReactNode; lit?: number; size?: 'title' | 'label'}> = ({children, lit = 0, size = 'title'}) => (
  <div data-gate="name" style={{display: 'inline-block', padding: size === 'title' ? '8px 22px 10px' : '6px 18px 8px', borderRadius: DS.R_CHIP,
    whiteSpace: 'nowrap', background: interpolateColors(lit, [0, 1], [DS.CHIP, DS.ACCENT]), boxShadow: '0 10px 28px rgba(0,0,0,0.45)',
    ...type(size, interpolateColors(lit, [0, 1], [DS.INK, DS.ON_ACCENT]))}}>{children}</div>
);

export const Stamp: React.FC<{at: number; text: string; lead?: string; y?: number; max?: number; dim?: number}> = ({at, text, lead,
  y = DS.CY, max = TYPE.display.fontSize, dim = 0.5}) => {
  const t = useT();
  const fonts = useFontsReady();
  if (t < at || !fonts) return null;
  const u = interpolate(t, [at, at + DS.DUR.stamp], [0, 1], {...clamp, easing: EASE.enter});
  const op = interpolate(t, [at, at + 0.05], [0, 1], clamp);
  const W = DS.W - 2 * DS.MX - 80;
  const fit = (s: string) => (W / textW(s, 100, TYPE.display.fontWeight, TYPE.display.letterSpacing)) * 100;
  const full = lead ? `${lead} ${text}` : text;
  const one = Math.min(max, fit(full));
  const two = !!lead && one < 112;
  const size = two ? Math.min(max, fit(lead as string), fit(text)) : one;
  const st: React.CSSProperties = {...type('display'), fontSize: size, whiteSpace: 'nowrap', textShadow: '0 4px 28px rgba(0,0,0,0.45)'};
  return (
    <AbsoluteFill data-gate="stamp" style={{pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: `rgba(0,0,0,${dim * u})`}} />
      <div style={{position: 'absolute', left: DS.MX, right: DS.MX, top: y, transform: `translateY(-50%) scale(${1.15 - 0.15 * u})`,
        transformOrigin: '50% 50%', opacity: op, textAlign: 'center'}}>
        {two ? (
          <>
            <div style={{...st, color: DS.ACCENT}}>{lead}</div>
            <div style={st}>{text}</div>
          </>
        ) : (
          <div style={st}>{lead ? <span style={{color: DS.ACCENT}}>{lead} </span> : null}{text}</div>
        )}
      </div>
    </AbsoluteFill>
  );
};

export const TypedLine: React.FC<{lines: string[]; keys: number[]; d: number; y?: number; size?: number}> = ({lines, keys: keys0, d,
  y = 178, size = TYPE.display.fontSize}) => {
  const t = useT();
  const fonts = useFontsReady();
  const keys = fitKeys(keys0, d);
  const n = keys.filter((k) => t >= k).length;
  if (n === 0 || !fonts) return null;
  // never past the content box: the size comes down to fit the longest line in 1600 px (with the cursor and the push)
  size = Math.min(size, ...lines.map((ln) => (1600 / Math.max(1, textW(ln, 100, TYPE.display.fontWeight, TYPE.display.letterSpacing))) * 100));
  const end = keys[keys.length - 1];
  const blink = t < end + 0.15 || Math.floor((t - end) * 2.2) % 2 === 0;
  const st: React.CSSProperties = {...type('display'), fontSize: size, whiteSpace: 'pre', textShadow: '0 4px 28px rgba(0,0,0,0.45)'};
  const starts = lines.map((_, i) => lines.slice(0, i).reduce((a, l) => a + l.length, 0));
  const cur = Math.max(0, starts.filter((s0) => s0 < n).length - 1);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div data-gate="stamp" style={{position: 'absolute', left: DS.MX, right: DS.MX, top: y, transform: 'translateY(-50%)', textAlign: 'center'}}>
        {lines.map((ln, i) => {
          const shown = Math.max(0, Math.min(ln.length, n - starts[i]));
          return (
            <div key={i} style={st}>
              {ln.slice(0, shown)}
              {i === cur && shown > 0 ? (
                <span style={{display: 'inline-block', width: size * 0.07, height: size * 0.78, marginLeft: size * 0.04, marginRight: -size * 0.11,
                  verticalAlign: '-0.04em', background: DS.INK, opacity: blink ? 1 : 0}} />
              ) : null}
              <span style={{opacity: 0}}>{ln.slice(shown)}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
