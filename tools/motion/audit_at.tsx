// The clip audit for built Shorts: pipe.py's audit walks a SHOTS list, and Shorts built from <At from to> ranges have none, so their
// clips would go unchecked (every clip covers its shot: a clip that runs out freezes on its last frame).
// This walks the composition's element tree instead: every <At> (a Sequence: its times are relative to the one around it), every element
// carrying a video Media (m= or art=; also inside bg=), the span it plays (start, for as long as its At runs) -> PLAYS_JSON.
// Components of the Short's own file that use hooks can't be called outside a render: they are listed as "opaque" to read by hand.
//   built and run by audit_short.py and frame_review_at.py (esbuild bundle, node)
import React from 'react';
import {__COMP__ as Comp} from '__MODULE__';

type Play = {at: number; len: number; src: string; from: number; comp: string; rate: number};
const plays: Play[] = [];
// every picture placed with the Shorts kit's Cover (Pic, the Short's own covers): its framing, for frame_review_at.py
const frames: Record<string, unknown>[] = [];
const opaque: {at: number; comp: string}[] = [];
const FPS = 60;

const nameOf = (el: any): string => (typeof el.type === 'string' ? el.type : el.type?.displayName || el.type?.name || '?');
const isVideo = (m: any) => m && typeof m === 'object' && typeof m.src === 'string' && /\.(mp4|webm|mov|mkv)$/i.test(m.src);

const walk = (el: any, at: number, d: number, depth = 0): void => {
  if (el == null || typeof el === 'boolean' || depth > 60) return;
  if (Array.isArray(el)) {
    el.forEach((e) => walk(e, at, d, depth + 1));
    return;
  }
  if (typeof el !== 'object' || !el.props) return;
  const p = el.props;
  const name = nameOf(el);
  let nat = at, nd = d;
  if (name === 'At') {
    nat = at + p.from;
    nd = p.to - p.from;
  } else if (name === 'Sequence') {
    nat = at + (p.from ?? 0) / FPS;
    nd = p.durationInFrames != null && isFinite(p.durationInFrames) ? p.durationInFrames / FPS : d - (p.from ?? 0) / FPS;
  }
  for (const k of ['m', 'art']) {
    if (isVideo(p[k])) plays.push({at: nat, len: nd, src: p[k].src, from: p.start ?? 0, comp: name, rate: p.rate ?? 1});
  }
  if (name === 'Cover' && p.m && typeof p.m.src === 'string') {
    frames.push({at: nat, len: nd, src: p.m.src, iw: p.m.iw, ih: p.m.ih, video: !!p.m.video, from: p.start ?? 0, rate: p.rate ?? 1,
      fx: p.fx, fy: p.fy, fx1: p.fx1, fy1: p.fy1, s0: p.s0, s1: p.s1, t0: p.t0, dur: p.dur, box: p.box, filter: p.filter ?? '', path: p.path});
  }
  if (p.bg && typeof p.bg === 'object') walk(p.bg, nat, nd, depth + 1);
  if (p.children !== undefined) {
    walk(p.children, nat, nd, depth + 1);
  } else if (typeof el.type === 'function' && !/^(Img|Credit|Credits|Drop|Box|Print|Tag9|Grade|FlashIn|Cover|OffthreadVideo|Video|Audio)$/.test(name)) {
    // a component without children: call it to see what it renders (kit pieces are pure; a hook throws -> opaque)
    try {
      walk(el.type(p), nat, nd, depth + 1);
    } catch {
      if (!/^(Pic|Card9|Blurred|Receipt9)$/.test(name)) opaque.push({at: nat, comp: name});
    }
  }
};

walk((Comp as any)({}), 0, 0);
const fs = require('fs');
fs.writeFileSync(process.env.PLAYS_JSON as string, JSON.stringify({plays, opaque, frames}, null, 1));
console.log(`${plays.length} video plays, ${opaque.length} opaque components`);
