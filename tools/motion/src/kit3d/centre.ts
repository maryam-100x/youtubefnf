// kit3d · where a 3D object lands on the frame, measured from its own geometry (a logo placed by its geometry's origin reads off centre
// when its weight sits to one side).
//
// A piece that shows ONE object meant to stand on a point of the frame (Emblem3D's logo, Phone3D's phone) places it by what the viewer
// sees, never by its geometry's origin; a GROUP (CaseNumber3D's box, number and the HTML under it) by its whole visible content's box, as
// kit3's rows centre theirs. On every frame the object's meshes are projected through that frame's own camera (three's matrices, the math the
// renderer draws with), the silhouette is rasterised on a 2-px grid, and its VISUAL CENTRE is taken the house's way: left to right,
// halfway between the box of the visible pixels and their centre of mass (centred to the eye, not by the box: box-centred and
// mass-centred each miss by half); up and down, the box's middle (a V-shaped logo's weight would pull it below the optical centre, which
// sits at or a touch above the middle). The camera then pans, parallel to the picture, until that point sits on the intended one (two
// passes reach a tenth of a pixel). Aimed at the shape's viewBox centre instead (its BOX centre), a logo whose weight sits on one side
// (a solid block, the lettering) lands ~25 px off the frame's centre.
//
// Pure math on three's own classes: it runs in the browser and in node (src/kit3d/test/centre.test.mjs), no WebGL, no DOM.
//   silhouette(parts, cam)        the projected object: box (clipped to the frame), centroid, visual centre, area, cut (past an edge)
//   centreOn(parts, camAt, P, ..., mode, extra)  the camera that puts the point (mode 'eye': the visual centre; 'box': the content's box
//                                 with `extra` HTML boxes) on P (px of the 1920 x 1080 frame), and the residual
//   centreVerdict(...)            the piece's `kit3d|` probe line and its refusal past CENTRE_TOL
//   emblemGeometry, phoneGeometry, caseGeometry + glyphGeometries + caseNumberParts: each piece's meshes, shared by the measure and the
//                                 drawing, so what is measured is what is drawn
import * as THREE from 'three';
import {TextGeometry} from 'three/examples/jsm/geometries/TextGeometry.js';
import type {Font} from 'three/examples/jsm/loaders/FontLoader.js';

export type V3 = [number, number, number];
export type CamSpec = {pos: V3; target: V3; fov: number; up?: V3; near?: number; far?: number};
export type Placed = {geo: THREE.BufferGeometry; matrix: THREE.Matrix4};
export type Silhouette = {
  box: [number, number, number, number];   // x0, y0, x1, y1 of the visible pixels, px of the frame
  centroid: [number, number];              // their centre of mass
  visual: [number, number];                // x halfway between the box's centre and the centroid (centred to the eye); y the box's middle
  area: number;                            // px²
  cut: boolean;                            // some of the object lies past the frame's edge
};

export const FRAME_W = 1920;
export const FRAME_H = 1080;
export const CENTRE_TOL = 2;                // px a centred object may sit off its point before the piece refuses (the gate's LOGO_OFF_CENTRE: 8)

const camera = (cam: CamSpec, W: number, H: number) => {
  const c = new THREE.PerspectiveCamera(cam.fov, W / H, cam.near ?? 0.05, cam.far ?? 200);
  c.position.set(cam.pos[0], cam.pos[1], cam.pos[2]);
  const up = cam.up ?? [0, 1, 0];
  c.up.set(up[0], up[1], up[2]);
  c.lookAt(cam.target[0], cam.target[1], cam.target[2]);
  c.updateProjectionMatrix();
  c.updateMatrixWorld();
  return c;
};

// a world point on the frame (px), by the same camera (core.tsx's `project` does the same for HTML placed on a 3D point)
export const projectPoint = (cam: CamSpec, p: V3, W = FRAME_W, H = FRAME_H): [number, number] => {
  const v = new THREE.Vector3(p[0], p[1], p[2]).project(camera(cam, W, H));
  return [((v.x + 1) / 2) * W, ((1 - v.y) / 2) * H];
};

// the object's pixels on the frame: every triangle of every mesh, projected and filled at the centres of a `cell`-px grid; the box from
// the vertices themselves (exact), clipped to the frame like the pixels
export const silhouette = (parts: Placed[], cam: CamSpec, W = FRAME_W, H = FRAME_H, cell = 2): Silhouette => {
  const c = camera(cam, W, H);
  const pv = new THREE.Matrix4().multiplyMatrices(c.projectionMatrix, c.matrixWorldInverse);
  const GW = Math.ceil(W / cell), GH = Math.ceil(H / cell);
  const grid = new Uint8Array(GW * GH);
  let bx0 = Infinity, by0 = Infinity, bx1 = -Infinity, by1 = -Infinity;
  const v = new THREE.Vector3();
  const fill = (ax: number, ay: number, bx: number, by: number, cx: number, cy: number) => {
    // sort by y, then fill each grid row whose centre line crosses the triangle, between its two edges
    if (ay > by) [ax, ay, bx, by] = [bx, by, ax, ay];
    if (ay > cy) [ax, ay, cx, cy] = [cx, cy, ax, ay];
    if (by > cy) [bx, by, cx, cy] = [cx, cy, bx, by];
    if (cy - ay < 1e-9) return;
    const j0 = Math.max(0, Math.ceil(ay / cell - 0.5)), j1 = Math.min(GH - 1, Math.floor(cy / cell - 0.5));
    for (let j = j0; j <= j1; j++) {
      const py = (j + 0.5) * cell;
      const xl = ax + (cx - ax) * ((py - ay) / (cy - ay));
      const xs = py < by ? ax + (bx - ax) * ((py - ay) / Math.max(1e-9, by - ay)) : bx + (cx - bx) * ((py - by) / Math.max(1e-9, cy - by));
      const lo = Math.min(xl, xs), hi = Math.max(xl, xs);
      const i0 = Math.max(0, Math.ceil(lo / cell - 0.5)), i1 = Math.min(GW - 1, Math.floor(hi / cell - 0.5));
      const row = j * GW;
      for (let i = i0; i <= i1; i++) grid[row + i] = 1;
    }
  };
  for (const {geo, matrix} of parts) {
    const m = new THREE.Matrix4().multiplyMatrices(pv, matrix);
    const pos = geo.getAttribute('position') as THREE.BufferAttribute;
    const n = pos.count;
    const sx = new Float64Array(n), sy = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      v.fromBufferAttribute(pos, i).applyMatrix4(m);
      sx[i] = ((v.x + 1) / 2) * W;
      sy[i] = ((1 - v.y) / 2) * H;
      if (sx[i] < bx0) bx0 = sx[i];
      if (sx[i] > bx1) bx1 = sx[i];
      if (sy[i] < by0) by0 = sy[i];
      if (sy[i] > by1) by1 = sy[i];
    }
    const idx = geo.getIndex();
    const tri = idx ? idx.count / 3 : n / 3;
    for (let k = 0; k < tri; k++) {
      const a = idx ? idx.getX(3 * k) : 3 * k, b = idx ? idx.getX(3 * k + 1) : 3 * k + 1, d = idx ? idx.getX(3 * k + 2) : 3 * k + 2;
      fill(sx[a], sy[a], sx[b], sy[b], sx[d], sy[d]);
    }
  }
  let cnt = 0, sxs = 0, sys = 0;
  for (let j = 0; j < GH; j++) {
    const row = j * GW;
    for (let i = 0; i < GW; i++) {
      if (grid[row + i]) {
        cnt++;
        sxs += i;
        sys += j;
      }
    }
  }
  const cut = bx0 < 0 || by0 < 0 || bx1 > W || by1 > H;
  const box: [number, number, number, number] = [Math.max(0, bx0), Math.max(0, by0), Math.min(W, bx1), Math.min(H, by1)];
  const centroid: [number, number] = cnt ? [(sxs / cnt + 0.5) * cell, (sys / cnt + 0.5) * cell] : [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2];
  const visual: [number, number] = [((box[0] + box[2]) / 2 + centroid[0]) / 2, (box[1] + box[3]) / 2];
  return {box, centroid, visual, area: cnt * cell * cell, cut};
};

// the point a piece puts on its mark: ONE object by the eye (`visual`); a GROUP (CaseNumber3D: the box, its number and the HTML
// under it) by its whole visible content's box, as kit3's rows centre theirs (B14), `extra` adding the boxes of its HTML (px, x0 y0 x1 y1)
export type CentreMode = 'eye' | 'box';
export const pointOf = (sil: Silhouette, mode: CentreMode, extra: [number, number, number, number][] = []): [number, number] => {
  if (mode === 'eye') return sil.visual;
  const b = [sil.box, ...extra];
  const x0 = Math.min(...b.map((q) => q[0])), x1 = Math.max(...b.map((q) => q[2]));
  const y0 = Math.min(...b.map((q) => q[1])), y1 = Math.max(...b.map((q) => q[3]));
  return [(x0 + x1) / 2, (y0 + y1) / 2];
};

// the camera that puts the piece's point on P: `camAt(pan)` is the piece's own camera moved by `pan` (position and target alike, so the
// view's direction and the object's look stay the same); each pass pans by the error at the target's distance
export const centreOn = (parts: Placed[], camAt: (pan: V3) => CamSpec, P: [number, number], W = FRAME_W, H = FRAME_H, passes = 3,
  mode: CentreMode = 'eye', extra?: (cam: CamSpec) => [number, number, number, number][]) => {
  let pan: V3 = [0, 0, 0];
  let cam = camAt(pan);
  let sil = silhouette(parts, cam, W, H);
  let point = pointOf(sil, mode, extra ? extra(cam) : []);
  const before = sil;
  for (let k = 0; k < passes; k++) {
    const ex = point[0] - P[0], ey = point[1] - P[1];
    if (Math.abs(ex) < 0.05 && Math.abs(ey) < 0.05) break;
    const c = camera(cam, W, H);
    const right = new THREE.Vector3().setFromMatrixColumn(c.matrixWorld, 0);
    const up = new THREE.Vector3().setFromMatrixColumn(c.matrixWorld, 1);
    const d = new THREE.Vector3(...cam.pos).distanceTo(new THREE.Vector3(...cam.target));
    const ppu = H / (2 * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2) * d);   // px per world unit at the target's distance
    pan = [pan[0] + (ex / ppu) * right.x - (ey / ppu) * up.x, pan[1] + (ex / ppu) * right.y - (ey / ppu) * up.y,
      pan[2] + (ex / ppu) * right.z - (ey / ppu) * up.z];
    cam = camAt(pan);
    sil = silhouette(parts, cam, W, H);
    point = pointOf(sil, mode, extra ? extra(cam) : []);
  }
  return {cam, sil, before, pan, point, err: [point[0] - P[0], point[1] - P[1]] as [number, number]};
};

// what every centred piece does with the result: in the gate's probe a `kit3d|` line per frame (qa_centred.py's LOGO_OFF_CENTRE reads
// `visual` against `target`); past CENTRE_TOL, or cut by the frame, the piece refuses (the still, the probe's B15, the render stop)
export const centreVerdict = (kind: string, what: string, c: ReturnType<typeof centreOn>, P: [number, number], t: number, mode: CentreMode) => {
  const r1 = (n: number) => Math.round(n * 100) / 100;
  const line = {kind, what, mode, box: c.sil.box.map(r1), centroid: c.sil.centroid.map(r1), visual: c.point.map(r1), target: P, cut: c.sil.cut};
  const bad = Math.abs(c.err[0]) > CENTRE_TOL || Math.abs(c.err[1]) > CENTRE_TOL || c.sil.cut;
  const msg = bad ? `kit3d ${kind} ${what}: its ${mode === 'eye' ? 'visual centre' : 'visible content'} sits (${c.err[0].toFixed(1)}, `
    + `${c.err[1].toFixed(1)}) px off its point (${P[0]}, ${P[1]})${c.sil.cut ? ', cut by the frame' : ''} at ${t.toFixed(2)} s (over `
    + `${CENTRE_TOL} px). A smaller size, a nearer x/y, or a camera that keeps the whole of it in view` : '';
  return {line, msg};
};

// ============================================================================================================================ Emblem3D
type Ring = number[][];
export type ShapeData = {w: number; h: number; png: string; base: {outer: Ring; holes: Ring[]}[]; raised: {outer: Ring; holes: Ring[]}[]};
export const EMBLEM_W = 4;   // the emblem's width in world units

const shapesOf = (list: ShapeData['base'], d: ShapeData) => list.map(({outer, holes}) => {
  const P = (p: number[]) => new THREE.Vector2(((p[0] - d.w / 2) / d.w) * EMBLEM_W, (-(p[1] - d.h / 2) / d.w) * EMBLEM_W);
  const sh = new THREE.Shape(outer.map(P));
  for (const h of holes) sh.holes.push(new THREE.Path(h.map(P)));
  return sh;
});

// the base silhouette extruded with a rounded bevel, the lettering block standing a little prouder (emblem.tsx's look, unchanged)
export const emblemGeometry = (d: ShapeData, depth: number) => {
  const D = depth * EMBLEM_W;
  const bt = D * 0.22;   // bevel: thickness and size, so the edge rounds into the side
  const base = new THREE.ExtrudeGeometry(shapesOf(d.base, d), {depth: D, bevelEnabled: true, bevelThickness: bt, bevelSize: bt * 0.7,
    bevelSegments: 6, curveSegments: 1, steps: 1});
  const rD = D * 0.32;
  const rbt = rD * 0.35;
  const raised = new THREE.ExtrudeGeometry(shapesOf(d.raised, d), {depth: rD, bevelEnabled: true, bevelThickness: rbt, bevelSize: rbt * 0.8,
    bevelSegments: 5, curveSegments: 1, steps: 1});
  // the base from z = -bt to D + bt, its depth centred on z = 0; the raised block's back sits on the base's face
  const zBase = -(D + 2 * bt) / 2 + bt;
  const zFront = zBase + D + bt;
  const zRaised = zFront + rbt - rbt * 0.25;
  const parts: Placed[] = [
    {geo: base, matrix: new THREE.Matrix4().makeTranslation(0, 0, zBase)},
    {geo: raised, matrix: new THREE.Matrix4().makeTranslation(0, 0, zRaised)},
  ];
  return {base, raised, zBase, zRaised, parts, H: (d.h / d.w) * EMBLEM_W};
};

// ============================================================================================================================ Phone3D
// a rounded rectangle centred on 0 (device.tsx's outline)
export const roundedShape = (w: number, h: number, r: number) => {
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

// the phone's slab as held: the screen `aspect` long by 1 short, bezels round it, depth 0.085 (its silhouette: the screen, the glass and
// the camera hole lie on its face). `parts(yaw, pitch)`: the slab turned as the piece turns it
export const phoneGeometry = (aspect: number, landscape: boolean) => {
  const bez = 0.035;
  const sw = landscape ? aspect : 1;
  const sh = landscape ? 1 : aspect;
  const W = sw + 2 * bez;
  const H = sh + 2 * bez;
  const D = 0.085;
  const R = 0.13;
  const body = new THREE.ExtrudeGeometry(roundedShape(W - 0.024, H - 0.024, R - 0.012), {depth: D - 0.024, bevelEnabled: true,
    bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 8, curveSegments: 24});
  body.translate(0, 0, -(D - 0.024) / 2);
  const parts = (yawDeg: number, pitchDeg: number): Placed[] => [{geo: body,
    matrix: new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler((pitchDeg * Math.PI) / 180, (yawDeg * Math.PI) / 180, 0))}];
  return {body, bez, sw, sh, W, H, D, R, parts};
};

// ======================================================================================================================= CaseNumber3D
// a product case: 1.35 x 1.70 x 0.14 (1 unit = 100 mm), rounded corners (objects.tsx's Case3D)
const roundedRectQ = (w: number, h: number, r: number) => {
  const s = new THREE.Shape();
  const x = -w / 2;
  const y = -h / 2;
  s.moveTo(x + r, y);
  s.lineTo(x + w - r, y);
  s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r);
  s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h);
  s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r);
  s.quadraticCurveTo(x, y, x + r, y);
  return s;
};
export const CASE_W = 1.35;
export const CASE_H = 1.7;
export const caseGeometry = () => {
  const d = 0.14;
  const b = 0.012;
  const geo = new THREE.ExtrudeGeometry(roundedRectQ(CASE_W - 2 * b, CASE_H - 2 * b, 0.035), {depth: d - 2 * b, bevelEnabled: true, bevelThickness: b,
    bevelSize: b, bevelSegments: 4, curveSegments: 8});
  geo.translate(0, 0, -(d - 2 * b) / 2);
  return geo;
};

// the number's glyphs one by one (each stands up on its own), laid out by the font's own advances (TextGeometry per glyph)
export const glyphGeometries = (font: Font, text: string, size: number, depth: number) => {
  const out: {geo: THREE.BufferGeometry; x: number; w: number}[] = [];
  let x = 0;
  const data = (font as unknown as {data: {glyphs: Record<string, {ha: number}>; resolution: number}}).data;
  const scale = size / data.resolution;
  for (const ch of text) {
    const g = data.glyphs[ch];
    if (!g) throw new Error(`kit3d Number3D: "${ch}" is not in the font`);
    const adv = g.ha * scale;
    if (ch !== ' ') {
      const geo = new TextGeometry(ch, {font, size, depth, curveSegments: 10, bevelEnabled: true, bevelThickness: depth * 0.12,
        bevelSize: size * 0.012, bevelSegments: 4});
      geo.computeBoundingBox();
      out.push({geo, x, w: adv});
    }
    x += adv;
  }
  return {glyphs: out, width: x, depth};
};

// the case and the number as they stand once every digit is up (the group is centred on its FINAL content from the first frame, as
// kit3's rows place their items: nothing slides while the digits stand up)
export const caseNumberParts = (caseGeo: THREE.BufferGeometry, caseX: number, rotY: number, num: ReturnType<typeof glyphGeometries>,
  numX: number, baseY: number): Placed[] => [
  {geo: caseGeo, matrix: new THREE.Matrix4().makeTranslation(caseX, 0, 0).multiply(new THREE.Matrix4().makeRotationY(rotY))},
  ...num.glyphs.map((g) => ({geo: g.geo, matrix: new THREE.Matrix4().makeTranslation(numX + g.x - num.width / 2, baseY, -num.depth / 2)})),
];
