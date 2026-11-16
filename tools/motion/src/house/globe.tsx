// A designed globe (the Vox / Johnny Harris vector look; MOTION_CRAFT §3 B1): Natural Earth land and borders on an orthographic
// projection, lit from the upper left, a thin atmosphere, and routes that lift off the surface as arcs while the camera turns with them.
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {geoOrthographic, geoPath, geoGraticule10, geoInterpolate} from 'd3-geo';
import {feature, mesh} from 'topojson-client';
import land50 from 'world-atlas/land-50m.json';
import countries50 from 'world-atlas/countries-50m.json';
import {FPS, clamp} from '../lib';
import {ACCENT, INK, PAPER, mix} from '../brand';
import {TEXT} from '../look';

// the globe's tones, all from the look's paper and ink (src/look.json)
const SKY0 = mix(PAPER, INK, 0.06), SKY1 = mix(PAPER, '#000000', 0.5), SEA0 = mix(PAPER, INK, 0.12), SEA1 = mix(PAPER, '#000000', 0.3);
const LANDC = mix(PAPER, INK, 0.24), EDGE = mix(PAPER, INK, 0.55), ATMO = mix(PAPER, INK, 0.6);
import {EASE} from './motion';

const LAND = feature(land50 as never, (land50 as never as {objects: {land: never}}).objects.land);
const BORDERS = mesh(countries50 as never, (countries50 as never as {objects: {countries: never}}).objects.countries, ((a: unknown, b: unknown) => a !== b) as never);

export type Pin = {at: [number, number]; name: string; show: number};   // lon/lat, label, local second it appears
export type Route = {from: [number, number]; to: [number, number]; t: [number, number]};   // drawn between local seconds t[0]..t[1]

export const Globe: React.FC<{dur: number; pins?: Pin[]; routes?: Route[]; look?: [[number, number], [number, number]]; zoom?: [number, number];
  accent?: string; cx?: number; cy?: number}> = ({dur, pins = [], routes = [], look, zoom = [430, 520], accent = ACCENT, cx = 960, cy = 560}) => {
  const fr = useCurrentFrame();
  const t = fr / FPS;
  // the camera: from look[0] to look[1] (lon/lat) over the shot, or following the first route
  const r0 = routes[0];
  const p0 = r0 ? interpolate(t, r0.t, [0, 1], {...clamp, easing: EASE.move}) : 0;
  const centre: [number, number] = look
    ? geoInterpolate(look[0], look[1])(interpolate(t, [0, dur], [0, 1], {...clamp, easing: EASE.drift})) as [number, number]
    : r0 ? geoInterpolate(r0.from, r0.to)(Math.min(1, 0.08 + p0 * 0.84)) as [number, number] : [0, 20];
  const scale = interpolate(t, [0, dur], zoom, clamp);
  const proj = geoOrthographic().scale(scale).translate([cx, cy]).rotate([-centre[0], -centre[1] * 0.85, 0]).clipAngle(90);
  const path = geoPath(proj);
  const arc = (r: Route) => {
    const p = interpolate(t, r.t, [0, 1], {...clamp, easing: EASE.move});
    const ip = geoInterpolate(r.from, r.to);
    const n = 64, pts: [number, number][] = [];
    const qa = proj(r.from), qb = proj(r.to);
    const chord = qa && qb ? Math.hypot(qb[0] - qa[0], qb[1] - qa[1]) : 0;
    for (let i = 0; i <= n * p; i++) {
      const s = i / n;
      const q = proj(ip(s) as [number, number]);
      if (!q) continue;
      // the flight arc: lifted toward the top of the frame, highest at its middle (0.22 of the chord)
      pts.push([q[0], q[1] - 0.22 * chord * Math.sin(Math.PI * s)]);
    }
    return {d: pts.length > 1 ? 'M' + pts.map((q) => q.join(',')).join('L') : '', head: pts[pts.length - 1], p};
  };
  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 45%, ${SKY0} 0%, ${SKY1} 78%)`}}>
      <svg width={1920} height={1080}>
        <defs>
          <radialGradient id="g-sea" cx="38%" cy="32%" r="75%"><stop offset="0%" stopColor={SEA0} /><stop offset="100%" stopColor={SEA1} /></radialGradient>
          <radialGradient id="g-atmo" cx="50%" cy="50%" r="50%">
            <stop offset="88%" stopColor={ATMO} stopOpacity="0" /><stop offset="93%" stopColor={ATMO} stopOpacity="0.22" /><stop offset="100%" stopColor={ATMO} stopOpacity="0" />
          </radialGradient>
          <radialGradient id="g-light" cx="34%" cy="28%" r="80%"><stop offset="0%" stopColor="#ffffff" stopOpacity="0.10" /><stop offset="55%" stopColor="#000000" stopOpacity="0" /><stop offset="100%" stopColor="#000000" stopOpacity="0.45" /></radialGradient>
          <filter id="g-glow"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <circle cx={cx} cy={cy} r={scale * 1.09} fill="url(#g-atmo)" />
        <path d={path({type: 'Sphere'} as never) ?? ''} fill="url(#g-sea)" />
        <path d={path(geoGraticule10()) ?? ''} fill="none" stroke="#ffffff" strokeOpacity={0.045} strokeWidth={1} />
        <path d={path(LAND as never) ?? ''} fill={LANDC} />
        <path d={path(BORDERS as never) ?? ''} fill="none" stroke={EDGE} strokeOpacity={0.35} strokeWidth={0.7} />
        <path d={path({type: 'Sphere'} as never) ?? ''} fill="url(#g-light)" />
        {routes.map((r, i) => {
          const a = arc(r);
          return (
            <g key={i}>
              <path d={a.d} fill="none" stroke={accent} strokeOpacity={0.35} strokeWidth={10} strokeLinecap="round" filter="url(#g-glow)" />
              <path d={a.d} fill="none" stroke={accent} strokeWidth={3.5} strokeLinecap="round" />
              {a.head && a.p < 1 ? <circle cx={a.head[0]} cy={a.head[1]} r={7} fill="#ffffff" filter="url(#g-glow)" /> : null}
            </g>
          );
        })}
        {pins.map((p, i) => {
          const q = proj(p.at);
          if (!q) return null;
          const o = interpolate(t, [p.show, p.show + 0.35], [0, 1], clamp);
          const pulse = (t * 1.2) % 1;
          return (
            <g key={i} opacity={o}>
              <circle cx={q[0]} cy={q[1]} r={7} fill={accent} />
              <circle cx={q[0]} cy={q[1]} r={7 + 20 * pulse} fill="none" stroke={accent} strokeOpacity={0.6 * (1 - pulse)} strokeWidth={2} />
              <text x={q[0] + 18} y={q[1] - 16} fill={INK} style={{font: `700 30px ${TEXT}`, letterSpacing: 1}}>{p.name}</text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
