// The ledger walker's recorder (asset_ledger.py): the state one sampled frame renders with, and what every media element and
// component reports while it renders. Shared by the Remotion stub (remotion_stub.tsx), the React wrapper (react_wrap.ts) and walk.tsx.
// Imports the real React: the bundler only swaps React for the wrapper inside src/ (build.mjs).
import * as React from 'react';

export const S = {frame: 0, fps: 60, width: 1920, height: 1080, durationInFrames: 1, id: ''};

// Remotion's SequenceContext, plus what the ledger needs: the top-level sequence (the shot) and the window this sequence can render in
export type SeqVal = {
  cumulatedFrom: number;
  relativeFrom: number;
  parentFrom: number;
  absoluteFrom: number;
  cumulatedNegativeFrom: number;
  durationInFrames: number;
  playbackRate: number;
  id: string;
  height: null;
  width: null;
  premounting: boolean;
  postmounting: boolean;
  premountDisplay: null;
  postmountDisplay: null;
  root: {from: number; dur: number};
  winStart: number;
  winEnd: number;
};
export const SeqCtx = React.createContext<SeqVal | null>(null);
export const FreezeCtx = React.createContext<number | null>(null);
// the components above an element, outermost first: [name, module]
export const PathCtx = React.createContext<[string, string][]>([]);

const pathKey = (p: [string, string][]) => p.map((x) => x[0]).join('>');
const rootOf = (seq: SeqVal | null) => seq?.root ?? {from: 0, dur: S.durationInFrames};

type MediaRec = {kind: string; src: string; path: [string, string][]; root: {from: number; dur: number}; first: number; last: number; n: number;
  // videos: the source frame the element starts at, its rate, where its sequence's frame 0 is, the window it can render in, and the
  // source seconds seen at the first and last sample
  startFrom?: number; rate?: number; seqStart?: number; winStart?: number; winEnd?: number; t0?: number; t1?: number; frozen?: boolean};
type CompRec = {name: string; mod: string; path: [string, string][]; root: {from: number; dur: number}; first: number; last: number; n: number;
  props: string; variants: number};

export const MEDIA = new Map<string, MediaRec>();
export const COMPS = new Map<string, CompRec>();
export const ERRORS: {frame: number; error: string}[] = [];
// the first frame of every sequence the renders met (shown or not): walk.tsx samples each one, so no shot falls between two samples
export const SEQ_STARTS = new Set<number>();

export const recordImage = (kind: string, src: unknown, seq: SeqVal | null, path: [string, string][]) => {
  if (typeof src !== 'string' || !src) return;
  const root = rootOf(seq);
  const key = `${kind}|${root.from}|${src}|${pathKey(path)}`;
  const m = MEDIA.get(key);
  if (m) {
    m.first = Math.min(m.first, S.frame);
    m.last = Math.max(m.last, S.frame);
    m.n++;
  } else MEDIA.set(key, {kind, src, path, root, first: S.frame, last: S.frame, n: 1, winStart: seq ? seq.winStart : 0, winEnd: seq ? seq.winEnd : S.durationInFrames});
};

export const recordVideo = (src: unknown, startFrom: number, rate: number, rel: number, frozen: boolean, seq: SeqVal | null, path: [string, string][]) => {
  if (typeof src !== 'string' || !src) return;
  const root = rootOf(seq);
  const seqStart = seq ? seq.cumulatedFrom + seq.relativeFrom : 0;
  const t = (startFrom + rel * rate) / S.fps;
  const key = `video|${root.from}|${src}|${startFrom}|${rate}|${seqStart}|${frozen ? rel : ''}|${pathKey(path)}`;
  const m = MEDIA.get(key);
  if (m) {
    if (S.frame < m.first) {
      m.first = S.frame;
      m.t0 = t;
    }
    if (S.frame > m.last) {
      m.last = S.frame;
      m.t1 = t;
    }
    m.n++;
  } else {
    MEDIA.set(key, {kind: 'video', src, path, root, first: S.frame, last: S.frame, n: 1, startFrom, rate, seqStart,
      winStart: seq ? seq.winStart : 0, winEnd: seq ? seq.winEnd : S.durationInFrames, t0: t, t1: t, frozen});
  }
};

// a prop worth keeping in the ledger: numbers, short strings, flags, small arrays and objects of those (never children or functions)
const keep = (v: unknown, depth = 0): unknown => {
  if (v === null || v === undefined) return undefined;
  if (typeof v === 'number') return Number.isFinite(v) ? Math.round(v * 1000) / 1000 : undefined;
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v.length <= 240 ? v : v.slice(0, 240) + '…';
  if (typeof v === 'function' || React.isValidElement(v)) return undefined;
  if (depth >= 2) return undefined;
  if (Array.isArray(v)) {
    const a = v.slice(0, 24).map((x) => keep(x, depth + 1)).filter((x) => x !== undefined);
    return a.length ? a : undefined;
  }
  if (typeof v === 'object') {
    const o: Record<string, unknown> = {};
    for (const [k, x] of Object.entries(v as Record<string, unknown>).slice(0, 16)) {
      const y = keep(x, depth + 1);
      if (y !== undefined) o[k] = y;
    }
    return Object.keys(o).length ? o : undefined;
  }
  return undefined;
};

export const summarize = (props: Record<string, unknown>) => {
  const o: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(props ?? {})) {
    if (k === 'children' || k === 'key' || k === 'ref') continue;
    const y = keep(v);
    if (y !== undefined) o[k] = y;
  }
  const s = JSON.stringify(o);
  return s.length <= 1500 ? s : s.slice(0, 1500) + '…';
};

export const recordComp = (name: string, mod: string, props: Record<string, unknown>, seq: SeqVal | null, path: [string, string][]) => {
  const root = rootOf(seq);
  const key = `${root.from}|${mod}|${name}|${pathKey(path)}`;
  const m = COMPS.get(key);
  if (m) {
    m.first = Math.min(m.first, S.frame);
    m.last = Math.max(m.last, S.frame);
    m.n++;
    return;
  }
  COMPS.set(key, {name, mod, path, root, first: S.frame, last: S.frame, n: 1, props: summarize(props), variants: 1});
};
