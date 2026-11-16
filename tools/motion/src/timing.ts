// Word-anchored timing: every cue in a composition is a word of the voice, never a typed second. A video's src/<folder>/words.json
// ([{w, start, end, beat}]) and beats.json ({duration, beats: [{id, start, voice_end, end}]}) come from sync_words.py (the voice's own
// times) or, before the voice exists, from placeholder_words.py (the same two files from the script at the house voice's pace, beats.json
// saying "placeholder": true). A new take re-times the video by itself. Each video's own t.ts makes its helpers once:
//
//   import words from './words.json';
//   import beats from './beats.json';
//   export const {w, we, wl, b0, bEnd, bStart, bVoice, bStop, MISSES, check, DURATION, PLACEHOLDER} = timing(words, beats);
//
//   w(beat, phrase, off?, nth?)   when a phrase starts inside a beat (+ off s; nth picks a later match in the same beat)
//   we(beat, phrase, off?, nth?)  when it ends (its last word's end)
//   wl(beat, phrase, nth?)        when its LAST word starts ("basic one" -> when "one" starts)
//   b0(beat, off?) / bEnd(beat)   the beat's first word's start / its last word's end (the voice's real onset and end)
//   bStart / bVoice / bStop(beat) the beat's slot in beats.json: its start, the end of its voice, the end of its slot (the next start);
//                                 the only anchors a hold has (a beat with no narration words of its own)
//
// Words match ignoring case and punctuation ("youve" matches "you've"). A phrase the voice no longer says:
//   long form (the default): never throws at import; it is recorded in MISSES and returns the beat's first word, and the composition
//     calls check() before it renders (it throws with every miss named, so the fix is in the error)
//   Shorts ({strict: true}): throws at once
import type React from 'react';

export type Word = {w: string; start: number; end: number; beat: string};
export type Beat = {id: string; start: number; voice_end: number; end: number};
export type Beats = {duration: number; placeholder?: boolean; narration?: string; note?: string; beats: Beat[]};
// a shot of a long video: where it starts (seconds of the film, from the words) and what it draws for its length
export type Shot = {at: number; el: (dur: number) => React.ReactNode};

export const norm = (s: string) => s.toLowerCase().replace(/[’']/g, '').replace(/[^a-z0-9]/g, '');

export const timing = (wordsJson: unknown, beatsJson: unknown, opts: {strict?: boolean} = {}) => {
  const WORDS = wordsJson as Word[];
  const BEATS = beatsJson as Beats;
  const MISSES: string[] = [];
  const miss = (msg: string, beat: string) => {
    if (opts.strict) throw new Error(`timing: ${msg}`);
    MISSES.push(msg);
    const x = WORDS.find((y) => y.beat === beat);
    return x ? x.start : 0;
  };
  // the indices of a phrase's first and last word inside a beat, or null
  const find = (beat: string, phrase: string, nth: number): [number, number] | null => {
    const toks = phrase.split(/\s+/).map(norm).filter(Boolean);
    if (!toks.length) return null;
    let seen = 0;
    for (let i = 0; i < WORDS.length; i++) {
      if (WORDS[i].beat !== beat) continue;
      if (toks.every((tk, k) => WORDS[i + k] && WORDS[i + k].beat === beat && norm(WORDS[i + k].w) === tk)) {
        if (seen === nth) return [i, i + toks.length - 1];
        seen++;
      }
    }
    return null;
  };
  const w = (beat: string, phrase: string, off = 0, nth = 0) => {
    const r = find(beat, phrase, nth);
    return r ? WORDS[r[0]].start + off : miss(`"${phrase}" (#${nth}) is not in ${beat}`, beat);
  };
  const we = (beat: string, phrase: string, off = 0, nth = 0) => {
    const r = find(beat, phrase, nth);
    return r ? WORDS[r[1]].end + off : miss(`"${phrase}" (#${nth}) is not in ${beat}`, beat) + off;
  };
  const wl = (beat: string, phrase: string, nth = 0) => {
    const r = find(beat, phrase, nth);
    return r ? WORDS[r[1]].start : miss(`"${phrase}" (#${nth}) is not in ${beat}`, beat);
  };
  const b0 = (beat: string, off = 0) => {
    const x = WORDS.find((y) => y.beat === beat);
    return x ? x.start + off : miss(`no words in ${beat}`, '') + off;
  };
  const bEnd = (beat: string) => {
    const xs = WORDS.filter((y) => y.beat === beat);
    return xs.length ? xs[xs.length - 1].end : miss(`no words in ${beat}`, '');
  };
  const slot = (beat: string) => BEATS.beats.find((y) => y.id === beat);
  const bStart = (beat: string) => slot(beat)?.start ?? miss(`no beat ${beat} in beats.json`, '');
  const bVoice = (beat: string) => slot(beat)?.voice_end ?? miss(`no beat ${beat} in beats.json`, '');
  const bStop = (beat: string) => slot(beat)?.end ?? miss(`no beat ${beat} in beats.json`, '');
  // call before rendering (in the composition's body): a render with an anchor the voice no longer says stops, every miss named
  const check = () => {
    if (MISSES.length) throw new Error(`timing: ${MISSES.length} anchor(s) not in the voice's words: ${MISSES.join('; ')}`);
  };
  return {w, we, wl, b0, bEnd, bStart, bVoice, bStop, check, MISSES, WORDS, BEATS, DURATION: BEATS.duration, PLACEHOLDER: !!BEATS.placeholder};
};

