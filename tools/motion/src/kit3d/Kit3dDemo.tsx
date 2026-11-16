// kit3d's demo: each piece as its own composition on drawn material (kit3d_assets.py: shapes and colour, nobody's picture;
// standard/3D.md §5), for its stills and its clip. From tools/motion:
//   bash with_remotion_lock.sh "kit3d proof" node kit3d_proof.mjs <out_dir> [stills|clips|all]
// Public dir: TMP/pub_kit3d (hard links of PUBLIC/kit3d, kit3d_assets.py link).
import React from 'react';
import {AbsoluteFill, Composition} from 'remotion';
import {FPS} from '../lib';
import {Credit, DS, Stage} from '../kit3';
import {CaseNumber3D, Emblem3D, Globe3D, Parallax25D, Phone3D} from '.';

const f = (s: number) => Math.round(s * FPS);

export const DEMO = {
  emblem: 5,
  parallaxA: 5,
  parallaxB: 5,
  globe: 6,
  phone: 5,
  caseNumber: 5,
};

// the demo logo as an object, in front of the drawn skyline at dusk (defocused: the house ground), reflecting it
export const DemoEmblem: React.FC = () => (
  <AbsoluteFill style={{background: '#050505'}}>
    <Stage dur={DEMO.emblem} img="kit3d/img/demo_city.jpg" />
    <Emblem3D shape="kit3d/logos/demo_logo_shape.json" dur={DEMO.emblem} photo="kit3d/img/demo_city.jpg" rim="#ffc58a" />
    <Credit pic="Demo logo" />
  </AbsoluteFill>
);

// two people in front of a street, with depth: the pair hold their place, the street turns behind them
export const DemoParallaxA: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Parallax25D src="kit3d/img/demo_people" dur={DEMO.parallaxA} />
    <Credit pic="Demo picture" />
  </AbsoluteFill>
);

// the skyline: the near blocks and the far ones at their own depths
export const DemoParallaxB: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Parallax25D src="kit3d/img/demo_city" dur={DEMO.parallaxB} slide={[-0.16, 0.03]} dolly={0.4} />
    <Credit pic="Demo picture" />
  </AbsoluteFill>
);

// orbit at night down to the coast the detail patch covers (globe.tsx PATCH), a city pinned on its word
export const DemoGlobe: React.FC = () => (
  <AbsoluteFill style={{background: '#000'}}>
    <Globe3D dur={DEMO.globe} from={{lat: 31, lon: -7, alt: 2.4, tilt: 0}} to={{lat: 39.96, lon: -10.15, alt: 0.16, tilt: 50}} move={3.6}
      pins={[{lat: 38.72, lon: -9.14, name: 'Lisbon', at: 3.4, lit: 3.9}]} />
    <Credit pic="NASA Earth Observatory (Black Marble 2016)" />
  </AbsoluteFill>
);

// a clip on a phone, turning to camera over the defocused people
export const DemoPhone: React.FC = () => (
  <AbsoluteFill style={{background: '#050505'}}>
    <Stage dur={DEMO.phone} img="kit3d/img/demo_people.jpg" />
    <Phone3D dur={DEMO.phone} clip="kit3d/clips/demo_phone.mp4" />
    <Credit pic="Demo clip" />
  </AbsoluteFill>
);

// a product's box and its number
export const DemoCaseNumber: React.FC = () => (
  <AbsoluteFill style={{background: '#050505'}}>
    <Stage dur={DEMO.caseNumber} img="kit3d/img/demo_people.jpg" dim={0.22} blur={14} />
    <CaseNumber3D dur={DEMO.caseNumber} cover="kit3d/img/demo_cover.jpg" value="230" unit="thousand copies"
      subject="of the album sold in its first year" at={0.35} lit={1.2} />
    <Credit pic="Demo cover" source="Demo figures" />
  </AbsoluteFill>
);

export const Kit3dRoot: React.FC = () => (
  <>
    <Composition id="K3dEmblem" component={DemoEmblem} durationInFrames={f(DEMO.emblem)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="K3dParallaxA" component={DemoParallaxA} durationInFrames={f(DEMO.parallaxA)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="K3dParallaxB" component={DemoParallaxB} durationInFrames={f(DEMO.parallaxB)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="K3dGlobe" component={DemoGlobe} durationInFrames={f(DEMO.globe)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="K3dPhone" component={DemoPhone} durationInFrames={f(DEMO.phone)} fps={FPS} width={DS.W} height={DS.H} />
    <Composition id="K3dCaseNumber" component={DemoCaseNumber} durationInFrames={f(DEMO.caseNumber)} fps={FPS} width={DS.W} height={DS.H} />
  </>
);
