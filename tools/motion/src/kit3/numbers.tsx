// kit3 · numbers that show the thing itself (a number about a thing shows that thing, never a card about it).
//
// Which piece for a number (KIT3.md has the full rule):
//  1. the number is ON a real thing (a video page's view count, a chart, a store page, a post): Page with a mark on the number, and the
//     people or the thing `beside` it. That IS the number piece; no card.
//  2. the number has no page but its subject has a picture: NumberBeside (the picture and the rolling number side by side).
//  3. the number has no picture of its own at all: NumberBeside with `noPicture` saying why (a reviewer reads the reason in the code).
// A number centred alone on a card over blurred footage cannot be built: NumberBeside needs `picture` or `noPicture`.
//
//   Odometer      digits rolling in their slots (each higher digit turning as the one below passes 9 -> 0), never a digit swap (a swap
//                 reads stiff); slots marked data-gate="roll". Props: value (now), max, decimals?, group?, lh?, weight?
//   BigNumber     the number in display size and the accent, its unit beside it on one baseline, its subject under it (unit and subject
//                 required: a number without them is an unreadable ring of digits). Props: value, at, unit, subject, from?, roll?,
//                 decimals?, prefix?, suffix?, kicker?, size?, w?, align?, enterAt?
//   NumberBeside  a picture (a photo whole or a cut-out by its visible pixels) and the BigNumber in one centred group over a live ground;
//                 the column exactly as wide as its widest line (so the group centres by real widths), entering on the roll (never "0
//                 million" waiting on screen). Props: d, value, at, unit, subject, picture | noPicture, pictureH?, pictureAt?, kicker?, line?
//                 ([plain, lit]: a second line, its last part lit on lineAt), fixed? (lands whole), decimals?, prefix?, suffix?, ground?, img?,
//                 start?, credit?, source?
import {useT} from '../lib';
import {DS, TYPE, enterP, enterStyle, moveP, type} from './tokens';
import {textW, useFontsReady} from './measure';
import {Enter, Split, Stage} from './stage';
import {Lit} from './text';
import {Picture} from './pictures';

export const Odometer: React.FC<{value: number; max: number; decimals?: number; group?: boolean; lh?: number; weight?: number}> = ({value,
  max, decimals = 0, group = true, lh = TYPE.display.lineHeight, weight = TYPE.display.fontWeight}) => {
  const fonts = useFontsReady();
  const scale = Math.pow(10, decimals);
  const n = Math.max(0, value * scale);
  const N = Math.max(1, Math.round(Math.max(max, value) * scale));
  const D = Math.max(String(N).length, decimals + 1);
  const dw = fonts ? Math.max(...'0123456789'.split('').map((c) => textW(c, 100, weight))) / 100 : 0.62;
  const cw = fonts ? textW(',', 100, weight) / 100 : 0.24;
  const pw = fonts ? textW('.', 100, weight) / 100 : 0.24;
  const out: React.ReactNode[] = [];
  for (let k = D - 1; k >= 0; k--) {
    const p10 = Math.pow(10, k);
    const below = n - Math.floor(n / p10) * p10;
    const pos = Math.floor(n / p10) + Math.min(1, Math.max(0, below - (p10 - 1)));
    const vis = k <= decimals ? 1 : Math.min(1, Math.max(0, (n - p10 * 0.9) / (p10 * 0.1)));
    if (vis <= 0.001) continue;
    const ph = ((pos % 10) + 10) % 10;
    out.push(
      <span key={`d${k}`} data-gate="roll" style={{display: 'inline-block', position: 'relative', width: `${dw * vis}em`, height: `${lh}em`,
        overflow: 'hidden', opacity: vis, verticalAlign: 'top', flex: 'none'}}>
        <span style={{position: 'absolute', left: 0, top: 0, width: `${dw}em`, letterSpacing: 0, transform: `translateY(${-ph * lh}em)`}}>
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map((dg, i) => (
            <span key={i} style={{display: 'block', height: `${lh}em`, lineHeight: `${lh}em`, textAlign: 'center'}}>{dg}</span>
          ))}
        </span>
      </span>,
    );
    if (decimals > 0 && k === decimals) {
      out.push(<span key="pt" style={{display: 'inline-block', width: `${pw}em`, height: `${lh}em`, lineHeight: `${lh}em`, flex: 'none'}}>.</span>);
    }
    const ki = k - decimals;
    if (group && ki > 0 && ki % 3 === 0) {
      out.push(<span key={`c${k}`} style={{display: 'inline-block', width: `${cw * vis}em`, height: `${lh}em`, lineHeight: `${lh}em`, overflow: 'hidden',
        opacity: vis, verticalAlign: 'top', flex: 'none'}}>,</span>);
    }
  }
  return <span style={{display: 'inline-flex', whiteSpace: 'nowrap'}}>{out}</span>;
};

export const BigNumber: React.FC<{value: number; at: number; unit: string; subject: string; from?: number; roll?: number; decimals?: number;
  prefix?: string; suffix?: string; kicker?: string; size?: number; group?: boolean; w?: number; align?: 'left' | 'center'; enterAt?: number}> = ({
  value, at, unit, subject, from = 0, roll = DS.DUR.roll, decimals = 0, prefix = '', suffix = '', kicker, size = TYPE.display.fontSize,
  group = true, w = 820, align = 'left', enterAt}) => {
  const t = useT();
  if (!unit.trim() || !subject.trim()) throw new Error(`kit3 BigNumber ${value}: a number needs its unit and its subject (what it counts, of what)`);
  const v = from + (value - from) * moveP(t, at, roll);
  const u = enterP(t, enterAt ?? Math.min(at, 0));
  const lh = TYPE.display.lineHeight;
  const lift = Math.max(0, 0.126 * size - 0.166 * TYPE.headline.fontSize);   // the unit's baseline on the digits' baseline
  return (
    <div style={{width: w, textAlign: align, flex: 'none', ...enterStyle(u)}}>
      {kicker ? <div style={{...type('label', DS.INK2), marginBottom: DS.S.s}}>{kicker}</div> : null}
      <div style={{display: 'flex', alignItems: 'flex-end', justifyContent: align === 'center' ? 'center' : 'flex-start', whiteSpace: 'nowrap'}}>
        <div style={{...type('display', DS.ACCENT), fontSize: size, display: 'flex', alignItems: 'flex-end'}}>
          {prefix ? <span style={{display: 'inline-block', height: `${lh}em`, lineHeight: `${lh}em`}}>{prefix}</span> : null}
          <Odometer value={v} max={Math.max(value, from)} decimals={decimals} group={group} lh={lh} />
          {suffix ? <span style={{display: 'inline-block', height: `${lh}em`, lineHeight: `${lh}em`}}>{suffix}</span> : null}
        </div>
        <div style={{...type('headline'), marginLeft: DS.S.m, marginBottom: lift}}>{unit}</div>
      </div>
      <div style={{...type('title'), marginTop: DS.S.m}}>{subject}</div>
    </div>
  );
};

type Beside = {picture: string; noPicture?: never} | {picture?: never; noPicture: string};
export const NumberBeside: React.FC<Beside & {d: number; value: number; at: number; unit: string; subject: string; pictureH?: number;
  pictureAt?: number; pictureCaption?: string; kicker?: string; line?: [string, string]; lineAt?: number; fixed?: boolean; decimals?: number;
  prefix?: string; suffix?: string; roll?: number; size?: number; ground?: string; img?: string; start?: number; dim?: number; credit?: string;
  source?: string}> = ({d, value, at, unit, subject, picture, noPicture, pictureH = 620, pictureAt = 0, pictureCaption, kicker, line, lineAt,
  fixed, decimals, prefix, suffix, roll, size, ground, img, start, dim = 0.62, credit, source}) => {
  const fonts = useFontsReady();
  if (!picture && !(noPicture && noPicture.trim().length >= 8)) {
    throw new Error(`kit3 NumberBeside ${value} ${unit}: give the picture of what it counts, or noPicture="why none exists" (show the thing itself)`);
  }
  if (!fonts) return <Stage dur={d} ground={ground} img={img} start={start} dim={dim} credit={credit} source={source} />;
  const enter = Math.max(0, at - (fixed ? 0.06 : 0.08));
  const sz = size ?? TYPE.display.fontSize;
  const dw = Math.max(...'0123456789'.split('').map((c) => textW(c, 100, TYPE.display.fontWeight))) / 100;
  const digits = value.toFixed(decimals ?? 0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const row = textW((prefix ?? '') + (suffix ?? ''), sz, TYPE.display.fontWeight) + digits.length * dw * sz + DS.S.m
    + textW(unit, TYPE.headline.fontSize, TYPE.headline.fontWeight, TYPE.headline.letterSpacing);
  const sub = textW(subject, TYPE.title.fontSize, TYPE.title.fontWeight);
  const l2 = line ? textW(line.join(''), TYPE.title.fontSize, TYPE.title.fontWeight) : 0;
  const kk = kicker ? textW(kicker, TYPE.label.fontSize, TYPE.label.fontWeight) : 0;
  const col = Math.ceil(Math.max(row, sub, l2, kk)) + 4;
  if (col > (picture ? 1000 : 1600)) {
    throw new Error(`kit3 NumberBeside: its widest line is ${col} px (over ${picture ? 1000 : 1600}): a shorter subject or kicker`);
  }
  return (
    <Stage dur={d} ground={ground} img={img} start={start} dim={dim} credit={credit} source={source}>
      <Split>
        {picture ? <Picture src={picture} h={pictureH} at={pictureAt} caption={pictureCaption} /> : null}
        <div style={{width: col, flex: 'none'}}>
          {kicker ? <Enter at={enter}><div style={{...type('label'), marginBottom: DS.S.s}}>{kicker}</div></Enter> : null}
          <BigNumber value={value} from={fixed ? value : 0} at={at} roll={roll} unit={unit} subject={subject} prefix={prefix} suffix={suffix}
            decimals={decimals} enterAt={enter} w={col} size={size} />
          {line ? (
            <div style={{marginTop: DS.S.l}}>
              <Enter at={lineAt}><div style={{...type('title'), whiteSpace: 'nowrap'}}>{line[0]}<Lit at={lineAt}>{line[1]}</Lit></div></Enter>
            </div>
          ) : null}
        </div>
      </Split>
    </Stage>
  );
};
