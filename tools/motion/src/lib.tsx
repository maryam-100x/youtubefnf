// Building blocks for every composition: the clock (seconds -> frames), scenes, camera moves, clips that never freeze, stills and a few
// screen effects. Everything is timed in seconds of the video (S) and converted to frames here, so cues come straight from the word timings.
import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Internals,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {noise2D} from '@remotion/noise';
import clipDurs from './clipdurs.json';
import clipEdges from './clipedges.json';
import {gateLog, gateOn} from './gate';
import {DISPLAY, LOOK, TEXT} from './look';

// the creator's look (src/look.json): DISPLAY for headlines and numbers, TEXT for small type; LOOK for the rest
export {DISPLAY, LOOK, TEXT};
// the creator's colours (brand.ts, set at setup): the accent, light ink, the dark paper ground, the Shorts' key-phrase colour
export {ACCENT, ACCENT_RGB, ON_ACCENT, INK, INK_RGB, PAPER, PAPER_RGB, KEY, KEY_RGB, CHANNEL} from './brand';
// REMOTION_FPS=30 renders a composition at 30 fps (for 30-fps source footage on a busy CPU); everything here is in seconds and converts with FPS
const ENV_FPS = (() => {
  try {
    return Number(process.env.REMOTION_FPS);   // REMOTION_ variables are baked into the bundle
  } catch {
    return NaN;
  }
})();
export const FPS = ENV_FPS || 60;
export const f = (s: number) => Math.round(s * FPS);
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const easeOut = Easing.bezier(0.16, 1, 0.3, 1); // expo-like: fast in, long settle
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);

// A span of the video, in seconds. Children get a local clock starting at 0.
// Sound components among the children (marked `isAudio`, also inside fragments) play in their own Sequence that outlives the scene, so a
// boom's tail rings on past the cut (a boom is never cut short); the pictures still end at `to`.
const flat = (children: React.ReactNode): React.ReactNode[] =>
  React.Children.toArray(children).flatMap((c) => (React.isValidElement(c) && c.type === React.Fragment ? flat((c.props as {children?: React.ReactNode}).children) : [c]));
// a scene's sounds may start up to this long before the scene (a whoosh's rise into the cut)
const PRE_ROLL = 1;
const isAudio = (c: React.ReactNode) => React.isValidElement(c) && typeof c.type !== 'string' && (c.type as {isAudio?: boolean}).isAudio === true;
export const At: React.FC<{from: number; to: number; children: React.ReactNode; z?: number}> = ({from, to, children, z}) => {
  const all = flat(children);
  const audio = all.filter(isAudio);
  return (
    <>
      <Sequence from={f(from)} durationInFrames={Math.max(1, f(to) - f(from))} layout="none">
        {/* data-gateat: the gate's probe reads every range's first frame as a cut (a built Short's shots are its <At> ranges) */}
        <AbsoluteFill data-gateat={f(from)} style={{zIndex: z}}>{audio.length ? all.filter((c) => !isAudio(c)) : children}</AbsoluteFill>
      </Sequence>
      {audio.length ? (
        <Sequence from={f(from) - f(PRE_ROLL)} layout="none">
          {audio.map((c, i) => {
            const el = c as React.ReactElement<{at: number | number[]}>;
            const at = el.props.at;
            return React.cloneElement(el, {key: i, at: Array.isArray(at) ? at.map((x) => x + PRE_ROLL) : at + PRE_ROLL});
          })}
        </Sequence>
      ) : null}
    </>
  );
};

// local time in seconds inside the current Sequence
export const useT = () => useCurrentFrame() / FPS;

// value over local time with easing: keys [[t, v], ...]
export const kf = (t: number, keys: [number, number][], ease = easeInOut) =>
  interpolate(
    t,
    keys.map((k) => k[0]),
    keys.map((k) => k[1]),
    {...clamp, easing: ease},
  );

type Move = {s0?: number; s1?: number; x0?: number; x1?: number; y0?: number; y1?: number; r0?: number; r1?: number; dur: number; ease?: (t: number) => number};

// camera move on a layer: scale/translate/rotate from 0 to dur (never static: the references keep every shot moving)
export const useMove = (m: Move) => {
  const t = useT();
  const e = m.ease ?? easeInOut;
  const p = interpolate(t, [0, m.dur], [0, 1], {...clamp, easing: e});
  const s = (m.s0 ?? 1) + ((m.s1 ?? m.s0 ?? 1) - (m.s0 ?? 1)) * p;
  const x = (m.x0 ?? 0) + ((m.x1 ?? m.x0 ?? 0) - (m.x0 ?? 0)) * p;
  const y = (m.y0 ?? 0) + ((m.y1 ?? m.y0 ?? 0) - (m.y0 ?? 0)) * p;
  const r = (m.r0 ?? 0) + ((m.r1 ?? m.r0 ?? 0) - (m.r0 ?? 0)) * p;
  // never past the zoom's spare edge ((s-1)*960 px across, (s-1)*540 up/down), or the frame shows a black bar
  const mx = Math.max(0, (s - 1) * 960), my = Math.max(0, (s - 1) * 540);
  const gx = Math.max(-mx, Math.min(mx, x)), gy = Math.max(-my, Math.min(my, y));
  return `translate(${gx}px, ${gy}px) scale(${s}) rotate(${r}deg)`;
};

// every video in the public dir: {"<public path>": [the last frame's start (s), fps]}, measured by ffprobe when a clip is cut (its prep
// step writes src/clipdurs.json; empty until the first clips are cut)
const DURS0 = clipDurs as unknown as Record<string, [number, number]>;
// Slivers: frames of the source's neighbouring shot at a clip's start or end (a tenth of a second of another scene opening a shot).
// src/clipedges.json: {"<public path>": [the first good frame (s), the last good frame (s) or null]}, each checked by eye. A clip never
// shows a sliver: its start is clamped to the first good frame, and fitClip treats the last good frame as the end
const EDGES = clipEdges as unknown as Record<string, [number, number | null]>;
const DURS: Record<string, [number, number]> = Object.fromEntries(
  Object.entries(DURS0).map(([k, [last, fps]]) => [k, [EDGES[k]?.[1] ?? last, fps] as [number, number]]),
);
export const firstGood = (src: string) => EDGES[src]?.[0] ?? 0;

export const lastFrame = (src: string) => DURS[src]?.[0] ?? 0;
export const clipFps = (src: string): number | undefined => DURS[src]?.[1];

// A clip must never run past its last frame: Remotion then holds that frame, a freeze (most often a blurred background that outlasts a
// short shot; the clip audit, tools/motion/qa_clips.py, finds them). When the scene (the clip's Sequence) asks for more than the file has,
// the clip starts earlier; `fits` false = even that is short (cut to a second clip). Clips that fit are untouched. `minRate` lowers the
// rate floor for one clip (a shot a longer voice outgrew by a fraction of a second, slowed a little instead of freezing its last frame).
export const fitClip = (src: string, start0: number, rate: number, len: number | null, minRate?: number) => {
  const g = firstGood(src);
  const start = Math.max(start0, g);
  const m = DURS[src];
  if (!m || !len || len <= 0) return {start, rate, fits: true};
  const [last, fps] = m;
  const floor = minRate ?? 1.0; // a clip is never slowed to fill its shot; a short clip starts earlier instead, and a shot even that
  // can't fill shows up in qa_clips as an overrun: cut to a second clip
  if (start + len * rate <= last + 0.5 / fps) return {start, rate, fits: true};
  const r1 = (last - start) / len;
  if (r1 >= floor && r1 <= rate) return {start, rate: r1, fits: true};
  const s1 = last - Math.min(rate, floor) * len;
  if (s1 >= g) return {start: s1, rate: Math.min(rate, floor), fits: true};
  return {start: g, rate: Math.min(rate, floor), fits: false};
};

// footage: a clip from the public dir, starting at `start` s inside the clip, at `rate`, with a camera move (fitted: fitClip)
export const Clip: React.FC<{
  src: string;
  start?: number;
  rate?: number;
  move?: Move;
  filter?: string;
  objectPosition?: string;
  style?: React.CSSProperties;
  fit?: boolean;
  floor?: number;
}> = ({src, start: start0 = 0, rate: rate0 = 1, move, filter, objectPosition, style, fit = true, floor}) => {
  const tr = useMove(move ?? {dur: 1});
  const seq = React.useContext(Internals.SequenceContext);
  const fc = fit ? fitClip(src, start0, rate0, seq ? seq.durationInFrames / FPS : null, floor) : {start: start0, rate: rate0, fits: true};
  const {start, rate} = fc;
  // QA (motion/qa_clips.py): with REMOTION_CLIP_AUDIT=1 an audio-only render logs the source second each clip shows, per video frame,
  // to find clips that run past their end (Remotion then holds the last frame: a freeze). No effect on a normal render.
  const abs = Internals.useAbsoluteTimelinePosition();
  const f = useCurrentFrame();
  // the pre-render gate (src/gate.tsx): what this clip shows on this frame, after the fit; no frame is fetched
  if (gateOn) {
    gateLog('clip', {abs, src, f, s: Math.round(start * FPS) / FPS + (f / FPS) * rate, start, rate, s0: start0, r0: rate0,
      dur: seq ? seq.durationInFrames : null, fits: fc.fits});
    // an empty pane in the video's place, so its box (after every zoom and crop) is measured with the rest; the video's own filter rides
    // on it (a Stage's ground is blur(8px) brightness(0.42): without it the probe would read every ground as sharp and full-bright)
    return (
      <AbsoluteFill data-gateclip={src} style={{overflow: 'hidden', ...style, ...(filter ? {filter} : {})}}>
        <AbsoluteFill style={{transform: tr}} />
      </AbsoluteFill>
    );
  }
  if (typeof window !== 'undefined' && (window as unknown as {process?: {env?: Record<string, string>}}).process?.env?.REMOTION_CLIP_AUDIT === '1') {
    console.log(`CLIPAUDIT|${abs}|${src}|${(Math.round(start * FPS) / FPS + (f / FPS) * rate).toFixed(3)}`);
    return null; // the audit needs only the log: no frame is fetched, so it runs fast
  }
  // REMOTION_NO_VIDEO=1: an audio-only render (the sound effects track) that fetches no video frame (with the clips mounted the same
  // render runs many times longer; the sounds are all <Audio>, so the picture isn't needed)
  if (typeof window !== 'undefined' && (window as unknown as {process?: {env?: Record<string, string>}}).process?.env?.REMOTION_NO_VIDEO === '1') return null;
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <AbsoluteFill style={{transform: tr, filter}}>
        <OffthreadVideo
          src={staticFile(src)}
          startFrom={Math.round(start * FPS)}
          playbackRate={rate}
          muted
          style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Still: React.FC<{src: string; move?: Move; filter?: string; fit?: 'cover' | 'contain'; objectPosition?: string; style?: React.CSSProperties}> = ({
  src,
  move,
  filter,
  fit = 'cover',
  objectPosition,
  style,
}) => {
  const tr = useMove(move ?? {dur: 1});
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <AbsoluteFill style={{transform: tr, filter}}>
        <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: fit, objectPosition}} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// blur-in reveal: heavy blur to sharp in `dur`, with opacity
export const useBlurIn = (dur = 0.3, from = 22) => {
  const t = useT();
  const b = interpolate(t, [0, dur], [from, 0], {...clamp, easing: easeOut});
  const o = interpolate(t, [0, dur * 0.6], [0, 1], clamp);
  return {filter: `blur(${b}px)`, opacity: o};
};

export const Vignette: React.FC<{strength?: number}> = ({strength = 0.55}) => (
  <AbsoluteFill style={{background: `radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,${strength}) 100%)`, pointerEvents: 'none'}} />
);

// film grain: SVG turbulence with a seed that changes every 2 frames
export const Grain: React.FC<{opacity?: number}> = ({opacity = 0.07}) => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / 2) % 50;
  return (
    <AbsoluteFill style={{opacity, mixBlendMode: 'overlay', pointerEvents: 'none'}}>
      <svg width="1920" height="1080">
        <filter id={`grain${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="1920" height="1080" filter={`url(#grain${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};

// true inside a stage that shows the scene's own footage: the dust specks were made for the flat dark stage and stay off
export const OnFootage = React.createContext(false);

// drifting dust specks on dark backgrounds (number cards)
export const Dust: React.FC<{n?: number; color?: string}> = ({n = 70, color = '255,255,255'}) => {
  const onFootage = React.useContext(OnFootage);
  const t = useT();
  if (onFootage) return null;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {new Array(n).fill(0).map((_, i) => {
        const x = ((noise2D('x' + i, i * 0.37, 0) + 1) / 2) * 1920 + noise2D('dx' + i, t * 0.15, i) * 60;
        const y = ((noise2D('y' + i, 0, i * 0.41) + 1) / 2) * 1080 - t * (8 + (i % 7) * 3);
        const r = 1 + (i % 4) * 0.8;
        const o = 0.15 + ((noise2D('o' + i, t * 0.5, i) + 1) / 2) * 0.45;
        return <div key={i} style={{position: 'absolute', left: x, top: ((y % 1080) + 1080) % 1080, width: r * 2, height: r * 2, borderRadius: r, background: `rgba(${color},${o})`, filter: 'blur(0.6px)'}} />;
      })}
    </AbsoluteFill>
  );
};

// RGB-split + slice glitch over children while active
export const GlitchFilters: React.FC = () => (
  <svg width="0" height="0" style={{position: 'absolute'}}>
    <filter id="onlyRed">
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" />
    </filter>
    <filter id="onlyCyan">
      <feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0" />
    </filter>
  </svg>
);

export const Glitch: React.FC<{amount: number; seed?: number; children: React.ReactNode}> = ({amount, seed = 1, children}) => {
  const frame = useCurrentFrame();
  if (amount <= 0.001) return <AbsoluteFill>{children}</AbsoluteFill>;
  const k = Math.floor(frame / 2) + seed * 13;
  const off = 6 + amount * 40;
  const slices = new Array(7).fill(0).map((_, i) => {
    const y0 = ((Math.sin(k * 12.9898 + i * 78.233) * 43758.5453) % 1 + 1) % 1;
    const h = 0.02 + (((Math.sin(k * 4.1 + i * 9.7) * 1000) % 1 + 1) % 1) * 0.09 * amount;
    const dx = (((Math.sin(k * 7.3 + i * 3.1) * 1000) % 1) - 0.5) * 220 * amount;
    return {y0: y0 * 100, h: h * 100, dx};
  });
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{filter: 'url(#onlyRed)', transform: `translateX(${off}px)`}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{filter: 'url(#onlyCyan)', transform: `translateX(${-off}px)`, mixBlendMode: 'screen'}}>{children}</AbsoluteFill>
      {slices.map((sl, i) => (
        <AbsoluteFill key={i} style={{clipPath: `inset(${sl.y0}% 0 ${Math.max(0, 100 - sl.y0 - sl.h)}% 0)`, transform: `translateX(${sl.dx}px)`}}>
          {children}
        </AbsoluteFill>
      ))}
    </AbsoluteFill>
  );
};

// white flash, peak at `at` local seconds
export const Flash: React.FC<{at: number; dur?: number; max?: number}> = ({at, dur = 0.25, max = 0.85}) => {
  const t = useT();
  const o = interpolate(t, [at - 0.03, at, at + dur], [0, max, 0], clamp);
  return <AbsoluteFill style={{background: 'white', opacity: o, pointerEvents: 'none'}} />;
};

// light leak sweep (a diagonal light bar)
export const LightBar: React.FC<{from: number; dur?: number; angle?: number; opacity?: number}> = ({from, dur = 0.9, angle = 20, opacity = 0.75}) => {
  const t = useT();
  const p = interpolate(t, [from, from + dur], [-0.4, 1.4], {...clamp, easing: easeInOut});
  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen', opacity}}>
      <div style={{position: 'absolute', left: `${p * 100 - 30}%`, top: '-50%', width: '22%', height: '200%', transform: `rotate(${angle}deg)`,
        background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,240,220,0.9) 50%, rgba(255,255,255,0) 100%)', filter: 'blur(18px)'}} />
    </AbsoluteFill>
  );
};

// letterbox bars (story mode)
export const Letterbox: React.FC<{inAt?: number; outAt?: number; h?: number}> = ({inAt = 0, outAt = 999, h = 135}) => {
  const t = useT();
  const p = interpolate(t, [inAt, inAt + 0.45, outAt, outAt + 0.4], [0, 1, 1, 0], {...clamp, easing: easeOut});
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: h * p, background: 'black'}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: h * p, background: 'black'}} />
    </AbsoluteFill>
  );
};
