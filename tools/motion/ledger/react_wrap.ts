// React as the edits see it in the ledger walker (build.mjs swaps it in for imports from src/ only): the same React, except that every
// element made from one of our components renders through a wrapper that reports the component (its name, its file, its props) and the
// path of components above it; <img>, <video>, SVG <image> and CSS url(...) backgrounds report the file they show.
import * as Real from '../node_modules/react/index.js';
import {PathCtx, recordComp, recordImage, SeqCtx} from './rec';

const R = ((Real as unknown as {default?: typeof Real}).default ?? Real) as typeof Real;

type Fn = ((p: Record<string, unknown>) => unknown) & {__ledger_mod?: string; __ledger_stub?: boolean; displayName?: string; prototype?: {isReactComponent?: unknown}};
const WRAPPED = new WeakMap<Fn, Fn>();
const TAGS = new Map<string, Fn>();
const MEDIA_TAGS = new Set(['img', 'image', 'video']);

const urls = (style: unknown): string[] => {
  if (!style || typeof style !== 'object') return [];
  const out: string[] = [];
  for (const v of Object.values(style as Record<string, unknown>)) {
    if (typeof v !== 'string' || !v.includes('url(')) continue;
    for (const m of v.matchAll(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g)) if (!m[1].startsWith('#') && !m[1].startsWith('data:')) out.push(m[1]);
  }
  return out;
};

const tagWrapper = (tag: string): Fn => {
  const hit = TAGS.get(tag);
  if (hit) return hit;
  const W = ((props: Record<string, unknown>) => {
    const seq = R.useContext(SeqCtx);
    const path = R.useContext(PathCtx);
    if (tag === 'img') recordImage('image', props.src, seq, path);
    if (tag === 'image') recordImage('image', props.href ?? props.xlinkHref, seq, path);
    if (tag === 'video') recordImage('video-tag', props.src, seq, path);
    for (const u of urls(props.style)) recordImage('css', u, seq, path);
    if (MEDIA_TAGS.has(tag)) return null;
    return R.createElement(tag, props);
  }) as Fn;
  W.__ledger_stub = true;
  W.displayName = `ledger:${tag}`;
  TAGS.set(tag, W);
  return W;
};

export const wrapType = (type: unknown, props: Record<string, unknown> | null | undefined): unknown => {
  if (typeof type === 'string') {
    if (MEDIA_TAGS.has(type) || urls(props?.style).length) return tagWrapper(type);
    return type;
  }
  if (typeof type !== 'function') return type;
  const fn = type as Fn;
  if (fn.__ledger_stub || fn.prototype?.isReactComponent) return type;
  const hit = WRAPPED.get(fn);
  if (hit) return hit;
  const name = fn.displayName || (fn as unknown as {name: string}).name || 'Anonymous';
  const mod = fn.__ledger_mod ?? '';
  const W = ((props: Record<string, unknown>) => {
    const path = R.useContext(PathCtx);
    const seq = R.useContext(SeqCtx);
    recordComp(name, mod, props, seq, path);
    const out = fn(props);
    return R.createElement(PathCtx.Provider, {value: [...path, [name, mod]]}, out as React.ReactNode);
  }) as Fn;
  Object.assign(W, fn);
  W.displayName = name;
  W.__ledger_stub = true;
  WRAPPED.set(fn, W);
  return W;
};

const createElement = (type: unknown, config: Record<string, unknown> | null, ...children: unknown[]) =>
  (R.createElement as (...a: unknown[]) => unknown)(wrapType(type, config), config, ...children);

export * from '../node_modules/react/index.js';
export {createElement};
export default {...R, createElement};
