// kit3 · the stage every built graphic stands on, and the frame pieces around it.
//
//   Stage   the ground (the shot's own footage full frame, defocused 8 px, dimmed to 42%; or a still; or plain #050505), a soft vignette,
//           the foreground's ONE camera move (a linear push 1.00 -> 1.03, one way), the credit. `hold` (s): the foreground's push stops
//           there (a page with a mark on it stands still while the mark shows); the ground keeps its own slow push, so the frame never
//           stands wholly still (the gate's STILL) while nothing under a mark moves. The ground mounts at once, measurement or not (the
//           black-frames race, measure.ts). Props: dur, ground? (clip path), start?, img? (still path), dim?, blur?, push?, hold?,
//           credit?, source?, children.
//   Credit  ONE line bottom right on the title-safe corner: "whose picture  ·  Source: where the number comes from" (data-gate="credit")
//   Split   a group centred in the content box by its real widths (flexbox: never a hand-set `left:`). Props: gap? (96), column?, align?
//   Enter   any block's entrance on its word (rise 32 px + fade, EASE.enter) and optional exit. Props: at?, d?, dy?, dx?, out?
//   Card    the one card (surface 88%, radius 12, the one shadow, no border). Props: w?, pad? ([40, 48]), at?, out?
//   Hold    a clip frozen from `at` (the shot's seconds) on: <Freeze> (remotion.dev/docs/freeze: video inside is paused)
//   hasClip / needClip   a clip is in src/clipdurs.json (measured, so lib.tsx's fitClip keeps it inside its file: gate B1 FREEZE);
//           a clip that isn't shows "pending" in the Studio and FAILS any render (stills, the gate's probe, the render)
import React from 'react';
import {AbsoluteFill, Freeze, Img, getRemotionEnvironment, interpolate} from 'remotion';
import {Clip, FPS, clamp, useT} from '../lib';
import durs from '../clipdurs.json';
import {DS, enterP, enterStyle, exitP, heldT, type} from './tokens';
import {INK_RGB} from '../brand';
import {url} from './measure';

export const hasClip = (path: string) => path in (durs as Record<string, unknown>);
export const Pending: React.FC<{what: string}> = ({what}) => {
  if (getRemotionEnvironment().isRendering) {
    throw new Error(`kit3: ${what} is not in src/clipdurs.json (cut it with its prep script, which measures it): no pending box in a render`);
  }
  return (
    <AbsoluteFill style={{background: '#202020', alignItems: 'center', justifyContent: 'center', ...type('label', '#888')}}>pending: {what}</AbsoluteFill>
  );
};

export const Hold: React.FC<{at?: number; children: React.ReactNode}> = ({at, children}) => {
  if (at === undefined) return <>{children}</>;
  const F = Math.max(0, Math.round(at * FPS));
  return <Freeze frame={F} active={(fr) => fr >= F}>{children}</Freeze>;
};

export const Credit: React.FC<{pic?: string; source?: string}> = ({pic, source}) => {
  const text = [pic, source ? `Source: ${source}` : ''].filter(Boolean).join('  ·  ');
  if (!text) return null;
  return (
    <div data-gate="credit" style={{position: 'absolute', right: DS.SAFE_X, bottom: DS.SAFE_Y, padding: '4px 12px', borderRadius: DS.R_CHIP,
      background: 'rgba(0,0,0,0.5)', whiteSpace: 'nowrap', ...type('meta', `rgba(${INK_RGB},0.8)`)}}>{text}</div>
  );
};

export const Stage: React.FC<{dur: number; ground?: string; start?: number; img?: string; dim?: number; blur?: number;
  push?: [number, number]; hold?: number; credit?: string; source?: string; children?: React.ReactNode}> = ({dur, ground, start = 0, img,
  dim = DS.GROUND.dim, blur = DS.GROUND.blur, push = DS.PUSH, hold, credit, source, children}) => {
  const t = useT();
  const sFg = interpolate(heldT(t, hold), [0, Math.max(0.01, dur)], push, clamp);
  const sBg = interpolate(t, [0, Math.max(0.01, dur)], push, clamp);
  const filter = `${blur ? `blur(${blur}px) ` : ''}brightness(${dim})`;
  // the picture grows 4% (GROUND.scale) the moment blur leaves 0: a blur animated up from 0 jumps the picture on its first non-zero frame;
  // animate `dim`, keep `blur` 0 or fixed for the whole shot
  const grow = blur ? DS.GROUND.scale : 1;
  return (
    <AbsoluteFill style={{background: '#050505', overflow: 'hidden'}}>
      {ground ? (hasClip(ground) ? (
        <AbsoluteFill style={{transform: `scale(${grow * sBg})`}}><Clip src={ground} start={start} filter={filter} /></AbsoluteFill>
      ) : <Pending what={ground} />) : null}
      {img ? (
        <AbsoluteFill style={{transform: `scale(${grow * sBg})`, filter}}>
          <Img src={url(img)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
        </AbsoluteFill>
      ) : null}
      {ground || img ? <AbsoluteFill style={{background: 'radial-gradient(ellipse 80% 80% at 50% 50%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)'}} /> : null}
      <AbsoluteFill style={{transform: `scale(${sFg})`, transformOrigin: `${DS.CX}px ${DS.CY}px`}}>{children}</AbsoluteFill>
      <Credit pic={credit} source={source} />
    </AbsoluteFill>
  );
};

export const Split: React.FC<{children: React.ReactNode; gap?: number; column?: boolean; align?: 'center' | 'flex-start' | 'flex-end';
  style?: React.CSSProperties}> = ({children, gap = DS.S.xxl, column, align = 'center', style}) => (
  <div style={{position: 'absolute', left: DS.MX, right: DS.MX, top: DS.TOP, bottom: DS.H - DS.BOTTOM, display: 'flex',
    flexDirection: column ? 'column' : 'row', alignItems: align, justifyContent: 'center', gap, ...style}}>{children}</div>
);

export const Enter: React.FC<{at?: number; d?: number; dy?: number; dx?: number; out?: number; style?: React.CSSProperties;
  children: React.ReactNode}> = ({at, d = DS.DUR.enter, dy = DS.RISE.text, dx = 0, out, style, children}) => {
  const t = useT();
  return <div style={{...style, ...enterStyle(enterP(t, at, d), dy, dx, exitP(t, out))}}>{children}</div>;
};

export const Card: React.FC<{w?: number; pad?: [number, number]; at?: number; out?: number; style?: React.CSSProperties;
  children: React.ReactNode}> = ({w, pad = [DS.S.l, 48], at, out, style, children}) => {
  const t = useT();
  return (
    <div style={{width: w, padding: `${pad[0]}px ${pad[1]}px`, boxSizing: 'border-box', borderRadius: DS.R, background: DS.SURFACE,
      boxShadow: DS.SHADOW, flex: 'none', ...style, ...enterStyle(enterP(t, at), DS.RISE.text, 0, exitP(t, out))}}>{children}</div>
  );
};
