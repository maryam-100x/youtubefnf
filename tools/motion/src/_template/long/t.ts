// The template's timing: its own words.json + beats.json (placeholders until the voice exists: placeholder_words.py; then
// sync_words.py writes the voice's own in the same format) through src/timing.ts. Copy this folder to start a video.
import words from './words.json';
import beats from './beats.json';
import {timing} from '../../timing';

export type {Shot} from '../../timing';
export const {w, we, wl, b0, bEnd, bStart, bVoice, bStop, check, MISSES, DURATION, PLACEHOLDER} = timing(words, beats);
