// kit3 · the tokens: the creator's look for every long video (standard/KIT3.md; the look itself: src/look.json): the grid, the type
// scale, one ink, the creator's accent as the one accent (src/brand.ts), one card, one credit, one motion set. Every kit3 component takes its numbers from here: a video never sets its
// own sizes, colours or curves. A video's own palette is NOT a kit3 thing: the brand repeats, the devices don't.
//
//   DS        the grid (content box x 120-1800, y 96-968; centre lines x 960, y 532), spacing (8 16 24 40 64 96), radii, colours, motion
//   TYPE      the five type roles (display 168, headline 84, title 52, label 40, meta 26; the look's display family; tabular figures)
//   type(k)   a role's whole CSS font style
//   enterP / exitP / moveP / lightP / enterStyle   motion progress 0..1 on the house EASE curves (src/house/motion.tsx)
//   markStart / heldT   where a mark's light starts and the time a held layer sees (the picture under a mark stands still)
import type React from 'react';
import {interpolate} from 'remotion';
import {ACCENT, ACCENT_RGB, INK, INK_RGB, ON_ACCENT, RADIUS, RADIUS_CHIP, SURFACE} from '../brand';
import {DISPLAY, DISPLAY_FONT, LOOK, SHADOW as LOOK_SHADOW, SHADOW_SM} from '../look';
import {clamp} from '../lib';
import {EASE} from '../house/motion';

// the one family: the look's display family (src/look.json). Its loader blocks the render until its faces are in; FONTS.waitUntilDone()
// is the only true "ready" for measuring text (document.fonts.load alone can resolve on the fallback face, every width 13% off)
export const FONTS = DISPLAY_FONT;
export const FONT = DISPLAY;
// the family's nearest loaded weight to w (a family without 800 never gets a faux bold)
export const W = (w: number) => LOOK.fonts.display.weights.reduce((a, b) => (Math.abs(b - w) < Math.abs(a - w) ? b : a));
// the look's case for every kit3 text (measured the same way: measure.ts)
export const UPPER = LOOK.type.display_upper;

export const DS = {
  W: 1920,
  H: 1080,
  MX: 120,                       // the content box: x 120-1800
  TOP: 96,                       //                  y 96-968
  BOTTOM: 968,                   // the band below is the credit's (the gate's BOTTOM flags text >= 40 px there)
  CX: 960,
  CY: 532,                       // the content box's centre line: groups centre on it
  SAFE_X: 96,                    // title-safe: the credit's corner
  SAFE_Y: 54,
  S: {xs: 8, s: 16, m: 24, l: 40, xl: 64, xxl: 96},
  R: RADIUS,                     // cards, photo frames, page cards (the look's corners)
  R_CHIP: RADIUS_CHIP,           // chips, marks, the credit's backing
  INK,
  INK2: `rgba(${INK_RGB},0.66)`,
  INK3: `rgba(${INK_RGB},0.3)`,
  ACCENT,                        // the one accent (src/brand.ts), only on what the voice names now
  ACCENT_TINT: `rgba(${ACCENT_RGB},0.14)`,
  ON_ACCENT,
  SURFACE,                       // the look's card surface
  CHIP: SURFACE,
  BORDER: LOOK.shape.border ? `${LOOK.shape.border}px solid rgba(${INK_RGB},0.22)` : 'none',
  SHADOW: LOOK_SHADOW,           // the look's card shadow
  SHADOW_SM,
  CUT_SHADOW: 'drop-shadow(0 22px 34px rgba(0,0,0,0.55))',
  GROUND: {blur: 8, dim: 0.42, scale: 1.04},
  // zoom: Foot's quick zoom into its marks
  DUR: {enter: 0.4, text: 0.3, exit: 0.25, move: 0.9, roll: 1.2, stamp: 0.16, stagger: 0.08, light: 0.12, lead: 0.06, zoom: 0.45},
  RISE: {text: 32, cut: 56, exit: 24},
  PUSH: [1.0, 1.03] as [number, number],
  // marks ("tight and clean"): the box's OUTER edge sits PAD px from the marked ink on every side, its border drawn inside the box
  // (border-box), so the gap between border and letters is PAD - BORDER on all four sides
  MARK: {PAD: 8, BORDER: 4, WASH: 0.85, VEIL: 0.28, LATE: 0.6},
};

export type TypeKey = 'display' | 'headline' | 'title' | 'label' | 'meta';
export const TYPE: Record<TypeKey, {fontSize: number; fontWeight: number; lineHeight: number; letterSpacing: number}> = {
  display: {fontSize: 168, fontWeight: W(LOOK.type.display_weight), lineHeight: 0.92, letterSpacing: LOOK.type.display_tracking},
  headline: {fontSize: 84, fontWeight: W(LOOK.type.display_weight), lineHeight: 1.0, letterSpacing: LOOK.type.display_tracking / 2},
  title: {fontSize: 52, fontWeight: W(700), lineHeight: 1.12, letterSpacing: 0},
  label: {fontSize: 40, fontWeight: W(600), lineHeight: 1.2, letterSpacing: 0},
  meta: {fontSize: 26, fontWeight: W(500), lineHeight: 1.25, letterSpacing: 0},
};
export const type = (k: TypeKey, color: string = DS.INK, weight?: number): React.CSSProperties => ({
  fontFamily: FONT, fontSize: TYPE[k].fontSize, fontWeight: weight ?? TYPE[k].fontWeight, lineHeight: TYPE[k].lineHeight,
  letterSpacing: `${TYPE[k].letterSpacing}em`, color, fontVariantNumeric: 'tabular-nums', fontStyle: 'normal',
  textTransform: UPPER ? 'uppercase' : 'none',
});

// an entrance landing on its word: it starts DUR.lead before `at`, so the thing is there as the word starts
export const enterP = (t: number, at: number | undefined, d: number = DS.DUR.enter) =>
  at === undefined ? 1 : interpolate(t, [at - DS.DUR.lead, at - DS.DUR.lead + d], [0, 1], {...clamp, easing: EASE.enter});
export const exitP = (t: number, at: number | undefined, d: number = DS.DUR.exit) =>
  at === undefined ? 0 : interpolate(t, [at, at + d], [0, 1], {...clamp, easing: EASE.exit});
export const moveP = (t: number, at: number, d: number = DS.DUR.move) => interpolate(t, [at, at + d], [0, 1], {...clamp, easing: EASE.move});
// a word or a mark lighting as it is said (0.04 s before the word, 0.12 s long)
export const lightP = (t: number, at: number) => interpolate(t, [at - 0.04, at - 0.04 + DS.DUR.light], [0, 1], {...clamp, easing: EASE.enter});
export const enterStyle = (u: number, dy: number = DS.RISE.text, dx = 0, out = 0): React.CSSProperties => ({
  opacity: Math.min(1, u / 0.6) * (1 - out),
  transform: `translate(${dx * (1 - u)}px, ${dy * (1 - u) + DS.RISE.exit * out}px)`,
});

// a mark's first frame (its light starts 0.04 s before its word; the picture under it stops DUR.lead before, so it stands still)
export const markStart = (at: number) => Math.max(0, at - DS.DUR.lead);
// Foot's `lift`: a shadow curve for a slightly dim pick (a murky span is re-picked, not lifted), per channel on the picture's own sRGB
// values: v + A v (1 - v)^N. 0 stays 0 and 1 stays 1 (no black point moved, no highlight clipped), never below the source (its slope
// never under 0.8), +63% at 0.05, +6% at 0.2, nothing above 0.35 (tools/motion/lift_check.py measures it: a dark shot's mean 14.4 ->
// 20.0, a daylight shot 91.1 -> 93.3). It replaces the CSS `brightness(1.22) contrast(1.06) saturate(1.06)`, which DARKENED every value
// under 26/255 (contrast pivots on mid-grey) and clipped the darkest to black
export const LIFT = {A: 1.3, N: 14};
export const liftCurve = (v: number) => v + LIFT.A * v * (1 - v) ** LIFT.N;
export const LIFT_TABLE = Array.from({length: 65}, (_, i) => liftCurve(i / 64).toFixed(5)).join(' ');   // 0.24 of a level from the curve
export const heldT = (t: number, hold?: number) => (hold === undefined ? t : Math.min(t, hold));
