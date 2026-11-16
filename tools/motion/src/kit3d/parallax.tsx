// kit3d · Parallax25D: a real screenshot turned into a shot with depth (standard/3D.md §5).
//
// Two layers built by kit3d_assets.py parallax: the subject (its own pixels, its matte) and the background behind it (the same picture,
// the subject's region filled by OpenCV's Telea inpainting, classical, no generated content). Each layer is a mesh of 480 x 270 cells
// whose every vertex sits on the ray through its pixel at the depth Depth-Anything-V2-Small read for it (1/Z linear in the model's
// relative inverse depth, from `near` to `far`). Seen from the origin (the middle of the move) the shot IS the screenshot, pixel for
// pixel; as the camera moves, near things move more than far ones. The subject's depth is read from its core only and filled outward
// past its outline (kit3d_assets.py), so the outline moves exactly with the subject (a depth read up to the edge smears it into teeth); the slivers the
// move uncovers behind it show the filled background.
//
// The camera: ONE linear move over the shot (the house camera is linear: an eased push stands still in its last third, the gate's
// STILL), a dolly in plus a slide, turning round the subject's depth (`pivot`) so the subject holds its place and the world turns
// behind it. Keep it small: the fill and the depth's guesses show past ~3% of the frame's width of parallax.
//
// Props: src (public path without extension: 'kit3d/img/demo_people' reads _fg.png, _bg.jpg, _depth.png, _bgdepth.png), dur,
//   dolly (world units toward the subject, default 0.35), slide ([x, y], default [0.14, 0.03]: ~40 px of parallax at 1440p), near/far (default 5 / 14: the depth
//   range, their ratio is the parallax's strength), pivot (0..1 of the way from near to far the camera turns round, default 0.08),
//   overscan (default 1.07: the edges stay covered through the slide), fov (default 30), start (0..1: where in the move the shot
//   begins, for a cut inside a longer move)
import React, {useMemo} from 'react';
import * as THREE from 'three';
import {AbsoluteFill} from 'remotion';
import {useT} from '../lib';
import {Cam, Load, Stage3D, all, lerp, useAssets} from './core';

const COLS = 720;
const ROWS = 405;

// the depth at (u, v), bilinear between the four pixels round it (16-bit, packed R high, G low)
const depthAt = (img: ImageData, u: number, v: number) => {
  const fx = Math.min(img.width - 1, Math.max(0, u * (img.width - 1)));
  const fy = Math.min(img.height - 1, Math.max(0, (1 - v) * (img.height - 1)));
  const x0 = Math.floor(fx);
  const y0 = Math.floor(fy);
  const x1 = Math.min(img.width - 1, x0 + 1);
  const y1 = Math.min(img.height - 1, y0 + 1);
  const ax = fx - x0;
  const ay = fy - y0;
  const at = (x: number, y: number) => {
    const i = (y * img.width + x) * 4;
    return (img.data[i] * 256 + img.data[i + 1]) / 65535;
  };
  return (at(x0, y0) * (1 - ax) + at(x1, y0) * ax) * (1 - ay) + (at(x0, y1) * (1 - ax) + at(x1, y1) * ax) * ay;
};

// the layer's mesh: each vertex on its pixel's ray at its depth (camera at the origin looking down -z)
const layerGeometry = (img: ImageData, near: number, far: number, fov: number, aspect: number, overscan: number) => {
  const n = (COLS + 1) * (ROWS + 1);
  const pos = new Float32Array(n * 3);
  const uv = new Float32Array(n * 2);
  const ty = Math.tan((fov / 2) * Math.PI / 180) * overscan;
  const tx = ty * aspect;
  let k = 0;
  for (let j = 0; j <= ROWS; j++) {
    const v = j / ROWS;
    for (let i = 0; i <= COLS; i++) {
      const u = i / COLS;
      const d = depthAt(img, u, v);
      const Z = 1 / (1 / far + d * (1 / near - 1 / far));
      pos[k * 3] = (u * 2 - 1) * tx * Z;
      pos[k * 3 + 1] = (v * 2 - 1) * ty * Z;
      pos[k * 3 + 2] = -Z;
      uv[k * 2] = u;
      uv[k * 2 + 1] = v;
      k++;
    }
  }
  const idx = new Uint32Array(COLS * ROWS * 6);
  let q = 0;
  for (let j = 0; j < ROWS; j++) {
    for (let i = 0; i < COLS; i++) {
      const a = j * (COLS + 1) + i;
      const b = a + 1;
      const c = a + COLS + 1;
      const e = c + 1;
      idx.set([a, b, c, b, e, c], q);
      q += 6;
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
};

const Layers: React.FC<{a: {fg: THREE.Texture; bg: THREE.Texture; fgd: ImageData; bgd: ImageData}; near: number; far: number; fov: number;
  overscan: number}> = ({a, near, far, fov, overscan}) => {
  const m = useMemo(() => {
    const aspect = 16 / 9;
    const bgGeo = layerGeometry(a.bgd, near, far, fov, aspect, overscan);
    const fgGeo = layerGeometry(a.fgd, near, far, fov, aspect, overscan);
    const bgMat = new THREE.MeshBasicMaterial({map: a.bg, toneMapped: false});
    const fgMat = new THREE.MeshBasicMaterial({map: a.fg, toneMapped: false, transparent: true, depthWrite: false});
    return {bgGeo, fgGeo, bgMat, fgMat};
  }, [a, near, far, fov, overscan]);
  return (
    <group>
      <mesh geometry={m.bgGeo} material={m.bgMat} />
      <mesh geometry={m.fgGeo} material={m.fgMat} renderOrder={1} />
    </group>
  );
};

export const Parallax25D: React.FC<{src: string; dur: number; dolly?: number; slide?: [number, number]; near?: number; far?: number;
  pivot?: number; overscan?: number; fov?: number; start?: number}> = ({src, dur, dolly = 0.35, slide = [0.14, 0.03], near = 5, far = 14,
  pivot = 0.08, overscan = 1.07, fov = 30, start = 0}) => {
  const t = useT();
  const a = useAssets(`parallax:${src}`, () => all({
    fg: Load.texture(`${src}_fg.png`), bg: Load.texture(`${src}_bg.jpg`), fgd: Load.pixels(`${src}_depth.png`), bgd: Load.pixels(`${src}_bgdepth.png`),
  }));
  if (!a) return null;
  const u = lerp(start, 1, Math.min(1, Math.max(0, t / Math.max(0.01, dur))));
  const Zp = near + (far - near) * pivot;
  // the camera slides by `slide` and dollies by `dolly`, always looking at the pivot point straight ahead of where it started
  const pos: [number, number, number] = [-slide[0] / 2 + slide[0] * u, -slide[1] / 2 + slide[1] * u, -dolly * u];
  const cam: Cam = {pos, target: [0, 0, -Zp], fov, near: 0.1, far: far * 3};
  return (
    <AbsoluteFill>
      <Stage3D kind="Parallax25D" cam={cam} post={false} tone="none" bg="#000000">
        <Layers a={a} near={near} far={far} fov={fov} overscan={overscan} />
      </Stage3D>
    </AbsoluteFill>
  );
};
