// The house asks, drawn in the creator's look (src/look.json: its fonts, surface, corners, shadow, pop, the designs and their words; the
// accent from src/brand.ts):
//   SignOff       the end piece: the question card (the voice's ask, on its words) over the like and comment buttons; the like pressed
//                 on "like" (the look's like -> liked words, filled in the accent), the comment button lit on "comments"; all go on
//                 `outAt`. gate.py's B26 OUTRO reads the look's like and comment words on screen: a long video whose last 25 s ask for a
//                 like and a comment must show them.
//   SubscribeAsk  the halfway ask: the channel's avatar and name, the button pressed on "subscribe", the bell on its word, gone before
//                 the cut.
// Two designs each (look.json signoff.design / subscribe.design): "bar" (low and centred) and "corner" (the sign-off at the lower
// right, the subscribe card at the upper right), all on the same safe edge (EDGE). Times are the shot's own seconds (from the voice's
// words: src/timing.ts). The avatar is CHANNEL.avatar (a public-dir path the setup fills); without one, a circle in the accent with
// the name's first letter. Icons: Lucide (ISC licence, lucide.dev).
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {easeInOut, easeOut, kf, useT} from '../lib';
import {ACCENT, CHANNEL, INK, INK_RGB, ON_ACCENT, RADIUS, SURFACE} from '../brand';
import {LOOK, SHADOW, SHADOW_GROUP, TEXT, TRACK_END, labelCase, labelTrack} from '../look';

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
// the frame's safe edge for every ask (from the frame's sides and its bottom or top), the gap between pieces, the buttons' height
const EDGE = 96;
const GAP = 18;
const BUTTON_H = 92;
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

// likeAt: when "like" is said (the buttons arrive 0.75 s before it and the like is pressed on it); knowAt: when the ask starts (the
// question card arrives carrying `line`); commentsAt: "comments" (the comment button pops and lights on it); outAt: all go (past the
// film's end: the film's own fade takes them with the picture).
// One column on one axis: the question card on top, the like and comment buttons in a row under it, every piece the same card style
// and the two buttons the same height. "bar" centres the column low in the frame; "corner" sets it at the lower right, every right edge
// on one line. Nothing moves when a label changes (a button is as wide as its longer label).
export const SignOff: React.FC<{likeAt: number; knowAt: number; commentsAt: number; outAt: number; line: string}> = ({likeAt, knowAt, commentsAt, outAt, line}) => {
  const t = useT();
  const W = LOOK.signoff;
  const corner = W.design === 'corner';
  const out = kf(t, [[outAt, 0], [outAt + 0.35, 1]], easeInOut);
  const bp = kf(t, [[likeAt - 0.75, 0], [likeAt - 0.4, 1]], easeOut);
  const liked = t >= likeAt + 0.07;
  const qp = kf(t, [[knowAt - 0.1, 0], [knowAt + 0.28, 1]], easeOut);
  const lit = t >= commentsAt + 0.07;
  const button = (icon: 'like' | 'comment', on: boolean, scale: number, labels: string[], shown: string) => (
    <div style={{...CARD, height: BUTTON_H, padding: `0 ${BUTTON_H * 0.36}px 0 ${BUTTON_H * 0.3}px`, display: 'flex', alignItems: 'center',
      gap: BUTTON_H * 0.18, borderRadius: Math.min(RADIUS, BUTTON_H / 2), background: on ? ACCENT : SURFACE, boxShadow: 'none',
      transform: `scale(${scale})`}}>
      <Icon name={icon} size={BUTTON_H * 0.44} color={on ? ON_ACCENT : INK} filled={on} />
      <div style={{display: 'grid'}}>
        {labels.map((l) => (
          <div key={l} style={{...LABEL, ...TRACK_END(LOOK.type.label_tracking), gridArea: '1 / 1', fontSize: BUTTON_H * 0.39,
            color: on ? ON_ACCENT : INK, visibility: l === shown ? 'visible' : 'hidden'}}>{l}</div>
        ))}
      </div>
    </div>
  );
  return (
    <AbsoluteFill style={{opacity: 1 - out}}>
      <div style={{position: 'absolute', bottom: EDGE, ...(corner ? {right: EDGE} : {left: 0, right: 0}), display: 'flex',
        flexDirection: 'column', alignItems: corner ? 'flex-end' : 'center', gap: GAP, transform: `translateY(${out * 30}px)`}}>
        <div style={{...CARD, padding: '26px 38px 28px', maxWidth: 1100, opacity: qp, transform: `translateY(${(1 - qp) * 30}px)`}}>
          <div style={{fontFamily: TEXT, fontWeight: 600, fontSize: 46, color: INK, lineHeight: 1.15}}>{line}</div>
        </div>
        {/* the row casts one shadow under both buttons (SHADOW_GROUP): the comment button's never falls on the like button */}
        <div style={{display: 'flex', gap: GAP, opacity: bp, transform: `translateY(${(1 - bp) * 36}px)`, filter: SHADOW_GROUP}}>
          {button('like', liked, pressScale(t, likeAt), [W.like, W.liked], liked ? W.liked : W.like)}
          {button('comment', lit, pressScale(t, commentsAt), [W.comment], W.comment)}
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
      background: done ? `rgba(${INK_RGB},0.14)` : ACCENT, color: done ? INK : ON_ACCENT, transform: `scale(${btnS})`}}>
      <span style={TRACK_END(LOOK.type.label_tracking)}>{done ? S.done : S.button}</span></div>
  );
  const bell = <Icon name="bell" size={46} color={rung ? ACCENT : INK} filled={rung} style={{transform: `rotate(${swing}deg)`, transformOrigin: '50% 10%'}} />;
  if (S.design === 'corner') {
    return (
      <AbsoluteFill>
        <div style={{...CARD, position: 'absolute', right: EDGE, top: EDGE, display: 'flex', alignItems: 'center', gap: 22, padding: '18px 28px 18px 18px',
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
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: EDGE}}>
      <div style={{...CARD, display: 'flex', alignItems: 'center', gap: 26, padding: '18px 30px 18px 18px', opacity: e,
        transform: `translateY(${(1 - inn) * 40 + out * 24}px)`}}>
        <Avatar size={96} />
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
