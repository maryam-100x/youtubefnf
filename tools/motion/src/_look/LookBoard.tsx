// LookBoard: one look shown with the studio's real pieces, for the setup's look step (tools/motion/look_board.py renders it once per
// look in tools/motion/looks/, passing the look as inputProps {look, accent}; with no props it shows src/look.json and brand.ts's
// accent). One still, 1920 x 2260: a strip with the look's name, then eight tiles, each a 1920 x 1080 frame at half size, all at
// t 2.5 s (frame 2.5 x FPS, LOOK_BOARD_FRAME):
//   a turn card            a number on its picture
//   a stamp on a picture   the sign-off (like pressed, the comment card)
//   the subscribe ask      a Short with its caption
//   a dated card           a kit3 card with a lit tag
// Nothing here is a video's: the grounds are plain gradients from the look's own colours.
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TurnCard, NumberFrame, Stamp, DateStamp} from '../house/cards';
import {SignOff, SubscribeAsk} from '../house/signoff';
import {Card, Kicker, Headline, Tag} from '../kit3';
import {ACCENT, INK, PAPER, mix} from '../brand';
import {FPS} from '../lib';
import {LOOK, TEXT} from '../look';
import {loadFamily} from '../fonts';

const CAPTION = loadFamily(LOOK.fonts.caption.family, [LOOK.fonts.caption.weight]).fontFamily;
export const LOOK_BOARD_SECONDS = 3;
export const LOOK_BOARD_FRAME = Math.round(2.5 * FPS);
export const LOOK_BOARD_W = 1920;
export const LOOK_BOARD_H = 100 + 4 * 540;
const TOP = 100;

// a stand-in for a picture: a soft diagonal of the look's colours with a light from the upper left
const Ground: React.FC<{hue?: number}> = ({hue = 0}) => (
  <AbsoluteFill style={{background: `radial-gradient(ellipse at 30% 25%, ${mix(PAPER, INK, 0.32)} 0%, transparent 60%),
    linear-gradient(${135 + hue}deg, ${mix(PAPER, ACCENT, 0.35)} 0%, ${mix(PAPER, INK, 0.12)} 55%, ${mix(PAPER, '#000000', 0.4)} 100%)`}} />
);

const Quarter: React.FC<{x: number; y: number; children: React.ReactNode}> = ({x, y, children}) => (
  <div style={{position: 'absolute', left: x * 960, top: TOP + y * 540, width: 1920, height: 1080, transform: 'scale(0.5)', transformOrigin: '0 0',
    overflow: 'hidden'}}>
    <AbsoluteFill>{children}</AbsoluteFill>
  </div>
);

// a Short (1080 x 1920) at half its size, centred in its quarter, with one caption line in the look's caption style
const ShortMock: React.FC = () => {
  const c = LOOK.captions;
  const up = (s: string) => (c.upper ? s.toUpperCase() : s);
  const stroke = `${c.outline}`;
  const shadow = [-1, 0, 1].flatMap((dx) => [-1, 0, 1].map((dy) => `${dx * 5}px ${dy * 5}px 0 ${stroke}`)).join(', ');
  return (
    <AbsoluteFill style={{background: PAPER, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{width: 540, height: 960, position: 'relative', overflow: 'hidden', borderRadius: 24}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920, transform: 'scale(0.5)', transformOrigin: '0 0'}}>
          <Ground hue={40} />
          <div style={{position: 'absolute', left: 60, right: 60, top: 1180, textAlign: 'center', fontFamily: CAPTION,
            fontWeight: LOOK.fonts.caption.weight, fontSize: 110, lineHeight: 1.1, color: c.color, textShadow: shadow}}>
            {up('this changed')} <span style={{color: c.key}}>{up('everything')}</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Strip: React.FC = () => (
  <div style={{position: 'absolute', left: 0, top: 0, width: LOOK_BOARD_W, height: TOP, display: 'flex', alignItems: 'center', gap: 28,
    padding: '0 40px', boxSizing: 'border-box', background: mix(PAPER, '#000000', 0.5), color: INK, fontFamily: TEXT}}>
    <div style={{fontSize: 46, fontWeight: 800}}>{LOOK.name}</div>
    <div style={{fontSize: 28, fontWeight: 500, opacity: 0.7}}>{LOOK.about}</div>
    <div style={{marginLeft: 'auto', display: 'flex', gap: 12}}>
      {[ACCENT, LOOK.colors.ink, LOOK.colors.paper, LOOK.colors.alert].map((c, i) => (
        <div key={i} style={{width: 44, height: 44, borderRadius: 22, background: c, boxShadow: '0 0 0 2px rgba(255,255,255,0.25)'}} />
      ))}
    </div>
  </div>
);

export const LookBoard: React.FC = () => (
  <AbsoluteFill style={{background: PAPER}}>
    <Strip />
    <Quarter x={0} y={0}><TurnCard text="Here's the twist" second="nobody saw it coming" secondAt={0.4} /></Quarter>
    <Quarter x={1} y={0}><NumberFrame value="2,400" source="people asked the same question" at={0.2}><Ground hue={20} /></NumberFrame></Quarter>
    <Quarter x={0} y={1}><Ground hue={-30} /><Stamp text="Confirmed" at={0.3} size={130} /></Quarter>
    <Quarter x={1} y={1}><Ground hue={60} /><SignOff likeAt={0.8} knowAt={1.1} commentsAt={1.5} outAt={99} line="Which one would you pick?" /></Quarter>
    <Quarter x={0} y={2}><Ground hue={90} /><SubscribeAsk clickAt={0.8} bellAt={1.2} exitAt={99} /></Quarter>
    <Quarter x={1} y={2}><ShortMock /></Quarter>
    <Quarter x={0} y={3}><DateStamp date="March 2019" at={0.2} typeDur={0.4} /></Quarter>
    <Quarter x={1} y={3}>
      <Ground hue={-60} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <Card w={1200} at={0.2}>
          <Kicker>The short version</Kicker>
          <Headline>Three things changed</Headline>
          <div style={{marginTop: 28}}><Tag lit={1}>Price</Tag> <Tag>Speed</Tag> <Tag>Size</Tag></div>
        </Card>
      </AbsoluteFill>
    </Quarter>
  </AbsoluteFill>
);
