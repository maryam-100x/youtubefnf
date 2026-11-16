// kit3's demo: every piece in its variants, on drawn material and the faults the kit guards against, so its stills prove the kit
// (kit3_proof.mjs renders them, kit3_check.py measures them; standard/KIT3.md "The proof"). Its material is drawn by
// kit3_demo_assets.py (public dir TMP/pub_kit3). Its own entry, src/kit3_index.ts, so it renders whatever any video's code is doing.
//   Kit3Demo    47 s, the sections below (from, length); the marks use the pages' LOOSE word boxes (as a page's DOM gives them): the kit
//               snaps them to the ink
//   Kit3Refuse  one refusal per `case` input prop: each must THROW (the proof expects every one to fail with its reason)
import React from 'react';
import {AbsoluteFill, Composition, Sequence} from 'remotion';
import {FPS, f} from '../lib';
import {DS} from './tokens';
import {keysAcross} from './layout';
import {Stage} from './stage';
import {Page} from './page';
import {Foot, Still, StampShot, TagShot, TypedShot} from './footage';
import {LogosLand, Row} from './rows';
import {NumberBeside} from './numbers';
import {Read} from './read';
import {Timeline} from './timeline';

const P = 'kit3/demo/pages/', I = 'kit3/demo/img/', C = 'kit3/demo/clips/';
const R = 'Demo material';

export const SECTIONS: {id: string; from: number; dur: number; el: (d: number) => React.ReactNode}[] = [
  // A · a light page (a video page): the wash. The boxes are the DOM's: 13 px blank over, 16 under, 12 right; the title starts at the
  // capture's x 3 (the crop grows left in the page's own paper so the padded box stays whole)
  {id: 'A_page_light', from: 0, dur: 3, el: (d) => (
    <Page d={d} src={`${P}page_light.png`} crop={[0, 170, 1150, 330]} kicker="Video page, launch day"
      credit="Demo page" marks={[{box: [0, 418, 683, 65], at: 0.5}, {box: [729, 331, 263, 55], at: 1.3}]} />
  )},
  // B · a dark page (a company's news post): the box, one phrase over three lines (up to 26 px blank over, 21 under; "servers!"
  // with its "!" outside the box), over a live ground
  {id: 'B_page_dark', from: 3, dur: 3, el: (d) => (
    <Page d={d} src={`${P}page_dark.png`} crop={[40, 140, 1080, 245]} ground={`${C}ground_a.mp4`}
      source="Company news post" marks={[{box: [806, 152, 153, 70], at: 0.6}, {box: [72, 229, 856, 70], at: 0.6},
        {box: [72, 305, 156, 70], at: 0.6}]} />
  )},
  // C · the receipt with the thing beside it (show the thing itself): a news headline, "tops the charts" marked, the album beside it
  {id: 'C_page_beside', from: 6, dur: 3.5, el: (d) => (
    <Page d={d} src={`${P}page_headline.png`} kicker="News site, launch week" credit={R}
      source="News site" beside={{src: `${I}cover.jpg`, h: 560, caption: 'The album'}} marks={[{box: [73, 200, 796, 124], at: 0.6}]} />
  )},
  // D · a number on its own page (show the thing itself): the views on a video page, marked (18 px blank over them)
  {id: 'D_page_number', from: 9.5, dur: 3, el: (d) => (
    <Page d={d} src={`${P}page_number.png`} crop={[20, 40, 840, 260]} maxScale={1.6} credit="Demo page"
      marks={[{box: [57, 253, 133, 39], at: 0.5}]} />
  )},
  // E · marks on a picture: the still standing still from the first box, each named on its word, the newest in the accent and the
  // ones before it an ink outline, the rest dimmed
  {id: 'E_still_marks', from: 12.5, dur: 3.5, el: (d) => (
    <Still src={`${I}still.png`} d={d} region={[331, 20, 1538, 865]} credit="Demo picture" marks={[
      {box: [1005, 80, 190, 140], name: 'Sun disc', at: 0.4, nameSide: 'below'},
      {box: [813, 667, 136, 110], name: 'Triangle', at: 1.0, nameSide: 'above'},
      {box: [1035, 663, 152, 108], name: 'Square', at: 1.6, nameSide: 'above'},
      {box: [1264, 657, 117, 109], name: 'Blue diamond', at: 2.2, nameSide: 'above'}]} />
  )},
  // F · a mark on footage: the clip freezes and stops pushing from the light
  {id: 'F_foot_mark', from: 16, dur: 2.2, el: (d) => (
    <Foot clip={`${C}subject.mp4`} d={d} push={[1.0, 1.02]} credit="Demo clip" marks={[{box: [410, 330, 380, 100], at: 0.9, name: 'The subject'}]} />
  )},
  // G · names much wider than their figures (the widest name on the narrowest device); on the plain stage (the check)
  {id: 'G_row_devices', from: 18.2, dur: 3, el: (d) => (
    <Stage dur={d} credit={R}>
      <Row h={420} items={[{src: `${I}device_a.png`, name: 'Coffee Mill 3', at: 0.2}, {src: `${I}device_b.png`, name: 'Coffee Mill 4', at: 0.5},
        {src: `${I}device_c.png`, name: 'Coffee Mill 5', at: 0.8, litAt: 1.4}]} />
    </Stage>
  )},
  // H · the alpha test: three covers with transparent margins of 0-420 px on every side, one cut narrower; placed by their files they
  // would sit off centre with unequal gaps
  {id: 'H_row_alpha', from: 21.2, dur: 3, el: (d) => (
    <Stage dur={d} credit={R}>
      <Row h={520} items={[{src: 'kit3/pad_a.png', name: '2001', at: 0.1}, {src: 'kit3/pad_b.png', name: '2002', at: 0.3},
        {src: 'kit3/pad_c.png', name: '2004', at: 0.5, litAt: 1.0}]} />
    </Stage>
  )},
  // I · people cut at the legs (bleed): three people, the middle one named
  {id: 'I_row_bleed', from: 24.2, dur: 3, el: (d) => (
    <Stage dur={d} ground={`${C}ground_b.mp4`} credit={R}>
      <Row mode="bleed" h={880} items={[{src: `${I}person_a.png`, name: 'Alex', at: 0}, {src: `${I}person_b.png`, name: 'Sam',
        at: 0, litAt: 1.0}, {src: `${I}person_c.png`, name: 'Robin', at: 0}]} />
    </Stage>
  )},
  // J · logos landing (the white one has 211 px of transparent margin each side), centred by their visible pixels; plain stage
  {id: 'J_logos', from: 27.2, dur: 3, el: (d) => (
    <LogosLand d={d} items={[{src: `${I}logo_a.png`, at: 0.2}, {src: `${I}logo_b.png`, at: 0.6},
      {src: `${I}logo_c.png`, at: 1.0}]} credit="Demo logos" />
  )},
  // K · someone's words read: whole from the first frame, the phrase the voice leans on lit on its word
  {id: 'K_read', from: 30.2, dur: 3, el: (d) => (
    <Read d={d} page={`${P}page_dark.png`} kicker="Company news post"
      lines={['Simply overwhelming in the case', 'of some of our servers!']} lit={[{text: 'Simply overwhelming', at: 0.8}]} />
  )},
  // L · a number beside the picture of what it counts (no page for it here)
  {id: 'L_number', from: 33.2, dur: 3.5, el: (d) => (
    <NumberBeside d={d} picture={`${I}cover.jpg`} pictureH={620} value={230} at={0.4} unit="million plays"
      subject="in its first year" kicker="The label's figures" ground={`${C}ground_c.mp4`} credit={R} source="Demo figures" />
  )},
  // M · dates at true distances: 46 days then 15; the close label goes above by itself
  {id: 'M_timeline', from: 36.7, dur: 3.5, el: (d) => (
    <Timeline d={d} kicker="A release, in dates" ground={`${C}ground_a.mp4`} credit={R} span={[46, 61]} spanText="2 weeks" spanAt={2.0}
      marks={[{date: 'Oct 31', what: 'the songs recorded', day: 0, at: 0.3}, {date: 'Dec 16', what: 'the album out', day: 46, at: 0.9},
        {date: 'Dec 31', what: 'the news', day: 61, at: 1.5}]} />
  )},
  // N-P · the footage pieces: a name in the tag's place, a stamp, a typed date (whole 0.3 s before the cut)
  {id: 'N_tag', from: 40.2, dur: 2, el: (d) => <TagShot clip={`${C}subject.mp4`} d={d} tag="Alex Morgan" tagAt={0.3} credit="Demo clip" />},
  {id: 'O_stamp', from: 42.2, dur: 2.5, el: (d) => <StampShot clip={`${C}ground_b.mp4`} d={d} stampAt={0.5} lead="10 YEARS" text="AT THE TOP" credit={R} />},
  {id: 'P_typed', from: 44.7, dur: 2.2, el: (d) => (
    <TypedShot clip={`${C}ground_a.mp4`} d={d} text="September 21, 2015" keys={keysAcross(18, 0.2, 2.1)} credit={R} />
  )},
];
export const KIT3_SECONDS = 47;

export const Kit3Demo: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    {SECTIONS.map((s) => <Sequence key={s.id} from={f(s.from)} durationInFrames={f(s.dur)}>{s.el(s.dur)}</Sequence>)}
  </AbsoluteFill>
);

// every guard, one case each (rendered at frame 30): the kit must refuse each with its reason
export const REFUSALS: Record<string, {expect: string; el: React.ReactNode}> = {
  redundant: {expect: 'needs no mark', el: (
    <Page d={3} src={`${P}page_header.png`} crop={[130, 30, 560, 130]} maxScale={2.2}
      marks={[{box: [254, 86, 262, 33], at: 0.08}]} />)},
  nothing: {expect: 'no ink under its box', el: (
    <Page d={3} src={`${P}page_light.png`} crop={[0, 170, 1150, 330]} marks={[{box: [1000, 420, 120, 50], at: 0.5}]} />)},
  late: {expect: 'MARK_LATE', el: (
    <Page d={3} src={`${P}page_light.png`} crop={[0, 170, 1150, 330]} marks={[{box: [729, 331, 263, 55], at: 2.6}]} />)},
  read_all_lit: {expect: 'show it plain', el: (
    <Read d={3} kicker="Company news post" lines={['Simply overwhelming']} lit={[{text: 'Simply overwhelming', at: 0.5}]} />)},
  read_overflow: {expect: 'break it', el: (
    <Read d={3} kicker="A forum" lines={['The Big Summer Redesign Has Ruined The Whole App For Everyone Who Still Uses It Daily']} />)},
  read_lit_missing: {expect: 'not on the card', el: (
    <Read d={3} kicker="Company news post" lines={['Simply overwhelming in the case', 'of some of our servers!']} lit={[{text: 'crashed', at: 0.5}]} />)},
  clip_unmeasured: {expect: 'clipdurs', el: <Foot clip={`${C}not_cut_yet.mp4`} d={3} />},
  frame_mark_huge: {expect: 'nothing to pick it out from', el: (
    <Foot clip={`${C}subject.mp4`} d={2.2} marks={[{box: [100, 100, 1500, 800], at: 0.5}]} />)},
  still_upscale: {expect: 'never upscaled', el: (
    <Still src={`${I}still.png`} d={3} region={[790, 0, 480, 270]} />)},
  number_alone: {expect: 'show the thing itself', el: (
    // @ts-expect-error: neither picture nor noPicture (the type refuses it too; this is the runtime guard)
    <NumberBeside d={3} value={25} at={0.5} unit="million views" subject="on one video" />)},
  number_unit: {expect: 'unit and its subject', el: (
    <NumberBeside d={3} picture={`${I}cover.jpg`} value={25} at={0.5} unit="" subject="" />)},
  row_too_wide: {expect: 'cannot fit', el: (
    <Stage dur={3}><Row h={300} items={[{src: `${I}cover.jpg`, name: 'A name far too long for any row on this screen, really very long indeed'}]} /></Stage>)},
};
export const Kit3Refuse: React.FC<{which: string}> = ({which}) => {
  const c = REFUSALS[which];
  return <AbsoluteFill style={{background: '#000'}}>{c ? c.el : null}</AbsoluteFill>;
};

export const Kit3Root: React.FC = () => (
  <>
    <Composition id="Kit3Demo" component={Kit3Demo} durationInFrames={f(KIT3_SECONDS)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="Kit3Refuse" component={Kit3Refuse} durationInFrames={f(3)} fps={FPS} width={DS.W} height={DS.H}
      defaultProps={{which: 'redundant'}} />
  </>
);
