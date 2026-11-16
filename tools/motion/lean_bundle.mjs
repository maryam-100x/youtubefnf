// One Remotion bundle that does not copy the public dir (a long video's public dir can hold many GB: copying it into the temp folder on
// every stills run or every chunk costs minutes and the same space again).
// Remotion's bundle() copies publicDir into <bundle>/public (its own symlinkPublicDir is off on Windows, and file symlinks need a
// privilege Windows doesn't grant by default: EPERM). So: bundle with an empty public dir, then put a directory junction (no privilege
// needed) at <bundle>/public pointing at the real public dir. Remotion's file server lstat()s the final file, a real file behind the
// junction, so it serves it; the junction's target is a lean dir of hard links (pipe.py link), never the originals in PUBLIC (those get
// the old copy), so even a delete that followed the junction could only remove links. Cleaning takes the junction out first (rmdir on
// a junction never touches its target), checks it is gone, then deletes the bundle. On macOS a symlink does the same (unlink takes out only the link).
//   in a script:  const {serveUrl, cleanup} = await leanBundle({entryPoint, publicDir});   try { ... } finally { cleanup(); }
//   for CLI renders (pipe.py):  node lean_bundle.mjs make <publicDir> [entry]   -> prints {"serveUrl": ...}; render with the bundle
//   folder as the entry point (no --public-dir); then  node lean_bundle.mjs clean <bundleDir>
// QA_COPY=1 falls back to Remotion's own copy.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {PUBLIC} from '../common/paths.mjs';

const ORIGINALS = path.resolve(PUBLIC).toLowerCase();

export function cleanLeanBundle(serveUrl) {
  const link = path.join(serveUrl, 'public');
  const isLink = () => {
    try {
      return fs.lstatSync(link).isSymbolicLink();
    } catch (e) {
      if (e.code === 'ENOENT') return false;
      throw e;
    }
  };
  if (isLink()) (process.platform === 'win32' ? fs.rmdirSync : fs.unlinkSync)(link);   // removes the link only, never what it points at
  if (isLink()) throw new Error(`the junction is still there, the bundle is left for a hand check: ${link}`);
  fs.rmSync(serveUrl, {recursive: true, force: true});
}

export async function leanBundle({entryPoint, publicDir}) {
  const pub = path.resolve(publicDir);
  if (process.env.QA_COPY === '1' || pub.toLowerCase() === ORIGINALS) {   // a junction on Windows, a symlink on macOS: no copy
    const serveUrl = await bundle({entryPoint, publicDir: pub});
    return {serveUrl, cleanup: () => fs.rmSync(serveUrl, {recursive: true, force: true}), junction: false};
  }
  if (!fs.statSync(pub).isDirectory()) throw new Error(`public dir is not a folder: ${pub}`);
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), 'lean-pub-'));
  let serveUrl;
  try {
    serveUrl = await bundle({entryPoint, publicDir: empty});
  } finally {
    fs.rmSync(empty, {recursive: true, force: true});
  }
  const link = path.join(serveUrl, 'public');
  fs.rmSync(link, {recursive: true, force: true});   // the empty public dir the bundle made
  fs.symlinkSync(pub, link, 'junction');
  return {serveUrl, cleanup: () => cleanLeanBundle(serveUrl), junction: true};
}

// the CLI (pipe.py's chunked renders)
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [, , cmd, a, b] = process.argv;
  if (cmd === 'make') {
    const {serveUrl, junction} = await leanBundle({entryPoint: path.resolve(b || 'src/index.ts'), publicDir: a});
    console.log(JSON.stringify({serveUrl, junction}));
  } else if (cmd === 'clean') {
    if (!a || !fs.existsSync(path.join(a, 'index.html'))) throw new Error(`not a bundle folder: ${a}`);
    cleanLeanBundle(a);
    console.log(`cleaned ${a}`);
  } else {
    console.error('usage: node lean_bundle.mjs make <publicDir> [entry] | clean <bundleDir>');
    process.exit(2);
  }
}
