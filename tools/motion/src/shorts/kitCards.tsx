// The pieces of the Shorts' house look: the picture fills the frame, captions dead centre, receipts in a browser window above them with
// their own words marked on the voice's, numbers below the captions as big Anton type inside x 180-900 (the like column starts at x 900,
// tools/footage/phone_view.py). Zones: nothing above y 260; the upper asset y 290-880; the captions ~y 910-1010; the numbers y 1080-1410.
import React from 'react';
import {AbsoluteFill, Img, Internals, OffthreadVideo, staticFile, useCurrentFrame} from 'remotion';
import {ACCENT, ANTON, easeInOut, fitClip, FPS, kf, useT} from '../lib';
import {settle, SHADOW_LIFT} from './look';
import {Box, FULL, M, place} from './kitFlash';

export type Shot = {src: string; iw: number; ih: number};
export type R = [number, number, number, number]; // x, y, w, h in the file's pixels
export const BW = 940, BX = 70; // the browser window: width, left (centred on x 540)

// a clip at a speed in a cover-fitted box: never past its last good frame, never slowed to fill, logging for qa_clips.py
export const Clip: React.FC<{m: M; start: number; rate?: number; box?: Box; fx?: number; fx1?: number; fy?: number; s0?: number; s1?: number; dur?: number; filter?: string}> = ({
  m, start, rate = 1, box = FULL, fx = 0.5, fx1, fy = 0.5, s0 = 1, s1 = 1, dur = 3, filter,
}) => {
  const t = useT();
  const seq = React.useContext(Internals.SequenceContext);
  const abs = Internals.useAbsoluteTimelinePosition();
  const fr = useCurrentFrame();
  const fit = fitClip(m.src, start, rate, seq ? seq.durationInFrames / FPS : null, 1.0); // never slowed to fill (a slowed clip reads as slow motion)
  if (typeof window !== 'undefined' && (window as unknown as {process?: {env?: Record<string, string>}}).process?.env?.REMOTION_CLIP_AUDIT === '1') {
    console.log(`CLIPAUDIT|${abs}|${m.src}|${(Math.round(fit.start * FPS) / FPS + (fr / FPS) * fit.rate).toFixed(3)}`);
    return null;
  }
  const {left, top, dw, dh} = place(m, box, {fx, fx1, fy, s0, s1, dur, ease: (x) => x}, t); // fx1: a pan to it over dur
  return (
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, overflow: 'hidden', background: '#05090a'}}>
      <OffthreadVideo src={staticFile(m.src)} startFrom={Math.round(fit.start * FPS)} playbackRate={fit.rate} muted
        style={{position: 'absolute', left, top, width: dw, height: dh, filter}} />
    </div>
  );
};

export const SHADE = 'linear-gradient(180deg, rgba(0,0,0,0.38) 0%, rgba(0,0,0,0.12) 34%, rgba(0,0,0,0.12) 62%, rgba(0,0,0,0.38) 100%)';
// footage, the whole frame, a soft darkening at the top and bottom
export const Full: React.FC<{m: M; start?: number; rate?: number; fx?: number; dur: number; filter?: string; push?: boolean}> = ({m, start = 0, rate = 1, fx = 0.5, dur, filter, push = true}) => (
  <>
    <Clip m={m} start={start} rate={rate} fx={fx} s0={1.0} s1={push ? 1.05 : 1.0} dur={dur} filter={filter} />
    <AbsoluteFill style={{background: SHADE}} />
  </>
);
// a still photo, the whole frame, a slow push (s1: the push's end scale; a 6% push over a 2-s slot reads as a frozen picture to
// qa_render.py, standard/SHORTS.md "a 5% push read as frozen"; receipts push 13%)
export const Still: React.FC<{m: M; fx?: number; fy?: number; dur: number; filter?: string; s1?: number}> = ({m, fx = 0.5, fy = 0.5, dur, filter, s1 = 1.06}) => {
  const t = useT();
  const {left, top, dw, dh} = place(m, FULL, {fx, fy, s0: 1.0, s1, dur, ease: (x) => x}, t);
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: '#05090a'}}>
      <Img src={staticFile(m.src)} style={{position: 'absolute', left, top, width: dw, height: dh, maxWidth: 'none', filter}} />
      <AbsoluteFill style={{background: SHADE}} />
    </AbsoluteFill>
  );
};

// a region of a screenshot, `k` px per image px: `marks` sweep the accent highlighter over the page's own words from their time (dark
// print on light: multiply; light print on dark: the glyphs inverted dark on the accent). No camera moves: a zoom cut whole lines at the window's edges
export const Page: React.FC<{shot: Shot; c: R; k: number; dark?: boolean; marks?: [R, number][]}> = ({shot, c, k, dark, marks = []}) => {
  const t = useT();
  const W = c[2] * k, H = c[3] * k;
  return (
    <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: dark ? '#121212' : '#ffffff'}}>
      <Img src={staticFile(shot.src)} style={{position: 'absolute', left: -c[0] * k, top: -c[1] * k, width: shot.iw * k, height: shot.ih * k, maxWidth: 'none'}} />
      {marks.map(([m, at], i) => {
        const p = kf(t, [[at, 0], [at + 0.32, 1]], easeInOut);
        if (p <= 0) return null;
        const box = {position: 'absolute' as const, left: (m[0] - c[0] - 6) * k, top: (m[1] - c[1] - 3) * k, width: (m[2] + 12) * k * p, height: (m[3] + 6) * k,
          overflow: 'hidden', borderRadius: 5 * k};
        return dark ? (
          <div key={i} style={box}>
            <Img src={staticFile(shot.src)} style={{position: 'absolute', left: -(m[0] - 6) * k, top: -(m[1] - 3) * k, width: shot.iw * k, height: shot.ih * k,
              maxWidth: 'none', filter: 'invert(1) grayscale(1) contrast(1.6)'}} />
            <div style={{position: 'absolute', inset: 0, background: ACCENT, mixBlendMode: 'multiply'}} />
          </div>
        ) : <div key={i} style={{...box, background: ACCENT, mixBlendMode: 'multiply'}} />;
      })}
    </div>
  );
};

// a browser window: three dots, the address blurred, a tag (the source); settling in from below at `at` (none: already there)
export const Browser: React.FC<{top: number; at?: number; tag?: string; children: React.ReactNode}> = ({top, at, tag, children}) => {
  const t = useT();
  const e = at === undefined ? 1 : settle(t, at, 0.42);
  return (
    <div style={{position: 'absolute', left: BX, top, width: BW, borderRadius: 16, overflow: 'hidden', boxShadow: SHADOW_LIFT, background: '#1c1f26',
      opacity: Math.min(1, e * 1.4), transform: `translateY(${(1 - e) * 70}px)`}}>
      <div style={{height: 58, display: 'flex', alignItems: 'center', padding: '0 20px', gap: 11, background: '#2a2e36'}}>
        {['#ff5f57', '#febc2e', '#28c840'].map((col) => <div key={col} style={{width: 17, height: 17, borderRadius: 9, background: col}} />)}
        <div style={{marginLeft: 16, flex: 1, height: 36, borderRadius: 18, background: '#1c1f26', display: 'flex', alignItems: 'center', padding: '0 18px'}}>
          <div style={{width: 220, height: 13, borderRadius: 7, background: '#59606e', filter: 'blur(4px)'}} />
        </div>
        {tag ? <div style={{marginLeft: 10, padding: '4px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.85)',
          fontFamily: 'Inter, Arial, sans-serif', fontSize: 18, letterSpacing: 0.5, whiteSpace: 'nowrap'}}>{tag}</div> : null}
      </div>
      {children}
    </div>
  );
};

// a number below the captions: Anton, a shadow, settling in at `at` (at < 0: already there); long ones at 145 px to stay inside x 180-900
export const Num: React.FC<{text: string; at: number; size?: number; color?: string}> = ({text, at, size = 210, color = '#FFFFFF'}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const p = settle(t, at, 0.36);
  return (
    <div style={{position: 'absolute', left: 0, width: 1080, top: 1080, height: 330, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontFamily: ANTON, fontSize: size, lineHeight: 1, color, transform: `scale(${0.6 + 0.4 * p})`, opacity: Math.min(1, p * 2),
        textShadow: '0 8px 30px rgba(0,0,0,0.65), 0 2px 4px rgba(0,0,0,0.5)'}}>{text}</div>
    </div>
  );
};

// a source credit for others' footage, small, top left under the icon row
export const Credit: React.FC<{text: string}> = ({text}) => (
  <div data-gate="credit" style={{position: 'absolute', left: 36, top: 270, padding: '5px 11px 6px', background: 'rgba(0,0,0,0.45)', borderRadius: 5, fontFamily: 'Inter, Arial, sans-serif',
    fontWeight: 500, fontSize: 21, color: 'rgba(255,255,255,0.92)', whiteSpace: 'nowrap'}}>{text}</div>
);
