// The Short template (1080 x 1920): the Shorts kit (src/shorts, standard/SHORTS.md) on a plain ground, with no media of its own, so it
// renders on a fresh setup. Every element lands on a word of the voice (t.ts). The captions are not drawn here: finish_short.py burns
// them at y ~960. Copy src/_template/short to src/s<NNN>/, write the script's placeholder words into it, register the copy in
// src/Root.tsx as gated(), and act every line out with the creator's real pictures, e.g.
//   <Sequence from={f(b0('S01'))} durationInFrames={f(bStart('S02') - b0('S01'))}>
//     <Pic m={vid('<video>/clips/shot_01.mp4', 1920, 1080)} dur={...} fx={0.5} fy={0.45} credit="Source, platform" />
//   </Sequence>
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FlashIn} from '../../shorts/kitFlash';
import {Num} from '../../shorts/kitCards';
import {Push, Tag9, ground} from '../../shorts/kitS';
import {DURATION, w} from './t';

export const TEMPLATE_SHORT_SECONDS = DURATION;

export const TemplateShort: React.FC = () => (
  <AbsoluteFill style={{background: ground('#1b2433')}}>
    <Push k={0.05}>
      {/* S01: a name label for a thing on screen that has no logo, on its word */}
      <Tag9 name="Your Name" sub="what they do" at={w('S01', 'a name')} />
      {/* S02: a number under the captions, on its word */}
      <Num text="90%" at={w('S02', 'ninety percent')} />
    </Push>
    <FlashIn />
  </AbsoluteFill>
);
