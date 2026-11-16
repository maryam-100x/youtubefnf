// The Shorts kit's framing and object helpers (kitS.tsx builds on them): media, cover-fitted pictures with a camera move, prints, the
// opening flash. Bands (the house captions at y ~1018-1100): TOP y 272-975, BOT y 1143-1846; nothing above y 260; one focal thing
// centred on x 540.
import React from 'react';
import {AbsoluteFill, Img, Internals, interpolate, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {gateLog, gateOn} from '../gate';
import {clamp, clipFps, easeIn, easeInOut, easeOut, fitClip, FPS, INK, kf, PAPER, useT} from '../lib';
import {PhotoPrint, SHADOW_LIFT, settle} from './look';

export type M = {src: string; iw: number; ih: number; video?: boolean};
export const img = (src: string, iw: number, ih: number): M => ({src, iw, ih});
export const vid = (src: string, iw = 3840, ih = 2160): M => ({src, iw, ih, video: true});

// ---------------------------------------------------------------------------------------------------------------- framing
export type Box = {x: number; y: number; w: number; h: number};
export const FULL: Box = {x: 0, y: 0, w: 1080, h: 1920};
// the split's panels: the same size, evenly around the measured caption box (y 1014-1119), nothing above y 272 (YouTube's icon row)
export const TOP: Box = {x: 0, y: 272, w: 1080, h: 703};
export const BOT: Box = {x: 0, y: 1143, w: 1080, h: 703};

export type Frame = {fx?: number; fy?: number; fx1?: number; fy1?: number; s0?: number; s1?: number; t0?: number; dur?: number; ease?: (x: number) => number;
  scale?: (t: number) => number; fxf?: (t: number) => number; fyf?: (t: number) => number; path?: number[][]};
// a value through keys (ts, vs) at t: smooth through every key, no overshoot and no stop at a key (monotone cubic, Fritsch-Carlson),
// held before the first key and after the last; two equal keys in a row = a hold, so a move after them starts from rest
export const mono = (ts: number[], vs: number[], t: number) => {
  const n = ts.length;
  if (n === 1 || t <= ts[0]) return vs[0];
  if (t >= ts[n - 1]) return vs[n - 1];
  const d = ts.slice(1).map((x, i) => (vs[i + 1] - vs[i]) / (x - ts[i]));
  const m = vs.map((_, i) => (i === 0 ? d[0] : i === n - 1 ? d[n - 2] : d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2));
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const a = m[i] / d[i], b = m[i + 1] / d[i], q = a * a + b * b;
    if (q > 9) {
      m[i] = (3 / Math.sqrt(q)) * a * d[i];
      m[i + 1] = (3 / Math.sqrt(q)) * b * d[i];
    }
  }
  let i = 0;
  while (t > ts[i + 1]) i++;
  const h = ts[i + 1] - ts[i], u = (t - ts[i]) / h, u2 = u * u, u3 = u2 * u;
  return (2 * u3 - 3 * u2 + 1) * vs[i] + (u3 - 2 * u2 + u) * h * m[i] + (-2 * u3 + 3 * u2) * vs[i + 1] + (u3 - u2) * h * m[i + 1];
};
// where a cover-fitted picture sits in its box at local time t: never past its edges (no black bars), the focus as near the centre as it can.
// path [[t, fx, fy, s?], ...] (local seconds): a camera that follows its subject through the shot (the subject stays centred the whole
// time), placed key by key on frame_review_at.py's --cols sheet; without s the push s0 -> s1 runs
export const place = (m: M, box: Box, fr: Frame, t: number) => {
  const p = interpolate(t, [fr.t0 ?? 0, (fr.t0 ?? 0) + (fr.dur ?? 3)], [0, 1], {...clamp, easing: fr.ease ?? easeInOut});
  const pk = fr.path && fr.path.length ? fr.path : null, ts = pk ? pk.map((k) => k[0]) : [];
  const s = pk && pk.every((k) => k.length > 3) ? mono(ts, pk.map((k) => k[3]), t)
    : fr.scale ? fr.scale(t) : (fr.s0 ?? 1) + ((fr.s1 ?? fr.s0 ?? 1) - (fr.s0 ?? 1)) * p;
  const fx = pk ? mono(ts, pk.map((k) => k[1]), t) : fr.fxf ? fr.fxf(t) : (fr.fx ?? 0.5) + ((fr.fx1 ?? fr.fx ?? 0.5) - (fr.fx ?? 0.5)) * p;
  const fy = pk ? mono(ts, pk.map((k) => k[2]), t) : fr.fyf ? fr.fyf(t) : (fr.fy ?? 0.5) + ((fr.fy1 ?? fr.fy ?? 0.5) - (fr.fy ?? 0.5)) * p;
  const k = Math.max(box.w / m.iw, box.h / m.ih) * s;
  const dw = m.iw * k, dh = m.ih * k;
  const left = Math.min(0, Math.max(box.w - dw, box.w / 2 - fx * dw));
  const top = Math.min(0, Math.max(box.h - dh, box.h / 2 - fy * dh));
  return {left, top, dw, dh};
};

// a video never runs past its last frame (lib fitClip), and logs for qa_clips.py like lib's Clip. floor: the slowest it may play to
// fill its scene (default 24 distinct frames a second); lower only for a shot that barely moves (a skyline panning 0.3 px a frame at
// 1080p shows no judder at 0.37x)
export const Media: React.FC<{m: M; start?: number; w: number; h: number; floor?: number}> = ({m, start = 0, w: ww, h, floor}) => {
  const seq = React.useContext(Internals.SequenceContext);
  const abs = Internals.useAbsoluteTimelinePosition();
  const fr = useCurrentFrame();
  if (!m.video) return <Img src={staticFile(m.src)} style={{width: ww, height: h, display: 'block'}} />;
  const fit = fitClip(m.src, start, 1, seq ? seq.durationInFrames / FPS : null, floor);
  // the pre-render gate (src/gate.tsx): every Short's clips go through here (kitS Pic -> Cover -> Media), not lib's Clip
  if (gateOn) {
    gateLog('clip', {abs, src: m.src, f: fr, s: Math.round(fit.start * FPS) / FPS + (fr / FPS) * fit.rate, start: fit.start, rate: fit.rate,
      s0: start, r0: 1, dur: seq ? seq.durationInFrames : null, fits: fit.fits});
    return <div data-gateclip={m.src} style={{width: ww, height: h, display: 'block'}}><div style={{width: '100%', height: '100%'}} /></div>;
  }
  if (typeof window !== 'undefined' && (window as unknown as {process?: {env?: Record<string, string>}}).process?.env?.REMOTION_CLIP_AUDIT === '1') {
    console.log(`CLIPAUDIT|${abs}|${m.src}|${(Math.round(fit.start * FPS) / FPS + (fr / FPS) * fit.rate).toFixed(3)}`);
    return null;
  }
  return <OffthreadVideo src={staticFile(m.src)} startFrom={Math.round(fit.start * FPS)} playbackRate={fit.rate} muted style={{width: ww, height: h, display: 'block'}} />;
};

// a picture or clip filling its box (default: the whole frame), with a camera move; `over` draws in the picture's own pixel space
// (fractions of its width/height), so a callout moves with the push
// lock (a clip whose own camera moves): the window moves only when the clip's frame changes. A 30-fps clip in a 60-fps Short shows each
// frame twice; a window moving every frame over a picture moving every second frame twitches back and forth (the shift goes -3, +5,
// -3, +5 px a frame). The frame shown is floor(media time x fps), media time = startFrom / FPS + t x rate (qa_jitter.py measures it on a
// render: a 2.96-px zig-zag drops to 0.06 px). true = the clip's fps
// from clipdurs.json (30 when unknown)
export const Cover: React.FC<{m: M; start?: number; box?: Box; filter?: string; over?: React.ReactNode; floor?: number; lock?: boolean | number} & Frame> = ({m, start, box = FULL,
  filter, over, floor, lock, ...fr}) => {
  const t = useT();
  const seq = React.useContext(Internals.SequenceContext);
  let tw = t;
  if (lock && m.video) {
    const fit = fitClip(m.src, start ?? 0, 1, seq ? seq.durationInFrames / FPS : null, floor);
    const fps = typeof lock === 'number' ? lock : clipFps(m.src) ?? 30;
    const sf = Math.round(fit.start * FPS) / FPS;
    tw = Math.max(0, (Math.floor((sf + t * fit.rate) * fps + 1e-6) / fps - sf) / fit.rate);
  }
  const {left, top, dw, dh} = place(m, box, fr, tw);
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, overflow: 'hidden', background: '#05090a'}}>
      <div style={{position: 'absolute', left, top, width: dw, height: dh, filter}}>
        <Media m={m} start={start} w={dw} h={dh} floor={floor} />
      </div>
      {over ? <div style={{position: 'absolute', left, top, width: dw, height: dh}}>{over}</div> : null}
    </div>
  );
};

// the same picture blurred behind a graphic: overscaled so the blur's soft rim falls outside the frame (else a dark rim shows)
export const Back: React.FC<{m: M; start?: number; blur?: number; dim?: number; sat?: number; fx?: number; fy?: number; s0?: number; s1?: number; dur?: number}> = ({
  m, start, blur = 24, dim = 0.5, sat = 1.1, fx = 0.5, fy = 0.5, s0 = 1.0, s1 = 1.06, dur = 4,
}) => {
  const pad = blur * 3;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#05090a'}}>
      <Cover m={m} start={start} box={{x: -pad, y: -pad, w: 1080 + 2 * pad, h: 1920 + 2 * pad}} fx={fx} fy={fy} s0={s0} s1={s1} dur={dur} ease={(x) => x}
        filter={`blur(${blur}px) brightness(${dim}) saturate(${sat})`} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, rgba(5,12,14,0) 30%, rgba(5,12,14,0.5) 100%)'}} />
    </AbsoluteFill>
  );
};

// a slow push on a group of objects (never a static screen), around (540, cy)
export const Drift: React.FC<{amt: number; dur: number; cy: number; children: React.ReactNode}> = ({amt, dur, cy, children}) => {
  const t = useT();
  return <AbsoluteFill style={{transform: `scale(${1 + amt * Math.min(1, t / dur)})`, transformOrigin: `540px ${cy}px`}}>{children}</AbsoluteFill>;
};

// a quick punch on a hit word: the picture snaps 1 -> 1+amt in 0.18 s (ease-out) and holds (a "drop zoom")
export const punch = (t: number, at: number, base: (t: number) => number, amt = 0.16) => base(t) * (1 + amt * kf(t, [[at, 0], [at + 0.18, 1]], easeOut));
export const drift = (a: number, b: number, d: number) => (t: number) => a + (b - a) * Math.min(1, Math.max(0, t / d));

// ---------------------------------------------------------------------------------------------------------------- objects
// a photo print landing centred on (x, y): drops from 1.3x with a small overshoot (look.tsx settle), or slides in
export const Print: React.FC<{src: string; at: number; x: number; y: number; w: number; img: number; rot?: number; pos?: string; out?: number; border?: number;
  from?: 'drop' | 'up' | 'down' | 'left' | 'right'; lift?: number; scale?: number}> = ({
  src, at, x, y, w: pw, img: ih, rot = 0, pos, out = 999, border = 20, from = 'drop', lift = 0, scale = 1,
}) => {
  const t = useT();
  if (t < at - 0.01 || t > out + 0.3) return null;
  const p = from === 'drop' ? settle(t, at, 0.38) : kf(t, [[at, 0], [at + 0.34, 1]], easeOut);
  const o = kf(t, [[at, 0], [at + 0.08, 1]], easeOut) * (t > out ? 1 - kf(t, [[out, 0], [out + 0.25, 1]], easeIn) : 1);
  const d = 1 - p;
  const tx = from === 'left' ? -900 * d : from === 'right' ? 900 * d : 0;
  const ty = from === 'up' ? -700 * d : from === 'down' ? 900 * d : 0;
  const sc = (from === 'drop' ? 1 + 0.15 * d : 1) * scale;
  const h = ih + 2 * border;
  return (
    <div style={{position: 'absolute', left: x - pw / 2, top: y - h / 2, width: pw, opacity: o,
      transform: `translate(${tx}px, ${ty}px) rotate(${rot}deg) scale(${sc})`}}>
      <PhotoPrint src={src} w={pw} img={ih} border={border} pos={pos} lift={lift} />
    </div>
  );
};

// a product's cover (a book, a boxed product), centred on x (rounded, the kit's shadow), popping in; `fly` sends it up and out
export const BoxArt: React.FC<{src: string; at: number; x?: number; y: number; w: number; rot?: number; fly?: number}> = ({src, at, x = 540, y, w: cw, rot = 0, fly = 999}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const p = settle(t, at, 0.36);
  const f = kf(t, [[fly, 0], [fly + 0.3, 1]], easeIn);
  const ch = cw * 1.5;
  return (
    <div style={{position: 'absolute', left: x - cw / 2, top: y - ch / 2, width: cw, height: ch, borderRadius: 16, overflow: 'hidden',
      opacity: kf(t, [[at, 0], [at + 0.07, 1]], easeOut) * (1 - f), boxShadow: SHADOW_LIFT,
      transform: `translateY(${-1300 * f}px) rotate(${rot}deg) scale(${1 + 0.35 * (1 - p)})`}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  );
};

// a speech bubble with a voice waveform (the same line, every time); `tail` points down-left or down-right
export const BARS = [0.35, 0.7, 0.5, 1, 0.62, 0.85, 0.42, 0.75, 0.3];
export const Bubble: React.FC<{at: number; x: number; y: number; s?: number; tail?: 'l' | 'r'; rot?: number; out?: number}> = ({at, x, y, s = 1, tail = 'l', rot = 0, out = 999}) => {
  const t = useT();
  if (t < at - 0.01 || t > out + 0.1) return null;
  const sc = (t < at + 0.1 ? kf(t, [[at, 0.2], [at + 0.1, 1.12]], easeOut) : kf(t, [[at + 0.1, 1.12], [at + 0.2, 1]], easeInOut)) *
    (t >= out ? 1 - kf(t, [[out, 0], [out + 0.1, 1]], easeIn) : 1);
  const bw = 250, bh = 128;
  return (
    <div style={{position: 'absolute', left: x - bw / 2, top: y - bh / 2, width: bw, height: bh, transform: `rotate(${rot}deg) scale(${s * sc})`,
      transformOrigin: tail === 'l' ? '20% 120%' : '80% 120%', filter: 'drop-shadow(0 3px 3px rgba(0,0,0,0.3)) drop-shadow(0 14px 22px rgba(0,0,0,0.4))'}}>
      <svg width={bw} height={bh + 34} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <rect x={0} y={0} width={bw} height={bh} rx={52} fill={INK} />
        <path d={tail === 'l' ? `M 52 ${bh - 8} L 30 ${bh + 32} L 96 ${bh - 4} Z` : `M ${bw - 52} ${bh - 8} L ${bw - 30} ${bh + 32} L ${bw - 96} ${bh - 4} Z`} fill={INK} />
        {BARS.map((v, i) => {
          const bx = 44 + i * 20.5, bhh = 18 + 58 * v;
          return <rect key={i} x={bx} y={bh / 2 - bhh / 2} width={11} height={bhh} rx={5.5} fill={PAPER} />;
        })}
      </svg>
    </div>
  );
};

// the opening flash: from white over the first 0.25 s, with its sound (every Short opens on it)
export const FlashIn: React.FC = () => {
  const t = useT();
  const o = kf(t, [[0, 1], [0.25, 0]], (x) => x);
  return o > 0 ? <AbsoluteFill style={{background: `rgba(255,255,255,${o})`}} /> : null;
};

// cinema bars (the "main character" moment); they stay clear of the captions (y 1018-1100)
export const Bars: React.FC<{at: number; h?: number}> = ({at, h = 170}) => {
  const t = useT();
  const p = kf(t, [[at, 0], [at + 0.32, 1]], easeOut);
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: h * p, background: 'black'}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: h * p, background: 'black'}} />
    </AbsoluteFill>
  );
};

// a coloured flash over the frame (the refs' colour-flash on a hit word): on in one frame, gone in 0.3 s
export const Tint: React.FC<{at: number; color: string; max?: number}> = ({at, color, max = 0.45}) => {
  const t = useT();
  const o = interpolate(t, [at - 0.001, at, at + 0.3], [0, max, 0], clamp);
  return o > 0 ? <AbsoluteFill style={{background: color, opacity: o, mixBlendMode: 'screen', pointerEvents: 'none'}} /> : null;
};

