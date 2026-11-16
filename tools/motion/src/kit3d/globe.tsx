// kit3d · Globe3D: the real Earth at night, one camera move from orbit down to a place (standard/3D.md §5).
//
// NASA's Black Marble 2016 (city lights seen by Suomi NPP, the land's own faint blue): the world at 3 km a pixel (8192 x 4096) and,
// where the move lands, a ~1-km patch (the region PATCH names: NASA's 500-m tile at half size, kit3d_assets.py earth),
// feathered into the world map. A thin
// atmosphere at the limb (the one light that is not a texture: the real look of the planet's edge from orbit, kept faint). No stars,
// no clouds, no lens flare: less is more. The move is ONE eased flight (EASE.drift by default) from `from` to `to`, then a slow drift;
// the camera tilts toward the horizon as it comes down, so the last frames look across the coast, not straight down at a map.
//
// Places are pinned with `pins`: a small dot on the ground (the accent only while the voice names it: `lit` time) and the place's name
// as an HTML Tag beside it (Archivo, the house chip), placed by projecting the same camera; a pin on the far side is hidden.
//
// Props: dur, from/to {lat, lon, alt (Earth radii above the ground), tilt (degrees from straight down)}, at (start, default 0),
//   move (length, default 3.2 s), pins [{lat, lon, name, at, lit?}], drift (degrees of longitude a second after the move, default 0.15)
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {AbsoluteFill} from 'remotion';
import {useT} from '../lib';
import {DS, Tag, enterP, enterStyle, lightP} from '../kit3';
import {CURVE, Cam, Load, Stage3D, V3, all, lerp, prog, project, rad, useAssets} from './core';

// a point on the globe (radius r) at latitude / longitude, in three's SphereGeometry frame (u = 0 at longitude -180, the texture's left)
export const ll = (lat: number, lon: number, r = 1): V3 => {
  const phi = rad(lon + 180);
  const theta = rad(90 - lat);
  return [-Math.cos(phi) * Math.sin(theta) * r, Math.cos(theta) * r, Math.sin(phi) * Math.sin(theta) * r];
};

export type GeoView = {lat: number; lon: number; alt: number; tilt?: number};
export type Pin = {lat: number; lon: number; name: string; at: number; lit?: number};

// the camera for a view: above (lat - tilt offset) looking at the ground point, `alt` radii up
const camFor = (v: GeoView): Cam => {
  const tilt = Math.min(70, v.tilt ?? 0);
  // a tilted view stands back toward the south along the meridian (alt x tan(tilt) of arc), so the horizon rises into the top of the
  // frame on a low, steep view
  const back = Math.min(0.6, v.alt * Math.tan(rad(tilt)));
  const pos = ll(v.lat - (back * 180) / Math.PI, v.lon, 1 + v.alt);
  const target = ll(v.lat, v.lon, 1);
  return {pos, target, fov: 32, near: 0.001, far: 50};
};

// blend two views: lat/lon linear, altitude on a log scale (a zoom feels even)
const mix = (a: GeoView, b: GeoView, u: number): GeoView => ({
  lat: lerp(a.lat, b.lat, u), lon: lerp(a.lon, b.lon, u), alt: Math.exp(lerp(Math.log(a.alt), Math.log(b.alt), u)),
  tilt: lerp(a.tilt ?? 0, b.tilt ?? 0, u),
});

const ATMO = {
  vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
  // outside the limb: the back faces of a slightly larger sphere, brightest where they graze the planet's edge
  halo: 'uniform vec3 c; uniform float k; varying vec3 vN; varying vec3 vV; void main(){ float d = dot(vN, vV); float f = pow(clamp(1.0 + d, 0.0, 1.0), 9.0); gl_FragColor = vec4(c*f*k, 1.0); }',
  // on the disc: a faint rim where the ground turns away
  rim: 'uniform vec3 c; uniform float k; varying vec3 vN; varying vec3 vV; void main(){ float d = clamp(dot(vN, vV), 0.0, 1.0); float f = pow(1.0 - d, 6.0); gl_FragColor = vec4(c*f*k, 1.0); }',
};

// the ~1-km patch: lon -19..-3, lat 33..47 (kit3d_assets.py earth), a sphere segment just above the world, its edges feathered
const PATCH = {lon0: -19, lon1: -3, lat0: 33, lat1: 47};
const patchMaterial = (tex: THREE.Texture) => new THREE.ShaderMaterial({
  uniforms: {map: {value: tex}},
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
  fragmentShader: `uniform sampler2D map; varying vec2 vUv;
    void main(){ vec4 c = texture2D(map, vUv); float e = min(min(vUv.x, 1.0-vUv.x), min(vUv.y, 1.0-vUv.y)); float a = smoothstep(0.0, 0.08, e);
      gl_FragColor = vec4(c.rgb, a);
      #include <colorspace_fragment>
    }`,
  transparent: true, depthWrite: false,
});

const Earth: React.FC<{world: THREE.Texture; patch: THREE.Texture}> = ({world, patch}) => {
  const m = useMemo(() => {
    const geo = new THREE.SphereGeometry(1, 256, 128);
    const mat = new THREE.MeshBasicMaterial({map: world});
    // SphereGeometry: phi from -180 lon (u = 0), theta from the north pole
    const pg = new THREE.SphereGeometry(1.0004, 128, 112, rad(PATCH.lon0 + 180), rad(PATCH.lon1 - PATCH.lon0), rad(90 - PATCH.lat1),
      rad(PATCH.lat1 - PATCH.lat0));
    const pm = patchMaterial(patch);
    // a thin line at the limb and a faint haze inside it (a wide halo and a strong rim read as two blue rings: a cheap look)
    const halo = new THREE.ShaderMaterial({uniforms: {c: {value: new THREE.Color('#6a9bff')}, k: {value: 0.9}}, vertexShader: ATMO.vertexShader,
      fragmentShader: ATMO.halo, blending: THREE.AdditiveBlending, side: THREE.BackSide, depthWrite: false, transparent: true});
    const rim = new THREE.ShaderMaterial({uniforms: {c: {value: new THREE.Color('#4f86ff')}, k: {value: 0.22}}, vertexShader: ATMO.vertexShader,
      fragmentShader: ATMO.rim, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true});
    return {geo, mat, pg, pm, halo, rim};
  }, [world, patch]);
  return (
    <group>
      <mesh geometry={m.geo} material={m.mat} />
      <mesh geometry={m.pg} material={m.pm} renderOrder={1} />
      <mesh geometry={m.geo} material={m.rim} scale={1.0006} renderOrder={2} />
      <mesh geometry={m.geo} material={m.halo} scale={1.018} renderOrder={3} />
    </group>
  );
};

const PinDot: React.FC<{p: Pin; t: number}> = ({p, t}) => {
  const lit = p.lit === undefined ? 0 : lightP(t, p.lit);
  const u = enterP(t, p.at, 0.3);
  const pos = ll(p.lat, p.lon, 1.0012);
  // the material is ours and its colour is set on every render: a Color object passed as a prop and mutated in place is never seen
  // again by R3F (same reference), so a tab that first drew the pin unlit would keep it unlit (the clip's pin in ink, the still's in the
  // accent)
  const mat = useMemo(() => new THREE.MeshBasicMaterial({toneMapped: false}), []);
  mat.color.set(DS.INK).lerp(new THREE.Color(DS.ACCENT), lit);
  return (
    <mesh position={pos} scale={Math.max(0.001, u)} material={mat}>
      <sphereGeometry args={[0.0018, 24, 16]} />
    </mesh>
  );
};

export const Globe3D: React.FC<{dur: number; from: GeoView; to: GeoView; at?: number; move?: number; pins?: Pin[]; drift?: number}> = ({
  dur, from, to, at = 0, move = 3.2, pins = [], drift = 0.15}) => {
  const t = useT();
  const a = useAssets('globe', () => all({world: Load.texture('kit3d/earth/blackmarble_8k.jpg'), patch: Load.texture('kit3d/earth/bm500_patch.jpg')}));
  if (!a) return null;
  void dur;
  const u = prog(t, at, move, CURVE.drift);
  const v = mix(from, to, u);
  v.lon += Math.max(0, t - at - move) * drift;
  const cam = camFor(v);
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <Stage3D kind="Globe3D" cam={cam} bg="#000000" tone="neutral" post={{bloom: {strength: 0.35, radius: 0.45, threshold: 0.82}, grain: 0.012}}>
        <Earth world={a.world} patch={a.patch} />
        {pins.map((p) => <PinDot key={p.name} p={p} t={t} />)}
      </Stage3D>
      {pins.map((p) => {
        const s = project(cam, ll(p.lat, p.lon, 1.0012));
        const facing = (() => {
          const g = new THREE.Vector3(...ll(p.lat, p.lon, 1));
          const c = new THREE.Vector3(...cam.pos);
          return g.clone().normalize().dot(c.sub(g).normalize()) > 0.05;
        })();
        if (!facing || s.z > 1) return null;
        const e = enterP(t, p.at);
        return (
          <div key={p.name} style={{position: 'absolute', left: s.x + 22, top: s.y, transform: 'translateY(-50%)', ...enterStyle(e, 0, -16)}}>
            <Tag lit={p.lit === undefined ? 0 : lightP(t, p.lit)}>{p.name}</Tag>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
