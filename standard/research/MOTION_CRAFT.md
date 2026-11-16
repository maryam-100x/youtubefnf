# Motion craft: what top documentary/commentary channels do, how it's made, how to make it top-tier in code

*The question: what do the top documentary and commentary channels do in motion graphics, how do their makers build it, and how do we
reach that level in code (Remotion + ffmpeg, with Blender and Python where they win)? Grades: A = primary (vendor docs for what a
product does, standards bodies), B = measured by us or a methodical secondary source, C = a practitioner's blog or tutorial, D = vendor
marketing or resellers. Nothing here was rendered or tested when it was researched: every "in the stack" recipe is a build to A/B in
the motion lab (`standard/research/MOTION_LAB.md`) against a reference frame.*

**Limits of this research:**
- **The web-search budget ran out midway.** These stay unsearched: halation recipes, gate-weave amounts, J/L-cut lead lengths, and the
  current prices of Deep Glow 2, Red Giant and Motion Array. Where a number is missing, the text says so.
- **Sites that refused automated fetches:** aescripts.com, toolfarm.com, motionarray.com (403 or Cloudflare), Reddit and its redlib
  mirror (bot check). They were not bypassed.
- **YouTube refused automated downloads** (HTTP 429, then "confirm you're not a bot").
  - The 3 outside reference videos in §7 marked ≈ carry approximate positions from YouTube's automatic frames.
  - The others come from our own frame-by-frame studies and carry measured timestamps or durations.
- **Creator tool claims, publicly sourced only:**
  - Johnny Harris's map tool (GEOlayers in After Effects) and Vox's 12-fps trick have a source.
  - LEMMiNO's, MagnatesMedia's and fern's tools, and those of the top creators we studied, are **not confirmed**. LEMMiNO's 4M Q&A
    shows his app list on screen only; the transcript doesn't name them.

---

## 0. The answer in short
1. **The tool doesn't separate top channels from cheap ones.** What does:
   - real material staged in depth (LEMMiNO's dark void of floating artifacts, fern's tilted pages with focus falloff)
   - one continuous, eased camera with motion blur
   - designed type and colour
   - restraint
   - the real thing or a faithful recreation (the outlet's own logo and type, the platform's own UI), never generic shapes: LEMMiNO keeps
     the real typography of his subject, fern keeps the outlet's own type
2. **The usual fixable gaps of a code-built kit** (measured by us on our own kits before this research):
   - **No motion blur** anywhere (0 uses in `src`).
   - **Flat CSS cards:** tilt without depth of field, light or shadow logic.
   - **Hand-rolled transitions:** 21 Remotion transition presentations were installed and none was used.
   - **No map engine**, no depth-based photo parallax, and no real 3D in a shipped video.
   - Film texture is one SVG grain layer.
3. **Remotion 4.0.53x ships most of what AE plugins sell.** A code-built kit tends to have most of it installed and use almost none of it:
   - `<HtmlInCanvasMotionBlur>` (v4.0.529, "the state-of-the-art recommended way")
   - 21 transitions, among them `blurSlide` (a whip pan), `zoomBlur`, `crossZoom`, `filmBurn` and `pushCut`
   - `@remotion/effects`: about 70 canvas effects (WebGL2/2D) on `<Img>`, `<Video>` and `<HtmlInCanvas>`, among them LUT, glow, chromatic
     aberration, barrel distortion, light leak, zoom blur, progressive blur, corner pin, paper, scanlines and tear
   - three.js through `@remotion/three`, with pmndrs postprocessing for depth of field, bloom and lens distortion
   - maps with MapLibre and turf, with an official agent skill (`remotion-maps`)
   - video matting (MODNet, BEN2) for text behind a subject
4. **Tools:**
   - **Don't buy After Effects or template packs first.** The free stack can reach top-tier if it's built and tested piece by piece
     (§5).
   - **Install Blender** (free) on the day a video needs a white 3D city or a hero 3D object (`standard/3D.md`).
   - **For photo parallax, install torch plus Depth Anything 3 Mono-Large.** It's Apache-2.0. Avoid the CC-BY-NC Depth Anything
     checkpoints on a monetized channel.
   - **Gate test for After Effects + GEOlayers:** one month of AE plus GEOlayers 3 (about $330) only if the code-built maps lose a
     side-by-side against a Johnny Harris map frame.

---

## 1. The stack (inventory)

### 1.1 The Remotion project (`tools/motion`)
- **Remotion 4.0.532** (npm latest was 4.0.535 when this was researched). React 19.1, three 0.178, @react-three/fiber 9.3.
- `remotion.config.ts`: JPEG frames at quality 92, concurrency 6, `--gl=angle` (the GPU).
  - Measured by us: 41 ms against 95 ms a Full frame with software WebGL (an 8 GB RTX 3060-class GPU).
  - Remotion warns that angle can leak memory, so long videos render in parts.

| Package | In `tools/motion/package.json` | What it gives |
|---|---|---|
| `@remotion/motion-blur` 4.0.532 | yes | `<HtmlInCanvasMotionBlur>` (8 samples default, 180° shutter), `<CameraMotionBlur>`, `<Trail>` |
| `@remotion/transitions` 4.0.532 | yes | `TransitionSeries` and 21 presentations: fade, slide, wipe, flip, clockWipe, iris, cube, none, pushCut, blurSlide, bookFlip, crossZoom, crosswarp, dissolve, dreamyZoom, filmBurn, linearBlur, ripple, swap, zoomBlur, zoomInOut (all present in `node_modules/@remotion/transitions/dist/presentations`) |
| `@remotion/paths` | yes | `evolvePath` (line draws, routes), path interpolation |
| `@remotion/shapes` | yes | Shapes that accept effects (from 4.0.474) |
| `@remotion/layout-utils` | yes | `fitText` / `measureText` for type that fits exactly |
| `@remotion/media-utils` | yes | Audio data (visualisers; LEMMiNO's waveforms) |
| `@remotion/noise` | yes | Dust, organic drift |
| `@remotion/three` | yes | r3f in Remotion; `useOffthreadVideoTexture` (footage on 3D planes); `ThreeWebGPUCanvas` (experimental, 4.0.503) |
| `@remotion/media` 4.0.532 | yes | `<Video>` that accepts `effects` (`<OffthreadVideo>` doesn't) |
| `remotion` core | yes | `<Img>` takes `effects` (checked in `remotion/dist/cjs/Img.d.ts`); `<HtmlInCanvas>` is exported |

**Beyond the core.** Each is version-matched to 4.0.532 on npm, checked for `@remotion/effects`.

| Package | Since | In `package.json` | What it gives |
|---|---|---|---|
| `@remotion/effects` | 4.0.464 | yes | ~70 effects, among them `lut` (.cube), `noise`, `vignette`, `glow`, `chromatic-aberration`, `barrel-distortion`, `fisheye`, `zoom-blur`, `linear/radial-progressive-blur`, `region-blur`, `corner-pin`, `light-leak`, `paper`, `halftone`, `scanlines`, `tv-signal-off`, `tear`, `pixel-dissolve`, `shine`, `starburst`, `duotone`, `levels`, `white-balance`, `wave`; custom ones via `createEffect()` (Canvas 2D, WebGL2 or WebGPU) |
| `@remotion/rough-notation` | – | yes | Hand-drawn highlight, underline, circle, box, bracket, strike-through (Remotion's own recommendation for text highlights) |
| `@remotion/mac-cursors` | – | yes | Real macOS cursor components |
| `@remotion/video-matting` | 4.0.523 | no | Separates a video into base and foreground layers on the GPU. Models: MODNet (people, 25.9 MB, Apache-2.0) and BEN2 base (general, 219 MB, MIT) |
| `@remotion/lottie` | – | no | Lottie (After Effects via Bodymovin, LottieFiles) |
| `@remotion/gsap` | 4.0.517 | no | GSAP timelines, deterministic. GSAP is now 100% free (gsap.com/pricing: "free for everyone ... thanks to Webflow"), including CustomEase, SplitText and MorphSVG |
| `@remotion/rive`, `@remotion/skia` | – | no | Rive files; Skia drawing |
| `maplibre-gl` + `@turf/turf` | – | no (`d3-geo`, `topojson-client` and `world-atlas` are) | Map animation, per Remotion's "Maps" doc |

- **Remotion agent skills:** `npx skills add remotion-dev/skills`, 12 skills including `remotion-maps` and `remotion-best-practices`.
- **`@remotion/light-leaks`:** deprecated; use `lightLeak()` from `@remotion/effects`.

**HTML-in-canvas:**
- What it is: draw a live DOM node into a canvas, then shade it with WebGL or WebGPU. It powers the new transitions and the best motion
  blur.
- **Rendering needs nothing.** Remotion ships a Chrome build with the flag on (from 4.0.455), and `--gl=angle` is required for shaders,
  which the config already sets.
- **Studio preview needs Chrome 149+** with `chrome://flags/#canvas-draw-element` on.
- The API is experimental in Chrome and may change (Remotion docs, grade A).

### 1.2 What the kits hold
`tools/motion/src/lib.tsx` (ships with the repo):
- The house timing (`useT`, `kf`) and easings: `easeOut` bezier(0.16,1,0.3,1) expo-like, `easeInOut` (0.65,0,0.35,1), `easeIn`
  (0.7,0,0.84,0).
- `Clip` (OffthreadVideo with edge-safe trims), `Still`/`useMove` (Ken Burns), `useBlurIn` (22 px → 0 in 0.3 s), `Vignette` (radial
  gradient), `Grain` (SVG feTurbulence, reseeded every 2 frames, overlay at 7%), `Dust` (noise2D specks), `Glitch` (RGB split + 7
  slices), `Flash`, `LightBar` (CSS gradient sweep, screen), `Letterbox`.
- Fonts: Anton, Montserrat, Space Grotesk; colours from the brand tokens in `tools/motion/src/brand.ts`.

The shared kits are kit3 (`standard/KIT3.md`), graphics kit 2 (`standard/GRAPHICS_KIT2.md`) and the Shorts kit
(`tools/motion/src/shorts/kitS.tsx`). Before them, per-video kits (not shipped) held these techniques, named here because the catalogue
in §3 points at them as starting points:

| Kit (by job) | Held (technique) |
|---|---|
| Shorts framing kit | `place`/`Cover`/`Back`/`Drift`/`punch` (framing and punch-ins), `Print` (photo prints), a cover-art print, a logo badge, `Bubble`, `FlashIn`, `Bars`, `Tint` |
| Film kit | `ChapterCard`, `Plain`, `QuoteCard`, `HeadlineText` (outlet, kicker, mark), `BigNum`, `SubscribeF`, `Lines` |
| Receipts kit | `Foot`, `BlurBack`, `Cap`, `Pred`, `Receipt` (page with marks), `Photo`, `Punch`, `Count` (counter), `Claim`, `Pop`, `Ring` (callout ellipse), `Corner`, `Line`, `Scrim`, `SignOff` |
| The kit of a long video that performed well | `Archive` (B&W strobe in an old-TV frame, white flash on each change), `PageAlive` (real page, cursor glides and clicks, push-in on the click), `Subtitles`, `Who`, `Card`, `Fit`, `Credit`, `PlaceFill` (number as a place), `WorldLights`, `TitleCard`, `NightMap` |
| Stacks kit | `Card41`, `Deck`/`Column`/`Solo` (stacks of receipts), `Push`, `Ratio` |
| Documentary kit | `YearCard`, `QuoteCard`, `DateDots` (timeline), `HeadcountChart`, `RegionMap` (static map with lit region and zoom), `PhoneCall`, `ChatMsg`, `Calendar`, `ThreeHeads`, `LikeBar`, `StockDay` (line chart), `Strike` |
| Moments kit | `Moment` (clip with lift zoom, cam moves, marks), `NameSubs`, `PageCard` (capture with measured word boxes: yellow multiply highlight on white pages, red screen on dark; cursor click with ring; 1.5% push), `Panels` (side by side), `Lower` |

**The page pipeline is a real asset.** The page capture (`tools/footage/capture_page.mjs`) measures each phrase's box on the real page, so highlights
land on the exact words. That's better than most AE workflows, which draw highlight boxes by hand.

### 1.3 Outside Remotion
- **ffmpeg 8.0.1 full** (gyan.dev):
  - GPU and filters: libplacebo, Vulkan, OpenCL, CUDA/NVENC
  - film-look and lens filters: frei0r, lensfun, `lenscorrection`, `displace`, `dblur`, `gblur`, `noise`, `vignette`, `lut3d`, `haldclut`, `rgbashift`, `chromashift`, `tmix`, `v360`, `xfade`
- **DaVinci Resolve 21.1 free.** The free version has no motion-blur effects and lacks "multiple Resolve FX" and the noise reduction;
  those are Studio, $295 one-time (Blackmagic 21.1 readme, A). Fusion is included.
- **Blender:** installed on the day a video needs it, never kept around: the official 5.2.2 LTS zip, 404 MB.
- **Python:** the pipeline needs no torch; depth models need a torch CUDA install (multi-GB). onnxruntime runs ONNX models without it.
  ImageMagick and yt-dlp are the other helpers.

### 1.4 Missing, ranked by how much it would lift quality
| # | Gap | Why it matters (evidence) | Fix in the stack | Size |
|---|---|---|---|---|
| 1 | **Motion blur** on everything that moves fast | The standard film look (180° shutter); AE turns it on per layer; "easing and motion blur" are the two named amateur-vs-pro markers (Noble Desktop, C) | `<HtmlInCanvasMotionBlur>` around moving groups; `disabled` keyframed off on holds | Low |
| 2 | **Documents in real depth** (tilt + focus falloff + light) | LEMMiNO 0:08-0:13 and fern (documents sit on a tilted plane with focus falloff; measured by us, B) | CSS 3D or a three.js plane, plus `linear-progressive-blur` or `TiltShiftEffect`, a soft key light and a two-layer shadow | Low-Med |
| 3 | **A transition set** with blur and camera logic | Vox's camera-move + blur transition (PremiumBeat, C); fern's push through an address bar; LEMMiNO's defocus dissolves | `TransitionSeries` + `blurSlide`/`zoomBlur`/`crossZoom`/`pushCut`/`linearBlur` + our own | Low |
| 4 | **A map engine** (vector + tiles + globe) | Johnny Harris, Vox, LEMMiNO (2:58, 16:31), SunnyV2 (a number as a place), a top creator we studied (country outlines as scale anchors) | d3-geo + Natural Earth; MapLibre + turf; Google Earth Studio for satellite | Med |
| 5 | **Depth parallax on stills** | The documentary standard for photos with no footage | DA3MONO-LARGE depth → three.js displaced mesh or DepthFlow; or layered cut-outs | Med |
| 6 | **A 3D stage** (artifacts floating in a void, footage on screens) | LEMMiNO's whole look; fern's 3D rooms; a top creator's white 3D city | r3f + `useOffthreadVideoTexture` + postprocessing DOF/bloom; Blender for the city | Med-High |
| 7 | **A finishing pass** (LUT, luminance-aware grain, halation, gate weave) | Grain, halation, bloom and weave are "the film look" (ProVideo Coalition review via search, C) | `@remotion/effects` lut/noise/glow, or an ffmpeg chain on the master | Low-Med |
| 8 | **Hand-drawn annotation variety** (circle, underline, strike) | Remotion's own recommendation; fern's highlights are recolours, not boxes | `@remotion/rough-notation` | Low |

---

## 2. Premium vs cheap: the principles, with numbers
| # | Principle | The number | Source (grade) | Check in the build |
|---|---|---|---|---|
| 1 | **Never linear; decelerate into rest** | Material 3 "emphasized" bezier(0.2,0,0,1); emphasized-decelerate (0.05,0.7,0.1,1) for entrances; emphasized-accelerate (0.3,0,0.8,0.15) for exits; standard (0.2,0,0,1) | Material Web token source `_md-sys-motion.scss` (A) | `lib.tsx`'s `easeOut` (0.16,1,0.3,1) is a strong expo-out, good for entrances. There is no dedicated exit curve: use accelerate for exits |
| 2 | **Pronounced eases, not defaults** | AE's Easy Ease is a mild 33% influence; tutors push it to ~70% "for a more extreme curve" | Bring Your Own Laptop course (C) | Fine: the house curves are already strong |
| 3 | **Duration scales with distance and size** | Material tokens: short 50-200 ms (small parts), medium 250-400 ms (cards), long 450-600 ms, extra-long 700-1000 ms (full-screen). At 60 fps: a card 15-24 frames, a full-frame move 27-60 | `_md-sys-motion.scss` (A, built for UI; a starting scale for video) | Most moves sit at 0.3-0.5 s. Check big moves aren't rushed |
| 4 | **Exits faster than entrances** | Accelerate curves exist because exits get out of the way; Material pairs them with shorter durations | Material token family (A); duration pairing is UI convention (C) | Make it systematic |
| 5 | **Motion blur on fast movement, not on reading** | 180° shutter is the film default; AE's defaults are 180° and 16 samples per frame; Remotion recommends 5-10 samples for CameraMotionBlur; too much blur makes small UI-like layouts "soft or hard to read" | Remotion docs (A); Creative Cow 2009 + ProVideo Coalition (C); Jake in Motion docs (C) | Wrap moving groups (H3) |
| 6 | **Offsets, not unison** | Secondary elements settle 4-8 frames after the primary; 2-4 frames of anticipation before a reveal | An animation-principles skill page (C-, unsourced; treat as a starting point to test) | Staggered panels do it; extend it |
| 7 | **Never static** | Every still drifts, pushes or pans; the references hold long only when things change on them (LEMMiNO: ~14 graphic states a minute with 2.1 hard cuts a minute) | Measured by us on the reference videos (B) | `Drift`, the 1.5% push on a page card |
| 8 | **Text holds long enough to read** | Netflix English: 20 characters a second for adults, 42 per line, 2 lines. So a 60-character headline needs ≥ 3 s if it must be read in full | Netflix guide via two secondary pages (C; Netflix's own page not retrieved) | Check on every card |
| 9 | **Inside the safe areas** | Title-safe 90%, action-safe 93% (SMPTE ST 2046-1; Netflix's graphics guide). At 1920×1080 the title-safe margin is 96 px left/right and 54 px top/bottom | SMPTE via NAB + Netflix (A/B) | Not checked automatically yet |
| 10 | **Character through frame rate and texture, used on purpose** | Vox animates some graphics at 12 fps inside a 24-fps edit ("on twos"); backgrounds "boil" with 2-3 texture swaps a second | PremiumBeat 2021-03-08 (C) | A choice for a paper/collage section, not everywhere |
| 11 | **Real over generic** | The real thing or a faithful recreation of it (the outlet's own logo and type, the platform's own UI); a generic shape (an oval with a date inside) reads cheap | The references (LEMMiNO's and fern's real typography, row 13) and the house standard (`standard/LONG_FORM.md`) | Generic shapes (`Pop`, `Ring`, icon chips) are the risk in any kit |
| 12 | **Graphics graded into the footage** | Text "slapped on" is the named failure; match colour temperature to the footage | A YouTube summary page (C) | Graphics sitting in their own palette with no per-shot match is the gap |
| 13 | **Depth in every frame** | LEMMiNO's cards are tilted 3-8° with one side out of focus; fern's pages sit on a tilted plane with focus falloff; a top creator we studied blurs cut-outs by depth | Measured by us (B) | Tilt without focus falloff is the gap |
| 14 | **One camera through one space** | LEMMiNO: "The whole video feels like one camera moving through one space"; most picture changes happen inside continuous moves | Measured by us (B) | Cutting between flat cards is the gap |
| 15 | **Restraint: one transition language per source type, effects on structure only** | Glitch for time jumps, white-through for documents, hard cuts on the beat; LEMMiNO uses one glitch in 18 minutes, at 10:16 (the most replayed moment after the opening, 0.737) | Measured by us across the reference videos (B) | Partly |

**Type rules, observed but not measured with a source:**
- **One family carries the video, a second at most.** LEMMiNO keeps his subject's real typography; fern keeps the outlet's own type on grey.
- **Read close-ups are huge:** LEMMiNO pushes in until the text is 350 px tall (10:37).
- **fern has text on 94% of frames**, so legibility is the job.
- **No size standard for phone legibility** turned up before the search budget ran out. Set the size by testing at 1080p and 4K on the
  screen the videos are reviewed on.

---

## 3. The technique catalogue
Each entry has five parts: **what / where** · **how pros make it** · **top-tier in the stack** · **difficulty** · **starting points**.
Reference timestamps and durations are from our measured studies unless marked ≈.

### A. Stills and photos

**A1. 2.5D photo parallax (depth on a still)**
- **What / where:**
  - A photo becomes a shot: the subject separates from the background and the camera dollies or pushes.
  - It's the documentary answer to "no footage exists".
  - MagnatesMedia's cut-out people over textured backdrops (≈17:08 and ≈34:17 in "Why Netflix is Collapsing"); a top creator we
    studied opens on a 1.4 s parade of cut-outs.
- **How pros make it:**
  - Photoshop: cut the photo into at least 3 planes (fore, mid, back) and fill the holes with Clone Stamp or Content-Aware Fill.
  - After Effects: import as 3D layers, add a 3D camera, ease the keyframes (Adobe's tutorial and Motion Array, C).
  - The paid "one-click" route is Immersity-style depth tools.
- **In the stack, top-tier:** two routes, chosen per photo.
  - **(a) Layered cut-outs (cleanest):**
    1. Subject matte from BEN2 (`@remotion/video-matting`'s model, MIT) or rembg.
    2. Fill the background holes with OpenCV inpainting (Telea/NS, classical, no generated content). For bigger holes LaMa
       (Apache-2.0) is an AI fill: generated content, so the house rules on AI pictures and the creator decide; keep camera travel
       small so little fill is ever seen.
    3. Planes in r3f with a real perspective camera, `DepthOfFieldEffect`, and motion blur during the move.
  - **(b) Depth mesh (fast, organic):**
    1. Depth map from **Depth Anything 3 Mono-Large** (`DA3MONO-LARGE`, 0.35B, **Apache-2.0**; DA3 repo, A).
    2. A subdivided plane (e.g. 512×288 segments) with the depth as `displacementMap` in three.js, the camera on a short eased dolly.
    3. Or **DepthFlow** (ray-marched GLSL; AGPL-3.0, v1.0.1, actively maintained). It claims 8k50 on an RTX 3060 (vendor claim, D) and
       has vignette, DOF and lens distortion built in.
- **The tell is edge stretching.** Keep the dolly short (start at ~3% of frame width, our proposal to test), add grain and a slight DOF.
- **Licences:**
  - DA v2 Small and DA3 Base/Small/Mono-Large/Metric-Large are Apache-2.0.
  - **DA v2 Base/Large/Giant and DA3 Large/Giant/Nested are CC-BY-NC-4.0: not for a monetized channel.**
  - Video Depth Anything has a 28.4M Small model for temporally stable depth on video.
- **Difficulty:** Medium (one install day: torch CUDA, the model, a test).
- **Starting points:** 2D Ken Burns (`Still`/`useMove`, `Drift`), print and cover-art cut-outs. No depth.

**A2. Photo stacks**
- **What / where:** Prints land on a pile, each slightly rotated, with a shadow. A top creator we studied uses crumpled headlines; the
  stacks kit's `Deck`.
- **How pros make it:** AE: 3D layers with drop shadows, rotation ±3-8°, a texture overlay.
- **In the stack, top-tier:**
  - Real print borders: a white border and a paper texture (`@remotion/effects` `paper`, or a CC0 scan).
  - A light gradient across each print, a two-layer shadow (contact + ambient), a settle of 4-8 frames after landing.
  - Motion blur on the drop, DOF on the lower prints.
- **Difficulty:** Low. **Starting points:** `Print`, `Deck`, `Column`, `Solo`.

**A3. Ken Burns with blur / B&W → colour on the name / archival strobe in a CRT**
- **What / where:**
  - A top creator we studied switches colour on at the word (a 10 s B&W stretch that turns to colour on the name).
  - Two top creators we studied open on B&W in an old TV, 0.1-0.2 s each, flashes between (a 4 s and a 17 s run).
  - Johnny Harris-style photo slides: an eased move plus a fading Gaussian blur and a projector sound (Motion Array, C).
- **In the stack, top-tier:**
  - Already built once (`Archive`, `useBlurIn`).
  - Upgrade the TV with `@remotion/effects` `barrel-distortion` + `scanlines` + `chromatic-aberration` (a real tube curve instead of
    a flat rounded mask), plus a real-glass reflection layer.
- **Difficulty:** Low. **Starting points:** most of it.

### B. Maps

**B1. Animated maps: routes, zooms, borders, globe (Johnny Harris / Vox style)**
- **What / where:**
  - Vox "Why all world maps are wrong": projection shapes on paper-white with letter-spaced caps (≈3:00, the Gall-Peters frame).
  - LEMMiNO: a grey world map with red dots (2:58-3:10, 7:02-7:09); dark street maps with POSTER/AIRPORT pins joined by yellow routes
    (16:31-16:52).
  - A top creator we studied: real country outlines laid beside the area the video is about, each with its km² (9 s).
  - SunnyV2: a number as a place.
- **How pros make it:**
  - **Johnny Harris:** After Effects + **GEOlayers 3**. His own tutorial says "I make maps using this AE Plugin" and links GEOlayers
    (aescripts learn page via search, C). Jason Boone animated maps for the channel and calls GEOlayers "one of the main map creation
    tools in AE" (PremiumBeat 2022-03-24, C).
  - **Google Earth Studio** for satellite flyovers: track points export as 3D data, and a script builds the AE project with a camera
    and null layers (same article).
  - Styles come from Mapbox or MapTiler.
- **In the stack, top-tier:** three tiers, picked by the shot.
  1. **Designed vector maps:** the most "Vox".
     - d3-geo projections, including orthographic for a globe and projection interpolation for a morph.
     - Natural Earth shapes (public domain).
     - `@remotion/paths` `evolvePath` for routes and borders drawing on.
     - Paper texture plus a grain boil for the Vox paper look.
     - Full control of palette and type.
  2. **Tile maps:** MapLibre GL + OpenFreeMap (no key, no limits).
     - Attribution "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" on screen (secondary sources, C).
     - Or MapTiler, or Mapbox (key; globe and 3D buildings).
     - Turf for great-circle routes.
     - The camera is set per frame with `jumpTo` (Remotion "Maps" doc, A; the `remotion-maps` skill compares the options).
  3. **Satellite flyovers:** Google Earth Studio.
     - **Allowed:** "news broadcasts, television shows, films, documentaries ... online video (e.g. YouTube) primarily for educational,
       instructional, recreational, or entertainment purposes", with "Google Earth" on screen for the whole shot.
     - **Not allowed:** ads or promotional use, so never in a sponsor read (Google Geo Guidelines, A).
     - It runs in Chrome under the creator's Google account: the chat writes the camera path, the creator (or computer use) renders it.
     - CesiumJS is the code alternative. Google's photorealistic 3D-tiles licence for rendered video is unverified.
- **Real places vs made-up maps:** a real place's map is fine from OSM data (with its attribution). A fictional or proprietary map (a
  novel's map art, a theme park's or a transit network's own map) needs licence-safe art: the owner's own published version, never
  leaked material.
- **Difficulty:** Medium (each tier is a few days to get premium).
- **Starting points:** `RegionMap`, `NightMap`, `WorldLights`, `PlaceFill` (all image or SVG based; no engine), and kit3's map parts
  (`standard/KIT3.md`).

**B2. The white 3D city**
- **What / where:** a top creator we studied flies over a white clay model of a city for 22 s, and the model recurs through the video.
- **How pros make it:** Blender with OSM buildings (or Cinema 4D), a clay material, soft sky light. Tools unconfirmed.
- **In the stack, top-tier** (`standard/3D.md`):
  - Install Blender 5.2.2 LTS (404 MB zip).
  - An OSM extract of the city → buildings extruded by height: a Python OSM import in bpy, or a GIS add-on (versions unverified).
  - White principled material, sun + sky, EEVEE or Cycles OptiX.
  - The camera path from a script; render a PNG sequence and grade it in Remotion.
- **Difficulty:** High. **Starting points:** none.

### C. Documents, posts, pages

**C1. Article / post callouts (highlighter, punch-in, 3D tilt, paper, cursor clicks)**
- **What / where:**
  - **fern:** headline cards with the outlet's logo on grey, the key phrase highlighted (38:15, 40:46.8). A push-in while a blue
    highlight follows the words read (31:39-31:43.8), then an extreme close-up where only "was absolutely lovely" is lit (31:48.4-31:51.4).
  - **LEMMiNO:** pages tilted 3-8°, one side out of focus, drifting sideways; a push until the text is 350 px tall (10:37-10:39).
    Highlights are recolours, not boxes.
  - **A top creator we studied:** a hard cut to a ~3× close-up while the highlight sweeps word by word and the camera follows its head
    (1.3 s).
  - **Another:** the real page alive, a cursor clicks the video on it, the view count rolls (11 s).
  - **Another:** cards drop in (0.4 s) and leave upward (0.4 s), about 4 s apart.
- **How pros make it:** AE: the screenshot as a 3D layer; a camera with depth of field; a highlight shape with a multiply blend or a
  track matte; a cursor layer; a paper-texture overlay.
- **In the stack, top-tier:** keep the page capture (exact word boxes) and add five things.
  1. **Real depth:** CSS `perspective` with rotateY 6-12° and rotateX 3-6°, with `linear-progressive-blur` (`@remotion/effects`, a
     blur whose radius changes across a two-stop gradient), so one side falls out of focus. Or the page on a three.js plane with
     `TiltShiftEffect`/`DepthOfFieldEffect` for a true focal plane.
  2. **Camera follow:** the camera's x follows the highlight's leading edge with an eased lag, and the push ends on the close-up
     (LEMMiNO).
  3. **Annotation variety:** `@remotion/rough-notation` (Highlight, Underline, Circle, StrikeThrough, Bracket) next to the flat
     highlighter, picked per source (a clean newspaper gets a clean marker).
  4. **Cursor:** `@remotion/mac-cursors` (the real OS cursor, a faithful recreation) on an eased path with a slight overshoot; press
     scale ~0.88 for 2-4 frames; a ring; motion blur while it travels.
  5. **Light:** a soft gradient across the page as if lit from one side; contact + ambient shadow; a faint `paper` texture on printed
     sources only.
  - Posts: the real UI from capture, never a generic card (real over generic, §2 row 11).
- **Difficulty:** Low-Medium. **Starting points:** `PageCard`, `Receipt`, `PageAlive`, `HeadlineText`, `ChatMsg`, `PhoneCall`,
  `QuoteCard`, and kit3's page parts (`standard/KIT3.md`).

**C2. Headline machine-gun / wall of posts**
- **What / where:** a top creator we studied opens with 2.2 s of headlines, one every 0.2-0.4 s on crumpled paper; Barely Sociable's
  wordless opener (1:20.8-3:15.1, heatmap peak 1:39-1:55 = 1.000).
- **In the stack:**
  - A sequence of real captures (never invented headlines).
  - Each lands with a 2-frame flash or a hard cut, with a slight rotation and paper.
  - Under 0.4 s each, so only the highlighted name needs to read.
- **Difficulty:** Low. **Starting points:** the parts.

### D. Type

**D1. Kinetic typography and title cards**
- **What / where:**
  - A top creator we studied: a slam banner, scale 5→1 in 0.6 s ease-out, then a slow shrink (1.9 s in all).
  - Another: black title cards on turns ("However", "In fact") and role labels on clips.
  - Another: a blur-in date card (0.4 s).
  - Part cards ("PART N" + a two-line title); Barely Sociable's chapter cards (15:27-15:51, 21:45-22:10).
  - A word-by-word card that slides off to reveal the footage (1.2 s).
- **How pros make it:** AE text animators (per-character range selectors), or preset packs (Motion Bro, AEJuice).
- **In the stack, top-tier:**
  - Words timed to the measured voice (word stamps).
  - `fitText`/`measureText` (`@remotion/layout-utils`) for exact fits.
  - Per-word or per-character reveals: mask (overflow hidden, y 100%→0), opacity, 8-12 px blur → 0, staggered 1-2 frames,
    emphasized-decelerate.
  - Variable-font weight or tracking animation for emphasis.
  - Motion blur on slams.
  - **Text behind the subject:** a matte from `@remotion/video-matting` (MODNet for people, BEN2 for objects), with the title between
    the background and the matte. MagnatesMedia's "VIDEO TAPES" type sits behind the person's head (≈17:08).
  - GSAP SplitText via `@remotion/gsap` if per-character choreography gets complex.
- **Difficulty:** Low. **Starting points:** `TitleCard`, `ChapterCard`, `Punch`, `Line`, `YearCard`, `Lower`, `Plain`.

### E. Data

**E1. Timelines**
- **What / where:** a dated line the camera travels along; a top creator we studied gives each year its own beat over ~3 minutes.
- **In the stack:**
  - The line draws with `evolvePath`; nodes pop with a spring (with overshoot) on their word.
  - Each date in tabular figures; a photo hangs at each node.
  - The camera pans with an eased lag and motion blur.
  - A "now" marker can glow (`glow`).
- **Difficulty:** Low. **Starting points:** `DateDots`, `Calendar`, `Strike`.

**E2. Number animations (counters, bars, tallies)**
- **What / where:**
  - A top creator we studied runs one counter through a whole argument (110 → 28.5 → 13.48 across ~2 minutes) and shows ranked bars
    with the outlier last.
  - Another rolls a year counter through the years in 2.1 s.
  - Another punches in on a small on-screen number in 0.35 s.
- **In the stack:**
  - Ease-out counters with tabular figures (`font-variant-numeric: tabular-nums`) so digits don't jitter.
  - An odometer roll per digit, with motion blur on the roll.
  - Bars that grow with a slight overshoot and stagger; a unit and an anchor ("= Switzerland"); a source line.
- **Difficulty:** Low. **Starting points:** `Count`, `BigNum`, `LikeBar`, `StockDay`, `HeadcountChart`, `Ratio`, `PlaceFill`.

### F. Screen

**F1. Picture-in-picture**
- **What / where:** a clip inset over its own blurred copy (streams, reactions, a post's video).
- **In the stack:**
  - Rounded corners, a thin 1 px light border, a two-layer shadow, a 2-4° tilt with DOF on the backdrop.
  - Enter with motion blur. Colour-match the inset to the scene.
- **Difficulty:** Low. **Starting points:** `BlurBack`, `Fit`, `Card`, `Panels`.

**F2. Screen-recording zooms**
- **What / where:** a recording zooms 1.5-2.5× toward the cursor and back (Screen-Studio style); a top creator we studied opens on a
  mock search page that types with keyboard clicks (6 s).
- **In the stack:**
  - Record real pages with Playwright video, or capture stills and animate.
  - The camera follows the cursor with an eased lag; motion blur during the zoom; typing timed with the sound.
- **Difficulty:** Low-Medium. **Starting points:** `PageAlive`.

### G. Film and texture

**G1. Grain, halation, light leaks, gate weave, LUT, vignette**
- **What / where:** the "film look is mostly grain, halation, bloom, and weave" (a review via search, C). Halation is the red-orange glow
  around bright lights and contrasty edges (Dehancer's feature page, D).
- **How pros make it:** Dehancer or FilmConvert plug-ins, or node by node in Resolve. A cinematographer notes each part "can all be done
  individually on separate nodes" (Reddit via search, D).
- **In the stack, top-tier:** a finishing layer over the whole video, under the text graphics.
  - **LUT:** `lut()` from `@remotion/effects` (.cube, 4.0.526), or ffmpeg `lut3d` on the master.
  - **Grain:**
    - `noise()`/`white-noise()` in `@remotion/effects`, animated every frame.
    - Or ffmpeg `noise=alls=…:allf=t` on the master.
    - Better still, real scanned grain plates overlaid (licence to check per pack).
    - The SVG grain in `lib.tsx` reseeds every 2 frames at 7% and is **not luminance-aware**; real grain is strongest in the mids.
  - **Halation:** threshold the highlights → large blur → tint red-orange → screen back at 10-20%. Build it as a `createEffect()`
    shader, or in ffmpeg (`split`, `lutyuv` threshold, `gblur`, `colorchannelmixer`, `blend=screen`). Our recipe from first
    principles, untested.
  - **Light leaks:** `lightLeak()` (seeded shapes, hue shift) on transitions only.
  - **Gate weave:** a per-frame low-frequency translate of about ±0.5-1.5 px and ±0.05° from `noise2D` (our proposal, untested; no
    source before the budget ran out). For archival or "film" sections only, never on UI recreations.
  - **Vignette:** `vignette()`; the one in `lib.tsx` is a CSS radial gradient.
- **Rule:** subtle. Check at 100% on the review screen; the effect should be felt, not seen.
- **Difficulty:** Low-Medium. **Starting points:** `Grain`, `Vignette`, `Dust`, `LightBar`, `Letterbox`.

**G2. CRT / VHS / archival**
- **What / where:** two top creators we studied (old TV frames); a VHS rewind (0.6 s); Nexpo's rewind glitch into "Something is
  wrong." (14:46-15:15).
- **In the stack:**
  - `barrel-distortion` + `scanlines` + `chromatic-aberration` + `tv-signal-off` (`@remotion/effects`).
  - Reverse playback for rewinds, plus the `Archive` frame.
- **Difficulty:** Low. **Starting points:** `Archive`.

### H. Lens and camera

**H1. Glitch**
- **What / where:** a top creator we studied (0.6 s of 2-frame RGB splits, then a block glitch cut); LEMMiNO's single glitch at 10:16
  (the most replayed moment after the opening); fern's logo glitch (2:05.0-2:07.3).
- **In the stack:**
  - Keep `Glitch` (RGB split + slices).
  - Add `tear`, `pixel-dissolve`, `chromatic-aberration` and `tv-signal-off` from `@remotion/effects`, or a custom HTML-in-canvas
    shader (Remotion has a "glitch effect" prompt in its gallery).
  - 2-6 frames, on structure only.
- **Difficulty:** Low. **Starting points:** `Glitch`, `GlitchFilters`.

**H2. Lens distortion and chromatic aberration**
- **Where:** on whip and zoom transitions, 3D scenes, and CRTs.
- **In the stack:** `barrel-distortion`, `fisheye`, `zoom-blur`, `chromatic-aberration` (`@remotion/effects`); pmndrs
  `LensDistortionEffect` and `ChromaticAberrationEffect` in three.js; ffmpeg `lenscorrection` on footage.
- **Difficulty:** Low. **Starting points:** none.

**H3. Motion blur**
- **What / where:** everywhere fast things move in the references: AE's per-layer switch, 180° shutter.
- **In the stack:**
  - `<HtmlInCanvasMotionBlur width height samples={8} shutterAngle={180}>` around moving groups (renders with no setup; `disabled`
    can be keyframed off during holds).
  - `<CameraMotionBlur>` as the fallback: 5-10 samples, "destructive to colors" at high counts.
  - Every animated component must call `useCurrentFrame()` **inside** the blur wrapper (Remotion's "common mistake" page). Components
    that call `useT()` inside themselves are fine; check any parent that computes motion and passes it down.
  - Cost: ~N samples × the layer's render cost (our estimate, to measure).
- **Difficulty:** Low. **Starting points:** none.

**H4. Camera shake**
- **Where:** impacts (slams, booms), handheld feel on stills.
- **In the stack:** `noise2D` drives x/y/rotation with an envelope: 6-12 frames decaying on an impact; constant micro-drift of 1-3 px on
  "handheld" stills (our proposal, to tune by eye). Never constant hard shake. Add motion blur during big shakes.
- **Difficulty:** Low. **Starting points:** none (`Drift` is smooth).

**H5. Depth of field**
- **What / where:** a top creator we studied blurs the near cut-outs; LEMMiNO's tilted cards; fern's bokeh focus pull with a pixel-grid
  dissolve (2:08.0-2:09.5).
- **In the stack:**
  - Flat layers: per-layer CSS blur by depth, or `linear/radial-progressive-blur`.
  - Photos: depth-map-driven blur (DA3 depth into a `createEffect` shader).
  - 3D: pmndrs `DepthOfFieldEffect`/`BokehEffect`/`TiltShiftEffect`.
  - Focus pulls are animated between subjects on the word.
- **Difficulty:** Low-Medium. **Starting points:** CSS blur only.

### I. 3D

**I1. 3D objects and the 3D void**
- **What / where:** LEMMiNO's dark grey void where the real artifacts float and turn a few degrees a second, with the camera pulling
  back to reveal more windows (0:05.6-0:31.4); fern's meme drawings in 3D rooms (1:59.0-2:00.9); a top creator's white 3D city (B2).
- **How pros make it:** Cinema 4D or Blender for hero objects; AE's camera with Element 3D or native 3D for cards. AE 26.0 (2026-01)
  added a parametric mesh tool and shadow-casting lights; 26.3 (2026-06) added depth of field to its Advanced 3D renderer (Adobe
  "What's new", A).
- **In the stack, top-tier** (`standard/3D.md`):
  - **r3f inside Remotion for cards, screens and simple objects:**
    - the real captures as textures on thin boxes (rounded geometry)
    - footage on screens via `useOffthreadVideoTexture`
    - HDRI lighting (Poly Haven CC0)
    - postprocessing `DepthOfFieldEffect`, `BloomEffect`, `SMAAEffect`, `NoiseEffect`, `VignetteEffect`, `ToneMappingEffect`
    - a slow, continuous, eased camera
  - **Blender (bpy, headless `blender -b -P script.py`)** for anything needing real light transport (a city model, a product, a glossy
    logo): render RGBA PNG sequences, composite in Remotion.
  - A "dark room with glowing screens" test scene is a good first build.
- **Difficulty:** Medium (r3f) / High (Blender). **Starting points:** a 3D test scene and a globe test.

### J. Masking reveals
- **What / where:** footage inside letters, shapes wiping on, a line drawing a border, a page revealed by a hand-drawn stroke.
- **In the stack:**
  - CSS `clip-path` and SVG masks animated with `@remotion/paths`; `@remotion/shapes` shapes as masks.
  - Text as a mask (`background-clip: text` with video, or an SVG mask).
  - `iris()`, `wipe()`, `clockWipe()` presentations; GSAP MorphSVG for shape morphs (free).
- **Difficulty:** Low. **Starting points:** clip-path slices inside `Glitch` only.

### K. Transitions
| Transition | Where (reference) | In the stack |
|---|---|---|
| **Whip pan** | fast pans between scenes (Vox, documentaries) | `blurSlide()` (4.0.523, "whips both scenes in one direction with a heavy motion blur, like a fast camera pan"), or `linearBlur()` |
| **Zoom-through** | fern pushes through the IE address bar (4:10.5-4:11.9); a top creator we studied dives the camera into the next shot | `zoomBlur()`, `crossZoom()`, `zoomInOut()`; better, a real push *into* an object in the next shot (scale 1→8 on the address bar, then cut on the blur peak) |
| **Defocus / camera-move dissolve** | LEMMiNO between the void and the outside world; a top creator's CRT bokeh dissolve; Vox's backward camera move with a blur peaking on the cut (PremiumBeat) | Both sides blurred, peaking on the cut, plus a camera move through the edit (our build); `linearBlur()` |
| **Mask wipes** | shape follows a subject | `wipe()`, `iris()`, `clockWipe()`, custom SVG masks |
| **Light leak** | between warm or nostalgic scenes | `lightLeak()` on the cut |
| **Flash / dip** | a white strobe on archival changes; a 0.8 s dip to black; the house white flash on a change | `Flash` (in `lib.tsx`), `pushCut()` (4.0.500: punch-in on both scenes + a brief flash), dip to black |
| **Glitch cut** | time jumps (a top creator we studied) | `Glitch` + effects |
| **Film burn** | archival or film sections | `filmBurn()` |
| **Match cut** | same shape or word across two shots | Edit choice: align the subject position across the cut |
| **J/L cuts** | the next scene's sound leads the picture (J) or the last scene's sound trails (L) | Done in the sound and mix tools (`tools/sound`), not Remotion. Lead length: no source before the budget ran out. Measure it in reference videos |

**Rules for transitions:**
- **One language per source type** (measured by us across the reference videos).
- **Most changes are hard cuts.** The shader transitions are seasoning: a few a minute at most (our reading of our reference studies).
- Every HTML-in-canvas transition (blurSlide, zoomBlur, crossZoom, filmBurn, crosswarp, dissolve, dreamyZoom, linearBlur, ripple, swap,
  bookFlip, zoomInOut) **renders** without setup, but shows in Studio only with the Chrome flag.

---

## 4. Tools: what pros use, prices, and buy/skip
Prices as read when this was researched (2026).

| Tool | What it is | Price (source, grade) | Scriptable by an AI? | Verdict |
|---|---|---|---|---|
| **After Effects** | The industry standard for motion graphics | **US$22.99/mo** (annual plan billed monthly); Creative Cloud Pro US$34.99/mo promo, US$69.99 regular (adobe.com, A). EU prices not read | Yes: ExtendScript (.jsx) builds comps, layers, keyframes, eases and effects; `aerender` CLI; **nexrender** (MIT, active 2026-06) renders JSON jobs | **Skip first; gate test** (§5) |
| **GEOlayers 3** (AE) | Map tiles, routes, globe, terrain inside AE | **$329.99** single user (aescripts via several listings; the page itself refused the fetch, C); GEOlayers 2 → 3 upgrade $205; map data from MapTiler (6 months included per Toolfarm, C) | Through AE scripting | Only if the map gate fails |
| **Google Earth Studio** | Satellite flyovers in Chrome | Free; documentaries and YouTube allowed with "Google Earth" on screen; no ads (Google, A) | Camera paths can be written; rendering is in the browser UI | **Use** for satellite shots |
| **Saber** (Video Copilot) | Glow and energy strokes | Free (C) | AE only | Skip (`glow` + shaders) |
| **Deep Glow 2** | Physically-based glow | Not confirmed; v1 was $49.95 (aescripts cache, C) | AE only | Skip |
| **Element 3D** | 3D models in AE | **$199.95** (videocopilot.net, A) | AE only | Skip (r3f / Blender do it better) |
| **Red Giant** (Trapcode, Universe, Magic Bullet) | Particles, looks, transitions | $599/yr at launch (2020-era press, C; current price not confirmed). Maxon trial 14 days | AE/Premiere/Resolve | Skip |
| **Motion Bro** | Preset packs inside AE/Premiere | Free extension; packs $59 personal / $118 commercial up to $160 / $320 bundles (motionbro.com, 15% off shown, A) | AE/Premiere only | Skip (generic presets: the real-over-generic risk, §2 row 11) |
| **AEJuice** | Preset packs | Plans from $7 to $83.25/mo, plus lifetime tiers (aejuice.com) | AE/Premiere | Skip |
| **Envato** (Elements) | Templates, stock, music | Core €14.50/mo billed yearly or €29 monthly; Plus €33/€49. Per-project licence; new projects need an active subscription (elements.envato.com, A) | Templates need AE/Premiere | Skip for motion; maybe for SFX |
| **Motion Array** | Templates, stock | Not read (403) | AE/Premiere | Skip |
| **DaVinci Resolve / Fusion** | Edit, colour, node compositing | Free (21.1); Studio $295 one-time adds motion blur, more ResolveFX, noise reduction (Blackmagic readme, A) | Python/Lua scripting | Keep for colour checks; not the motion engine |
| **Blender 5.2** | 3D: modelling, EEVEE, Cycles, geometry nodes | Free | **Fully**: `blender -b -P script.py` | **Install on the day** (city, hero objects) |
| **Cavalry** | Procedural 2D motion (rigs, Lottie export) | **Now free for individuals** ("Cavalry by Canva", needs a Canva account) (cavalry.scenegroup.co, A) | Scripting and command-line rendering not checked | Skip (Remotion covers it) |
| **Rive** | Interactive vector animation | Free tier can't export .riv; Cadet ~$9/seat/mo yearly (aggregators, C) | – | Skip |
| **Motion Canvas** | Code animation (TypeScript) | Free MIT; last push 2026-07-02 | Yes | Skip (Remotion is ahead) |
| **Lottie / LottieFiles** | Vector animations from AE | Free (`@remotion/lottie`) | – | Use for small icons only if they pass real-over-generic |
| **DepthFlow** | Image → parallax video (GLSL) | Free, AGPL-3.0 (local tool use is fine), v1.0.1 | Python CLI | **Test** in the motion lab |
| **Depth Anything 3** | Depth maps | Free; **Mono-Large Apache-2.0** | Python (torch) | **Use DA3MONO-LARGE** |
| **pmndrs postprocessing** | DOF, bloom, lens distortion, noise, LUT for three.js | Free (Zlib) | Yes | **Use** |
| **GSAP** | Timelines, CustomEase, SplitText, MorphSVG | Free (gsap.com, A) | Yes (`@remotion/gsap`) | Use where it saves work |
| **Dehancer / FilmConvert** | Film emulation plug-ins | Not read | Resolve/AE | Skip (the finishing chain, G1) |

---

## 5. Would After Effects or template packs clearly raise quality? (honest)
**What AE really has over a code stack:**
1. **The ecosystem:**
   - GEOlayers (maps with data and styles)
   - Particular-class particles
   - Deep Glow-class glow
   - a market of presets
2. **The graph editor:** artists hand-tune every curve while looking.
3. **A mature 3D camera** with DOF and motion blur built in.
4. **Tutorials for every look.**

**Why it isn't a clear win:**
1. **Code equivalents now exist for almost all of it** (§1, §3):
   - motion blur
   - DOF and bloom through three.js postprocessing
   - LUT, glow, lens and light-leak effects through `@remotion/effects`
   - 21 transitions
   - maps through MapLibre, d3 and turf, with an official agent skill
   - GSAP's free CustomEase for arbitrary curves
   - Only GEOlayers' map workflow and high-end particles have no equal in the stack.
2. **AE is scriptable, but just as blind for the chat.** ExtendScript plus aerender (or nexrender) can build and render comps, so AE
   isn't off-limits. But the chat still checks by rendering frames and looking, the same loop as Remotion, only slower and with an app
   it can't see live. Remotion's hot reload and `remotion still` make that loop faster.
3. **Templates are the cheap risk.** Generic shapes, icons and stock-looking reveals are exactly what reads as a cheap copy of the real
   thing (§2 row 11). Presets also lock the look to one vendor's taste, used by thousands of channels.
4. **Cost and ownership:** ~US$23/mo plus about $330 for GEOlayers, with no code you own.

**Verdict:** don't buy AE or templates first. Build the gaps in §1.4 in Remotion, Blender and Python.

**The gate test:**
1. Build one Johnny Harris-style map shot (tier 1 + tier 2) and one LEMMiNO-style document shot in the stack.
2. Put each beside the reference frame.
3. If the map loses on styling or terrain, propose an AE 7-day trial plus the GEOlayers trial (its trial is mentioned by one listing,
   unconfirmed) for that one shot type, with the price, and the creator decides.

---

## 6. What a mid-range PC handles (an 8 GB RTX 3060-class GPU, 16 GB RAM, a 6-core CPU)
- **Remotion:** 41 ms a Full frame with `angle` (measured by us); concurrency 6; render long videos in parts (the angle leak).
  - **Motion blur multiplies the cost** by about its sample count for the wrapped layer, so wrap only moving groups and switch it off on
    holds (estimate, to measure).
  - **three.js / r3f** at 1080p with DOF, bloom and SMAA should be fine (a 3D test scene and a globe test ran). 4K costs 4×.
  - **WebGPU** (`ThreeWebGPUCanvas`) is experimental: don't build on it yet.
- **Depth models:**
  - DA3MONO-LARGE (0.35B) and DA v2 Small (25M) should fit in 8 GB at ~518-1024 px input. Not measured (torch is a multi-GB install).
  - Video Depth Anything Small (28.4M) for video.
  - DA3's streaming mode quotes <12 GB for ultra-long video, more than an 8 GB card. Not needed for stills.
  - Without torch: ONNX (onnxruntime) or transformers.js on WebGPU (what `@remotion/video-matting` uses).
- **DepthFlow** claims 8k50 on an RTX 3060-class GPU (vendor, D).
- **Blender:**
  - EEVEE is comfortable at 1080p.
  - Cycles with OptiX works for small scenes; denoise on.
  - A whole city's OSM buildings at 16 GB RAM may need tiling (to test).
- **ffmpeg:** NVENC, libplacebo, Vulkan and OpenCL are present for GPU finishing passes.
- Heavy jobs follow the shared-PC rules (`standard/PIPELINE.md`).

---

## 7. Reference videos with outstanding motion design
Rows with a URL are channels outside any one niche. The top creators we studied are described by what to learn; their measured numbers
stay.

| # | Video | Where | Technique | What to learn |
|---|---|---|---|---|
| 1 | LEMMiNO, "Cicada 3301: An Internet Mystery" https://www.youtube.com/watch?v=I2O7blSSzpI | 0:05.6-0:31.4; 10:37-10:39 | The 3D void of real artifacts; continuous camera; push until text is 350 px | One camera through one space: ~14 graphic states a minute with 2.1 cuts a minute; tilted cards with focus falloff; real typography kept (measured by us, B) |
| 2 | fern, "The Strangest Place on the Internet" (formerly titled "the entire history of 4chan, i guess") https://www.youtube.com/watch?v=dU7gCt-7kKk | 4:10.5-4:11.9; 31:39-31:51.4; 2:05.0-2:09.5 | Push through the address bar; highlight follows the words, then an extreme close-up; glitch logo + bokeh focus pull + pixel-grid dissolve | Documents on a tilted plane with focus falloff; outlet type on grey; a quality bar for documentary visuals (measured by us, B) |
| 3 | A top creator we studied | – | Cut-out parade with depth blur, slam banner, glitch cut; punch-in highlighter with camera follow; year counter | Dense, sound-punctuated motion at its best (measured by us, B) |
| 4 | A top creator we studied | – | Archival strobe in a TV frame; the real page alive with a cursor; the **white 3D city** | Premium, clean 3D "map" imagery; real pages for a second (measured by us, B) |
| 5 | A top creator we studied | – | Montage bursts (14 cuts in 3 s); role labels on clips; black title cards on turns | 25.7 cuts a minute; graphics are labels and cards, not effects (measured by us, B) |
| 6 | A top creator we studied | – | Mock search UI with typing; country outlines as scale anchors; running counter; ranked bars | Numbers made visible; ~12 graphic states a minute on only 2.5 cuts a minute (measured by us, B) |
| 7 | A top creator we studied | – | Blur-in date card (0.4 s); a 0.35 s eased punch-in held 0.5 s; cards drop in and leave up | Clean, restrained motion; its strength is the cuts and pacing and the clip mash-up, not its graphics (measured by us, B) |
| 8 | Barely Sociable, "The Book Tied To 75,000 Disappearances" https://www.youtube.com/watch?v=q-1HikE4b54 | 1:20.8-3:15.1; 15:27-15:51 | Wordless headline opener (heatmap peak 1:39-1:55 = 1.000); chapter cards | Documentary restraint: few, perfectly timed graphics (measured by us, B) |
| 9 | Nexpo, "The Internet's Deepest Rabbit Hole" https://www.youtube.com/watch?v=6zLCZ_Ic1hI | 13:28-15:15 | False ending: a "MYSTERY SOLVED" stamp, a rewind glitch, 3 s of silence, "Something is wrong." | Motion as a story device, not decoration (measured by us, B) |
| 10 | Vox, "Why all world maps are wrong" https://www.youtube.com/watch?v=kIID5FDi2JQ | ≈3:00 (YouTube's automatic middle frame; exact second unverified) | Projection shapes on paper-white, letter-spaced caps | Designed vector maps: palette, type, paper; Vox's 12-fps graphics and texture boil (PremiumBeat, C) |
| 11 | MagnatesMedia, "Why Netflix is Collapsing..." https://www.youtube.com/watch?v=UXZzyKTsBMw | ≈17:08 and ≈34:17 (automatic frames; unverified) | Cut-out people with huge type behind them; red duotone with blurred type; B&W cut-out with red label chips | Layering cut-outs, type and a two-colour grade into a brand look. Its icon chips are close to generic shapes: take the layering, not the icons |
| 12 | Johnny Harris, "The most important country you've never heard about, Mapped" https://www.youtube.com/watch?v=yczYThn4nDI | Map sequences; **timestamps unverified** (YouTube refused the download; the automatic frames show his desk) | GEOlayers maps, Google Earth flyovers, paper and photo textures | The map benchmark for the gate test in §5 |

**For a next pass:** read rows 10-12 with storyboards (`yt-dlp` sb formats) and replace ≈ with seconds. Optionally add Wendover "How
Ocean Shipping Works" (8d5d_HXGeMA) and PolyMatter "How the Chinese Communist Party Works" (vre_yhZXPVU). Their automatic frames showed
footage and textured B&W archival, nothing conclusive.

---

## 8. Build order for a motion library, each piece tested against a reference frame
1. **`Blur` wrapper:** `HtmlInCanvasMotionBlur` with a keyframeable `disabled`. Retrofit card entries, slams, the cursor and counters.
   Measure the render cost.
2. **`DocStage`:** the captured page in depth: tilt + progressive blur or tilt-shift, light gradient, two-layer shadow, camera follow on
   the highlight, rough-notation variants, a real macOS cursor. Side by side with fern 31:39 and LEMMiNO 0:08.
3. **The transition set:** `TransitionSeries` with blurSlide, pushCut, zoomBlur, linearBlur, plus our camera-move defocus dissolve and
   a push-through. One language per source type.
4. **The finishing chain:** LUT + luminance-aware grain + halation + optional weave, under the graphics. A/B at 100% on the review
   screen.
5. **The map kit:** d3-geo vector maps (globe, morph, routes, outlines, paper) and MapLibre tiles with turf routes. Gate test against
   Johnny Harris (§5).
6. **Depth parallax:** install torch CUDA + DA3MONO-LARGE (and try DepthFlow); a displaced-mesh component; the layered cut-out route.
   Any AI fill follows the house rules on AI pictures and the creator's call.
7. **`Void3D`:** r3f stage for floating artifacts with video textures, DOF, bloom, a slow camera.
8. **Blender on the day** a video needs the white city or a hero object (`standard/3D.md`).

---

## Sources
**Remotion (A):**
- The docs on GitHub `remotion-dev/remotion/packages/docs/docs`: `effects/index.mdx`, `effects.mdx`, `html-in-canvas-guide.mdx`,
  `motion-blur/{camera-motion-blur,html-in-canvas-motion-blur,common-mistake}.mdx`, `transitions/presentations/*.mdx`, `maps.mdx`,
  `light-leaks/light-leak.mdx`, `video-matting/{index,get-available-models}.mdx`, `three-webgpu-canvas.mdx`, `after-effects.mdx`,
  `text-highlights.mdx`, `gsap/index.mdx`, `effects/{linear-progressive-blur,corner-pin,lut,glow,paper,light-leak,noise,zoom-blur}.mdx`.
- Package manifests: `packages/*/package.json`.
- The `remotion-dev/skills` repo (`skills/remotion-maps/SKILL.md`).
- npm registry: remotion latest 4.0.535 (at research time).

**Other primary sources (A):**
- Material Web tokens: https://raw.githubusercontent.com/material-components/material-web/main/tokens/versions/v0_192/_md-sys-motion.scss
- Adobe After Effects plans: https://www.adobe.com/products/aftereffects/plans.html
- Adobe "What's new in After Effects" (versions 26.0, 26.3, 26.5; via search).
- Blackmagic, About DaVinci Resolve 21: https://www.blackmagicdesign.com/support/content/readme/6aefbffe870f4ba686e61ecb83b19ec0
- Google Earth Studio FAQ: https://www.google.com/earth/studio/faq/
- Google Geo Guidelines: https://about.google/brand-resource-center/products-and-services/geo-guidelines/
- Video Copilot Element 3D: https://www.videocopilot.net/products/element2/
- Cavalry: https://cavalry.scenegroup.co/pricing (redirected page)
- Envato: https://elements.envato.com/pricing
- Motion Bro: https://www.motionbro.com/
- AEJuice: https://aejuice.com/pricing/
- GSAP: https://gsap.com/pricing/
- Models and repos:
  - Depth Anything 3 README: https://github.com/ByteDance-Seed/Depth-Anything-3
  - Depth Anything V2 README (licence section): https://github.com/DepthAnything/Depth-Anything-V2
  - Video Depth Anything: https://github.com/DepthAnything/Video-Depth-Anything
  - DepthFlow: https://github.com/BrokenSource/DepthFlow ; https://pypi.org/project/depthflow/
  - pmndrs postprocessing `src/effects`: https://github.com/pmndrs/postprocessing
- SMPTE ST 2046-1 safe areas, via NAB TV Tech Check 2010-03-15: https://www.nab.org/xert/scitech/pdfs/tv031510.pdf
- Netflix: https://backlothelp.netflix.com/hc/en-us/articles/4406208331923-Title-Safe-and-Safe-Action-Best-Practices

**Practitioner and secondary sources (C/D):**
- Jason Boone, "How I Got a Gig Making Maps for Johnny Harris", PremiumBeat 2022-03-24: https://www.premiumbeat.com/blog/making-maps-for-johnny-harris/
- aescripts learn pages on Johnny Harris maps (via search): https://aescripts.com/learn/how-johnny-harris-makes-maps/ ; https://aescripts.com/learn/making-maps-for-johnny-harris---volcanoes/
- Lewis McGregor, "5 Breakdowns on Replicating the VOX Motion Graphic Look", PremiumBeat 2021-03-08: https://www.premiumbeat.com/blog/replicating-vox-motion-graphic/
- Motion Array, Johnny Harris-style documentary tips: https://blog.motionarray.com/learn/premiere-pro/edit-documentary-in-premiere-pro/
- Motion Array, 2.5D parallax: https://blog.motionarray.com/learn/after-effects/animate-flat-2d-images-after-effects/
- Adobe, Animate a picture: https://www.adobe.com/learn/after-effects/web/animate-picture
- Noble Desktop, easing and motion blur: https://blog.nobledesktop.com/learn/after-effects/making-an-animated-gif-adding-easing-motion-blur
- Bring Your Own Laptop, easing: https://bringyourownlaptop.com/courses/become-a-motion-graphics-designer-using-after-effects/10-easing-your-animation-after-effects
- Jake in Motion, motion blur: https://docs.jakeinmotion.com/motion-state/controls/motion-blur/
- Animation principles, video motion graphics (C-): https://playbooks.com/skills/dylantarre/animation-principles/video-motion-graphics
- AE motion blur defaults: https://creativecow.net/?p=97118 ; https://www.provideocoalition.com/motion_blur/
- Film look:
  - Digital Production, "Halation and diffusion" 2024-01-30: https://digitalproduction.com/2024/01/30/halation-and-diffusion-on-the-hunt-for-the-ultimate-film-look/
  - Dehancer features: https://www.dehancer.com/features
  - Mixing Light Dehancer review: https://mixinglight.com/color-grading-tutorials/dehancer-film-print-emulation-review-part-2/
- LEMMiNO 4M Q&A transcript (rosetta.to): https://rosetta.to/u/lemmino/4-000-000-q-a
- Prices from aggregators and resellers (C/D):
  - GEOlayers $329.99: https://www.toolfarm.com/buy/markus_bergelt_geolayers/ (via search)
  - Red Giant $599/yr: https://nofilmschool.com/red-giant-complete-launch
  - Rive: https://agentdeals.dev/vendor/rive
  - Deep Glow v1 $49.95: https://aescripts.com/deep-glow
- OpenFreeMap terms (secondary): https://simonwillison.net/2024/Sep/28/openfreemap ; https://www.toolradar.com/tools/openfreemap
- Motion Canvas / Canvas Commons status: https://slama.dev/motion-canvas/1/ and the GitHub API (pushed 2026-07-02).
- nexrender: https://github.com/inlife/nexrender (GitHub API: MIT, pushed 2026-06-03).

**Measured by us (B):**
- Frame-by-frame studies of the reference videos in §7 (cut counts, graphic states a minute, timestamps and durations, the most-replayed
  heatmap values).
- An inventory of a code-built kit set: its components, `package.json` and `node_modules/@remotion/*`.
- The automatic frames of the three outside references marked ≈ (i.ytimg.com hq1-3, viewed by eye).
- Render timings with `--gl=angle` against software WebGL.
