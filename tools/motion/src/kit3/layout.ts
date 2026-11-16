// kit3 · the pure math (no React, no browser): every placement rule a component enforces, as functions the unit test runs in node
// (kit3/test/layout.test.mjs). Remotion's own testing guidance (remotion.dev/docs/testing): test components like any React code, and
// keep the math testable on its own; the pictures are proven by stills (kit3_proof.mjs + kit3_check.py).
//
//   inkSnap        a mark's box snapped to the ink it marks (the run's own ink + its touching punctuation; a box on no ink is null)
//   markVerdict    the guards every mark passes (redundancy, MARK_LATE, the box on nothing)
//   markRect       a snapped ink box in a page's film px: whole pixels, the even pad, the border inside
//   expandCrop     a crop grown so every padded mark sits whole inside its card (never a lit phrase cut at the crop's edge)
//   rowLayout      a row of pictures: one height, equal gaps between their VISIBLE pixels, the whole visible content (pictures and their
//                  names) centred, names never touching (gate B13/B14)
//   timelineLayout dates at true distances, labels never overlapping (alternating sides), kept inside the content box
//   fitKeys / keysAcross   a typed line's keys, finished 0.3 s before the cut (gate MOVING_AT_CUT)

export type Box = [number, number, number, number];   // x, y, w, h

// ======================================================================================================================== ink and marks
// ink(x, y): is the pixel at (x, y) of a region ink (unlike the paper)? The region's paper is its dominant colour (paperOf). A pixel is
// ink when any channel differs from the paper by more than INK_T (24%): dark text on white, light text on black, red or yellow text alike.
export const INK_T = 60;
export const paperOf = (rgba: Uint8ClampedArray | number[], step = 1): [number, number, number] => {
  const counts = new Map<number, number>();
  let best = 0, bestN = -1;
  for (let i = 0; i < rgba.length; i += 4 * step) {
    const q = ((rgba[i] >> 4) << 8) | ((rgba[i + 1] >> 4) << 4) | (rgba[i + 2] >> 4);
    const n = (counts.get(q) ?? 0) + 1;
    counts.set(q, n);
    if (n > bestN) {
      bestN = n;
      best = q;
    }
  }
  return [((best >> 8) & 15) * 16 + 8, ((best >> 4) & 15) * 16 + 8, (best & 15) * 16 + 8];
};
export const isInk = (rgba: Uint8ClampedArray | number[], i: number, paper: [number, number, number]) =>
  Math.max(Math.abs(rgba[i] - paper[0]), Math.abs(rgba[i + 1] - paper[1]), Math.abs(rgba[i + 2] - paper[2])) > INK_T;
export const isDark = (paper: [number, number, number]) => 0.2126 * paper[0] + 0.7152 * paper[1] + 0.0722 * paper[2] < 110;

// The snap: `region` is the pixels of the area around the box (rx, ry its top-left in the capture, rw x rh), `box` the given word box
// (a page capture's DOM word box: its height is the line box, so the words' ink sits inside it with blank above and below, up to 26 px
// of it). Glyphs, not rows: the ink is split into connected components (8-connected), then
//  1. the line's core band: the rows inside the box whose ink (in the box's columns) reaches 25% of the busiest row's: the x-height
//     zone of the marked line. A neighbouring line's descender reaching into the box (a tight headline: line 1's "p" in line 2's
//     box) is a few pixels per row and stays out of it;
//  2. the run: every glyph on the core band (40% of its height in it) with its centre inside the box's columns, then any glyph on the band
//     that starts within `gapX` (12% of the line box) of the run (the colon after "pulled", the "!" after "servers"; a word space is wider);
//  3. the marks on the run's letters: a small glyph (60% of the band at most) clear of the band, within 0.8 bands over or under it, over
//     the run's columns (an i's dot, an accent);
// and the ink box is the union of those glyphs (a descender or ascender of the run's own letters is part of its glyph). Returns the box
// in capture px, or null when there is no ink under the box (a box on blank space, e.g. 44 px off its tile: refused by markVerdict).
export const inkSnap = (region: {data: Uint8ClampedArray | number[]; rx: number; ry: number; rw: number; rh: number},
  box: Box, paper: [number, number, number]): Box | null => {
  const {data, rx, ry, rw, rh} = region;
  const [bx, by, bw, bh] = box;
  const N = rw * rh;
  const ink = new Uint8Array(N);
  for (let i = 0; i < N; i++) ink[i] = isInk(data, i * 4, paper) ? 1 : 0;
  const c0 = Math.max(0, bx - rx), c1 = Math.min(rw, bx + bw - rx);      // the box's columns in the region
  const r0 = Math.max(0, by - ry), r1 = Math.min(rh, by + bh - ry);      // its rows
  const count = new Array(Math.max(0, r1 - r0)).fill(0);
  for (let y = r0; y < r1; y++) for (let x = c0; x < c1; x++) count[y - r0] += ink[y * rw + x];
  const top = Math.max(0, ...count);
  if (top === 0) return null;
  // 1. the core band: from the busiest row out, while rows keep 25% of it (two thin rows forgiven)
  const peak = count.indexOf(top);
  const thr = 0.25 * top;
  let cT = peak, cB = peak;
  for (let y = peak - 1, low = 0; y >= 0 && low <= 2; y--) {
    if (count[y] >= thr) {
      cT = y;
      low = 0;
    } else low++;
  }
  for (let y = peak + 1, low = 0; y < count.length && low <= 2; y++) {
    if (count[y] >= thr) {
      cB = y;
      low = 0;
    } else low++;
  }
  cT += r0;
  cB += r0;
  const coreH = cB - cT + 1;
  // the glyphs (8-connected components) with their boxes
  const lab = new Int32Array(N);
  const comps: {x0: number; y0: number; x1: number; y1: number}[] = [];
  const stack: number[] = [];
  for (let i = 0; i < N; i++) {
    if (!ink[i] || lab[i]) continue;
    const id = comps.length + 1;
    const c = {x0: rw, y0: rh, x1: -1, y1: -1};
    lab[i] = id;
    stack.push(i);
    while (stack.length) {
      const j = stack.pop() as number;
      const x = j % rw, y = (j - x) / rw;
      if (x < c.x0) c.x0 = x;
      if (x > c.x1) c.x1 = x;
      if (y < c.y0) c.y0 = y;
      if (y > c.y1) c.y1 = y;
      for (let dy = -1; dy <= 1; dy++) {
        const yy = y + dy;
        if (yy < 0 || yy >= rh) continue;
        for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx;
          if (xx < 0 || xx >= rw) continue;
          const k = yy * rw + xx;
          if (ink[k] && !lab[k]) {
            lab[k] = id;
            stack.push(k);
          }
        }
      }
    }
    comps.push(c);
  }
  // on the line: at least 40% of the glyph's own height inside the core band (a letter, a period, a comma, a colon); a neighbouring
  // line's descender poking into the band has a few % of its height there
  const crosses = (c: {y0: number; y1: number}) => Math.max(0, Math.min(c.y1, cB) - Math.max(c.y0, cT) + 1) >= 0.4 * (c.y1 - c.y0 + 1);
  const take = comps.map((c) => crosses(c) && (c.x0 + c.x1) / 2 >= c0 && (c.x0 + c.x1) / 2 < c1);
  if (!take.some(Boolean)) return null;
  let L = rw, R = -1;
  comps.forEach((c, i) => {
    if (take[i]) {
      L = Math.min(L, c.x0);
      R = Math.max(R, c.x1);
    }
  });
  // 2. glyphs on the core band touching the run (gap < gapX), until none is added
  const gapX = Math.max(3, Math.round(0.12 * bh));
  for (let grew = true; grew;) {
    grew = false;
    comps.forEach((c, i) => {
      if (take[i] || !crosses(c)) return;
      if (c.x0 <= R + gapX && c.x1 >= L - gapX) {
        take[i] = true;
        L = Math.min(L, c.x0);
        R = Math.max(R, c.x1);
        grew = true;
      }
    });
  }
  // 3. dots and accents over or under the run's letters: small (60% of the band at most), clear of the band, whole inside the search
  // region (a glyph cut by its edge is part of something bigger: a neighbouring line's letter)
  comps.forEach((c, i) => {
    if (take[i]) return;
    const clear = c.y1 < cT || c.y0 > cB;
    const whole = c.y0 > 0 && c.y1 < rh - 1;
    if (clear && whole && c.y1 - c.y0 + 1 <= 0.6 * coreH && c.y0 >= cT - 0.8 * coreH && c.y1 <= cB + 0.8 * coreH && c.x0 >= L - gapX
      && c.x1 <= R + gapX) take[i] = true;
  });
  let T = rh, B = -1;
  L = rw;
  R = -1;
  comps.forEach((c, i) => {
    if (!take[i]) return;
    L = Math.min(L, c.x0);
    R = Math.max(R, c.x1);
    T = Math.min(T, c.y0);
    B = Math.max(B, c.y1);
  });
  return [rx + L, ry + T, R - L + 1, B - T + 1];
};

// The guards (thrown by the components: a mark that fails one never reaches a render).
//  - LATE (gate B5 MARK_LATE, LONG_FORM "every mark ends at least 0.6 s before its page's cut"): the light (0.12 s) is done 0.6 s
//    before the cut
//  - NOTHING: a box with no ink under it (a box placed beside the thing, e.g. 44 px below its tile)
//  - REDUNDANT ("a crop that is only that thing needs none"; "almost the whole text highlighted" reads as nothing marked): a mark (or
//    all marks together) holding 60% or more of the crop's ink, or a box covering 45% or more of the crop's area. On measured cases: a
//    name alone in its crop 0.78 of the ink (refused), a two-line headline half lit 0.51 (kept), three lit lines of a press page 0.45
//    together (kept)
export const REDUNDANT_INK = 0.6;
export const REDUNDANT_AREA = 0.45;
export type MarkCase = {at: number; ink: Box | null; inkCount: number; area: number};
export const markVerdict = (d: number, cropArea: number, cropInk: number, marks: MarkCase[], what = 'mark'): string[] => {
  const out: string[] = [];
  marks.forEach((m, i) => {
    if (m.at > d - DS_LATE - 0.12) out.push(`${what} ${i + 1} lights at ${m.at.toFixed(2)} s of a ${d.toFixed(2)}-s shot: inside its last 0.6 s (MARK_LATE)`);
    if (!m.ink) out.push(`${what} ${i + 1}: no ink under its box (a box on blank space)`);
    if (cropInk > 0 && m.inkCount / cropInk >= REDUNDANT_INK) {
      out.push(`${what} ${i + 1} holds ${(100 * m.inkCount / cropInk).toFixed(0)}% of its crop's ink: the crop is only that thing, it needs no mark`);
    }
    if (cropArea > 0 && m.area / cropArea >= REDUNDANT_AREA) {
      out.push(`${what} ${i + 1} covers ${(100 * m.area / cropArea).toFixed(0)}% of its crop: nothing to pick it out from`);
    }
  });
  const all = marks.reduce((a, m) => a + m.inkCount, 0);
  if (marks.length > 1 && cropInk > 0 && all / cropInk >= REDUNDANT_INK) {
    out.push(`the ${marks.length} marks together hold ${(100 * all / cropInk).toFixed(0)}% of the crop's ink: almost the whole text lit`);
  }
  return out;
};
const DS_LATE = 0.6;

// A snapped ink box on a page card: the card shows `crop` at scale k; the mark's outer edge PAD px from the ink on every side, on whole
// pixels (left/top floored from the ink's own edge, right/bottom ceiled), so the four gaps are equal within a pixel.
export const markRect = (ink: Box, crop: Box, k: number, pad: number): Box => {
  const L = Math.floor((ink[0] - crop[0]) * k) - pad;
  const T = Math.floor((ink[1] - crop[1]) * k) - pad;
  const R = Math.ceil((ink[0] + ink[2] - crop[0]) * k) + pad;
  const B = Math.ceil((ink[1] + ink[3] - crop[1]) * k) + pad;
  return [L, T, R - L, B - T];
};

// A crop grown to hold every padded mark whole with `margin` px of the card around it (in film px at scale k; k depends on the crop, so
// the caller iterates). Past the capture's own edge the card shows the page's paper colour (a title that starts at the capture's x 0
// would otherwise lose its box's left border to the card's edge).
export const expandCrop = (crop: Box, inks: Box[], k: number, pad: number, margin: number): Box => {
  let [x0, y0] = crop;
  let x1 = crop[0] + crop[2], y1 = crop[1] + crop[3];
  const e = (pad + margin) / k;
  for (const b of inks) {
    x0 = Math.min(x0, b[0] - e);
    y0 = Math.min(y0, b[1] - e);
    x1 = Math.max(x1, b[0] + b[2] + e);
    y1 = Math.max(y1, b[1] + b[3] + e);
  }
  return [Math.floor(x0), Math.floor(y0), Math.ceil(x1) - Math.floor(x0), Math.ceil(y1) - Math.floor(y0)];
};

// ================================================================================================================================ rows
// A row of pictures by their visible pixels. Each item: its visible width and height in its file's px (alpha above 16), its name's width
// in film px (0 for none), its size factor k (only when the words compare real sizes) and an optional cap on its width on screen (a wide
// logo). One height `h` for the row; the gap between every pair of VISIBLE figures the same, and wide enough that the names centred under
// them keep `nameGap` between them (a long name under a narrow product would otherwise run past it and push the row off centre); the
// whole visible content (figures and names) centred on `cx`; a row wider than `maxW` shrinks as a whole (the figures; names keep their
// size). Returns each figure's scale (film px per file px), its visible left edge and width on screen, and the gap.
// A LONE figure (a row of one: LogosLand's single logo, one cut-out) is centred to the eye, not by its box (a logo whose weight sits off
// its box's middle reads off centre): `wdx`, its visible pixels' centre of mass from its box's middle (file px), moves it so the point
// halfway between the two sits on `cx`. A row of two or more stays centred by its visible content (B14).
// A wide lockup (wider than LOCKUP_ASPECT: an icon beside a wordmark, read like a line of text) stays centred by its box;
// qa_centred.py lists such a one to look at, never blocks it.
export const LOCKUP_ASPECT = 2.5;
export type RowItem = {vw: number; vh: number; nameW?: number; k?: number; maxW?: number; wdx?: number};
export type RowOut = {scale: number[]; left: number[]; width: number[]; height: number[]; gap: number; fit: number; extent: [number, number]};
export const rowLayout = (items: RowItem[], o: {h: number; gap: number; cx: number; maxW: number; nameGap?: number}): RowOut => {
  const nameGap = o.nameGap ?? 24;
  const base = items.map((it) => {
    let s = (o.h * (it.k ?? 1)) / Math.max(1, it.vh);
    if (it.maxW) s = Math.min(s, it.maxW / Math.max(1, it.vw));
    return s;
  });
  const lay = (fit: number) => {
    const scale = base.map((s) => s * fit);
    const width = items.map((it, i) => it.vw * scale[i]);
    const over = items.map((it, i) => Math.max(0, ((it.nameW ?? 0) - width[i]) / 2));
    let gap = o.gap;
    for (let i = 0; i + 1 < items.length; i++) gap = Math.max(gap, over[i] + over[i + 1] + nameGap);
    const total = width.reduce((a, w) => a + w, 0) + gap * Math.max(0, items.length - 1);
    return {scale, width, over, gap, extentW: total + over[0] + over[items.length - 1]};
  };
  // the largest fit that holds the row inside maxW (the gap may grow as figures shrink under wide names: bisect, don't guess)
  let fit = 1;
  let r = lay(fit);
  if (r.extentW > o.maxW) {
    let lo = 0.05, hi = 1;
    for (let n = 0; n < 50; n++) {
      const mid = (lo + hi) / 2;
      if (lay(mid).extentW <= o.maxW) lo = mid;
      else hi = mid;
    }
    fit = lo;
    r = lay(fit);
  }
  if (r.extentW > o.maxW + 0.5) throw new Error(`kit3 row: ${items.length} items cannot fit ${o.maxW} px even at ${(fit * 100).toFixed(0)}%: fewer items or shorter names`);
  const left: number[] = [];
  // a lone figure to the eye (header); a wide lockup by its box
  const lone = items.length === 1 && items[0].vw / Math.max(1, items[0].vh) <= LOCKUP_ASPECT ? -((items[0].wdx ?? 0) * r.scale[0]) / 2 : 0;
  let x = o.cx - r.extentW / 2 + r.over[0] + lone;
  r.width.forEach((w) => {
    left.push(x);
    x += w + r.gap;
  });
  return {scale: r.scale, left, width: r.width, height: items.map((it, i) => it.vh * r.scale[i]), gap: r.gap, fit,
    extent: [o.cx - r.extentW / 2 + lone, o.cx + r.extentW / 2 + lone]};
};

// =========================================================================================================================== timeline
// Dates at their true distances between L and R; each label (its width in px) centred on its dot below the line, or above when it would
// touch the label before it on the same side; a label that touches on both sides is refused (the dates are too close for words: show
// fewer). The first and last labels shift inward to stay inside [minX, maxX]; their dots stay at their true places.
export const timelineLayout = (days: number[], labelW: number[], L: number, R: number, minX: number, maxX: number, gap = 32) => {
  const span = Math.max(...days) - Math.min(...days) || 1;
  const d0 = Math.min(...days);
  const x = days.map((d) => L + ((R - L) * (d - d0)) / span);
  const lastEnd = {below: -1e9, above: -1e9};
  const out = days.map((_, i) => {
    let left = Math.min(maxX - labelW[i], Math.max(minX, x[i] - labelW[i] / 2));
    let side: 'below' | 'above' = 'below';
    if (left < lastEnd.below + gap) {
      side = 'above';
      if (left < lastEnd.above + gap) {
        throw new Error(`kit3 Timeline: label ${i + 1} (${labelW[i].toFixed(0)} px) touches its neighbours on both sides at true distances: show fewer dates`);
      }
    }
    lastEnd[side] = left + labelW[i];
    left = Math.round(left);
    return {x: x[i], left, side};
  });
  return out;
};

// ======================================================================================================================== typed lines
export const keysAcross = (chars: number, a: number, b: number) =>
  Array.from({length: chars}, (_, i) => (chars === 1 ? b : a + ((b - a) * i) / (chars - 1)));
// the line whole and at rest for the shot's last `rest` s (gate MOVING_AT_CUT: a date still typing at the cut): keys past d - rest
// pulled in, the spread kept from the first key (the cue sheet's key sounds read the same function: export it to them)
export const fitKeys = (keys: number[], d: number, rest = 0.3) => {
  if (!keys.length) return keys;
  const a = keys[0], b = keys[keys.length - 1], lim = d - rest;
  if (b <= lim) return keys;
  if (keys.length < 2) return [lim];
  const a2 = Math.min(a, lim - 0.04 * (keys.length - 1));
  return keys.map((k) => a2 + ((k - a) * (lim - a2)) / (b - a));
};
