# AI slop vs premium: what the look is, what top channels do, and the redesign brief

*The question: what makes a narrated video's visuals read as AI slop versus premium, what top channels do instead, and the
redesign brief that follows. Read with `standard/research/MOTION_CRAFT.md` (motion principles and tools),
`standard/research/MOTION_LAB.md` (what was built and tested) and `standard/research/FOOTAGE_SOURCING.md` (paid stock prices).
Every source was read with WebFetch, curl or the Wayback Machine. No browser was used.*

*Grades:*
- ***A*** *= primary or measured: a licence or policy text itself, our own count in our own graphics code, or our own look at the real video frames (measured by us).*
- ***B*** *= the maker's own docs: a vendor or studio describing its own product or work.*
- ***C*** *= an expert practitioner, or an independent analysis.*
- ***D*** *= anecdote or marketing, including vendor blogs that sell the fix.*

**Limits of this pass**
- **YouTube was read through its public watch page, signed out.** That gives the title, date, chapters and storyboard frames
  (YouTube's scrubbing thumbnails: 320×180 or 160×90 px, one every 5-10 s).
  - Timestamps are ±5-10 s.
  - Motion can't be judged from stills: easing, blur, transitions. Those points lean on `standard/research/MOTION_CRAFT.md`.
- **Some sites refused**, with the workaround named next to each claim (a search summary or a Wayback copy):
  - Reddit (403/429): not quoted.
  - uxdesign.cc (403), aescripts (403), Adobe's Mixamo FAQ (403) and ActionVFX (403/429).
  - noaa.gov's library (405), and the archive.org PDFs (timed out).
  - usgs.gov (403, and its Wayback copy didn't load): the USGS line in §5 rests on US law for federal works, not its page.
  - sec.gov (403 to a script that declares no contact): EDGAR is named from its own address only.
- **Sources are paraphrased.** There is one short quote.
- **Nothing was rendered.** Every item in §5 is a design to build in the motion lab and A/B against the reference frame named
  for it.
- **Some channels we studied are described, not named or linked** (two hardware-review channels, a maker's own feature
  explainer and a software maker's launch video). Their findings stay as our own observations (A), with what
  we saw.

---

## 0. The answer in short
1. **"AI slop" in graphics means the default look.** It is what a model makes when nobody chose anything:
   - dark navy cards with one or two neon accents, and glows
   - tracked-out caps labels, the Inter font, monospace "data"
   - big centred numbers
   - drawn shapes standing in for real things

   Anthropic's own design guide lists these traits as what AI-made design clusters around (B).
2. **One of our own builds was that default.** Measured in its code (A):
   - a navy palette (`#0b1822` → `#03070b`) with teal `#3FE0D0` and pink `#FF4FA3`
   - palette tokens literally named `card`, `cardEdge` and `glow`
   - a caps "kicker" label tracked at 0.28 em
   - four font families in one video, and 69 letter-spacing settings
   - 56 rounded-corner settings (31 of them 10-18 px, 8 pills), and 47 shadows or glows
3. **No premium channel we checked draws a stand-in for a real thing.** They show the thing itself: the real frame from the
   source, the real page, the real UI, a real photo, a real 3D render, or a physical demo. Their graphics annotate that material
   (boxes, zoom insets, lines, labels) instead of replacing it.
4. **A technical point is best shown by its own footage, not by a diagram.** A long breakdown can run without one drawn
   diagram: the source video is looped, cropped and slowed. Comparisons show the same view in several versions as 2-4 labelled
   slices, and real measurements are plotted one point per sample (the hardware-review channels we studied plot that way, A).
5. **Drawing can be premium, but only at full craft.** Kurzgesagt uses a dark, neon palette like the default look. It reads
   premium because every scene is lit, detailed and art-directed, at about 1,200 hours a video (their own figure, B). Code can't
   reach that soon, so real material is the route.
6. **A number belongs in its source:**
   - MKBHD shows Apple's own chip graphic for the transistor counts.
   - LTT shows Intel's own slides, with one red arrow.
   - ColdFusion shows the real post.

   A big-number card is the AI default (B).
7. **Data charts are the one place flat graphics are fine**, when the data is real and the template is one plain house style (LTT,
   PolyMatter, and the hardware-review channels we studied). A cost-split bar in one of our builds was worse
   than flat: its boxes looked like data that nobody had measured, so it was slop and an unbacked claim at once.
8. **The real assets are free or cheap, and licensable:**
   - rain on black (Pexels, Pixabay, Mixkit)
   - lightning, smoke and dust plates with alpha (ActionVFX's free packs)
   - satellite and radar imagery (NOAA, NASA: public domain, with credit)
   - CC0 3D scenes (Poly Haven, Blender's demo files)
   - and, above all, the primary source's own material and UI (the maker's official videos, press kit, site)
9. **The brief (§5):**
   - The footage is the palette.
   - One type family.
   - Real materials only.
   - Three depth planes and one camera move.
   - Annotations attached to the real thing.
   - One orchestrated move per beat.

   Six worked examples are there.
10. **The quick test:** redo a frame if it could illustrate another video by changing its words, or if a shape in it stands for
    something we could show instead.

---

## 1. The AI-slop tells: a checklist to run on a frame

**What people mean by it**
- **The word:** Merriam-Webster named "slop" its 2025 Word of the Year on 2025-12-14, defined as low-quality digital content,
  usually mass-produced with AI (B, via AP and TechCrunch).
- **How common it is:** Kapwing's report (2025-11-28) found that 104 of the first 500 Shorts (21%) shown to a new account were
  AI-generated (C).
- **Creators push back:** Kurzgesagt's "AI Slop Is Killing Our Channel" (2025-10-07) promises to stay human-made (C, listing
  pages only).

So viewers now look for the signs.

**In design, it means the default**
- **Why models converge:** Anthropic's post on its frontend-design skill (2025-11-12) calls it distributional convergence. A
  model samples the most common, safe choices in its training data, so without direction it lands on the same look every time (B).
- **What it converges on:** the skill's current version (commit of 2026-09-03) lists the traits AI-made design clusters around.
  It calls them "defaults rather than choices", which show up whatever the subject is (B).
- **It applies here:** this repo's graphics are written by an AI, in Remotion code.
- **The Claude + Remotion look:** a template seller describes 2026's Claude + Remotion videos (D: it sells the fix):
  - a dark background, a glowing headline and a soft gradient blob
  - every element entering with the same spring
  - type filling the frame, because the model has no other material to show

**Why it costs**
- **YouTube:** its monetization policy, last updated 2025-07-15, refuses to monetize AI-made content built on generic templates
  that looks mass-produced (A). A narrated video with its own script isn't in that group, but the platform clearly reads the
  template look as low value.
- **The house standard** treats it as a quality failure (`standard/LONG_FORM.md`).

### The checklist
Run it on the frame sheet before a render. **Two or more tells in one frame means redo.** The last column was measured by us in
the code of one of our own builds (A) unless it says otherwise.

| # | Look for this in the frame | Who names it (grade) | In a build we measured |
|---|---|---|---|
| 1 | **A near-black or navy field with one or two neon accents** (teal, pink, acid green) | Anthropic: near-black plus one bright accent; tinted near-blacks such as #111 standing in for black (B). Fountain Institute: neon palettes and an aurora-like glow in the background (C). Better Images of AI: blue is the stock colour of technology and reads clinical and distant (C) | Palette `#0b1822`→`#03070b`, `#3FE0D0`, `#FF4FA3`; the shared kit's neutral palette used an acid-green accent; `#111111` five times |
| 2 | **Everything in identical rounded cards**: thin bright borders, one corner radius, the same soft shadow | Anthropic: its SaaS card-kit trait (B). Fountain: cards on cards (C). prg.sh and superdesign: rounded corners everywhere, shadows at 0.1 opacity (C, D) | Tokens `card` and `cardEdge` in every palette of the shared kit; 56 corner radii in the video: 10-18 px 31 times, pills 8 times |
| 3 | **Glow**: outer glows, text glows, gradient blobs, light behind type | Fountain (C). Mika Reyes: glossy effects; her fix bans glow (C). The template seller, on Remotion videos (D) | A `glow` token in every palette; in the video, 21 box shadows, 12 text shadows, 14 drop shadows |
| 4 | **A tracked-out ALL-CAPS label above every heading** (the "eyebrow"), often condensed | Anthropic: the first item of its template-chrome trait, and all-caps labels are on its list of typographic tells (B). Venngage: caps subtitles with uneven spacing (D) | `Kicker`: Inter 700, caps, letter-spacing 0.28 em; 69 letter-spacing settings in the video |
| 5 | **Monospace "code" type** for data and sources, or to signal "technology" | Anthropic: a monospace face for small data labels (B). Better Images of AI: "descending code" as a technology cliché (C) | JetBrains Mono, 11 uses in the video (sources, receipts) |
| 6 | **Default fonts, and too many of them**: Inter, Roboto, Arial, system fonts, Space Grotesk; three or more families | Anthropic's post: Inter is what the model reaches for (B). prg.sh, superdesign (C, D) | In the video: Barlow Condensed (70 uses), Inter (15), JetBrains Mono (11), Anton (10). The motion code also loaded Montserrat, Roboto, Poppins and Space Grotesk |
| 7 | **A big number with a small label**, centred, on a card or over blurred footage | Anthropic: the default "hero" treatment (B) | A centred video-length card; an odometer counting up to a big total |
| 8 | **Shapes standing in for real things**: people built from rounded shapes, an SVG sun or tree, rain as white strokes, a box with the thing's name written in it | The template seller: the model fills frames with type and shapes because it has nothing else (D). The review of that build flagged each one (A) | Figures built from rounded shapes; a natural event drawn as a blob; cost-share boxes |
| 9 | **A fake UI**: an invented app card ("SCORE 98%"), status dots, thin line icons, emoji | Fountain: status dots, emoji (C). 925studios: interchangeable thin line icons (D) | An invented app card for a product |
| 10 | **Centred and symmetric, with every scene in the same layout**: no single focal point, every inch filled | prg.sh: a centred hero plus three boxes (C). Mika Reyes: no breathing room; one size of one sans (C). Venngage: unrelated designs that look the same (D) | Check on the frames |
| 11 | **The same entrance for everything**: each element fades and slides up, or pops with the same spring | Anthropic: fade-and-slide-up entrances on every section read as AI-made (B). The template seller (D) | The kit's `TitleBlock` rises 12 px with an opacity fade |
| 12 | **Fake data**: bars or proportions that look measured but aren't | The house line on unmeasured claims (`rules/SHARED.md`; not a design source) | The cost-split bar implied shares that nobody measured |
| 13 | **No real material in the frame**: no footage, photo, page capture, real UI or real render | The template seller (D). Every premium example in §2 is the counter-case (A) | Count it per frame sheet |
| 14 | **If any picture is AI-generated**: plastic skin, perfectly even light, creamy bokeh, garbled text, shadows that disagree | Trend Micro and the Canadian Centre for Cyber Security (C, via search). 925studios on Midjourney's house style (D) | Generate no pictures; skip AI-generated stock (Pixabay labels some) |

**What is not a tell on its own.** Caps labels, a dark chart background or a monospace axis can be premium when they form one
consistent house system on real data:
- PolyMatter sets condensed caps titles with small axis numbers on one brand red.
- LTT's chart template sets italic condensed caps titles on every chart (§2).

A tell is a default that appears whatever the subject is.

**The quick test: five questions per graphic**
1. Is there real material in this frame? If not, redo it.
2. Does any shape stand for a real thing we could show? Then show the thing.
3. Could this frame illustrate another video if we changed its words? Then it's a template.
4. How many tells from the table does it have? With two or more, redo it.
5. Does any number or proportion claim something nobody measured? Source it or remove it.

---

## 2. What premium looks like: techniques with examples
The timestamps were read off YouTube's storyboard frames, so each is ±5-10 s. Every row is A (observed) unless marked.

| # | Technique | See it here | Tools, where documented |
|---|---|---|---|
| P1 | **Real material inside every graphic**: diagrams are built from real frames, renders or photos | A maker's own feature explainer we studied: a flow chart whose two ends are real pictures (observed by us). · Vox, an explainer on how 3D models are built (2019-01-10), 3:20: a real 3D teapot goes from wireframe to shaded to textured | — |
| P2 | **Annotate the real frame instead of redrawing it**: a box on the region, a magnified inset, labels such as "2x ZOOM" and "50% SPEED"; in a long breakdown, minutes of punch-ins on one small detail of the source | — (plain craft) | a synced side-by-side compare in the edit itself (up to 4 clips, a slider, zoom and pan) |
| P3 | **Same-camera comparisons**: 2-4 vertical slices or a split of the identical view (or of two versions of the same surface), labelled at the bottom, with the measured value on top | — (plain craft) | a synced compare in the edit |
| P4 | **Measured data, drawn plainly**: one point per sample on an axis in real units, one house chart template, one highlight colour | A hardware-review channel: interval plots, one point per sample. · Another hardware-review channel: bars under a header that carries a real screenshot of what was tested, with an orange "% faster" highlight (all observed by us) | — |
| P5 | **Numbers shown in their source** | MKBHD, "I shrunk down into an M5 chip" (2025-12-26), 0:20: Apple's own chip graphic with the transistor counts. https://www.youtube.com/watch?v=Jh9pFp1oM7E&t=20s · LTT, Core Ultra 270K Plus review (2026-03-23), 3:55-4:55: Intel's own slides with one red arrow. https://www.youtube.com/watch?v=lSSkQnHWisM&t=235s | — |
| P6 | **A number that must stand alone sits in the scene**, next to the object it measures, with units | Cleo Abram, "The Sun Is Weirder Than You Think" (2026-09-30), 3:30 and 4:30: speeds and distances set beside the probe and the sun, inside a 3D scene. https://www.youtube.com/watch?v=eNkxTjirY-Q&t=270s | — |
| P7 | **Real sources in their own interface**: posts, essays, news clips with the broadcaster's own lower third, websites tilted in 3D | ColdFusion, "The AI Industry is a Complete Mess" (2026-10-01), at 1:00, 1:30, 2:40 and 5:30. https://www.youtube.com/watch?v=e2zjpCqTmyo&t=90s · PolyMatter, "The Entry-Level Job Crisis" (2026-06-12), 1:40-2:00: real articles with a highlight. https://www.youtube.com/watch?v=j2QEieIiiXg&t=100s | The repo's page component (`tools/motion/src/kit3/page.tsx`, `standard/KIT3.md`) already does this (`standard/research/MOTION_LAB.md`) |
| P8 | **Physical demonstrations of invisible things** | A hardware-review channel we studied: Schlieren imaging shows the hot air leaving the device (observed by us). · Vox's 3D-models explainer, 3:45: the host holds a paper triangle. · WSJ, "How Noise-Canceling Headphones Create Silence" (2023-06-12), 1:10: an engineer draws the sound wave on a real whiteboard. https://www.youtube.com/watch?v=c10LhVego4o&t=70s | Schlieren optics (named in that channel's chapter title) |
| P9 | **The explanation lives inside a real-looking 3D scene**: labels sit in perspective, and the camera moves through the scene | Branch Education (two explainers, observed by us): the mechanism drawn through a photoreal room, then a before and after shown as two real renders of the same scene. · Cleo Abram, 3:30 (P6): numbers and the probe inside a 3D scene of the sun | Blender 4.2 and Blender's free demo scenes (their own description, B) |
| P10 | **Scale with real anchors**: a figure at true scale beside real objects, in real footage | MKBHD with Epic Spaceman, 2:00-4:50: a CG presenter at true size on a real logic board, with a rice grain and a banana as anchors. https://www.youtube.com/watch?v=Jh9pFp1oM7E&t=230s · The Weather Channel, "Storm Surge in Your Home" (2019-10-10), 0:30-0:48: surge heights as labelled lines on photoreal water inside a room. https://www.youtube.com/watch?v=uphdsq4cG-g&t=30s | Epic Spaceman: Blender and a Rokoko mocap suit (Rokoko interview, C). The Weather Channel: Unreal Engine through The Future Group, driven by hurricane-centre data (80.lv, C) |
| P11 | **Maps and weather made from real imagery** | Wendover, "The Incredible Logistics Behind Weather Forecasting" (2022-06-29), 2:10-2:40: a globe textured with satellite imagery and real station dots; at 6:20, a forecaster at a real radar screen. https://www.youtube.com/watch?v=V0Xx0E8cs7U&t=130s · Johnny Harris, "American-Backed Coups, Mapped" (2023-02-09), 1:20-1:50: paper-textured maps. https://www.youtube.com/watch?v=_wIOqHSsV9c&t=80s | Johnny Harris's video descriptions name the GEOlayers plugin for After Effects as his map tool (A) |
| P12 | **Texture and material**: paper, film frames, archival pages, real photo cut-outs pinned to places | Johnny Harris, 4:30-4:40: real portraits in round cut-outs on the map; at 5:10 and 6:00, real book and newspaper pages. · Bloomberg Originals, "The Race to Build a Perfect Computer Chip" (2022-11-10), 3:30: paper-white art in an engraving style. https://www.youtube.com/watch?v=VsUF_CBJq50&t=210s | Vox: graphics animated at 12 fps ("on twos"), with a boiling texture (PremiumBeat 2021, C, via `standard/research/MOTION_CRAFT.md`) |
| P13 | **One house system with few fonts and one accent**, kept for years | PolyMatter, 1:10-1:30 and 4:30: every chart on one brand red, with yellow and white data, a condensed caps title and small axis labels. https://www.youtube.com/watch?v=j2QEieIiiXg&t=70s | — |
| P14 | **Illustration only at full craft** | Kurzgesagt, "AI Just Crossed the Terrifying Line" (2026-10-05), 2:50: a lit, detailed isometric room. It is dark navy with neon accents, like the default look, but every scene is lit and art-directed. https://www.youtube.com/watch?v=ujkD4SxPKOI&t=170s | About 1,200 hours and 200 Illustrator panels per video, with 2-3 illustrators for 8-12 weeks (their 2020 making-of, https://www.youtube.com/watch?v=uFk0mgljtns, B) |
| P15 | **Restraint**: long stretches of pure footage, and graphics only where footage can't show the point: a long breakdown can go many minutes with no drawn diagram, the source video looped, cropped and slowed while the voice talks | — (plain craft) | — |
| P16 | **Motion**: one camera moving through one space, eased, with motion blur on fast moves | Not visible on storyboards. See `standard/research/MOTION_CRAFT.md` §2 (LEMMiNO, fern; B and C) | `HtmlInCanvasMotionBlur` (`standard/research/MOTION_LAB.md`) |

### Channel by channel: what makes each one premium
- **Johnny Harris** ("American-Backed Coups, Mapped", 2023-02-09):
  - Paper-toned maps: cream land, sage-green sea, ochre for the subject.
  - Real portraits and seals pinned to places, with a timeline scrubber along the bottom.
  - Archival photos in film frames, and real pages.
  - He presents in front of a real wall map.
  - Tool: GEOlayers, named in his descriptions (A).
- **Vox** (the 3D-models explainer, 2019-01-10):
  - Real footage of the finished 3D product, and real editor viewports in wireframe (1:30-1:45).
  - A real 3D render progression (3:20), and a paper triangle in the host's hand (3:45).
  - A flat white triangle on black appears only as one brief beat (2:40).
- **PolyMatter** ("The Entry-Level Job Crisis", 2026-06-12): one bold colour system for every chart. Real articles with
  highlights, and stock footage between them. Flat can be premium when it is one opinionated system on real data.
- **Wendover** ("Weather Forecasting", 2022-06-29):
  - Maps on satellite imagery, and real equipment footage (radar domes, balloons, forecasters' screens).
  - The description names an animation lead.
- **Cleo Abram** ("The Sun", 2026-09-30):
  - 3D scenes built on real solar imagery, with numbers and units placed beside their objects.
  - Experts on video calls, and real lab footage of the probe.
  - A real torch test filmed in the lab (6:10), and sound waveforms laid over real imagery (6:50).
  - Her method: find the key visual first, then let it shape the story (her 2022 interview, B).
- **MKBHD with Epic Spaceman** (2025-12-26): the official vendor graphic for the numbers, and a true-scale composite into real
  macro footage.
- **Linus Tech Tips** (2026-03-23):
  - The LTT Labs chart template: dark, italic condensed caps titles, team-coloured bars, an outline highlight on the rows
    compared.
  - The vendor's own slides, annotated.
- **A hardware-review channel we studied** (observed by us):
  - A light chart template whose header carries a real screenshot of what was tested.
  - Product B-roll with toy props (1:40-2:30).
  - Results under the heaviest and the lightest test load, in two chapters of their own.
- **Another hardware-review channel we studied** (observed by us): a measurement plotted one point per sample, and Schlieren
  imaging.
- **ColdFusion** (2026-10-01): every claim shown in its original interface, whether a post, an essay, a broadcast or a website.
- **Kurzgesagt** (2026-10-05): full illustration, lit and detailed. This is the exception that proves the craft bar.
- **Bloomberg Originals** (2022-11-10): restrained editorial line art on off-white paper, real fab footage and interviews.
- **WSJ "Tech Behind"** (2023-06-12):
  - A real whiteboard, photoreal 3D renders of the product with thin labels, and macro shots of the product.
  - The end credits name the animator and the stock sources: Storyblocks, AP, Getty (6:20).
- **NYT Visual Investigations:**
  - 3D reconstructions built with photogrammetry (RealityCapture) and Blender.
  - Satellite imagery from Planet and Maxar in almost every story.
  - Source: GIJN's 2019 interview with Malachy Browne, read through a search summary (C).
- **A maker's own feature explainer** (observed by us): diagrams built from real pictures, splits with zoom boxes, and the
  measured values on screen.
- **A software maker's own launch video** (observed by us): the program's own inside view (its debug display) cut into the
  finished result.
- **Branch Education** (observed by us): explanations inside photoreal Blender scenes, with real renders as the proof.
- **The Weather Channel** (Immersive Mixed Reality, 2019-10-10): data lines on photoreal 3D water, driven by live data.

**Type in these channels.** Most use one or two families. Condensed caps labels do appear (Johnny Harris, PolyMatter, LTT), always as one fixed house style on real material. No font names could be confirmed from 320 px frames.

---

## 3. Technical concepts: the premium way to show each

The pattern carries to any invisible mechanism in any niche (a chemical reaction, an algorithm, a market mechanism, a machine,
a body): **measure it, take the real thing apart, show the same view two ways, show the tool's own inside view, render the
mechanism in a real scene, or demonstrate it physically.** The cheap version is always a drawn symbol. Each example below names
public sources; check each item's own licence before use.

**What's inside a device (a phone, an engine): take the real thing apart.**
- **The real thing, opened:** a repair site's teardown. iFixit publishes step-by-step teardown photos and videos of new phones
  and laptops. Its content is CC BY-NC-SA 3.0, which bars commercial use, so on a monetized channel treat it as another
  creator's material (short, credited, in commentary) or ask iFixit for a licence (its licensing page, B).
- **For engines and machines:** museum cutaways. Wikimedia Commons has categories of real cutaway engines (cars, motorcycles,
  aircraft); use the CC0, public-domain or plain CC BY files (§4).
- **Annotation:** a box on the part the voice names, a label pinned to it, and a magnified inset of the real photo.
- **Cheap:** an exploded drawing of grey rounded rectangles.

**What's inside a body (a medical point): the tool's own inside view.**
- **The scanner's own images are the inside view:** a real CT or MRI series, scrolled slice by slice, with the organ outlined as
  the voice names it.
- **Where to get them:** The Cancer Imaging Archive hosts de-identified public scan sets. Most collections are CC BY 3.0 or 4.0;
  a few carry non-commercial or data-use limits, and the licence is stated per collection (its usage page, B). Wikimedia Commons
  has scan images and slice animations under per-file licences.
- **Cheap:** a glowing organ inside a drawn body outline.

**A market move (why a price changed): measure it, and show the number in its source.**
- **The measurement in its own interface:** the real price chart for that day, captured from a public finance page, or the
  business channel's own on-air chart as a short credited clip.
- **The cause as its real document:** the company's filing on the SEC's EDGAR system, or its own press release, captured as a
  page, with the sentence highlighted and its time set beside the drop on the chart. (sec.gov refuses scripts that don't
  declare a contact: the creator opens it in a browser.)
- **If the chart page can't be captured cleanly,** plot the real prices in the house chart template, with the source on screen.
- **Cheap:** a red arrow pointing down on a dark card.

**Flow through a city (traffic, a subway at rush hour): the mechanism in a real scene, and the same view two ways.**
- **The data on a real map:** the city's own open data, drawn on an OpenStreetMap base. Transport for London, for example,
  releases its public data free for developers (sign-up needed; check its terms). OpenStreetMap is ODbL: credit OpenStreetMap
  and its contributors and name the licence (its copyright page, A).
- **The same view two ways:** one real camera position on the platform or the street, at rush hour and at midday (filmed, or
  from stock), as a split or a slider.
- **Then the real scene:** footage of the crowd at the busiest station the data names.
- **Cheap:** dots sliding along drawn lines on a navy field.

**Weather.**
- **The Weather Channel:** labelled data lines drawn on photoreal water
  (https://www.youtube.com/watch?v=uphdsq4cG-g&t=30s).
- **Wendover:** a satellite-textured globe and real forecaster screens.
- **The forecaster's own material:** the national weather service's own radar loops and briefing graphics for that storm (NWS
  pages are public domain unless noted, §4), credited.
- **To build it:**
  - real NOAA GOES satellite loops (public domain, credited)
  - real radar
  - real rain plates
  - then the real storm on the ground (a local station's report or a storm chaser's clip, credited)
- **Cheap:** a dark blob with white strokes (tell 8).

---

## 4. Where to get premium real assets (free or cheap, licensed for monetized YouTube)
The licence lines are paraphrased; the links go to the full text.

| Source | What's there | Key licence line (paraphrased) | Credit? | Grade |
|---|---|---|---|---|
| **Pexels** https://www.pexels.com/license/ | Rain on black, e.g. video 36344044, "Heavy rain falling on black background" (search https://www.pexels.com/search/videos/rain%20overlay/); storms, cities, people | Free to use and modify, no attribution needed. Don't: show identifiable people in a bad light, sell unaltered copies, imply endorsement, or re-upload to stock sites | No | A |
| **Pixabay** https://pixabay.com/service/license-summary/ | Many 4K rain overlays (https://pixabay.com/videos/search/rain%20overlay/), storms, film textures | Free, no attribution, may modify. No standalone resale; no commercial use of content showing recognisable trademarks or logos; no misleading use. The summary isn't binding: the full terms are at `/service/terms/`. **Some items are AI-generated: skip those** | No | A |
| **Mixkit** https://mixkit.co/license/ ; https://mixkit.co/llm-info/ (updated December 2025) | Rain, lightning ("Lightning Strike and thunders"), weather clips | The **Free License** allows commercial use, including YouTube, with no attribution. The **Restricted License** is personal and non-commercial only. Check each clip's label | No | A |
| **ActionVFX** https://www.actionvfx.com/license (the Wayback copy of 2026-04-12; the live site refused) | Free packs captured on Wayback in 2025-26: lightning, smoke plumes, dust wave, snow FX, lens-dirt overlays, surface imperfections, camera-shake presets. Many come pre-keyed as ProRes 4444 with alpha (CG Channel, C) | One lifetime licence covers both paid and free products. Use them in nearly any project, internet content included, as long as you add substantial value. The Individual tier gives full commercial rights below $200k a year in revenue. No AI training. Free packs rotate, and some are time-limited (CG Channel, 2026-01-08) | No | A (licence), C (packs) |
| **Videvo → Freepik → Magnific** | Stock video | videvo.net now redirects to freepik.com/videos. Freepik's legal pages redirect to magnific.com; reports date the rebrand to 2026-04-28 (C). Magnific's terms (June 2026) make free use conditional on attribution; Premium removes it | Yes, on the free plan | A (terms), C (rebrand) |
| **Unsplash** https://unsplash.com/license | Real photos to cut out | Free, commercial use included, no permission needed. Don't sell them without significant changes, or build a competing service. Unsplash+ items have their own licence | No | A |
| **NASA images** https://www.nasa.gov/nasa-brand-center/images-and-media/ (updated 2026-08-13) | Storms and Earth from orbit, satellites | Generally not copyrighted in the US. Credit NASA, imply no endorsement, leave the logo alone. Third-party items inside NASA's collections need their owner's permission | Yes | A |
| **NASA Earthdata and Worldview** https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy (updated 2026-10-20); https://worldview.earthdata.nasa.gov/ | Daily satellite imagery of any region | NASA mission data are CC0, with no restrictions on use; citation is requested | Cite it | A |
| **NOAA and NWS** https://www.weather.gov/disclaimer | Radar, forecast graphics | NWS pages are public domain unless noted. Third-party imagery is excluded. The NWS name and logo are trademarks, so imply no endorsement | Courtesy credit | A |
| **GOES satellite loops** https://www.star.nesdis.noaa.gov/GOES/ (regional sectors; GeoColor; loops); CIRA's SLIDER https://rammb-slider.cira.colostate.edu/ | Real thunderstorm and hurricane loops over a region | NOAA material is public domain (a Wikimedia file note, C). No use statement was found on the STAR site itself. CIRA asks for the credit "CSU/CIRA & NOAA" on GOES imagery (https://satlib.cira.colostate.edu/credit-media, A) | Yes | A/C |
| **NOAA Photo and Digital Library** (https://www.noaa.gov/digital-library, which refused with a 405) | Storm, lightning and hurricane photos | Public domain unless the caption says otherwise. Don't imply endorsement or use the emblem. Videos often contain third-party footage (search summary, C) | Yes | C |
| **Wikimedia Commons** https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia (edited 2026-08-11) | Real photos of places, people, hardware | Each file has its own licence: credit the creator and link the licence. Share-alike applies to changes. Under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/legalcode.en), an adapted work must carry the same licence. **So don't make cut-outs of BY-SA photos**: use CC0 or public domain, or plain CC BY with credit | Usually | A |
| **Poly Haven** https://polyhaven.com/license | HDRIs, textures, 3D models | CC0: any use, no credit needed | No | A |
| **Blender demo files** https://www.blender.org/download/demo-files/ | Full 3D scenes for three.js or Blender demos | Licensed per file. Classroom is CC0; Agent 327 Barbershop and Barcelona Pavillion are CC-BY; Human Base Meshes and Cube Diorama are CC0. Skip the files with no licence stated | Per file | A |
| **Sketchfab** https://sketchfab.com/licenses | 3D models of devices, phones, cars | Store licences: Standard allows commercial use but no standalone redistribution; Editorial allows no commercial use. Free downloads carry per-model CC licences, which couldn't be confirmed from that page | Per model | A/C |
| **Mixamo** (Adobe; the help page refused with a 403) | Rigged humans and animations, for a moving person in a 3D demo scene | Royalty-free in personal and commercial projects of any kind, films included. Free with an Adobe ID. Don't redistribute the raw files (via search) | No | B |
| **FootageCrate / ProductionCrate** | Overlays (weather, smoke) | **Couldn't confirm.** The licence page returned a 404. A third-party summary says the free tier needs attribution | ? | D |
| **Paid, only if the free set fails** | Storyblocks (WSJ credits it), Envato Elements, Artlist | Prices and licence notes are in `standard/research/FOOTAGE_SOURCING.md` §8. Storyblocks' licence ends for new projects when you cancel | — | — |
| **The creator's own** | The primary source's own material (the maker's official videos, press kit, site); page captures; BiRefNet cut-outs; the creator's own screen or camera captures | Short clips of others' material in commentary: the house line lives in `rules/SHARED.md` | Source line | — |

**Compositing notes**
- **Plates on black go in with Screen or Add blend**, so the black drops out. Alpha plates (ProRes 4444) need no keying.
- **Avoid "free PNG" sites** whose licences are unclear.
- **Avoid AI-generated stock entirely.** Pixabay hosts some, and it would bring tell 14 straight back.

---

## 5. Design brief for the redesign (one page)

**The principle:** the real thing first. A self-made graphic goes in only where nothing real shows the point, and then it is
built from real material.

**Palette**
- **The footage is the palette.** Graphics take their colour from the shot they sit on.
- **Ink:** warm white (`INK` in `tools/motion/src/brand.ts`, `#F4EFE6`) for text and lines on footage. Plain black `#000000` for
  scrims and shadows. No navy or tinted near-black.
- **Marker:** the house highlighter (`KEY` in `tools/motion/src/brand.ts`, `#FFD21F`), only to highlight real text or real UI.
- **Accent:** one per video, sampled from the primary source's own art for that topic (for example, the main colour of the
  maker's logo), and used only on the one thing the voice names. Where no topic colour fits, the brand accent from
  `tools/motion/src/brand.ts`.
- **Comparisons:** for then vs now, desaturate the old side and keep the new in full colour. Never two neon colours.
- **Banned:** navy fields, teal and pink neon, glows, decorative gradients, glass cards.

**Type**
- **One family.** Proposal to test: Archivo (OFL; widths 62-125 and weights 100-900). Its condensed width covers labels and its
  normal width covers numbers.
- **Where a graphic imitates the source's own UI** (a phone screen, an app), match that UI's type instead.
- **Labels:** sentence case, normal tracking, no monospace.
- **Numbers:** tabular figures, always with units.
- **Sizes:** one label size and one headline size, tested at 1080p and 4K on the review screen (no published standard was found;
  `standard/research/MOTION_CRAFT.md` §2).

**Materials: what a graphic is made of**
- the shot itself
- page captures, and the source's own UI
- cut-outs from real photos and frames, with contact shadows that match the shot's light
- real VFX plates (rain, smoke, lightning) on black or with alpha
- real data imagery: satellite and radar
- real 3D renders of CC0 scenes in `@remotion/three`
- paper scans for maps and documents

One film-grain finishing pass goes over everything.

**Depth**
- **Three planes:** the footage at the back (defocused when something in front is speaking), the subject in the middle, and the
  annotation at the front.
- **Annotations attach to the subject.** No floating cards.
- **One eased camera move per beat** carries the viewer through the planes, with motion blur.

**How real material goes inside graphics**
- **Annotate the real frame:** a box on the region plus a magnified inset; a line drawn onto the thing; a label pinned to it.
- **Compare from the same camera:** slices, a split or a slider, built from real captures.
- **Build diagrams out of real thumbnails,** the way a maker's own feature explainer does (P1).
- **Put a number in its source,** or in the scene beside what it measures.
- **Take weather, scale and space from real imagery.**

**Motion**
- One orchestrated move per beat. Elements don't each fade and slide in.
- Lines draw on along their subject, and highlights sweep in reading order.
- Fast moves get motion blur; exits are quicker than entrances.
- Footage keeps playing under the graphics. A freeze is a deliberate "look closer" beat.

**Measured data**
- One plain house chart template, in the style of the hardware-review channels we studied (P4).
- Real numbers only, with one highlight colour and the source on screen.

### Six worked examples
1. **How a dam holds back a flood** (a claim that a reservoir kept a flood off the towns downstream).
   - **Picture:** real aerial footage of the dam with its spillway running: the operator's own video (when the operator is a US federal
     agency, its own footage is public domain as a federal work) or a news clip.
   - **Annotation:** a thin line marks the water level on the real dam face. Under the shot, in the house chart template, the real
     inflow into the reservoir against the outflow released, from the operator's or the USGS's published gauge readings, with
     the gap between the two lines in the marker colour.
   - **The same view two ways:** NASA satellite imagery of the valley before the storm and the first clear day after it (Worldview,
     CC0, §4; for a small reservoir its daily imagery is coarse), as a slider: the reservoir swollen, the plain below it still dry.
   - **Fallback:** if no footage exists, a real photo of the dam (Wikimedia Commons, CC0 or CC BY) with a slow push and the level
     line drawn on it.
   - **Never:** a drawn wall with blue arrows.
2. **Why a stock fell on one day.**
   - **Picture:** the real intraday chart of that day, captured from a public finance page in the repo's page component
     (`tools/motion/src/kit3/page.tsx`), or the business channel's own on-air chart as a short credited clip.
   - **Annotation:** a thin line drops onto the chart at the minute of the fall, labelled with the time. Then the cause as its real
     page: the filing on EDGAR or the company's release, with the marker sweeping the sentence that moved the price.
   - **Fallback:** if the page won't capture cleanly, the real prices plotted in the house chart template, with the source and the
     time zone on screen.
   - **Never:** a red arrow pointing down on a dark card, or a price line with an invented shape.
3. **A wildfire's spread over a map.**
   - **Base:** a real map: satellite imagery (NASA Worldview) or an OpenStreetMap render with its credit.
   - **The fire:**
     - real Worldview daily images of the burned area, one for each day the voice names
     - cropped to that area, masked with a soft edge over one part of the map
     - the rest of the map stays as it was
     - credit: "NASA Worldview" (citation requested, §4)
   - **The push-in:**
     - a real smoke plate with alpha (an ActionVFX smoke plume, §4)
     - the area under the plume darkened
     - one more plume on the line that names the wind turning
   - **Then the real thing:** footage of that fire on the ground (a local station's report or the fire agency's own clip,
     credited), on the line that names it.
   - **Never:** an orange blob with drawn flames.
4. **How a vaccine trains the body.**
   - **Picture:** real electron-microscope images of the virus (CDC's Public Health Image Library holds many; most are US
     government work, and each image's page gives its rights), then real footage of the shot being given (stock).
   - **The mechanism in a real scene:** the real molecular structures from the Protein Data Bank (its data files and structure
     images are CC0, B): the virus's surface protein, then an antibody bound to it, rendered in `@remotion/three` with labels
     pinned in perspective.
   - **Annotation:** a line draws onto the spot the antibody grips, as the voice names it.
   - **Fallback:** the health authority's own explainer page (the NHS's vaccination pages, for example) captured in the page
     component and credited, with the marker on the line that says it.
   - **Never:** cartoon germs, glowing shields or a drawn syringe.
5. **A feature on a phone screen** (an app's view of an e-bike, shown in the maker's launch video).
   - **The picture:** the real app screen from the maker's own video, full frame, with a slow push to the phone in the person's
     hand.
   - **The words:** a marker sweep on each feature word (range, lock, location) as the voice says each one.
   - **If the UI text is too small:** a magnified inset of the real screen, with a box marking where it comes from.
   - **If a clean version is ever needed:** a 1:1 recreation sampled from that frame (colours, type, icons), corner-pinned back
     onto the phone with the footage's grain and blur.
   - **Never** invented fields.
6. **A big number** (a video's length, say 18:32).
   - **Show the source.** That is the real YouTube page of that video (the channel, the views, the length badge), captured, in
     the repo's page component (`tools/motion/src/kit3/page.tsx`): a push to the badge, then the page holds still while the marker
     lights it.
   - **If the number is our own calculation:** set it big in the house family, with tabular figures and units, inside the scene
     (on a wall, a screen or the map) with the scene's light and grain, or beside the object it measures (Cleo Abram, 4:30).
   - **Never** a centred number on a card over blurred footage.

### Acceptance (before render)
1. **Run the §1 checklist** on the dense frame sheet. No frame may show two or more tells, and every graphic frame must show
   real material.
2. **A/B each graphic against its reference frame:**
   - comparisons: same-camera slices (P3); pick the reference frame from a top technical-review channel in the creator's niche
   - graphs: a one-point-per-sample plot (P4), from the same kind of channel
   - 3D explanations: Cleo Abram at 3:30 (P6, P9)
   - maps: Johnny Harris at 4:30
   - numbers: MKBHD at 0:20
   - weather and data lines: The Weather Channel at 0:30
3. **The creator judges.**

**Build order:**
1. the annotation kit on real footage (box, inset, draw-on line, marker)
2. the house chart template
3. the comparison kit (slices, split, slider)
4. plate compositing (Screen or Add blend, masks)
5. the 3D demo stage in `@remotion/three` (a CC0 scene or a real structure, one real light, labels in perspective)
6. the map stage (a real satellite or OpenStreetMap base, real data drawn on it, its credit line)

---

## Sources

**AI slop and generic design**
- Anthropic, frontend-design skill (last commit 2026-09-03, #1713):
  https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md (raw file via curl) — B
- Anthropic, "Improving frontend design through Skills" (2025-11-12): https://claude.com/blog/improving-frontend-design-through-skills — B
- Ken Imoto on the skill's rewrite (DEV): https://dev.to/kenimo49/anthropic-rewrote-frontend-design-skill-3-ai-design-cliches-named-with-hex-codes-22m4 — C
- prg.sh, "Why Your AI Keeps Building the Same Purple Gradient Website" (2025-10-26):
  https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website — C
- Jeff Humble, "7 Tells that a UI is AI-Generated" (about 2026-04):
  https://pages.thefountaininstitute.com/posts/7-tells-that-a-ui-is-ai-generated — C
- Mika Reyes, "How to Fix AI-Looking Graphic Design and Posters" (2026-08-05):
  https://mikareyes.com/ai/how-to-fix-ai-looking-graphic-design-and-posters — C
- Jason Zhou (superdesign, an AI design tool), "Why AI design looks generic" (2026-06-15):
  https://www.superdesign.dev/blog/why-ai-design-looks-generic — D
- Venngage, "AI slop in design" (updated 2026-08-12): https://venngage.com/blog/ai-slop-in-design/ — D
- 925studios, "AI slop design tells" (2026): https://www.925studios.co/blog/ai-slop-design-tells — D
- Keston Collins (AutoAE, which sells templates), "Why Claude Remotion Videos Look Flat" (2026-10-07):
  https://autoae.online/blog/claude-remotion-videos-look-flat — D
- Dihal & Duarte, "Better Images of AI: A Guide for Users and Creators" (2023):
  https://blog.betterimagesofai.org/wp-content/uploads/2023/02/Better-Images-of-AI-Guide-Feb-23.pdf (text extracted locally) — C
- Merriam-Webster's 2025 Word of the Year, via TechCrunch (2025-12-15):
  https://techcrunch.com/2025/12/15/merriam-webster-names-slop-the-word-of-the-year/ (search summary) — B
- Kapwing, "AI Slop Report" (2025-11-28, Liam Curtis):
  https://www.kapwing.com/blog/ai-slop-report-the-global-rise-of-low-quality-ai-videos/ — C
- YouTube, channel monetization policies (update of 2025-07-15): https://support.google.com/youtube/answer/1311392 — A
- Kurzgesagt, "AI Slop Is Killing Our Channel" (2025-10-07), listing:
  https://www.tvmaze.com/episodes/3391530/kurzgesagt-in-a-nutshell-2025-10-07-ai-slop-is-killing-our-channel/gallery — C
- How to spot AI images: Trend Micro https://helpcenter.trendmicro.com/en-us/article/TMKA-13276 ; Canadian Centre for Cyber
  Security https://www.getcybersafe.gc.ca/en/resources/recognize-artificial-intelligence-ai-9-ways-spot-ai-content-online (search
  summaries) — C

**Premium channels: videos read through page metadata and storyboard frames (A)**
- Linus Tech Tips, Core Ultra 270K Plus (2026-03-23): https://www.youtube.com/watch?v=lSSkQnHWisM
- Branch Education: two explainers, not linked here (a description names Blender, B)
- Vox, the 3D-models explainer (2019-01-10), not linked here
- Johnny Harris (2023-02-09): https://www.youtube.com/watch?v=_wIOqHSsV9c (its description names GEOlayers)
- PolyMatter (2026-06-12): https://www.youtube.com/watch?v=j2QEieIiiXg
- Wendover (2022-06-29): https://www.youtube.com/watch?v=V0Xx0E8cs7U
- Cleo Abram (2026-09-30): https://www.youtube.com/watch?v=eNkxTjirY-Q
- MKBHD with Epic Spaceman (2025-12-26): https://www.youtube.com/watch?v=Jh9pFp1oM7E
- ColdFusion (2026-10-01): https://www.youtube.com/watch?v=e2zjpCqTmyo
- Kurzgesagt (2026-10-05): https://www.youtube.com/watch?v=ujkD4SxPKOI ; their making-of (2020-02-16):
  https://www.youtube.com/watch?v=uFk0mgljtns (B)
- Bloomberg Originals (2022-11-10): https://www.youtube.com/watch?v=VsUF_CBJq50
- WSJ Tech Behind (2023-06-12): https://www.youtube.com/watch?v=c10LhVego4o
- The Weather Channel, Immersive Mixed Reality (2019-10-10): https://www.youtube.com/watch?v=uphdsq4cG-g
- Observed by us, not linked here: two hardware-review channels (a review with per-sample plots and Schlieren imaging; a chart-template review at two load levels); a maker's own
  feature explainer; a software maker's own launch video.

**Premium channels: documented tools**
- Cleo Abram's interview, IN SYNC episode 8 (2022-10-15): https://videoconsortium.org/mag/episode-8-cleo-abram — B
- Rokoko on Epic Spaceman (2023-10-04): https://www.rokoko.com/insights/epic-spaceman — C
- GIJN, Malachy Browne's tools (2019-11-25): https://gijn.org/2019/11/25/my-favorite-tools-malachy-browne/ (search summary) — C
- 80.lv on The Weather Channel's mixed reality: https://80.lv/articles/using-mixed-reality-and-unreal-for-weather-broadcasts (search
  summary) — C
- The Vox look: PremiumBeat (2021-03-08), via `standard/research/MOTION_CRAFT.md` — C

**Sources for the examples in §3 and §5**
- iFixit, licensing (CC BY-NC-SA 3.0; commercial licences on request): https://www.ifixit.com/Info/Licensing — B; its teardowns:
  https://www.ifixit.com/Teardown
- Wikimedia Commons, cutaway categories (found through the Commons API), e.g. https://commons.wikimedia.org/wiki/Category:Cutaways_of_aircraft_engines
  and https://commons.wikimedia.org/wiki/Category:Cutaways_of_automobile_engines — A (licence per file)
- The Cancer Imaging Archive, data usage policies: https://www.cancerimagingarchive.net/data-usage-policies-and-restrictions/ — B
- SEC EDGAR full-text search: https://www.sec.gov/edgar/search/ (refused a script with no declared contact, 403) — B
- Transport for London, open data: https://tfl.gov.uk/info-for/open-data-users/ (terms behind sign-up, not read) — B
- OpenStreetMap, copyright and licence (ODbL): https://www.openstreetmap.org/copyright — A
- USGS, copyrights and credits: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits (403; US
  federal works are public domain under 17 U.S.C. § 105) — C
- NASA Earth Observatory (moved to https://science.nasa.gov/earth/earth-observatory/; satellite image stories of floods and
  fires) — B; NASA's media guidelines in §4
- CDC Public Health Image Library: https://wwwn.cdc.gov/phil/ (electron micrographs; rights stated per image) — B
- RCSB Protein Data Bank, usage policy (data files and structure images CC0; Molecule of the Month art CC BY 4.0):
  https://www.rcsb.org/pages/usage-policy — B
- NHS, vaccinations: https://www.nhs.uk/vaccinations/ — B

**Assets and licences** (in §4): Pexels, Pixabay, Mixkit (plus `/llm-info/`), ActionVFX (Wayback copy 20260412153458; the list of
free collections from Wayback's CDX index), CG Channel (2020-12-13: https://www.cgchannel.com/2020/12/download-actionvfxs-three-free-stock-effects-collections/ ;
2026-01-08: https://www.cgchannel.com/2026/01/download-30-free-flamethrower-effects-clips-from-actionvfx/, via search — C), Magnific
terms (June 2026: https://www.magnific.com/legal/terms-of-use), the Freepik→Magnific rebrand (https://www.all-ai.de/news/news26/freepic-magnific-neu,
via search — C), Unsplash, NASA, NASA Earthdata, NWS, NESDIS STAR GOES, CIRA's credit page, Wikimedia Commons, the CC BY-SA 4.0
legal code, Poly Haven, Blender demo files, Sketchfab, Mixamo (via search), and the Google Fonts metadata for Archivo
(https://github.com/google/fonts/blob/main/ofl/archivo/METADATA.pb) — A unless marked in §4.

**Measured by us (A)**
- The palette, token, font, letter-spacing, corner-radius and shadow counts in §0 and §1: a grep over the graphics code of one of
  our own builds and its shared kit.
- The review verdicts on that build (drawn figures, a drawn blob for a natural event, unmeasured cost-share boxes, a centred number card).
- The described channels above: our own look at their storyboard frames and chapters.
