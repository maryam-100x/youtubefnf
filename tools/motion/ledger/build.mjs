// Bundles one ledger walker entry (asset_ledger.py writes it: a composition and walk()) for node:
//   node tools/motion/ledger/build.mjs <entry.tsx> <out.cjs>
// 'remotion' and the @remotion add-ons become the stubs in this folder; inside src/ React and its JSX runtime become react_wrap/jsx_wrap,
// and every top-level component of a src/ file is tagged with its file (__ledger_mod) so the ledger knows where each graphic comes from.
import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const MOTION = path.resolve(HERE, '..');
// the edit's src/: the working tree, or a committed one exported by asset_ledger.py --rev (LEDGER_SRC)
const SRC = path.resolve(process.env.LEDGER_SRC || path.join(MOTION, 'src'));
const [entry, outfile] = process.argv.slice(2);
if (!entry || !outfile) {
  console.error('usage: node build.mjs <entry.tsx> <out.cjs>');
  process.exit(2);
}
const inSrc = (p) => !!p && path.resolve(p).toLowerCase().startsWith(SRC.toLowerCase() + path.sep);

const ledger = {
  name: 'ledger',
  setup(b) {
    b.onResolve({filter: /^remotion$/}, () => ({path: path.join(HERE, 'remotion_stub.tsx')}));
    b.onResolve({filter: /^@remotion\/(google-fonts|motion-blur|transitions|effects|mac-cursors|media|three)(\/.*)?$/}, () => ({path: path.join(HERE, 'pkg_stub.tsx')}));
    b.onResolve({filter: /^react$/}, (a) => (inSrc(a.importer) ? {path: path.join(HERE, 'react_wrap.ts')} : undefined));
    b.onResolve({filter: /^react\/jsx(-dev)?-runtime$/}, (a) => (inSrc(a.importer) ? {path: path.join(HERE, 'jsx_wrap.ts')} : undefined));
    b.onLoad({filter: /\.tsx?$/}, async (a) => {
      if (!inSrc(a.path)) return undefined;
      const src = await fs.promises.readFile(a.path, 'utf8');
      const rel = path.relative(SRC, a.path).replace(/\\/g, '/');
      const names = [...new Set([...src.matchAll(/^(?:export\s+)?(?:const|function|let)\s+([A-Z][A-Za-z0-9_]*)/gm)].map((m) => m[1]))];
      const tag = names.map((n) => `try{if(typeof ${n}==='function')Object.defineProperty(${n},'__ledger_mod',{value:${JSON.stringify(rel)},configurable:true});}catch(e){}`);
      return {contents: `${src}\n${tag.join('\n')}\n`, loader: a.path.endsWith('x') ? 'tsx' : 'ts', resolveDir: path.dirname(a.path)};
    });
  },
};

await esbuild.build({
  entryPoints: [entry],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  outfile,
  keepNames: true,
  logLevel: 'error',
  jsx: 'automatic',
  define: {'process.env.NODE_ENV': '"production"'},
  plugins: [ledger],
});
