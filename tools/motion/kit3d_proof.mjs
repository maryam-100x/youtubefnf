// kit3d's proof, one Remotion job (run it under the heavy ticket, standard/3D.md §7):
//   bash with_remotion_lock.sh "kit3d proof" node kit3d_proof.mjs <out_dir> [stills|clips|all] [comp,comp...]
// 1. stills at 2560 x 1440 (--scale 4/3, as pipe.py renders long videos): each demo at its first frame, mid-move and at rest
// 2. clips: each demo whole, h264 CRF 16 at 1440p, timed: s/frame at concurrency 1 (the true cost of a frame) on its whole length,
//    then the wall time at the house concurrency (6, or the CPU cores when fewer) for the same frames
// One bundle (lean: the public dir TMP/pub_kit3d behind a junction, kit3d_assets.py link), one Chrome, GL angle (the GPU, remotion.config.ts).
// Writes <out>/proof.json and prints a table.
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {leanBundle} from './lean_bundle.mjs';
import {TMP} from '../common/paths.mjs';

const out = path.resolve(process.argv[2] || 'out/kit3d_proof');
const what = process.argv[3] || 'all';
const only = process.argv[4] ? process.argv[4].split(',') : null;
fs.mkdirSync(out, {recursive: true});
const SCALE = 4 / 3;
// seconds into each demo for its stills: the first frame (the cut), mid-move, at rest
const STILLS = {
  K3dEmblem: [0, 0.7, 1.4, 4.0],
  K3dParallaxA: [0, 2.5, 4.9],
  K3dParallaxB: [0, 2.5, 4.9],
  K3dGlobe: [0, 1.5, 2.7, 4.2, 5.8],
  K3dPhone: [0, 0.8, 3.5],
  K3dCaseNumber: [0, 0.6, 1.0, 3.0],
};
const comps = Object.keys(STILLS).filter((c) => !only || only.includes(c));

const lean = await leanBundle({entryPoint: path.resolve('src/kit3d_index.ts'), publicDir: path.join(TMP, 'pub_kit3d')});
const chromiumOptions = {gl: process.env.QA_GL || 'angle'};
const browser = await openBrowser('chrome', {chromiumOptions});
const reportFile = path.join(out, 'proof.json');
const report = fs.existsSync(reportFile) ? JSON.parse(fs.readFileSync(reportFile, 'utf8')) : {stills: [], clips: []};
report.started = new Date().toISOString();
const keep = (arr, comp) => arr.filter((r) => r.comp !== comp);
try {
  for (const id of comps) {
    const comp = await selectComposition({serveUrl: lean.serveUrl, id, chromiumOptions, puppeteerInstance: browser});
    if (what === 'stills' || what === 'all') {
      report.stills = keep(report.stills, id);
      for (const s of STILLS[id]) {
        const frame = Math.min(comp.durationInFrames - 1, Math.round(s * comp.fps));
        const file = path.join(out, 'stills', `${id}_${String(frame).padStart(4, '0')}.png`);
        fs.mkdirSync(path.dirname(file), {recursive: true});
        const t0 = Date.now();
        await renderStill({composition: comp, serveUrl: lean.serveUrl, output: file, frame, scale: SCALE, chromiumOptions,
          puppeteerInstance: browser, timeoutInMilliseconds: 120000});
        const ms = Date.now() - t0;
        report.stills.push({comp: id, frame, file, ms});
        console.log(`still ${id} f${frame}: ${ms} ms -> ${file}`);
      }
    }
    if (what === 'clips' || what === 'all') {
      report.clips = keep(report.clips, id);
      const file = path.join(out, 'clips', `${id}.mp4`);
      fs.mkdirSync(path.dirname(file), {recursive: true});
      const row = {comp: id, frames: comp.durationInFrames, file};
      const HOUSE = Math.max(1, Math.min(6, typeof os.availableParallelism === 'function' ? os.availableParallelism() : os.cpus().length));
      for (const conc of [...new Set([1, HOUSE])]) {
        const t0 = Date.now();
        await renderMedia({composition: comp, serveUrl: lean.serveUrl, codec: 'h264', crf: 16, x264Preset: 'slow', colorSpace: 'bt709',
          outputLocation: conc === HOUSE ? file : path.join(out, 'clips', `${id}_c1.mp4`), scale: SCALE, chromiumOptions, puppeteerInstance: browser,
          concurrency: conc, muted: true, timeoutInMilliseconds: 120000, imageFormat: 'jpeg', jpegQuality: 92, overwrite: true});
        const s = (Date.now() - t0) / 1000;
        row[`wall_c${conc}_s`] = Math.round(s * 10) / 10;
        row[`s_per_frame_c${conc}`] = Math.round((s / comp.durationInFrames) * 1000) / 1000;
        console.log(`clip ${id} concurrency ${conc}: ${s.toFixed(1)} s for ${comp.durationInFrames} frames = ${(s / comp.durationInFrames).toFixed(3)} s/frame`);
      }
      fs.rmSync(path.join(out, 'clips', `${id}_c1.mp4`), {force: true});
      report.clips.push(row);
    }
    fs.writeFileSync(reportFile, JSON.stringify(report, null, 1));
  }
} finally {
  await browser.close({silent: true}).catch(() => {});
  lean.cleanup();
  report.finished = new Date().toISOString();
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 1));
}
