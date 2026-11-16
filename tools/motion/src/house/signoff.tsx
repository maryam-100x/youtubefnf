// The house asks, drawn in the creator's look (src/look.json: its fonts, surface, corners, shadow, pop, the designs and their words; the
// accent from src/brand.ts):
//   SignOff       the end piece: the like button pressed on "like" (the look's like -> liked words, filled in the accent), the comment
//                 card with the question on its words, popped on "comments"; both go on `outAt`. gate.py's B26 OUTRO reads the look's
//                 like and comment words on screen: a long video whose last 25 s ask for a like and a comment must show them.
//   SubscribeAsk  the halfway ask: the channel's avatar and name, the button pressed on "subscribe", the bell on its word, gone before
//                 the cut.
// Two designs each (look.json signoff.design / subscribe.design): "bar" (low, centred, side by side) and "corner" (a column at the
// right edge). Times are the shot's own seconds (from the voice's words: src/timing.ts). The avatar is CHANNEL.avatar (a public-dir
// path the setup fills); without one, a circle in the accent with the name's first letter. Icons: Lucide (ISC licence, lucide.dev).
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {easeInOut, easeOut, kf, useT} from '../lib';
import {ACCENT, ACCENT_RGB, CHANNEL, INK, INK_RGB, ON_ACCENT, RADIUS, SURFACE} from '../brand';
import {LOOK, SHADOW, SHADOW_SM, TEXT, labelCase, labelTrack} from '../look';

const PATHS: Record<'like' | 'comment' | 'bell', string[]> = {
  like: ['M7 10v12', 'M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z'],
  comment: ['M7.9 20A9 9 0 1 0 4 16.1L2 22Z'],
  bell: ['M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9', 'M10.3 21a1.94 1.94 0 0 0 3.4 0'],
};
const Icon: React.FC<{name: keyof typeof PATHS; size: number; color: string; filled?: boolean; style?: React.CSSProperties}> = ({name, size, color, filled, style}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={filled ? color : 'none'} stroke={color} strokeWidth={2} strokeLinecap="round"
    strokeLinejoin="round" style={{display: 'block', flex: 'none', ...style}}>
    {PATHS[name].map((d) => <path key={d} d={d} />)}
  </svg>
);

const CARD: React.CSSProperties = {background: SURFACE, borderRadius: RADIUS, boxShadow: SHADOW, boxSizing: 'border-box',
  border: LOOK.shape.border ? `${LOOK.shape.border}px solid rgba(${INK_RGB},0.22)` : undefined};
const LABEL: React.CSSProperties = {fontFamily: TEXT, fontWeight: 700, textTransform: labelCase(), letterSpacing: labelTrack, lineHeight: 1,
  whiteSpace: 'nowrap'};
const POP = LOOK.motion.pop;
// a press on `at`: in by 6%, back out past 1 by the look's pop, settled (0 before, 1 after)
const pressScale = (t: number, at: number) => {
  const dn = kf(t, [[at - 0.02, 0], [at + 0.07, 1]], easeInOut);
  const up = kf(t, [[at + 0.07, 0], [at + 0.2, 1], [at + 0.42, 0]], easeInOut);
  return t < at + 0.07 ? 1 - 0.06 * dn : 1 + (POP - 1) * up;
};

// the channel's avatar: its picture, or the name's first letter on the accent
export const Avatar: React.FC<{size: number; style?: React.CSSProperties}> = ({size, style}) => CHANNEL.avatar ? (
  <Img src={staticFile(CHANNEL.avatar)} style={{width: size, height: size, borderRadius: size / 2, objectFit: 'cover', flex: 'none', ...style}} />
) : (
  <div style={{width: size, height: size, borderRadius: size / 2, background: ACCENT, color: ON_ACCENT, display: 'flex', alignItems: 'center', flex: 'none',
    justifyContent: 'center', fontFamily: TEXT, fontWeight: 700, fontSize: size * 0.5, lineHeight: 1, boxSizing: 'border-box', ...style}}>
    {(CHANNEL.name || '?').trim().charAt(0).toUpperCase()}
  </div>
);

// likeAt: when "like" is said (the button arrives 0.75 s before it and is pressed on it); knowAt: when the ask starts (the comment
// card arrives carrying `line`, the question); commentsAt: "comments" (the card pops on it); outAt: both go (past the film's end: the
// film's own fade takes them with the picture)
export const SignOff: React.FC<{likeAt: number; knowAt: number; commentsAt: number; outAt: number; line: string}> = ({likeAt, knowAt, commentsAt, outAt, line}) => {
  const t = useT();
  const W = LOOK.signoff;
  const out = kf(t, [[outAt, 0], [outAt + 0.35, 1]], easeInOut);
  const lp = kf(t, [[likeAt - 0.75, 0], [likeAt - 0.4, 1]], easeOut);
  const on = t >= likeAt + 0.07;
  const cp = kf(t, [[knowAt - 0.1, 0], [knowAt + 0.28, 1]], easeOut);
  const lit = t >= commentsAt;
  const likeS = pressScale(t, likeAt);
  const comS = pressScale(t, commentsAt);
  const likeColor = on ? ON_ACCENT : INK;
  if (W.design === 'corner') {
    // a column at the right edge: two round buttons, the question in a card to the comment button's left
    const B = 116;
    const button = (icon: 'like' | 'comment', filled: boolean, s: number, p: number, bg: string, color: string) => (
      <div style={{width: B, height: B, borderRadius: B / 2, background: bg, boxShadow: SHADOW_SM, display: 'flex', alignItems: 'center',
        justifyContent: 'center', opacity: p, transform: `translateX(${(1 - p) * 60}px) scale(${s})`}}>
        <Icon name={icon} size={52} color={color} filled={filled} />
      </div>
    );
    return (
      <AbsoluteFill style={{opacity: 1 - out, transform: `translateX(${out * 40}px)`}}>
        <div style={{position: 'absolute', right: 96, top: 470, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12}}>
          {button('like', on, likeS, lp, on ? ACCENT : SURFACE, likeColor)}
          <div style={{...LABEL, fontSize: 30, color: INK, opacity: lp, textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>{on ? W.liked : W.like}</div>
        </div>
        <div style={{position: 'absolute', right: 96, top: 690, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12}}>
          {button('comment', lit, comS, cp, lit ? ACCENT : SURFACE, lit ? ON_ACCENT : INK)}
          <div style={{...LABEL, fontSize: 30, color: INK, opacity: cp, textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>{W.comment}</div>
        </div>
        <div style={{...CARD, position: 'absolute', right: 96 + B + 36, top: 690 + B / 2, transform: `translateY(-50%) translateX(${(1 - cp) * 40}px)`,
          opacity: cp, padding: '24px 34px', maxWidth: 1100}}>
          <div style={{fontFamily: TEXT, fontWeight: 600, fontSize: 44, color: INK, lineHeight: 1.15}}>{line}</div>
        </div>
      </AbsoluteFill>
    );
  }
  // "bar": low and centred, the like chip and the comment card side by side
  return (
    <AbsoluteFill style={{opacity: 1 - out, transform: `translateY(${out * 30}px)`, justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 104}}>
      <div style={{display: 'flex', alignItems: 'stretch', gap: 20}}>
        <div style={{...CARD, display: 'flex', alignItems: 'center', gap: 18, padding: '0 38px 0 30px', height: 116,
          background: on ? ACCENT : SURFACE, opacity: lp, transform: `translateY(${(1 - lp) * 36}px) scale(${likeS})`}}>
          <Icon name="like" size={50} color={likeColor} filled={on} />
          <div style={{...LABEL, fontSize: 42, color: likeColor}}>{on ? W.liked : W.like}</div>
        </div>
        <div style={{...CARD, display: 'flex', alignItems: 'center', gap: 22, padding: '0 40px 0 30px', minHeight: 116, opacity: cp,
          transform: `translateY(${(1 - cp) * 36}px) scale(${comS})`, maxWidth: 1180}}>
          <Icon name="comment" size={50} color={lit ? ACCENT : INK} filled={false} />
          <div>
            <div style={{...LABEL, fontSize: 24, color: lit ? ACCENT : `rgba(${INK_RGB},0.66)`}}>{W.comment}</div>
            <div style={{fontFamily: TEXT, fontWeight: 600, fontSize: 40, color: INK, marginTop: 8, lineHeight: 1.12}}>{line}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// the halfway ask: in over 0.4 s, the button pressed on `clickAt`, the bell rung on `bellAt`, out from `exitAt`
export const SubscribeAsk: React.FC<{clickAt: number; bellAt: number; exitAt: number}> = ({clickAt, bellAt, exitAt}) => {
  const t = useT();
  const S = LOOK.subscribe;
  const inn = kf(t, [[0, 0], [0.4, 1]], easeOut);
  const out = kf(t, [[exitAt, 0], [exitAt + 0.3, 1]], easeInOut);
  const e = inn * (1 - out);
  const done = t >= clickAt + 0.07;
  const btnS = pressScale(t, clickAt);
  const rung = t >= bellAt;
  const swing = t > bellAt && t < bellAt + 0.9 ? Math.sin((t - bellAt) * 30) * 12 * (1 - (t - bellAt) / 0.9) : 0;
  const button = (
    <div style={{...LABEL, fontSize: 30, height: 68, padding: '0 34px', display: 'flex', alignItems: 'center', borderRadius: Math.min(RADIUS, 34),
      background: done ? `rgba(${INK_RGB},0.14)` : ACCENT, color: done ? INK : ON_ACCENT, transform: `scale(${btnS})`}}>{done ? S.done : S.button}</div>
  );
  const bell = <Icon name="bell" size={46} color={rung ? ACCENT : INK} filled={rung} style={{transform: `rotate(${swing}deg)`, transformOrigin: '50% 10%'}} />;
  if (S.design === 'corner') {
    return (
      <AbsoluteFill>
        <div style={{...CARD, position: 'absolute', right: 96, top: 96, display: 'flex', alignItems: 'center', gap: 22, padding: '20px 26px 20px 20px',
          opacity: e, transform: `translateX(${(1 - inn) * 80 + out * 40}px)`}}>
          <Avatar size={84} />
          <div style={{fontFamily: TEXT, fontWeight: 700, fontSize: 36, color: INK, lineHeight: 1, whiteSpace: 'nowrap', marginRight: 6}}>{CHANNEL.name}</div>
          {button}
          {bell}
        </div>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 120}}>
      <div style={{...CARD, display: 'flex', alignItems: 'center', gap: 26, padding: '22px 30px 22px 22px', opacity: e,
        transform: `translateY(${(1 - inn) * 40 + out * 24}px)`}}>
        <Avatar size={96} style={{boxShadow: `0 0 0 3px rgba(${ACCENT_RGB},0.5)`}} />
        <div style={{marginRight: 10}}>
          <div style={{fontFamily: TEXT, fontWeight: 700, fontSize: 42, color: INK, lineHeight: 1, whiteSpace: 'nowrap'}}>{CHANNEL.name}</div>
          {CHANNEL.tagline ? <div style={{fontFamily: TEXT, fontWeight: 500, fontSize: 24, color: `rgba(${INK_RGB},0.6)`, marginTop: 10,
            whiteSpace: 'nowrap'}}>{CHANNEL.tagline}</div> : null}
        </div>
        {button}
        {bell}
      </div>
    </AbsoluteFill>
  );
};
