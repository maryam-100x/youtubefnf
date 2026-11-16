// The Shorts kit's paper look (the pieces kitFlash.tsx, kitCards.tsx and kitS.tsx use): type sits straight on the footage, and anything
// that is a "card" is a real object (paper, a photo print, a price tag, a product box), never a generic dark card on a tinted void.
//   SHADOW / SHADOW_LIFT  a sheet's shadow: a tight contact shadow plus a soft cast shadow (Material: dark shadows express elevation)
//   PhotoPrint            a photo print with a white border (polaroid strip for a caption)
//   settle                the curve objects land on
import React from 'react';
import {Img, interpolate, staticFile} from 'remotion';
import {clamp, INK} from '../lib';

export const SHADOW = '0 1px 2px rgba(0,0,0,0.35), 0 18px 36px rgba(0,0,0,0.42), 0 46px 90px rgba(0,0,0,0.28)';
export const SHADOW_LIFT = '0 2px 3px rgba(0,0,0,0.35), 0 30px 56px rgba(0,0,0,0.5), 0 70px 120px rgba(0,0,0,0.32)';

// paper fibre: a static fractal noise multiplied over the sheet (seeded, so it doesn't crawl)
const Fibre: React.FC<{w: number; h: number; o?: number}> = ({w, h, o = 0.13}) => (
  <svg width={w} height={h} style={{position: 'absolute', inset: 0, mixBlendMode: 'multiply', opacity: o, pointerEvents: 'none'}}>
    <filter id="fibre">
      <feTurbulence type="fractalNoise" baseFrequency="0.9 0.55" numOctaves="4" seed="7" />
      <feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.56  0 0 0 0 0.52  0 0 0 0.9 0" />
    </filter>
    <rect width={w} height={h} filter="url(#fibre)" />
  </svg>
);

// a photo print: the picture inside a white border; `strip` makes a polaroid-style bottom strip for a caption
export const PhotoPrint: React.FC<{src: string; w: number; img: number; border?: number; strip?: number; caption?: React.ReactNode; fit?: 'cover' | 'contain'; pos?: string;
  style?: React.CSSProperties; imgFilter?: string; overlay?: React.ReactNode; lift?: number}> = ({src, w, img, border = 26, strip = 0, caption, fit = 'cover', pos, style, imgFilter, overlay, lift = 0}) => (
  <div style={{position: 'relative', width: w, padding: border, paddingBottom: strip || border, background: INK, borderRadius: 4, boxShadow: lift > 0.5 ? SHADOW_LIFT : SHADOW, ...style}}>
    <div style={{position: 'relative', width: w - 2 * border, height: img, overflow: 'hidden', borderRadius: 2, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.12)'}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: fit, objectPosition: pos, filter: imgFilter}} />
      {overlay}
    </div>
    {strip ? <div style={{position: 'absolute', left: border, right: border, bottom: 0, height: strip, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{caption}</div> : null}
    <Fibre w={w} h={img + border + (strip || border)} o={0.08} />
  </div>
);

// a spring-like settle for objects landing (fast, a small overshoot; Material 3's "fast spatial" curve, 9% overshoot)
export const settle = (t: number, at: number, dur = 0.42) => interpolate(t, [at, at + dur], [0, 1], {...clamp, easing: (x) => {
  const c1 = 1.70158 * 1.15, c3 = c1 + 1;
  return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2);
}});
