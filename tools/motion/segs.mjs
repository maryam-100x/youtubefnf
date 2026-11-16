// Patch segments of a composition with one bundle (pipe.py patch runs it; finish --patches lays them over the picture: a version's few
// fixed shots without re-rendering whole chunks). The chunk renders' settings: H.264 CRF 16 slow in MKV, BT.709, the composition at
// <scale> (1440p from 1080p: 1.3333), muted. Writes <out_dir>/seg_<a>-<b>.mkv for each frame range and prints its patch time.
//   node segs.mjs <out_dir> <scale> <a>-<b> [<a>-<b> ...]   (QA_COMP=<composition id>; QA_PUBLIC=<the render's lean public dir>;
//   QA_PROPS=<input props as JSON>, e.g. an option switch read with getInputProps() for numbered samples)
// The bundle holds a junction to the public dir and is deleted when done (lean_bundle.mjs). Nothing else on Remotion while it runs.
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import {leanBundle} from './lean_bundle.mjs';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {PUBLIC} from '../common/paths.mjs';

const CONC = Math.max(1, Math.min(3, typeof os.availableParallelism === 'function' ? os.availableParallelism() : os.cpus().length));

const [, , out, scale, ...ranges] = process.argv;
fs.mkdirSync(out, {recursive: true});
// QA_ENTRY: a video on its own entry (src/<video>_index.ts), as pipe.py's render and gate take it
const lean = await leanBundle({entryPoint: path.resolve(process.env.QA_ENTRY || 'src/index.ts'), publicDir: process.env.QA_PUBLIC || PUBLIC});   // no public-dir copy (lean_bundle.mjs)
const serveUrl = lean.serveUrl;
try {
  const chromiumOptions = {gl: process.env.QA_GL || 'angle'};   // the GPU by default; QA_GL=swangle for software
  const inputProps = JSON.parse(process.env.QA_PROPS || '{}');
  const composition = await selectComposition({serveUrl, id: process.env.QA_COMP || 'Full', chromiumOptions, inputProps});
  for (const r of ranges) {
    const [a, b] = r.split('-').map(Number);
    const file = path.join(out, `seg_${a}-${b}.mkv`);
    await renderMedia({composition, serveUrl, inputProps, codec: 'h264-mkv', outputLocation: file, frameRange: [a, b], crf: 16, x264Preset: 'slow',
      colorSpace: 'bt709', scale: Number(scale), muted: true, chromiumOptions, concurrency: CONC, timeoutInMilliseconds: 120000});
    console.log(`${file}@${(a / composition.fps).toFixed(6)}`);
  }
} finally {
  lean.cleanup();
}
