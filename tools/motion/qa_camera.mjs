// Every card's camera in a composition, read from its own code frame by frame: no render, seconds for a whole film. A card whose camera
// zooms in, pauses, then zooms in again reads as a stutter; a card is meant to make ONE move. Each shot whose element holds a card
// (PageStage, Still) is called as a plain function once per frame, with remotion's useCurrentFrame read from a global (an esbuild shim),
// and the transform of its camera layer (the first style with a scale) is read: scale and translate per frame, then the screen speed of
// a grid over the frame's middle 80% (2D: a page's fixed tilt is left out). A card is ONE MOVE when that speed, smoothed over 5 frames,
// has one hump; a second hump of at least a quarter of the top speed after the speed fell under 40% of the first hump's peak is TWO MOVES
// (the same rule as qa_zoom.py, which measures a render). tools/pipeline/qa_gate.py runs it.
//   node tools/motion/qa_camera.mjs src/<video>/<Video>.tsx [--json out/cards.json]
// The module must export SHOTS ({at, el(dur)}[]) and one <NAME>_SECONDS. --json writes every card as a window for qa_zoom.py
// ({name, t0, t1, verdict}: its first and last frame on the timeline), to measure the same cards on the render.
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import * as esbuild from 'esbuild';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const comp = path.resolve(args[0]);
const jsonOut = args.includes('--json') ? path.resolve(args[args.indexOf('--json') + 1]) : null;
const real = createRequire(path.join(HERE, 'package.json')).resolve('remotion');

const entry = `
import * as M from ${JSON.stringify(comp.replace(/\\/g, '/'))};
const FPS = Number(process.env.REMOTION_FPS) || 60;
const SHOTS = M.SHOTS;
const SECONDS = Object.entries(M).find(([k]) => /_SECONDS$/.test(k))[1];
const CARDS = new Set(['PageStage', 'Still']);
const nm = (t) => (typeof t === 'string' ? t : (t && (t.displayName || t.name)) || '').replace(/\\d+$/, '');
const find = (node, ok) => {
  if (!node || typeof node !== 'object') return null;
  if (Array.isArray(node)) { for (const n of node) { const r = find(n, ok); if (r) return r; } return null; }
  if (ok(node)) return node;
  return find(node.props && node.props.children, ok);
};
const isCard = (n) => n.type && CARDS.has(nm(n.type));
const hasCam = (n) => n.props && n.props.style && typeof n.props.style.transform === 'string' && /scale[(]/.test(n.props.style.transform);
const num = (tr, fn) => { const m = tr.match(new RegExp(fn + '[(]([-0-9.e+]+)')); return m ? parseFloat(m[1]) : 0; };
const gx = [], gy = [];
for (let a = 0; a < 9; a++) for (let b = 0; b < 7; b++) { gx.push(-768 + (1536 * a) / 8); gy.push(-432 + (864 * b) / 6); }
const out = [];
SHOTS.forEach((s, i) => {
  const end = i + 1 < SHOTS.length ? SHOTS[i + 1].at : SECONDS;
  let el = find(s.el(end - s.at), isCard);
  if (!el) return;
  const kind = nm(el.type);
  const name = String(el.props.src || '').split('/').pop();
  const a = Math.round(s.at * FPS), n = Math.round(end * FPS) - a;
  const cam = [];
  for (let fr = 0; fr < n; fr++) {
    globalThis.__FRAME = fr;
    const c = find(el.type(el.props), hasCam);
    const tr = c ? c.props.style.transform : '';
    cam.push([num(tr, 'translateX'), num(tr, 'translateY'), num(tr, 'scale') || 1]);
  }
  const speed = cam.map((r, k) => {
    if (k === 0) return 0;
    const p = cam[k - 1];
    let sum = 0;
    for (let j = 0; j < gx.length; j++) sum += Math.hypot(r[0] - p[0] + (r[2] - p[2]) * gx[j], r[1] - p[1] + (r[2] - p[2]) * gy[j]);
    return (sum / gx.length) * FPS;
  });
  if (speed.length > 1) speed[0] = speed[1];
  out.push({i, at: s.at, a, n, kind, name, fps: FPS, s0: cam[0][2], s1: cam[cam.length - 1][2], speed});
});
module.exports = out;
`;

// only the bare 'remotion' is swapped (its subpaths, e.g. remotion/no-react, stay real); the shim reads the frame from a global
const shim = {name: 'frame-shim', setup(b) {
  b.onResolve({filter: /^remotion$/}, () => ({path: 'remotion-shim', namespace: 'qa'}));
  b.onLoad({filter: /.*/, namespace: 'qa'}, () => ({loader: 'js', resolveDir: HERE, contents:
    `const r = require(${JSON.stringify(real)});
     module.exports = {...r, useCurrentFrame: () => globalThis.__FRAME || 0,
       useVideoConfig: () => ({fps: Number(process.env.REMOTION_FPS) || 60, width: 1920, height: 1080, durationInFrames: 1e7, id: 'qa', defaultProps: {}, props: {}})};`}));
}};
fs.mkdirSync(path.join(HERE, 'out'), {recursive: true});
const bundle = path.join(HERE, 'out', 'qa_camera_bundle.cjs');
await esbuild.build({stdin: {contents: entry, resolveDir: HERE, loader: 'js'}, bundle: true, platform: 'node', outfile: bundle, loader: {'.json': 'json'},
  logLevel: 'error', plugins: [shim], nodePaths: [path.join(HERE, 'node_modules')]});
const cards = createRequire(import.meta.url)(bundle);

// the hump rule (qa_zoom.py's): the speed smoothed over 5 frames; a hump is a peak of at least a quarter of the top speed, and two humps
// are two such peaks with a trough between them under 40% of each (a speed that only falls after its peak is one hump)
const humps = (speed) => {
  const s = speed.map((_, k) => { let t = 0; for (let j = k - 2; j <= k + 2; j++) t += speed[Math.min(speed.length - 1, Math.max(0, j))]; return t / 5; });
  const top = Math.max(...s);
  if (top < 1) return [];
  const hs = [];
  let up = false, pk = 0, pi = 0, low = 0;
  s.forEach((v, k) => {
    if (up) {
      if (v > pk) { pk = v; pi = k; }
      if (v < 0.4 * pk) { hs.push([pi, pk]); up = false; low = v; }
    } else {
      low = Math.min(low, v);
      if (v >= 0.25 * top && low <= 0.4 * v) { up = true; pk = v; pi = k; }
    }
  });
  if (up) hs.push([pi, pk]);
  return hs;
};
const mmss = (t) => `${Math.floor(t / 60)}:${(t % 60).toFixed(2).padStart(5, '0')}`;
const kinds = {};
let two = 0;
const wins = [];
for (const c of cards) {
  const h = humps(c.speed);
  const v = h.length >= 2 ? 'TWO MOVES' : h.length ? 'one move' : 'still';
  kinds[c.kind] = (kinds[c.kind] || 0) + 1;
  if (v === 'TWO MOVES') {
    two++;
    console.log(`TWO MOVES ${mmss(c.at)} shot ${c.i} ${c.kind} ${c.name}: humps at ${h.map(([k, p]) => `${(k / c.fps).toFixed(2)} s (${p.toFixed(0)} px/s)`).join(', ')}`);
  }
  wins.push({name: `${mmss(c.at)} #${c.i} ${c.kind} ${c.name}`, t0: c.a / c.fps, t1: (c.a + c.n - 1) / c.fps, verdict: v});
}
console.log(`${path.basename(comp)}: ${cards.length} cards (${Object.entries(kinds).map(([k, n]) => `${k} ${n}`).join(', ')}): ${cards.length - two} one move, ${two} two moves`);
if (jsonOut) fs.writeFileSync(jsonOut, JSON.stringify(wins, null, 1));
fs.rmSync(bundle, {force: true});
process.exitCode = two ? 1 : 0;
