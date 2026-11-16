// The house asks, drawn in the brand tokens (src/brand.ts) on dark glass:
//   SignOff       the end piece: LIKE pressed to LIKED on "like", a COMMENTS card (the channel's avatar and the question) on its words,
//                 low left; both drop away on `outAt`. gate.py's B26 OUTRO reads its LIKE / COMMENTS text: a long video whose last 25 s
//                 ask for a like and a comment must show it.
//   SubscribeAsk  the halfway ask: a dark glass bar with the avatar, the channel's name and tagline, the button pressed on "subscribe",
//                 the bell on its word, gone before the cut.
// Times are the shot's own seconds (from the voice's words: src/timing.ts). The avatar is CHANNEL.avatar (a public-dir path the setup
// fills); without one, a circle in the accent with the name's first letter.
import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {loadFont as loadInterTight} from '@remotion/google-fonts/InterTight';
import {easeInOut, easeOut, kf, MONT, useT} from '../lib';
import {ACCENT, ACCENT_RGB, CHANNEL, INK, INK_RGB, ON_ACCENT} from '../brand';

export const TIGHT = loadInterTight('normal', {weights: ['400', '500', '600'], subsets: ['latin']}).fontFamily;

const THUMB = 'M2 21h4V9H2v12zm20-11a2 2 0 0 0-2-2h-6.3l1-4.6v-.3c0-.4-.2-.8-.4-1.1L13.2 1 6.6 7.6c-.4.4-.6.9-.6 1.4V19a2 2 0 0 0 2 2h9c.8 0 1.5-.5 1.8-1.2l3-7.1c.1-.2.2-.5.2-.7v-2z';
const GLASS: React.CSSProperties = {background: 'rgba(14,15,16,0.66)', border: `1px solid rgba(${INK_RGB},0.14)`, backdropFilter: 'blur(14px)',
  WebkitBackdropFilter: 'blur(14px)', boxShadow: '0 18px 50px rgba(0,0,0,0.35)'};

// the channel's avatar: its picture, or the name's first letter on the accent
export const Avatar: React.FC<{size: number; style?: React.CSSProperties}> = ({size, style}) => CHANNEL.avatar ? (
  <Img src={staticFile(CHANNEL.avatar)} style={{width: size, height: size, borderRadius: size / 2, objectFit: 'cover', ...style}} />
) : (
  <div style={{width: size, height: size, borderRadius: size / 2, background: ACCENT, color: ON_ACCENT, display: 'flex', alignItems: 'center',
    justifyContent: 'center', fontFamily: TIGHT, fontWeight: 600, fontSize: size * 0.5, lineHeight: 1, boxSizing: 'border-box', ...style}}>
    {(CHANNEL.name || '?').trim().charAt(0).toUpperCase()}
  </div>
);

// likeAt: when "like" is said (the button rises 0.75 s before it and is pressed on it); knowAt: when the ask starts (the COMMENTS card
// lands carrying `line`, the question); commentsAt: "comments" (the card pops on it); outAt: both drop away (past the film's end: the
// film's own fade takes them with the picture)
export const SignOff: React.FC<{likeAt: number; knowAt: number; commentsAt: number; outAt: number; line: string}> = ({likeAt, knowAt, commentsAt, outAt, line}) => {
  const t = useT();
  const out = kf(t, [[outAt, 0], [outAt + 0.35, 1]], easeInOut);
  const lp = kf(t, [[likeAt - 0.75, 0], [likeAt - 0.4, 1]], easeOut);
  const press = kf(t, [[likeAt - 0.02, 0], [likeAt + 0.08, 1], [likeAt + 0.26, 0]], easeInOut);
  const on = t >= likeAt + 0.08;
  const ring = kf(t, [[likeAt + 0.08, 0], [likeAt + 0.55, 1]], easeOut);
  const cp = kf(t, [[knowAt - 0.1, 0], [knowAt + 0.28, 1]], easeOut);
  // the comments box pops on its click (7%: a 3% nudge reads as nothing under the sound)
  const nudge = kf(t, [[commentsAt - 0.02, 0], [commentsAt + 0.1, 1], [commentsAt + 0.32, 0]], easeInOut);
  return (
    <AbsoluteFill style={{opacity: 1 - out, transform: `translateY(${out * 24}px)`}}>
      <div style={{position: 'absolute', left: 96, top: 640, opacity: lp, transform: `translateY(${(1 - lp) * 26}px) scale(${1 - 0.07 * press})`,
        transformOrigin: 'left center'}}>
        <div style={{position: 'absolute', left: -6, top: -6, right: -6, bottom: -6, borderRadius: 60, border: `3px solid ${ACCENT}`,
          opacity: on ? 0.9 * (1 - ring) : 0, transform: `scale(${1 + 0.35 * ring})`}} />
        <div style={{...GLASS, display: 'flex', alignItems: 'center', gap: 20, padding: '20px 36px 20px 28px', borderRadius: 60,
          background: on ? ACCENT : GLASS.background, border: on ? `1px solid ${ACCENT}` : GLASS.border}}>
          <svg width={50} height={50} viewBox="-1 -1 26 26">
            <path d={THUMB} fill={on ? ON_ACCENT : 'none'} stroke={on ? ON_ACCENT : INK} strokeWidth={on ? 0 : 1.7} strokeLinejoin="round" />
          </svg>
          <div style={{fontFamily: MONT, fontWeight: 800, fontSize: 42, letterSpacing: 4, color: on ? ON_ACCENT : INK, lineHeight: 1}}>{on ? 'LIKED' : 'LIKE'}</div>
        </div>
      </div>
      <div style={{position: 'absolute', left: 96, top: 770, opacity: cp, transform: `translateY(${(1 - cp) * 26}px) scale(${1 + 0.07 * nudge})`,
        transformOrigin: 'left center'}}>
        <div style={{...GLASS, display: 'flex', alignItems: 'center', gap: 24, padding: '22px 40px 22px 22px', borderRadius: 26, whiteSpace: 'nowrap'}}>
          <Avatar size={84} style={{border: `2px solid rgba(${ACCENT_RGB},${0.35 + 0.65 * nudge})`}} />
          <div>
            <div style={{fontFamily: MONT, fontWeight: 800, fontSize: 22, letterSpacing: 5, color: `rgba(${INK_RGB},0.62)`}}>COMMENTS</div>
            <div style={{fontFamily: TIGHT, fontWeight: 600, fontSize: 42, color: INK, marginTop: 4}}>{line}</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// the halfway ask: in over 0.4 s, the button pressed on `clickAt`, the bell rung on `bellAt`, out from `exitAt`
export const SubscribeAsk: React.FC<{clickAt: number; bellAt: number; exitAt: number}> = ({clickAt, bellAt, exitAt}) => {
  const t = useT();
  const inn = kf(t, [[0, 0], [0.4, 1]], easeOut);
  const out = kf(t, [[exitAt, 0], [exitAt + 0.3, 1]], easeInOut);
  const e = inn * (1 - out);
  const c = kf(t, [[clickAt, 0], [clickAt + 0.12, 1]], easeOut);
  const press = t > clickAt && t < clickAt + 0.15 ? 0.95 : 1;
  const bell = kf(t, [[bellAt, 0], [bellAt + 0.15, 1]], easeOut);
  const swing = t > bellAt && t < bellAt + 0.9 ? Math.sin((t - bellAt) * 34) * 14 * (1 - (t - bellAt) / 0.9) : 0;
  const BX = 1180;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 420, top: 470, width: 1080, height: 150, borderRadius: 75, background: 'rgba(14,15,18,0.82)', backdropFilter: 'blur(14px)',
        boxShadow: '0 30px 80px rgba(0,0,0,0.5), inset 0 0 0 1.5px rgba(255,255,255,0.1)', opacity: e, transform: `translateY(${(1 - inn) * 40}px)`}}>
        <Avatar size={110} style={{position: 'absolute', left: 20, top: 20}} />
        <div style={{position: 'absolute', left: 156, top: 30}}>
          <div style={{fontFamily: TIGHT, fontWeight: 600, fontSize: 50, color: '#FFFFFF', lineHeight: 1, letterSpacing: -0.8}}>{CHANNEL.name}</div>
          {CHANNEL.tagline ? <div style={{fontFamily: TIGHT, fontWeight: 500, fontSize: 24, color: 'rgba(255,255,255,0.55)', marginTop: 10, letterSpacing: 0.4}}>
            {CHANNEL.tagline}</div> : null}
        </div>
        <div style={{position: 'absolute', left: BX - 420 - 140, top: 75 - 34, width: 280, height: 68, borderRadius: 34, display: 'flex', alignItems: 'center',
          justifyContent: 'center', background: c > 0.5 ? 'rgba(255,255,255,0.14)' : '#FFFFFF', color: c > 0.5 ? '#FFFFFF' : '#0A0A0A', fontFamily: TIGHT, fontWeight: 600,
          fontSize: 28, letterSpacing: 0.3, transform: `scale(${press})`}}>{c > 0.5 ? 'Subscribed' : 'Subscribe'}</div>
        <svg width={50} height={56} viewBox="0 0 64 70" style={{position: 'absolute', left: 1400 - 420 - 25, top: 75 - 28, transform: `rotate(${swing}deg)`, transformOrigin: '50% 8%'}}>
          <path d="M32 4 C 20 4 13 13 13 25 L 13 40 L 6 50 L 58 50 L 51 40 L 51 25 C 51 13 44 4 32 4 Z" fill={bell > 0.5 ? '#FFFFFF' : 'none'} stroke="#FFFFFF" strokeWidth={4}
            strokeLinejoin="round" />
          <path d="M 24 56 C 25 62 39 62 40 56" fill="none" stroke="#FFFFFF" strokeWidth={4} strokeLinecap="round" />
        </svg>
      </div>
    </AbsoluteFill>
  );
};
