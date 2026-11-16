// kit3 · Timeline: dates on one line at their TRUE distances (three dates over 61 days, 45 then 16 apart, sit 45 and 16 parts apart),
// each landing on its words with what it was; `span` lights the stretch the words name (a line that marks something).
// By construction (layout.timelineLayout, unit-tested): each label measured in Archivo, centred under its dot; a label that would touch
// the one before it goes above the line instead; one that touches on both sides is refused (the dates are too close for words: show
// fewer); the first and last labels stay inside the content box (the dots keep their true places), so no two labels run into each
// other (gate B13).
// Props: d, kicker, marks [{date, what, day, at}] (day = days from the first), span? [fromDay, toDay], spanText?, spanAt?, ground?, img?,
// start?, credit?, source?
import React from 'react';
import {useT} from '../lib';
import {DS, TYPE, enterP, enterStyle, lightP, type} from './tokens';
import {INK_RGB} from '../brand';
import {timelineLayout} from './layout';
import {textW, useFontsReady} from './measure';
import {Stage} from './stage';

export const Timeline: React.FC<{d: number; kicker: string; marks: {date: string; what: string; day: number; at: number}[]; span?: [number, number];
  spanText?: string; spanAt?: number; ground?: string; img?: string; start?: number; credit?: string; source?: string}> = ({d, kicker, marks, span,
  spanText, spanAt, ground, img, start, credit, source}) => {
  const t = useT();
  const fonts = useFontsReady();
  const stage = (fg: React.ReactNode) => <Stage dur={d} ground={ground} img={img} start={start} dim={0.62} credit={credit} source={source}>{fg}</Stage>;
  if (!fonts) return stage(null);
  const L = 300, R = DS.W - 300, Y = DS.CY + 20;
  const widths = marks.map((m) => Math.max(textW(m.date, TYPE.headline.fontSize, TYPE.headline.fontWeight, TYPE.headline.letterSpacing),
    textW(m.what, TYPE.label.fontSize, TYPE.label.fontWeight)));
  const lay = timelineLayout(marks.map((m) => m.day), widths, L, R, DS.MX, DS.W - DS.MX);
  const d0 = Math.min(...marks.map((m) => m.day)), d1 = Math.max(...marks.map((m) => m.day));
  const x = (day: number) => L + ((R - L) * (day - d0)) / Math.max(1, d1 - d0);
  const lit = spanAt === undefined ? 0 : lightP(t, spanAt);
  const blockH = Math.round(TYPE.headline.fontSize * TYPE.headline.lineHeight) + DS.S.xs + Math.round(TYPE.label.fontSize * TYPE.label.lineHeight);
  return stage(
    <>
      <div style={{position: 'absolute', left: 0, right: 0, top: DS.TOP, textAlign: 'center', ...type('label')}}>{kicker}</div>
      <div style={{position: 'absolute', left: L, width: R - L, top: Y - 3, height: 6, borderRadius: 3, background: `rgba(${INK_RGB},0.35)`}} />
      {span ? (
        <div style={{position: 'absolute', left: x(span[0]), width: (x(span[1]) - x(span[0])) * lit, top: Y - 5, height: 10, borderRadius: 5,
          background: DS.ACCENT}} />
      ) : null}
      {span && spanText ? (
        <div style={{position: 'absolute', left: x(span[0]), width: x(span[1]) - x(span[0]), top: Y + DS.S.l + blockH + DS.S.m, textAlign: 'center',
          whiteSpace: 'nowrap', ...type('title', DS.ACCENT), ...enterStyle(lit, 16)}}>{spanText}</div>
      ) : null}
      {marks.map((m, i) => {
        const u = enterP(t, m.at);
        const p = lay[i];
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left: p.x - 14, top: Y - 14, width: 28, height: 28, borderRadius: 14, background: DS.INK,
              boxShadow: '0 4px 14px rgba(0,0,0,0.5)', opacity: Math.min(1, u / 0.6)}} />
            <div style={{position: 'absolute', left: p.left, width: widths[i] + 2, textAlign: 'center', whiteSpace: 'nowrap',
              top: p.side === 'below' ? Y + DS.S.l : Y - DS.S.l - blockH, ...enterStyle(u, p.side === 'below' ? 24 : -24)}}>
              <div style={type('headline')}>{m.date}</div>
              <div style={{...type('label'), marginTop: DS.S.xs}}>{m.what}</div>
            </div>
          </React.Fragment>
        );
      })}
    </>,
  );
};
