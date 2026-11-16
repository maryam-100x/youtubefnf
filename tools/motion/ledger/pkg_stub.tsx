// Every @remotion/* add-on the edits import, for the ledger walker: fonts give a family name, blur and transition wrappers pass their
// children through, a cursor or an effect draws nothing. None of them shows a media file, so the ledger loses nothing.
import React from 'react';

const Pass: React.FC<{children?: React.ReactNode}> = ({children}) => <>{children}</>;
const Nothing: React.FC = () => null;

export const loadFont = () => ({fontFamily: 'LedgerFont', fonts: {}, unicodeRanges: {}, waitUntilDone: () => Promise.resolve(undefined)});
export const getInfo = () => ({fontFamily: 'LedgerFont'});
export const HtmlInCanvasMotionBlur = Pass;
export const CameraMotionBlur = Pass;
export const Trail = Pass;
export const linearTiming = (o: unknown) => o;
export const springTiming = (o: unknown) => o;
export const TransitionSeries = Object.assign(Pass, {Sequence: Pass, Transition: Nothing, Overlay: Nothing});
const presentation = () => ({component: Pass, props: {}});
export const blurSlide = presentation;
export const zoomBlur = presentation;
export const pushCut = presentation;
export const crossZoom = presentation;
export const linearBlur = presentation;
export const fade = presentation;
export const slide = presentation;
export const wipe = presentation;
export const flip = presentation;
export const clockWipe = presentation;
const effect = () => ({});
export const linearProgressiveBlur = effect;
export const vignette = effect;
export const noise = effect;
export const MacOSCursor = Nothing;
export const ThreeCanvas = Nothing;
export {OffthreadVideo as Video, Audio} from './remotion_stub';

for (const c of [Pass, Nothing, TransitionSeries]) (c as unknown as {__ledger_stub: boolean}).__ledger_stub = true;
