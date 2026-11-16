// Cards that carry structure, from the opening studies (standard/research/MOTION_CRAFT.md): turn cards and number frames on the look's
// ground, dated stamps, denial stamps. Small, plain type for turns; the number huge, its source small. Fonts, colours, case, corners and
// the stamp's style are the creator's look (src/look.json).
import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {FPS, clamp} from '../lib';
import {EASE} from './motion';
import {ALERT, INK, INK_RGB, PAPER} from '../brand';
import {DISPLAY, LOOK, TEXT, displayCase} from '../look';

// the look's two families: DISPLAY for headlines and numbers, TEXT for small type (kept as the names the kits import)
export {DISPLAY, TEXT};
const DW = LOOK.type.display_weight;

// A turn card: the voice's linking word ("However", "In fact", "It's 2014") small and centred on black; an optional second line pops on
// at `second` (local s) with the voice. Hold them 1-2.3 s; cut the music under the biggest turn.
export const TurnCard: React.FC<{text: string; second?: string; secondAt?: number; size?: number}> = ({text, second, secondAt = 0.6, size = 96}) => {
  const t = useCurrentFrame() / FPS;
  const pop = second ? interpolate(t, [secondAt, secondAt + 0.08], [0, 1], clamp) : 0;
  return (
    <AbsoluteFill style={{background: PAPER, justifyContent: 'center', alignItems: 'center', flexDirection: 'column'}}>
      <div style={{font: `${DW} ${size}px ${DISPLAY}`, color: INK, letterSpacing: `${LOOK.type.display_tracking}em`, textTransform: displayCase()}}>{text}</div>
      {second ? <div style={{font: `italic 500 ${size * 0.62}px ${TEXT}`, color: INK, opacity: pop, marginTop: 10,
        transform: `scale(${0.96 + 0.04 * pop})`}}>{second}</div> : null}
    </AbsoluteFill>
  );
};

// A dated stamp: black, the date typed letter by letter from `at` over `typeDur` s (each letter lands on a cut-like frame), held.
// Put a boom on `at` in the cue list.
// caret: a typing caret after the last letter (the date typed like on a mechanical keyboard), solid while it types, then blinking
export const DateStamp: React.FC<{date: string; at?: number; typeDur?: number; size?: number; color?: string; caret?: boolean}> = ({date, at = 0, typeDur = 0.35, size = 110, color = INK, caret}) => {
  const t = useCurrentFrame() / FPS;
  const n = Math.floor(interpolate(t, [at, at + typeDur], [0, date.length], clamp));
  const on = t < at + typeDur || Math.floor((t - at - typeDur) * 2.2) % 2 === 1;
  return (
    <AbsoluteFill style={{background: PAPER, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{font: `${DW} ${size}px ${DISPLAY}`, color, letterSpacing: `${Math.max(0.02, LOOK.type.label_tracking)}em`, textTransform: 'uppercase'}}>
        {date.slice(0, n)}
        {caret && t >= at ? <span style={{display: 'inline-block', width: size * 0.07, height: size * 0.9, marginLeft: size * 0.06, verticalAlign: '-0.08em',
          background: color, opacity: on ? 1 : 0}} /> : null}
        <span style={{opacity: 0}}>{date.slice(n)}</span>
      </div>
    </AbsoluteFill>
  );
};

// The number is the frame: the footage behind blurs and darkens while the number scales in over 2 frames;
// the source sits under it in small italics, a receipt without a page.
// count: the number counts up from 0 over this many seconds from `at` (eased out, the digits in place: tabular figures), e.g. 40,000,000
// counting up with a counting sound effect on it
export const NumberFrame: React.FC<{value: string; source?: string; at?: number; children?: React.ReactNode; size?: number; accent?: string; count?: number}> = ({value, source, at = 0, children, size = 340, accent = INK, count}) => {
  const fr = useCurrentFrame();
  const t = fr / FPS;
  const p = interpolate(t, [at, at + 2 / FPS], [0, 1], clamp);
  const target = Number(value.replace(/[^0-9]/g, ''));
  // the backdrop dims and blurs as the number lands on a picture already on screen (at > 0); at a cut (at <= 0) it starts dimmed: ramped
  // from the raw clip, its first frame reads as a flash frame (mean luma 55 -> 123 -> 75)
  const bp = at > 0 ? p : 1;
  const shown = count ? Math.round(target * interpolate(t, [at, at + count], [0, 1], {...clamp, easing: (x) => 1 - Math.pow(1 - x, 3)})).toLocaleString('en-US') : value;
  const settle = interpolate(t, [at + 2 / FPS, at + 0.4], [LOOK.motion.pop, 1], {...clamp, easing: EASE.enter});
  const src = interpolate(t, [at + 0.35, at + 0.6], [0, 1], clamp);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{filter: `blur(${14 * bp}px) brightness(${1 - 0.45 * bp})`, transform: `scale(${1 + 0.04 * bp})`}}>{children}</AbsoluteFill>
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', flexDirection: 'column'}}>
        <div style={{font: `${DW} ${size}px ${DISPLAY}`, color: accent, letterSpacing: `${LOOK.type.display_tracking}em`, opacity: p, transform: `scale(${(0.7 + 0.3 * p) * (p >= 1 ? settle : 1)})`,
          textShadow: '0 8px 40px rgba(0,0,0,0.5)', fontVariantNumeric: 'tabular-nums'}}>{shown}</div>
        {source ? <div style={{font: `italic 500 ${Math.min(size * 0.2, 50)}px ${TEXT}`, color: `rgba(${INK_RGB},0.85)`, opacity: src, marginTop: -size * 0.04,
          maxWidth: 1800, textAlign: 'center'}}>{source}</div> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// A stamp slammed onto a picture ("OUT OF SERVICE"): scale 1.6 -> 1 in 3 frames at the look's tilt; put a stamp/thud on `at`. Its style
// is the look's (stamp.style): "fill" (a solid block), "box" (an outlined box), "underline" (a bar under the words). One line always
// (a stamp wrapped inside a box sized to the frame's edge reads broken).
export const Stamp: React.FC<{text: string; at?: number; x?: number; y?: number; rot?: number; color?: string; size?: number; blend?: 'normal' | 'multiply'}> = ({text, at = 0, x = 960, y = 540, rot = LOOK.stamp.tilt, color = ALERT, size = 120, blend = 'normal'}) => {
  const t = useCurrentFrame() / FPS;
  if (t < at) return null;
  const k = interpolate(t, [at, at + 3 / FPS], [1.6, 1], {...clamp, easing: EASE.enter});
  const style = LOOK.stamp.style;
  const shade = blend === 'normal' ? '0 2px 12px rgba(0,0,0,0.35)' : undefined;
  const look: React.CSSProperties = style === 'fill'
    ? {background: color, color: '#FFFFFF', padding: `${size * 0.08}px ${size * 0.24}px`, borderRadius: Math.min(LOOK.shape.chip, size * 0.12), boxShadow: shade}
    : style === 'underline'
      ? {color, padding: `0 ${size * 0.04}px ${size * 0.06}px`, borderBottom: `${size * 0.09}px solid ${color}`, textShadow: shade}
      : {color, border: `${size * 0.08}px solid ${color}`, padding: `${size * 0.05}px ${size * 0.2}px`, borderRadius: Math.min(LOOK.shape.chip, size * 0.1),
        textShadow: shade, boxShadow: shade};
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${k})`,
      font: `${DW} ${size}px ${DISPLAY}`, letterSpacing: `${Math.max(0.02, LOOK.type.label_tracking)}em`, textTransform: 'uppercase', whiteSpace: 'nowrap',
      mixBlendMode: blend, opacity: 0.96, ...look}}>{text}</div>
  );
};
