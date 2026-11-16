// kit3 · measuring in the browser: fonts, text widths, a picture's visible pixels, a page's ink. Every measurement holds the render
// (useDelayRender, Remotion's recommended hook since v4.0.342; remotion.dev/docs/use-delay-render) until it is in, and releases it only
// AFTER the render that mounts what waited on it.
//
// The black-frames race this prevents: a hook that released its handle the moment the boxes were in, before the components waiting on
// them had mounted, let a blurred ground (an OffthreadVideo) take its own delayRender one render too late, and each render tab's first
// frame went out black (3 at concurrency 3, up to 6 at 6). Here, by construction:
//   1. the handle is released in an effect that runs after the commit that used the measurement (a parent's effect runs after its
//      children's, so every child's own delayRender, an <Img>'s or an OffthreadVideo's, is already held by then);
//   2. the kit's components never hide their ground while they measure: Stage mounts its footage at once and only the measured foreground
//      waits (a stage that returned null while measuring went out black);
//   3. a handle is taken per measurement key, so a prop change that needs a new measurement holds the frame again.
// Every render tab has its own copy of these caches (remotion.dev/docs/flickering: tabs share no state): nothing depends on render order.
import {useEffect, useRef, useState} from 'react';
import {staticFile, useDelayRender} from 'remotion';
import {DS, FONT, FONTS} from './tokens';
import {Box, inkSnap, isDark, isInk, paperOf} from './layout';

const CACHE = new Map<string, unknown>();
const PENDING = new Map<string, Promise<unknown>>();

// the generic hold: `load` runs once per key per tab; the component gets null until the value is in
export function useMeasured<T>(key: string, load: () => Promise<T>, label: string): T | null {
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const handles = useRef(new Map<string, number>());
  const [loaded, bump] = useState(0);
  if (!CACHE.has(key) && !handles.current.has(key)) {
    handles.current.set(key, delayRender(`kit3: ${label}`, {timeoutInMilliseconds: 60000}));
  }
  useEffect(() => {
    if (CACHE.has(key)) return;
    let live = true;
    let p = PENDING.get(key) as Promise<T> | undefined;
    if (!p) {
      p = load().then((v) => {
        CACHE.set(key, v);
        return v;
      });
      PENDING.set(key, p);
    }
    p.then(() => {
      if (live) bump((x) => x + 1);
    }, (e) => cancelRender(e));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  // after the commit that mounted what waited (see the header)
  useEffect(() => {
    for (const [k, h] of Array.from(handles.current.entries())) {
      if (CACHE.has(k)) {
        continueRender(h);
        handles.current.delete(k);
      }
    }
  }, [loaded, key, continueRender]);
  // unmounted before the value came: never leave a handle to time out
  useEffect(() => () => {
    for (const h of Array.from(handles.current.values())) continueRender(h);
    handles.current.clear();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return CACHE.has(key) ? (CACHE.get(key) as T) : null;
}

// ================================================================================================================================ fonts
const FAMILY = `"${FONT.replace(/["']/g, '')}"`;
let FONTS_OK = false;
const loadFonts = () => FONTS.waitUntilDone()
  .then(() => Promise.all(['500', '600', '700', '800'].map((w) => document.fonts.load(`${w} 100px ${FAMILY}`, '0123456789AZaz'))))
  .then(() => {
    FONTS_OK = true;
    return true;
  });
// true once Archivo's faces are in (a width measured before that is the fallback face's: odometer slots 13% narrow)
export const useFontsReady = () => !!useMeasured('fonts', loadFonts, 'fonts') || FONTS_OK;

// a text's width at `px` (Archivo, `weight`, tracking in em), on a real span laid out like the text (a canvas measure was ~3% off);
// only once useFontsReady() is true (a width taken before is never kept)
const WIDTHS = new Map<string, number>();
export const textW = (text: string, px: number, weight: number, tracking = 0) => {
  const key = `${weight}|${px}|${tracking}|${text}`;
  const hit = WIDTHS.get(key);
  if (hit !== undefined) return hit;
  const sp = document.createElement('span');
  Object.assign(sp.style, {position: 'absolute', left: '0px', top: '0px', visibility: 'hidden', whiteSpace: 'pre', fontFamily: FAMILY,
    fontSize: `${px}px`, fontWeight: String(weight), letterSpacing: `${tracking}em`, fontVariantNumeric: 'tabular-nums', lineHeight: '1'});
  sp.textContent = text;
  document.body.appendChild(sp);
  const w = sp.getBoundingClientRect().width;
  document.body.removeChild(sp);
  if (FONTS_OK) WIDTHS.set(key, w);
  return w;
};

// =============================================================================================================================== images
// a file in the public dir (a path from its root: '<video>/img/x.png')
export const url = (src: string) => staticFile(src);
const IMGS = new Map<string, Promise<HTMLImageElement>>();
const loadImage = (src: string) => {
  let p = IMGS.get(src);
  if (!p) {
    p = new Promise<HTMLImageElement>((resolve, reject) => {
      const im = new Image();
      im.onload = () => resolve(im);
      im.onerror = () => reject(new Error(`kit3: cannot load ${src} (is it in the public dir?)`));
      im.src = url(src);
    });
    IMGS.set(src, p);
  }
  return p;
};
const pixels = (im: HTMLImageElement, sx: number, sy: number, sw: number, sh: number, dw = sw, dh = sh) => {
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(dw));
  c.height = Math.max(1, Math.round(dh));
  const g = c.getContext('2d', {willReadFrequently: true}) as CanvasRenderingContext2D;
  g.drawImage(im, sx, sy, sw, sh, 0, 0, c.width, c.height);
  return g.getImageData(0, 0, c.width, c.height).data;
};

// a picture's own size and the box of its visible pixels (alpha > 16, as the gate's alpha_box), measured at up to 2048 px on its long
// side (at 640 px a tall cut-out measured up to 1.4 film px off, beyond the 2-px row test); `wx`, `wy`: the visible pixels' centre of
// mass (alpha-weighted), for a lone logo centred to the eye (layout.visualDx)
export type ImgBox = {iw: number; ih: number; x0: number; y0: number; x1: number; y1: number; wx: number; wy: number};
const measureAlpha = async (src: string): Promise<ImgBox> => {
  const im = await loadImage(src);
  const iw = im.naturalWidth, ih = im.naturalHeight;
  const k = Math.min(1, 2048 / Math.max(iw, ih));
  const cw = Math.max(1, Math.round(iw * k)), ch = Math.max(1, Math.round(ih * k));
  const d = pixels(im, 0, 0, iw, ih, cw, ch);
  let x0 = cw, y0 = ch, x1 = -1, y1 = -1;
  let sa = 0, sx = 0, sy = 0;
  for (let y = 0; y < ch; y++) {
    for (let x = 0; x < cw; x++) {
      const a = d[(y * cw + x) * 4 + 3];
      if (a > 16) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
        sa += a;
        sx += a * x;
        sy += a * y;
      }
    }
  }
  return x1 < 0 ? {iw, ih, x0: 0, y0: 0, x1: iw, y1: ih, wx: iw / 2, wy: ih / 2}
    : {iw, ih, x0: x0 / k, y0: y0 / k, x1: Math.min(iw, (x1 + 1) / k), y1: Math.min(ih, (y1 + 1) / k), wx: (sx / sa + 0.5) / k,
      wy: (sy / sa + 0.5) / k};
};
export const useImgBoxes = (srcs: string[]): ImgBox[] | null =>
  useMeasured(`alpha|${srcs.join('|')}`, () => Promise.all(srcs.map((s) => {
    const k = `alpha1|${s}`;
    if (!PENDING.has(k)) PENDING.set(k, measureAlpha(s));
    return PENDING.get(k) as Promise<ImgBox>;
  })), `measuring ${srcs.length} picture(s)`);

// ============================================================================================================================ page ink
// One page: its size, its paper (the crop's dominant colour) and whether it is dark, the crop's ink count, and each mark's box snapped to
// its ink (layout.inkSnap) with the ink it holds. The crop is counted at up to 1200 px wide (the share is a ratio); the snap runs at 1:1.
export type PageInk = {iw: number; ih: number; paper: [number, number, number]; dark: boolean; cropInk: number;
  marks: {ink: Box | null; inkCount: number}[]};
const measurePage = async (src: string, crop: Box | undefined, boxes: Box[], snap: boolean[]): Promise<PageInk> => {
  const im = await loadImage(src);
  const iw = im.naturalWidth, ih = im.naturalHeight;
  const [cx, cy, cw, ch] = crop ?? [0, 0, iw, ih];
  const sx = Math.max(0, cx), sy = Math.max(0, cy);
  const sw = Math.max(1, Math.min(iw, cx + cw) - sx), sh = Math.max(1, Math.min(ih, cy + ch) - sy);
  const q = Math.min(1, 1200 / sw, 1200 / sh);
  const cd = pixels(im, sx, sy, sw, sh, sw * q, sh * q);
  const qw = Math.max(1, Math.round(sw * q)), qh = Math.max(1, Math.round(sh * q));
  const paper = paperOf(cd, 1);
  let cropInk = 0;
  for (let i = 0; i < cd.length; i += 4) if (isInk(cd, i, paper)) cropInk++;
  const inkIn = (b: Box) => {
    let n = 0;
    const x0 = Math.max(0, Math.floor((b[0] - sx) * q)), x1 = Math.min(qw, Math.ceil((b[0] + b[2] - sx) * q));
    const y0 = Math.max(0, Math.floor((b[1] - sy) * q)), y1 = Math.min(qh, Math.ceil((b[1] + b[3] - sy) * q));
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) if (isInk(cd, (y * qw + x) * 4, paper)) n++;
    return n;
  };
  const marks = boxes.map((b, i) => {
    if (!snap[i]) {
      const inside = b[0] < iw && b[1] < ih && b[0] + b[2] > 0 && b[1] + b[3] > 0;
      return {ink: inside ? b : null, inkCount: inkIn(b)};
    }
    const ext = Math.round(0.6 * b[3]), vext = Math.round(0.3 * b[3]);
    const rx = Math.max(0, b[0] - ext), ry = Math.max(0, b[1] - vext);
    const rw = Math.max(1, Math.min(iw, b[0] + b[2] + ext) - rx), rh = Math.max(1, Math.min(ih, b[1] + b[3] + vext) - ry);
    const data = pixels(im, rx, ry, rw, rh);
    const ink = inkSnap({data, rx, ry, rw, rh}, b, paper);
    return {ink, inkCount: ink ? inkIn(ink) : 0};
  });
  return {iw, ih, paper, dark: isDark(paper), cropInk: Math.round(cropInk / (q * q)), marks: marks.map((m) => ({...m,
    inkCount: Math.round(m.inkCount / (q * q))}))};
};
export type PageReq = {src: string; crop?: Box; boxes: Box[]; snap: boolean[]};
export const usePagesInk = (reqs: PageReq[]): PageInk[] | null =>
  useMeasured(`pages|${reqs.map((r) => `${r.src}|${r.crop ? r.crop.join(',') : '-'}|${r.boxes.map((b) => b.join(',')).join(';')}|${r.snap.join(',')}`).join('||')}`,
    () => Promise.all(reqs.map((r) => measurePage(r.src, r.crop, r.boxes, r.snap))), `reading ${reqs.map((r) => r.src).join(', ')}`);

export const PAD = DS.MARK.PAD;
