# Graphics kit 2: the catalogue of designed forms

*Part of `STANDARD.md`, beside `standard/LONG_FORM.md` and `standard/KIT3.md`. Code: `tools/motion/src/kit2/`. Previews: the `KIT2-*`
compositions (`src/kit2/Kit2Preview.tsx`, registered in `src/Root.tsx`); render their sheets with `node tools/motion/kit2_stills.mjs
<out>` (one bundle of a small public dir; per card its first frame, 1.2 s and its end state, one row a card, `<out>/<comp>_sheet.jpg`;
`KIT2_VIDEO=1` also writes a half-size clip of each for the motion checks).*

## Where kit 2 stands

kit 2 is a catalogue of graphic FORMS: timelines, numbers, stat tiles, bars, rankings, lockups, lower thirds, quotes, photo cards, cover
rows, splits, maps, punch-ins, speed ramps and wipes, each in 2-3 variants. **kit3 is the house kit and comes first** (`standard/KIT3.md`:
`Timeline`, `BigNumber` / `NumberBeside`, `Row`, `Read`, `Page`, `PhotoFrame`, `Stamp`, `TagShot` ...). A kit 2 piece goes into a video
only where kit3 has no form for the idea (a bar comparison, a ranking, a map with callouts, a before/after split, a speed ramp, a match
cut), and then only:
- **with real material inside it** (the covers, photos, frames, clips of what the words name; kit 2's dark cards built bare, with
  nothing real in them, are exactly what reads as AI slop);
- **through the AI-template checklist** (`standard/LONG_FORM.md`): kit 2 predates kit3 and the creator's look, and its own defaults carry
  tells (card edge lines, a glow token, a monospace face, five type families: tells 2, 3, 5 and 6). Pick the variant and props that avoid
  them (no `mono`, one family where the component allows it), give it the house palette (below), and look at its frame: two tells or
  more = not used;
- **inside kit3's look**: the creator's one accent only on what the voice names now, kit3's credit line, the grid's content box.

When a video needs a kit 2 form a second time, the form moves into kit3 on kit3's tokens, with a unit test and a demo section (the way
every shared piece enters kit3), and kit3's version is used from then on.

## What every kit 2 component follows (and why)

| The fault it prevents | The rule in the code |
|---|---|
| Items of one graphic at different sizes, tilted, off one line, one almost off screen: lopsided, not thought through from a professional editor's view | One system per graphic: every item the same size, upright, on one baseline; a year with two items stacked with one fixed gap; "lit" is an outline, never a size change; the camera frames a **range** and eases between ranges in one move; whatever nears the frame's edge fades out before it is cut (`edgeFade`) |
| A zoom in, a pause, then a zoom in again: stuttery | **One eased camera move per card from its first frame** (`useDrift`): no settle, no drift-stop-push. `qa_camera.mjs` / `qa_zoom.py` verify it (one hump of screen speed per card) |
| A company named small in a corner, almost hidden | A name is a **Lockup**: big and centred, three styles. A company, product or place is shown by its picture, face, logo or footage first; the name in type only where none exists |
| Numbers shown the same way one to one in every video | **BigNumber** in four styles and **StatCard** in three; the variant varies between videos (below) |
| Plain, bland graphics: flat boxes | Material: a ground with a key light and texture, surfaces lit from the top left, a two-layer shadow (inside kit3's never-list: no glows, no borders) |

**Variety between videos is in the devices, never in the brand.** Before a build, list the components the last three videos used with
their variant (`PIPE tools/motion/reuse_check.py <video> --last 3` reads it from the asset ledger); this video takes other variants where
it uses the same form. Colours, type and the card are the brand's and repeat; a graph or a line is never taken one to one from another
video (rebuilt inside the style).

## Using it

```tsx
import {Timeline} from '../kit2/timeline';
import {makePalette} from '../kit2/core';
import {BRAND, PAPER} from '../brand';
const P = makePalette('house', {bg: [PAPER, '#000000'], accent: BRAND});
<Timeline dur={dur} palette={P} variant="covers" events={MODELS} range={[1996, 2024]} view={[[0, 1996, 2004], [1.9, 1996, 2024]]}
  pops={...} lit={['2024_model']} litAt={2.9} source="the maker's model history · Source: the maker's annual report" />
```

- Every component takes `dur` (its seconds on screen) and times everything in **local seconds** (`at`, `pops`, `hlAt`, `view[i][0]`), the
  way kit3 does (`w(beat, phrase) - t0` gives them).
- `palette`: a `Palette` object. The house palette is built with `makePalette` from `src/brand.ts` (its ground and the one accent), so
  kit 2 draws in the creator's colours; `paper` (a light ground) only where the words are a printed document.
- At a cut a graphic starts in its settled state: components with `at` default to 0 (present on the first frame); an `at` over 0 means
  the graphic lands on a picture already on screen (the backdrop dims then).
- Pictures passed as `children` sit behind the graphic, dimmed and softened (BigNumber, StatCard, Lockup, QuoteCard).
- Covers and photos: `aspect` crops every cover to one shape (height over width, e.g. 1.28); a photo gives its natural `w`/`h` and is never
  upscaled.
- Sources: `source` draws the small source line inside the safe area (96 / 54 px); in a video, the credit goes through kit3's `Credit`
  (one line, bottom right).
- Previews run on their own small public dir (hard links); a video's build uses its own lean public dir as always.

## The components

### Timeline (`timeline.tsx`)
`events: {year, label, img?, key?, major?}[]`, `range`, `view: [t, firstYear, lastYear][]` (the camera frames these years from `t`),
`variant: 'covers' | 'blocks'`, `pops` (event i lands at pops[i]), `lit`/`litAt`, `dim`/`dimAt`, `gap: {from, to, at, text}`, `emptyW` (an
empty year's width, 0.42 of a release year; blocks: always 1), `title`, `kicker`, `source`.
- **covers**: the real pictures (album covers, book covers, product shots) on one baseline, equal, two of a year stacked. For "six
  albums in ten years, then one in nine".
- **blocks**: a calendar strip: every year an equal cell, releases filled, empty years hollow. The gap *is* the picture. A strike lives
  inside its words' own box (`Gap`).
- (`ticks`, labels alternating above and below the line, is retired: labels of one kind sit on one side of the axis.)
When: a run of dates where the spacing is the point. Camera: one eased move per `view` pair; frame the range the words name. kit3's
`Timeline` (true distances, measured labels) comes first.

### BigNumber (`numbers.tsx`)
`value` (number -> commas; string as typed), `prefix`, `suffix`, `label`, `source`, `at`, `variant: 'odometer' | 'slam' | 'flip' |
'wipe'`, `size`, `roll` (odometer/flip seconds), `children` (a picture behind).
- **odometer**: drums roll to rest, the right digits spinning most, smeared while they move. A count that "arrives".
- **slam**: from far and big to sharp in 0.3 s, a shake and a ring of light. A number that hits (the one shake of the video).
- **flip**: a split-flap board, digits flipping left to right. Years, dates, totals on a board.
- **wipe**: the outline stands, the accent fills behind a bright edge. A quiet reveal under a calm line.
When: one number that must land on its word. Never two of these in a row; never the same count-up in every video. A number always beside
its picture (a number alone over blur is the AI-template "hero" look): kit3's `NumberBeside` first.

### StatCard (`numbers.tsx`)
`items: {value, label, delta?: {text, up}, sub?}[]`, `variant: 'tile' | 'strip' | 'ring'`, `pct` (ring, 0..1), `at`, `title`, `kicker`,
`source`, `children`.
- **tile**: one card: label, the number revealed from under a mask, a change chip, a sub line.
- **strip**: 2-4 tiles landing one after another (a dashboard of one fact).
- **ring**: a share as a ring closing to its percentage, the number inside, its "x of y" and its subject said on the ring (a ring with
  no "1 of 6" and no subject reads as nothing).
When: a number with its context (a change, a share), or several numbers of one kind at once.

### Compare (`bars.tsx`)
`items: {label, value, display?, hot?, sub?}[]`, `at`, `per` (stagger) or `ats`, `variant: 'bars' | 'columns' | 'split'`, `ratio: {text,
at}` (a "19x" badge), `title`, `kicker`, `source`, `unit`.
- **bars**: horizontal, labels left, values riding the ends. Two to five things.
- **columns**: on a baseline, the value above each; a dashed guide at the small one's height carries the "x N".
- **split**: one bar, 100%, cut into named parts. A breakdown.
- (`squares`, nested squares by area, is retired: it reads as low effort and incoherent.)
When: a number against another. The `hot` item takes the accent; everything else stays ink. The graph's form follows its point (a share:
a donut or a split; a contrast: two sides; a count: units; growth: before/after), labels once on one side, no guide lines but the one
that carries the ratio.

### Ranked (`bars.tsx`)
`items: {name, value?, img?, sub?, round?}[]`, `variant: 'rows' | 'podium' | 'ladder'`, `hot` (the index in the accent), `at`, `per`,
`title`, `kicker`, `source`, `aspect`.
- **rows**: rank, picture, name, value; up to eight. **podium**: 2nd, 1st, 3rd on plinths, the first rising last. **ladder**: two tight
  columns for ten.
When: an order. Pictures are equal boxes; never round crops of screenshots (`round` only for real face icons made by `make_icon.py`).
A ranking that changes over time glides as kit3 §1.6 says (the places fixed, the hero row passing).

### Lockup (`type.tsx`)
`lines: (string | {t, color?, w?})[]`, `kicker`, `sub`, `variant: 'stack' | 'wide' | 'plate'`, `face: 'display' | 'sans' | 'cond'`,
`width`, `at`, `children`, `ground` (false: over whatever is under it).
- **stack**: every line set to the same ink width (`fitText`), revealed from under a mask line by line.
- **wide**: one tracked line between two rules, its letter-spacing closing as it arrives.
- **plate**: an accent bar draws, a plate wipes open with the name and its line ("a small bakery in a small town").
When: a name, a place, a title, only where no picture of it exists: big, centred, never a corner label.

### LowerThird (`type.tsx`)
`name`, `role`, `at`, `out`, `variant: 'plate' | 'line' | 'tag'`, `x`, `y` (default the safe area, lower left).
- **plate**: accent edge + a translucent plate, wiping in from the left and back out. **line**: name · role on one baseline, an accent
  rule drawing under. **tag**: the role as an accent tag, the name revealed under it.
When: who is on screen, on their first picture (a name and a job). In and out are one move each. The name's one place for the whole
video (kit3's `TagShot` top right, or on the person) wins when they differ.

### QuoteCard (`type.tsx`)
`quote`, `who`, `where`, `hl` (the phrase the voice reads), `hlAt: [t0, t1]` (lit word by word across it), `variant: 'serif' | 'sans' |
'paper'`, `push` (default 1 -> 1.045, one move), `at`, `children`.
- **serif**: a serif face, a big faint opening mark behind, an accent rule before the attribution. The pull quote.
- **sans**: a heavy sans against an accent bar, left-aligned. The blunt line.
- **paper**: a light document card in slight perspective with a header (who, where) and a marker. A filing, a report, a letter.
Dark palettes light the words by recolouring them to the accent; paper uses the marker.
When: the words themselves are the point (pages and quotes stay a minority). A real captured page is kit3's `Page`, and `Read` is the
house quote card: QuoteCard only where neither fits.

### PhotoCard (`pictures.tsx`)
`src`, `w`, `h` (natural pixels), `caption`, `sub`, `source`, `variant: 'print' | 'full' | 'window'`, `push`, `tilt` (print), `origin`
(full), `at`.
- **print**: a paper-bordered print with its caption on the margin, lit on the ground. **full**: the frame filled and graded into the
  palette, a caption lockup lower left (needs 1920 px or more; smaller falls back to print). **window**: a card with a header strip
  (outlet, date).
When: a photo that is not footage. Never blown up past its pixels. kit3's `PhotoFrame` (whole, at most 1.3x, captioned) comes first.

### Covers (`pictures.tsx`)
`covers: {src, name?, at?, lit?, cross?}[]`, `variant: 'row' | 'grid'`, `h`, `cols`, `litAt`, `names`, `title`, `kicker`, `source`,
`aspect`.
- **row**: equal heights on one line, each landing on its word, no rotation; lit = outline, the rest dim; `cross` draws a cross over the
  whole thing.
- **grid**: equal tiles landing row by row; a lit subset.
When: several products or titles named in one breath. kit3's `Row` (visible-pixel centring) first for cut-outs.

### Split (`pictures.tsx`)
`a`, `b: {src, label?, sub?}`, `variant: 'wipe' | 'slide' | 'diagonal'`, `at`, `wipeDur`, `to` (where the divider stops: 0.5 holds a
comparison, 1 reveals b fully), `children: [A, B]` for two clips instead of stills.
When: before/after, then/now, the old version against the new one, each side its real picture from the same kind of framing.

### MapCallouts (`map.tsx`)
`region: 'world' | 'europe' | 'uk' | 'americas' | 'north-america' | 'usa' | [[lon, lat], [lon, lat]]`, `lit: ['<country>']`, `litAt`,
`pins: {at: [lon, lat], label, sub?, show, dx?, dy?}[]`, `route: {from, to, t}`, `zoom: [a, b]` (one move toward `focus` or the first pin),
`variant: 'dark' | 'paper'`, `title`, `kicker`, `source`. Data: Natural Earth 1:50m (world-atlas).
When: a "where" the words name (a company's city, a route, a country). The real Earth flown to a place is kit3d's `Globe3D`
(`standard/3D.md`).

### Edit techniques and transitions (`edit.tsx`)
- **PunchIn** `{at, to, dur, origin: [x, y], back}`: one eased scale toward a point on the word (`dur` 0 = the one-frame punch),
  optionally released at `back`. Never two stages.
- **matchCut(a, b)** / **Matched**: the transform that lands shot B's subject on shot A's (same place, same size) at the cut; `settle`
  eases it to B's own framing.
- **SpeedRamp** `{src, start, from, to, at, ramp}`: footage from `from`x easing to `to`x (1.0 or more, always: clips are never slowed) in
  one ramp; `rampSourceTime` for the checks. (It reports its clip to the gate's probe, as `lib.tsx`'s `Clip` does.)
- **BlockWipe** `{at, palette, dir}`: three palette blocks sweep over the cut (the cut at `at`).
- **ColorFlash** `{at, palette}`: the flash in the palette's accent. **Iris** `{at, from, children}`: the next shot opens from a point.
The house whip and dive (`house/motion.tsx` `CUT.whip`, `CUT.dive`) stay for `TransitionSeries`. Most changes remain hard cuts.

## What the preview rounds caught (check a new or changed component for the same)

Labels colliding on adjacent years; a timeline's camera moving from frame 0 instead of on its key word; drums on half digits and a flip
board on a random number before the word; a ratio badge cut at the frame's edge; a 0-px square drawn as a dot before it grew; the lowest
podium plinth cutting its value; a three-line stack running off the frame (fitted to its width only); a line clipped at both ends (type
measured before its font had loaded); a quote breaking mid-phrase (the lit phrase was one unbreakable run); gaps in the marker between
lit words; every map region framed as the whole world (the bounding ring wound the wrong way for d3-geo); a split's handle half off the
edge at 100%; a block wipe's last block not covering the frame at the cut; a marker sliver before each lit word on a paper quote's first
frame. Every one of these is a fault the stills show, at the first frame, at 1.2 s and at the end state.

## Checks before a kit 2 graphic goes into a video

- [ ] kit3 has no piece for this form (else kit3's is used).
- [ ] Real material inside it; run through the AI-template checklist (`standard/LONG_FORM.md`): fewer than two tells, in the house
      palette, no monospace, no glow, no card edge line.
- [ ] Stills at the card's first frame, 1.2 s and its end state (`stills.mjs`): equal sizes, aligned, nothing cut at an edge, the safe
      area kept, every text box inside its card at its end state.
- [ ] `node tools/motion/qa_camera.mjs src/<video>/<Comp>.tsx`: every card ONE MOVE; on a render `EDIT tools/motion/qa_zoom.py`.
- [ ] Readable at phone size: a 480-px-wide copy of the still still reads (labels 40 px or more at 1080p, kit3's smallest readable size;
      values 40 px or more).
- [ ] Not the last three videos' variant for the same form.
- [ ] Every number from a source in the script's facts table; the credit line names it; every number with its unit and subject.
