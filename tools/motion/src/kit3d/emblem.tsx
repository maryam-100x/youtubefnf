// kit3d · Emblem3D: a real logo made into a lit object, the way a product is shot (standard/3D.md §5).
//
// The logo's own artwork is its face (the SVG as a browser draws it, 4096 px: kit3d_assets.py emblem), its silhouette extruded with a
// bevelled edge, the lettering block (the white words with their dark outline) standing a little prouder than the base, so the edges
// catch the light separately. Glossy print on the face (a clear coat), dark lacquered metal on the sides. It reflects the shot it
// stands in (`photo`: the ground's picture as its environment) and a studio of soft panels; one strip of light crosses the face once
// during the move and leaves it (a specular sweep), so the shot rests clean. A fixed key
// front-left lights the face to its own colours (whites read white), a rim from behind in the ground's colour draws the top edges.
// The camera makes ONE move:
// from a three-quarter view to almost face-on, landing so the logo reads flat and whole, then only a slow drift. The emblem never
// spins and its back is never shown (Remotion's own logo prompt keeps the turn inside -90..90 for that reason).
//
// CENTRED BY WHAT YOU SEE: on every frame the logo's own meshes are projected through that frame's camera and the camera pans until the
// logo's VISUAL centre (left to right halfway between its visible pixels' box and their centre of mass; up and down its box's middle)
// sits on the intended point: the frame's centre, or (x, y). Aimed at the shape's origin (its BOX centre), a logo whose weight sits to
// one side (a heavy letter, the lettering) lands ~25 px off centre (centre.ts).
// A logo that can't be brought within CENTRE_TOL (2 px) of its point is refused, loudly (the still, the gate's probe and the render stop);
// in the gate's probe each frame logs `kit3d|{frame, box, centroid, visual, target}` for qa_centred.py's LOGO_OFF_CENTRE.
//
// Props (times are the shot's own seconds):
//   shape     public path of the <name>_shape.json (its `png` is the face)
//   dur       the shot's length
//   at        when the move and the sweep start (default 0: the shot cuts in already moving)
//   move      the move's length (default 1.8 s, EASE.move)
//   height    the emblem's height as a share of the frame at rest (default 0.5)
//   from/to   camera [azimuth, elevation] in degrees (default [-30, 9] -> [-8, 3]); the drift continues `drift` deg/s after (default 0.8)
//   photo     public path of a still of the shot's ground (its colours in the reflections); none: the studio alone
//   rim       colour of the light from behind (default warm white; take it from the ground: a sunset's orange, a night's blue)
//   depth     the extrusion as a share of the emblem's width (default 0.05)
//   x, y      where the emblem's VISUAL centre sits, as a share of the frame from its centre, + right / + up (default 0, 0)
//   key       the key light's intensity (default 3.6: a face square to it shows its albedo; lower it for a darker, moodier shot)
//   sideColor the sides' colour (default a dark neutral; set it to the logo's own outline colour)
//   veil      the bloom's veil on the ground (default false: the ground at its own `dim`; true: the veil, core.tsx PostSpec.veil)
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {AbsoluteFill, Internals} from 'remotion';
import {useT} from '../lib';
import {gateLog, gateOn} from '../gate';
import {CURVE, Cam, Load, STUDIO, Stage3D, all, lerp, orbit, prog, strip, useAssets} from './core';
import {FRAME_H, FRAME_W, ShapeData, centreOn, centreVerdict, emblemGeometry} from './centre';

type Geo = ReturnType<typeof emblemGeometry>;

const Body: React.FC<{g: Geo; face: THREE.Texture; sideColor: string}> = ({g, face, sideColor}) => {
  const mats = useMemo(() => {
    // the face's picture over the caps: uv = position (three's world UV generator), so repeat/offset map the logo's own bounds
    const tex = face.clone();
    tex.needsUpdate = true;
    tex.repeat.set(1 / 4, 1 / g.H);
    tex.offset.set(0.5, 0.5);
    tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
    const faceMat = new THREE.MeshPhysicalMaterial({map: tex, roughness: 0.42, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.06,
      envMapIntensity: 1});
    const sideMat = new THREE.MeshPhysicalMaterial({color: new THREE.Color(sideColor), roughness: 0.3, metalness: 0.75, clearcoat: 0.8,
      clearcoatRoughness: 0.12});
    return {faceMat, sideMat, tex};
  }, [g, face, sideColor]);
  return (
    <group>
      <mesh geometry={g.base} material={[mats.faceMat, mats.sideMat]} position={[0, 0, g.zBase]} />
      <mesh geometry={g.raised} material={[mats.faceMat, mats.sideMat]} position={[0, 0, g.zRaised]} />
    </group>
  );
};

export const Emblem3D: React.FC<{
  shape: string; dur: number; at?: number; move?: number; height?: number; from?: [number, number]; to?: [number, number];
  drift?: number; photo?: string; rim?: string; depth?: number; sideColor?: string; x?: number; y?: number; key?: number; veil?: boolean;
}> = ({shape, dur, at = 0, move = 1.8, height = 0.5, from = [-30, 9], to = [-8, 3], drift = 0.8, photo, rim = '#ffe9d0', depth = 0.05,
  sideColor = '#1a1d24', x = 0, y = 0, key = 3.6, veil = false}) => {
  const t = useT();
  const abs = Internals.useAbsoluteTimelinePosition();
  const a = useAssets(`emblem:${shape}:${photo ?? ''}`, async () => {
    const d = await Load.json<ShapeData>(shape);
    return all({d: Promise.resolve(d), face: Load.texture(d.png), photo: photo ? Load.texture(photo) : Promise.resolve(null)});
  });
  // the geometry once per shape: the measure and the drawing use the same meshes
  const g = useMemo(() => (a ? emblemGeometry(a.d, depth) : null), [a, depth]);
  if (!a || !g) return null;
  void dur;
  const fov = 30;
  // the distance that makes the emblem `height` of the frame at rest
  const dist = g.H / height / (2 * Math.tan((fov / 2) * Math.PI / 180));
  const u = prog(t, at, move);
  const az = lerp(from[0], to[0], u) + Math.max(0, t - at - move) * drift;
  const el = lerp(from[1], to[1], u);
  const k = lerp(1.12, 1, u);   // a slight dolly in with the turn
  // the orbit round the logo, then panned (position and target alike) so its visual centre lands on (x, y) of the frame
  const o = orbit([0, 0, 0], dist * k, az, el);
  const camAt = (p: [number, number, number]): Cam => ({pos: [o[0] + p[0], o[1] + p[1], o[2] + p[2]], target: p, fov, near: 0.1, far: 100});
  const P: [number, number] = [FRAME_W / 2 + x * FRAME_W, FRAME_H / 2 - y * FRAME_H];
  const c = centreOn(g.parts, camAt, P);
  const v = centreVerdict('Emblem3D', shape, c, P, t, 'eye');
  if (gateOn) gateLog('kit3d', {frame: abs, ...v.line});
  if (v.msg) throw new Error(v.msg);
  const cam = c.cam;
  // the sweep: a strip of light crosses the face once during the move. The face mirrors the environment round azimuth -az (+-25 deg),
  // so the strip runs from 45 deg past that on one side (at the start) to 45 deg past it on the other (at the end): off the face at
  // both ends, across it in between, and the shot rests clean
  const sw = prog(t, at, move * 1.1, CURVE.drift);
  const sweepAz = lerp(-from[0] + 45, -to[0] - 45, sw);
  return (
    <AbsoluteFill>
      <Stage3D kind="Emblem3D" cam={cam}
        env={{key: `emb:${photo ?? ''}`, panels: STUDIO, sweep: strip(sweepAz, 3.5), photo: a.photo ?? undefined, photoLevel: 0.5, intensity: 1}}
        post={{bloom: {strength: 0.2, radius: 0.35, threshold: 1.1}, grain: 0.018, veil}}>
        {/* the key: front-left and high, fixed (the shading turns as the camera moves); the rim from behind, in the ground's colour */}
        <directionalLight position={orbit([0, 0, 0], 10, -40, 35)} intensity={key} color="#fff7ee" />
        <directionalLight position={orbit([0, 0, 0], 10, 150, 20)} intensity={3} color={rim} />
        <Body g={g} face={a.face} sideColor={sideColor} />
      </Stage3D>
    </AbsoluteFill>
  );
};
