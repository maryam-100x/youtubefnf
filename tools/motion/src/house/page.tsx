// A real press page or post, staged in depth (the fern / LEMMiNO look; MOTION_CRAFT §3 C1): tilted, the far side out of focus, lit from
// one side, a slow camera push, the quoted words highlighted in reading order the moment the voice reads them, optionally a real macOS
// cursor gliding in and clicking them. The capture comes from tools/footage/capture_page.mjs: a 2x PNG plus `marks` (one box per line,
// in capture px).
//
// It cuts in (a fade from 0 on every page reads as a dip to black between two pages): the page is there on the first frame with the
// camera already moving, one eased push from the first frame to where it lands (a 2% settle in the first 0.3 s and a drift that stops
// before a second, faster push read as "zoom in, pause, and then zoom in again"; qa_zoom.py measures it on a render). `fadeIn` brings
// the old fade back where a page should arrive softly. A long page shows only its part (`crop`, the rest fading out under it) and the
// camera can travel to the quote (`focus`), so the words read at TV size (never walls of small text).
import React from 'react';
import {INK, KEY, KEY_RGB, PAPER, mix} from '../brand';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {linearProgressiveBlur} from '@remotion/effects/linear-progressive-blur';
import {MacOSCursor} from '@remotion/mac-cursors';
import {FPS, clamp} from '../lib';
import {Blur, EASE} from './motion';

export type Mark = {x: number; y: number; w: number; h: number};
export type PageProps = {
  src: string;                 // the capture PNG (public dir)
  capW: number;                // the capture's width in px
  capH?: number;               // its height (needed by `focus` when there is no `crop`)
  marks?: Mark[];              // the quoted phrase, one box per line, capture px
  dur: number;                 // seconds on screen
  W?: number;                  // drawn width (<= 1.35x the capture keeps text crisp)
  hl?: [number, number];       // highlight sweep start/end (local seconds): the voice reading the phrase
  hlEach?: [number, number][]; // or one sweep per mark box (two phrases of one page lit at their own words)
  click?: number;              // the cursor's click time (local seconds); no cursor if undefined
  tilt?: [number, number];     // rotateY, rotateX (degrees)
  push?: [number, number];     // camera scale over the shot
  pushAt?: [number, number];   // the push lands at pushAt[1] (local s; default the shot's end), one move from the first frame. pushAt[0], once
                               // the end of a drift before the push, is not used: a drift, a stop and a push read as a stutter
  pan?: [number, number];      // camera x over the shot (px)
  focus?: [number, number];    // the point the camera travels to (capture px): it ends in the frame's centre
  focus0?: [number, number];   // the point the camera starts on (capture px; default the page's centre): a page's second shot carrying on
                               // from where its first landed (else the camera jumps back to the centre and pushes again)
  crop?: [number, number];     // show only capture rows y0..y1; below y1 the page fades out
  fadeBand?: number;           // px of the crop's fade-out at the bottom (default 150)
  fadeIn?: number;             // seconds of fade from black (default 0: a cut)
  depth?: boolean;             // the far side out of focus (default off: a quote in the blurred half reads poorly; on for a long page)
  dark?: boolean;              // a dark backdrop (default) or a light desk
  masthead?: string;           // the outlet's logo above the page (the real thing)
  paper?: string;              // the card behind the capture: the page's own background (a dark site keeps its dark)
  lightInk?: boolean;          // light text on a dark page: the highlight recolours the words yellow (multiply keeps the dark dark)
  overlays?: {src: string; x: number; y: number; w: number}[];   // sharper images laid in at their place (capture px), under the marks:
                               // e.g. fine print rendered from a PDF inside its box scan, so a 10x push stays sharp (none = as before)
};

// a marker stroke, not a rectangle: rounded uneven ends, a slight tilt, multiply so the text stays black. It marks itself data-gate="mark"
// (no pixel changes): gate.py's B12 MARK_MOVES fails a page that pushes, pans or drifts under its marker
const Marker: React.FC<{m: Mark; k: number; w: number; light?: boolean}> = ({m, k, w, light}) => light ? (
  // light ink: solid yellow multiplied over white text turns the words yellow and leaves the dark page dark (fern's recolour)
  // the band is the line's own glyphs (14-88% of the word box), never the box's leading (a band over the leading reads as a box)
  <div data-gate="mark" style={{position: 'absolute', left: m.x * k, top: m.y * k + m.h * k * 0.14, height: m.h * k * 0.74, width: Math.max(0, w * k), background: KEY,
    mixBlendMode: 'multiply'}} />
) : (
  <div data-gate="mark" style={{position: 'absolute', left: m.x * k - 4, top: m.y * k + m.h * k * 0.08, height: m.h * k * 0.86, width: Math.max(0, w * k + 8),
    background: `linear-gradient(180deg, rgba(${KEY_RGB},0.62), rgba(${KEY_RGB},0.55))`, mixBlendMode: 'multiply',
    borderRadius: '6px 14px 8px 12px / 10px 8px 12px 6px', transform: 'rotate(-0.35deg)'}} />
);

const PAD = 40;

export const PageStage: React.FC<PageProps> = ({src, capW, capH, marks = [], dur, W = 1500, hl, hlEach, click, tilt = [-14, 6], push = [0.95, 1.16],
  pushAt, pan = [60, -80], focus, focus0, crop, fadeBand = 150, fadeIn = 0, depth = false, dark = true, masthead, paper = '#fbfbf8', lightInk, overlays}) => {
  const fr = useCurrentFrame();
  const t = fr / FPS;
  const k = W / capW;
  // the camera: one eased move (EASE.drift) from the first frame, landing at pushAt[1] or the shot's end, then the pan's slow drift alone
  // (a drift to a fifth of the push, a stop, then a push, on top of a 2% settle in the first 0.3 s, are two humps in the camera's speed:
  // qa_zoom.py; it reads as "zoom in, pause, and then zoom in again")
  const cam = interpolate(t, [0, Math.max(1 / FPS, pushAt ? pushAt[1] : dur)], [0, 1], {...clamp, easing: EASE.drift});
  const s = push[0] + (push[1] - push[0]) * cam;
  const x = interpolate(t, [0, dur], pan, clamp);
  const opacity = fadeIn > 0 ? interpolate(t, [0, fadeIn], [0, 1], {...clamp, easing: EASE.enter}) : 1;
  // the drawn page: card padding, the masthead, the visible rows
  const y0 = crop ? crop[0] : 0;
  const rowsH = crop ? (crop[1] - crop[0]) * k : (capH ?? 0) * k;
  const mastH = masthead ? 54 + 26 : 0;
  const pageW = W + 2 * PAD, pageH = rowsH + 2 * PAD + mastH;
  // the focus point's offset from the page's centre (the page sits centred in the frame), carried to the centre by the camera
  const offX = (p: [number, number]) => PAD + p[0] * k - pageW / 2, offY = (p: [number, number]) => PAD + mastH + (p[1] - y0) * k - pageH / 2;
  const fx = focus ? (focus0 ? offX(focus0) * (1 - cam) : 0) + offX(focus) * cam : 0;
  const fy = focus && (crop || capH) ? (focus0 ? offY(focus0) * (1 - cam) : 0) + offY(focus) * cam : 0;
  const total = marks.reduce((a, m) => a + m.w, 0);
  const sweep = hl ? interpolate(t, hl, [0, total], {...clamp, easing: EASE.move}) : 0;
  let before = 0;
  // the cursor: in from the lower right, eased with a little overshoot, pressing 3 frames at `click`
  const m0 = marks[0];
  const tx = m0 ? (m0.x + m0.w * 0.3) * k : 0, ty = m0 ? (m0.y - y0 + m0.h * 0.65) * k : 0;
  const cur = click !== undefined ? interpolate(t, [click - 0.75, click - 0.05], [0, 1], {...clamp, easing: EASE.enter}) : 0;
  const press = click !== undefined && t >= click && t < click + 3 / FPS ? 0.86 : 1;
  const ring = click !== undefined ? interpolate(t, [click, click + 0.45], [0, 1], clamp) : 0;
  // a cropped page fades out over its last `fadeBand` px, so the line above the band stays whole however tight the crop
  const fadeMask = crop ? `linear-gradient(180deg, #000 0px, #000 calc(100% - ${fadeBand}px), transparent 100%)` : undefined;
  return (
    <AbsoluteFill style={{background: dark ? `radial-gradient(ellipse at 35% 40%, ${mix(PAPER, INK, 0.2)} 0%, ${mix(PAPER, '#000000', 0.1)} 72%)` : 'radial-gradient(ellipse at 40% 40%, #f3f1ec 0%, #cfccc4 80%)',
      perspective: 1400, overflow: 'hidden'}}>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity,
        transform: `translateX(${x - fx * s}px) translateY(${-fy * s}px) scale(${s}) rotateY(${tilt[0]}deg) rotateX(${tilt[1]}deg)`,
        transformStyle: 'preserve-3d'}}>
        <div style={{position: 'relative', width: pageW, background: paper, padding: PAD, borderRadius: 4, boxSizing: 'border-box',
          boxShadow: '0 3px 8px rgba(0,0,0,0.45), 0 40px 90px rgba(0,0,0,0.55)', WebkitMaskImage: fadeMask, maskImage: fadeMask}}>
          {masthead ? <Img src={staticFile(masthead)} style={{height: 54, display: 'block', marginBottom: 26}} /> : null}
          <div style={{position: 'relative', overflow: 'hidden', height: crop ? rowsH : undefined}}>
            <div style={{position: 'relative', marginTop: -y0 * k}}>
              <Img src={staticFile(src)} style={{width: W, display: 'block'}}
                effects={depth ? [linearProgressiveBlur({start: [0.55, 0.5], end: [1, 0.5], startBlur: 0, endBlur: 6})] : undefined} />
              {(overlays ?? []).map((o, i) => (
                <Img key={`o${i}`} src={staticFile(o.src)} style={{position: 'absolute', left: o.x * k, top: o.y * k, width: o.w * k, display: 'block'}} />
              ))}
              {marks.map((m, i) => {
                const w = hlEach?.[i] ? interpolate(t, hlEach[i], [0, m.w], {...clamp, easing: EASE.move}) : Math.max(0, Math.min(m.w, sweep - before));
                before += m.w;
                return w > 0 ? <Marker key={i} m={m} k={k} w={w} light={lightInk} /> : null;
              })}
            </div>
            {click !== undefined && ring > 0 && ring < 1 ? (
              <div style={{position: 'absolute', left: tx - 36, top: ty - 36, width: 72, height: 72, borderRadius: 36,
                border: `4px solid rgba(20,20,20,${0.7 * (1 - ring)})`, boxShadow: `0 0 0 2px rgba(255,255,255,${0.7 * (1 - ring)})`,
                transform: `scale(${0.4 + ring})`}} />
            ) : null}
            {click !== undefined && cur > 0 ? (
              // the blur's canvas is taken out of the page's flow (it would push the page's layout)
              <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 1200, pointerEvents: 'none'}}>
                <Blur w={W} h={1200} samples={6}>
                  <div style={{position: 'absolute', left: interpolate(cur, [0, 1], [W * 1.05, tx]), top: interpolate(cur, [0, 1], [ty + 420, ty]),
                    transform: `scale(${3.4 * press})`, transformOrigin: '0 0'}}>
                    <MacOSCursor cursor="default" />
                  </div>
                </Blur>
              </div>
            ) : null}
          </div>
          <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(255,255,255,0.10), rgba(0,0,0,0.18))',
            pointerEvents: 'none', borderRadius: 4}} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
