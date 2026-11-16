// Every composition Remotion Studio and the renders see: the two templates (copy a folder of src/_template to start a video) and the
// kits' demos. A video's own composition is registered here as gated(X): the pre-render gate's probe (src/gate.tsx); `pipe.py gate`
// refuses a composition that isn't (gate.py B0).
//   Template       the long-form template, 1920 x 1080 (the setup's test render: frames 0-179, no media needed)
//   TemplateShort  the Short template, 1080 x 1920
//   Kit3Demo / Kit3Refuse               kit3's demo and its refusal cases (kit3_demo_assets.py draws their media; kit3_proof.mjs)
//   LookBoard      one look on the studio's real pieces, one still (tools/motion/look_board.py; the setup's look step)
//   K3dEmblem, K3dParallaxA/B, K3dGlobe, K3dPhone, K3dCaseNumber   kit3d's demos (kit3d_assets.py; kit3d_proof.mjs)
import React from 'react';
import {Composition} from 'remotion';
import {FPS} from './lib';
import {gated} from './gate';
import {Template, TEMPLATE_SECONDS} from './_template/long/Template';
import {TemplateShort, TEMPLATE_SHORT_SECONDS} from './_template/short/TemplateShort';
import {Kit3Root} from './kit3/Kit3Demo';
import {Kit3dRoot} from './kit3d/Kit3dDemo';
import {LookBoard, LOOK_BOARD_H, LOOK_BOARD_SECONDS, LOOK_BOARD_W} from './_look/LookBoard';

export const Root: React.FC = () => (
  <>
    <Composition id="Template" component={gated(Template)} durationInFrames={Math.round(TEMPLATE_SECONDS * FPS)} fps={FPS} width={1920} height={1080} />
    <Composition id="TemplateShort" component={gated(TemplateShort)} durationInFrames={Math.round(TEMPLATE_SHORT_SECONDS * FPS)} fps={FPS} width={1080}
      height={1920} />
    <Composition id="LookBoard" component={LookBoard} durationInFrames={Math.round(LOOK_BOARD_SECONDS * FPS)} fps={FPS} width={LOOK_BOARD_W}
      height={LOOK_BOARD_H} />
    <Kit3Root />
    <Kit3dRoot />
  </>
);
