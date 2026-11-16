// kit3 · the one mark, drawn the same everywhere (pages, stills, footage). Never placed on its own: Page, Still and Foot draw it inside
// the layer of the picture it marks, so it rides with that picture, and they stop the picture under it from its first light (a mark on
// a moving picture can't be read).
//
//   MarkBox  rect [x, y, w, h] in its layer's px (the OUTER edge: the pad is already in it). Two looks:
//            'wash' (a light page): the accent under the words, multiplied (the ink stays black), 85%
//            'box'  (a dark page, a coloured thing on a light page, any picture): a 4-px accent border INSIDE the box (border-box: a
//                   content-box border would sit 4 px from the words on the left/top and 12 on the right/bottom) over a 14% accent tint
//            `u` its light 0..1; `older` (pictures only) fades a mark the voice has moved past to a 70% ink outline, so the accent stays
//            on what is named now. data-gate="mark" (gate B12 MARK_MOVES reads it); data-kit3-ink: the ink box it was padded from (layer px)
//   Veil     the rest of a page or picture dimmed a little while a part is lit: one SVG mask, a hole per mark that opens with that
//            mark's own light (no pop), the holes exactly the marks' rects
//   frameMarkVerdict  the guards for marks on a picture (no ink to read there): MARK_LATE, a box off the picture, a box covering 45% or
//            more of what is shown (nothing to pick it out from)
//
// THE SPOT LOOK (`look="spot"` on Still, Foot, Page; the box stays the default look). No shape drawn round the thing: the rest of the
// layer dims and greys outside a feathered light on it, and the thing stands out by the light alone (a drawn box over a picture reads
// as clutter; the dim reads as the eye's own focus). Made from a mock-up's measured light (tools/motion/markmock.py).
//   SpotDim  the layer dimmed and greyed (SpotLook's dim and grey) outside a light on `rect` (layer px): 'round' (a thing in a picture:
//            an ellipse, 0.95 x 1.25 of the box's width and height as semi-axes, its edge falling off as the mock-up's blur measured) or
//            'line' (words: the padded words, feathered FEATHER px). A backdrop filter, so it dims whatever is under it (a still, a page,
//            a clip); its light `u` scales the filter (no pop, no second copy of the picture)
//   SpotRim  a thing's OWN silhouette (spotmask.py's mask, measured from the picture's pixels: <dir>/sil/<stem>__x_y_w_h.png, the box
//            padded by p = ceil(max(w, h) / 2), the thing as alpha) drawn in the accent: a 2-px line just outside its edge and a soft glow
//            over it, in screen px whatever the picture's scale (1.5-1.6 px and 6 px on the mock-up). Off unless SpotLook's `rim`
//   SpotInk  marked words on a dark page turned to the accent (their ink: brighter than the paper), the words' own letters carrying the
//            colour the way a picture's thing carries its rim. Off unless SpotLook's `ink`
//   SpotGate the mark's box for the gate (data-gate="mark", invisible): its checks read the same rect as the box look's
//   SpotLook a video's own settings round its composition: <SpotLook dim={0.22} lift={2.7}>; none = the defaults below
import React, {useId} from 'react';
import {Img, interpolateColors} from 'remotion';
import {DS} from './tokens';
import {INK_RGB} from '../brand';
import {Box} from './layout';
import {Tag} from './text';
import {url, useMeasured} from './measure';

export const MarkBox: React.FC<{rect: Box; u: number; look: 'wash' | 'box'; older?: number; ink?: Box; name?: string;
  nameSide?: 'above' | 'below'}> = ({rect, u, look, older = 0, ink, name, nameSide = 'below'}) => {
  if (u <= 0) return null;
  const [x, y, w, h] = rect;
  const base: React.CSSProperties = {position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: DS.R_CHIP, boxSizing: 'border-box'};
  const data = {'data-gate': 'mark', 'data-kit3': 'mark', 'data-kit3-ink': ink ? ink.map((v) => Math.round(v)).join(',') : ''};
  if (look === 'wash') {
    return <div {...data} style={{...base, background: DS.ACCENT, mixBlendMode: 'multiply', opacity: DS.MARK.WASH * u}} />;
  }
  const edge = interpolateColors(older, [0, 1], [DS.ACCENT, `rgba(${INK_RGB},0.7)`]);
  return (
    <div {...data} style={{...base, border: `${DS.MARK.BORDER}px solid ${edge}`, background: older >= 1 ? 'transparent' : DS.ACCENT_TINT, opacity: u}}>
      {name && older < 1 ? (
        <div style={{position: 'absolute', left: '50%', transform: 'translateX(-50%)', whiteSpace: 'nowrap',
          ...(nameSide === 'above' ? {bottom: h + DS.S.s} : {top: h + DS.S.s}), opacity: 1 - older}}>
          <Tag lit={1} size="title">{name}</Tag>
        </div>
      ) : null}
    </div>
  );
};

// how far a dim layer reaches past its picture on every side (the parent's overflow clip trims it): see SpotDim
export const OVER = 2;

export const Veil: React.FC<{W: number; H: number; holes: {rect: Box; u: number}[]; strength?: number}> = ({W, H, holes, strength = DS.MARK.VEIL}) => {
  const id = `k3v${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const top = Math.max(0, ...holes.map((m) => m.u));
  if (top <= 0) return null;
  const O = OVER;   // past the picture on every side, as SpotDim (no undimmed edge line)
  return (
    <svg width={W + 2 * O} height={H + 2 * O} viewBox={`${-O} ${-O} ${W + 2 * O} ${H + 2 * O}`} style={{position: 'absolute', left: -O, top: -O,
      pointerEvents: 'none'}}>
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse" x={-O} y={-O} width={W + 2 * O} height={H + 2 * O}>
          <rect x={-O} y={-O} width={W + 2 * O} height={H + 2 * O} fill="#fff" />
          {holes.map((m, i) => (
            <rect key={i} x={m.rect[0]} y={m.rect[1]} width={m.rect[2]} height={m.rect[3]} rx={DS.R_CHIP} fill="#000" fillOpacity={m.u} />
          ))}
        </mask>
      </defs>
      <rect x={-O} y={-O} width={W + 2 * O} height={H + 2 * O} fill="#000" fillOpacity={strength * top} mask={`url(#${id})`} />
    </svg>
  );
};

// ============================================================================================================================ the spot
// DIM 0.22: the light left outside the spot. LIGHT_W/H: the light's smallest half-width and half-height as shares of the layer (a light
// sized to a small group of things becomes a glowing disc, "a moon"; a wide soft light reads as the scene's own glow: half-axes 0.18 x
// 0.22 of the frame)
export const SPOT = {DIM: 0.22, GREY: 0.6, RIM: 2, GLOW: 6, GLOW_A: 0.55, FEATHER: 22, LIGHT_W: 0.18, LIGHT_H: 0.22};
// the light's fall-off (1 - light) along its ellipse's radius (1 = the ellipse's edge): the mock-up's ellipse blurred by 0.45 of the box's
// long side, measured on boxes of 100 x 71 to 282 x 149 px (the same within 0.02 on both axes)
const FALL: [number, number][] = [[0, 0], [0.25, 0.038], [0.5, 0.152], [0.75, 0.332], [1, 0.545], [1.25, 0.735], [1.5, 0.875],
  [1.75, 0.952], [2, 0.985], [2.5, 1]];

// The spot's per-video settings, set once round a video's composition with <SpotLook>:
//   dim   the light left outside the spot (default SPOT.DIM, 0.22)
//   grey  how much of the colour goes outside it (default 0.6)
//   lift  the inside lift's exponent: the lit thing pushed brighter by 1-(1-v)^lift per channel, whites never clipped (0 = off; 2.7 a
//         tried value). ONLY on a mark that says `bright: true` (a sign, a screen, lights: the thing itself is the light); a dark thing
//         against a bright sky is never lifted: the lift lights the sky round it into a white hot spot. Never on words
//   rim, ink  the accent on the thing (its outline in the accent; marked words turned to the accent): OFF by default (the thing is
//         shown by the light alone, which reads cleaner); true brings the accent back where a video asks for it
// A context, not a module setting: Root.tsx bundles every video together, so one video's setting must never reach another's.
export type SpotLookSettings = {dim?: number; grey?: number; lift?: number; rim?: boolean; ink?: boolean};
const SpotCtx = React.createContext<Required<SpotLookSettings>>({dim: SPOT.DIM, grey: SPOT.GREY, lift: 0, rim: false, ink: false});
export const SpotLook: React.FC<SpotLookSettings & {children?: React.ReactNode}> = ({dim = SPOT.DIM, grey = SPOT.GREY, lift = 0,
  rim = false, ink = false, children}) => <SpotCtx.Provider value={{dim, grey, lift, rim, ink}}>{children}</SpotCtx.Provider>;
// the lift's curve as an feComponentTransfer table, its strength u (0..1) mixed in so it lights with the mark (no pop)
const liftTable = (g: number, u: number) => Array.from({length: 33}, (_, i) => {
  const v = i / 32;
  return ((1 - u) * v + u * (1 - Math.pow(1 - v, g))).toFixed(4);
}).join(' ');

// `zs`: the layer's own scale on screen (Foot's zoom): the light's smallest size is a share of the SCREEN, so a zoomed-in thing keeps the
// darkness round it as it was before the zoom
// `rects` (shape 'round'): things named together, ONE dim with a light on each (with a dim per mark, each dimmed the other's light away).
// The masks multiply (mask-composite intersect): the dim falls only where no light is
// `rects` (shape 'line'): words lit together (a quote over two lines, a name and its title), ONE dim with a hole round each (with a dim
// per mark, each darkened the other's words and only the last stayed lit).
// A line hole is two gradients, which CSS can't intersect hole by hole in one mask list, so the holes are one SVG mask (each box grown
// FEATHER/2 and blurred by FEATHER/4: transparent at the box, half at FEATHER/2 out, dim at FEATHER, as the single hole's ramp), and the
// layer waits for that image (MaskReady) so no render tab's first frame paints it unmasked
// `ls` (one per rect, 0..1): how open each hole is. ONE room dim for a run of marks, the light handed from hole to hole (with a dim per
// mark, the old dim went in 0.12 s while the next took 0.4 s to come in, so the room flashed brighter between two lights, background
// 18 -> 47 -> 17): the caller keeps `u` (the room) steady and opens and closes the holes.
// `tight` (words on a page): the light ends at the box (half at its edge, gone 3 px out) instead of FEATHER px past it, so the next
// word's first letter stays dim (word gaps are 10-16 px)
const TIGHT = 3;
const svgHoles = (all: Box[], LW: number, LH: number, F: number, ls?: number[], tight = false) => {
  const r = (v: number) => v.toFixed(1);
  const gx = tight ? 0 : F / 2;
  const holes = all.map(([x, y, w, h], i) => `<rect x='${r(x - gx)}' y='${r(y - F / 2)}' width='${r(w + 2 * gx)}' height='${r(h + F)}'`
    + `${ls && ls[i] < 1 ? ` fill-opacity='${Math.max(0, ls[i]).toFixed(2)}'` : ''}/>`).join('');
  const sd = tight ? `${r(TIGHT / 2)} ${r(F / 4)}` : r(F / 4);
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${r(LW)}' height='${r(LH)}'><defs><filter id='b' filterUnits='userSpaceOnUse' `
    + `x='0' y='0' width='${r(LW)}' height='${r(LH)}'><feGaussianBlur stdDeviation='${sd}'/></filter><mask id='m' maskUnits='userSpaceOnUse' `
    + `x='0' y='0' width='${r(LW)}' height='${r(LH)}'><rect width='100%' height='100%' fill='white'/><g fill='black' filter='url(#b)'>${holes}</g>`
    + `</mask></defs><rect width='100%' height='100%' fill='black' mask='url(#m)'/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
};
const MaskReady: React.FC<{src: string; children: React.ReactNode}> = ({src, children}) => {
  const ok = useMeasured(`mask:${src}`, () => new Promise<boolean>((res) => {
    const im = new Image();
    im.onload = () => res(true);
    im.onerror = () => res(false);
    im.src = src;
  }), 'spot holes');
  return ok === null ? null : <>{children}</>;
};
export const SpotDim: React.FC<{W: number; H: number; rect?: Box; rects?: Box[]; u: number; shape: 'round' | 'line'; bright?: boolean;
  brights?: boolean[]; zs?: number; src?: string; ls?: number[]; tight?: boolean}> = ({W, H, rect, rects, u, shape, bright, brights, zs = 1,
  src, ls, tight = false}) => {
  const s = React.useContext(SpotCtx);
  const lid = `k3l${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  // the layer reaches OVER px past the picture on every side: a dim the exact size of a card at fractional px leaves the picture's last
  // column and row undimmed (a flickering bright line at the right and bottom edge). Every parent that holds a dim clips (overflow
  // hidden), so the overscan never shows.
  const O = OVER;
  const all = (rects ?? (rect ? [rect] : [])).map((r) => [r[0] + O, r[1] + O, r[2], r[3]] as Box);
  if (u <= 0 || !all.length) return null;
  const [x, y, w, h] = all[0];
  let mask: string;
  let light: string | null = null;
  let many = false;
  let holes: string | null = null;
  // each hole's opening, quantized (a handover's frames reuse a few masks)
  const lq = ls ? all.map((_, i) => Math.round(Math.min(1, Math.max(0, ls[i] ?? 1)) * 50) / 50) : null;
  if (lq && lq.every((l) => l <= 0)) {
    // every hole shut: the whole layer dims (one plain layer, no mask)
    mask = 'none';
  } else if (shape === 'line' && (all.length > 1 || (lq && lq[0] < 1))) {
    holes = svgHoles(all, W + 2 * O, H + 2 * O, SPOT.FEATHER, lq ?? undefined, tight);
    mask = `url("${holes}")`;
  } else if (shape === 'round') {
    // the ellipse round the thing, never smaller than a soft light over about a fifth of the layer (no glowing disc)
    const ell = ([ex, ey, ew, eh]: Box) => `ellipse ${Math.max(0.95 * ew, (SPOT.LIGHT_W * W) / Math.max(1, zs))}px ${Math.max(1.25 * eh,
      (SPOT.LIGHT_H * H) / Math.max(1, zs))}px at ${ex + ew / 2}px ${ey + eh / 2}px`;
    // a hole half open: its dim alpha raised toward 1 (shut) everywhere in it
    const op = (i: number, a: number) => (lq ? 1 - lq[i] * (1 - a) : a);
    mask = all.map((r, i) => `radial-gradient(${ell(r)}, ${FALL.map(([q, a]) => `rgba(0,0,0,${op(i, a).toFixed(3)}) ${q * 100}%`).join(', ')})`).join(', ');
    const lit = all.map((r, i) => ({r, i})).filter(({i}) => (brights ? brights[i] : true) && (!lq || lq[i] > 0));
    light = lit.length ? lit.map(({r, i}) => `radial-gradient(${ell(r)}, ${FALL.map(([q, a]) => `rgba(0,0,0,${((1 - a) * (lq ? lq[i] : 1)).toFixed(3)}) ${q * 100}%`).join(', ')})`).join(', ') : null;
    many = all.length > 1;
  } else if (tight) {
    // a word's light ends at its box: half at the box's left and right edges, gone TIGHT px out (top and bottom keep the soft fall)
    const F = SPOT.FEATHER, T = TIGHT;
    mask = `linear-gradient(to right, #000 ${x - T}px, rgba(0,0,0,0.5) ${x}px, transparent ${x + T}px, transparent ${x + w - T}px, `
      + `rgba(0,0,0,0.5) ${x + w}px, #000 ${x + w + T}px), linear-gradient(to bottom, #000 ${y - F}px, rgba(0,0,0,0.5) `
      + `${y - F / 2}px, transparent ${y}px, transparent ${y + h}px, rgba(0,0,0,0.5) ${y + h + F / 2}px, #000 ${y + h + F}px)`;
  } else {
    const F = SPOT.FEATHER;
    mask = `linear-gradient(to right, #000 ${x - F}px, rgba(0,0,0,0.5) ${x - F / 2}px, transparent ${x}px, transparent ${x + w}px, `
      + `rgba(0,0,0,0.5) ${x + w + F / 2}px, #000 ${x + w + F}px), linear-gradient(to bottom, #000 ${y - F}px, rgba(0,0,0,0.5) `
      + `${y - F / 2}px, transparent ${y}px, transparent ${y + h}px, rgba(0,0,0,0.5) ${y + h + F / 2}px, #000 ${y + h + F}px)`;
  }
  const f = `grayscale(${(s.grey * u).toFixed(4)}) brightness(${(1 - (1 - s.dim) * u).toFixed(4)})`;
  const tab = light && (bright || (brights ?? []).some(Boolean)) && s.lift > 0 ? liftTable(s.lift, u) : null;
  const out = (
    <>
      {tab && light ? (
        <>
          <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden>
            <filter id={lid} colorInterpolationFilters="sRGB">
              <feComponentTransfer>
                <feFuncR type="table" tableValues={tab} />
                <feFuncG type="table" tableValues={tab} />
                <feFuncB type="table" tableValues={tab} />
              </feComponentTransfer>
            </filter>
          </svg>
          <div data-kit3="spot-lift" style={{position: 'absolute', left: -O, top: -O, width: W + 2 * O, height: H + 2 * O, pointerEvents: 'none',
            backdropFilter: `url(#${lid})`, WebkitBackdropFilter: `url(#${lid})`, maskImage: light, WebkitMaskImage: light,
            maskRepeat: 'no-repeat', WebkitMaskRepeat: 'no-repeat'}} />
        </>
      ) : null}
      {src ? (
        // `src` (the picture under the layer, drawn at 0,0 W x H): the dim is that picture's own copy, filtered and masked, instead of a
        // backdrop filter. A backdrop filter makes Chrome composite the layer, and a composited layer under a camera's scale is painted at
        // its own size and blown up (at 1.3x, faces went soft: Laplacian variance 57 vs 223); the copy is painted through the scale like
        // the picture itself. Same box, same snapping: the copy sits exactly on the picture
        <div data-kit3="spot" style={{position: 'absolute', left: -O, top: -O, width: W + 2 * O, height: H + 2 * O, pointerEvents: 'none',
          filter: f, maskImage: mask, WebkitMaskImage: mask, maskRepeat: 'no-repeat', WebkitMaskRepeat: 'no-repeat',
          ...(many ? {maskComposite: 'intersect', WebkitMaskComposite: 'source-in'} : {})}}>
          <Img src={src} style={{position: 'absolute', left: O, top: O, width: W, height: H}} />
        </div>
      ) : (
        <div data-kit3="spot" style={{position: 'absolute', left: -O, top: -O, width: W + 2 * O, height: H + 2 * O, pointerEvents: 'none',
          backdropFilter: f, WebkitBackdropFilter: f, maskImage: mask, WebkitMaskImage: mask, maskRepeat: 'no-repeat',
          WebkitMaskRepeat: 'no-repeat', ...(many ? {maskComposite: 'intersect', WebkitMaskComposite: 'source-in'} : {})}} />
      )}
    </>
  );
  return holes ? <MaskReady src={holes}>{out}</MaskReady> : out;
};

// the silhouette's file for a picture and a mark's box (spotmask.py writes it there)
export const silOf = (src: string, box: Box) => {
  const i = src.lastIndexOf('/');
  const stem = src.slice(i + 1).replace(/\.(png|jpe?g|webp)$/i, '');
  return `${src.slice(0, i + 1)}sil/${stem}__${box.map((v) => Math.round(v)).join('_')}.png`;
};

// `box` the mark's box in image px; `sc`, `ox`, `oy` the layer's mapping (layer px = (image px - o) x sc)
export const SpotRim: React.FC<{src: string; box: Box; sc: number; ox?: number; oy?: number; u: number}> = ({src, box, sc, ox = 0, oy = 0, u}) => {
  const id = `k3r${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const s = React.useContext(SpotCtx);
  if (u <= 0 || !s.rim) return null;   // no accent rim unless a video asks for it (SpotLook rim)
  const [x, y, w, h] = box;
  const p = Math.ceil(Math.max(w, h) / 2);
  return (
    <>
      <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden>
        <filter id={id} x="-5%" y="-5%" width="110%" height="110%" colorInterpolationFilters="sRGB">
          <feMorphology in="SourceAlpha" operator="dilate" radius={SPOT.RIM} result="d" />
          <feComposite in="d" in2="SourceAlpha" operator="out" result="ring" />
          <feGaussianBlur in="ring" stdDeviation="0.6" result="ringS" />
          <feMorphology in="SourceAlpha" operator="dilate" radius="1" result="d1" />
          <feGaussianBlur in="d1" stdDeviation={SPOT.GLOW} result="g" />
          <feComponentTransfer in="g" result="g2"><feFuncA type="linear" slope={SPOT.GLOW_A} /></feComponentTransfer>
          <feMerge result="a"><feMergeNode in="g2" /><feMergeNode in="ringS" /></feMerge>
          <feFlood floodColor={DS.ACCENT} result="c" />
          <feComposite in="c" in2="a" operator="in" />
        </filter>
      </svg>
      <Img src={url(silOf(src, box))} data-kit3="spot-rim" style={{position: 'absolute', left: (x - p - ox) * sc, top: (y - p - oy) * sc,
        width: (w + 2 * p) * sc, height: (h + 2 * p) * sc, maxWidth: 'none', filter: `url(#${id})`, opacity: u}} />
    </>
  );
};

// `rect` the padded words (layer px); `img` where the page's picture sits in the layer; `paper` the page's paper colour (0-255)
export const SpotInk: React.FC<{src: string; rect: Box; img: {left: number; top: number; width: number; height: number};
  paper: [number, number, number]; u: number}> = ({src, rect, img, paper, u}) => {
  const id = `k3i${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const s = React.useContext(SpotCtx);
  if (u <= 0 || !s.ink) return null;   // no accent ink unless a video asks for it (SpotLook ink)
  const pl = (0.2126 * paper[0] + 0.7152 * paper[1] + 0.0722 * paper[2]) / 255;
  // the ink: brighter than the paper by more than 0.05; fully accent 0.25 above it (a grey date is ~0.46 on a black paper)
  return (
    <div data-kit3="spot-ink" style={{position: 'absolute', left: rect[0], top: rect[1], width: rect[2], height: rect[3], overflow: 'hidden', opacity: u}}>
      <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden>
        <filter id={id} colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values={`0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0.2126 0.7152 0.0722 0 ${-(pl + 0.05)}`} result="a0" />
          <feComponentTransfer in="a0" result="a"><feFuncA type="linear" slope="5" /></feComponentTransfer>
          <feFlood floodColor={DS.ACCENT} result="c" />
          <feComposite in="c" in2="a" operator="in" />
        </filter>
      </svg>
      <Img src={url(src)} style={{position: 'absolute', left: img.left - rect[0], top: img.top - rect[1], width: img.width, height: img.height,
        maxWidth: 'none', filter: `url(#${id})`}} />
    </div>
  );
};

export const SpotGate: React.FC<{rect: Box; u: number; ink?: Box}> = ({rect, u, ink}) => (u <= 0 ? null : (
  <div data-gate="mark" data-kit3="spot-gate" data-kit3-ink={ink ? ink.map((v) => Math.round(v)).join(',') : ''} style={{position: 'absolute',
    left: rect[0], top: rect[1], width: rect[2], height: rect[3], opacity: u, pointerEvents: 'none'}} />
));

export const frameMarkVerdict = (d: number, frame: [number, number], marks: {box: Box; at: number}[], what: string): string[] => {
  const out: string[] = [];
  marks.forEach((m, i) => {
    const [x, y, w, h] = m.box;
    if (m.at > d - DS.MARK.LATE - DS.DUR.light) out.push(`${what} mark ${i + 1} lights at ${m.at.toFixed(2)} s of a ${d.toFixed(2)}-s shot: inside its last 0.6 s (MARK_LATE)`);
    if (x < 0 || y < 0 || x + w > frame[0] || y + h > frame[1] || w < 4 || h < 4) out.push(`${what} mark ${i + 1} [${m.box.join(', ')}] is off its picture (${frame.join(' x ')})`);
    if ((w * h) / (frame[0] * frame[1]) >= 0.45) out.push(`${what} mark ${i + 1} covers ${(100 * w * h / (frame[0] * frame[1])).toFixed(0)}% of the picture: nothing to pick it out from`);
  });
  return out;
};

// a label for errors: the kit refuses loudly, naming the piece
export const refuse = (piece: string, problems: string[]) => {
  if (problems.length) throw new Error(`kit3 ${piece}: ${problems.join('; ')}`);
};
