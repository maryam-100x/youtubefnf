// see gatecrash_test_index.ts: a piece that throws on frames 10-14 (an easing over an empty list)
import React from 'react';
import {AbsoluteFill, Composition, interpolate, useCurrentFrame} from 'remotion';
import {gated} from './gate';
import {ACCENT} from './brand';

const Piece: React.FC = () => {
  const f = useCurrentFrame();
  const empty: number[] = [];
  const a = f >= 10 && f <= 14 ? Math.min(...empty) : 0;   // Infinity, as an empty word list gives
  const op = interpolate(f, [a, a + 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <div style={{position: 'absolute', left: 100, top: 100, width: 400, height: 200, background: ACCENT, opacity: op}} />;
};

const Comp: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Piece />
  </AbsoluteFill>
);

const GatedComp = gated(Comp);

export const GateCrashRoot: React.FC = () => (
  <Composition id="GateCrash" component={GatedComp} durationInFrames={30} fps={60} width={1920} height={1080} />
);
