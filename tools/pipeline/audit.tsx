// The static clip audit of any composition that exports SHOTS ({at, el(dur)}[]) and <NAME>_SECONDS (V12 and every video built like
// it). pipe.py fills the three __PLACEHOLDERS__ from video.toml, writes the result to tools/motion/out/audit_<comp>.tsx, bundles it
// with esbuild and runs it with node: no render, seconds for a whole film. Every shot's element is built with its real length and
// walked for the components that play a file; each play's last source
// second is checked against the file's own length (src/clipdurs.json, written by the prep scripts and curate.py). Writes a JSON report
// (PLAYS_JSON) with every play, every shot's slot, the overruns, the files it could not measure, and the shots or plays under MIN_SHOT
// seconds (the flash-frame rule: a shot whose word landed just before the next beat's first shot). Clips played inside a component's
// own render (a montage that picks its own files) are not seen: those get proof stills.
import React from 'react';
import * as M from '__MODULE__';
import durs from '../src/clipdurs.json';

const PLAYS = new Set<string>(__PLAYS__);         // components with src + start|from (+ dur, rate)
const BG = new Set<string>(__BG__);               // components with bg + bgStart
const MIN_SHOT = __MIN_SHOT__;
type ShotT = {at: number; el: (dur: number) => React.ReactNode};
const SHOTS = (M as unknown as {SHOTS: ShotT[]}).SHOTS;
const SECONDS = Object.entries(M).find(([k]) => /_SECONDS$/.test(k))![1] as number;

const D = durs as unknown as Record<string, [number, number]>;
const SRCDIR = '__MODULE__'.split('/').slice(-2, -1)[0];   // the composition's folder (v12): its clips first when names repeat
type Play = {shot: number; at: number; src: string; from: number; len: number; rate: number; comp: string};
const plays: Play[] = [];
// a mark on most of the text is no mark: every card's mark against its whole text, by letters; pipe.py fails a mark over half of it
type Mark = {shot: number; at: number; comp: string; text: string; hl: string; share: number};
const marks: Mark[] = [];
// every string a viewer reads in a card's props (a working label such as "his take" shown as a source line): pipe.py fails internal words
type Cap = {shot: number; at: number; comp: string; prop: string; text: string};
const caps: Cap[] = [];
const CAP_PROPS = ['source', 'sub', 'label', 'kicker', 'role', 'where', 'who', 'title', 'name', 'line', 'quote'];
const letters = (s: string) => s.replace(/[^\p{L}\p{N}]/gu, '').length;

const nm = (t: unknown) => {
  const x = t as {name?: string; displayName?: string} | string;
  return (typeof x === 'string' ? x : x.displayName || x.name || '').replace(/\d+$/, '');   // the bundler renames duplicates (Foot2)
};

const walk = (node: unknown, shot: number, at: number, dur: number) => {
  if (Array.isArray(node)) {
    node.forEach((n) => walk(n, shot, at, dur));
    return;
  }
  if (!node || typeof node !== 'object' || !('props' in (node as object))) return;
  const el = node as React.ReactElement<Record<string, unknown>>;
  const name = nm(el.type);
  const p = el.props;
  const d = typeof p.dur === 'number' ? (p.dur as number) : dur;
  const body = typeof p.quote === 'string' ? (p.quote as string) : typeof p.text === 'string' ? (p.text as string) : null;
  for (const k of CAP_PROPS) if (typeof p[k] === 'string' && p[k]) caps.push({shot, at, comp: name, prop: k, text: p[k] as string});
  if (body && typeof p.hl === 'string' && p.hl) marks.push({shot, at, comp: name, text: body, hl: p.hl as string, share: letters(p.hl as string) / Math.max(1, letters(body))});
  if (PLAYS.has(name) && typeof p.src === 'string') {
    const from = typeof p.start === 'number' ? (p.start as number) : typeof p.from === 'number' ? (p.from as number) : 0;
    plays.push({shot, at, src: p.src as string, from, len: d, rate: (p.rate as number) ?? 1, comp: name});
  } else if (BG.has(name) && typeof p.bg === 'string') {
    plays.push({shot, at, src: p.bg as string, from: (p.bgStart as number) ?? 0, len: d, rate: 1, comp: name});
  } else if (name === 'Chain') {
    const parts = p.parts as {src: string; start?: number; len?: number; rate?: number}[];
    let t0 = 0;
    parts.forEach((c, i) => {
      const len = i + 1 < parts.length ? (c.len ?? 1) : d - t0;
      plays.push({shot, at: at + t0, src: c.src, from: c.start ?? 0, len, rate: c.rate ?? 1, comp: 'Chain'});
      t0 += len;
    });
  }
  // a component that plays clips by name inside its own render (a frame's `clip`, a row's `panes`, a split screen's `a`/`b`, a
  // montage's `clips`...) would go unseen, and its clips could freeze at their end. Any prop value, at any depth (lists,
  // objects), that names one of this film's clips counts as a play of
  // it from its `start` (when its object has one) for the whole shot: the conservative reading, as these components run their clips from
  // the shot's first frame; a list beside a numeric `burst` plays one after another, burst / n each
  if (!PLAYS.has(name) && !BG.has(name)) {
    const clipKey = (c: string) => (D[`${SRCDIR}/clips/${c}.mp4`] ? `${SRCDIR}/clips/${c}.mp4` : null);
    const scan = (v: unknown, depth: number, each: number, from: number, via: string) => {
      if (typeof v === 'string') {
        const k = clipKey(v);
        if (k) plays.push({shot, at, src: k, from, len: each, rate: 1, comp: via});
      } else if (Array.isArray(v) && depth < 4) {
        v.forEach((x) => scan(x, depth + 1, each, from, via));
      } else if (v && typeof v === 'object' && !('$$typeof' in (v as object)) && depth < 4) {
        // an object with its own `start` and `dur` (an insert's items) plays its clip for that long, from there
        const o = v as Record<string, unknown>;
        const st = typeof o.start === 'number' ? (o.start as number) : from;
        // ... and one with its own `at` (TwoUp's sides, PaneRow's panes) starts its clip there
        const ln = typeof o.dur === 'number' ? (o.dur as number) : typeof o.at === 'number' ? each - Math.max(0, o.at as number) : each;
        Object.values(o).forEach((x) => scan(x, depth + 1, ln, st, via));
      }
    };
    // a numeric `delay` (a screen switching on) starts the component's clips that much later
    const dl = typeof p.delay === 'number' ? (p.delay as number) : 0;
    for (const [key, v] of Object.entries(p)) {
      if (key === 'children') continue;
      const each = Array.isArray(v) && typeof p.burst === 'number' ? (p.burst as number) / Math.max(1, (v as unknown[]).length) : d - dl;
      scan(v, 0, each, typeof p.start === 'number' ? (p.start as number) : 0, `${name}.${key}`);
    }
  }
  walk(p.children, shot, at, dur);
};

// every shot's signature (tools/pipeline/reprobe.py): what the shot builds, written out (each element's component and
// props, a function by its source, numbers to 1e-4) and hashed, with its length in frames. Two builds with the same signature for a shot
// draw it the same, wherever it sits in the film, as long as the components it names didn't change inside (reprobe.py follows those
// through the changed files' importers), so the probe of an unchanged shot is reused, moved with the timing.
const fnv = (s: string) => {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 0x01000193) >>> 0;
  return h.toString(16).padStart(8, '0');
};
// numbers go to `nums` and stand as '#' in the text (the shape): a timing change moves every time in a shot by float noise (a bite
// 14 frames shorter: 1.907 against 1.9067), so reprobe.py matches a shot by its shape and its numbers within a tolerance
const ser = (x: unknown, names: Set<string>, nums: number[], depth = 0): string => {
  if (depth > 60) return '~';
  if (x === null || x === undefined || typeof x === 'boolean') return String(x);
  if (typeof x === 'number') {
    nums.push(Math.round(x * 1e4) / 1e4);
    return '#';
  }
  if (typeof x === 'string') return JSON.stringify(x);
  if (typeof x === 'function') return 'fn:' + (x as Function).toString().replace(/\s+/g, ' ');
  if (Array.isArray(x)) return '[' + x.map((y) => ser(y, names, nums, depth + 1)).join(',') + ']';
  if (typeof x === 'object') {
    const o = x as Record<string, unknown>;
    if ('$$typeof' in o && 'props' in o) {
      const n = nm((o as {type: unknown}).type) || String((o as {type: unknown}).type);
      names.add(n);
      return `<${n} ${ser(o.props, names, nums, depth + 1)}>`;
    }
    return '{' + Object.keys(o).sort().map((k) => k + ':' + ser(o[k], names, nums, depth + 1)).join(',') + '}';
  }
  return '?';
};

const shots: {i: number; at: number; end: number; sig?: string; names?: string[]; nums?: number[]}[] = [];
SHOTS.forEach((s, i) => {
  const end = i + 1 < SHOTS.length ? SHOTS[i + 1].at : SECONDS;
  const el = s.el(end - s.at);
  const names = new Set<string>();
  const nums: number[] = [];
  const text = ser(el, names, nums);
  const sig = fnv(Math.round((end - s.at) * 60) + '|' + text) + fnv(text + '#');   // the shape: length in frames + the text with '#'
  const form = fnv(text) + fnv('#' + text);                                          // the shape alone (a review ignores length)
  shots.push({i, at: s.at, end, sig, form, names: [...names].sort(), nums, ...(process.env.AUDIT_SER ? {ser: text.slice(0, 40000)} : {})});
  walk(el, i, s.at, end - s.at);
});

const over: {play: Play; asks: number; len: number; frozen: number}[] = [];
const unknown = new Set<string>();
for (const pl of plays) {
  const m = D[pl.src];
  if (!m) {
    unknown.add(pl.src);
    continue;
  }
  const [len, fps] = m;
  const last = len - 1 / fps;
  const asks = pl.from + pl.len * pl.rate;
  if (asks > last + 0.5 / fps) over.push({play: pl, asks, len, frozen: asks - last});
}
const short = shots.filter((s) => s.end - s.at < MIN_SHOT);
const shortPlays = plays.filter((p) => p.len < MIN_SHOT - 1e-6);
const slow = plays.filter((p) => p.rate < 0.999);
const report = {seconds: SECONDS, shots, plays, over, unknown: [...unknown], short, shortPlays, slow, minShot: MIN_SHOT, marks, caps};
console.log(`${plays.length} plays in ${shots.length} shots over ${SECONDS.toFixed(2)} s; ${over.length} overrun(s); ${short.length} shot(s) and ${shortPlays.length} play(s) under ${MIN_SHOT} s; ${slow.length} play(s) under 1.0x; ${unknown.size} file(s) not in clipdurs.json`);
if (process.env.PLAYS_JSON) require('fs').writeFileSync(process.env.PLAYS_JSON, JSON.stringify(report));
