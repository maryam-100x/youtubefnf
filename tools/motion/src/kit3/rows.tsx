// kit3 · rows of things, people or logos, placed by what you SEE (a row placed by file boxes sits off centre, with unequal gaps, a
// figure cut by the frame, a long name running past a narrow product). The math is layout.rowLayout (unit-tested).
//
//   Row        items [{src, name?, at?, k?, litAt?, dimAt?}], h (the visible figures' height), mode:
//                'floor'  things standing on one floor line, a soft pool under each, the name under each (title size)
//                'bleed'  people cut at the legs: their cut 40 px under the frame's foot, the name on a chip 160 px above the foot
//                'centre' logos: their visible centres on one line (y), no floor, no names by default
//              By construction: each figure's width from its own VISIBLE pixels (alpha > 16, measured at up to 2048 px); the same gap between
//              every pair of visible figures, widened (for all, so they stay equal) until the names under them keep 24 px apart; the whole
//              visible content (figures AND names) centred on `cx`; a row wider than `maxW` (1680) shrinks as a whole and refuses when it
//              can't fit; the floor recomputed from the shrunk heights (an unshrunk floor sits the row low). Items land at their final
//              places from the first frame (no shuffling as they arrive); `recentre` lets the row glide aside as items arrive.
//              Names mark themselves data-gate="name" (gate B14 reads them with the figures); the row data-kit3="row" carries its gaps.
//              Props: items, h, mode?, gap? (64), cx? (960), y? (centre line for 'centre'), floor?, maxW? (1680), itemMaxW?, recentre?, pools?
//   LogosLand  real logos landing one by one on their words, centred and evenly gapped by their visible pixels (Row 'centre'); a wide logo
//              is capped at `itemMaxW` (640) so it doesn't outweigh the others (~280 px tall, or 640 wide when wide).
//              A row of ONE (a lone logo, one cut-out) is centred to the eye, left to right halfway between its visible box and its centre
//              of mass (a logo whose weight sits off its box's middle looks off centre box-centred); the gate's LOGO_OFF_CENTRE measures it.
import React from 'react';
import {AbsoluteFill, Img, interpolate, interpolateColors} from 'remotion';
import {clamp, useT} from '../lib';
import {EASE} from '../house/motion';
import {DS, TYPE, enterP, enterStyle, lightP, moveP, type} from './tokens';
import {rowLayout} from './layout';
import {textW, url, useFontsReady, useImgBoxes} from './measure';
import {Stage} from './stage';
import {Tag} from './text';

export type RowItem = {src: string; name?: string; at?: number; k?: number; litAt?: number; dimAt?: number};
const NAME_GAP = 28;                                                           // floor line to the name's top
const NAME_H = Math.round(TYPE.title.fontSize * TYPE.title.lineHeight);

export const Row: React.FC<{items: RowItem[]; h: number; mode?: 'floor' | 'bleed' | 'centre'; gap?: number; cx?: number; y?: number;
  floor?: number; maxW?: number; itemMaxW?: number; recentre?: boolean; pools?: boolean}> = ({items, h, mode = 'floor', gap = DS.S.xl,
  cx = DS.CX, y = DS.CY, floor, maxW = DS.W - 2 * DS.MX, itemMaxW, recentre = false, pools = true}) => {
  const t = useT();
  const fonts = useFontsReady();
  const boxes = useImgBoxes(items.map((i) => i.src));
  if (!boxes || !fonts) return null;
  // a name's width on screen: the chip's (bleed: text + 44 px of padding) or the title line's
  const nameW = items.map((it) => (!it.name ? 0 : textW(it.name, TYPE.title.fontSize, TYPE.title.fontWeight) + (mode === 'bleed' ? 44 : 0)));
  // each figure's visible size, and where its weight sits from its box's middle (a lone figure is centred to the eye: layout.rowLayout)
  const vis = boxes.map((b) => ({vw: b.x1 - b.x0, vh: b.y1 - b.y0, wdx: b.wx - (b.x0 + b.x1) / 2}));
  const lay = (set: boolean[]) => rowLayout(items.map((it, i) => ({...vis[i], nameW: set[i] ? nameW[i] : 0, k: it.k, maxW: itemMaxW}))
    .filter((_, i) => set[i]), {h, gap, cx, maxW});
  const all = items.map(() => true);
  const fin = lay(all);
  // the heights after any shrink: the floor centres figures + names on the centre line (or as given)
  const hMax = Math.max(...fin.height);
  const named = items.some((i) => i.name);
  const base = mode === 'bleed' ? DS.H + 40 : mode === 'centre' ? y : floor ?? Math.round(DS.CY + (hMax - (named ? NAME_GAP + NAME_H : 0)) / 2);
  // x of each visible figure's left edge now: its final place, or (recentre) its place among the items that have arrived, eased
  const times = Array.from(new Set(items.map((i) => i.at ?? -1e9))).sort((a, b) => a - b);
  const placeAt = (k: number) => {
    const set = items.map((i) => (i.at ?? -1e9) <= times[k]);
    const r = lay(set);
    const out: number[] = [];
    let j = 0;
    set.forEach((on) => out.push(on ? r.left[j++] : NaN));
    return out;
  };
  const places = recentre ? times.map((_, k) => placeAt(k)) : [];
  const xAt = (i: number) => {
    if (!recentre) return fin.left[i];
    const a = times.indexOf(items[i].at ?? -1e9);
    let L = places[a][i];
    for (let k = a + 1; k < times.length; k++) L += (places[k][i] - places[k - 1][i]) * moveP(t, times[k] - DS.DUR.lead, 0.6);
    return L;
  };
  return (
    <AbsoluteFill data-kit3="row" data-kit3-gap={fin.gap.toFixed(1)}>
      {mode === 'floor' && pools ? items.map((it, i) => {
        const W = fin.width[i];
        const u = enterP(t, it.at);
        return <div key={`p${i}`} style={{position: 'absolute', left: xAt(i) - W * 0.1, width: W * 1.2, top: base - 30, height: 64,
          opacity: Math.min(1, u / 0.6), background: 'radial-gradient(closest-side, rgba(0,0,0,0.78), rgba(0,0,0,0.35) 55%, rgba(0,0,0,0))'}} />;
      }) : null}
      {items.map((it, i) => {
        const b = boxes[i], s = fin.scale[i];
        const u = enterP(t, it.at);
        const dim = it.dimAt === undefined ? 0 : interpolate(t, [it.dimAt, it.dimAt + 0.3], [0, 1], {...clamp, easing: EASE.move});
        const top = mode === 'centre' ? base - fin.height[i] / 2 - b.y0 * s : base - b.y1 * s;
        return (
          <Img key={`i${i}`} src={url(it.src)} style={{position: 'absolute', left: xAt(i) - b.x0 * s, top, width: b.iw * s, height: b.ih * s,
            maxWidth: 'none', opacity: Math.min(1, u / 0.6) * (1 - 0.55 * dim), transform: `translateY(${DS.RISE.cut * (1 - u)}px)`,
            filter: `${DS.CUT_SHADOW}${dim ? ` saturate(${1 - 0.7 * dim})` : ''}`}} />
        );
      })}
      {items.map((it, i) => {
        if (!it.name) return null;
        const W = fin.width[i];
        const u = enterP(t, it.at === undefined ? undefined : it.at + DS.DUR.stagger, DS.DUR.text);
        const lit = it.litAt === undefined ? 0 : lightP(t, it.litAt);
        const dim = it.dimAt === undefined ? 0 : interpolate(t, [it.dimAt, it.dimAt + 0.3], [0, 1], clamp);
        const op = Math.min(1, u / 0.6) * (1 - 0.6 * dim);
        const L = xAt(i) + W / 2 - nameW[i] / 2;
        return mode === 'bleed' ? (
          <div key={`n${i}`} style={{position: 'absolute', left: L, width: nameW[i], bottom: 160, ...enterStyle(u, 20), opacity: op}}>
            <Tag lit={lit}>{it.name}</Tag>
          </div>
        ) : (
          <div key={`n${i}`} data-gate="name" style={{position: 'absolute', left: L, width: nameW[i], top: mode === 'centre' ? base + hMax / 2 + DS.S.m : base + NAME_GAP,
            whiteSpace: 'nowrap', ...type('title', interpolateColors(lit, [0, 1], [DS.INK, DS.ACCENT])), ...enterStyle(u, 20), opacity: op}}>{it.name}</div>
        );
      })}
    </AbsoluteFill>
  );
};

export const LogosLand: React.FC<{d: number; items: {src: string; at: number; name?: string}[]; h?: number; itemMaxW?: number; ground?: string;
  img?: string; start?: number; dim?: number; credit?: string; source?: string}> = ({d, items, h = 280, itemMaxW = 640, ground, img, start, dim = 0.6,
  credit, source}) => (
  <Stage dur={d} ground={ground} img={img} start={start} dim={dim} credit={credit} source={source}>
    <Row mode="centre" h={h} itemMaxW={itemMaxW} gap={DS.S.xxl} items={items} />
  </Stage>
);
