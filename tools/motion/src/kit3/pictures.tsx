// kit3 · single pictures as blocks in the flow (so Split centres them by what you SEE).
//
//   Cutout      a cut-out PNG as a block the size of its VISIBLE pixels (alpha > 16): its transparent margins take no room, so a group
//               centres on the figure itself (sized by the whole file, a logo with a wide margin sits off centre).
//               Props: src, h (the visible figure's height), w? (or its width), at?, caption? (under it, label, data-gate="name"), shadow?
//   PhotoFrame  a photo whole at its own shape (no crop), radius 12, the card's shadow, never past `maxScale` x its pixels (1.3: never
//               upscaled), caption + muted sub under it. Props: src, h? (640) or w?, caption?, sub?, at?, maxScale?
//   Picture     either one by the file: a .png with transparency is a Cutout, anything else a PhotoFrame (a cut-out never sits on a
//               frame's black box: the gate's CUTOUT_ON_CARD)
import React from 'react';
import {Img} from 'remotion';
import {useT} from '../lib';
import {DS, enterP, enterStyle, type} from './tokens';
import {url, useImgBoxes} from './measure';

export const Cutout: React.FC<{src: string; h?: number; w?: number; at?: number; caption?: React.ReactNode; sub?: string; shadow?: boolean;
  style?: React.CSSProperties}> = ({src, h, w, at, caption, sub, shadow = true, style}) => {
  const t = useT();
  const boxes = useImgBoxes([src]);
  if (!boxes) return null;
  const b = boxes[0];
  const vw = b.x1 - b.x0, vh = b.y1 - b.y0;
  const s = h !== undefined ? h / Math.max(1, vh) : (w ?? 400) / Math.max(1, vw);
  const W = vw * s, H = vh * s;
  return (
    <div data-kit3="cutout" style={{width: W, flex: 'none', ...style, ...enterStyle(enterP(t, at), DS.RISE.cut)}}>
      <div style={{position: 'relative', width: W, height: H}}>
        <Img src={url(src)} style={{position: 'absolute', left: -b.x0 * s, top: -b.y0 * s, width: b.iw * s, height: b.ih * s, maxWidth: 'none',
          filter: shadow ? DS.CUT_SHADOW : undefined}} />
      </div>
      {caption ? <div data-gate="name" style={{...type('label'), marginTop: DS.S.s, textAlign: 'center', whiteSpace: 'nowrap'}}>{caption}</div> : null}
      {sub ? <div style={{...type('label', DS.INK2), marginTop: 2, textAlign: 'center', whiteSpace: 'nowrap'}}>{sub}</div> : null}
    </div>
  );
};

export const PhotoFrame: React.FC<{src: string; h?: number; w?: number; caption?: React.ReactNode; sub?: string; at?: number; maxScale?: number;
  style?: React.CSSProperties}> = ({src, h = 640, w, caption, sub, at, maxScale = 1.3, style}) => {
  const t = useT();
  const boxes = useImgBoxes([src]);
  if (!boxes) return null;
  const {iw, ih} = boxes[0];
  let H = w ? (w * ih) / iw : h;
  H = Math.min(H, ih * maxScale);
  const W = (H * iw) / ih;
  return (
    <div style={{width: W, flex: 'none', ...style, ...enterStyle(enterP(t, at))}}>
      <div style={{width: W, height: H, borderRadius: DS.R, overflow: 'hidden', boxShadow: DS.SHADOW, background: '#000'}}>
        <Img src={url(src)} style={{width: '100%', height: '100%', display: 'block'}} />
      </div>
      {caption ? <div data-gate="name" style={{...type('label'), marginTop: DS.S.s}}>{caption}</div> : null}
      {sub ? <div style={{...type('label', DS.INK2), marginTop: 2}}>{sub}</div> : null}
    </div>
  );
};

export const Picture: React.FC<{src: string; h?: number; at?: number; caption?: React.ReactNode; sub?: string}> = ({src, h = 640, at, caption,
  sub}) => (src.toLowerCase().endsWith('.png')
  ? <Cutout src={src} h={h} at={at} caption={caption} sub={sub} />
  : <PhotoFrame src={src} h={h} at={at} caption={caption} sub={sub} />);
