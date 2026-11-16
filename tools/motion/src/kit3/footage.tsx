// kit3 · footage and stills full frame (every clip full frame, never in a panel), with the shot's ONE camera move.
//
//   Foot      a clip full frame, a linear push one way ([1, 1.03]; 720p sources [1, 1.02]). `marks` [{box, at, name?, nameSide?}] (frame px,
//             the thing's own edges): the clip FREEZES from the first mark's light and its push stops (a mark needs the picture under
//             it frozen), each mark padded 8 px, border inside, drawn in the clip's layer (it rides with it), the newest lit in the accent
//             and the ones before it fading to an ink outline, the rest dimmed. `zoom`: from that freeze the picture zooms `zoom` x
//             toward the marks (their union) over DS.DUR.zoom on EASE.move, so a small thing is seen, landing as near the frame's centre
//             as the picture's own edges allow (an interface corner stays in its corner: no edge of the frame ever shows bare), then
//             drifts on slowly (a keep-alive); the spot's light keeps its size on screen. The gate's B4 UPSCALE reads the clip file's own
//             pixels: a zoom showing them past 1.3x (a 1080p cut past 1.3x; a 4K cut past 2.6x) is flagged, so a zoomed clip is cut
//             from the 4K master by its prep step; B25 MARK_SMALL flags a mark on a small thing that isn't zoomed into.
//             `hold`: freeze without marks. `blurs` [x, y, w, h] (frame px):
//             a username or a stranger's name blurred, riding with the picture. `lift`: a slightly dim capture's shadows raised by the
//             shadow curve (tokens.ts LIFT: black stays black, highlights untouched, a normal shot ~unchanged; a MURKY span is re-picked,
//             never lifted), drawn by the SVG filter `kit3-lift` (LiftFilter).
//             Props: clip (public path), d, push?, start?, origin?, hold?, marks?, look? ('spot': marks.tsx's spot look, the default;
//             a still's thing rimmed from its spotmask.py silhouette), live?, blurs?, filter?, lift?, credit?, children?
//   Still     a still full frame (cover), or one `region` [x, y, w, h] of it (image px) filling the frame; `from`: the camera glides from that
//             region onto `region` (EASE.move), done before the first mark. Refuses to show a picture past `maxScale` (1.3) x its pixels
//             unless `upscaleOk` says why (a low-resolution screenshot zoomed 4x reads as mush). `marks` as Foot's (image px), the still
//             standing still from the first light; `names` [{text, x, y, at}] (image px): a name chip on a person, riding with the picture
//             (a label is not a mark: no freeze needed). `bars` [top, bottom] px: a letterboxed TV frame's own bars kept fixed and
//             straight. `icons` [{src, x, y, at, d?}] (image px): a person placed on a map or a diagram as a round profile picture (a face
//             in a circle reads at once where a name card doesn't), a ring in ink, `d` px across on screen (default 132), riding with the
//             picture, landing on `at`. Each icon is made by make_icon.py from a frame of the footage and carries its sidecar
//             <name>.icon.json: an icon with no sidecar, cut from artwork, or whose measured face sits more than 4% of the circle off its
//             centre or fills outside 42-72% of its height is refused. The <img> marks itself data-gate="icon" (qa_centred.py).
//   Burst     hard cuts between clips at `cuts` (the shot's seconds), the last to the shot's own last frame (never a dark frame at its end)
//   TagShot   footage or a still with a name on its chip in the tag's one place (top right; `left` over a person on the left; `on` [x, y]
//             on the person), landing on `tagAt`; the clip plays on under it (a name is not a mark)
//   StampShot footage (or a still, or a burst) with the passage's claim stamped on its word (text.Stamp)
//   TypedShot footage (or a still, or a burst) with a date typing itself top centre (text.TypedLine, whole 0.3 s before the cut)
import React from 'react';
import {AbsoluteFill, Easing, Img, Sequence, interpolate} from 'remotion';
import {Clip, FPS, clamp, useT} from '../lib';
import {DS, LIFT_TABLE, heldT, lightP, markStart, moveP} from './tokens';
import {Box} from './layout';
import {url, useImgBoxes, useMeasured} from './measure';
import {Credit, Enter, Hold, Pending, hasClip} from './stage';
import {MarkBox, SpotDim, SpotGate, SpotRim, Veil, frameMarkVerdict, refuse} from './marks';
import {Stamp, Tag, TypedLine} from './text';

// bright: the thing is itself a light (a sign, a screen): the video's spot lift may brighten it (marks.tsx SpotLook)
// `shape: 'line'`: a row of text in the picture (a list's item, a caption's line): its light hugs the row's box and stops at its edges,
// where the round light (at least ~a fifth of the frame) would light the rows round it too (rows 125 px apart: the lit row 170 against
// 140 beside it). A picture's marks take the line light when all of them are rows
export type FrameMark = {box: Box; at: number; name?: string; nameSide?: 'above' | 'below'; bright?: boolean; shape?: 'line'};

// the lift's shadow curve as an SVG filter: one table per colour channel on the picture's own sRGB values (color-interpolation-filters
// sRGB: SVG's default, linearRGB, would bend the curve), alpha untouched. A 0 x 0 svg (the gate's probe skips boxes under 2 px)
export const LiftFilter: React.FC = () => (
  <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden>
    <filter id="kit3-lift" colorInterpolationFilters="sRGB">
      <feComponentTransfer>
        <feFuncR type="table" tableValues={LIFT_TABLE} />
        <feFuncG type="table" tableValues={LIFT_TABLE} />
        <feFuncB type="table" tableValues={LIFT_TABLE} />
      </feComponentTransfer>
    </filter>
  </svg>
);

// a profile icon's sidecar, written by make_icon.py: where the face came from and where it sits on the icon (measured on the icon itself)
export type IconSide = {source?: {file?: string; kind?: string}; artwork?: boolean;
  face?: {dx: number; dy: number; share: number} | null} | null;
export const ICON_OFF = 0.04;                                   // the face's centre off the circle's centre, as a share of its side
export const ICON_SHARE: [number, number] = [0.42, 0.72];       // the face's height as a share of the circle's
const ARTWORK = /(artwork|cover[_ ]?art|postcard|wallpaper)/i;
export const sidecarOf = (src: string) => `${src.replace(/\.(png|jpe?g|webp)$/i, '')}.icon.json`;
export const iconVerdict = (src: string, s: IconSide): string[] => {
  if (!s) return [`icon ${src} has no sidecar ${sidecarOf(src)}: make it with make_icon.py from a frame of the footage`];
  const bad: string[] = [];
  if (s.artwork || ARTWORK.test(s.source?.file ?? '')) bad.push(`icon ${src} is cut from artwork (${s.source?.file}): cut it from the footage itself`);
  const m = s.face;
  if (!m) bad.push(`icon ${src}: no face measured on it`);
  else {
    if (Math.abs(m.dx) > ICON_OFF || Math.abs(m.dy) > ICON_OFF) {
      bad.push(`icon ${src}: its face sits ${(m.dx * 100).toFixed(1)}% / ${(m.dy * 100).toFixed(1)}% of the circle off its centre (over ${ICON_OFF * 100}%)`);
    }
    if (m.share < ICON_SHARE[0] || m.share > ICON_SHARE[1]) {
      bad.push(`icon ${src}: its face fills ${(m.share * 100).toFixed(0)}% of the circle's height (outside ${ICON_SHARE[0] * 100}-${ICON_SHARE[1] * 100}%)`);
    }
  }
  return bad;
};
// every icon's sidecar, read once per tab before the picture draws (a missing one reads as null and is refused by name, not as a load error)
const useIconSides = (srcs: string[]) => useMeasured<IconSide[]>(`icons|${srcs.join('|')}`, () => Promise.all(srcs.map((s) =>
  fetch(url(sidecarOf(s))).then((r) => (r.ok ? r.json() as Promise<IconSide> : null)).catch(() => null))), `reading ${srcs.length} icon sidecar(s)`);

// the marks of a picture, drawn in its layer: `sc` maps the picture's px to the layer's. `look` 'spot' (marks.tsx): the rest dims
// round a light on each thing (the newest; an older one's light and rim go as the next lights), the thing's own silhouette rimmed
// in the accent when the picture is a still and SpotLook asks for it (`src`: spotmask.py's mask beside it)
// `zs`: how much the layer itself is scaled on screen (Foot's zoom), so the spot's light keeps its size on screen
export const SAME_AT = 0.05;   // s: marks whose words land this close are named together
const PicMarks: React.FC<{marks: FrameMark[]; sc: number; ox: number; oy: number; W: number; H: number; look?: 'box' | 'spot'; src?: string;
  zs?: number}> = ({marks, sc, ox, oy, W, H, look = 'spot', src, zs = 1}) => {
  const t = useT();
  const order = marks.map((m, i) => ({m, i})).sort((a, b) => a.m.at - b.m.at);
  const rects = marks.map((m) => {
    const L = Math.floor((m.box[0] - ox) * sc) - DS.MARK.PAD, T = Math.floor((m.box[1] - oy) * sc) - DS.MARK.PAD;
    const R = Math.ceil((m.box[0] + m.box[2] - ox) * sc) + DS.MARK.PAD, B = Math.ceil((m.box[1] + m.box[3] - oy) * sc) + DS.MARK.PAD;
    return [L, T, R - L, B - T] as Box;
  });
  // a mark is "older" once the next one (in time) lights
  const older = marks.map((m, i) => {
    const k = order.findIndex((o) => o.i === i);
    return k + 1 < order.length ? lightP(t, order[k + 1].m.at) : 0;
  });
  const lit = marks.map((m) => lightP(t, m.at));
  const newest = order.reduce((a, o) => (lit[o.i] > 0 ? o.i : a), -1);
  if (look === 'spot') {
    const ink = (m: FrameMark): Box => [(m.box[0] - ox) * sc, (m.box[1] - oy) * sc, m.box[2] * sc, m.box[3] * sc];
    // marks named together (lighting within SAME_AT of each other) are one light: lit together, dimmed as one, older together (with the
    // same `at`, the second mark would count as "the next one" and switch the first one's light off the moment both lit)
    const groups: number[][] = [];
    order.forEach(({m, i}) => {
      const g = groups[groups.length - 1];
      if (g && m.at - marks[g[0]].at <= SAME_AT) g.push(i);
      else groups.push([i]);
    });
    const gOld = groups.map((_, k) => (k + 1 < groups.length ? lightP(t, marks[groups[k + 1][0]].at) : 0));
    const oldOf = marks.map((_, i) => gOld[groups.findIndex((g) => g.includes(i))]);
    const u = marks.map((_, i) => lit[i] * (1 - oldOf[i]));
    // the room darkens over 0.4 s round the first word (from 0.1 s before it), never in a 0.12-s blink: a dim of the whole picture is a
    // change of light, not a box popping on. ONE room dim for the picture's marks (a dim per group, the old one gone in 0.12 s while the
    // next took 0.4 s to come in, flashes the room brighter between two lights, 18 -> 47 -> 17): it stays; the light is handed from hole
    // to hole (the first group's hole open from the start, a later one's opening with its light)
    const gi = marks.map((_, i) => groups.findIndex((g) => g.includes(i)));
    const room = groups.length ? interpolate(t, [marks[groups[0][0]].at - 0.1, marks[groups[0][0]].at + 0.3], [0, 1],
      {...clamp, easing: Easing.inOut(Easing.cubic)}) : 0;
    const holes = marks.map((_, i) => (gi[i] === 0 ? 1 : lightP(t, marks[groups[gi[i]][0]].at)) * (1 - gOld[gi[i]]));
    return (
      <>
        {marks.length && marks.every((m) => m.shape === 'line')
          ? <SpotDim W={W} H={H} rects={rects} ls={holes} u={room} shape="line" tight />
          : marks.length ? <SpotDim W={W} H={H} rects={marks.map((m) => ink(m))} ls={holes} u={room} shape="round"
            brights={marks.map((m) => !!m.bright)} zs={zs} /> : null}
        {src ? marks.map((m, i) => <SpotRim key={`r${i}`} src={src} box={m.box} sc={sc} ox={ox} oy={oy} u={u[i]} />) : null}
        {/* the gate reads the light the viewer sees (u): a mark switched off reads as gone (B25b MARK_BLINK) */}
        {marks.map((m, i) => <SpotGate key={`g${i}`} rect={rects[i]} u={u[i]} ink={ink(m)} />)}
        {marks.map((m, i) => (m.name && u[i] > 0 ? (
          <div key={`n${i}`} style={{position: 'absolute', left: rects[i][0] + rects[i][2] / 2, transform: 'translateX(-50%)', whiteSpace: 'nowrap',
            ...(m.nameSide === 'above' ? {bottom: H - rects[i][1] + DS.S.s} : {top: rects[i][1] + rects[i][3] + DS.S.s}), opacity: u[i]}}>
            <Tag lit={1} size="title">{m.name}</Tag>
          </div>
        ) : null))}
      </>
    );
  }
  return (
    <>
      <Veil W={W} H={H} holes={newest >= 0 ? [{rect: rects[newest], u: lit[newest]}] : []} />
      {marks.map((m, i) => (
        <MarkBox key={i} rect={rects[i]} u={lit[i]} look="box" older={older[i]} name={m.name} nameSide={m.nameSide}
          ink={[(m.box[0] - ox) * sc, (m.box[1] - oy) * sc, m.box[2] * sc, m.box[3] * sc]} />
      ))}
    </>
  );
};

// a CSS transform-origin ('50% 50%', 'left top', '960px 540px') as frame px
const originPx = (o: string): [number, number] => {
  const p = o.trim().split(/\s+/);
  const v = (s: string | undefined, L: number) => (!s || s === 'center' ? L / 2 : s.endsWith('%') ? (parseFloat(s) / 100) * L
    : s === 'left' || s === 'top' ? 0 : s === 'right' || s === 'bottom' ? L : parseFloat(s));
  return [v(p[0], DS.W), v(p[1], DS.H)];
};
// DRIFT: the keep-alive after the zoom lands, a share per second (a shot's push is 3% over ~2.5 s); a rate, so a short hold never
// speeds it up into a second zoom
export const ZOOM = {MIN: 1.4, MAX: 3.0, DRIFT: 0.012};
// Foot's zoom as translate + scale round the frame's top-left at time t: from the push held at the freeze (k0 round `oc`) to `z` x with the
// marks' union `u` as near the centre as the frame's edges allow, then the keep-alive drift round where it landed. Every step keeps the
// frame covering the screen: the start and the end both do, a straight blend of two covering transforms covers too, and a drift that
// grows the picture round a point on screen only pushes its edges outward
export const zoomMove = (t: number, at: number, d: number, z: number, u: Box, k0: number, oc: [number, number]) => {
  const W = DS.W, H = DS.H;
  const px = u[0] + u[2] / 2, py = u[1] + u[3] / 2;
  const Z1 = Math.max(z, k0);
  const tx0 = oc[0] * (1 - k0), ty0 = oc[1] * (1 - k0);
  const tx1 = Math.min(0, Math.max(W * (1 - Z1), W / 2 - Z1 * px)), ty1 = Math.min(0, Math.max(H * (1 - Z1), H / 2 - Z1 * py));
  const g = moveP(t, at, DS.DUR.zoom);
  const s = k0 + (Z1 - k0) * g, tx = tx0 + (tx1 - tx0) * g, ty = ty0 + (ty1 - ty0) * g;
  const land = at + DS.DUR.zoom;
  const f = 1 + ZOOM.DRIFT * Math.max(0, Math.min(t, d) - land);
  const sx = tx1 + Z1 * px, sy = ty1 + Z1 * py;
  return {s: s * f, tx: sx + f * (tx - sx), ty: sy + f * (ty - sy)};
};

// `live`: the marks are on an on-screen overlay fixed on the screen (a score bug, a status icon), so the clip plays on under them
// instead of freezing (a blinking overlay frozen would show one colour). Never for a thing in the picture: that one moves (a mark needs
// the picture under it frozen). The gate's B12 reads such a mark over a playing clip; its allow names the overlay
export const Foot: React.FC<{clip: string; d: number; push?: [number, number]; start?: number; origin?: string; hold?: number;
  marks?: FrameMark[]; look?: 'box' | 'spot'; zoom?: number; live?: boolean; blurs?: Box[]; filter?: string; lift?: boolean; credit?: string;
  children?: React.ReactNode}> = ({clip, d, push = DS.PUSH, start = 0, origin = '50% 50%', hold: hold0, marks = [], look = 'spot', zoom, live,
  blurs = [], filter, lift, credit, children}) => {
  const t = useT();
  if (!hasClip(clip)) return <Pending what={clip} />;
  refuse(`Foot ${clip}`, frameMarkVerdict(d, [DS.W, DS.H], marks, 'Foot'));
  if (zoom !== undefined) {
    refuse(`Foot ${clip}`, [...(!marks.length ? ['a zoom with no marks: it zooms into what its marks show'] : []),
      ...(zoom < ZOOM.MIN || zoom > ZOOM.MAX ? [`zoom ${zoom}: between ${ZOOM.MIN} and ${ZOOM.MAX}`] : [])]);
  }
  const first = marks.length ? markStart(Math.min(...marks.map((m) => m.at))) : undefined;
  const hold = marks.length && !live ? first : hold0;
  const k = interpolate(heldT(t, hold), [0, Math.max(0.01, d)], push, clamp);
  const f = lift ? `url(#kit3-lift)${filter ? ' ' + filter : ''}` : filter;
  let tf = `scale(${k})`, to = origin, zs = k;
  if (zoom !== undefined && first !== undefined && t >= first) {
    const u: Box = [Math.min(...marks.map((m) => m.box[0])), Math.min(...marks.map((m) => m.box[1])), 0, 0];
    u[2] = Math.max(...marks.map((m) => m.box[0] + m.box[2])) - u[0];
    u[3] = Math.max(...marks.map((m) => m.box[1] + m.box[3])) - u[1];
    // the push stops where the zoom starts (a live clip's push too: the zoom and its drift carry the camera from there)
    const k0 = interpolate(heldT(first, hold), [0, Math.max(0.01, d)], push, clamp);
    const z = zoomMove(t, first, d, zoom, u, k0, originPx(origin));
    tf = `translate(${z.tx}px, ${z.ty}px) scale(${z.s})`;
    to = '0 0';
    zs = z.s;
  }
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      {lift ? <LiftFilter /> : null}
      <AbsoluteFill style={{transform: tf, transformOrigin: to}}>
        <Hold at={hold}><Clip src={clip} start={start} filter={f} /></Hold>
        {blurs.map(([x, y, w, h], i) => (
          <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 6, backdropFilter: 'blur(14px)'}} />
        ))}
        {marks.length ? <PicMarks marks={marks} sc={1} ox={0} oy={0} W={DS.W} H={DS.H} look={look} zs={zs} /> : null}
      </AbsoluteFill>
      {children}
      <Credit pic={credit} />
    </AbsoluteFill>
  );
};

export const Still: React.FC<{src: string; d: number; push?: [number, number]; origin?: string; region?: Box; from?: Box; marks?: FrameMark[]; look?: 'box' | 'spot';
  names?: {text: string; x: number; y: number; at: number}[]; icons?: {src: string; x: number; y: number; at: number; d?: number}[];
  bars?: [number, number]; maxScale?: number; upscaleOk?: string; credit?: string; children?: React.ReactNode}> = ({src, d, push = [1.0, 1.04],
  origin = '50% 50%', region, from, marks = [], look = 'spot', names = [], icons = [], bars, maxScale = 1.3, upscaleOk, credit, children}) => {
  const t = useT();
  const boxes = useImgBoxes([src]);
  const sides = useIconSides(icons.map((c) => c.src));
  if (!boxes || !sides) return <AbsoluteFill style={{background: '#000'}} />;
  const {iw, ih} = boxes[0];
  const hold = marks.length ? markStart(Math.min(...marks.map((m) => m.at))) : undefined;
  const R0: Box = region ?? [0, 0, iw, ih];
  refuse(`Still ${src}`, frameMarkVerdict(d, [iw, ih], marks, 'Still'));
  refuse(`Still ${src}`, icons.flatMap((c, i) => iconVerdict(c.src, sides[i])));
  // the camera: a glide from `from` onto the region (done 0.02 s before the first light), or the region with a linear push
  const g = from ? moveP(heldT(t, hold), 0, Math.max(0.04, (hold ?? d) - 0.02)) : 1;
  const R = from ? (R0.map((v, i) => from[i] + (v - from[i]) * g) as Box) : R0;
  const [bt, bb] = bars ?? [0, 0];
  const FH = DS.H - bt - bb;
  const sc = Math.max(DS.W / R[2], FH / R[3]);
  if (Math.max(DS.W / R0[2], FH / R0[3]) > maxScale + 1e-6 && !upscaleOk) {
    refuse(`Still ${src}`, [`shown at ${Math.max(DS.W / R0[2], FH / R0[3]).toFixed(2)}x its pixels (over ${maxScale}x: never upscaled). A sharper source, a wider region, or upscaleOk="why"`]);
  }
  const k = from ? 1 : interpolate(heldT(t, hold), [0, Math.max(0.01, d)], push, clamp);
  const ox = R[0] - (DS.W / sc - R[2]) / 2, oy = R[1] - (FH / sc - R[3]) / 2;   // the picture px at the frame's top-left
  return (
    <AbsoluteFill style={{background: '#000', overflow: 'hidden'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: bt, height: FH, overflow: 'hidden'}}>
        <AbsoluteFill style={{transform: `scale(${k})`, transformOrigin: origin}}>
          {/* the picture at its own px under ONE transform (nothing shakes: a picture placed per frame at fractional left/top/width
              snaps each edge on its own frame, so a glide steps in whole pixels) */}
          <Img src={url(src)} style={{position: 'absolute', left: 0, top: 0, width: iw, height: ih, maxWidth: 'none', transformOrigin: '0 0',
            transform: `translate(${-ox * sc}px, ${-oy * sc}px) scale(${sc})`}} />
          {marks.length ? <PicMarks marks={marks} sc={sc} ox={ox} oy={oy} W={DS.W} H={FH} look={look} src={src} /> : null}
          {names.map((n, i) => (
            <div key={`n${i}`} style={{position: 'absolute', left: 0, top: 0, transform: `translate(${(n.x - ox) * sc}px, ${(n.y - oy) * sc}px) translateX(-50%)`}}>
              <Enter at={n.at} dy={0}><Tag>{n.text}</Tag></Enter>
            </div>
          ))}
          {icons.map((c, i) => {
            const D = c.d ?? 132;
            return (
              <div key={`c${i}`} style={{position: 'absolute', left: 0, top: 0, width: D, height: D,
                transform: `translate(${(c.x - ox) * sc - D / 2}px, ${(c.y - oy) * sc - D / 2}px)`}}>
                <Enter at={c.at} dy={0}>
                  <Img data-gate="icon" src={url(c.src)} style={{width: D, height: D, borderRadius: '50%', border: `4px solid ${DS.INK}`, boxSizing: 'border-box',
                    boxShadow: '0 10px 28px rgba(0,0,0,0.5)', display: 'block'}} />
                </Enter>
              </div>
            );
          })}
        </AbsoluteFill>
      </div>
      {children}
      <Credit pic={credit} />
    </AbsoluteFill>
  );
};

export const Burst: React.FC<{d: number; clips: string[]; cuts: number[]; push?: [number, number]; credit?: string}> = ({d, clips, cuts,
  push = [1.0, 1.02], credit}) => (
  <AbsoluteFill style={{background: '#000'}}>
    {clips.map((n, i) => {
      const a = i === 0 ? 0 : cuts[i - 1];
      const b = i < cuts.length ? cuts[i] : d;
      const from = Math.round(a * FPS);
      const len = i < cuts.length ? Math.max(1, Math.round(b * FPS) - from) : Infinity;
      return (
        <Sequence key={`${n}${i}`} from={from} durationInFrames={len}>
          <Foot clip={n} d={b - a} push={push} />
        </Sequence>
      );
    })}
    <Credit pic={credit} />
  </AbsoluteFill>
);

// the picture of a shot: one clip, a still, or a burst
type Pic = {clip?: string; img?: string; clips?: string[]; cuts?: number[]; d: number; push?: [number, number]; start?: number; origin?: string;
  blurs?: Box[]};
const Picture: React.FC<Pic> = ({clip, img, clips, cuts, d, push, start, origin, blurs}) => (clips && cuts
  ? <Burst d={d} clips={clips} cuts={cuts} push={push} />
  : clip ? <Foot clip={clip} d={d} push={push} start={start} origin={origin} blurs={blurs} />
  : <Still src={img as string} d={d} push={push} origin={origin} />);

export const TagShot: React.FC<Pic & {tag: string; tagAt: number; left?: boolean; on?: [number, number]; credit?: string}> = ({tag, tagAt, left,
  on, credit, ...pic}) => (
  <AbsoluteFill>
    <Picture {...pic} />
    <div style={on ? {position: 'absolute', left: on[0], top: on[1], transform: 'translateX(-50%)'}
      : {position: 'absolute', ...(left ? {left: DS.MX} : {right: DS.MX}), top: DS.TOP}}>
      <Enter at={tagAt}><Tag>{tag}</Tag></Enter>
    </div>
    <Credit pic={credit} />
  </AbsoluteFill>
);

export const StampShot: React.FC<Pic & {stampAt: number; text: string; lead?: string; credit?: string}> = ({stampAt, text, lead, credit, ...pic}) => (
  <AbsoluteFill>
    <Picture {...pic} />
    <Stamp at={stampAt} lead={lead} text={text} />
    <Credit pic={credit} />
  </AbsoluteFill>
);

export const TypedShot: React.FC<Pic & {text: string; keys: number[]; credit?: string}> = ({text, keys, credit, ...pic}) => (
  <AbsoluteFill>
    <Picture {...pic} />
    <TypedLine lines={[text]} keys={keys} d={pic.d} />
    <Credit pic={credit} />
  </AbsoluteFill>
);
