// The Shorts kit: the pieces each Short acts its lines out with, real pictures and props on their words. Layout per standard/SHORTS.md:
// nothing above y 260, the upper asset in y 290-880, the captions at y ~960 (finish_short.py burns them), props and numbers in y
// 1080-1410, everything inside x 180-900; every full-frame picture framed by hand (fx/fy on its subject); credits small, top left
// (kitCards.tsx).
import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile} from 'remotion';
import {clamp, easeOut, KEY, KEY_RGB, kf, useT} from '../lib';
import {Cover, img, vid} from './kitFlash';
import {Credit, SHADE} from './kitCards';
import {settle} from './look';
import {DISPLAY, TEXT} from '../house/cards';
import {LOOK, TRACK_END} from '../look';

export {img, vid, Credit};
export type Media = ReturnType<typeof img>;

// a film's light over a picture: a colour cast and a vignette in one pass (each Short its own palette)
export const Grade: React.FC<{tint: string; amt?: number}> = ({tint, amt = 0.3}) => (
  <>
    <AbsoluteFill style={{background: tint, mixBlendMode: 'soft-light', opacity: amt}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 45%, rgba(0,0,0,0.6) 100%)'}} />
  </>
);

// two or more credit lines (a photo and a prop in one scene)
export const Credits: React.FC<{lines: string[]}> = ({lines}) => (
  <div data-gate="credit" style={{position: 'absolute', left: 36, top: 270, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 6}}>
    {lines.map((l) => (
      <div key={l} style={{padding: '5px 11px 6px', background: 'rgba(0,0,0,0.45)', borderRadius: 5, fontFamily: TEXT, fontWeight: 500,
        fontSize: 21, color: 'rgba(255,255,255,0.92)', whiteSpace: 'nowrap'}}>{l}</div>
    ))}
  </div>
);

// a prop keeps moving once it has landed (logos, devices and boxes that land and then sit still read as a frozen picture after 0.8-1.2 s):
// 10% a second from 0.3 s after its landing, at most +18% (6% a second still read as near-still on the QA's frame difference: 0.03
// against its 0.35)
export const drift = (t: number, at: number) => 1 + 0.1 * Math.min(1.8, Math.max(0, t - at - 0.3));

// a slow push over a whole scene (k per second)
export const Push: React.FC<{k?: number; origin?: string; children: React.ReactNode}> = ({k = 0.1, origin = '50% 40%', children}) => {
  const t = useT();
  return <AbsoluteFill style={{transform: `scale(${1 + k * t})`, transformOrigin: origin}}>{children}</AbsoluteFill>;
};

// a photo or a frame of footage filling 9:16, framed on its subject, one push (a 13% push over ~2 s moves; 5% reads as frozen);
// fx1/fy1: a pan that follows a subject moving across the frame (else a falling figure leaves the window), placed from
// frame_review_at.py's sheet; path [[t, fx, fy, s?], ...]: a camera that follows its subject key by key (kitFlash place());
// lock: the window steps with the clip's own frames, for a clip whose camera moves (kitFlash Cover)
export const Pic: React.FC<{m: Media; dur: number; fx?: number; fy?: number; fx1?: number; fy1?: number; s0?: number; s1?: number; filter?: string; tint?: string;
  amt?: number; credit?: string; start?: number; path?: number[][]; lock?: boolean | number; own?: boolean}> = ({m, dur, fx = 0.5, fy = 0.45, fx1, fy1, s0 = 1.0, s1 = 1.1, filter,
  tint, amt = 0.25, credit, start, path, lock, own}) => (
  // own: the picture says the words being said (a logo clip, a title card): it owns the caption line, the finish clears the captions
  <AbsoluteFill data-gate={own ? 'stamp' : undefined} style={{background: '#05070a'}}>
    <Cover m={m} start={start} fx={fx} fy={fy} fx1={fx1} fy1={fy1} s0={s0} s1={s1} dur={dur} filter={filter} path={path} lock={lock} />
    <AbsoluteFill style={{background: SHADE}} />
    {tint ? <Grade tint={tint} amt={amt} /> : null}
    {credit ? <Credit text={credit} /> : null}
  </AbsoluteFill>
);

// a picture blurred and dark behind a graphic, so the frame is never empty
export const Blurred: React.FC<{m: Media; fx?: number; fy?: number; start?: number; dim?: number}> = ({m, fx = 0.5, fy = 0.45, start, dim = 0.5}) => (
  <AbsoluteFill style={{opacity: dim}}><Cover m={m} start={start} fx={fx} fy={fy} s0={1.1} s1={1.4} dur={4} filter="blur(26px) brightness(0.5) saturate(0.85)" /></AbsoluteFill>
);

// a ground for a graphic (a receipt, a card, a logo, a cut-out): footage or art of the subject filling 9:16 behind it, half bright and
// moving, so the screen is never a small thing on a plain ground (cards on a flat gradient leave the lower half empty). Never the
// graphic's own picture (no picture on its own blurred copy). Bright enough to count as a picture (the gate's EMPTY: opacity x
// brightness 0.28+; a blurred skyline at 0.4 x 0.5 reads as black)
// credit: the ground is footage on screen, so it's credited like any (the gate's CREDIT); leave it out only when the graphic's own credit names it
export const Back9: React.FC<{m: Media; start?: number; dur: number; fx?: number; fy?: number; dim?: number; path?: number[][]; credit?: string}> = ({m, start, dur,
  fx = 0.5, fy = 0.45, dim = 0.5, path, credit}) => (
  <AbsoluteFill>
    <Cover m={m} start={start} fx={fx} fy={fy} s0={1.04} s1={1.04 + 0.05 * dur} dur={dur} path={path} filter={`blur(2px) brightness(${dim}) saturate(0.9)`} />
    {credit ? <Credit text={credit} /> : null}
  </AbsoluteFill>
);

// a logo or a cut-out landing on its word: drops in and settles (at < 0: already there); y is its centre
// fade: the bottom part of a cut-out (a fraction of its height) melts into the ground, for a bust whose cut edge would show
export const Drop: React.FC<{src: string; at: number; x?: number; y: number; w: number; from?: number; rot?: [number, number]; glow?: string; out?: number; fade?: number}> = ({
  src, at, x = 540, y, w, from = -360, rot = [0, 0], glow, out = 999, fade = 0}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const p = interpolate(t, [Math.max(-1, at - 0.0), at + 0.24], [0, 1], {...clamp, easing: (q) => 1 - Math.pow(1 - q, 3)});
  const bo = t >= at + 0.24 ? 10 * Math.exp(-(t - at - 0.24) * 12) * Math.sin((t - at - 0.24) * 38) : 0;
  const o = Math.min(1, p * 2.5) * (t > out ? Math.max(0, 1 - (t - out) / 0.2) : 1);
  return (
    <Img src={staticFile(src)} style={{position: 'absolute', left: x - w / 2, top: y + from * (1 - p) + bo, width: w,
      transform: `translateY(-50%) rotate(${rot[0] + (rot[1] - rot[0]) * p}deg) scale(${drift(t, at)})`,
      opacity: o, filter: `drop-shadow(0 24px 40px rgba(0,0,0,0.7))${glow ? ` drop-shadow(0 0 30px ${glow})` : ''}`,
      ...(fade > 0 ? {maskImage: `linear-gradient(to bottom, #000 ${Math.round((1 - fade) * 100)}%, transparent 100%)`,
        WebkitMaskImage: `linear-gradient(to bottom, #000 ${Math.round((1 - fade) * 100)}%, transparent 100%)`} : {})}} />
  );
};

// a print of a person: a photo card landing on its word
export const Print: React.FC<{src: string; x: number; y: number; wd: number; at: number; r?: number; greyAt?: number; ratio?: number; pos?: string}> = ({
  src, x, y, wd, at, r = 0, greyAt = 999, ratio = 1.25, pos = '50% 30%'}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const grey = interpolate(t, [greyAt, greyAt + 0.5], [0, 1], clamp);
  const p = settle(t, at, 0.34);
  return (
    <div style={{position: 'absolute', left: x, top: y, width: wd, padding: 12, background: '#f4f1ea', borderRadius: 6,
      transform: `translateY(${(1 - p) * 60}px) rotate(${r}deg) scale(${(0.85 + 0.15 * p) * drift(t, at)})`, opacity: Math.min(1, p * 2),
      boxShadow: '0 30px 60px rgba(0,0,0,0.6), 0 6px 14px rgba(0,0,0,0.35)', filter: `grayscale(${grey})`}}>
      <Img src={staticFile(src)} style={{width: wd - 24, height: (wd - 24) * ratio, objectFit: 'cover', objectPosition: pos, display: 'block'}} />
    </div>
  );
};

// a product's box popping in (rounded, lifted), centred on x/y
export const Box: React.FC<{src: string; at: number; x?: number; y: number; w: number; rot?: number}> = ({src, at, x = 540, y, w, rot = 0}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const p = settle(t, at, 0.3);
  const h = w * 1.25;
  return (
    <div style={{position: 'absolute', left: x - w / 2, top: y - h / 2, width: w, height: h, borderRadius: 14, overflow: 'hidden',
      opacity: kf(t, [[at, 0], [at + 0.07, 1]], easeOut), boxShadow: '0 30px 60px rgba(0,0,0,0.6), 0 6px 14px rgba(0,0,0,0.35)',
      transform: `rotate(${rot}deg) scale(${(1 + 0.3 * (1 - p)) * drift(t, at)})`}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
    </div>
  );
};

// a name label in the lower zone for a thing on screen that has no logo (a small shop with no free logo)
// top: where the label starts (1150, the lower zone); a label that replaces the captions sits on the caption line (~884)
// plate: the name and job on a dark plate, the job in full white and bigger (grey glass text over a face and a shirt is unreadable at
// feed size)
export const Tag9: React.FC<{name: string; sub?: string; at: number; color?: string; top?: number; plate?: boolean}> = ({name, sub, at, color = KEY, top = 1150,
  plate}) => {
  const t = useT();
  if (t < at - 0.01) return null;
  const p = settle(t, at, 0.34);
  return (
    <div style={{position: 'absolute', left: 0, width: 1080, top, display: 'flex', flexDirection: 'column', alignItems: 'center',
      opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 30}px)`}}>
      {plate ? null : <div style={{position: 'absolute', left: 140, right: 140, top: -40, height: 220, background: 'radial-gradient(ellipse at 50% 55%, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0) 70%)'}} />}
      <div style={plate ? {display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '18px 44px 22px', borderRadius: 22, background: 'rgba(6,8,12,0.82)',
        boxShadow: '0 20px 50px rgba(0,0,0,0.6), inset 0 0 0 2px rgba(255,255,255,0.08)'} : {display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{width: 64 * p, height: 6, borderRadius: 3, background: color, marginBottom: 16, boxShadow: `0 0 18px ${color}`}} />
        <div style={{font: `${LOOK.type.display_weight} 84px ${DISPLAY}`, color: '#fff', letterSpacing: `${LOOK.type.display_tracking}em`, ...TRACK_END(LOOK.type.display_tracking),
          textShadow: '0 6px 28px rgba(0,0,0,0.8)'}}>{name}</div>
        {sub ? <div style={{font: `${plate ? 700 : 600} ${plate ? 42 : 34}px ${TEXT}`, color: plate ? '#fff' : 'rgba(255,255,255,0.8)', marginTop: 6,
          textShadow: '0 4px 18px rgba(0,0,0,0.8)'}}>{sub}</div> : null}
      </div>
    </div>
  );
};

// a receipt for 9:16: a region of a captured page in a browser window, its spoken words lit as said (kitCards' Browser/Page way), one push
export type Cap = {marks: {phrase: string; x: number; y: number; w: number; h: number}[]};
export const Receipt9: React.FC<{src: string; iw: number; ih: number; crop: [number, number, number, number]; marks?: {box: [number, number, number, number]; at: number}[];
  top?: number; tag?: string; dark?: boolean; dur: number; bg?: React.ReactNode; line?: boolean; rise?: boolean}> = ({src, iw, ih, crop, marks = [], top = 330, tag, dark, dur, bg,
  line, rise}) => {
  const t = useT();
  // rise: the card comes up from below into place over its first 0.28 s, so a second receipt from the same page doesn't land the way the
  // first one did (two cards of the same size, place and entry read as a repeat)
  const up = rise ? interpolate(t, [0, 0.28], [1, 0], {...clamp, easing: (q) => 1 - Math.pow(1 - q, 3)}) : 0;
  // line: the receipt is the one thing on screen, big and centred on the caption line over a full-bleed ground (bg: a Back9), and
  // replaces the captions while it shows (finish_short clears them under its window; a receipt as a strip in the upper third over a
  // plain ground leaves the lower half empty, and captions under the lit words repeat them).
  // The ground's footage moves the frame, so the card itself pushes a gentle 6% a second and can be drawn 1000 px wide
  const rate = line ? 0.06 : 0.14;
  // 12% a second for the first second, then 6% (7% still reads as a frozen picture at a receipt's first 0.8 s)
  const s = 1 + Math.min(0.3, rate * t);   // 14% a second (10% on a white page still read as still), the whole shot (6% after the first second measured 0.25 of the QA's 0.35)
  // the push ends inside the frame and above the captions (a long push otherwise runs the card's last line under the captions, its text
  // to the frame's edge and its border out of the frame): a long push draws the card
  // narrower (20 px left each side at its end), and a card whose end would reach the captions (y ~920) is lifted, never above TOPBAND
  const sEnd = 1 + Math.min(0.3, rate * dur);
  const W = Math.min(line ? 1000 : 940, Math.floor(2 * (540 - 20) / sEnd)), k = W / crop[2], H = crop[3] * k;
  const y = line ? Math.round(960 - (54 + H) / 2) : Math.max(330, Math.min(top, 880 - (54 + H) * (0.3 + 0.7 * sEnd)));
  return (
    <AbsoluteFill style={{background: '#08090c'}}>
      {bg}
      <div data-gate="frame" style={{position: 'absolute', left: (1080 - W) / 2, top: y, width: W, borderRadius: 16, overflow: 'hidden', background: '#1c1f26', transform: `translateY(${up * 160}px) scale(${s})`, opacity: 1 - 0.9 * up,
        transformOrigin: line ? '50% 50%' : '50% 30%', boxShadow: '0 30px 70px rgba(0,0,0,0.65), 0 0 0 2px rgba(255,255,255,0.06)'}}>
        <div style={{height: 54, display: 'flex', alignItems: 'center', padding: '0 20px', gap: 11, background: '#2a2e36'}}>
          {['#ff5f57', '#febc2e', '#28c840'].map((col) => <div key={col} style={{width: 16, height: 16, borderRadius: 8, background: col}} />)}
          <div style={{marginLeft: 14, flex: 1, height: 34, borderRadius: 17, background: '#1c1f26'}} />
          {tag ? <div style={{marginLeft: 10, padding: '4px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.88)',
            fontFamily: TEXT, fontSize: 20, whiteSpace: 'nowrap'}}>{tag}</div> : null}
        </div>
        <div style={{position: 'relative', width: W, height: H, overflow: 'hidden', background: dark ? '#121212' : '#ffffff'}}>
          <Img src={staticFile(src)} style={{position: 'absolute', left: -crop[0] * k, top: -crop[1] * k, width: iw * k, height: ih * k, maxWidth: 'none'}} />
          {marks.map(({box: m, at}, i) => {
            const p = kf(t, [[at, 0], [at + 0.32, 1]], easeOut);
            if (p <= 0) return null;
            const L = (m[0] - crop[0] - 6) * k, T = (m[1] - crop[1] - 3) * k, Wm = (m[2] + 12) * k * p, Hm = (m[3] + 6) * k;
            // a dark page: yellow multiplied onto grey turns olive and the light type drowns, so under the
            // mark the page's own pixels are shown as ink on paper (inverted, grey) and the yellow lands on that: dark words on yellow
            if (dark) return (
              <div key={i} data-gate="mark" style={{position: 'absolute', left: L, top: T, width: Wm, height: Hm, overflow: 'hidden', borderRadius: 4 * k}}>
                <Img src={staticFile(src)} style={{position: 'absolute', left: -crop[0] * k - L, top: -crop[1] * k - T, width: iw * k, height: ih * k, maxWidth: 'none',
                  filter: 'invert(1) grayscale(1) contrast(2.2) brightness(1.15)'}} />
                <div style={{position: 'absolute', inset: 0, background: `rgb(${KEY_RGB})`, mixBlendMode: 'multiply'}} />
              </div>
            );
            return <div key={i} data-gate="mark" style={{position: 'absolute', left: L, top: T, width: Wm, height: Hm, background: `rgba(${KEY_RGB},0.9)`, mixBlendMode: 'multiply',
              borderRadius: 4 * k}} />;
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// cash stacks landing one by one in rows (a count shown as units); per = seconds between stacks
export const Cash: React.FC<{src: string; n: number; at: number; per: number; x0?: number; y0?: number; cols?: number; w?: number; dx?: number; dy?: number}> = ({
  src, n, at, per, x0 = 200, y0 = 1180, cols = 4, w = 200, dx = 170, dy = -95}) => {
  const t = useT();
  const out = [];
  for (let i = 0; i < n; i++) {
    const a = at + i * per;
    if (t < a) continue;
    const q = interpolate(t, [a, a + 0.16], [0, 1], {...clamp, easing: (z) => z * z});
    const r = Math.floor(i / cols), c = i % cols;
    const x = x0 + c * dx + (r % 2) * (dx / 2), y = y0 + r * dy;
    out.push(<Img key={i} src={staticFile(src)} style={{position: 'absolute', left: x - w / 2, top: y - (1 - q) * 220, width: w, opacity: Math.min(1, q * 3),
      filter: 'drop-shadow(0 16px 26px rgba(0,0,0,0.6))', zIndex: 100 - r}} />);
  }
  return <>{out}</>;
};

// a ground: a radial light in the scene's colour
export const ground = (inner: string, outer = '#05060a') => `radial-gradient(ellipse at 50% 36%, ${inner} 0%, ${outer} 78%)`;

// a source under 1080p (720p sources, TV, screen recordings) never fills 9:16 (a 405-px slice blown up 2.7x): it plays as a
// 16:9 card at or under its own size in the upper zone (y 290-880, the captions under it), on the scene's own ground: never on a blurred
// copy of itself, a soft light of the scene's colour behind it
// zoom: a letterboxed source filled inside its card (1.25 for a 1920x864 picture in a 1080 file), the title whole
// back: a full-bleed ground under the card (a Back9 of other footage of the subject), so the screen around it isn't empty (the gate's EMPTY)
export const Card9: React.FC<{m: Media; start?: number; dur: number; y?: number; w?: number; credit?: string; filter?: string; bg?: string; zoom?: number; own?: boolean;
  back?: React.ReactNode}> = ({m, start = 0, dur, y = 600, w = 1000, credit, filter, bg = 'radial-gradient(ellipse at 50% 32%, #1b2433 0%, #06080c 72%)', zoom = 1.0, own, back}) => {
  const t = useT();
  const h = Math.round((w * m.ih) / m.iw);
  const s = 1 + Math.min(0.16, 0.06 * t);
  return (
    <AbsoluteFill style={{background: bg}}>
      {back}
      <div data-gate={own ? 'stamp' : undefined} style={{position: 'absolute', left: 540 - w / 2, top: y - h / 2, width: w, height: h, borderRadius: 18, overflow: 'hidden', transform: `scale(${s})`,
        boxShadow: '0 12px 28px rgba(0,0,0,0.5), 0 50px 110px rgba(0,0,0,0.7)'}}>
        <Cover m={m} start={start} box={{x: 0, y: 0, w, h}} fx={0.5} fy={0.5} s0={zoom} s1={zoom} dur={dur} filter={filter} />
      </div>
      {credit ? <Credit text={credit} /> : null}
    </AbsoluteFill>
  );
};
