# kit3: the house kit for long videos

*Part of `STANDARD.md`, beside `standard/LONG_FORM.md`. Code: `tools/motion/src/kit3/`. kit3 is two things at once: **the one look**
every built graphic of a long video has (section 1: the design system, its numbers in `tokens.ts`, its colours in `src/brand.ts`), and
**the one set of pieces** that draw it (sections 2-6), each existing once, with every known fix, its rules enforced by the code.*

**Why it exists.** When every section of a film carries its own copy of the same pieces (a page card in five graphics files, a footage
shot in eight), each copy has its own bugs and a fix lands in one copy only: a mark border drawn outside its box sat 4 px from the words
on one side and 12 on the other in seven of eight copies; nearly half of all hand-boxed marks sat off their words; the same faults came
back section after section (marks, rows off centre, text over its card, black first frames). In kit3 each piece exists once, its rules
are in the code, so a builder can't make those mistakes and a fix lands once for every video.

## 1. The look: one design system for every built graphic

Every built graphic of a video comes from this one system. A graphic that looks amateur is rebuilt on it, never patched. **If a graphic
needs something this system doesn't have, it is added to kit3 (and this section) first, with its test and a demo section, then used.**
A video never sets its own sizes, colours or curves; a video's own palette is not a kit3 thing: the brand repeats, the devices don't.

**The test every graphic passes before it goes in:** a still of it, read for 2 seconds with the sound off, says what it is, what the
number counts (with its unit), and who or what is pictured. The group is centred (within 4 px), the gaps are equal (within 2 px),
nothing in the never-list (1.9) is on screen.

### 1.1 The grid (`DS` in `tokens.ts`)
| Token | Value | Use |
|---|---|---|
| Frame | 1920 x 1080, 60 fps (rendered at 1440p, finished at 4K) | |
| Content box | x 120-1800 (1680 wide), y 96-968 | every readable thing except the credit |
| Centre lines | x 960, y 532 | every group is centred on them by its real width (`Split`, `Row`) |
| Credit band | below y 968, on the right | the credit only (the gate's BOTTOM flags text of 40 px or more below 972) |
| Title-safe | 96 px sides, 54 px top and bottom | the credit sits on it; nothing readable outside |
| Columns | 12 x 118 px, 24 px gutters | aligning text blocks; a half is 6 columns (828 px) |
| Spacing | 8 · 16 · 24 · 40 · 64 · 96 (`DS.S` xs-xxl) | 8 inside chips; 16 kicker to headline, photo to caption; 24 headline to the line under it, number to its subject; 40 card padding (48 at the sides); 64 between pictures in a row; 96 between a picture and the text beside it |

Placement is never a hand-set `left:` number for a picture or a group: a row goes through `Row` (it measures), a picture and its text
through `Split` (flexbox centres the group by its real widths).

### 1.2 Type: one family (Archivo)
One family, tabular figures on every number, sentence case, normal tracking, no italics. `type(k)` gives a role's whole font style.

| Role | Size | Weight | Line height | Tracking | Used for |
|---|---|---|---|---|---|
| Display | 168 px | 800 | 0.92 | -0.02 em | ONE per frame: the number (`BigNumber`), the stamp (fitted, at most 168), a year |
| Headline | 84 px | 800 | 1.0 | -0.01 em | the statement, a quote up to 70 characters, a number's unit |
| Title | 52 px | 700 | 1.12 | 0 | names on pictures, a number's subject, a list's title, quotes past 70 characters |
| Label | 40 px | 600 (700 in list rows) | 1.2 | 0 | kickers, captions, list rows, the line under a headline; **the smallest size anything to be read may have** |
| Meta | 26 px | 500 | 1.25 | 0 | the credit line, nothing else |

- Caps only in a Stamp (it is a slogan); everywhere else sentence case. No tracked-out caps "eyebrows" above headings.
- A headline line holds about 24 characters at 84 px in an 820-px block, a label line about 42 in the same block: write to fit, never
  shrink the type to make words fit (only the Stamp fits itself).
- Text is HTML, never SVG `<text>`: SVG text in a graphic came out clipped on every third frame of a render while the HTML beside it
  was fine (lines and shapes may stay SVG).

### 1.3 Colour (from `src/brand.ts`, set at setup)
| Token | Value | Use |
|---|---|---|
| Ink | `INK` (warm white, `#F4EFE6` by default) | all text, all marks' outlines |
| Ink, muted | ink at 66% (`DS.INK2`) | kickers, units under things, ranks, a caption's second line |
| Ink, unlit | ink at 30% (`DS.INK3`) | a quote's words not said yet |
| **The accent** | `BRAND` (the creator's accent) | **the one accent, only on what the voice names now**: the number, the lit word, the hero row, the named cut-out's tag. At most one accent thing per frame (two only when the voice names both). Never on decoration |
| On the accent | `ON_ACCENT` | text on an accent fill |
| Surface | black at 88% (`DS.SURFACE`) | the one card |
| Black | `#000` | every dim, every shadow |

Never: a second accent, gradients as decoration, glows, coloured shadows, borders on cards, glass.

### 1.4 The card
- One card (`Card`): surface fill, radius 12, padding 40 top and bottom and 48 at the sides (quotes 44 / 56), shadow
  `0 2px 6px rgba(0,0,0,.35), 0 28px 72px rgba(0,0,0,.55)`, no border, no glow. Widths from the grid: 760-820 beside a picture, 1100
  for a list, up to 1200 alone.
- One card per frame (two only for a side-by-side comparison of two equal things).
- Chips (`Tag`, the credit's backing): radius 6, padding 8 / 22 (a name) or 4 / 12 (the credit).
- A card holds text. A cut-out never stands on a card (the gate's CUTOUT_ON_CARD); a clip never goes in one.

### 1.5 Pictures
| Kind | Rule |
|---|---|
| **Clips** | full frame, filling the screen, always: never in a panel, never cropped to hide an overlay, a picture-in-picture, a ticker or a label; a letterboxed source shows whole with its own bars |
| **The ground under a built graphic** (`Stage`) | the shot's own footage, full frame, running the whole shot (the gate's STILL), defocused 8 px and dimmed to 42%, scaled 1.04 to hide the blur's edge, a soft edge vignette (black 45% at the corners); or the graphic's own picture blurred. Plain near-black only when no footage fits the words |
| **Cut-outs** (`Row`, `Cutout`) | one height per row (the visible figure's height); each width from its own visible pixels (alpha over 16, measured in the browser: transparent margins don't count); 64 px between every pair of visible figures; the row centred on x 960 (or its column) and kept centred while its items arrive one by one; a row wider than 1680 shrinks as a whole. A size per item only when the words compare real sizes. **floor** (things): one floor line (by default the one that centres figures and names together on y 532), a contact shadow under each (an ellipse 110% of its width, 44 px tall, black 62% to 0), its name under it (title, 28 px below the floor). **bleed** (people cut at the legs): the cut 40 px under the frame's foot, no contact shadow, the name on a chip 160 px above the foot. Every cut-out a drop shadow `0 22px 34px` black 55%. Never two figures overlapping, never a straight cut edge inside the frame, never a cut-out over its own blurred copy |
| **Photos** (`PhotoFrame`) | shown whole at their own shape (no crop), radius 12, the card's shadow, at most 1.3x their own pixels (it caps itself), 600-760 px tall beside text; the caption under it (label: who or what; muted line: when, where). Full bleed only when the photo is 1477 px wide or more (1.3x), as a `Stage img` |
| **Logos** (`LogosLand`) | alone, centred, about 280 px tall (or 640 wide when wide), clean; never under text, never under a stamp, never half hidden |
| **Pages** (`Page`) | the page whole, or its lit lines framed whole: never a fragment that says nothing |

### 1.6 Motion (the house curves, `src/house/motion.tsx` `EASE`; progress helpers `enterP`, `exitP`, `moveP`, `lightP`)
| What | Curve | Duration | Distance | Notes |
|---|---|---|---|---|
| Entrance (cards, pictures) | `EASE.enter` (0.05, 0.7, 0.1, 1) | 0.40 s | rise 32 px (cut-outs 56) | opacity full at 60% of it; starts 0.06 s before its word (`enterP`) |
| Entrance (text) | `EASE.enter` | 0.30 s | rise 32 px | the parts of a block 0.08 s apart (kicker, headline, line) |
| Exit (rare: most graphics end on the cut) | `EASE.exit` (0.3, 0, 0.8, 0.15) | 0.25 s | fall 24 px + fade | exits quicker than entrances |
| A move on screen (re-order, re-layout) | `EASE.move` (0.2, 0, 0, 1) | 0.90 s | | every row in ONE move |
| **The camera** (`Stage`, `Foot`, `Still`) | linear | the whole shot | push 1.00 -> 1.03 (`DS.PUSH`; 720p sources 1.02) | one way, steady (an eased push stands still in its last third: the gate's STILL); never back |
| **A number lands** (`BigNumber`) | `EASE.move` | 1.2 s (0.9-1.6 by size) | | an odometer: every digit a strip rolling continuously, each higher digit turning only as the one below passes 9 to 0, leading digits growing in; starts on the number's word; the unit and the subject are on screen from the block's entrance |
| **A ranking moves** | `EASE.move` | 0.90 s | | one glide: the hero row (accent filled) passes over the others with a deeper shadow, the rows it overtakes step down, a leaving row fades out 64 px to the right in the first half, an arriving row fades in from the right in the second half; the rank numbers belong to the places (a standings board: they never move or swap), each lighting as the hero row passes it |
| **A row fills** (`Row`) | `EASE.move` | 0.60 s | | items land one by one on their words and the row stays centred the whole time: the ones already there glide aside to make room |
| **A quote is said** (`Read`) | `EASE.enter` | 0.12 s a word | | each word from 30% ink to full ink from 0.04 s before it is said; the phrase the voice leans on to the accent |
| **A word is named** (`Lit`, `Tag lit`) | `EASE.enter` | 0.12 s | | ink to accent on the word |
| **A stamp** (`Stamp`) | `EASE.enter` | 0.16 s | scale 1.15 -> 1.00 | opacity in 0.05 s; the footage under it dims to 50% on the same curve; on the stamp sound's frame; straight |
| A dim (`dimAt`) | `EASE.move` | 0.30 s | | to 45% opacity, saturation 30%: the ones the words leave out |

- Nothing steps: no digit swapped for the next, no position jumping from frame to frame, no "No.10 -> No.4" swap.
- Nothing springs back (the gate's YOYO), nothing moves in a shot's last 0.25 s (MOVING_AT_CUT), no highlight starts in a shot's last
  0.6 s (MARK_LATE). Every entrance, move, roll and stamp gets its sound in the cue sheet: a whoosh on a slide, the tick roll on a
  number, the stamp hit, the marker on a light; no effect over -7 LU against the voice.
- One shake per video at most, on an impact only; one self-made animation idea is used once per video.

### 1.7 Credits: one style, one place
`Credit` (also built into `Stage` as `credit` / `source`): ONE line, bottom right, its right edge on x 1824 (title-safe 96) and its foot
on y 1026 (54), meta 26 / 500, ink at 80%, on a quiet chip (black 50%, radius 6) so it reads over anything. Format: `whose picture  ·
Source: where the number or quote comes from`, e.g. `The maker's official video  ·  Source: the maker's annual report`. Never two lines,
never at the top, never centred, never italic (the gate's CREDITS_STACKED; B9 reads it against the clip's master: name the footage's
real source).

### 1.8 Labels: nothing on screen without its meaning
- **Every number** carries its unit and its subject in the same block (`BigNumber` and `NumberBeside` require `unit` and `subject`):
  "2.4 million tickets / sold for the tour in its first month". A share says "x of y" and of what. A date is absolute (Month
  YYYY).
- **Every list** says what it ranks and by what ("Best-selling cookbooks, last year" / "By copies sold").
- **Every person or thing a viewer can't name** gets its name (a `Tag` on a cut-out, a caption under a photo).
- **Every quote** says whose and where (the post's forum and month, the outlet and year).
- A graphic that needs the voice to be understood is unfinished (a ring with no "1 of 6" and no subject reads as nothing).
- On-screen words that repeat the spoken words come out of the captions there (`captions_hide.json`, the gate's B10).

### 1.9 Never
1. **Slammed, tilted words over a logo or a picture:** no rotated text anywhere; a stamp is straight and over footage only; no text
   over a logo, a face or other text.
2. **Lines that mark nothing:** no underline, rule, bar or divider unless it marks something the words say (a chart's zero line, a
   strike through the crossed-out thing, a box on the named region).
3. **Panels shrinking clips** on blurred grounds.
4. **Crops and zooms into fragments:** stills shown whole, at most 1.3x their pixels, pushes gentle.
5. **Stepped or stiff animation:** numbers roll, lists glide, everything eases, nothing swaps.
6. **Hand-placed rows:** unequal gaps, rows off centre, figures overlapping, a credit over a figure.
7. **Unreadable graphics:** text under 40 px (the credit excepted), a number without unit and subject, a shape standing in for a real
   thing we could show.
8. **The AI-template look** (`standard/LONG_FORM.md`, "The AI-template look"): a second accent, neon, glows and gradient blobs, borders on
   cards, glass, monospace, tracked caps eyebrows, a number centred alone on a card over blurred footage (it goes beside its picture), the
   same entrance on everything at once (stagger, land each on its word).
9. **Two looks:** another font, another size, another radius, another card, another credit style.

## 2. How to use it

- **Import, never copy.** `import {Page, Foot, Row, ...} from '../kit3';`. A video's graphics file holds only the one-off graphics that
  are that video's own ideas (the brand repeats, the devices don't). A piece that more than one section needs goes into kit3, with a unit
  test and a demo section, never into a video's folder.
- **Paths are public-dir paths** (`'<video>/img/x.png'`, `'<video>/clips/x.mp4'`, `'<video>/pages/x.png'`), so the kit belongs to no
  video.
- **Every clip must be in `src/clipdurs.json`** (written by the video's prep script, which measures each clip it cuts:
  `tools/motion/prep_template.py`). The Studio shows "pending" for a clip that isn't; any render, stills run or gate probe **fails** on
  it, so no grey box can reach a render.
- **The kit refuses a mistake, loudly.** A piece that gets an impossible or forbidden input throws with the reason ("kit3 Page ...: mark 1
  holds 78% of its crop's ink: the crop is only that thing, it needs no mark"). The still, the gate's probe and the render all stop on it
  (the gate's B15 KIT3_REFUSAL names it). Fix the input; never wrap the piece to swallow the error.
- **All times are the shot's own seconds** (`w(beat, phrase) - t0`).
- **The marker sound** comes from the cue sheet: one per mark, on its `at` (`tools/sound/autocues.py` writes them from the gate's probe).
- **The spot look is the default mark on pictures** (`Still`, `Foot`; on a `Page` it is `look="spot"`, the page's own default being the
  measured wash or box; section 4): set a video's own dim once round its composition with `<SpotLook dim={...}>`.

## 3. The pieces, and when to use which

| Need | Use | Not |
|---|---|---|
| Footage on its words | `Foot` (one clip), `Burst` (hard cuts on the bed's beat) | a clip in a panel or card |
| A still full frame, or one region of it | `Still` (`region`, `from` for a glide in) | a still past 1.3x its pixels (it refuses; `upscaleOk="why"` when nothing sharper exists) |
| A spot, box, outline or highlight on something in a picture | `Still marks` or `Foot marks` (the picture freezes under them) | a mark placed over a picture on its own (there is no such API) |
| A small thing marked | `Foot zoom` (a quick zoom from the freeze onto the marks, ~0.45 s), the clip cut from the 4K master | a mark on a speck (the gate's B25 MARK_SMALL) |
| A mark on a fixed on-screen overlay (a broadcast's score bug, a camera's timestamp) | `Foot marks` with `live` (the clip plays on under them) | a freeze of a blinking thing |
| A name on a person | `TagShot` (top right, `left`, or `on: [x, y]`), `Still names` | a name as a mark (a name label may sit on a playing clip) |
| The words of a page, post, video page or store page | `Page` (the page itself, sharp, the said words marked) | a card restating the page |
| A number | 1. on a real thing: `Page` with the number marked and the thing `beside` it; 2. no page but a picture: `NumberBeside picture=...`; 3. no picture at all: `NumberBeside noPicture="why"` | a number alone on a card over blur (it can't be built) |
| Someone's words, when the page can't be shown readable | `Read` (whole from its first frame, the leaned-on phrase lit) | a word-by-word reveal, unless the voice reads exactly those words then |
| A headline claim on its word | `StampShot` / `Stamp` | tilted or slammed text over a logo or face |
| A date typed | `TypedShot` / `TypedLine` (top centre, y 178) | a date placed where it fits |
| A row of things, people or covers | `Row` (`floor`, `bleed`, `centre`) | hand-set `left:` values |
| Logos | `LogosLand` | logos sized by their files |
| Dates in order | `Timeline` (true distances) | |
| Text blocks, chips, cards | `TextBlock`, `Kicker`, `Headline`, `Label`, `Lit`, `Tag`, `Card`, `Split`, `Enter` | own sizes, colours, cards |
| The ground under a built graphic | `Stage` (the shot's footage defocused and dimmed, or a still, or plain) | |
| A face icon (a person on a map, a chart, a lineup) | `Still icons`, each made by `make_icon.py` (section 5) | a face cropped by hand, a circle of a cropped screenshot as a shot's picture |

Every component's props are documented in its file's header comment.

## 4. What each piece enforces by construction

| Piece (file) | What it makes impossible to break | The fault it ends |
|---|---|---|
| marks (`marks.tsx`, used by `Page`, `Still`, `Foot`) | the border inside the box (border-box); the outer edge on whole pixels, 8 px from the ink on all four sides; one look per page kind (a wash on a light page, a box on a dark one, measured from the page's own paper colour); the newest mark in the accent, earlier ones fading to an ink outline (pictures); the rest dimmed, each hole opening with its own light | a border drawn outside its box (4 px from the words one side, 12 the other); pages guessed light or dark |
| the spot look (`marks.tsx`: `SpotDim`, `SpotRim`, `SpotInk`, `SpotGate`, `SpotLook`; the default on `Still` and `Foot`, `look="spot"` on `Page`) | no shape drawn round the thing: the rest of the layer dims and greys outside a feathered light on it (`SPOT.DIM` 0.22 of the light left, `GREY` 0.6 of the colour gone), a thing in a picture lit by a round light (an ellipse 0.95 x 1.25 of its box as semi-axes, falling off as the measured mock-up did), words by a line light hugging the padded words; the dim comes in over 0.4 s from 0.1 s before the word (a change of light, never a 0.12-s blink, which shows the bright frame for 6 frames and reads as a flash); the accent rim on a thing's own silhouette (`spotmask.py`) and the accent on marked words are OFF by default (the light alone reads cleaner); `SpotLook` per video: `dim`, `grey`, `lift` (a lit thing that is itself a light, a sign or a screen, marked `bright: true`, pushed brighter by 1-(1-v)^lift, never on words, never a dark thing against a bright sky), `rim`, `ink`; a context, so one video's setting never reaches another's; `SpotGate` gives the gate the same rect as the box look | a drawn box over a picture reading as clutter |
| `Page` (`page.tsx`) | every mark snapped to the INK of its words in the browser (the given box is only where to look: a page capture's DOM boxes carry up to 26 px of blank); a box on no ink, a mark lighting in the shot's last 0.6 s, a mark holding 60% of the crop's ink or covering 45% of its area, and marks together lighting 60% of the text are refused (a mark only where there is a choice; never almost the whole text lit; the gate's MARK_LATE); the crop grows to hold every padded mark whole, in the page's paper colour past the capture's edge; the page stands still from its first light to the cut, the blurred ground keeps its slow push (no fully frozen frame); several pages on one scale, each labelled; `beside` for the thing itself next to its receipt | marks offset, on the letters, loose on one side or round blank space; a name alone in its crop boxed for nothing; borders cut by short crops |
| `Foot` / `Still` (`footage.tsx`) | marks freeze the clip (`Hold`, Remotion's `Freeze`) and stop the push from the first light, drawn in the picture's layer so they ride with it (a mark that stays put while its picture moves leaves its target); `zoom` from that freeze toward the marks' union over 0.45 s, landing as near the centre as the picture's own edges allow (no bare frame edge ever shows; an interface corner stays in its corner), then a slow keep-alive drift; `live` keeps the clip playing under marks on a fixed overlay; a mark off its picture or covering 45% of it refused; a still past 1.3x its pixels refused without a written reason; `blurs` (a username, a stranger's name) ride with the picture; a clip not measured fails the render; a profile icon (`Still icons`) only with its `make_icon.py` sidecar: cut from a real frame, its face measured on the icon within 4% of the circle's centre and 42-72% of its height, else refused; the icon's `<img>` is `data-gate="icon"`; `bars` keep a letterboxed frame's own bars fixed and straight | boxes drifting off a wall poster as the footage pushed in; low-resolution stills zoomed 4x unremarked; face icons cut from artwork, a face 16% of its circle below its centre |
| `TagShot`, `Tag`, `Still names` | a name chip marks itself `data-gate="name"` (not a mark: it may sit on a playing clip); one place for the kind (top right, or on the person) | name tags frozen then unfrozen |
| `Row`, `LogosLand` (`rows.tsx`, the math in `layout.rowLayout`) | widths from the VISIBLE pixels (alpha over 16, measured at up to 2048 px); one gap between every pair of visible figures, widened for all when names need it (names keep 24 px apart); the whole visible content (figures and names) centred; a row too wide shrinks as a whole and the floor is recomputed from the shrunk heights; a row that can't fit is refused; names `data-gate="name"`; a row of ONE (a lone logo or cut-out) centred to the eye (section 5), a wide lockup (over 2.5:1) by its box | a narrow figure 64 px off its long name; unequal gaps between people; a floor computed before the shrink; a lone logo box-centred "too far right" |
| `Read` (`read.tsx`) | the card fits its text (each line measured; headline size only when it fits, title otherwise; a line too wide even at title size is refused); words whole from the first frame unless `reveal` gives each word's time; a lit phrase must be on the card, and lit phrases stay under 60% of the text | text running over its card; word-by-word reveals the voice doesn't read |
| `NumberBeside`, `BigNumber` (`numbers.tsx`) | no number without a picture or a written `noPicture` reason (also a TypeScript error); no number without unit and subject; the column exactly its widest line (the group centres by real widths); the block enters on the roll | number cards standing in for the thing; a counter showing "0 million" for 0.7 s |
| `Timeline` (`timeline.tsx`) | dates at true distances; each label measured, moved above the line when it would touch the one before, refused when it touches on both sides; first and last labels kept inside the content box | 440-px labels set 367 px apart |
| `TypedLine` / `TypedShot` (`text.tsx`) | the keys pulled in so the line is whole 0.3 s before the cut | a date cut mid-typing at the cut (the gate's MOVING_AT_CUT) |
| `Stage` (`stage.tsx`) | the ground mounts at once, never behind a measurement; `hold` stops only the foreground; one credit line, bottom right | black first frames (section 7) |
| measuring (`measure.ts`) | every measurement holds the render (`useDelayRender`) until it is in, and releases only after the commit that mounted what waited on it; a handle per measurement key; fonts measured only after `waitUntilDone()` | the black-frames race; a counter measured on the fallback font (its slots 13% narrower than the figures, digits cut at their edges) |

## 5. Centred to the eye, and face icons

- **What "centred" means:** left to right, halfway between the box of the visible pixels and their centre of mass (so each cue is off by
  half and neither shows); up and down, the box's middle. Measured on the picture, never judged from the code: a logo whose weight sits
  9.1% of its width right of its box's middle, box-centred, reads ~4.5% of its width "too far right" (25.6 px on a 3D emblem).
- **The kit does it:** a lone figure in `Row` / `LogosLand`, and kit3d's pieces (`standard/3D.md` §3 item 11). A wide lockup (an icon
  beside a wordmark, wider than 2.5:1) keeps its box (unverified with the creator's eye).
- **The gate's check:** `tools/motion/qa_centred.py` (`gate_flags(v, lay, cl)`, B21): `LOGO_OFF_CENTRE` when a lone cut-out placed to be
  centred, or a kit3d piece's own `kit3d|` lines, sit more than 12 px off their point on the 1920 frame (a passed set of logos measured
  at most 10.8); a wide lockup is listed to look at, never blocking.
- **A profile icon** (a person on a map, a chart, a lineup) is made, never cropped by hand: `EDIT tools/motion/make_icon.py make <out.png>
  --src <video, clip or screenshot> [--t <s>] [--pick biggest|n|x,y]`; `sheet` lays out candidates as they'd show, `check` reads an icon as
  the gate does. The face (YuNet, `MODELS/face_detection_yunet_2023mar.onnx`) is centred, 56% of the side; artwork is refused (real people
  read at once, artwork reads cheap beside the real thing). The gate's `ICON_FACE_OFF` (the face found on the icon's own file off by more
  than 4%, outside 42-72%, or none) and `ICON_NOT_REAL` (no sidecar, artwork). Prefer the newest real pictures of the person.
- **Tested:** the lone-figure cases in `src/kit3/test/layout.test.mjs`.

## 6. Foot's `lift`: a shadow curve

A CSS chain like `brightness(1.22) contrast(1.06) saturate(1.06)` pivots its contrast on mid-grey, so it DARKENS every value under
26/255 and clips the darkest to black: on a dim shot the mean went 14.4 -> 12.3, 83% of the pixels darker, pure black 3.6% -> 18.2%.
kit3's `lift` is a shadow curve on the picture's own sRGB values, per channel: `v + 1.3 v (1 - v)^14` (`tokens.ts` LIFT, drawn by the
SVG filter `kit3-lift`, a 65-step feComponentTransfer table within 0.24 of a level of the curve; no AI): black stays black, white stays
white, nothing gets darker, +63% at 0.05, +6% at 0.2, nothing above 0.35. Measured (`EDIT tools/motion/lift_check.py`, 4 frames a
second): two dim shots 14.4 -> 20.0 (median 10.1 -> 17.3, no pixel darker, black 3.6% -> 2.6%) and 11.4 -> 16.7; a daylight shot 91.1
-> 93.3, its highlights unchanged (90th percentile 163.1 both), 2.1 levels of change on average (the CSS chain: +18.5, 0.6% of it clipped
white). Through Chrome (Remotion stills of `Foot lift`, `lift_check.py --chrome`) each within 0.8 of the curve's own numbers. It is for a
slightly dim pick: a MURKY span is re-picked, never lifted (the gate's DARK flag).

## 7. The black-frames race, and how the kit closes it

A measuring hook that released its `delayRender` the moment its boxes were measured, one render before the page card it fed had mounted
its blurred `OffthreadVideo` ground, let the video's own `delayRender` come too late: every render tab lost its first frame (3 black
frames at concurrency 3, up to 6 at 6). kit3 closes it three ways: (1) `useMeasured` releases a handle in an effect after the commit
that used the measurement (a parent's effects run after its children's, so every child's own hold, an `<Img>`'s or an `OffthreadVideo`'s,
is already taken); (2) `Stage` mounts its ground at once and only the measured foreground waits; (3) a handle per measurement key, so a
prop change that needs a new measurement holds the frame again. Each render tab measures for itself (tabs share no state), so nothing
depends on render order. The gate's B3 BLANK flags 1-6 empty frames between pictures that fill the frame.

## 8. What the gate reads

kit3 uses only the `data-gate` values the gate knows (`tools/pipeline/gate.py`, header): `credit` (Credit), `name` (Tag, a row's names, a
picture's caption), `stamp` (Stamp, TypedLine), `roll` (Odometer slots), `mark` (every MarkBox and SpotGate), and `icon` (a `Still`
icon's `<img>`: `qa_centred.py` reads it; it counts as a picture otherwise). It sets them on the element itself, never on a container
(the probe takes the closest `data-gate`, so a container's value would re-label everything inside it). For further checks it also writes
`data-kit3`: `mark` (with `data-kit3-ink`, the ink box it was padded from, in its layer's px), `page`, `row` (with `data-kit3-gap`;
the gate's B14 ROW_CENTRE reads kit3 rows by it, since a kit3 cut-out is drawn as its whole file and its transparent margins share no
floor), `cutout`.

## 9. The proof (run it after any change to kit3)

Three layers, each runnable again (from `tools/motion`). The demo runs on material drawn in code (`kit3_demo_assets.py`,
`src/kit3/Kit3DemoArt.ts`: pages, scenes, cut-outs and logos as generated pictures), so it renders on any PC and needs no licence; its
marks use deliberately LOOSE word boxes, so the kit's ink snap does the work a hand check would.

1. **The math, in node** (no Remotion job): `node src/kit3/test/layout.test.mjs` compiles `layout.ts` with esbuild and runs the layout
   checks: a row of three cut-outs of different widths (equal gaps, names 24 px apart, visible content centred), a row that shrinks, a
   capped logo, the ink snap (the run plus its colon but not the next word; the blank over and under trimmed; a box on blank space is
   null; a descender kept; the line above's descender left out and an i's dot kept), the guards (a name alone refused at 78% of the ink,
   a headline kept at 51%, three lines kept at 45%, a tile crop, MARK_LATE, a box on nothing, two marks lighting 65%), whole-pixel even
   pads, the crop growing past the capture's edge, the timeline's labels, the typed keys. Every check passes.
2. **The demo, rendered** (`src/kit3/Kit3Demo.tsx` on its own entry `src/kit3_index.ts`; public dir `TMP/pub_kit3`, built by
   `EDIT tools/motion/kit3_demo_assets.py`): `bash with_remotion_lock.sh "kit3 proof" node kit3_proof.mjs <dir>` (the heavy ticket, one
   bundle, one Chrome; the demo's stills at 1920 x 1080, then every refusal case, each of which must FAIL with its reason: a name alone
   in its crop, a box on blank space, a light at 2.6 s of a 3-s shot, a card 100% lit, a line 2221 px wide, a lit phrase not on the card,
   a clip not in clipdurs, a picture mark over 58% of the frame, a still at 4x its pixels, a number with no picture and no reason, a
   number with no unit, a row that can't fit).
3. **The pixels, measured** (`EDIT tools/motion/kit3_check.py <dir> --sheet <png>`): every mark found in the still by its colour, the
   ink inside it found by glyphs (the kit's own definition, ported), its four gaps measured (each within 2 px of the kit's 8, the ink
   inside the target words' shape within 3%); every picture mark against where its target box lands on screen (within 2 px); every
   row's visible figures and names (gaps equal within 2 px, centred on x 960 within 4 px); the frozen pairs (0.00% of pixels changed
   after a first light; the same clip before its hold changes); the refusals.

What the proof showed the first time it ran: the same marks drawn the way hand-built copies drew them (box +-8, border outside) measured
L8-13, T20-34, R4-28, B16-37 px from their ink (a "!" under the border, up to 34 px of blank over the words) against the kit's even 8.
And two faults found on the way and fixed: a first snap that grew rows and climbed into the line above through a descender (the guard
refused the page at 76% instead of drawing a wrong box; the snap is now by glyphs on the line's core band); a wash reading that counted
the paper in the wash's rounded corners as ink.

## 10. Remotion's own rules behind kit3 (from Remotion's primary docs; installed `remotion` 4.0.532)

| Topic | Source | What it says | What kit3 does with it |
|---|---|---|---|
| `useDelayRender` | https://www.remotion.dev/docs/use-delay-render, https://www.remotion.dev/docs/delay-render, https://www.remotion.dev/docs/timeout | the hook (v4.0.342; its `cancelRender` v4.0.374) is the recommended way, the global functions "discouraged"; a handle is taken once (a `useState` initializer, never on every render), never at module level; the render waits for every handle; timeout 30 s by default (per call `timeoutInMilliseconds`), `retries` default 0; it does nothing in the Studio or Player | `useMeasured` takes its handles from `useDelayRender`, labelled `kit3: ...`, 60-s timeout, `cancelRender` on a failed load; the components render a placeholder until the value is in (the Studio doesn't wait) |
| Flicker and black frames | https://www.remotion.dev/docs/flickering | causes: animation not driven by `useCurrentFrame` (tabs share no state), assets not loaded (use the media tags, wait for fonts), async data without `delayRender`, CSS `background-image`, many `<Html5Video>`; `--concurrency=1` only as a workaround | every animation from `useT()`; every picture through `<Img>`; every measurement under a handle; caches per tab |
| Video for rendering | https://www.remotion.dev/docs/offthreadvideo, https://www.remotion.dev/docs/video-tags, https://www.remotion.dev/docs/media/video | `<OffthreadVideo>` extracts frames outside the browser (frame-perfect, not deprecated); `@remotion/media`'s `<Video>` is the recommended tag for new code (falls back to OffthreadVideo); both hold their own `delayRender` until their frame is ready | kit3 plays video only through `lib.tsx`'s `Clip` (OffthreadVideo), which the gate's probe needs (B0) |
| Images | https://www.remotion.dev/docs/img, https://www.remotion.dev/docs/staticfile, https://www.remotion.dev/docs/prefetch | `<Img>` holds the frame until loaded (`maxRetries` 2, then `cancelRender` unless `onError`); `staticFile()` encodes the name; `prefetch`/`preloadImage` only help the Player and Studio | pictures drawn with `<Img>`; the kit's own pixel reads (alpha bounds, ink) decode the same-origin `staticFile` URL into a canvas under their own handle |
| Freeze | https://www.remotion.dev/docs/freeze | `<Freeze frame active>`: children see the frozen frame, videos inside are paused (`active` since v4.0.127); `<Sequence freeze>` is the newer form | `Hold` (Foot's marks) uses `Freeze` with `active` from the hold frame on |
| Fonts and measuring text | https://www.remotion.dev/docs/google-fonts/load-font, https://www.remotion.dev/docs/layout-utils/best-practices, https://www.remotion.dev/docs/layout-utils/measure-text | `loadFont()` blocks the render itself and returns `waitUntilDone()` (v4.0.135); measure text only after the fonts are in, with every font property matched and `white-space: pre`; `validateFontIsLoaded` throws on a fallback measurement | `textW` measures a real span (`white-space: pre`, same family, weight, tracking) and keeps a width only once `waitUntilDone()` has resolved |
| Testing | https://www.remotion.dev/docs/testing, https://www.remotion.dev/docs/renderer/render-still, https://www.remotion.dev/docs/renderer/render-frames, https://github.com/mapbox/pixelmatch | components are tested like any React code; `renderStill()` with a reused browser (`openBrowser`) for many stills; nothing official on visual regression: pixel diffs of stills are the common way | the math is pure functions tested in node; the pictures are proven by stills from one bundle and one browser (`kit3_proof.mjs`) measured from their pixels (`kit3_check.py`), not by eye alone |

## 11. Not in kit3 (yet)

A video's one-off graphics stay in its own folder (`tools/motion/src/<video>/`). When a second video needs one, it is moved here with a
test and a demo section. Video for footage still goes through `lib.tsx`'s `Clip`. Designed forms kit3 has no piece for (bars, rankings,
maps, splits, transitions) are in kit 2 (`standard/GRAPHICS_KIT2.md`), used only inside this look; 3D pieces are kit3d
(`standard/3D.md`).

## 12. Open risks

1. **The ink snap needs contrast.** Ink is any pixel more than 24% (60 of 255, any channel) away from the page's paper colour. Light grey
   on white, text on a photo or a gradient may snap wrong or not at all (then it is refused as "no ink", loudly). For those, measure the
   box yourself and pass `snap: 'box'`.
2. **Tight leading.** When a page's lines overlap (a descender of line 1 reaching into line 2's ink band), the mark's border crosses the
   neighbouring glyph. No box round the line can avoid it.
3. **The redundant-mark guard is a measured heuristic.** 60% of the crop's ink or 45% of its area, calibrated on six real cases (a name
   alone refused at 0.78; a headline at 0.51 and three lines at 0.45 kept). A crop of one tile with noise round it could pass: the eye on
   the stills still looks.
4. **Marks on footage take the caller's box** (no ink can be read from video): measure it on the frame the clip freezes on (the first
   mark's `at` minus 0.06 s), with `automark.py` on that frame, or it sits off the thing.
5. **The marker sound** is the cue sheet's job: a video's cue parser must read kit3's `Page`, `Still` and `Foot` `marks`
   (`autocues.py` does).
6. **Video stays on `lib.tsx`'s `Clip` (OffthreadVideo)**: Remotion recommends `@remotion/media`'s `<Video>` for new code, but the gate's
   probe reads clips only through `Clip` (B0). Moving is the gate's call, with the gate's checks re-proven.
7. **A still that isn't 16:9 can't show whole in `Still`** (it fills the frame): a square or ultrawide picture shown whole needs its own
   piece (whole on the `Stage`, then one glide onto its subject); when a second video needs it, it moves into kit3.
