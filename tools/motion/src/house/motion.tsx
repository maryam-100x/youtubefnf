// The house library: the motion techniques tested and judged on their frames (standard/research/MOTION_LAB.md), consolidated so every
// video uses the same, proven pieces. Timing stays in seconds (lib.tsx).
import React from 'react';
import {AbsoluteFill, Easing, interpolate, useCurrentFrame} from 'remotion';
import {HtmlInCanvasMotionBlur} from '@remotion/motion-blur';
import {noise2D} from '@remotion/noise';
import {linearTiming} from '@remotion/transitions';
import {blurSlide} from '@remotion/transitions/blur-slide';
import {zoomBlur} from '@remotion/transitions/zoom-blur';
import {pushCut} from '@remotion/transitions/push-cut';
import {FPS, f, clamp} from '../lib';

// Material 3 motion tokens (MOTION_CRAFT §2): entrances decelerate into rest, exits accelerate away, standard for moves on screen
export const EASE = {
  enter: Easing.bezier(0.05, 0.7, 0.1, 1),
  exit: Easing.bezier(0.3, 0, 0.8, 0.15),
  move: Easing.bezier(0.2, 0, 0, 1),
  drift: Easing.bezier(0.33, 0, 0.2, 1),   // slow camera pushes on stills and pages
};

// Motion blur for anything that moves fast (180° shutter: the film look). Wrap the moving layer, not the whole frame; every animated
// child must read the frame itself (Remotion's rule). Renders in software GL too (MOTION_LAB.md).
export const Blur: React.FC<{children: React.ReactNode; w?: number; h?: number; samples?: number; off?: boolean}> = ({children, w = 1920, h = 1080, samples = 8, off}) => (
  <HtmlInCanvasMotionBlur width={w} height={h} samples={samples} shutterAngle={180} disabled={off}>
    <AbsoluteFill>{children}</AbsoluteFill>
  </HtmlInCanvasMotionBlur>
);

// An impact shake: a noise shake that decays in ~70 ms after `at` (seconds, local). Returns a CSS transform.
export const useShake = (at: number, px = 22, decay = 0.07) => {
  const fr = useCurrentFrame();
  const t0 = f(at);
  const k = fr < t0 ? 0 : Math.exp(-(fr - t0) / (decay * FPS));
  const x = noise2D('sx', fr * 0.9, at) * px * k, y = noise2D('sy', fr * 0.9, at) * px * 0.7 * k, r = noise2D('sr', fr * 0.9, at) * 0.5 * k;
  return `translate(${x}px, ${y}px) rotate(${r}deg)`;
};

// A punch-in on a word: `hard` = one frame (a hard snap), else eased over `dur` (0.3-0.5 s reads as a visible push).
export const usePunch = (at: number, to = 1.25, dur = 0, from = 1) => {
  const fr = useCurrentFrame();
  if (dur <= 0) return fr >= f(at) ? to : from;
  return interpolate(fr, [f(at), f(at + dur)], [from, to], {...clamp, easing: EASE.move});
};

// Transitions for TransitionSeries (judged on their frames). One language per source type; most changes stay hard cuts.
export const CUT = {
  // a camera whip: the outgoing shot streaks sideways; 0.25-0.3 s
  whip: (dir: 'from-left' | 'from-right' = 'from-right', s = 0.28) => ({presentation: blurSlide({direction: dir}), timing: linearTiming({durationInFrames: f(s)})}),
  // a dive into the next shot (into a detail, into a flashback)
  dive: (s = 0.4) => ({presentation: zoomBlur({}), timing: linearTiming({durationInFrames: f(s)})}),
  // punch both shots with a brief flash
  punch: (s = 0.3) => ({presentation: pushCut({}), timing: linearTiming({durationInFrames: f(s)})}),
};
