// kit3's pure math, tested in node (no browser, no Remotion job): node src/kit3/test/layout.test.mjs (from tools/motion).
// It compiles layout.ts with esbuild (in node_modules) and checks every placement rule the components rely on, on measured cases.
import {buildSync} from 'esbuild';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(os.tmpdir(), `kit3_layout_${process.pid}.mjs`);
buildSync({entryPoints: [path.join(here, '..', 'layout.ts')], outfile: out, format: 'esm', bundle: true, platform: 'node', logLevel: 'error'});
const L = await import(pathToFileURL(out).href);
fs.unlinkSync(out);

let pass = 0, fail = 0;
const ok = (cond, what) => {
  if (cond) pass++;
  else {
    fail++;
    console.log(`FAIL ${what}`);
  }
};
const near = (a, b, tol, what) => ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b} (tol ${tol})`);
const throws = (fn, re, what) => {
  try {
    fn();
    ok(false, `${what}: did not throw`);
  } catch (e) {
    ok(re.test(String(e.message)), `${what}: threw "${e.message}"`);
  }
};

// ------------------------------------------------------------------------------------------------------------------------------ rows
{
  // three products at one height; the name of the narrow one much wider than its figure
  const items = [{vw: 4005, vh: 2383, nameW: 330}, {vw: 3912, vh: 2656, nameW: 330}, {vw: 1928, vh: 3425, nameW: 330}];
  const r = L.rowLayout(items, {h: 420, gap: 64, cx: 960, maxW: 1680});
  const right = r.left.map((x, i) => x + r.width[i]);
  const gaps = [r.left[1] - right[0], r.left[2] - right[1]];
  near(gaps[0], gaps[1], 0.01, 'product row: equal gaps between visible figures');
  // the names (centred under their figures) keep 24 px apart
  const nameL = r.left.map((x, i) => x + r.width[i] / 2 - 165), nameR = nameL.map((x) => x + 330);
  ok(nameL[1] - nameR[0] >= 23.99 && nameL[2] - nameR[1] >= 23.99, `product row: names apart (${(nameL[1] - nameR[0]).toFixed(1)}, ${(nameL[2] - nameR[1]).toFixed(1)})`);
  // the whole visible content (figures and names) centred on 960
  const lo = Math.min(r.left[0], nameL[0]), hi = Math.max(right[2], nameR[2]);
  near((lo + hi) / 2, 960, 0.01, 'product row: visible content centred');
  ok(hi - lo <= 1680.5, 'product row: inside the content box');
}
{
  // a row too wide shrinks as a whole and stays centred with equal gaps
  const items = Array.from({length: 6}, (_, i) => ({vw: 1000 + 200 * i, vh: 1000}));
  const r = L.rowLayout(items, {h: 500, gap: 64, cx: 960, maxW: 1680});
  ok(r.fit < 1, 'wide row: shrunk');
  const right = r.left.map((x, i) => x + r.width[i]);
  near(r.extent[1] - r.extent[0], 1680, 0.5, 'wide row: fits 1680');
  near((r.left[0] + right[5]) / 2, 960, 0.01, 'wide row: centred');
  const gaps = r.left.slice(1).map((x, i) => x - right[i]);
  near(Math.max(...gaps) - Math.min(...gaps), 0, 0.01, 'wide row: equal gaps');
}
{
  // a capped wide logo (LogosLand) and a size factor
  const r = L.rowLayout([{vw: 2400, vh: 600, maxW: 640}, {vw: 652, vh: 562}], {h: 280, gap: 96, cx: 960, maxW: 1680});
  near(r.width[0], 640, 0.01, 'logo capped at 640 wide');
  near(r.height[1], 280, 0.01, 'logo at row height');
  throws(() => L.rowLayout([{vw: 100, vh: 100, nameW: 1700}], {h: 300, gap: 64, cx: 960, maxW: 1680}), /cannot fit/, 'row: a name wider than the box is refused');
}
{
  // a LONE logo is centred to the eye: a 4K logo face (4096 x 3110, every pixel visible in x) whose centre of mass sits 373 px (9.1% of
  // its width) right of its box's middle (measured with the gate's alpha reading); box-centred it reads too far right
  const logo = {vw: 4096, vh: 3110, wdx: 373.1, maxW: 640};
  const r = L.rowLayout([logo], {h: 280, gap: 96, cx: 960, maxW: 1680});
  const s = r.scale[0], boxMid = r.left[0] + r.width[0] / 2, weight = boxMid + logo.wdx * s;
  near((boxMid + weight) / 2, 960, 0.01, 'lone logo: halfway between its box and its weight on the centre');
  ok(boxMid < 960 && weight > 960, `lone logo: its box left of the centre, its weight right (${boxMid.toFixed(1)}, ${weight.toFixed(1)})`);
  // the same logo in a row of two keeps the row's own rule (visible content centred, equal gaps): wdx is not applied
  const two = L.rowLayout([logo, {vw: 652, vh: 562}], {h: 280, gap: 96, cx: 960, maxW: 1680});
  near((two.left[0] + two.left[1] + two.width[1]) / 2, 960, 0.01, 'row of two: visible content centred, weight ignored');
  // a symmetric lone logo doesn't move
  const sym = L.rowLayout([{vw: 1000, vh: 500, wdx: 0}], {h: 280, gap: 96, cx: 960, maxW: 1680});
  near(sym.left[0] + sym.width[0] / 2, 960, 0.01, 'lone symmetric logo: box centred');
  // a wide lockup (988 x 214 visible, 4.6:1, its weight 9.4% of its width left of its box's middle) stays box-centred (the check lists
  // it to look at, never blocks it)
  const lockup = L.rowLayout([{vw: 988, vh: 214, wdx: -92.6, maxW: 640}], {h: 280, gap: 96, cx: 960, maxW: 1680});
  near(lockup.left[0] + lockup.width[0] / 2, 960, 0.01, 'lone wide lockup: box centred');
}

// ------------------------------------------------------------------------------------------------------------------------- ink snap
const paint = (w, h, rects, paper = [248, 248, 248], ink = [20, 20, 20]) => {
  const d = new Uint8ClampedArray(w * h * 4);
  for (let i = 0; i < w * h; i++) d.set([...paper, 255], i * 4);
  for (const [x, y, rw, rh] of rects) for (let yy = y; yy < y + rh; yy++) for (let xx = x; xx < x + rw; xx++) d.set([...ink, 255], (yy * w + xx) * 4);
  return d;
};
{
  // a line box 60 px tall with the word's ink in rows 18-44, a colon 3 px after it, a word space, the next word at x 140
  const w = 220, h = 80;
  const data = paint(w, h, [[20, 18, 80, 27], [103, 26, 4, 18], [140, 18, 60, 27]]);
  const paper = L.paperOf(data, 1);
  near(paper[0], 248, 8, 'paper found');
  const r = L.inkSnap({data, rx: 0, ry: 0, rw: w, rh: h}, [12, 10, 88, 60], paper);
  ok(r && r[0] === 20 && r[0] + r[2] === 107, `snap: the run plus its colon, not the next word (${r})`);
  ok(r && r[1] === 18 && r[1] + r[3] === 45, `snap: the blank over and under trimmed (${r})`);
  ok(L.inkSnap({data, rx: 0, ry: 0, rw: w, rh: h}, [110, 50, 25, 25], paper) === null, 'snap: a box on blank space is null');
  // dark page, light text, a descender below the box (a too-tight box is grown to the ink that touches it)
  const d2 = paint(w, h, [[30, 20, 70, 22], [60, 42, 6, 10]], [10, 10, 10], [235, 235, 235]);
  const r2 = L.inkSnap({data: d2, rx: 0, ry: 0, rw: w, rh: h}, [28, 18, 74, 26], L.paperOf(d2, 1));
  ok(r2 && r2[1] + r2[3] === 52, `snap: the descender kept (${r2})`);
  ok(L.isDark(L.paperOf(d2, 1)) && !L.isDark(paper), 'light and dark pages told apart');
  // a tight headline: line 1's "p" descender reaches into line 2's word box; line 2's i-dot sits over its letters
  const d3 = paint(240, 130, [[20, 0, 120, 40], [60, 40, 10, 25], [20, 70, 160, 40], [100, 58, 6, 6]], [36, 36, 36], [240, 240, 240]);
  const r3 = L.inkSnap({data: d3, rx: 0, ry: 0, rw: 240, rh: 130}, [15, 55, 170, 60], L.paperOf(d3, 1));
  ok(r3 && r3.join() === '20,58,160,52', `snap: the line above's descender left out, the i-dot kept (${r3})`);
}

// ------------------------------------------------------------------------------------------------------------------------- the guards
{
  // measured cases (shares measured on real page captures)
  const vAlone = L.markVerdict(3, 560 * 130, 3377, [{at: 0.08, ink: [254, 86, 262, 33], inkCount: 2621, area: 262 * 33}]);
  ok(vAlone.some((s) => /needs no mark/.test(s)), `a name alone in its crop: refused (${vAlone})`);
  const vHalf = L.markVerdict(3, 1050 * 348, 67131, [{at: 1.2, ink: [73, 181, 796, 104], inkCount: 33903, area: 796 * 104}]);
  ok(vHalf.length === 0, `a headline, half of it lit: kept (${vHalf})`);
  const vThree = L.markVerdict(3, 1080 * 245, 33616, [2291, 10650, 2078].map((n) => ({at: 1, ink: [0, 0, 10, 10], inkCount: n, area: 100})));
  ok(vThree.length === 0, `a press page's three lit lines: kept (${vThree})`);
  const tile = L.markVerdict(3, 300 * 200, 9000, [{at: 1, ink: [10, 10, 280, 180], inkCount: 5000, area: 280 * 180}]);
  ok(tile.some((s) => /covers/.test(s)), 'a tile crop with the tile boxed: refused');
  ok(L.markVerdict(3, 1e5, 1e4, [{at: 2.4, ink: [0, 0, 10, 10], inkCount: 10, area: 100}]).some((s) => /MARK_LATE/.test(s)), 'a light in the last 0.6 s: refused');
  ok(L.markVerdict(3, 1e5, 1e4, [{at: 1, ink: null, inkCount: 0, area: 0}]).some((s) => /no ink/.test(s)), 'a box on nothing: refused');
  ok(L.markVerdict(3, 1e5, 1e4, [0.35, 0.3].map((f) => ({at: 1, ink: [0, 0, 10, 10], inkCount: 1e4 * f, area: 100}))).some((s) => /together/.test(s)),
    'two marks lighting 65% of the text: refused');
}

// ------------------------------------------------------------------------------------------------------------------- mark geometry
{
  const ink = [100.3, 50.7, 200.2, 40.1], crop = [10, 20, 600, 300], k = 1.37;
  const [x, y, w, h] = L.markRect(ink, crop, k, 8);
  const ix0 = (ink[0] - crop[0]) * k, iy0 = (ink[1] - crop[1]) * k, ix1 = ix0 + ink[2] * k, iy1 = iy0 + ink[3] * k;
  const gaps = [ix0 - x, iy0 - y, x + w - ix1, y + h - iy1];
  ok(gaps.every((g) => g >= 8 && g < 9), `mark: an even 8-px pad on whole pixels (${gaps.map((g) => g.toFixed(2))})`);
  ok([x, y, w, h].every(Number.isInteger), 'mark: edges on whole pixels');
  // a title starts at the capture's x 3, the crop at x 0: the crop grows left so the padded box stays whole
  const c2 = L.expandCrop([0, 170, 1150, 330], [[3, 427, 681, 44]], 1.4, 8, 8);
  ok(c2[0] < 0 && (3 - c2[0]) * 1.4 >= 16, `crop grown left past the capture (${c2})`);
  const c3 = L.expandCrop([0, 0, 1000, 500], [[400, 200, 100, 40]], 1.4, 8, 8);
  ok(c3.join() === '0,0,1000,500', 'a mark well inside: the crop unchanged');
}

// ------------------------------------------------------------------------------------------------------------------------- timeline
{
  // Oct 31, Dec 16, Dec 31 (days 0, 46, 61) between x 300 and 1620, labels ~330 px: Dec 31 would touch Dec 16 -> above
  const lay = L.timelineLayout([0, 46, 61], [300, 330, 330], 300, 1620, 120, 1800);
  ok(lay[0].side === 'below' && lay[1].side === 'below' && lay[2].side === 'above', `timeline: the close label goes above (${lay.map((p) => p.side)})`);
  ok(lay[2].left + 330 <= 1800, 'timeline: the last label inside the content box');
  throws(() => L.timelineLayout([0, 1, 2, 200], [400, 400, 400, 300], 300, 1620, 120, 1800), /both sides/, 'timeline: three labels in one spot refused');
}

// ------------------------------------------------------------------------------------------------------------------------ typed keys
{
  const k = L.fitKeys(L.keysAcross(17, 0.4, 1.9), 2.0);
  ok(k[k.length - 1] <= 1.7 + 1e-9 && k[0] === 0.4, `typed line: whole 0.3 s before the cut (${k[k.length - 1]})`);
  ok(L.fitKeys([0.2, 0.5], 2).join() === '0.2,0.5', 'typed line: keys in time untouched');
}

console.log(`kit3 layout: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
