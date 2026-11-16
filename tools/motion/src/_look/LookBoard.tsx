// LookBoard: one look shown with the studio's real pieces, for the setup's look step (tools/motion/look_board.py renders it once per
// look in tools/motion/looks/, passing the look as inputProps {look, accent}; with no props it shows src/look.json and brand.ts's
// accent). One still (LOOK_BOARD_W x LOOK_BOARD_H): a strip with the look's name, then eight labelled tiles, each a 1920 x 1080 frame
// at TILE_SCALE, all at t 2.5 s (frame 2.5 x FPS, the frame look_board.py takes):
//   a turn in the story          a number beside the thing it counts (kit3)
//   a stamp on a picture         the end: the question, like and comment
//   the subscribe ask            a Short's captions: a caption and a hero word (two 1080 x 1920 frames inside the tile)
//   a date                       an info card (kit3)
// The pictures are drawn, never anyone's photo, in their own colours as footage has (the look is judged on top of a picture, as in a
// video): Scene here (a city at dusk, a skyline at night, mountains by day, the sea) and, for kit3's number, two files look_board.py
// draws into the bundle's public dir (board/ground.jpg, board/cover.jpg).
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {TurnCard, Stamp, DateStamp} from '../house/cards';
import {SignOff, SubscribeAsk} from '../house/signoff';
import {Card, Kicker, Headline, Label, Lit, NumberBeside} from '../kit3';
import {ACCENT} from '../brand';
import {FPS} from '../lib';
import {LOOK, TEXT} from '../look';
import {loadFamily} from '../fonts';

const CAPTION = loadFamily(LOOK.fonts.caption.family, [LOOK.fonts.caption.weight]).fontFamily;
export const LOOK_BOARD_SECONDS = 3;
export const LOOK_BOARD_FRAME = Math.round(2.5 * FPS);
const STRIP = 110;
const SIDE = 44;
const COL_GAP = 40;
const TILE_W = (1920 - 2 * SIDE - COL_GAP) / 2;   // 896
const TILE_SCALE = TILE_W / 1920;
const TILE_H = 1080 * TILE_SCALE;                 // 504
const LABEL = 44;
const ROW_GAP = 40;
const TOP = STRIP + 30;
export const LOOK_BOARD_W = 1920;
export const LOOK_BOARD_H = TOP + 4 * (LABEL + TILE_H) + 3 * ROW_GAP + SIDE;
const BOARD = '#0D0E11';

// ---- the drawn pictures ----
const seeded = (seed: number) => () => {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
};
// a ridge line across the frame as a closed path (base y, height, roughness), the same every render
const ridge = (seed: number, base: number, amp: number, rough: number) => {
  const r = seeded(seed);
  const p1 = r() * 6.28, p2 = r() * 6.28, p3 = r() * 6.28;
  const pts: string[] = [];
  for (let x = 0; x <= 1920; x += 24) {
    const n = 0.55 + 0.25 * Math.sin(x / 260 + p1) + 0.14 * Math.sin(x / 97 + p2) + rough * Math.sin(x / 31 + p3);
    pts.push(`${x},${(base - amp * n).toFixed(1)}`);
  }
  return `M0,1080 L${pts.join(' L')} L1920,1080 Z`;
};
// a skyline: buildings along the bottom, some windows lit
const City: React.FC<{seed: number; fill: string; lit: number; maxH: number}> = ({seed, fill, lit, maxH}) => {
  const r = seeded(seed);
  const blocks: React.ReactNode[] = [];
  let x = -20;
  let i = 0;
  while (x < 1940) {
    const w = 70 + r() * 120;
    const h = 120 + r() * maxH;
    const top = 1080 - h;
    blocks.push(<rect key={`b${i}`} x={x} y={top} width={w} height={h} fill={fill} />);
    for (let wy = top + 22; wy < 1060; wy += 34) {
      for (let wx = x + 14; wx < x + w - 18; wx += 26) {
        if (r() < lit) blocks.push(<rect key={`w${i}_${wx}_${wy}`} x={wx} y={wy} width={11} height={15} fill="#FFD27F" opacity={0.55 + r() * 0.4} />);
      }
    }
    x += w + 4 + r() * 10;
    i++;
  }
  return <g>{blocks}</g>;
};
type Kind = 'dusk' | 'night' | 'day' | 'sea';
const SKY: Record<Kind, [string, string, string]> = {
  dusk: ['#1D2240', '#6E4664', '#E9966B'],
  night: ['#04060D', '#0C1430', '#22305E'],
  day: ['#3E78BC', '#7FAEDB', '#D3E4F1'],
  sea: ['#24476F', '#6F98C0', '#F0C595'],
};
const Scene: React.FC<{kind: Kind; slice?: boolean}> = ({kind, slice}) => {
  const [a, b, c] = SKY[kind];
  const id = `sky_${kind}`;
  return (
    <svg viewBox="0 0 1920 1080" preserveAspectRatio={slice ? 'xMidYMid slice' : 'none'} style={{position: 'absolute', inset: 0, width: '100%',
      height: '100%'}}>
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={a} /><stop offset="0.55" stopColor={b} /><stop offset="0.8" stopColor={c} />
        </linearGradient>
        <radialGradient id={`${id}_glow`}>
          <stop offset="0" stopColor="#FFE2B0" stopOpacity="0.85" /><stop offset="1" stopColor="#FFE2B0" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}_sea`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3D6E9E" /><stop offset="1" stopColor="#0C223D" />
        </linearGradient>
      </defs>
      <rect width="1920" height="1080" fill={`url(#${id})`} />
      {kind === 'dusk' && <>
        <circle cx="1580" cy="610" r="260" fill={`url(#${id}_glow)`} />
        <circle cx="1580" cy="610" r="74" fill="#FFD9A6" />
        <path d={ridge(7, 760, 260, 0.06)} fill="#4A3A5C" />
        <City seed={11} fill="#181626" lit={0.28} maxH={420} />
      </>}
      {kind === 'night' && <>
        <radialGradient id={`${id}_moon`}>
          <stop offset="0" stopColor="#C9D6F0" stopOpacity="0.35" /><stop offset="1" stopColor="#C9D6F0" stopOpacity="0" />
        </radialGradient>
        <circle cx="420" cy="210" r="170" fill={`url(#${id}_moon)`} />
        <circle cx="420" cy="210" r="44" fill="#E8EDF6" />
        <City seed={23} fill="#0A0E1C" lit={0.45} maxH={560} />
      </>}
      {kind === 'day' && <>
        <circle cx="1530" cy="190" r="190" fill={`url(#${id}_glow)`} opacity="0.7" />
        <circle cx="1530" cy="190" r="56" fill="#FFF6DD" />
        <path d={ridge(3, 760, 420, 0.08)} fill="#7D8FA6" />
        <path d={ridge(5, 860, 300, 0.05)} fill="#55687F" />
        <path d={ridge(9, 980, 200, 0.03)} fill="#3E5A3B" />
        <path d={ridge(13, 1080, 110, 0.02)} fill="#2C4529" />
      </>}
      {kind === 'sea' && <>
        <circle cx="960" cy="560" r="300" fill={`url(#${id}_glow)`} />
        <circle cx="960" cy="560" r="82" fill="#FFE0B0" />
        <rect y="560" width="1920" height="520" fill={`url(#${id}_sea)`} />
        {[0, 1, 2, 3, 4, 5, 6].map((k) => (
          <rect key={k} x={960 - (120 - k * 12)} y={582 + k * 26} width={(120 - k * 12) * 2} height={5} fill="#FFE0B0" opacity={0.6 - k * 0.07} rx={2} />
        ))}
      </>}
    </svg>
  );
};

// ---- the board's frames ----
const Tile: React.FC<{col: number; row: number; label: string; children: React.ReactNode}> = ({col, row, label, children}) => {
  const left = SIDE + col * (TILE_W + COL_GAP);
  const top = TOP + row * (LABEL + TILE_H + ROW_GAP);
  return (
    <>
      <div style={{position: 'absolute', left, top, height: LABEL - 12, display: 'flex', alignItems: 'center', fontFamily: TEXT, fontWeight: 600,
        fontSize: 24, color: 'rgba(255,255,255,0.72)', whiteSpace: 'nowrap'}}>{label}</div>
      <div style={{position: 'absolute', left, top: top + LABEL, width: TILE_W, height: TILE_H, overflow: 'hidden', borderRadius: 12,
        boxShadow: '0 0 0 1px rgba(255,255,255,0.10)'}}>
        <div style={{position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${TILE_SCALE})`, transformOrigin: '0 0',
          overflow: 'hidden'}}>
          <AbsoluteFill>{children}</AbsoluteFill>
        </div>
      </div>
    </>
  );
};

// A Short as the studio burns its captions in (tools/dj/ass.py): a 1080 x 1920 frame at half size. "chunk": one caption chunk, the
// caption font at 5.2% of the height, centred on the frame's middle, an outline of 9% of the size, the key word in the key colour;
// "hero": one hero word, the look's hero scale, all in the key colour, its outline 1.8x.
const ShortFrame: React.FC<{kind: Kind; mode: 'chunk' | 'hero'}> = ({kind, mode}) => {
  const c = LOOK.captions;
  const up = (s: string) => (c.upper ? s.toUpperCase() : s);
  const base = Math.round(1920 * 0.052);
  const hero = mode === 'hero';
  const size = hero ? Math.round(base * c.hero_scale) : base;
  const outline = Math.round(Math.max(4, Math.round(base * 0.09)) * (hero ? 1.8 : 1));
  // round outline corners as libass draws them (a browser's text outline is mitred: spikes on sharp letters), the outline under the fill
  const words = (
    <svg width={1080} height={1920} style={{position: 'absolute', left: 0, top: 0}}>
      <text x={540} y={960} textAnchor="middle" dominantBaseline="central" fontFamily={CAPTION} fontWeight={LOOK.fonts.caption.weight}
        fontSize={size} fill={hero ? c.key : c.color} stroke={c.outline} strokeWidth={outline * 2} strokeLinejoin="round" paintOrder="stroke">
        {hero ? up('huge') : <>{up('so')} <tspan fill={c.key}>{up('fast')}</tspan></>}
      </text>
    </svg>
  );
  return (
    <div style={{width: 540, height: 960, position: 'relative', overflow: 'hidden', borderRadius: 22, boxShadow: '0 0 0 2px rgba(255,255,255,0.14)',
      flex: 'none'}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: 1080, height: 1920, transform: 'scale(0.5)', transformOrigin: '0 0'}}>
        <Scene kind={kind} slice />
        {words}
      </div>
    </div>
  );
};
const ShortMock: React.FC = () => (
  <AbsoluteFill style={{background: '#08090B', flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 90}}>
    <ShortFrame kind="day" mode="chunk" />
    <ShortFrame kind="dusk" mode="hero" />
  </AbsoluteFill>
);

const Strip: React.FC = () => (
  <div style={{position: 'absolute', left: 0, top: 0, width: LOOK_BOARD_W, height: STRIP, display: 'flex', alignItems: 'center', gap: 28,
    padding: `0 ${SIDE}px`, boxSizing: 'border-box', background: '#000000', color: '#FFFFFF', fontFamily: TEXT}}>
    <div style={{fontSize: 48, fontWeight: 800}}>{LOOK.name}</div>
    <div style={{fontSize: 28, fontWeight: 500, opacity: 0.7}}>{LOOK.about}</div>
    <div style={{marginLeft: 'auto', display: 'flex', gap: 12}}>
      {[ACCENT, LOOK.colors.ink, LOOK.colors.paper, LOOK.colors.alert].map((col, i) => (
        <div key={i} style={{width: 44, height: 44, borderRadius: 22, background: col, boxShadow: '0 0 0 2px rgba(255,255,255,0.25)'}} />
      ))}
    </div>
  </div>
);

export const LookBoard: React.FC = () => (
  <AbsoluteFill style={{background: BOARD}}>
    <Strip />
    <Tile col={0} row={0} label="A turn in the story"><TurnCard text="Here's the twist" second="nobody saw it coming" secondAt={0.4} /></Tile>
    <Tile col={1} row={0} label="A number beside what it counts">
      <NumberBeside d={3} picture="board/cover.jpg" pictureH={560} value={12} at={0.4} unit="million" subject="plays in its first week"
        img="board/ground.jpg" />
    </Tile>
    <Tile col={0} row={1} label="A stamp on a picture"><Scene kind="day" /><Stamp text="Confirmed" at={0.3} size={130} /></Tile>
    <Tile col={1} row={1} label="The end: the question, like and comment">
      <Scene kind="sea" /><SignOff likeAt={0.8} knowAt={1.1} commentsAt={1.5} outAt={99} line="Which one would you pick?" />
    </Tile>
    <Tile col={0} row={2} label="The subscribe ask"><Scene kind="night" /><SubscribeAsk clickAt={0.8} bellAt={1.2} exitAt={99} /></Tile>
    <Tile col={1} row={2} label="A Short's captions: a line, a hero word"><ShortMock /></Tile>
    <Tile col={0} row={3} label="A date"><DateStamp date="March 2019" at={0.2} typeDur={0.4} /></Tile>
    <Tile col={1} row={3} label="An info card">
      <Scene kind="dusk" />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <Card at={0.2}>
          <Kicker>The short version</Kicker>
          <Headline>Sales <Lit at={0.6}>doubled</Lit></Headline>
          <Label>in the first month</Label>
        </Card>
      </AbsoluteFill>
    </Tile>
  </AbsoluteFill>
);
