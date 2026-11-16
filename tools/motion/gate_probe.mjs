// The pre-render gate's probe (tools/pipeline/gate.py runs it, src/gate.tsx is the other half). One bundle, one browser:
//   node gate_probe.mjs <out_dir> <scale> <a-b[:n][,c-d...] | @file> <every> [--png] [--real]
//     frames a..b (and c..d ...: one bundle for all the ranges), every <every>-th, through renderFrames (its pages are reused: renderStill set up a page per frame, ~1 s each)
//     (default) the gate mode: REMOTION_GATE=1, so no video frame is fetched; every Clip/SpeedRamp logs what it shows and <GateLayout/>
//               every visible text and picture's box -> <out_dir>/probe.jsonl (one GATE line each, the frame inside the line);
//               --png keeps each frame's picture (graphics only, the clips hidden) as element-<n>.jpeg for the motion and sync checks
//     --real    normal frames (the clips in) as pictures: black and empty frames
// QA_COMP = the composition, QA_PUBLIC = its lean public dir, GATE_CONC = pages at once (6, at most the CPU cores).
// The bundle holds a junction to the public dir, not a copy, and is deleted when done (lean_bundle.mjs).
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import {leanBundle} from './lean_bundle.mjs';
import {openBrowser, renderFrames, selectComposition} from '@remotion/renderer';
import {PUBLIC} from '../common/paths.mjs';

const [, , out, scale, range, every, ...flags] = process.argv;
const real = flags.includes('--real');
const pics = real || flags.includes('--png');
// ranges: "a-b,c-d" or "@<file>" (the same list in a file: reprobe.py's lists are longer than a Windows command line); a range may carry
// its own stride, "a-b:12" (reprobe.py's sentinel frames: every 12th frame of the film in one call, beside the changed shots)
const spec = range.startsWith('@') ? fs.readFileSync(range.slice(1), 'utf8').trim() : range;
const ranges = spec.split(/[,\s]+/).filter(Boolean).map((r) => {
  const [ab, n] = r.split(':');
  const [a, b] = ab.split('-').map(Number);
  return [a, b, n ? Number(n) : Number(every)];
});
fs.mkdirSync(out, {recursive: true});
const env = real ? {} : {REMOTION_GATE: '1'};
const chromiumOptions = {gl: process.env.QA_GL || 'angle'};   // the GPU by default; QA_GL=swangle for software
// QA_ENTRY: another entry point (reprobe.py's proof renders a copy of src/ with a change in it, never the shared tree)
const lean = await leanBundle({entryPoint: path.resolve(process.env.QA_ENTRY || 'src/index.ts'), publicDir: process.env.QA_PUBLIC || PUBLIC});   // no public-dir copy (lean_bundle.mjs)
const serveUrl = lean.serveUrl;
const browser = await openBrowser('chrome', {chromiumOptions});
const log = fs.createWriteStream(path.join(out, real ? 'real.jsonl' : 'probe.jsonl'));
const t0 = Date.now();
try {
  const composition = await selectComposition({serveUrl, id: process.env.QA_COMP || 'Full', chromiumOptions, envVariables: env, puppeteerInstance: browser});
  let last = 0;
  for (const [a, b, nth] of ranges) {
    if (a > composition.durationInFrames - 1) continue;
    await renderFrames({
      composition, serveUrl, chromiumOptions, envVariables: env, puppeteerInstance: browser, scale: Number(scale),
      frameRange: [a, Math.min(b, composition.durationInFrames - 1)], everyNthFrame: nth,
      concurrency: Math.max(1, Math.min(Number(process.env.GATE_CONC || 6),
        typeof os.availableParallelism === 'function' ? os.availableParallelism() : os.cpus().length)), imageFormat: pics ? 'jpeg' : 'none', ...(pics ? {jpegQuality: 80} : {}),
      outputDir: pics ? out : null, inputProps: {}, logLevel: 'error',   // the GATE lines go to probe.jsonl only, not the log too
      onStart: () => {},
      onBrowserLog: (l) => { if (l.text.startsWith('GATE|')) log.write(l.text.slice(5) + '\n'); },
      onFrameUpdate: (n) => { if (n - last >= 500) { last = n; console.log(`${n} frames, ${((Date.now() - t0) / 1000).toFixed(0)} s`); } },
    });
    console.log(`done: ${a}-${b} every ${nth}, ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
} finally {
  log.end();
  await browser.close({silent: true}).catch(() => {});
  lean.cleanup();
}
