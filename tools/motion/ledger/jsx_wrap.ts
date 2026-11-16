// react/jsx-runtime for the edits in the ledger walker: React's own, with each element's type passed through react_wrap's wrapType.
import * as RT0 from '../node_modules/react/jsx-runtime.js';
import {wrapType} from './react_wrap';

const RT = ((RT0 as unknown as {default?: typeof RT0}).default ?? RT0) as unknown as {
  Fragment: unknown;
  jsx: (t: unknown, p: Record<string, unknown>, k?: unknown) => unknown;
  jsxs: (t: unknown, p: Record<string, unknown>, k?: unknown) => unknown;
};

export const Fragment = RT.Fragment;
export const jsx = (t: unknown, p: Record<string, unknown>, k?: unknown) => RT.jsx(wrapType(t, p), p, k);
export const jsxs = (t: unknown, p: Record<string, unknown>, k?: unknown) => RT.jsxs(wrapType(t, p), p, k);
export const jsxDEV = (t: unknown, p: Record<string, unknown>, k?: unknown) => RT.jsx(wrapType(t, p), p, k);
