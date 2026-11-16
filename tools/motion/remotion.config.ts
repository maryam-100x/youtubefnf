import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setConcurrency(6);
Config.setOverwriteOutput(true);
// The GPU (angle) by default: about twice as fast per frame as software GL. On a PC whose graphics driver resets under the load (a
// streaming or capture app sharing the GPU fails with it), switch to 'swangle' (software GL) for good; tools/pipeline/pipe.py's GPU guard
// stops a render at the first driver reset. Both paths render the HTML-in-canvas transitions and motion blur correctly.
Config.setChromiumOpenGlRenderer('angle');

// The public dir (the media every composition reads through staticFile) is <media>/motion, outside the repo. The CLI runs this file from
// tools/motion, so the media root is read here the way tools/common/paths.mjs reads it: config/paths.toml's `media = "..."`, else
// STUDIO_MEDIA, else the default. The render tools pass their own lean public dir (lean_bundle.mjs), which wins over this.
const cfg = path.resolve(process.cwd(), '..', '..', 'config', 'paths.toml');
const m = fs.existsSync(cfg) ? fs.readFileSync(cfg, 'utf8').match(/^\s*media\s*=\s*"([^"]*)"/m) : null;
const media0 = (m && m[1]) || process.env.STUDIO_MEDIA || (process.platform === 'win32' ? 'C:/Studio' : '~/Studio');
const media = media0.startsWith('~') ? path.join(os.homedir(), media0.slice(1)) : media0;
Config.setPublicDir(path.join(media, 'motion'));
