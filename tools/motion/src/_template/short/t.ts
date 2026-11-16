// The Short template's timing: its own words.json + beats.json through src/timing.ts, strict (a phrase the voice no longer says throws
// at once). Copy this folder to start a Short.
import words from './words.json';
import beats from './beats.json';
import {timing} from '../../timing';

export const {w, we, wl, b0, bEnd, bStart, bVoice, bStop, DURATION, PLACEHOLDER} = timing(words, beats, {strict: true});
