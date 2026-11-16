// Many stills of a composition with one bundle (a QA aid: `remotion still` re-bundles every call).
//   node stills.mjs <out_dir> <scale> <frame> [<frame> ...]   (QA_COMP=<composition id>, default Full; QA_PUBLIC=<public dir>, default
//   PUBLIC (tools/common/paths.mjs); QA_ENTRY=<entry file>, default src/index.ts: e.g. a video's own entry renders that video alone, even
//   while Root's bundle throws)
// Writes <out_dir>/f_<frame>.png.
// The bundle lives in the temp folder and is deleted when done (it holds a junction to the public dir, not a copy: lean_bundle.mjs);
// leftover bundles would fill the disk. GPU WebGL via angle (about 2.4x faster than Chrome's software fallback).
import path from 'node:path';
import fs from 'node:fs';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {leanBundle} from './lean_bundle.mjs';
import {PUBLIC} from '../common/paths.mjs';

const [, , out, scale, ...frames] = process.argv;
fs.mkdirSync(out, {recursive: true});
const entryPoint = path.resolve(process.env.QA_ENTRY || 'src/index.ts');
const publicDir = process.env.QA_PUBLIC || PUBLIC;
// the bundle doesn't copy the public dir (lean_bundle.mjs: a junction to it; pixel-identical stills, in a fraction of the time);
// QA_COPY=1 copies as before, and PUBLIC itself is always copied
const lean = await leanBundle({entryPoint, publicDir});
const serveUrl = lean.serveUrl;
// the GPU by default (QA_GL=swangle for software, e.g. when a driver resets under the load)
const chromiumOptions = {gl: process.env.QA_GL || 'angle'};
// one Chrome for every still: renderStill without it launches a Chrome per still, each leaving a profile and an assets folder in the
// temp folder (they pile up into many GB). One Chrome is about twice as fast; the pictures match, though a text line can sit 1 px apart
// (fine for a check still). QA_SHARED_BROWSER=0: a Chrome per still, as before.
const browser = process.env.QA_SHARED_BROWSER === '0' ? undefined : await openBrowser('chrome', {chromiumOptions});
try {
  // QA_VARIANTS (a few looks side by side to pick from, e.g. three accents): a JSON list of {tag, props}; every frame is rendered once
  // per variant with those input props, as f_<frame>_<tag>.png, from the one bundle. Without it: one plain pass.
  const variants = process.env.QA_VARIANTS ? JSON.parse(process.env.QA_VARIANTS) : [{tag: '', props: {}}];
  for (const v of variants) {
    const inputProps = v.props || {};
    // the shell's REMOTION_* variables reach the bundle's process.env (Remotion passes only what envVariables names), e.g.
    // REMOTION_FPS=30, or a video's own switch that lets a full film take stills while one range is still unfinished
    const envVariables = Object.fromEntries(Object.entries(process.env).filter(([k]) => k.startsWith('REMOTION_')));
    const composition = await selectComposition({serveUrl, id: process.env.QA_COMP || 'Full', chromiumOptions, inputProps, envVariables,
      puppeteerInstance: browser});
    for (const f of frames) {
      const file = path.join(out, v.tag ? `f_${f}_${v.tag}.png` : `f_${f}.png`);
      await renderStill({composition, serveUrl, output: file, frame: Number(f), scale: Number(scale), chromiumOptions, inputProps,
        envVariables, puppeteerInstance: browser});
      console.log(file);
    }
  }
} finally {
  if (browser) await browser.close({silent: true}).catch(() => {});
  lean.cleanup();
}
