// kit3d · Case3D and Number3D: a real thing and its number, standing in one lit space (standard/3D.md §5).
//
// A number stands beside the thing it counts, in 3D too. Case3D is the product's real box: its cover art under a glossy sleeve (a clear
// coat), a dark plastic case (135 x 170 x 14 mm, a standard media case), rounded corners. Number3D is the number cut from the look's display font (kit3d/fonts/display.ttf: look_fonts.py)
// ExtraBold itself (the house face, its own TTF: kit3d/fonts), extruded with a small bevel, ink on its face and a darker ink
// on its sides, so it reads exactly like the house type when it faces the camera. Its digits stand up one after another on their word
// (each turns up from lying back, EASE.enter, 0.08 s apart: no overshoot, nothing springs back), and the camera ends almost face-on,
// so the number's last frames are as clean as flat type. The unit and the subject stay HTML (kit3's Label/Kicker: text is never
// geometry beyond the number itself), placed beside the number by projecting the same camera.
//
//   <CaseNumber3D dur cover="kit3d/img/demo_cover.jpg" value="230" unit="thousand copies" subject="of the album sold in its first year"
//      at={0.4} lit={0.9} />
//
// Props: dur, cover, value (the digits as said: '230'), unit, subject (both required: a number without them is refused), kicker?,
//   at (when the digits stand up, default 0.3), lit (when the number turns to the accent, optional: only when the voice names it),
//   from/to [azimuth, elevation] (default [-24, 7] -> [-7, 3]), move (default 1.8 s), veil (default false: the ground at its own
//   brightness; true: the veil, core.tsx PostSpec.veil)
// CENTRED BY WHAT YOU SEE (standard/3D.md §3): the box, its number and the HTML under it are one group, centred as kit3's
// rows centre theirs, by the whole visible content's box: on every frame the case and the standing digits are projected through the
// frame's camera, the HTML block's box (its lines measured) added under the number, and the camera pans until that box's centre sits on
// (960, DS.CY), the content box's centre line. The group is centred on its FINAL content from the first frame (as kit3 rows place their
// items), so nothing slides while the digits stand up. Past 2 px or cut by the frame it refuses; in the gate's probe it logs `kit3d|`.
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {AbsoluteFill, Internals} from 'remotion';
import {Font} from 'three/examples/jsm/loaders/FontLoader.js';
import {useT} from '../lib';
import {DS, TYPE, type, enterP, enterStyle, lightP, textW, useFontsReady} from '../kit3';
import {gateLog, gateOn} from '../gate';
import {CURVE, Cam, Load, STUDIO, Stage3D, all, lerp, orbit, prog, project, rad, strip, useAssets} from './core';
import {CASE_H, CASE_W, FRAME_H, FRAME_W, caseGeometry, caseNumberParts, centreOn, centreVerdict, glyphGeometries} from './centre';

// the case: 1.35 x 1.70 x 0.14 (1 unit = 100 mm); the cover is cropped to the case's shape at its centre. `geo`: the measured case
export const Case3D: React.FC<{cover: THREE.Texture; position?: [number, number, number]; rotY?: number; geo?: THREE.BufferGeometry}> = ({cover,
  position = [0, 0, 0], rotY = 0, geo: given}) => {
  const m = useMemo(() => {
    const w = CASE_W;
    const h = CASE_H;
    const geo = given ?? caseGeometry();
    const img = cover.image as {width: number; height: number};
    const tex = cover.clone();
    tex.needsUpdate = true;
    // cover the case's front (w x h) with the art, cropped centrally to the case's shape
    const ar = img.width / img.height;
    const caseAr = w / h;
    const sx = ar > caseAr ? caseAr / ar : 1;
    const sy = ar > caseAr ? 1 : ar / caseAr;
    // uv = position (three's world UV generator): u = x * sx / w + 0.5 maps -w/2..w/2 onto the middle `sx` of the art
    tex.repeat.set(sx / w, sy / h);
    tex.offset.set(0.5, 0.5);
    const front = new THREE.MeshPhysicalMaterial({map: tex, roughness: 0.5, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.07});
    const side = new THREE.MeshPhysicalMaterial({color: '#0b0c0e', roughness: 0.38, metalness: 0.1, clearcoat: 0.5, clearcoatRoughness: 0.2});
    return {geo, front, side};
  }, [cover, given]);
  return <mesh geometry={m.geo} material={[m.front, m.side]} position={position} rotation={[0, rotY, 0]} />;
};

// the glyphs one by one (each stands up on its own), laid out by the font's own advances: centre.ts glyphGeometries. `num`: the
// measured glyphs (CaseNumber3D passes the ones its centring projected)
export const Number3D: React.FC<{font: Font; text: string; size: number; t: number; at: number; lit: number; position: [number, number, number];
  rotY?: number; num?: ReturnType<typeof glyphGeometries>}> = ({font, text, size, t, at, lit, position, rotY = 0, num}) => {
  const m = useMemo(() => {
    const depth = size * 0.16;
    const {glyphs: gs, width} = num ?? glyphGeometries(font, text, size, depth);
    const face = new THREE.MeshPhysicalMaterial({color: new THREE.Color(DS.INK), roughness: 0.38, metalness: 0, clearcoat: 0.5, clearcoatRoughness: 0.2});
    const side = new THREE.MeshPhysicalMaterial({color: new THREE.Color('#8f8a82'), roughness: 0.45, metalness: 0.05});
    return {gs, width, face, side, depth};
  }, [font, text, size, num]);
  const brand = useMemo(() => new THREE.Color(DS.ACCENT), []);
  const ink = useMemo(() => new THREE.Color(DS.INK), []);
  m.face.color.copy(ink).lerp(brand, lit);
  return (
    <group position={position} rotation={[0, rotY, 0]}>
      {m.gs.map((g, i) => {
        const u = prog(t, at + i * 0.08, 0.5, CURVE.enter);
        // each glyph turns up about its own baseline from lying back 85 degrees, and is not there before its turn starts (digits lying on
        // the floor through the shot's first 0.3 s catch the key as a flash)
        return (
          <group key={i} position={[g.x - m.width / 2, 0, 0]} rotation={[-rad(85) * (1 - u), 0, 0]} visible={u > 0}>
            <mesh geometry={g.geo} material={[m.face, m.side]} position={[0, 0, -m.depth / 2]} />
          </group>
        );
      })}
    </group>
  );
};

// the HTML under the number: its lines' widths and its height (kit3's type sizes), for the group's box
const BLOCK_TOP = 40;                // px under the number's projected baseline
export const numberBlock = (unit: string, subject: string, kicker?: string) => {
  const L = TYPE.label, Hd = TYPE.headline;
  const w = Math.max(textW(unit, Hd.fontSize, Hd.fontWeight, Hd.letterSpacing), textW(subject, L.fontSize, L.fontWeight, L.letterSpacing),
    kicker ? textW(kicker, L.fontSize, L.fontWeight, L.letterSpacing) : 0);
  const h = (kicker ? L.fontSize * L.lineHeight + 8 : 0) + Hd.fontSize * Hd.lineHeight + 16 + L.fontSize * L.lineHeight;
  return {w, h};
};

export const CaseNumber3D: React.FC<{dur: number; cover: string; value: string; unit: string; subject: string; kicker?: string; at?: number;
  lit?: number; from?: [number, number]; to?: [number, number]; move?: number; veil?: boolean}> = ({dur, cover, value, unit, subject, kicker,
  at = 0.3, lit, from = [-24, 7], to = [-7, 3], move = 1.8, veil = false}) => {
  const t = useT();
  const abs = Internals.useAbsoluteTimelinePosition();
  const fonts = useFontsReady();
  if (!unit || !subject) throw new Error('kit3d CaseNumber3D: a number needs its unit and its subject (what it counts, of what)');
  const a = useAssets(`casenum:${cover}`, () => all({cover: Load.texture(cover), font: Load.font('kit3d/fonts/display.ttf')}));
  // the layout in world units: the case left of centre, the number right, both on the same floor line
  const size = 1.05;                  // cap height ~ 0.75 of size
  const caseX = -1.55;
  const numX = 1.05;
  const baseY = 0.02;                 // the number's baseline level with the case's top third
  const caseRot = rad(10);
  // the meshes once: the case and the digits the centring measures are the ones drawn
  const g = useMemo(() => (a ? {caseGeo: caseGeometry(), num: glyphGeometries(a.font, value, size, size * 0.16)} : null), [a, value]);
  if (!a || !g || !fonts) return null;
  void dur;
  const u = prog(t, 0, move);
  const az = lerp(from[0], to[0], u);
  const el = lerp(from[1], to[1], u);
  const fov = 26;
  const center: [number, number, number] = [0, 0.05, 0];
  const o = orbit(center, lerp(8.4, 7.6, u), az, el);
  const camAt = (q: [number, number, number]): Cam => ({pos: [o[0] + q[0], o[1] + q[1], o[2] + q[2]],
    target: [center[0] + q[0], center[1] + q[1], center[2] + q[2]], fov, near: 0.1, far: 60});
  // the group (the case, the standing number, the HTML under it) centred on the content box's centre line, by its visible box
  const blk = numberBlock(unit, subject, kicker);
  const htmlBox = (cm: Cam): [number, number, number, number][] => {
    const q = project(cm, [numX, baseY, 0]);
    return [[q.x - blk.w / 2, q.y + BLOCK_TOP, q.x + blk.w / 2, q.y + BLOCK_TOP + blk.h]];
  };
  const P: [number, number] = [FRAME_W / 2, DS.CY];
  const c = centreOn(caseNumberParts(g.caseGeo, caseX, caseRot, g.num, numX, baseY), camAt, P, FRAME_W, FRAME_H, 3, 'box', htmlBox);
  const v = centreVerdict('CaseNumber3D', `${cover} ${value}`, c, P, t, 'box');
  if (gateOn) gateLog('kit3d', {frame: abs, ...v.line});
  if (v.msg) throw new Error(v.msg);
  const cam = c.cam;
  const litU = lit === undefined ? 0 : lightP(t, lit);
  // the case's sleeve (turned 10 deg) mirrors round 20 - az: the strip crosses it, then the number, once, and leaves
  const sweepAz = lerp(20 - from[0] + 45, -to[0] - 45, prog(t, 0, move * 1.1, CURVE.drift));
  // the unit and subject (HTML) centred under the number, by the same camera
  const p = project(cam, [numX, baseY, 0]);
  const e = enterP(t, at + 0.35);
  return (
    <AbsoluteFill>
      <Stage3D kind="CaseNumber3D" cam={cam} env={{key: 'casenum', panels: STUDIO, sweep: strip(sweepAz, 3), intensity: 1}}
        post={{grain: 0.015, bloom: {strength: 0.12, radius: 0.3, threshold: 1.2}, veil}}>
        <directionalLight position={orbit([0, 0, 0], 10, -40, 35)} intensity={3.4} color="#fff7ee" />
        <directionalLight position={orbit([0, 0, 0], 10, 150, 20)} intensity={2} color="#e6eeff" />
        <Case3D cover={a.cover} position={[caseX, 0, 0]} rotY={caseRot} geo={g.caseGeo} />
        <Number3D font={a.font} text={value} size={size} t={t} at={at} lit={litU} position={[numX, baseY, 0]} num={g.num} />
      </Stage3D>
      <div style={{position: 'absolute', left: p.x, top: p.y + BLOCK_TOP, transform: 'translateX(-50%)', textAlign: 'center', whiteSpace: 'nowrap'}}>
        <div style={enterStyle(e)}>
          {kicker ? <div style={{...type('label', DS.INK2), marginBottom: 8}}>{kicker}</div> : null}
          <div style={{...type('headline')}}>{unit}</div>
          <div style={{...type('label', DS.INK2), marginTop: 16}}>{subject}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
