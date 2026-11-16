// brand.ts: the creator's look, the one place every graphic reads its colours and channel details from (kit3, kit3d, house/, the
// Shorts kits). No piece hard-codes a colour of its own: a change here re-colours every video.
// THE SETUP SETS THE ACCENT from the creator's choice by rewriting the one line `export const BRAND = '#RRGGBB';` below (keep it one
// plain line, single quotes, 6 hex digits: the Python tools read it there, tools/motion/brand.py and tools/sound/autocues.py). Until
// then the neutral default stands: a clear blue. Every other accent token is derived from it here, never typed.

// the one accent: only on what the voice names now (a mark, a lit word, a number landing)
export const BRAND = '#2F80ED';

// '#RRGGBB' -> 'r,g,b' (for rgba() washes and glows)
export const rgbOf = (hex: string) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
};
// relative luminance (WCAG) of '#RRGGBB'
const lum = (hex: string) => {
  const [r, g, b] = rgbOf(hex).split(',').map((v) => {
    const c = Number(v) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

export const ACCENT = BRAND;
export const ACCENT_RGB = rgbOf(BRAND);
// text and icons drawn ON the accent: white on a dark accent, near-black on a light one (whichever contrasts more)
export const ON_ACCENT = (lum(BRAND) + 0.05) / 0.05 >= 1.05 / (lum(BRAND) + 0.05) ? '#0B0C07' : '#FFFFFF';

// the neutral house tones (not the creator's colour; change them only to restyle every video at once)
// light text on dark grounds (headlines, labels, captions' plain words)
export const INK = '#F4EFE6';
export const INK_RGB = rgbOf(INK);
// the dark ground behind cards, stages and the Shorts' empty frames
export const PAPER = '#0A0F14';
export const PAPER_RGB = rgbOf(PAPER);
// the Shorts captions' key-phrase colour (the word the line turns on)
export const KEY = '#FFD21F';
export const KEY_RGB = rgbOf(KEY);

// the channel as the sign-off and the subscribe ask show it (the setup's channel step fills these): `avatar` is the profile picture's
// path in the public dir (e.g. 'brand/avatar.png'); '' draws the name's first letter on the accent instead
export const CHANNEL = {name: 'Your Channel', tagline: '', avatar: ''};
