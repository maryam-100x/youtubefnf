// look.ts: the creator's look, read from src/look.json (the setup's look step writes it from one of tools/motion/looks/ and their
// notes). Every graphic takes its fonts, colours, corners, shadows, pop and the asks' designs and words from here; the accent colour is
// brand.ts's. A render can try another look without touching the file: inputProps {look: {...}} (tools/motion/look_board.py does).
//
//   LOOK               the whole look (look.json, or the render's inputProps.look)
//   ACCENT_TRY         inputProps.accent, a render's own accent (the look board's); null in videos
//   DISPLAY / TEXT     the two font families (headlines, numbers, cards / labels, credits, small text), loaded
//   DISPLAY_FONT       its loader: DISPLAY_FONT.waitUntilDone() is the true "ready" for measuring text
//   SHADOW / SHADOW_SM the look's card shadow and a small one (chips, buttons); SHADOW_GROUP the card shadow for a row of pieces
//   displayCase / labelCase / labelTrack   the type's case and tracking as CSS
import type React from 'react';
import {getInputProps} from 'remotion';
import base from './look.json';
import {loadFamily} from './fonts';

export type Look = typeof base;

const props = (() => {
  try {
    return (getInputProps() as {look?: Look; accent?: string}) || {};
  } catch {
    return {};
  }
})();
const override = props.look ?? null;
// a render's own accent (the look board shows each look in its suggested accent, its key colour); videos use brand.ts's BRAND
export const ACCENT_TRY: string | null = typeof props.accent === 'string' && /^#[0-9A-Fa-f]{6}$/.test(props.accent) ? props.accent : null;

export const LOOK: Look = override ? {...base, ...override} : base;

export const DISPLAY_FONT = loadFamily(LOOK.fonts.display.family, LOOK.fonts.display.weights);
export const TEXT_FONT = loadFamily(LOOK.fonts.text.family, LOOK.fonts.text.weights);
export const DISPLAY = DISPLAY_FONT.fontFamily;
export const TEXT = TEXT_FONT.fontFamily;
export const FONTS_READY = () => Promise.all([DISPLAY_FONT.waitUntilDone(), TEXT_FONT.waitUntilDone()]);

export const displayCase = (): React.CSSProperties['textTransform'] => (LOOK.type.display_upper ? 'uppercase' : 'none');
export const labelCase = (): React.CSSProperties['textTransform'] => (LOOK.type.label_upper ? 'uppercase' : 'none');
export const labelTrack = `${LOOK.type.label_tracking}em`;

// the third: SHADOW as a filter for a group of pieces side by side (a row of buttons): the group casts one shadow under all of them,
// so one piece's shadow never falls on its neighbour
const SHADOWS: Record<string, [string, string, string]> = {
  soft: ['0 2px 6px rgba(0,0,0,0.3), 0 24px 64px rgba(0,0,0,0.5)', '0 2px 4px rgba(0,0,0,0.3), 0 10px 24px rgba(0,0,0,0.35)',
    'drop-shadow(0 2px 6px rgba(0,0,0,0.3)) drop-shadow(0 24px 64px rgba(0,0,0,0.5))'],
  hard: ['10px 10px 0 rgba(0,0,0,0.92)', '5px 5px 0 rgba(0,0,0,0.92)', 'drop-shadow(10px 10px 0 rgba(0,0,0,0.92))'],
  none: ['none', 'none', 'none'],
};
export const [SHADOW, SHADOW_SM, SHADOW_GROUP] = SHADOWS[LOOK.shape.shadow] ?? SHADOWS.soft;
