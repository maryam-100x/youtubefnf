// kit3 · Page: the receipt itself (show the thing itself; the picture under a mark stands still; a mark only where there is a choice;
// marks from the words' own boxes; never almost the whole text lit). ONE component for the real page, post, video page or store page,
// SHARP, framed whole on the stage (radius 12, the card's shadow), the part that matters (`crop`, the capture's own px) as big as the
// content box allows and never over `maxScale` x its pixels, the said words marked on their words.
//
// What it does by construction (each is a fault a hand-built page card makes):
//  - every mark hugs the INK it marks: the given box (a page capture's DOM word box, up to 26 px of blank above the words) is snapped to
//    the words' own ink in the browser (layout.inkSnap), then padded 8 px on every side on whole pixels, the border inside (border-box);
//    boxed by hand, nearly half of all marks needed re-boxing for exactly this
//  - a mark that marks nothing, that comes too late (its light inside the shot's last 0.6 s) or that the crop makes pointless (it holds
//    60% of the crop's ink, or covers 45% of the crop: a name alone in its crop, a tile boxed in a tile crop, a page's one title line) is
//    REFUSED: the component throws, so the still, the gate's probe and the render all fail with the reason
//  - the crop grows to hold every padded mark whole (the page's own paper colour past the capture's edge): no border cut by the card
//  - the page stands still from its first light to the cut (the foreground push holds; the blurred ground keeps its own push)
//  - light or dark is measured (the crop's paper colour), not guessed: a wash on a light page, a box on a dark one
//  - the rest of the page dims a little while a part is lit, each mark's hole opening with its own light (marks.Veil)
//  - several pages stack (one scale for all, centred as a group), each with its label; `beside` puts the thing itself next to its receipt
//    (the people or the thing beside the page that proves the number)
//
// Props: d (the shot's length, s), src + crop? (one page) or pages [{src, crop?, label?, dark?, outline?}], marks [{box, at, page?, snap?}]
// (box in the capture's px; at in the shot's seconds; snap 'ink' (default) or 'box' for a thing that is not text: a tile, a logo),
// maxScale? (1.3), kicker? (the one page's label over it: whose and where), beside? {src, h?, caption?, sub?}, ground? (clip) / img? /
// start?, credit?, source?, push? ([1, 1.03]), dimRest? (true), look? ('spot': marks.tsx's spot look: the rest of the page dims round the
// lit words), dark? / outline? (one page: override the measured look; `outline` = the box look on a light page, for a coloured thing a
// wash would recolour: a red review score).
// The cue sheet gives each mark its marker sound from its `at` (every highlight has its marker sound).
import React from 'react';
import {Easing, Img, interpolate} from 'remotion';
import {clamp, useT} from '../lib';
import {DS, TYPE, lightP, markStart, type} from './tokens';
import {Box, expandCrop, markRect, markVerdict} from './layout';
import {url, useImgBoxes, usePagesInk} from './measure';
import {Stage} from './stage';
import {MarkBox, SpotDim, SpotGate, SpotInk, Veil, refuse} from './marks';
import {Picture} from './pictures';

export type PageMark = {box: Box; at: number; page?: number; snap?: 'ink' | 'box'};
export type PageSpec = {src: string; crop?: Box; label?: string; dark?: boolean; outline?: boolean};

const MARGIN = 8;          // film px between a padded mark and its card's edge, at least
const GAP = DS.S.l;        // between stacked pages
const LABEL_H = Math.round(TYPE.label.fontSize * TYPE.label.lineHeight) + DS.S.s;

export const Page: React.FC<{d: number; src?: string; crop?: Box; pages?: PageSpec[]; marks?: PageMark[]; maxScale?: number; kicker?: string;
  dark?: boolean; outline?: boolean; beside?: {src: string; h?: number; caption?: string; sub?: string}; ground?: string; img?: string;
  start?: number; dim?: number; blur?: number; credit?: string; source?: string; push?: [number, number]; dimRest?: boolean;
  look?: 'auto' | 'spot'}> = ({d, src, crop, pages: pages0, marks = [], maxScale = 1.3, kicker, dark, outline, beside, ground, img, start,
  dim = 0.4, blur, credit, source, push = DS.PUSH, dimRest = true, look: markLook = 'auto'}) => {
  const t = useT();
  const pages: PageSpec[] = pages0 ?? [{src: src as string, crop, label: kicker, dark, outline}];
  if (!pages.length || !pages[0].src) throw new Error('kit3 Page: no page (give src or pages)');
  const per = pages.map((_, i) => marks.filter((m) => (m.page ?? 0) === i));
  const ink = usePagesInk(pages.map((p, i) => ({src: p.src, crop: p.crop, boxes: per[i].map((m) => m.box), snap: per[i].map((m) => m.snap !== 'box')})));
  const side = useImgBoxes(beside ? [beside.src] : []);
  const hold = marks.length ? markStart(Math.min(...marks.map((m) => m.at))) : undefined;
  // the ground mounts at once (never behind a measurement: the black-frames race)
  const groundImg = ground ? undefined : img ?? pages[0].src;
  const stage = (fg: React.ReactNode) => (
    <Stage dur={d} ground={ground} start={start} img={groundImg} dim={dim} blur={blur ?? (ground ? DS.GROUND.blur : 20)} push={push} hold={hold}
      credit={credit} source={source}>{fg}</Stage>
  );
  if (!ink || !side) return stage(null);

  // the guards: refused before anything is drawn
  pages.forEach((p, i) => {
    const pi = ink[i];
    const c0 = p.crop ?? [0, 0, pi.iw, pi.ih];
    refuse(`Page ${p.src}`, markVerdict(d, c0[2] * c0[3], pi.cropInk, per[i].map((m, j) => ({at: m.at, ink: pi.marks[j].ink,
      inkCount: pi.marks[j].inkCount, area: pi.marks[j].ink ? pi.marks[j].ink[2] * pi.marks[j].ink[3] : 0}))));
  });

  // the scale and the crops: one k for every page, the crops grown round their padded marks (k depends on the crops: settle in 3 rounds)
  const bW = beside && side.length ? ((beside.h ?? 640) * (side[0].x1 - side[0].x0)) / Math.max(1, side[0].y1 - side[0].y0) : 0;
  const availW = DS.W - 2 * DS.MX - (beside ? bW + DS.S.xxl : 0);
  const labels = pages.reduce((a, p) => a + (p.label ? LABEL_H : 0), 0);
  const availH = DS.BOTTOM - DS.TOP - labels - GAP * (pages.length - 1);
  let crops: Box[] = pages.map((p, i) => p.crop ?? [0, 0, ink[i].iw, ink[i].ih]);
  const inks = (i: number) => ink[i].marks.map((m) => m.ink as Box);
  let k = 1;
  for (let r = 0; r < 3; r++) {
    k = Math.min(availW / Math.max(...crops.map((c) => c[2])), availH / crops.reduce((a, c) => a + c[3], 0), maxScale);
    crops = pages.map((p, i) => expandCrop(p.crop ?? [0, 0, ink[i].iw, ink[i].ih], inks(i), k, DS.MARK.PAD, MARGIN));
  }
  k = Math.min(availW / Math.max(...crops.map((c) => c[2])), availH / crops.reduce((a, c) => a + c[3], 0), maxScale);
  const colW = Math.max(...crops.map((c) => c[2])) * k;
  const groupW = colW + (beside ? bW + DS.S.xxl : 0);
  const x0 = Math.round(DS.CX - groupW / 2);
  const colX = x0 + (beside ? Math.round(bW + DS.S.xxl) : 0);
  const totalH = crops.reduce((a, c) => a + c[3] * k, 0) + labels + GAP * (pages.length - 1);
  let y = Math.round(DS.CY - totalH / 2);

  const cards = pages.map((p, i) => {
    const c = crops[i];
    const W = Math.round(c[2] * k), H = Math.round(c[3] * k);
    const L = Math.round(colX + (colW - W) / 2);
    const top = y + (p.label ? LABEL_H : 0);
    y = top + H + GAP;
    const pi = ink[i];
    const isDark = p.dark ?? pi.dark;
    const look: 'wash' | 'box' = isDark || p.outline ? 'box' : 'wash';
    const ms = per[i].map((m, j) => ({rect: markRect(pi.marks[j].ink as Box, c, k, DS.MARK.PAD), ink: pi.marks[j].ink as Box, u: lightP(t, m.at)}));
    const pic = {left: -c[0] * k, top: -c[1] * k, width: pi.iw * k, height: pi.ih * k};
    const inkL = (m: {ink: Box}): Box => [(m.ink[0] - c[0]) * k, (m.ink[1] - c[1]) * k, m.ink[2] * k, m.ink[3] * k];
    // the spot look (marks.tsx): the newest lit words' light; an older mark's light and colour go as the next one lights
    const order = per[i].map((m, j) => ({at: m.at, j})).sort((a, b) => a.at - b.at);
    // marks on the same word (one `at`, within TIE s) light together as one group: the next mark is the next LATER word, and each box is
    // its own hole in the one dim below (two marks on one `at` would each take the other as "the next one", each dim darkening the
    // other's box, so only the last would light)
    const TIE = 0.05;
    const nextAt = (j: number) => order.find((o) => o.at > per[i][j].at + TIE)?.at;
    const su = ms.map((m, j) => {
      const n = nextAt(j);
      return m.u * (n !== undefined ? 1 - lightP(t, n) : 1);
    });
    // the dim: the room darkens over 0.4 s round the word (from 0.1 s before it), as the Still's spot look does (a change of light,
    // never a 0.12-s blink: a page's dim on the 0.12-s light, its mark 0.12 s after the cut, shows the bright row for 6 frames and then
    // snaps dark: a flash frame).
    // ONE room dim for the page's marks (a dim per mark lets the room flash brighter between two lights): it comes in round the first
    // word and stays; each mark's own box is a hole in it (the first word's open from the start, a later one's opening with its light),
    // handed over as the next word lights; each box's light ends at its edge (`tight`: the next word stays dim)
    const first = order.length ? order[0].at : 0;
    const room = interpolate(t, [first - 0.1, first + 0.3], [0, 1], {...clamp, easing: Easing.inOut(Easing.cubic)});
    const holes = ms.map((_, j) => {
      const n = nextAt(j);
      return (per[i][j].at <= first + TIE ? 1 : lightP(t, per[i][j].at)) * (n !== undefined ? 1 - lightP(t, n) : 1);
    });
    return (
      <React.Fragment key={i}>
        {p.label ? <div style={{position: 'absolute', left: L, top: top - LABEL_H, ...type('label'), whiteSpace: 'nowrap'}}>{p.label}</div> : null}
        <div data-kit3="page" style={{position: 'absolute', left: L, top, width: W, height: H, borderRadius: DS.R, overflow: 'hidden',
          boxShadow: DS.SHADOW, background: `rgb(${pi.paper.join(',')})`}}>
          <Img src={url(p.src)} style={{position: 'absolute', ...pic, maxWidth: 'none'}} />
          {markLook === 'spot' ? (
            <>
              {dimRest && ms.length ? <SpotDim W={W} H={H} rects={ms.map((m) => m.rect)} ls={holes} u={room} shape="line" tight /> : null}
              {ms.map((m, j) => (isDark ? <SpotInk key={`i${j}`} src={p.src} rect={m.rect} img={pic} paper={pi.paper} u={su[j]} />
                : <MarkBox key={`w${j}`} rect={m.rect} u={su[j]} look="wash" />))}
              {ms.map((m, j) => <SpotGate key={`g${j}`} rect={m.rect} u={m.u} ink={inkL(m)} />)}
            </>
          ) : (
            <>
              {dimRest && ms.length ? <Veil W={W} H={H} holes={ms.map((m) => ({rect: m.rect, u: m.u}))} /> : null}
              {ms.map((m, j) => <MarkBox key={j} rect={m.rect} u={m.u} look={look} ink={inkL(m)} />)}
            </>
          )}
        </div>
      </React.Fragment>
    );
  });
  return stage(
    <>
      {beside ? (
        <div style={{position: 'absolute', left: x0, top: DS.CY - (beside.h ?? 640) / 2}}>
          <Picture src={beside.src} h={beside.h ?? 640} at={0} caption={beside.caption} sub={beside.sub} />
        </div>
      ) : null}
      {cards}
    </>,
  );
};
