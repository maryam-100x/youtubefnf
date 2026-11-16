// 'remotion' for the ledger walker: the same timeline rules (a Sequence shows its children inside [from, from + duration), the frame inside
// it counts from its start, a video at startFrom + frame x rate), rendered by react-dom/server one sampled frame at a time. Media elements
// report what they would show instead of loading it. The pure helpers (interpolate, Easing, spring...) are Remotion's own.
import React from 'react';
import {Easing, interpolate, interpolateColors, measureSpring, random, spring} from '../node_modules/remotion/dist/cjs/index.js';
import {FreezeCtx, PathCtx, recordImage, recordVideo, S, SEQ_STARTS, SeqCtx, type SeqVal} from './rec';

export {Easing, interpolate, interpolateColors, measureSpring, random, spring};

const FILL: React.CSSProperties = {position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, width: '100%', height: '100%', display: 'flex',
  flexDirection: 'column'};

export const AbsoluteFill: React.FC<{style?: React.CSSProperties; className?: string; children?: React.ReactNode}> = ({style, className, children}) => (
  <div className={className} style={{...FILL, ...style}}>{children}</div>
);

export const staticFile = (p: string) => p;
export const delayRender = () => 0;
export const continueRender = () => undefined;
export const cancelRender = (e: unknown) => {
  throw e instanceof Error ? e : new Error(String(e));
};
export const getInputProps = () => ({});
export const registerRoot = () => undefined;
export const Composition: React.FC = () => null;
export const Still: React.FC = () => null;
export const Folder: React.FC<{children?: React.ReactNode}> = () => null;
export const prefetch = () => ({free: () => undefined, waitUntilDone: () => Promise.resolve('')});
export const useCurrentScale = () => 1;
export const getRemotionEnvironment = () => ({isStudio: false, isRendering: true, isPlayer: false, isReadOnlyStudio: false, isClientSideRendering: false});
export const useRemotionEnvironment = getRemotionEnvironment;

export const useVideoConfig = () => ({fps: S.fps, width: S.width, height: S.height, durationInFrames: S.durationInFrames, id: S.id, defaultProps: {},
  props: {}, defaultCodec: null, defaultOutName: null, defaultVideoImageFormat: null, defaultPixelFormat: null, defaultProResProfile: null});

export const useCurrentFrame = () => {
  const fz = React.useContext(FreezeCtx);
  const seq = React.useContext(SeqCtx);
  if (fz !== null) return fz;
  return S.frame - (seq ? seq.cumulatedFrom + seq.relativeFrom : 0);
};

export const Sequence: React.FC<{from?: number; durationInFrames?: number; layout?: 'absolute-fill' | 'none'; style?: React.CSSProperties;
  name?: string; children?: React.ReactNode}> = ({from = 0, durationInFrames = Infinity, layout = 'absolute-fill', style, children}) => {
  const parent = React.useContext(SeqCtx);
  const cumulatedFrom = parent ? parent.cumulatedFrom + parent.relativeFrom : 0;
  const start = cumulatedFrom + from;
  const actual = Math.max(0, Math.min(S.durationInFrames - from, parent ? parent.durationInFrames - from : Infinity, durationInFrames));
  if (actual > 0 && Number.isFinite(start)) SEQ_STARTS.add(Math.max(0, Math.round(start)));
  if (S.frame < start || S.frame > start + actual - 1) return null;
  const val: SeqVal = {cumulatedFrom, relativeFrom: from, parentFrom: parent?.relativeFrom ?? 0, absoluteFrom: start, cumulatedNegativeFrom: 0,
    durationInFrames: actual, playbackRate: 1, id: `seq${start}`, height: null, width: null, premounting: false, postmounting: false,
    premountDisplay: null, postmountDisplay: null, root: parent?.root ?? {from: start, dur: actual},
    winStart: Math.max(parent?.winStart ?? 0, start), winEnd: Math.min(parent?.winEnd ?? Infinity, start + actual)};
  const inner = <SeqCtx.Provider value={val}>{children}</SeqCtx.Provider>;
  return layout === 'none' ? inner : <div style={{...FILL, ...style}}>{inner}</div>;
};

export const Freeze: React.FC<{frame: number; active?: boolean | ((f: number) => boolean); children?: React.ReactNode}> = ({frame, active = true, children}) => {
  const f = useCurrentFrame();
  const on = typeof active === 'function' ? active(f) : active;
  return on ? <FreezeCtx.Provider value={frame}>{children}</FreezeCtx.Provider> : <>{children}</>;
};

export const Img: React.FC<{src?: string}> = ({src}) => {
  const seq = React.useContext(SeqCtx);
  const path = React.useContext(PathCtx);
  recordImage('image', src, seq, path);
  return null;
};

type VProps = {src?: string; startFrom?: number; trimBefore?: number; playbackRate?: number};
export const OffthreadVideo: React.FC<VProps> = ({src, startFrom, trimBefore, playbackRate = 1}) => {
  const seq = React.useContext(SeqCtx);
  const path = React.useContext(PathCtx);
  const fz = React.useContext(FreezeCtx);
  const rel = useCurrentFrame();
  recordVideo(src, trimBefore ?? startFrom ?? 0, playbackRate, rel, fz !== null, seq, path);
  return null;
};
export const Video = OffthreadVideo;
export const Html5Video = OffthreadVideo;
export const Audio: React.FC = () => null;
export const Html5Audio = Audio;

export const Internals = {
  SequenceContext: SeqCtx,
  useAbsoluteTimelinePosition: () => S.frame,
  useTimelinePosition: () => S.frame,
};

export const Series = Object.assign(({children}: {children?: React.ReactNode}) => <>{children}</>, {Sequence});
export const Loop: React.FC<{children?: React.ReactNode}> = ({children}) => <>{children}</>;

// the stubs are not the edit's components: react_wrap leaves them unrecorded
for (const c of [AbsoluteFill, Composition, Still, Folder, Sequence, Freeze, Img, OffthreadVideo, Audio, Series, Loop]) {
  (c as unknown as {__ledger_stub: boolean}).__ledger_stub = true;
}
