// kit3d's centring, tested in node (no browser, no Remotion job): node src/kit3d/test/centre.test.mjs [--json <out>] (from tools/motion)
// It compiles centre.ts with esbuild and runs an emblem shot (lopsided.mjs: a logo whose weight sits right of its box's middle) two
// ways, frame by frame over the shot (2.125 s at 60 fps, the move 1.5 s):
//   aimed   the camera aimed at the shape's origin (the viewBox centre = the logo's BOX centre)
//   now  Emblem3D's camera (centreOn: the visual centre, panned onto the frame's centre)
// and prints where the logo's visible pixels sit against the frame's centre. --json writes the per-frame numbers and `kit3d|` lines in
// the gate probe's format (qa_centred.py reads them: it must flag aimed and pass now).
// Then Phone3D (its slab turning 32 -> 6 deg, a 5-s shot) and CaseNumber3D (the box, "230" in Archivo ExtraBold and an HTML block under
// it, a 5-s shot) the same way: before (a camera aimed at the origin) and now (centred every frame). CaseNumber3D reads Archivo
// ExtraBold's TTF from the public dir (kit3d/fonts/Archivo-ExtraBold.ttf, kit3d_assets.py lists it): without it that part is skipped,
// and says so.
import {buildSync} from 'esbuild';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {PUBLIC} from '../../../../common/paths.mjs';
import {lopsided} from './lopsided.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(os.tmpdir(), `kit3d_centre_${process.pid}.mjs`);
buildSync({stdin: {contents: "export * from './centre';\nexport {TTFLoader} from 'three/examples/jsm/loaders/TTFLoader.js';\n"
  + "export {Font} from 'three/examples/jsm/loaders/FontLoader.js';\n", resolveDir: path.join(here, '..'), loader: 'ts'},
outfile: out, format: 'esm', bundle: true, platform: 'node', logLevel: 'error'});
const C = await import(pathToFileURL(out).href);
fs.unlinkSync(out);

// remotion's own easing (the house EASE.move: core.tsx CURVE.move), so the poses are the component's
const ease = (() => {
  // cubic-bezier(0.2, 0, 0, 1) solved as CSS does (Newton on x, then y)
  const [x1, y1, x2, y2] = [0.2, 0, 0, 1];
  const bx = (s) => 3 * x1 * s * (1 - s) ** 2 + 3 * x2 * s * s * (1 - s) + s ** 3;
  const by = (s) => 3 * y1 * s * (1 - s) ** 2 + 3 * y2 * s * s * (1 - s) + s ** 3;
  const dbx = (s) => 3 * x1 * (1 - s) ** 2 + 6 * (x2 - x1) * s * (1 - s) + 3 * (1 - x2) * s * s;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let s = x;
    for (let i = 0; i < 12; i++) {
      const e = bx(s) - x;
      const dv = dbx(s);
      if (Math.abs(e) < 1e-9 || dv === 0) break;
      s -= e / dv;
    }
    let lo = 0, hi = 1;
    for (let i = 0; i < 40 && Math.abs(bx(s) - x) > 1e-7; i++) {
      s = (lo + hi) / 2;
      if (bx(s) < x) lo = s; else hi = s;
    }
    return by(s);
  };
})();
const prog = (t, at, d) => ease(Math.min(1, Math.max(0, (t - at) / Math.max(1e-3, d))));
const lerp = (a, b, u) => a + (b - a) * u;
const rad = (d) => (d * Math.PI) / 180;
const orbit = (c, dist, az, el) => [c[0] + dist * Math.cos(rad(el)) * Math.sin(rad(az)), c[1] + dist * Math.sin(rad(el)),
  c[2] + dist * Math.cos(rad(el)) * Math.cos(rad(az))];

const d = lopsided();
const g = C.emblemGeometry(d, 0.05);

// the shot: an emblem's first shot of a video, 0.02 s to 2.145 s, move = min(1.5, max(0.9, d - 0.3))
const FPS = 60;
const dur = 2.145 - 0.02;
const P = {at: 0, move: Math.min(1.5, Math.max(0.9, dur - 0.3)), height: 0.5, from: [-30, 9], to: [-8, 3], drift: 0.8, x: 0, y: 0};
const fov = 30;
const dist = g.H / P.height / (2 * Math.tan(rad(fov / 2)));
const pose = (t) => {
  const u = prog(t, P.at, P.move);
  return {az: lerp(P.from[0], P.to[0], u) + Math.max(0, t - P.at - P.move) * P.drift, el: lerp(P.from[1], P.to[1], u), k: lerp(1.12, 1, u)};
};
// aimed: the camera aimed at the shape's origin
const camAimed = (t) => {
  const {az, el, k} = pose(t);
  const vh = 2 * Math.tan(rad(fov / 2)) * dist;
  const aim = [-P.x * vh * (16 / 9), -P.y * vh, 0];
  return {pos: orbit(aim, dist * k, az, el), target: aim, fov, near: 0.1, far: 100};
};
// now: Emblem3D's camera (centreOn)
const camAt = (t) => (pan) => {
  const {az, el, k} = pose(t);
  const o = orbit([0, 0, 0], dist * k, az, el);
  return {pos: [o[0] + pan[0], o[1] + pan[1], o[2] + pan[2]], target: pan, fov, near: 0.1, far: 100};
};
const target = [960 + P.x * 1920, 540 - P.y * 1080];

const rows = [];
const lines = [];
const frames = Math.round(dur * FPS);
const t0 = Date.now();
for (let fr = 0; fr < frames; fr++) {
  const t = fr / FPS;
  const a = C.silhouette(g.parts, camAimed(t));
  const b = C.centreOn(g.parts, camAt(t), target);
  rows.push({frame: fr, t: +t.toFixed(4), aimed: a, now: b.sil, err: b.err});
  const abs = Math.round(0.02 * FPS) + fr;
  for (const [tag, s] of [['aimed', a], ['now', b.sil]]) {
    lines.push({tag, line: `kit3d|${JSON.stringify({frame: abs, kind: 'Emblem3D', what: 'lopsided test logo',
      box: s.box.map((x) => +x.toFixed(2)), centroid: s.centroid.map((x) => +x.toFixed(2)), visual: s.visual.map((x) => +x.toFixed(2)),
      target, cut: s.cut})}`});
  }
}
const ms = (Date.now() - t0) / frames;

let pass = 0, fail = 0;
const ok = (cond, what) => {
  if (cond) pass++;
  else {
    fail++;
    console.log(`FAIL ${what}`);
  }
};
const f1 = (x) => (x >= 0 ? '+' : '') + x.toFixed(1);
console.log('frame    t   | aimed: box centre  centroid  visual (x - 960, px)  | now: visual x, y error');
for (const r of rows.filter((_, i) => i % 15 === 0 || i === rows.length - 1)) {
  const bc = (r.aimed.box[0] + r.aimed.box[2]) / 2 - 960;
  console.log(`${String(r.frame).padStart(4)} ${r.t.toFixed(2).padStart(5)} | ${f1(bc).padStart(8)} ${f1(r.aimed.centroid[0] - 960).padStart(9)} ${f1(r.aimed.visual[0] - 960).padStart(8)}`
    + `   box ${r.aimed.box.map((x) => x.toFixed(0)).join(',')} | ${f1(r.err[0]).padStart(6)} ${f1(r.err[1]).padStart(6)}`);
}
const rest = rows.filter((r) => r.t >= P.at + P.move);
const aimedx = rest.map((r) => r.aimed.visual[0] - 960);
const aimedc = rest.map((r) => r.aimed.centroid[0] - 960);
const aimedb = rest.map((r) => (r.aimed.box[0] + r.aimed.box[2]) / 2 - 960);
console.log(`aimed at rest (${rest.length} frames): box centre ${f1(Math.min(...aimedb))}..${f1(Math.max(...aimedb))} px, centroid ${f1(Math.min(...aimedc))}..`
  + `${f1(Math.max(...aimedc))}, visual ${f1(Math.min(...aimedx))}..${f1(Math.max(...aimedx))} (at 2560 x 1440: x 4/3)`);
const worst = Math.max(...rows.map((r) => Math.max(Math.abs(r.err[0]), Math.abs(r.err[1]))));
console.log(`now: worst visual-centre error over all ${rows.length} frames ${worst.toFixed(3)} px; ${ms.toFixed(1)} ms a frame (aimed measure + centring)`);

// the checks
ok(Math.min(...aimedx.map(Math.abs)) > 8, `aimed's logo sits off the centre at rest by more than the gate's 8 px (${f1(Math.min(...aimedx))})`);
ok(aimedx.every((x) => x > 0), 'aimed leans RIGHT at rest (the solid block on the right carries the weight)');
ok(worst < 0.5, `now: the visual centre within 0.5 px of the frame's centre on every frame (${worst.toFixed(3)})`);
ok(rows.every((r) => !r.now.cut), 'now: the logo whole in the frame on every frame');
// the move still reads as one move: the logo's visible width grows smoothly to rest, no jump between frames
const wNow = rows.map((r) => r.now.box[2] - r.now.box[0]);
ok(wNow.slice(1).every((w, i) => Math.abs(w - wNow[i]) < 12), 'now: the visible width changes smoothly (no jump > 12 px between frames)');

// ------------------------------------------------------------------------------------------------------------------------------ Phone3D
// its defaults (device.tsx): landscape, aspect 2, height 0.62, fov 28, yaw/pitch [32, -8] -> [6, -2] over 1.6 s, then a 0.6 deg/s drift
{
  const PH = {aspect: 2, landscape: true, height: 0.62, from: [32, -8], to: [6, -2], move: 1.6, drift: 0.6};
  const pg = C.phoneGeometry(PH.aspect, PH.landscape);
  const fovP = 28;
  const distP = (PH.aspect + 0.07) / PH.height / (2 * Math.tan(rad(fovP / 2)) * (16 / 9));
  const poseP = (t) => {
    const u = prog(t, 0, PH.move);
    return {yaw: lerp(PH.from[0], PH.to[0], u) - Math.max(0, t - PH.move) * PH.drift, pitch: lerp(PH.from[1], PH.to[1], u)};
  };
  const before = [], now = [];
  for (let fr = 0; fr < 5 * FPS; fr += 5) {
    const t = fr / FPS, {yaw, pitch} = poseP(t);
    const parts = pg.parts(yaw, pitch);
    const b = C.silhouette(parts, {pos: [0, 0, distP], target: [0, 0, 0], fov: fovP, near: 0.05, far: 50});   // the camera aimed at the origin
    const c = C.centreOn(parts, (q) => ({pos: [q[0], q[1], q[2] + distP], target: q, fov: fovP, near: 0.05, far: 50}), [960, 540]);
    before.push({t, x: b.visual[0] - 960, y: b.visual[1] - 540});
    now.push({t, err: c.err, cut: c.sil.cut});
  }
  const bx = before.map((r) => r.x);
  console.log(`Phone3D before: its visual centre ${f1(Math.min(...bx))}..${f1(Math.max(...bx))} px left to right over the turn `
    + `(${f1(before[0].x)} at the cut, ${f1(before[before.length - 1].x)} at rest)`);
  const wP = Math.max(...now.map((r) => Math.max(Math.abs(r.err[0]), Math.abs(r.err[1]))));
  console.log(`Phone3D now: worst error ${wP.toFixed(3)} px`);
  ok(wP < 0.5, `Phone3D now: its visual centre within 0.5 px on every frame (${wP.toFixed(3)})`);
  ok(now.every((r) => !r.cut), 'Phone3D now: whole in the frame');
}

// ------------------------------------------------------------------------------------------------------------------------ CaseNumber3D
// its layout (objects.tsx): the case at x -1.55 turned 10 deg, "230" at size 1.05 at x 1.05, baseline 0.02, fov 26, the orbit round
// [0, 0.05, 0] from [-24, 7] to [-7, 3] over 1.8 s (distance 8.4 -> 7.6); the HTML block under the number (the browser measures its
// lines; here two widths: none, and a 1100-px line wider than the 791-px "230") 40 px under the baseline, 196 px tall
const TTF = path.join(PUBLIC, 'kit3d', 'fonts', 'Archivo-ExtraBold.ttf');
if (!fs.existsSync(TTF)) console.log(`CaseNumber3D: skipped (no ${TTF}: the setup puts Archivo ExtraBold there)`);
else {
  const ttf = fs.readFileSync(TTF);
  const font = new C.Font(new C.TTFLoader().parse(ttf.buffer.slice(ttf.byteOffset, ttf.byteOffset + ttf.byteLength)));
  const num = C.glyphGeometries(font, '230', 1.05, 1.05 * 0.16);
  const caseGeo = C.caseGeometry();
  const parts = C.caseNumberParts(caseGeo, -1.55, rad(10), num, 1.05, 0.02);
  const center = [0, 0.05, 0];
  const camB = (t) => {
    const u = prog(t, 0, 1.8);
    return {pos: orbit(center, lerp(8.4, 7.6, u), lerp(-24, -7, u), lerp(7, 3, u)), target: center, fov: 26, near: 0.1, far: 60};
  };
  for (const blockW of [0, 1100]) {
    const before = [], now = [];
    for (let fr = 0; fr < 5 * FPS; fr += 5) {
      const t = fr / FPS;
      const cb = camB(t);
      const extra = (cam) => {
        if (!blockW) return [];
        const q = C.projectPoint(cam, [1.05, 0.02, 0]);
        return [[q[0] - blockW / 2, q[1] + 40, q[0] + blockW / 2, q[1] + 40 + 196]];
      };
      const sb = C.silhouette(parts, cb);
      const pb = C.pointOf(sb, 'box', extra(cb));
      const c = C.centreOn(parts, (q) => ({...cb, pos: [cb.pos[0] + q[0], cb.pos[1] + q[1], cb.pos[2] + q[2]],
        target: [center[0] + q[0], center[1] + q[1], center[2] + q[2]]}), [960, 532], 1920, 1080, 3, 'box', extra);
      before.push({t, x: pb[0] - 960, y: pb[1] - 532});
      now.push({t, err: c.err, cut: c.sil.cut});
    }
    const bx = before.map((r) => r.x);
    const wC = Math.max(...now.map((r) => Math.max(Math.abs(r.err[0]), Math.abs(r.err[1]))));
    console.log(`CaseNumber3D (HTML block ${blockW} px) before: its visible content ${f1(Math.min(...bx))}..${f1(Math.max(...bx))} px left to right `
      + `(${f1(before[before.length - 1].x)} at rest, ${f1(before[before.length - 1].y)} up and down); now: worst error ${wC.toFixed(3)} px`);
    ok(wC < 0.5, `CaseNumber3D (block ${blockW}) now: its visible content within 0.5 px of (960, 532) on every frame (${wC.toFixed(3)})`);
    ok(now.every((r) => !r.cut), `CaseNumber3D (block ${blockW}) now: whole in the frame`);
  }
}

const ji = process.argv.indexOf('--json');
if (ji > 0) {
  const o = process.argv[ji + 1];
  fs.mkdirSync(path.dirname(o), {recursive: true});
  fs.writeFileSync(o, JSON.stringify({shot: 'lopsided test logo', dur, props: P, rows}, null, 0));
  for (const tag of ['aimed', 'now']) {
    fs.writeFileSync(o.replace(/\.json$/, `_${tag}.jsonl`), lines.filter((l) => l.tag === tag).map((l) => l.line).join('\n') + '\n');
  }
  console.log(`wrote ${o} and its _aimed.jsonl / _now.jsonl`);
}
console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
