// The long-form template: a few shots built from kit3 (src/kit3, standard/KIT3.md) and the house sign-off, each starting on a word of
// the voice (t.ts), with no media of its own, so it renders on a fresh setup. Copy src/_template/long to src/v<NNN>/, write the script's
// placeholder words into it (placeholder_words.py), register the copy in src/Root.tsx as gated(), and replace these shots with the
// video's: a shot is {at: a word's time, el: (its length) => what it draws}, the next shot's start ends it.
import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame} from 'remotion';
import {f} from '../../lib';
import {NumberBeside, Read, Stage, Timeline} from '../../kit3';
import {SignOff} from '../../house/signoff';
import {Shot, b0, bEnd, check, w} from './t';

const FADE = 1.2;
const FILM_END = () => bEnd('S04') + 1.6;
export const TEMPLATE_SECONDS = FILM_END();

// a shot starting on its word: `t0` its start, so the times inside it are the shot's own seconds
const shot = (at: number, el: (d: number, t0: number) => React.ReactNode): Shot => ({at, el: (d) => el(d, at)});

export const SHOTS: Shot[] = [
  // S01: someone's words read, the phrase the voice leans on lit on its word
  shot(b0('S01'), (d, t0) => (
    <Read d={d} kicker="The template" lines={['Every shot starts on', 'a word of the voice']}
      lit={[{text: 'a word of the voice', at: w('S01', 'a word of the voice') - t0}]} />
  )),
  // S02: three dates at their true distances, each on its word
  shot(b0('S02'), (d, t0) => (
    <Timeline d={d} kicker="A project, in dates" marks={[
      {date: 'Jan 10', what: 'the idea', day: 0, at: w('S02', 'The idea') - t0},
      {date: 'Mar 2', what: 'the first draft', day: 51, at: w('S02', 'the first draft') - t0},
      {date: 'Apr 18', what: 'the release', day: 98, at: w('S02', 'the release') - t0}]} />
  )),
  // S03: a number with its unit and its subject; a number about a thing stands beside that thing (`picture`), this one has none
  shot(b0('S03'), (d, t0) => (
    <NumberBeside d={d} value={98} at={w('S03', 'ninety-eight') - t0} unit="days" subject="from the first idea to the release"
      kicker="From idea to release" noPicture="a span of time: there is no picture of it" />
  )),
  // S04: the house sign-off on the last line's ask (gate.py's B26 OUTRO wants its LIKE and COMMENTS when the last line asks)
  shot(b0('S04'), (d, t0) => (
    <Stage dur={d}>
      <SignOff likeAt={w('S04', 'like') - t0} knowAt={w('S04', 'tell me') - t0} commentsAt={w('S04', 'comments') - t0} outAt={999}
        line="What will you make?" />
    </Stage>
  )),
].sort((a, b) => a.at - b.at);

const Fade: React.FC<{end: number}> = ({end}) => {
  const fr = useCurrentFrame();
  const o = interpolate(fr, [f(end - FADE), f(end)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return o > 0 ? <AbsoluteFill style={{background: '#000', opacity: o}} /> : null;
};

export const Template: React.FC = () => {
  check();
  const end = FILM_END();
  return (
    <AbsoluteFill style={{background: '#000'}}>
      {SHOTS.map((s, i) => {
        const e = i + 1 < SHOTS.length ? SHOTS[i + 1].at : end;
        return (
          <Sequence key={i} from={f(s.at)} durationInFrames={Math.max(1, f(e) - f(s.at))}>
            {s.el(e - s.at)}
          </Sequence>
        );
      })}
      <Fade end={end} />
    </AbsoluteFill>
  );
};
