// kit3d · Phone3D: a phone with the real thing on its screen (a clip or a page capture), turning to camera (standard/3D.md §5).
//
// The phone is built in code (no model file, no brand): a rounded slab (the outline extruded with a rounded edge: flat glass front,
// flat back), a satin metal band, a black bezel, a punch-hole camera, the screen inset with its own rounded corners. The screen is the
// real material: a clip from @remotion/media's <Video headless> drawn into the texture on each frame (remotion.dev/docs/videos/
// as-threejs-texture: advance() inside onVideoFrame during a render), or a still (a post, a page, a store page). The screen emits its
// own light (no tone map: its colours are the clip's); a glass layer over it carries only reflections (additive), so the studio's
// strip slides across the glass as the phone turns. ONE move: from a three-quarter turn to face-on, then a slow drift.
//
// Props: dur, clip? (public path) | img? (public path), landscape? (default true), at (default 0), move (default 1.6 s),
//   from/to [yaw, pitch] in degrees (default [32, -8] -> [6, -2]), height (at rest, the phone's long side as a share of the frame's
//   width in landscape, of its height in portrait; default 0.62), x/y (centre offset as share of the frame, default 0), aspect (the
//   screen's long side / short side, default 2.0: the clip's own shape; make the clip that shape, kit3d_assets.py clip crops 2:1),
//   veil (default false: the ground at its own brightness; true: the veil, core.tsx PostSpec.veil)
// CENTRED BY WHAT YOU SEE (standard/3D.md §3): on every frame the slab, turned as it is drawn, is projected through the
// frame's camera and the camera pans until its visual centre sits on the frame's centre (or x/y), through the whole turn; past 2 px or cut
// by the frame it refuses; in the gate's probe it logs `kit3d|` lines (qa_centred.py). The slab measured is the slab drawn (phoneGeometry).
import React, {useCallback, useMemo, useRef} from 'react';
import * as THREE from 'three';
import {AbsoluteFill, Internals, useRemotionEnvironment} from 'remotion';
import {Video} from '@remotion/media';
import {useThree} from '@react-three/fiber';
import {staticFile} from 'remotion';
import {useT} from '../lib';
import {gateLog, gateOn} from '../gate';
import {CURVE, Cam, Load, STUDIO, Stage3D, all, lerp, orbit, prog, rad, strip, useAssets} from './core';
import {FRAME_H, FRAME_W, centreOn, centreVerdict, phoneGeometry} from './centre';

const rounded = (w: number, h: number, r: number) => {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x + w, y + h - r);
  s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2, false);
  s.lineTo(x + r, y + h);
  s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(x, y + r);
  s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5, false);
  return s;
};

// a ShapeGeometry's uv is its position: map it to 0..1 over the shape's box
const fitUV = (g: THREE.BufferGeometry, w: number, h: number) => {
  const p = g.getAttribute('position');
  const uv = new Float32Array(p.count * 2);
  for (let i = 0; i < p.count; i++) {
    uv[i * 2] = p.getX(i) / w + 0.5;
    uv[i * 2 + 1] = p.getY(i) / h + 0.5;
  }
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return g;
};

// the clip as a texture: <Video headless> hands each frame to onVideoFrame, drawn into a canvas the texture wraps
const useClipTexture = (w: number, h: number) => useMemo(() => {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 16;
  return {canvas, ctx: canvas.getContext('2d')!, tex};
}, [w, h]);

const ClipFeed: React.FC<{src: string; feed: ReturnType<typeof useClipTexture>}> = ({src, feed}) => {
  const {advance, invalidate} = useThree();
  const {isRendering} = useRemotionEnvironment();
  const onFrame = useCallback((frame: CanvasImageSource) => {
    feed.ctx.drawImage(frame, 0, 0, feed.canvas.width, feed.canvas.height);
    feed.tex.needsUpdate = true;
    if (isRendering) advance(performance.now());
    else invalidate();
  }, [feed, advance, invalidate, isRendering]);
  return <Video src={staticFile(src)} headless muted onVideoFrame={onFrame} />;
};

const Phone: React.FC<{screen: THREE.Texture; landscape: boolean; aspect: number; yaw: number; pitch: number;
  geo: ReturnType<typeof phoneGeometry>}> = ({screen, landscape, aspect, yaw, pitch, geo}) => {
  // built as it is held: the screen `aspect` long by 1 short, bezels round it, depth 0.085
  const m = useMemo(() => {
    const bez = 0.035;
    const sw = landscape ? aspect : 1;
    const sh = landscape ? 1 : aspect;
    const W = sw + 2 * bez;
    const H = sh + 2 * bez;
    const D = 0.085;
    const R = 0.13;
    const body = geo.body;   // the slab the centring measured (centre.ts phoneGeometry: the same outline, bevel and depth)
    const glass = new THREE.MeshPhysicalMaterial({color: '#050506', roughness: 0.08, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03});
    const band = new THREE.MeshPhysicalMaterial({color: '#3a3c40', roughness: 0.32, metalness: 1});
    const scr = fitUV(new THREE.ShapeGeometry(rounded(sw, sh, R - bez - 0.01), 24), sw, sh);
    const scrMat = new THREE.MeshBasicMaterial({map: screen, toneMapped: false});
    const gloss = new THREE.ShapeGeometry(rounded(W - 0.03, H - 0.03, R - 0.015), 24);
    // the glass: only its reflection, added over the screen. One specular layer (F0 0.04), the environment at 0.45 (a clear coat on top
    // and the full environment lay a white slab over a third of the clip mid-turn)
    const glossMat = new THREE.MeshPhysicalMaterial({color: '#000000', roughness: 0.05, metalness: 0, envMapIntensity: 0.45,
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false});
    const hole = new THREE.CircleGeometry(0.028, 32);
    const holeMat = new THREE.MeshBasicMaterial({color: '#000000'});
    // the punch-hole camera: at the top in portrait, at the left end in landscape (a phone turned anticlockwise)
    const holeAt: [number, number] = landscape ? [-sw / 2 + 0.07, 0] : [0, sh / 2 - 0.07];
    return {body, glass, band, scr, scrMat, gloss, glossMat, hole, holeMat, D, holeAt};
  }, [screen, aspect, landscape, geo]);
  const zf = m.D / 2 + 0.0005;
  return (
    <group rotation={[rad(pitch), rad(yaw), 0]}>
      <mesh geometry={m.body} material={[m.glass, m.band]} />
      <mesh geometry={m.scr} material={m.scrMat} position={[0, 0, zf]} />
      <mesh geometry={m.hole} material={m.holeMat} position={[m.holeAt[0], m.holeAt[1], zf + 0.0004]} />
      <mesh geometry={m.gloss} material={m.glossMat} position={[0, 0, zf + 0.0008]} renderOrder={2} />
    </group>
  );
};

export const Phone3D: React.FC<{dur: number; clip?: string; img?: string; landscape?: boolean; at?: number; move?: number;
  from?: [number, number]; to?: [number, number]; height?: number; x?: number; y?: number; aspect?: number; drift?: number; veil?: boolean}> = ({dur,
  clip, img, landscape = true, at = 0, move = 1.6, from = [32, -8], to = [6, -2], height = 0.62, x = 0, y = 0, aspect = 2.0, drift = 0.6,
  veil = false}) => {
  const t = useT();
  const abs = Internals.useAbsoluteTimelinePosition();
  const geo = useMemo(() => phoneGeometry(aspect, landscape), [aspect, landscape]);
  if (!clip && !img) throw new Error('kit3d Phone3D: give the screen its real material: `clip` or `img`');
  const a = useAssets(`phone:${img ?? ''}`, () => all({img: img ? Load.texture(img) : Promise.resolve(null)}));
  // the clip's canvas at the screen's shape, 1920 px on its long side
  const feed = useClipTexture(landscape ? 1920 : Math.round(1920 / aspect), landscape ? Math.round(1920 / aspect) : 1920);
  if (!a) return null;
  void dur;
  const screen: THREE.Texture = a.img ?? feed.tex;
  const fov = 28;
  const long = aspect + 0.07;
  const dist = long / height / (2 * Math.tan(rad(fov / 2)) * (landscape ? 16 / 9 : 1));
  const u = prog(t, at, move);
  const yaw = lerp(from[0], to[0], u) - Math.max(0, t - at - move) * drift;
  const pitch = lerp(from[1], to[1], u);
  // the glass mirrors the environment round azimuth 2 x yaw: the sweep's strip crosses it once during the turn, off it at both ends
  const sweepAz = lerp(2 * from[0] + 40, 2 * to[0] - 40, prog(t, at, move * 1.1, CURVE.drift));
  // the camera straight on, then panned (position and target alike) so the turning slab's visual centre sits on (x, y) of the frame
  const camAt = (p: [number, number, number]): Cam => ({pos: [p[0], p[1], p[2] + dist], target: p, fov, near: 0.05, far: 50});
  const P: [number, number] = [FRAME_W / 2 + x * FRAME_W, FRAME_H / 2 - y * FRAME_H];
  const c = centreOn(geo.parts(yaw, pitch), camAt, P);
  const v = centreVerdict('Phone3D', clip ?? img ?? '', c, P, t, 'eye');
  if (gateOn) gateLog('kit3d', {frame: abs, ...v.line});
  if (v.msg) throw new Error(v.msg);
  const cam = c.cam;
  return (
    <AbsoluteFill>
      <Stage3D kind="Phone3D" cam={cam} env={{key: 'phone', panels: STUDIO, sweep: strip(sweepAz, 1.1), intensity: 1}}
        post={{grain: 0.015, bloom: {strength: 0.15, radius: 0.3, threshold: 1.2}, veil}}>
        <directionalLight position={orbit([0, 0, 0], 10, -40, 35)} intensity={2.2} color="#fff7ee" />
        <directionalLight position={orbit([0, 0, 0], 10, 150, 20)} intensity={2.4} color="#dfe8ff" />
        {clip ? <ClipFeed src={clip} feed={feed} /> : null}
        <Phone screen={screen} landscape={landscape} aspect={aspect} yaw={yaw} pitch={pitch} geo={geo} />
      </Stage3D>
    </AbsoluteFill>
  );
};
