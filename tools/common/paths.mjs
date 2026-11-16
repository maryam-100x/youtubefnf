// paths.mjs: the same places as tools/common/paths.py, for the Node scripts (render, stills, probe, page captures).
//   import {REPO, MEDIA, PUBLIC, TMP, VIDEOS} from '../common/paths.mjs';
// MEDIA comes from config/paths.toml (the `media = "..."` line), else the default paths.py uses.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
export const REPO = path.resolve(here, '..', '..');
const cfgFile = path.join(REPO, 'config', 'paths.toml');
const cfg = {};
if (fs.existsSync(cfgFile)) {
  for (const line of fs.readFileSync(cfgFile, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([a-z_]+)\s*=\s*"([^"]*)"/);
    if (m) cfg[m[1]] = m[2];
  }
}
const win = process.platform === 'win32';
const expand = (p) => (p.startsWith('~') ? path.join(os.homedir(), p.slice(1)) : p);
export const MEDIA = expand(cfg.media || process.env.STUDIO_MEDIA || (win ? 'C:/Studio' : '~/Studio'));
export const PUBLIC = path.join(MEDIA, 'motion');
export const VIDEOS = path.join(MEDIA, 'videos');
export const TMP = path.join(MEDIA, 'tmp');
export const MOTION = path.join(REPO, 'tools', 'motion');
export const FFMPEG = cfg.ffmpeg || 'ffmpeg';
