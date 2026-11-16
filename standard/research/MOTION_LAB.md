# Motion lab: what was built, rendered and judged on its frames

*Each test is a Remotion composition, rendered and then read on dense frame sheets (`EDIT tools/qa/draft_sheet.py <render.mp4> <out
prefix> --step 0.25`: four frames a second, each stamped with its time). A technique enters the house kits only after its frames hold
up. The research behind each one: `standard/research/MOTION_CRAFT.md`. Render times are from a mid-range PC (an 8 GB RTX 3060-class
GPU, 16 GB RAM, 6 cores).*

## Lab 1: shader transitions, motion blur, a page in depth
Render: 14.6 s at 1920x1080/60 in ~3 min (`--gl=angle`, the project default).

| Technique | Verdict on the frames | Settings that worked | Notes for the kits |
|---|---|---|---|
| `blurSlide` (whip pan) | **Works.** A real camera whip: the outgoing shot smears sideways, ~4 frames of pure streak, the new shot resolves | 0.4 s (24 frames at 60) | 0.4 s reads slightly long for a whip; test 0.25-0.3 s. One direction per sequence (Hillier-Smith) |
| `zoomBlur` | **Works.** Radial blur dive from one shot into the next | 0.4 s | A "go deeper" move: into a detail, into a flashback |
| `pushCut`, `crossZoom`, `linearBlur` | Rendered; not yet read frame by frame | 0.4 s | Read before use |
| `HtmlInCanvasMotionBlur` | **Works.** A card flying in 0.35 s smears along its path and is sharp the moment it slows; the unblurred copy strobes | 8 samples, 180° shutter, emphasized-decelerate (0.05, 0.7, 0.1, 1) | Wrap every fast move; nothing readable is lost because the text resolves as it settles |
| Page in depth | **Works after one fix.** Tilt (rotateY -14°, rotateX 6°, perspective 1400), progressive blur on the far side (0 -> 6 px from 55% of the width), a two-layer shadow, a key light gradient, a slow push (0.95 -> 1.18 over 4 s) and pan | Capture drawn at 1.32x (1500 px from the 1140-px 2x capture) | **Bug found and fixed:** the page capture's marks (`tools/footage/capture_page.mjs`) are in the capture's 2x pixels, one box per line; the first draft scaled them 2x again and drew one box. Now each line's box sweeps in reading order, in proportion to its width |

**Still missing on the page, to reach fern/LEMMiNO level:** the outlet's real masthead and headline in the capture (the real thing
over a generic one), a softer marker-shaped highlight instead of a hard rectangle, and the framing keeping the whole highlighted phrase
plus a margin in frame at the end of the push (here the page's right edge leaves the frame: fine, but check per capture).

The repo's page component (`tools/motion/src/kit3/page.tsx`, `standard/KIT3.md`) carries what held up here, and it holds the page
still while a mark is lit: the push runs before the first light, never under it.

## Lab 2: punch-ins, a 0.25-s whip on real clips, impact shake, film finish on video, a globe route, a real cursor
Render: 16.85 s at 1920x1080/60 in ~2:45.

| Technique | Verdict on the frames | Notes for the kits |
|---|---|---|
| Punch-in on the word, eased 0.15 s + motion blur | **Works**, but emphasized-decelerate puts ~80% of the move in the first 2-3 frames: it reads as a cut with a settle | That is the feel of the top Short we studied for its zooms (an "instant" punch on the word, `standard/research/STUDY_SHORTS_REFS.md`). For a visible push, use 0.3-0.5 s with a gentler curve |
| Source letterboxing | **Caught:** a maker's launch video used as a source carries black bars; at scale 1 they show, the punch hides them | The QA must flag bars in any source (no letterbox bars on screen); crop or scale at prep, never on screen |
| Globe (d3-geo orthographic + Natural Earth 50m) | **Works:** the route draws Lisbon -> New York as a great circle while the globe turns with it; labels and pulsing pins read | Looks clean but plain: the atmosphere ring is a flat teal band (cheap), the route lies flat. Next: a thin glow falling off outward, light and shade across the sphere, faint borders, the route lifted as an arc with a soft trail (done in lab 3) |
| macOS cursor (`@remotion/mac-cursors`) | **Works:** the real OS arrow glides, presses, rings | At 1.6x it is too small for a TV: show it ~2.5-3x (60-70 px tall at 1080p); the click ring needs more contrast |
| Whip 0.25 s, impact shake, film finish (`noise` + `vignette` on `@remotion/media` Video) | Rendered; to read on their sheets before use | `@remotion/media`'s Video takes `effects`, so a film finish can sit on footage itself |

**Software GL:** `--gl=swangle` renders the HTML-in-canvas transitions and `HtmlInCanvasMotionBlur` correctly (frames checked: a
mid-whip streak and a blurred card in flight), so both GL paths are safe for these. The config defaults to the GPU (`angle`, about
twice as fast per frame); on a PC whose graphics driver resets under the load (a streaming or capture app sharing the GPU fails with
it), switch to `swangle` for good (`tools/motion/remotion.config.ts` says how; `standard/PIPELINE.md`).

## Lab 3: the kit versions
- **Page stage:** works. A marker-shaped highlight (uneven rounded ends, slight tilt, multiply) sweeps each measured line in reading
  order; the real macOS cursor glides in with motion blur and clicks with a two-tone ring. **Bug found and fixed:** the motion-blur
  canvas sat in the page's layout flow and stretched the page to 1,200 px tall (the camera looked at blank paper); it now sits in an
  absolutely positioned layer. Cursor scale raised 2.6 -> 3.4 for TV size.
- **Globe:** works and reads premium: a thin atmosphere falling off outward, light from the upper left with the far side shaded, faint
  borders, routes drawn as flight arcs lifted 0.22 of their chord toward the top, pulsing pins with labels.
- **Motion primitives:** Material 3 easing tokens, a motion-blur wrapper (180°, 8 samples), a shake hook, a punch-in hook, and
  whip / dive / punch cut presets.
