// kit3's proof, one Remotion job (run it under the heavy ticket):
//   bash with_remotion_lock.sh "kit3 proof" node kit3_proof.mjs <out_dir>
// 1. the demo's stills (src/kit3/Kit3Demo.tsx) at full size, f_<frame>.png, for kit3_check.py (marks on their ink, rows centred) and the eye
// 2. every refusal case (REFUSALS in Kit3Demo.tsx) rendered once: each must FAIL with its reason; a case that renders is a broken guard
// One bundle (lean: the public dir TMP/pub_kit3 behind a junction, kit3_demo_assets.py), one Chrome. Writes proof.json.
import path from 'node:path';
import fs from 'node:fs';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';
import {leanBundle} from './lean_bundle.mjs';
import {TMP} from '../common/paths.mjs';

const out = path.resolve(process.argv[2] || 'out/kit3_proof');
fs.mkdirSync(out, {recursive: true});
// the stills: each section at rest (every mark lit, every row landed), plus some mid-move frames for the eye
export const FRAMES = [60, 120, 174, 330, 354, 564, 744, 792, 954, 980, 1000, 1040, 1056, 1086, 1266, 1446, 1626, 1806, 1962, 2040, 2172, 2382, 2430, 2502,
  2652, 2802];
const REFUSE = ['redundant', 'nothing', 'late', 'read_all_lit', 'read_overflow', 'read_lit_missing', 'clip_unmeasured', 'frame_mark_huge',
  'still_upscale', 'number_alone', 'number_unit', 'row_too_wide'];
const EXPECT = {redundant: 'needs no mark', nothing: 'no ink under its box', late: 'MARK_LATE', read_all_lit: 'show it plain',
  read_overflow: 'break it', read_lit_missing: 'not on the card', clip_unmeasured: 'clipdurs', frame_mark_huge: 'nothing to pick it out from',
  still_upscale: 'never upscaled', number_alone: 'show the thing itself', number_unit: 'unit and its subject', row_too_wide: 'cannot fit'};

const lean = await leanBundle({entryPoint: path.resolve('src/kit3_index.ts'), publicDir: path.join(TMP, 'pub_kit3')});
const chromiumOptions = {gl: process.env.QA_GL || 'angle'};
const browser = await openBrowser('chrome', {chromiumOptions});
const report = {stills: [], refusals: [], started: new Date().toISOString()};
try {
  const demo = await selectComposition({serveUrl: lean.serveUrl, id: 'Kit3Demo', chromiumOptions, puppeteerInstance: browser});
  for (const fr of (process.env.KIT3_FRAMES ? process.env.KIT3_FRAMES.split(',').map(Number) : FRAMES)) {
    const file = path.join(out, `f_${fr}.png`);
    const t0 = Date.now();
    await renderStill({composition: demo, serveUrl: lean.serveUrl, output: file, frame: fr, scale: 1, chromiumOptions, puppeteerInstance: browser});
    report.stills.push({frame: fr, file, ms: Date.now() - t0});
    console.log(file);
  }
  if (process.env.KIT3_SKIP_REFUSALS !== '1') {
    for (const which of REFUSE) {
      const inputProps = {which};
      const comp = await selectComposition({serveUrl: lean.serveUrl, id: 'Kit3Refuse', chromiumOptions, inputProps, puppeteerInstance: browser});
      let err = '';
      try {
        await renderStill({composition: comp, serveUrl: lean.serveUrl, output: path.join(out, `refuse_${which}.png`), frame: 30, scale: 0.25,
          chromiumOptions, inputProps, puppeteerInstance: browser, timeoutInMilliseconds: 60000});
      } catch (e) {
        err = String(e && e.message ? e.message : e).split('\n')[0];
      }
      const ok = !!err && err.includes(EXPECT[which]);
      report.refusals.push({which, refused: !!err, ok, expect: EXPECT[which], error: err.slice(0, 300)});
      console.log(`${ok ? 'REFUSED' : 'BROKEN '} ${which}: ${err.slice(0, 200) || '(rendered: the guard did not fire)'}`);
    }
  }
} finally {
  await browser.close({silent: true}).catch(() => {});
  lean.cleanup();
  report.finished = new Date().toISOString();
  fs.writeFileSync(path.join(out, 'proof.json'), JSON.stringify(report, null, 1));
}
