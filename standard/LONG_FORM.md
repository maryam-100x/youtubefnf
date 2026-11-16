# Long form: the standard

*Part of `STANDARD.md`. Re-read this file before every long video, together with `standard/BAR_LONG_FORM.md` (what a video at the bar
is, in words: the qualities every minute has, with their numbers, and worked openings shot by shot) and the newest finished long video
of this studio, once there is one (`STATUS.md` names it: watch it, read its code, its cue sheet and its `videos/<video>/BUILD.md`). The order of the work and
what blocks each stage: `standard/WORKFLOW.md`. The one look and the pieces: `standard/KIT3.md`; 3D: `standard/3D.md`; other designed
forms: `standard/GRAPHICS_KIT2.md`. The gate and renders: `standard/PIPELINE.md`. Sound, voice and music: `standard/SOUND_AND_VOICE.md`,
`standard/VOICE_LOCK.md`, `standard/MUSIC.md`.*

**The bar is a level, never a template.** Every section is built to the level of `BAR_LONG_FORM.md` and of the newest video the creator
signed off, and finds its own pictures, effects, sound and music for what it says. Copying a signed-off video's devices (its chart, its
count-up, its cross, its black before a date) into other sections or other videos is the template mistake: a passed prototype is a
level of quality, never a set of devices to repeat. The brand (type, colours, cards, sounds) repeats; the devices don't.

## The bar

- **Every shot starts on the word it shows, and it shows exactly that.** Shots are placed on the narration's own word times
  (`w(beat, phrase)` over `words.json`), never in seconds. Each person, place, thing and number named gets its real, current picture on
  its word, found by searching all the footage. When nothing fits, the primary source's own material on the subject (the maker's
  official videos, press kit, site), never a repeat or generic stock. A clip's span is chosen on its whole sheet, where the thing named
  fills the frame, whole and clear: a line about a lit rooftop sign took a source's first 4 s (a tower, the sign a sliver at the top
  edge) while its seconds 17-24 showed the sign lit and filling the frame. A chart or diagram that someone outside made carries a small
  credit to its maker under it, and its numbers are said as their estimate. A technical point is demonstrated with the clearest material made for it
  (an online comparison, a creator's side by side), credited, never with footage that wasn't recorded for the point.
  **Every footage pick has something going on** (people, animals, a match, a market, hands at work): an empty vista, aerial, desert or open
  water only when the line is about that exact place, and then its busiest version; ask "what is happening in this shot?" of every span
  (a held landscape bores and measurably costs retention). A source's best real photo or frame carries its line, never its cover
  illustration. A line that is an image is acted out on its picture: the things it names drop onto it on their words with a heavy impact
  and its sound (products slamming onto a mountain on "stacked higher than ...").
- **The first frame of every shot is its words' first word, and something to look at**: the picture changes on the first word of its
  clause, and frame 0 of a shot is never an empty road, a black frame or a picture still loading.
- **Words on screen stand long enough to read; a graphic is centred, crisp and simple.** Text there for less than a second before a cut
  is a fault, and an off-centre or busy graphic reads as ugly where a simpler one would be clean and professional. A stamped word or
  phrase lands ON its word and stands at least its reading time (1.2 s, +0.03 s a character past 10) before anything cuts it: when it
  lands near a line's end, the next picture starts later, into the next line. The gate's B24 TEXT_SHORT measures it on the probe. A
  graphic holds only its subject, centred and whole, crisp at its size (never a big zoom into a frame's corner through a black pad); a
  box measured for it is checked on the frame before use. The creator's fixes go out as samples of just those moments; the prototype
  stage ends at their pass.
- **The pro editor's level, by default, from the first build:** what's said is demonstrated on screen (a rule of how the subject works
  gets a built graphic of it, the statement's words stamped on their word); every cut, length, zoom, pan and switch sits exactly on its
  words; a mark is the thing exposed and the rest dimmed (kit3's spot look; a box only when asked); no blank frame: nothing on screen
  for ~0.5 s or more unless its thing is arriving (B3 BLANK_LONG); a "no" is a clean modern device, never a hand-drawn stroke over a
  grey picture; a section opens on its most engaging real clip (a chapter about a rescue opens on the rescue at its tensest, not on a still
  of the aftermath). The level of every graphic: the subject's own element drawn crisp and centred, the picture behind blurred back, the
  statement under it, held ~1.5 s. It is made that way from the first build, never only after a note.
- **About 25-32 cuts a minute, median shot about 1.6-1.9 s, cut on meaning.** Measured: a hit 28.2 a minute
  (median 1.87 s); a signed-off opening 31.2 (1.57 s); openings run faster (33.6-36.4 a
  minute). A video at 13.9 a minute with half its shots at 4 s or more failed. A film told mostly on stills and pages (a history told on
  old photos, a receipts video) runs nearer 20-25 a minute, every still one beat (~2-3.5 s, one move). The gate's tolerance is 18-32.
  Never a Shorts timer.
- **Bursts and holds, not an even beat.** Bursts of 0.2-0.4-s shots only on a list or a big claim, each picture the same screen time
  (8 shots in 3 s; a rewind through six eras on "forty years"). Shots of 4 s or more only on something live: a real clip with its own
  sound, a moving map, a designed black.
- **No flash frame, no freeze, no slowed clip.** No lone shot short enough to read as a flash: either it comes earlier and stays longer,
  or it goes. No sliver of a source's next shot at a clip's edge; nothing stands still past about 2 s (a held graphic keeps a visible
  drift); a card goes about 3 s after its point; clips play at 1.0, slow motion only as a deliberate replay. What makes flashes: a
  graphic that eases its backdrop's dim in at a cut (one bright frame of the shot under it), a clip fading up from black, a source's next
  shot at a clip's edge, an empty first frame before a graphic drew, two anchors landing within 0.5 s. At a cut a graphic starts in its
  settled state. In a breakdown the clip plays first, then stops on its best frame for the look.
- **Footage plays through its shot; builds finish before the cut; no graphic stands empty.** A clip shorter than its words freezes
  0.2-0.8 s under a moving push (qa_render can't see it: run the static clip audit, 0 overruns, before any render); a transition's second
  half uncovers the incoming shot; a map pin, a reveal or a row stays about a second after its last element lands (the next picture may
  come a beat after its word); a graphic's backdrop blurs before it arrives and it arrives already moving (flip cards standing blank over
  sharp footage read as broken).
- **Every clip full frame, filling the screen.** No crop to hide an on-screen overlay, a picture-in-picture, a ticker or a label, no zoom into a part,
  no clip shrunk into a panel on a blurred ground; a soft or ugly source gets a cleaner source, never a crop. A letterboxed source shows
  whole with its own bars, never cropped to fill (the gate's LETTERBOX_CUT). The only person rule: never someone's voice over a clip of
  them saying other words.
- **Receipts are the real page, alive and readable on a TV.** The page cuts in (no fade), cropped to the lines that matter, the camera
  travels to the quote, the quote lights as the voice reads it; never blurred, never off the edge; never a page read under the voice
  for long (half the frames as pages and number cards is a failed film). The lit phrase is the few words that are the point; when the
  point is the whole line, the card shows plain with no highlight (a line lit but for two words is pointless); the mark stays inside its
  own line (a band tinting the descenders of the line above is a fault).
  **Pages are the minority:** a page where its words are the point (the quote that is the story, the headline as proof, the number that
  shocks); every other line a picture, clip or graphic of what is said. A signed-off opening gave pages about 16% of its time; a film at
  35% was felt at once: the text cards got too much screen time.
  **Show the thing itself, never a card about it:** when the words name a thing that exists as a picture (a video, a post, a page, a
  chart, a stream), the screen shows it, sharp and full frame, with its number lit on it as the receipt (the video's page with its view
  count marked on a frozen frame), with the people or thing themselves beside it or before it. A big-number card over a blurred stand-in
  is only for a number that has no picture of its own.
  **The same inside a graphic:** a product on a timeline is its picture, a person their face, a company its logo, never the name in
  type where a picture can stand in; labels of one kind on one side of the axis.
- **Text cards are the last resort.** People watch YouTube for instant visual feedback, not to read. Every line gets a clip that shows
  it; a system or a comparison gets a built demonstration from real material (a before | after split screen, a map acted out, a 3D
  piece); a page, headline, quote or number card only where the words are about that text itself, with `// card: <why>` above the shot.
  The gate's B19 CARDS refuses a card without its reason, cards over 8% of the film, and two cards within 20 s. Explaining lines get
  built, animated graphics, never cards or piles of images.
- **A lit small thing is zoomed into; a claim about an on-screen readout is shown on its proof.** Every mark on a small thing zooms in
  (~0.45 s, kit3 `Foot zoom`) from its freeze with the dark kept round it; a thing in a corner of an interface is zoomed in its corner;
  the clip is cut from the 4K master (gate B4 UPSCALE, B25 MARK_SMALL). A blinking indicator plays on under its zoom (`live`); things
  named together light together (B25b); a feature is shown in use, and the exact moment named beats a general one; a feature the
  previous version already had is never sold as new; an explanation never sits mid-sentence; the house sign-off on the last line
  (B26 OUTRO). A mark only on something framed big and central: a mark on a small thing in a corner never ships (MARK_SMALL: a lit mark
  under 48 px tall on the 1080 frame, 64 at 1440p; MARK_CORNER: its centre in the outer 15% of both the width and the height).
- **Marks sit on a frozen picture, only where there is a choice, measured on their target.** A box, ring, spot or highlight on a spot
  inside a picture needs the picture under it standing still for as long as the mark shows (the clip freezes on its frame, no push or
  pan under it); a mark that rides with its moving page or still is fine; a name label on a person in a playing clip is fine. A mark only
  where the eye has something to pick out (a crop that is only that thing needs no mark). Boxes come from the pixels (`automark.py`),
  never placed by eye.
- **A zoom starts on the whole picture.** A zoom only where it is fully coherent (it lands on the words' own thing): the shot opens on
  the full picture and moves onto its subject while it plays, the subject centred where it lands; a shot never opens on a crop. A
  picture shown above ~1.15x needs `// zoom: <why>` above it, and never past 1.3x its pixels. This is the zoom that SHOWS something; the
  very slow drift that keeps a frame alive is another thing and stays.
- **A card's camera is one move.** A page, photo or still cuts in with its push already moving and lands once: one eased move
  (`EASE.drift`) from the first frame to the quote, then only the pan's slow drift; no settle at the cut, no drift that stops before a
  second push. A push that drifted to a fifth of its travel, stopped, then pushed again read as "zoom in, pause, zoom in again":
  stuttery. Measured (`qa_zoom.py`, within a few % of the code's own curve): a speed hump at the cut, the speed down to 3-9% of it,
  then the push's hump 0.3-0.6 s after the cut; the cards that read smooth had one hump (no drift) or a drift so long the settle read as
  part of the cut. kit3's pieces are one move by construction; `qa_camera.mjs` proves it from the code.
- **Real people speak in their own clip, mouth moving.** The narration stops, the clip plays its real sound, "Name: words" subtitles
  above the broadcast's own lower third; the speaker's words taken from the broadcast's own captions; any clip under the narration is
  muted. A reference clip never repeats our words: our line leads into it ("and the chief said it straight:") or says it generally in our
  own words, and the clip carries the exact line; never our quote word for word followed by the same words.
- **Graphics are designed, few, and each one a real idea.** A number lands as a picture or an animation with a small source line (a bar
  shooting up on "four"; 40,000,000 counting up). No text that repeats the voice; no add-on that doesn't belong to the graphic (an
  "UP 40%" arrow). Real objects are real cut-outs, never one real object among drawn icons (a real device beside line icons of a
  phone, a keyboard and a mouse). Each graphic is designed against a professional reference, with material, light, depth and type with
  character; flat boxes and line icons on a dark card read as plain and bland, typical AI slop.
- **The real thing first; graphics premium or not at all.** A real page, clip, interface or asset shows the point wherever one exists;
  a self-made graphic is built from real material (footage, captures, cut-outs, effect plates with alpha, satellite imagery, real
  renders) and annotates it. Never shapes standing for real things, never a navy card with neon accents, glows, tracked caps labels,
  monospace "data" or a big centred number on blurred footage (the checklist below). Layout: a group sits centred, never corner to
  corner; an overlay shows once; term labels have no pin or line and one place and size for the whole video; a demonstration plays to
  its payoff; a zoom aimed at a detail lands on it. **The kinds of graphic built from real material** (each in kit3 or built for the
  video on its tokens): a real clip or screenshot pushed into, a thin box or the spot light drawn onto the thing; the real interface
  magnified in an inset; two or three real pictures side by side with their numbers under them (a contrast); a number low on sharp
  footage, counting on its word; milliseconds or durations as thin lines over the footage; a real post or headline, underlined as
  said, translated when foreign; a real logo on the dark stage; a quote line; a person's frame with their name line; a term label;
  a tag in plain words (never a pill). Real material first: ask research agents for documentation images with licences, creators' own
  captures and exact video spans with timestamps before drawing anything.
- **A change between two pictures is shown with both real pictures and the real thing moving.** Where a line says something moved, was
  copied, was taken out or came back, the two real pictures stand whole side by side and the real cut-out travels from one to the other
  and lands where it belongs (its own alpha cut-out, the hole it leaves filled classically), never a drawn stand-in.
- **Nothing is shrunk, lowered or moved to keep it clear of words, a logo or another thing.** It is layered (text over a dimmed picture,
  a credit on its chip); the size is decided first and big, then the place.
- **No device becomes the film's default.** One graphic component as the main picture of more than 6 appearances needs `// device: <why
  this line needs it>` (B23 DEVICE_SPREAD); a round crop of a screenshot as a shot's picture never ships (ROUND_CROP: circles all over
  a video read as a template); the house stamp is a passage's headline claim (a number said as a statement, a multiplier, a record),
  never a phrase the voice just says or a question, unless `// stamp: <why it is the headline claim>` sits above it. Emoji are props
  inside a piece built from real material, never the graphic; all emoji graphics count as ONE device under the same cap.
- **Every effect stands for an action you can name, on its frame.** One house sound per action (the house effects, named by job in
  `assets/house_sfx.zip`'s manifest: pop, marker, stamp, whoosh_fast, number_land ...); every highlight gets the marker sound from its
  light's first frame; silence where it's right (no sound on "a billion", none on a rewind). A signed-off opening had 12 effects in 71 s.
  Details: `standard/SOUND_AND_VOICE.md`.
- **Voice and music:** warm from the first word, no word swallowed; one sound world ~22 dB under the voice; a designed stop has
  something under it, never digital silence; the next bed on a downbeat where the story turns.
- **Picture quality and shape:** every full-frame picture 1080p or better; nothing cut at the frame's edge; logos centred on their
  visual weight (`standard/KIT3.md` §5). The real moment's picture is used and made crisp (a sharper copy of the same source, a frame
  stacked or cut from the 4K master), never swapped for stock because it is "too soft". The only real example of a thing stays, even
  under a loose line. No AI-generated or AI-enhanced pictures in a video. Among many fitting clips, prefer the newest official material.
- **The story starts fast** (a hit kept 52% of its viewers at 0:41; a signed-off opening reached its first turning point at 60 s). The
  subscribe ask sits at a real break; the video ends on the like and comment sign-off, then a fade to black and silence.

## One design system per video

Every built graphic of a video comes from one system: kit3's (`standard/KIT3.md` §1: the grid, one type family in five roles, one ink
and the creator's one accent, one card, one credit line, one motion set, the never-list). Eight hands building with eight looks (five
credit styles, four ink colours, type from 22 to 220 px, every component its own stage) is what an amateur film looks like. A graphic that
needs something the system lacks gets it added to kit3 first, then used. Design and coherency are objective: an amateur-looking graphic,
a picture that doesn't match its words, a line nobody would say are errors to find before the creator watches, not matters of taste
(taste is a preference like a colour).

## The AI-template look, and the premium look

Our graphics are written by an AI in code, and a model without direction samples the most common, safe choices: the same look every
time, whatever the subject (a dark ground, a glowing headline, a soft gradient blob, every element entering with the same spring, type
filling the frame because there is no other material). Viewers read it as mass-produced, and YouTube refuses to monetise content built
on generic templates that looks mass-produced. So every graphic frame is run through this checklist on the frame sheet before a render.
**Two or more tells in one frame means redo.**

| # | Look for this in the frame |
|---|---|
| 1 | A near-black or navy field with one or two neon accents (teal, pink, acid green); tinted near-blacks standing in for black |
| 2 | Everything in identical rounded cards: thin bright borders, one corner radius, the same soft shadow; cards on cards |
| 3 | Glow: outer glows, text glows, gradient blobs, light behind type |
| 4 | A tracked-out ALL-CAPS label above every heading (the "eyebrow"), often condensed |
| 5 | Monospace "code" type for data and sources, or to signal "technology" |
| 6 | Default fonts, and too many of them (three or more families) |
| 7 | A big number with a small label, centred, on a card or over blurred footage |
| 8 | Shapes standing in for real things: people built from rounded shapes, a drawn tree or house, coins as yellow circles, a box labelled DATA |
| 9 | A fake interface: an invented app card, status dots, thin line icons, emoji as the graphic |
| 10 | Centred and symmetric with every scene in the same layout: no single focal point, every inch filled |
| 11 | The same entrance for everything: each element fades and slides up, or pops with the same spring |
| 12 | Fake data: bars or proportions that look measured but aren't |
| 13 | No real material in the frame: no footage, photo, page capture, real interface or real render |
| 14 | Any AI-generated picture: plastic skin, perfectly even light, creamy bokeh, garbled text, shadows that disagree |

A tell is a default that appears whatever the subject is: caps labels or a dark chart ground can be premium when they form one
consistent house system on real data.

**The quick test, five questions per graphic:** 1. Is there real material in this frame? If not, redo it. 2. Does any shape stand for a
real thing we could show? Then show the thing. 3. Could this frame illustrate another video if its words changed? Then it's a template.
4. How many tells from the table? Two or more: redo. 5. Does any number or proportion claim something nobody measured? Source it or
remove it.

**What premium is made of:** the footage is the palette (graphics take their colour from the shot they sit on; warm white ink, plain
black for scrims and shadows, the one accent only on the thing the voice names); one type family, sentence case, tabular figures with
units; materials: the shot itself, page captures and the subject's own interface, cut-outs from real photos and frames with contact
shadows that match the shot's light, real effect plates (smoke, sparks, dust) on black or with alpha, real data imagery (satellite,
microscopy), real 3D renders of free (CC0) scenes, paper scans for maps and documents; depth in three planes (the footage at the back,
defocused when something in front is speaking; the subject in the middle; the annotation at the front, attached to the subject, never a
floating card); one orchestrated camera move per beat, lines drawing on along their subject, highlights sweeping in reading order, exits
quicker than entrances; footage keeps playing under graphics, a freeze is a deliberate "look closer" beat; measured data in one plain
house chart, real numbers only, one highlight colour and the source on screen. The ways real material goes inside a graphic: annotate
the real frame (a box on the region plus a magnified inset; a line drawn onto the thing; a label pinned to it); compare from the same
camera (slices, a split, a slider from real captures); build diagrams out of real thumbnails; put a number in its source, or in the
scene beside what it measures; take scale and space from real imagery. Each graphic is held up against a professional reference
frame of its kind (a comparison, a graph, a 3D explanation, a map, a number) from a top channel before it goes in.

## The method

PIPE and EDIT are the two Pythons (`python tools/common/paths.py` prints them). Remotion commands run in `tools/motion`. A video's
repo side is `videos/<video>/` (script, `video.toml`, `score/cues.py`, `options/`, `STORYBOARD.md`, `BUILD.md`, `gate_allow.json`), its
media side `MEDIA/videos/<video>/`, its pictures and clips under the public dir `PUBLIC/<video>/` (`clips/`, `img/`, `pages/`, `art/`,
`dl/`), its composition `tools/motion/src/<video>/`. The order and what blocks each step: `standard/WORKFLOW.md`.

1. **Study the bar.** `standard/BAR_LONG_FORM.md` in full; the newest finished long video of this studio (watch it; its code, cue
   sheet and BUILD.md); the creator's casebooks (`cases/PICTURE.md`, `cases/COHERENCE.md`). Any reference video (a top creator in the
   niche): `EDIT tools/qa/measure_edit.py <mp4> <out>` measures its shots, cut rate and loudness.
2. **Research to the day of the build:** footage and receipts from the primary source (`standard/research/FOOTAGE_SOURCING.md` §3, §7:
   the TV News Archive is searchable by spoken words); the maker's official media only from its own media page or press kit, in full
   quality; big news during the build is woven into the structure; the research lands in `kb/` first.
3. **Script with a picture for every line** (`standard/SCRIPTS_AND_PACKAGING.md`), then **the creator's view**: with the script
   finished, the interview (a few open questions, their answers blended in, never quoted verbatim, never made up). A new long video
   starts with its opening at the finished look: a 60-s prototype for the creator, or the level for the rest built in one go, as
   `creator/choices.toml` says. The creator never reads scripts.
4. **Voice** (`standard/VOICE_LOCK.md`, `standard/SOUND_AND_VOICE.md`): the ready stamps, the takes picked by the machine, the chain,
   the sound gate, the lock.
5. **Word times.** Until the voice exists the picture is built on placeholder words (`PIPE tools/motion/placeholder_words.py`, the
   house pace of 3.24 words a second; `beats.json` says `"placeholder": true`); the voice chain writes the real `words.json` and
   `beats.json` (`tools/motion/sync_words.py <video> <folder>`) into `tools/motion/src/<video>/`, and every anchor re-times itself.
   The folder is the one the composition imports (check its timing file: a re-timed narration written to another folder plays under the
   old cuts). After the lock, word times change only inside a lay-in. `PIPE tools/motion/qa_anchors.py tools/motion/src/<video>`: a phrase that occurs
   twice in its beat anchors to the FIRST (name it uniquely or pass `nth`).
6. **The storyboard** (`videos/<video>/STORYBOARD.md`; a section's builder writes `STORYBOARD_<section>.md`): one row per shot with the
   words it starts on, the picture (file or source span, and why it beats the others), the subject's box in source pixels, the move,
   the marks (on which word), the sound. On top, the **Findings**: what was measured about the material and holds for every builder (a
   thing that exists only in one crop of a picture; a subject so near the edge that no centred window exists, so it is lit on the whole
   picture instead; a source that is nearly used up; a picture a line talks about that only exists as someone's post). Every shot is read
   against the creator's casebook (`cases/PICTURE.md`) here, before any code: a fault caught on the storyboard is a one-line change, not a
   second version.
7. **The options board, for every shot.** A premium editor collects the options before picking; the first thing that sort of fits is the
   fault. But never extreme: the test per shot is one question, does it directly show what the words talk about, in some form; a shot
   that passes stays even if something 1% better might exist. A re-pick takes a few (about 3) candidates that are easy to find, from
   different sources (the primary source's footage at every resolution, its other official videos, creators' footage, photos, pages, a
   built picture), and the best of them wins; no search loops, no long hunts; 1080p or better where it exists. Inside a source, the pick
   is its best moment for the line, never the first part seen: scan the candidate source whole first
   (`PIPE tools/motion/source_sheet.py <source video> <out prefix> --clips PUBLIC/<video>/clips [--manifests <prep>_clips.json] [--vf
   crop=...]`: every second as a thumbnail, red where a past video played it, orange where this video already cut it).
   - **Finding the candidates:** `EDIT tools/footage/pick_boards.py boards <script> <out>` (every line's options on a board in one run,
     light and subject measured, artwork and murky spans ranked down); `EDIT tools/footage/find_shot.py "<the line>" --n 12 --sheet
     <png>` (ranked spans by meaning and by picture, flags for murky and used footage; the pick is still made by eye on the sheet);
     `PIPE tools/footage/catalogue.py find <words> --sheet <png>`; `PIPE tools/footage/scan.py <video> <from> <to> <out.jpg> --step 0.25`;
     `kb/FOOTAGE.md` (the map of the creator's sources). Three different wordings before writing that something doesn't exist; then a line
     with no footage of its action says so at its shot (`// no-footage: <action>, searched: <wordings>`).
   - **The board:** `videos/<video>/options/OPTIONS_<section>.json`, one slot per line: `{"id", "words", "film", "dur", "intent",
     "cands": [{"src": "@KEY/file.mp4", "t": [in, out], "vf": "", "what": "what happens in the span", "why": "strengths and weaknesses"} |
     {"img": "@KEY/file.jpg", ...} | {"built": "what would be built", "img": "...", ...}], "pick": 0, "pick_why": "the moment that won and
     why it beats the others and the source's other moments", "media": ["the clip or picture names the shot uses"]}` (paths through the
     spec's `prefix` keys). `PIPE tools/motion/options_board.py <spec.json>` draws one sheet per line (a clip as three frames, the pick
     framed in the accent, each labelled), `--md` writes the boards as text. Look at every sheet and fix any red (missing) frame.
   - **What every candidate must pass:** full frame, filling the screen (the only black is a letterboxed source's own bars); no AI
     upscale (YouTube's "-sr" formats are AI-upscaled: download the native ladder with `-f "bv*[format_id!*=-sr]+ba/b"`;
     `PIPE tools/footage/qa_upscaled.py <prep files>` refuses them); the exact thing the words name, seen, lit, in frame, in action (`what` says what
     happens); the sharpest source and its best span (4K where it exists; on a 720p source the least-compressed span, not the frames right
     after the source's own cut; one camera shot with no cut inside, lit frames at both edges, no freeze inside, at least the shot's length
     + 0.3 s); no run of same-palette shots (three dark night shots in a row is a note); others' design work is never ours (their footage
     yes, their graphics, edits and thumbnails no); private people never named; a minor's face never featured; receipts as the real page.
   - **The check:** `PIPE tools/motion/qa_options.py --tsx src/<video>/<files>.tsx --options videos/<video>/options/OPTIONS_*.json
     --media PUBLIC/<video> --min 3` fails a shot whose media no board names, a slot with fewer candidates, a slot without a pick or a
     reason. A note in words never stopped first-fit picking; this check does.
8. **Pictures, cut and measured.** Find the source's own cuts frame by frame before setting an in-point. The clips are cut by the
   video's copy of `tools/motion/prep_template.py` (`tools/motion/prep<id>.py`): at the source's own frame rate, `-bf 0`, `-map 0:v:0
   -dn`, `setpts=PTS-STARTPTS`, whole with a letterbox's bars kept, into `PUBLIC/v<id>/clips/` named `s<beat>_<what>.mp4`; each clip's
   last frame into `src/clipdurs.json` under its lock and the gate's manifest `prep<id>_clips.json`; `--check` scans each cut for a
   camera cut inside; `EDIT tools/motion/prep<id>.py --proof` draws every measured box on its file (a box is reused only after it is drawn on its file and looked
   at). Choose each clip's span on its whole sheet (`ffmpeg -i <clip> -vf "fps=1,scale=320:-1,tile=6x5" -frames:v 1 <sheet.jpg>`): the
   seconds where the thing named fills the frame; look at every clip in its folder before settling; a better source when none shows it.
   Objects are photo cut-outs (rembg), never icons. A zoomed clip is cut from the 4K master (`EDIT tools/footage/brain_zoom.py`).
   **A claim line gets the moment that proves it, picked on the storyboard.** Every line that says how something works names in its
   storyboard row the moment that proves it and what in the picture does: a claim about an on-screen readout on the moment the readout
   shows it; a feature in use rather than its spec sheet; the exact moment the words name rather than a general one. A number or claim that a
   known clip seems to contradict is shown with that clip and the words that reconcile it. The coherency read checks every claim line
   against its picked moment, once.
   **Marks are measured, never placed by eye:** `EDIT tools/motion/automark.py <image> "<what>" [--region x,y,w,h] [--proof out.jpg]`
   (the named thing's box from its pixels; the first run ~3 min per 4K picture under the heavy ticket, then cached; exit 2 when the
   picture holds more of the thing than asked: `--region` picks); a thing's outline for the spot look: `EDIT tools/motion/spotmask.py
   <image> x,y,w,h --what <thing> --count N [--method dark] [--proof out]` (writes `<image dir>/sil/<stem>__x_y_w_h.png`), then
   `PIPE tools/pipeline/pipe.py <video> link`. A zoom window that centres a measured box is arithmetic (`[cx - W/2, cy - H/2, W, H]`,
   clamped to the picture); when the edge stops it, the nearest centre is written in the `// zoom:` reason. Face icons: `make_icon.py`
   (`standard/KIT3.md` §5).
9. **Receipts.** `node tools/footage/capture_page.mjs <url> <out.png> <selector> --mark "<phrase>"` (a PNG plus the phrase's word box,
   so a page mark needs no measuring; `"text=<words>"` for other boxes), `PIPE tools/footage/snap_marks.py <capture.png> --marks x,y,w,h` to snap loose boxes; staged
   with kit3's `Page` (`crop`, `marks` on the spoken words, at most 1.3x the capture). **Capture at phone width for 16:9 too** (`--mobile
   1 --width 430`, drawn ~1300 px wide: the words ~60 px): a desktop column (~110 characters a line, ~27-px words, half-cut lines above and
   below) held 4.5-5.7 s reads as a frozen picture. Crop to whole lines; a page over ~3 s gets the person or the thing first, then their
   words. Old fixed-width pages ignore `--mobile`: `--wrap 330` lays the block out narrower (archived pages on the Wayback Machine).
10. **The composition.** Copy `tools/motion/src/_template/` to `tools/motion/src/<video>/`: its timing file (`w(beat, phrase, off?,
    nth?)` the start of a phrase in that beat's words, `we()` its end, `b0(beat)` a beat's first word, `bEnd(beat)` its last word's end,
    `bStart()` / `bStop()` a beat's own span for a HOLD with no narration; an anchor the voice no longer says goes into `MISSES` and the
    composition refuses to render naming it), the composition registered as `gated(<Comp>)` on its own root and entry
    (`src/<video>_index.ts`, so it bundles even while another composition is half-built; gate and stills take it as `QA_ENTRY`). **Each
    shot is one line:** `shot(w('S04', 'and the maker has never'), (d) => <Still src=... d={d} .../>)`. A shot ends where the next starts,
    so a shot's length IS its words' length; every `at` inside it is a phrase too (`w('S04', 'one word') - w('S04', 'and the maker has
    never')`). **Nothing is ever placed in seconds.** Anchors stay inline on their words (never a named constant: the coherency packet
    must show the words). The pieces come from kit3 (`import {...} from '../kit3'`, never copied: `standard/KIT3.md`); a video's own
    graphics file holds only that video's own ideas; 3D once or twice a video (`standard/3D.md`); kit 2 only where kit3 has no form for the
    idea (`standard/GRAPHICS_KIT2.md`). Footage only through `lib.tsx`'s `Clip` (never below 1.0x, skips stray edge frames, writes the clip
    log the checks read). The end: the subscribe ask at a real break, the house sign-off (`SignOff` in `tools/motion/src/house/signoff.tsx`: LIKE on "like", the comment card on
    "comments") on the last line, then the fade. Type-check: `npx tsc --noEmit -p .`.
    **The reasons above each shot**, read by the checks: `// subject: <label> x y w h` (the named thing in the picture file's pixels;
    `-> x y w h` for a glide) on every still and every cropped or zoomed clip; `// art: <why no real picture shows it>` on artwork;
    `// card: <why the text itself is the point>`; `// zoom: <why>`; `// device: <why this line needs it>`; `// stamp: <why it is the
    headline claim>`; `// no-footage: <action>, searched: <wordings>`; `// named-moment: "<the words>" <why it is the only source>`;
    `// repeat: <why this picture again>`.
11. **Proof stills before any render:** `cd tools/motion && bash with_remotion_lock.sh "<what>" env QA_ENTRY=src/<video>_index.ts
    QA_COMP=<Comp> QA_PUBLIC=<the lean public dir> node stills.mjs <out dir> 1 <frame> <frame> ...` (frames are the composition's, at 60
    fps; one bundle, one Chrome) at every quote, card, real-person clip, burst and mark; judge each by looking at it, in motion for
    anything that moves. A graphic that builds (items landing one by one, a row, a timeline) gets a still at its first frame and at its
    end state, and a clip at its first half-second: a still 1.2 s into each shot showed empty frames where items had not landed, while the
    end states held rows wider than the frame and one clip opened on a second of black. Motion is judged by numbers, never on stills (a
    still can't show a pause): `node tools/motion/qa_camera.mjs src/<video>/<Comp>.tsx` reads every card's camera from the code, before
    any render.
12. **Sound** (`standard/SOUND_AND_VOICE.md`, `standard/MUSIC.md`): the cue sheet `videos/<video>/score/cues.py`, effects by
    `pal(name)`, timed from the composition's own anchors; `EDIT tools/sound/autocues.py <video> --compare <cue sheet>` writes every
    marker, stamp, count-up and landing from the gate's probe with the frame that proves it (right on about 93% of those effects, half of
    all a film's effects); a person adds the one drop, the whooshes on real flights, pops and impacts. The mix: `PIPE
    tools/pipeline/pipe.py <video> score --picture <render>`; read its report.
13. **Gate, render, finish** (`standard/PIPELINE.md`): `pipe.py <video> link | audit | plays | gate`, then `render` in 1440p parts
    (it refuses code the gate hasn't passed; the render scan runs on every render), then `finish` (4K60, -14 LUFS, subtitles; `--test
    0-10` first on a new chain). One Remotion job at a time on the PC: while a render runs, no other Remotion process at all (stills,
    previews, samples), since two side by side kill each other. Render from the lean public dir of hard links (`link`): Remotion copies its
    public dir into the temp folder on every render or stills run. GPU rendering (`angle`); after a GPU driver reset during a render, the
    software renderer (`swangle`) for good.
14. **After the creator's notes:** a clear fix (they name the issue and the fix is clear, or a plain error with one right answer: a line
    or mark off its words, a flash frame, a wrong name) is fixed once, measured, and patched straight into the next version, with no
    sample and no choice. Every fix that is their judgement (a sound, a voice, a cut point, a new look) and every bigger visual fix goes
    to them first as a before/after sample (`PIPE tools/motion/ab_samples.py <delivered.mp4> <new mix.wav> <items.json> <out.mp4>`; a
    fixed shot as a quick render in an item's `b_video`; several versions as `variants`), sent one at a time, unchecked by the chat (they
    check). Then the cheapest path to the file: a sound fix is a remux (`finish_long.py ... --video-from <delivered.mp4> --gain-only`); a
    few fixed shots are `pipe.py patch` segments spliced into the delivered file (`PIPE tools/motion/splice_patch.py <delivered.mp4> <its
    picture.mkv> <patches.json> <out.mp4>`: only the stretch round each patch encoded again, ~1 min; it fails a splice that loses an
    earlier version's patch, so pass those again), or laid over the picture in a new encode (`finish --patches`, ~15 min), or their parts
    re-rendered (`render --only`); a full render only when the timing moved everywhere (a re-voice). Patches match the picture by frame
    number, never by time (a render's timestamps drift up to 8 ms by a film's end). Many changed shots go as one reel per part
    (`PIPE tools/pipeline/review_reels.py <video> --version N --since-version M`, planned from the code diff). Every verdict goes into its
    casebook the same turn.

## Before it goes to the creator

**A first version free of actual mistakes.** `pipe.py <video> gate` runs before every render and `render` refuses code it hasn't
passed: the sound half (A1-A13 + the lock) and the picture half (B0-B26, every frame probed), each check proven on real notes of a
creator: `standard/PIPELINE.md`. A new kind of note from the creator = every instance of its kind fixed, its check added to the gate and
proven on their case, then the rule. **The gate confirms, it never discovers:** every builder and fixer runs `pipe.py <video> gate
--scope <the frames of their shots>` (every picture check on those shots only, 1-2 min for a handful) until it is clean before handing
back; the full gate before the render only confirms, and a flag it finds is a miss of the loop, written down as such. **One full gate
round a build** (`standard/WORKFLOW.md`).

*After the render, the render scan (`qa_render_scan.py`: black dips, stray frames, render-time freezes) runs on every render by itself.
The items below that are marked (render) are covered by the scan and by the gate's probe; run them by hand only for what the scan and the
gate can't see. Everything before the render runs every time.*

- [ ] **The code checks before every render** (each exits 1 on a fault): `EDIT tools/motion/qa_continued.py "prep<id>*.py" --code
      "src/<video>/*.tsx"` (no two clips from one camera shot of their source, no span twice, across every prep file and every copy of one
      online video); `PIPE tools/motion/qa_repeat_pics.py --src tools/motion/src/<video>` (no picture twice in the film by content, across every code file, unless
      the extra place says `named-moment:` or `repeat: <why>`); `PIPE tools/motion/qa_options.py ...` (every shot's media on a board);
      `PIPE tools/motion/qa_cards.py <video>` (B19); `PIPE tools/motion/qa_still_words.py <video>` (B20); `PIPE tools/motion/qa_shots.py
      <video>` (B22); `PIPE tools/motion/qa_devices.py <video> --list` (B23); `EDIT tools/motion/qa_kept_area.py` (each clip ~100% kept and
      filling the frame, a bar crop counts as a crop); `PIPE tools/footage/qa_upscaled.py "prep<id>*.py"`; `PIPE tools/motion/qa_fades.py
      tools/motion/prep<id>.py` on every span (no clip opening or closing inside a fade or a dissolve: the cut scans see hard cuts only; the gate's
      B2 runs it on every play); `grep -n "rate={0\." src/<video>/*.tsx` (no rate under 1.0 outside a deliberate replay: an overrun gets an
      earlier in-point, a second clip or a cut).
- [ ] **The static clip audit** (`pipe.py <video> audit`: every play's asked span against its file's length in `src/clipdurs.json`,
      every shot and play under 0.5 s, plays under 1.0x, both edges against the source's own cuts, `has_b_frames=0`) shows 0 overruns,
      run after every re-sync of the words and before every render. **Every component that plays a clip is in the audit:** `video.toml
      [audit] plays` (src + start) or `bg` (a background clip). A piece left out of the audit hid a 4-frame flash (an inset opening on its
      source's previous shot), a clip 0.05 s short and two insets opening on a cut.
- [ ] **Every EDGE row of the audit read as frames:** `pipe.py <video> audit > audit.txt`, then `EDIT tools/motion/qa_edgesheets.py
      audit.txt <render or picture> <dir>`: a different picture inside the shot or a fade from black is fixed, re-audited, patched; footage
      that is choppy by nature (a top-down scroll scores a "cut" on every frame) and a deliberate switch are not. (Nine real slivers hid
      among 59 rows that the plays sheets missed.)
- [ ] **Every play's first, middle and last frame read on its sheet** (`pipe.py <video> plays`, before every render): each shows what
      its words say; no disclaimer card, black, end card or stray logo where footage was meant (an "early test" line played a disclaimer card for
      1.75 s that the edge scan and the stills both missed). Its dark-frame list is looked at one by one (a logo or a night shot may be
      meant).
- [ ] Both edges of every clip at 30 fps (`PIPE tools/footage/scan.py <clip> <from> <to> <out.jpg> --step 0.033`): no frame of the source's next shot; `PIPE
      tools/motion/qa_flash.py <Comp>` (slivers from the clip audit); every flag looked at (a bright or black first frame, a sliver of
      another shot, a clip fading up from black, a graphic's empty first frame) and the real ones fixed before the creator watches.
- [ ] **Every outside source's own frame rate measured before it's cut** (`qa_cadence.framediffs` on the file: the share of frame pairs
      that don't change): a capture repeating every other frame (~15 real fps in a 30-fps file) shows as a run of holds in the render's
      stutter check; a clean 30-fps capture changes on nearly every frame.
- [ ] A 2-fps sheet of the whole picture read against the words (render): each shot shows what its words say; every name, place, thing
      and number in the script has its picture (a film once lacked 22); every shot of 4 s or more is live.
- [ ] **The storyboard and every builder's shot plan read row by row before they're built:** no text-only card (a word, a stamp or a
      number on black or on a blurred photo) and no "a later part" of a camera shot the video already shows (nine text cards, seven
      continued shots and one stock clock four times were caught only on a render's sheet; real pictures existed for all of them).
      And `PIPE tools/pipeline/marks_ends.py <pages.json> <page dir> --used "src/<video>/*.tsx" --sheet <png>`: every lit box ends where
      its word ends (a box lit to "Recor" of "Record"); judge each flag on the sheet (punctuation trips it too). And `coherency.py
      packet`'s two lists: every gloss (one per term) and every still shown over 1.3x its pixels.
- [ ] **The picture moves when the words move; a moment the words point at is shown, not carded:** `PIPE tools/motion/qa_still_words.py
      <video>` on the gate's probe and the words: STILL_UNDER_ACTION (a still, a frozen or marked hold, a page or a text or number card held
      under a verb of motion, a change, "one ... at a time" / "every single" / "year by year", or a list said over one held picture) and
      CARD_FOR_MOMENT (a card under "we can see", "in the video", "shows"). Pieces acting the words out (2+ changes inside the held run:
      things appearing, going, moving) are not a held picture; a held picture under an action with no footage carries `// no-footage:
      <action>, searched: <wordings>`. A flag is fixed, or allowed in `gate_allow.json` with the reason that proves it.
- [ ] **The named thing found at a glance; real pictures before artwork; no murky picture:** `PIPE tools/motion/qa_shots.py <video>` on
      the gate's probe: SUBJECT_MISSING (no `// subject:` line); SUBJECT_LOST (the box on screen more than 22% off the middle, under 75% on
      screen, small or dim: cash at 70% across and 76% down had to be searched for); ART_OVER_REAL (artwork where a real picture shows it),
      ART_CLOSE (a third artwork shot inside 20 s), ART_SHARE (over 8% of the film); DARK (a picture standing alone with mean light under
      14, 95% under 64 and no block over 90; black cards pass; allowed with the reason when the line is about the dark). A fresh span of a
      used record is cut only after its own frames are read: `find_shot.py` prints each hit's lit and murky spans. A murky span is
      re-picked, never lifted.
- [ ] **No device becomes the film's default, no circles of cropped screenshots, no stamp on a mere phrase:** `PIPE tools/motion/qa_devices.py <video>
      --list` (B23): DEVICE_SPREAD, ROUND_CROP, STAMP_PHRASE, emoji graphics as one device. Every builder brief names the devices the
      film already uses (`--list`'s table).
- [ ] **Text cards are the last resort** (B19 CARDS: a reason on every card, at most 8% of the film, never two within 20 s) and **every
      mark big and central** (MARK_SMALL, MARK_CORNER: measured on screen at full light, so a picture framed onto its target first passes).
- [ ] Repeats: no narration line said again word for word from another video (`script_lint.py`'s "a line also in another video" flags
      rewritten) and no graphic taken one to one from another video (rebuilt inside the style); inside the video no footage or song twice.
      Footage MAY repeat across videos: the best fit wins, and a past video having played it is no reason to pass it over.
- [ ] Other creators' material (their footage, thumbnails, titles, pages) within the creator's share for the video, the whole video's
      total, measured on the shot list before the render (stacked or spread is the chat's call).
- [ ] Screen time by kind: pages near ~16%, each page kept only where its words are the point.
- [ ] Every clip's span chosen on its whole sheet: the thing named is the main frame, whole and clear.
- [ ] Every label on a graphic read: could a picture, face, logo or clip stand in for the words? Then it does.
- [ ] Every graphic frame run through the AI-template checklist above: real material in it, no shape standing for a real thing, two or
      more tells = redo; every text box checked at its end state for overflow; every aimed zoom checked on its last frame.
- [ ] Every graph's form named against its point (a share: a donut; a contrast: two sides; a count: units; growth: before/after), labels
      once on one side, no guide lines.
- [ ] Every mark ends at least 0.6 s before its page's cut; a second page of the same source only when it shows something new.
- [ ] Every lit phrase shows whole inside its card's crop: no word of it marked alone at the crop's edge (a number lit on a crop's last
      line with its source cut off below). Read each crop's marks against its crop lines.
- [ ] Graphics: real objects as real cut-outs (no icon beside a photo object); each graphic held up against a professional reference.
- [ ] Pages: the headline stays in frame through the push, the quote lights as it's said, text sharp and whole, one marking style; the
      lit phrase a few words, never most of the card, and the mark inside its own line on a still at 100%.
- [ ] **Text in graphics is HTML, not SVG `<text>`** (SVG labels flickered on every third frame of a render; a label that flickers is
      fixed by a patch of its one shot, never a full render).
- [ ] Every arrow, cross, stamp and spot checked at 100% on its frame; no circles; no mark where the frame already shows the thing.
- [ ] Real people's clips: start matched by audio, at 1.0, the speaker's mouth moving, the right name, subtitles clear of the
      broadcast's banners. The bite's end cut right after the last word: its word times from Whisper on the bite's own audio
      (`word_timestamps=True`), checked against its loudness every 10 ms; the last word's end and the next word's start written down; a
      tight gap goes to the creator as 3-5 numbered samples.
- [ ] Every picture's pixels against its size on screen at the render's size: never blown up past 1x for a cover or a photo (280x350
      covers shown 820 px tall read as mush), never past 1.3x for a still; every qa_render "soft shot" WARN looked at and fixed.
- [ ] Letterboxed sources whole with their bars, no full-frame picture under 1080p, no push that cuts off a subject or the source's own
      on-screen text, logos on their weight.
- [ ] Every effect nameable in three words, on its frame; every highlight has its marker from its light's first frame; a removed visual
      took its sound with it. `EDIT tools/sound/sfx_sheet.py <cues.py> <final.mp4> <out.jpg>` read row by row (render), and score.py's
      "effects against the voice" line clean (none over -7 LU, nothing memey outside a joke).
- [ ] `score.py`'s report: voice over music ~22 dB (checked 20.5-24), "silences outside the designed ones: []", never two beds at once;
      final -14 LUFS, true peak at most -1 dBTP; the sound gate clean.
- [ ] Footage moves smoothly: `has_b_frames=0` on every clip; after any re-render `PIPE tools/motion/qa_cadence.py <render> <previous>`
      reports 0 held frames (render).
- [ ] Every card moves in one go: `node tools/motion/qa_camera.mjs src/<video>/<Comp>.tsx --json out/cards.json` reports 0 TWO MOVES
      (from the code: every page and still card); on a render `EDIT tools/motion/qa_zoom.py <render> out/cards.json <dir>` measures the
      same cards frame by frame, "one move" each, its plot looked at. A new card component passes both before it is used.
- [ ] The black frames (the render scan, and `qa_render.py`'s "black frames" line on the export): every black under 0.2 s inside the
      film looked at; a designed one (a wipe through black) kept with a reason, the rest fixed (one-frame blacks at the ends of chains of
      clips are the usual find).
- [ ] `EDIT tools/qa/qa_render.py <mp4> --format long --words <words.json>` (render): no FAIL; cuts a minute 18-32; every WARN looked
      at on its sheet, fixed or allowed (`--allow a-b`) with a written reason.
- [ ] The end: the subscribe ask at a real break, the like and comment sign-off on the last line, then a fade to black and silence,
      nothing after.
- [ ] The chat's own read first, section by section against `BAR_LONG_FORM.md` and the newest signed-off video: the creator's notes are
      a sample, not the list. But nothing of the chat's stands between a render and the creator: the watchable copy goes the minute it
      exists, and their watch is the fix list (`standard/WORKFLOW.md`).
- [ ] After the creator's notes: every fix of their judgement and every bigger visual fix goes to them as a quick before/after sample
      first; the full render only after their OK. A clear fix is one measured fix, patched in without a sample.

## Read before building one

1. `standard/BAR_LONG_FORM.md`, then the newest finished long video of this studio (its export, code, cue sheet, BUILD.md and review
   files).
2. `rules/SHARED.md`, `rules/LONG_FORM.md` and the casebooks `cases/PICTURE.md`, `cases/COHERENCE.md`: the creator's line.
3. `standard/KIT3.md` (the look and the pieces), `standard/3D.md`, `standard/GRAPHICS_KIT2.md`.
4. `standard/research/LONGFORM_CRAFT.md` §0, §2, §3, §10 (outside evidence, except where it conflicts with this file: this file wins).
5. `standard/research/MOTION_CRAFT.md` §2-§3 and `tools/motion/src/house/` (the house motion curves and the older house pieces).
6. `standard/research/FOOTAGE_SOURCING.md` §0, §3, §5, §7 and `kb/FOOTAGE.md`: where real pictures come from.
7. `standard/CHECKLIST.md`, `standard/PIPELINE.md`, `tools/qa/qa_render.py`'s docstring: every check and the mistake behind it.
