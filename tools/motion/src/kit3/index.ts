// kit3: the house kit for long videos (standard/KIT3.md). A video imports from here, never copies a piece into its own folder: a fix to
// a piece lands once for every video. A piece a video needs that isn't here is added HERE (with its test and a demo section), not built
// in the video's graphics file.
export {DS, TYPE, FONT, type, enterP, exitP, moveP, lightP, enterStyle, markStart, heldT} from './tokens';
export type {TypeKey} from './tokens';
export {useMeasured, useFontsReady, textW, url, useImgBoxes, usePagesInk} from './measure';
export type {ImgBox, PageInk} from './measure';
export {rowLayout, timelineLayout, inkSnap, markVerdict, markRect, expandCrop, fitKeys, keysAcross, REDUNDANT_INK, REDUNDANT_AREA} from './layout';
export type {Box} from './layout';
export {Stage, Credit, Split, Enter, Card, Hold, hasClip, Pending} from './stage';
export {Kicker, Headline, Label, TextBlock, Lit, Tag, Stamp, TypedLine} from './text';
export {MarkBox, Veil, frameMarkVerdict, SPOT, SpotDim, SpotRim, SpotInk, SpotGate, SpotLook, silOf} from './marks';
export type {SpotLookSettings} from './marks';
export {Cutout, PhotoFrame, Picture} from './pictures';
export {Page} from './page';
export type {PageMark, PageSpec} from './page';
export {Foot, Still, Burst, TagShot, StampShot, TypedShot} from './footage';
export type {FrameMark} from './footage';
export {Row, LogosLand} from './rows';
export type {RowItem} from './rows';
export {Odometer, BigNumber, NumberBeside} from './numbers';
export {Read} from './read';
export {Timeline} from './timeline';
