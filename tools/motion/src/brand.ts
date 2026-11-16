// brand.ts: the creator's accent and channel, and the one place every graphic reads its colours from (kit3, kit3d, house/, the Shorts
// kits): the accent here, the other tones from their look (src/look.json, look.ts). No piece hard-codes a colour of its own.
// THE SETUP SETS THE ACCENT from the creator's choice by rewriting the one line `export const BRAND = '#RRGGBB';` below (keep it one
// plain line, single quotes, 6 hex digits: the Python tools read it there, tools/motion/brand.py and tools/sound/autocues.py). Until
// then the starting look's own accent stands (looks/clean.json's key). Every other accent token is derived from it here, never typed.

import {ACCENT_TRY, LOOK} from './look';

// the one accent: only on what the voice names now (a mark, a lit word, a number landing)
export const BRAND = '#6EE7C8';

// '#RRGGBB' -> 'r,g,b' (for rgba() washes and glows)
export const rgbOf = (hex: string) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
};
// '#RRGGBB' between a (t 0) and b (t 1): tones derived from the look's own colours, never typed
export const mix = (a: string, b: string, t: number) => {
  const [r1, g1, b1] = rgbOf(a).split(',').map(Number);
  const [r2, g2, b2] = rgbOf(b).split(',').map(Number);
  const h = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, '0');
  return `#${h(r1, r2)}${h(g1, g2)}${h(b1, b2)}`;
};
// relative luminance (WCAG) of '#RRGGBB'
const lum = (hex: string) => {
  const [r, g, b] = rgbOf(hex).split(',').map((v) => {
    const c = Number(v) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

// the accent every graphic uses: BRAND (a render may try another, inputProps.accent: the look board)
export const ACCENT = ACCENT_TRY ?? BRAND;
export const ACCENT_RGB = rgbOf(ACCENT);
// text and icons drawn ON the accent: white on a dark accent, near-black on a light one (whichever contrasts more)
export const ON_ACCENT = (lum(ACCENT) + 0.05) / 0.05 >= 1.05 / (lum(ACCENT) + 0.05) ? '#0B0C07' : '#FFFFFF';

// the look's tones (src/look.json, the creator's look; never typed here)
// light text on dark grounds (headlines, labels, captions' plain words)
export const INK = LOOK.colors.ink;
export const INK_RGB = rgbOf(INK);
// the dark ground behind cards, stages and the Shorts' empty frames
export const PAPER = LOOK.colors.paper;
export const PAPER_RGB = rgbOf(PAPER);
// the key colour: the Shorts captions' key phrase, highlighter strokes, name dashes
export const KEY = LOOK.colors.key;
export const KEY_RGB = rgbOf(KEY);
// the alert colour: stamps, crosses, "wrong" marks
export const ALERT = LOOK.colors.alert;
export const ALERT_RGB = rgbOf(ALERT);
// the card surface (solid, at the look's opacity) and the look's corners
export const SURFACE = `rgba(${rgbOf(LOOK.colors.surface)},${LOOK.colors.surface_alpha})`;
export const RADIUS = LOOK.shape.radius;
export const RADIUS_CHIP = LOOK.shape.chip;

// the channel as the sign-off and the subscribe ask show it (the setup's channel step fills these): `avatar` is the profile picture's
// path in the public dir (e.g. 'brand/avatar.png'); '' draws the name's first letter on the accent instead
export const CHANNEL = {name: 'Your Channel', tagline: '', avatar: ''};
