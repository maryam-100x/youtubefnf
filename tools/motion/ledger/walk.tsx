// The ledger walker's loop: one composition rendered by react-dom/server at every `step`-th frame (no browser, no video decoded), each frame
// reporting the files it shows (rec.ts). Writes one JSON for asset_ledger.py: every media element with the frames it was seen at (videos:
// the source seconds too) and every component with its props, each under the top-level sequence (the shot) it belongs to.
import React from 'react';
import fs from 'node:fs';
import {renderToStaticMarkup} from 'react-dom/server';
import {COMPS, ERRORS, MEDIA, S, SEQ_STARTS} from './rec';
import {Sequence} from './remotion_stub';

type Shot = {at: number; el: (dur: number) => React.ReactNode};
export type WalkOpts = {id: string; comp: React.ComponentType<Record<string, unknown>>; props?: Record<string, unknown>; seconds: number; fps?: number;
  width: number; height: number; shots?: Shot[]};

// A composition that is its SHOTS list played back to back (a Sequence per shot) builds every shot's element on every frame; this
// root builds only the shots on screen at the sampled frame, with the same Sequences, so a 25-minute film walks in a fraction of the time
const shotsRoot = (shots: Shot[], seconds: number): React.FC => () => {
  const f = (s: number) => Math.round(s * S.fps);
  const els: React.ReactNode[] = [];
  shots.forEach((s, i) => {
    const end = i + 1 < shots.length ? shots[i + 1].at : seconds;
    const from = f(s.at), dur = Math.max(1, f(end) - f(s.at));
    SEQ_STARTS.add(Math.max(0, from));
    if (S.frame >= from && S.frame < from + dur) els.push(React.createElement(Sequence, {key: i, from, durationInFrames: dur}, s.el(end - s.at)));
  });
  return React.createElement(React.Fragment, null, ...els);
};

export const walk = (o: WalkOpts) => {
  S.fps = o.fps ?? 60;
  S.width = o.width;
  S.height = o.height;
  S.durationInFrames = Math.max(1, Math.round(o.seconds * S.fps));
  S.id = o.id;
  const step = Math.max(1, Number(process.env.LEDGER_STEP || 6));
  const el = o.shots ? React.createElement(shotsRoot(o.shots, o.seconds)) : React.createElement(o.comp, o.props ?? {});
  const t0 = Date.now();
  const frames: number[] = [];
  for (let f = 0; f < S.durationInFrames; f += step) frames.push(f);
  if (frames[frames.length - 1] !== S.durationInFrames - 1) frames.push(S.durationInFrames - 1);
  const seen = new Set<number>();
  const render = (list: number[]) => {
    for (const f of list) {
      seen.add(f);
      S.frame = f;
      try {
        renderToStaticMarkup(el);
      } catch (e) {
        ERRORS.push({frame: f, error: String((e as Error)?.message ?? e).slice(0, 400)});
      }
    }
  };
  render(frames);
  // then the first frame of every sequence the samples stepped over (a short shot, a chain's part), until none is left
  for (let pass = 0; pass < 6; pass++) {
    const extra = [...SEQ_STARTS].filter((f) => f < S.durationInFrames && !seen.has(f)).sort((a, b) => a - b);
    if (!extra.length) break;
    render(extra);
    frames.push(...extra);
  }
  const out = {id: o.id, fps: S.fps, width: S.width, height: S.height, frames: S.durationInFrames, step, samples: frames.length,
    ms: Date.now() - t0, media: [...MEDIA.values()], comps: [...COMPS.values()], errors: ERRORS.slice(0, 200), errorCount: ERRORS.length};
  const file = process.env.LEDGER_OUT;
  if (file) fs.writeFileSync(file, JSON.stringify(out));
  console.log(`${o.id}: ${frames.length} frames in ${out.ms} ms; ${out.media.length} media, ${out.comps.length} components, ${ERRORS.length} errors`);
};
