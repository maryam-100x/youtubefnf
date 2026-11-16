// The pre-render gate's probe: a first version free of real mistakes is checked before the render, not after it.
// With REMOTION_GATE=1 (tools/motion/gate_probe.mjs passes it to renderFrames) nothing here or in Clip/SpeedRamp fetches video:
//   - every Clip and SpeedRamp logs one `GATE|clip|{...}` line per frame: its file, the source second it shows, its fitted start and
//     rate, its Sequence's length and where it sits, so a clip asked past its file's end (a freeze) is found in any graphic; in place of
//     the video it leaves an empty pane marked data-gateclip, so the pane's real box is measured like everything else;
//   - <GateLayout/> (in every gated() composition) logs one `GATE|layout|{...}` line per frame: every visible text (its own words' box),
//     picture, clip pane and drawn shape (a mark, a bar, an svg) with its real box after all zooms, the box its overflow-hidden parents
//     leave it, its opacity and font size, and the item it sits inside, so text cut by a zoom or the frame edge, text on text, a picture
//     half off-screen, an animation still moving at the cut and an effect with nothing happening are measured, not judged from one still.
// A normal render or still never sees any of it (gateOn is false).
import React from 'react';
import {continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';

type Env = {process?: {env?: Record<string, string>}};
export const gateOn = typeof window !== 'undefined' && (window as unknown as Env).process?.env?.REMOTION_GATE === '1';

export const gateLog = (kind: string, o: Record<string, unknown>) => console.log(`GATE|${kind}|${JSON.stringify(o)}`);

const r1 = (n: number) => Math.round(n * 10) / 10;
// a short hash (djb2): only whether something changed matters
const sig = (x: string) => {
  let h = 5381;
  for (let i = 0; i < x.length; i++) h = ((h << 5) + h + x.charCodeAt(i)) | 0;
  return h;
};

const visibleColour = (c: string) => {
  const m = c.match(/rgba?\(([^)]+)\)/);
  if (!m) return false;
  const p = m[1].split(',').map((x) => parseFloat(x));
  return (p.length < 4 ? 1 : p[3]) > 0.15;
};

const measure = (frame: number, W: number, H: number) => {
  const items: Record<string, unknown>[] = [];
  const index = new Map<Element, number>();
  const all = Array.from(document.body.querySelectorAll('*')) as HTMLElement[];
  // kit3's rows (tools/motion/src/kit3/rows.tsx, data-kit3="row"): every item inside one names its row, so B14 reads the row the
  // kit built instead of guessing it from picture boxes (kit3 cut-outs keep their transparent margins: the boxes don't share a floor)
  const rows = Array.from(document.querySelectorAll('[data-kit3="row"]'));
  for (const el of all) {
    const tag = el.tagName;
    const clipSrc = el.getAttribute('data-gateclip');
    const textNodes = Array.from(el.childNodes).filter((n) => n.nodeType === 3 && (n.textContent || '').trim());
    const isImg = tag === 'IMG';
    const isSvg = tag === 'svg';
    let kind = '';
    if (clipSrc) kind = 'clip';
    else if (isImg) kind = 'img';
    else if (textNodes.length) kind = 'text';
    else if (isSvg) kind = 'svg';
    else {
      const cs0 = getComputedStyle(el);
      if (visibleColour(cs0.backgroundColor) || (parseFloat(cs0.borderTopWidth) > 0 && visibleColour(cs0.borderTopColor)) || cs0.backgroundImage !== 'none') kind = 'box';
      // a mark that draws nothing itself is still the mark's box (kit3's SpotGate: the spot look lights the picture round the thing
      // instead of drawing a box). Without this the probe would skip every spot mark and B12/B16/B25 would never see one
      else if (el.getAttribute('data-gate') === 'mark') kind = 'box';
    }
    if (!kind) continue;
    // a text's own words, not its element's box (a span inside a div is its own item)
    let r: DOMRect;
    if (kind === 'text') {
      const range = document.createRange();
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const n of textNodes) {
        range.selectNodeContents(n);
        for (const q of Array.from(range.getClientRects())) {
          if (q.width < 1 || q.height < 1) continue;
          x0 = Math.min(x0, q.left); y0 = Math.min(y0, q.top); x1 = Math.max(x1, q.right); y1 = Math.max(y1, q.bottom);
        }
      }
      if (x1 < x0) continue;
      r = new DOMRect(x0, y0, x1 - x0, y1 - y0);
    } else {
      const target = kind === 'clip' ? (el.firstElementChild as HTMLElement | null) || el : el;
      r = target.getBoundingClientRect();
    }
    if (r.width < 2 || r.height < 2) continue;
    if (kind === 'box' && r.width >= W * 0.97 && r.height >= H * 0.97) continue;   // a full-frame backdrop
    let op = 1;
    let br = 1;   // the brightness its filters leave (blur(26px) brightness(0.5) on a ground): a dimmed ground reads as black
    let bl = 0;   // the blur its filters add up to, in px (a blurred ground under a page hides its own cadence and edges)
    let hidden = false;
    let clip = {x0: -1e9, y0: -1e9, x1: 1e9, y1: 1e9};
    let pa = -1;
    for (let p: HTMLElement | null = el; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      op *= parseFloat(cs.opacity || '1');
      for (const m of (cs.filter || '').matchAll(/brightness\(([\d.]+)(%?)\)/g)) br *= parseFloat(m[1]) / (m[2] ? 100 : 1);
      for (const m of (cs.filter || '').matchAll(/blur\(([\d.]+)px\)/g)) bl += parseFloat(m[1]);
      if (cs.visibility === 'hidden' || cs.display === 'none') hidden = true;
      if (p !== el && pa < 0 && index.has(p)) pa = index.get(p) as number;
      if (p !== el && (cs.overflowX !== 'visible' || cs.overflowY !== 'visible')) {
        const pr = p.getBoundingClientRect();
        clip = {x0: Math.max(clip.x0, pr.left), y0: Math.max(clip.y0, pr.top), x1: Math.min(clip.x1, pr.right), y1: Math.min(clip.y1, pr.bottom)};
      }
    }
    if (kind === 'clip') {
      // the pane itself (overflow hidden) crops its moved inner fill
      const pr = el.getBoundingClientRect();
      clip = {x0: Math.max(clip.x0, pr.left), y0: Math.max(clip.y0, pr.top), x1: Math.min(clip.x1, pr.right), y1: Math.min(clip.y1, pr.bottom)};
    }
    if (hidden || op < 0.05) continue;
    const cs = getComputedStyle(el);
    index.set(el, items.length);
    items.push({
      k: kind,
      t: kind === 'img' ? decodeURIComponent(((el as HTMLImageElement).src || '').split('/public/').pop() || '') : kind === 'clip' ? clipSrc : kind === 'text' ? textNodes.map((n) => n.textContent).join(' ').trim().slice(0, 60) : '',
      x: r1(r.left), y: r1(r.top), w: r1(r.width), h: r1(r.height),
      cx0: r1(clip.x0), cy0: r1(clip.y0), cx1: r1(clip.x1), cy1: r1(clip.y1),
      op: Math.round(op * 100) / 100,
      br: Math.round(br * 100) / 100,
      bl: r1(bl),
      rw: rows.length ? rows.indexOf(el.closest('[data-kit3="row"]') as Element) : -1,
      fs: kind === 'text' ? r1(parseFloat(cs.fontSize || '0')) : 0,
      // what it looks like besides where it is: a text's colour, a shape's fill and edge, an svg's drawing (a circle growing, a line
      // drawn, a city lit), so an effect lands on a change of look too
      // a hollow box: an outline with nothing filled in (a dashed slot waiting for a cover): empty unless something sits in it
      e: kind === 'box' && !visibleColour(cs.backgroundColor) && cs.backgroundImage === 'none' ? 1 : 0,
      c: kind === 'text' ? sig(cs.color) : kind === 'box' ? sig(cs.backgroundColor + cs.borderTopColor + cs.backgroundImage) : kind === 'svg' ? sig(el.innerHTML) : 0,
      pa,
      // a component can name what an item is (data-gate="credit", "mark", "stamp" ...): the checks treat credits and marks by it
      g: el.closest('[data-gate]')?.getAttribute('data-gate') || '',
      // a spot-look mark (kit3 SpotGate) draws no box: B16's border-on-ink tests don't apply to it (the light is soft, there is no edge)
      ...(el.getAttribute('data-kit3') === 'spot-gate' ? {sp: 1} : {}),
      // a box's corner radius as a share of its short side (0.5 = a circle): an untagged round outline is a graphic's ping or reticle,
      // not a mark (gate.mark_items)
      ...(kind === 'box' && parseFloat(cs.borderTopLeftRadius) > 0
        ? {rr: Math.round(Math.min(1, parseFloat(cs.borderTopLeftRadius) / Math.max(1, Math.min(r.width, r.height))) * 100) / 100} : {}),
    });
  }
  const ats = Array.from(document.querySelectorAll('[data-gateat]')).map((e) => Number(e.getAttribute('data-gateat')));
  gateLog('layout', {frame, W, H, items, ats});
};

// Every hold this page made and hasn't released. After a piece throws, React throws away the frame's first render and renders it
// again, so the useMemo below makes a second hold and the first is never released: the probe would then die of Remotion's 28-s
// delayRender timeout ("gate layout 10") although GateBoundary caught the refusal (src/gatecrash_test_index.ts repeats that throw).
// A page renders one frame at a time, so a measured frame releases every hold left.
const holds = new Set<number>();

const GateLayout: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  // one hold per frame: renderFrames keeps a page and moves its frame, so the frame isn't done until it has been measured
  const handle = React.useMemo(() => {
    const h = delayRender(`gate layout ${frame}`);
    holds.add(h);
    return h;
  }, [frame]);
  React.useEffect(() => {
    let done = false;
    const go = () => requestAnimationFrame(() => requestAnimationFrame(() => {
      if (done) return;
      done = true;
      measure(frame, width, height);
      for (const h of Array.from(holds)) {
        holds.delete(h);
        continueRender(h);
      }
    }));
    // measure when the frame is what the render would capture: every other delayRender of the page released (a component that measures
    // its pictures and then mounts them holds one) and every <img> loaded, then two paints. Measured right after its own first paint, a
    // frame rendered cold (every 12th frame, or a tab's first) would lose pictures still being mounted: the same frame read two ways on
    // two runs
    let timer: ReturnType<typeof setTimeout> | undefined;
    const others = () => (((window as unknown as {remotion_delayRenderHandles?: number[]}).remotion_delayRenderHandles) || []).filter((h) => !holds.has(h));
    const wait = (n: number) => {
      const busy = others().length > 0 || Array.from(document.images).some((i) => !i.complete);
      if (busy && n < 200) {
        timer = setTimeout(() => wait(n + 1), 15);
        return;
      }
      go();
    };
    wait(0);
    const t = setTimeout(go, 4000);
    return () => {
      clearTimeout(t);
      if (timer) clearTimeout(timer);
    };
  }, [frame, handle, width, height]);
  return null;
};

// A piece that refuses its input throws (kit3: "kit3 Page ...: mark 1 holds 78% of its crop's ink ..."; standard/KIT3.md). In a render
// that stops the render, as it should. In the gate's probe one refusal would end a whole long probe with a crash; here, in the gate
// mode only, it is caught per frame and logged as `GATE|refusal|{frame, msg}` (gate.py reports each as a named flag with its reason),
// the composition draws nothing on that frame, and the probe goes on. The boundary resets on the next frame.
type BoundaryProps = {frame: number; children: React.ReactNode};
class GateBoundary extends React.Component<BoundaryProps, {err: string | null; frame: number}> {
  state = {err: null as string | null, frame: -1};
  static getDerivedStateFromProps(p: BoundaryProps, s: {err: string | null; frame: number}) {
    return p.frame !== s.frame ? {err: null, frame: p.frame} : null;
  }
  static getDerivedStateFromError(e: unknown) {
    return {err: String((e as Error)?.message || e)};
  }
  componentDidCatch(e: unknown) {
    gateLog('refusal', {frame: this.props.frame, msg: String((e as Error)?.message || e).slice(0, 400)});
  }
  render() {
    return this.state.err ? null : this.props.children;
  }
}
const GateCatch: React.FC<{children: React.ReactNode}> = ({children}) => {
  const frame = useCurrentFrame();
  return <GateBoundary frame={frame}>{children}</GateBoundary>;
};

// every composition is registered as gated(X) in Root.tsx; `pipe.py gate` refuses a composition that isn't
export const gated = <P extends object>(C: React.ComponentType<P>): React.FC<P> => {
  const G: React.FC<P> = (props) => (
    <>
      {gateOn ? <GateCatch><C {...props} /></GateCatch> : <C {...props} />}
      {gateOn ? <GateLayout /> : null}
    </>
  );
  G.displayName = `gated(${C.displayName || C.name || 'Comp'})`;
  return G;
};
