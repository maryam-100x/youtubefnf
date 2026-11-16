// The film's picture in parts, one browser for all of them (tools/pipeline/pipe.py render runs it).
//   node render_parts.mjs <job.json>
// job.json: {serveUrl (a ready bundle: lean_bundle.mjs make), comp, scale, gl, concurrency, crf, preset, imageFormat, jpegQuality,
//            timeoutMs, cacheBytes?, threads?, parallel? ("auto" | "force" | "off"), info? (true: print the composition and stop),
//            parts: [{i, f0, f1, file}]}
// Prints one machine line per event (pipe.py reads them; the stall watchdog reads the log growing):
//   COMP {"durationInFrames", "fps", "width", "height"}       the composition itself: the frame count comes from here, never a guess
//   ENC {"parallel": bool, "freeMemory", "estimated"}         whether Remotion encodes while it renders (see `parallel`)
//   PROGRESS <i> <rendered>/<frames> <encoded> <s>           every ~200 frames of a part
//   DONE <i> <frames> <seconds>                             a part finished: its file is in place (renamed from <file>.part.mkv)
//   FAIL <i> <message>                                      a part failed; the script stops (exit 3): pipe.py decides the retry
// A part renders to <file>.part.mkv and is renamed only when complete, so a file at <file> is always whole. Remotion can't resume a
// half-rendered output (no resume, no frame retry), so the parts are kept small: a failure costs one part, never the run.
// `parallel`: Remotion 4.0.532 encodes while it renders only when the free memory minus 1 GB per megapixel of output stays over 2 GB
// (renderer/dist/prestitcher-memory-usage.js); at 2560x1440 that asks 5.7 GB free, which a 16-GB PC with other apps open rarely has, so
// every part would render all its frames to disk first and encode after. Remotion removed that check in 4.0.534 ("20-35% longer at
// 1080p" sequential). "force" applies 4.0.534's decision to this version: encode while rendering.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

// the renderer's CommonJS build (not its ESM bundle), so its own modules are shared objects this script can read and, with
// parallel: "force", adjust
const require = createRequire(import.meta.url);
const {openBrowser, renderMedia, selectComposition} = require('@remotion/renderer');
const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const say = (s) => process.stdout.write(s + '\n');

const pre = require(path.join(path.dirname(require.resolve('@remotion/renderer')), 'prestitcher-memory-usage.js'));
if (job.parallel === 'force') {
  const orig = pre.shouldUseParallelEncoding;
  pre.shouldUseParallelEncoding = (o) => ({...orig(o), hasEnoughMemory: true});
}

const chromiumOptions = {gl: job.gl || 'angle'};
const browser = await openBrowser('chrome', {chromiumOptions});
let code = 0;
try {
  const composition = await selectComposition({serveUrl: job.serveUrl, id: job.comp, chromiumOptions, puppeteerInstance: browser, inputProps: {}});
  say(`COMP ${JSON.stringify({durationInFrames: composition.durationInFrames, fps: composition.fps, width: composition.width, height: composition.height})}`);
  if (!job.info) {
    const w = Math.round(composition.width * job.scale), h = Math.round(composition.height * job.scale);
    const d = pre.shouldUseParallelEncoding({width: w, height: h, logLevel: 'error'});
    say(`ENC ${JSON.stringify({parallel: job.parallel !== 'off' && (job.parallel === 'force' || d.hasEnoughMemory), freeMemory: d.freeMemory, estimated: d.estimatedUsage})}`);
    for (const p of job.parts) {
      const tmp = `${p.file}.part.mkv`;
      fs.rmSync(tmp, {force: true});
      const t0 = Date.now();
      let last = -1;
      try {
        await renderMedia({
          composition, serveUrl: job.serveUrl, inputProps: {}, codec: 'h264-mkv', outputLocation: tmp, frameRange: [p.f0, p.f1],
          crf: job.crf, x264Preset: job.preset, colorSpace: 'bt709', scale: job.scale, muted: true, chromiumOptions,
          concurrency: job.concurrency, timeoutInMilliseconds: job.timeoutMs || 120000, puppeteerInstance: browser,
          imageFormat: job.imageFormat || 'jpeg', ...(job.imageFormat === 'png' ? {} : {jpegQuality: job.jpegQuality || 92}),
          ...(job.cacheBytes ? {offthreadVideoCacheSizeInBytes: job.cacheBytes} : {}),
          ...(job.threads ? {offthreadVideoThreads: job.threads} : {}),
          ...(job.parallel === 'off' ? {disallowParallelEncoding: true} : {}),
          logLevel: 'warn',
          onProgress: ({renderedFrames, encodedFrames}) => {
            if (renderedFrames - last >= 200 || renderedFrames === p.f1 - p.f0 + 1) {
              last = renderedFrames;
              say(`PROGRESS ${p.i} ${renderedFrames}/${p.f1 - p.f0 + 1} ${encodedFrames} ${((Date.now() - t0) / 1000).toFixed(0)}`);
            }
          },
        });
        fs.renameSync(tmp, p.file);
        say(`DONE ${p.i} ${p.f1 - p.f0 + 1} ${((Date.now() - t0) / 1000).toFixed(1)}`);
      } catch (e) {
        say(`FAIL ${p.i} ${String(e && e.message ? e.message : e).replace(/\s+/g, ' ').slice(0, 1500)}`);
        fs.rmSync(tmp, {force: true});
        code = 3;
        break;
      }
    }
  }
} finally {
  await browser.close({silent: true}).catch(() => {});
}
process.exit(code);
