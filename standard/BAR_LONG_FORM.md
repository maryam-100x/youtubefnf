# The long-form bar: what a long video at this studio's level is

*Part of `STANDARD.md`. There are no example videos in this repo, so this file is the bar in words: what a minute of a finished long
video looks and sounds like, measured; two openings worked second by second at the finished look; and what makes a whole long video
hit. Read it in full before every long video, beside `standard/LONG_FORM.md` (the rules and the checks), `standard/KIT3.md` and
`standard/3D.md` (the pieces), `standard/SOUND_AND_VOICE.md` and `standard/MUSIC.md` (sound and music),
`standard/SCRIPTS_AND_PACKAGING.md` (the words) and the casebooks `cases/PICTURE.md` and `cases/COHERENCE.md` (where the creator drew
each line). This file describes the level; the rules that hold it live in those files and in `rules/LONG_FORM.md`. When a rule and
this file disagree, the rule wins and this file is rewritten to it.*

**The bar is the quality, never the moves.** The numbers below were measured on finished videos that passed; the two openings in §2
are invented to teach the level. Nothing here is a template: a new video reaches the same level with its own pictures, devices,
effects and music, chosen for its own words. Copying a device from this file (a typed date, a black stop, a row of products, a stamp)
into a video because it is here is the template mistake; using it because the words ask for it is the craft.

---

## 1. What every minute has

A minute of a long video at the bar, played to someone who has never seen the channel: they always see the thing being said, the
moment it is said, sharp and full frame; they never wait on a picture that has stopped saying anything; they hear every action and
never notice the mix; and nothing on screen looks like a template. The qualities, one by one, with what they measured.

### 1.1 Pace: cuts a minute, holds and bursts

- **About 25-32 cuts a minute in the body, cut on meaning; openings faster.** Measured: a hit documentary of about ten minutes ran
  28.2 cuts a minute (minute by minute 33, 22, 37, 20, 33, 34, 23, 31, 23, 14), median shot 1.87 s, quartiles 1.25-2.60 s; shot
  lengths under 1 s 20%, 1-2 s 35%, 2-4 s 36%, 4 s and over 8%. Openings that passed: 31-36 cuts a minute (30 shots in 56 s; 43 shots in 71 s). A technical explainer that passed ran slower on
  purpose, 21.3 a minute, median 2.5 s, because a technical point needs its picture held long enough to read. A film told mostly on
  stills and pages runs nearer 20-25. A video at 13.9 a minute with half its shots at 4 s or more, most of them frozen frames of one
  source, failed: after the first second of each hold the eye had nothing new while the voice explained.
- **Holds only on something live.** A shot of 4 s or more is a real clip playing (a speaker, a moving map, a demonstration to its
  payoff, a time-lapse) or a designed black; the longest holds in the hit were a long moving shot (10.7 s) and the sign-off (10.4 s).
  A still is one beat, about 2-3.5 s with one purposeful move; a still held 5 s was flagged at once.
- **Bursts on a list or a big claim, never as an even beat.** When the point is "many" (8 shots in 3 s; 5 money close-ups in 1.5 s),
  0.2-0.4 s a picture. When each moment must register on its own, 0.4-0.9 s each on the music's quarter notes: four moments that read
  beat seven that flicker.
- **No clip under ~1 s between longer shots** outside a deliberate burst: a half-second clip between two longer ones reads as a
  mistake and nobody sees it, so the shot before plays on instead.
- **Nothing on screen for ~0.5 s or more unless its thing is arriving**, nothing standing still past ~2 s (a held graphic keeps a
  visible drift), words on screen at least their reading time (1.2 s, +0.03 s a character past 10) before anything cuts them.
- **The opening decides the video.** The hit kept 95% of viewers at 0:00, 74% at 0:23 and 52% at 0:41; the one big exit was the end of
  the intro, then the curve fell only about 3 points a minute (46% at 2:00, 29% at 9:00). Measure any reference the same way: `EDIT
  tools/qa/measure_edit.py <mp4> <out>` (scene cuts, shot lengths, loudness, contact sheets).

### 1.2 Every picture on its words

- **Each shot starts on the first word of what it shows, and shows exactly that.** Shots are anchored on the narration's own word
  times (`w(beat, phrase)` over `words.json`); the picture changes on the first word of its own sentence or clause, never under the
  tail of the one before. At an opening's pace the cut moves onto the bed's eighth note when one sits from 0.16 s before the word to
  0.04 s after it, so the picture lands on the music and the word at once.
- **Everything named gets its own real picture on its word:** every person, place, thing, number, feature and step. In a list each
  item is its own picture ("chop, stir, plate" is three clips; a label is never a substitute for footage). Words that point at the
  screen ("this", "here", "like this") only over the thing itself.
- **The exact thing, in action.** Words naming an action get that action (a dog catching the ball, not the dog at rest;
  whisking the eggs, not a bowl of eggs); a feature shown in use, not its spec sheet; a claim about how something works shown on the
  moment that proves it; the literal moment that exists is found before anything is built (a line about passing the salt gets the clip
  of the salt passed). A demonstration plays its whole action, start to landing.
- **Found at a glance.** The thing named is big, central and lit; the clearest picture is judged by how it reads on screen (face-on,
  big), never by its source's prestige; a picture too dark to read is replaced where a brighter one exists; footage has something
  going on (people, vehicles, hands at work), never an empty vista unless the line is about that place.
- **Sharp and whole.** Every full-frame picture 1080p or better, the least-compressed span of its source; a still never past 1.3x its
  own pixels; a soft 720p source pushed at most 1.02. Clips play full frame, filling the screen, never in a panel, never cropped to
  hide an overlay; a letterboxed source whole with its own bars. A zoom opens on the whole picture and moves onto its subject,
  centred, only where it lands on the words' own thing; a crop that only makes people bigger has no purpose; a slow keep-alive drift
  (1.00-1.03) is not a zoom and stays.
- **Frame 0 of the video is its first words and something to look at:** a subject the eye lands on at once, big, lit and moving.
- **Fresh and best.** Never the same clip span twice inside a video; never the same picture twice when material is plentiful; the only
  real example of a thing stays even under a loose line.
- **How it is held:** an options board per line (5+ candidates from different sources, every source scanned whole at 1 fps so its best
  moment is on the board, not its first fitting one; the pick and why it beats the rest: `tools/motion/options_board.py`,
  `tools/motion/source_sheet.py`, `tools/footage/find_shot.py`, `tools/footage/pick_boards.py`; `tools/motion/qa_options.py` fails a
  shot whose media no board names), a shot comment the gate reads (`// subject:`, `// zoom:`, `// repeat:`), the coherency read of
  every line against its picture (`tools/pipeline/coherency.py`, calibrated on `cases/COHERENCE.md`), and the gate.

### 1.3 The speaker on screen for their own words

- **A person named is shown the first time they are named:** a name chip on them in their own footage (`TagShot`), or their photo
  whole with a caption (`PhotoFrame`).
- **When someone's own words carry the line, they say them.** The narration stops; their clip plays at 1.0 in its own sound, mouth
  moving, its start matched by audio; "Name: words" subtitles from the source's own captions sit above the broadcast's own lower
  third; the bed drops about 32 dB under them. One or two sentences, after our line: our line teases or paraphrases, never the same
  words first. The clip starts right on our last word, with nothing of the next line before it (`tools/sound/hold_insert.py`, the
  edges measured). A clip under the narration is muted, and nobody's voice ever runs over a clip of them saying other words.
- **A quote or a named reference whose original exists is played**, as a short insert after our line, not only described.

### 1.4 Real receipts, shown

- **The claim's proof on screen:** the real page, post, video page, store page or document, sharp and readable on a TV. It cuts in (no
  fade), cropped to whole lines, captured at phone width so the words are ~60 px on screen (`tools/footage/capture_page.mjs --mobile`,
  with `--mark "<phrase>"` for exact word boxes), the page inside the frame for its whole move, the camera travelling once onto the
  lines.
- **Lit on the words that are the point, as they are said.** The picture stands still from the light (a mark on a moving picture
  drifts off its target), the rest dims to about a fifth of its light and the thing is exposed (kit3's spot look: the light at least
  0.18 x 0.22 of the frame, no colour rim), the marker sound on the light's first frame. A mark only where the eye has a choice (never
  on what everyone already sees), at least 48 px tall on screen; a small thing is zoomed into in ~0.45 s from the frozen whole; things
  named together light together; never a light in a shot's last 0.6 s; at most ~3 marks in any 5 s. Word-by-word lighting only where
  the voice reads exactly those words then; otherwise the card shows whole from its first frame.
- **A number that is the point is shown on the thing it counts:** the video's page with its count marked, the store page with its
  price; a number with a picture but no page beside its picture (`NumberBeside`); a number alone on a card over blur never. Every
  number carries its unit and its subject; a share says "x of y" and of what; a date is absolute.
- **Pages are the minority:** about 16% of a passed opening's time; a film at 35% was felt at once as too much text. Text cards are
  the last resort: at most 8% of a film, never two within 20 s, each with a written reason (`tools/motion/qa_cards.py`, gate B19),
  because people watch to see, not to read.

### 1.5 No flash frame, no frozen shot

- **Flashes the bar never has:** a lone shot so short it reads as a flash; a sliver of the source's own next shot at a clip's edge
  (every clip's edges frame-stepped; detectors miss soft cuts); one dark frame at a cut (a burst whose last item ended a frame before
  its shot, showing the black behind it); a white-out first frame; a clip fading up from black; a graphic easing its dim in at a cut
  (one bright frame of the shot under it); an empty first frame before a graphic draws. At a cut a graphic starts in its settled
  state.
- **Freezes the bar never has:** a clip shorter than its shot (the renderer holds its last frame: the static clip audit must read 0
  overruns), the source's own stutter inside a span (`tools/motion/qa_midfreeze.py`), a still held while the words move on, an eased
  push that stops in its last third (the camera's push is linear), the same picture carried across a cut with its push restarting
  (`tools/pipeline/qa_rezoom.py`). Clips play at 1.0 (`lib.tsx`'s `Clip` never goes below it); a slowed, interpolated replay breaks
  into blocks and is not used.
- **Nothing shakes.** A card that moves moves as ONE picture under one transform; edges set as their own fractional sizes step a pixel
  on different frames and read as a twitch.
- **Measured, not eyeballed:** the gate before every render (`PIPE tools/pipeline/pipe.py <video> gate`), the render scan on every
  render (black dips, flash frames, freezes), the luma of every frame (no frame under 20 between brighter neighbours).

### 1.6 Graphics built from real material; premium; less is more

- **The real thing first.** Footage, the real page, the real interface, the real product photo show the point wherever one exists. A
  built graphic only where nothing real shows it, and then built FROM real material: cut-outs of real objects and people, real photos
  whole, real screenshots and drawings annotated (the thing lit, a magnified inset), maps at true scale. An explaining line gets a
  built animation made of that material (a timeline on the real pictures; the pictures side by side; the real cut-out travelling); a
  change between two pictures shows both, whole, with the changed thing cut from one travelling to its place in the other.
- **What premium looked like when it passed:** the subject's own element drawn crisp and centred, the picture behind blurred back, the
  statement under it, held ~1.5 s; a built scene with real-looking licensed 3D assets, light and motion blur; a screen nobody filmed
  built in the house phone (`kit3d` `Phone3D`) acting out exactly what the words say; a real prop landing on its word for an object no
  footage holds. An emoji is a prop inside such a piece, never the graphic.
- **What failed:** shapes standing for real things (a ring drawn from a circle and a diamond; a train as circles on a road), circles
  of cropped screenshots all over a film after one good graphic, a crowded graphic with five ideas, a busy pop-in reveal over two long
  quotes, a borrowed diagram with hairline outlines and stacked chips, a zoom into nothing, a graph off centre, a line drawn under things that
  marks nothing, words slammed tilted over a half-hidden logo.
- **Less is more:** one idea per moment, centred and big; an overlay shows once; a point is made once; no add-on that doesn't belong;
  simple and centred beats complete. The two-second test: a still of the graphic, read for 2 s with the sound off, says what it is,
  what the number counts (with its unit) and who or what is pictured; the group is centred within 4 px and its gaps are equal within 2
  px.
- **No device becomes the film's default.** A passed piece is a level, never a device to copy: one film used the same number card for
  82 of its 862 shots and read as one effect repeated (`tools/motion/qa_coherence.py` caps it; gate B23). One self-made animation idea
  is used once a video; one shake a video at most, on an impact.
- **3D only where the words are about the object**, once or twice a video, one object, one light, one camera move each
  (`standard/3D.md`): `Emblem3D` when a name IS the event, `Parallax25D` on a photo with a clear subject before a deep scene,
  `Globe3D` for a real place on Earth, `Phone3D` for a post or a screen, `CaseNumber3D` for a number about a thing that has a box.
- **The never-list** (`standard/LONG_FORM.md`'s AI-template table): a second accent, neon, glows and gradient blobs, borders on cards,
  glass, monospace "data", tracked-caps eyebrows, pills, navy cards, a number centred alone over blurred footage, the same entrance on
  everything at once, any AI-generated picture.

### 1.7 One design system per video

Every built graphic of a video comes from one system, kit3's (`tools/motion/src/kit3/tokens.ts`; in full in `standard/KIT3.md` §1).
Built by many hands with many looks (five credit styles, four ink colours, type from 22 to 220 px) a film looks amateur, whatever each
graphic is worth alone. What the system is:

- **The grid:** 1920 x 1080 at 60 fps; content box x 120-1800, y 96-968; groups centred on x 960, y 532 by their real widths (never a
  hand-set `left:`); title-safe 96 px at the sides and 54 at the top and foot; the band under y 968 is the credit's; spacing steps 8
  (inside chips), 16 (kicker to headline, photo to caption), 24 (headline to the line under it, number to its subject), 40 (card
  padding, 48 at the sides), 64 (between pictures in a row), 96 (a picture to the text beside it).
- **Type:** one family (Archivo), tabular figures, sentence case, normal tracking, no italics, HTML text (never SVG text). Display 168
  px / 800 (one per frame: the number, the stamp, a year); Headline 84 / 800 (a statement, a quote up to ~70 characters); Title 52 /
  700 (names on pictures, a number's subject, longer quotes); Label 40 / 600 (kickers, captions, rows: the smallest anything to be
  read may be); Meta 26 / 500 (the credit only). Caps only in a stamp. Words are written to fit (a headline line ~24 characters in an
  820-px block), never shrunk to fit.
- **Colour:** ink `#F4EFE6` for all text and marks, 66% for muted lines, 30% for a quote's words not said yet; the creator's one
  accent (`tools/motion/src/brand.ts`) only on what the voice names now, at most one accent thing a frame (two only when the voice
  names both), never on decoration; black for every dim and shadow; the one card's surface black at 88%.
- **One card** (radius 12, padding 40 / 48, shadow `0 2px 6px rgba(0,0,0,.35), 0 28px 72px rgba(0,0,0,.55)`, no border, no glow;
  760-820 wide beside a picture, up to 1200 alone), one card a frame; chips radius 6. A card holds text; a cut-out never stands on a
  card, a clip never goes in one.
- **Pictures:** the ground under a built graphic is the shot's own footage, full frame and running, defocused 8 px, dimmed to 42%,
  scaled 1.04, a soft vignette (`Stage`); consecutive built shots on grounds of different colour (four small objects in a row on the
  same murky blur read as a slide deck). Rows of cut-outs: one height, widths from their visible pixels, 64 px between visible
  figures, centred while items arrive, one floor with a contact shadow under each, names under them, never overlapping, never a
  straight cut edge inside the frame (`Row`). Photos whole at their own shape, radius 12, at most 1.3x their pixels, a caption under
  (who or what; when, where). Logos alone, centred to the eye, about 280 px tall, never under text or half hidden.
- **Motion** (`tools/motion/src/house/motion.tsx` `EASE`): entrances 0.40 s on the enter curve, rising 32 px (cut-outs 56), starting
  0.06 s before their word; text 0.30 s, a block's parts 0.08 s apart; exits rare and quicker (0.25 s); a move on screen 0.90 s, a row
  in ONE move; the camera linear over the whole shot, 1.00-1.03 (1.04 on a ground), one way, never back; a number rolls as an odometer
  for 1.2 s, each digit a continuous strip; a ranking glides 0.90 s with the rank numbers fixed to the places; a stamp lands in 0.16 s
  from 1.15x, straight, the footage under it dimming to 50%; a word lights in 0.12 s from 0.04 s before it is said. Nothing steps,
  springs back, or moves in a shot's last 0.25 s.
- **One credit:** one line, bottom right (right edge x 1824, foot y 1026), 26 px on a quiet chip: "whose picture · Source: where the
  number or quote comes from"; short, upright, never over a subject.
- **The video's own pieces** are built from these tokens, written into the video's notes with a reference still of each before any
  section uses them; a piece the system lacks is added to kit3 first (with its test), never a second look. Widths are measured only
  after the font has loaded (measured before, every number's digits came out 13% narrow and cut at their edges).

### 1.8 Sound on what happens

- **Every action has its sound, on its frame, and only actions do.** Every entrance, slide, roll, landing, stamp and light is heard;
  each effect is nameable in three words; one house sound per job (`assets/house_sfx.zip`, its manifest names each): `pop` an item
  appears, `marker` a highlight lights (one per lit phrase, from the light's first frame), `count_up` only under digits that visibly
  roll, cut to the count, `number_land` a number or date landing, `stamp` on the stamp's landing frame, `click` a real click,
  `chapter_card` a soft airy whoosh as a card or a row slides in, `paper` a document sliding on, `typing_keyboard` or `key_press` a
  typed line, `notification` a message landing, `phone_ring`, `money`, `error`, `fail`, `camera`, `glass_shatter`, `whoosh_fast` only
  on a real fast flight across the screen, `cinematic_hit` a dramatic landing, `reveal_boom` a big reveal (pure sub: big on a TV),
  `black_cut` a low stinger on a cut to black, `bass_drop` a statement drop (the same sound for every drop, on the statement's key
  word), `glitch`.
- **Under the voice, always:** no effect over -7 LU against the voice over 1.5 s (the loudest in a passed long video: -8.1 LU).
- **No quota, and no patter.** A passed 71-s opening had 12 effects; a passed explainer about 5 a minute. Two of a kind within ~1.5 s
  is overkill; a sound on every dot of a graphic made the ear hurt; a swell used every few seconds across a film became noise (27 cut
  to 13); `tools/sound/autocues.py` never places 4 inside any 5 s.
- **Silence where it's right:** a number said with weight and nothing shown lands harder with no sound; a removed picture takes its
  sound with it; a sound the viewer can't tie to a picture goes (a ticking in a bed was taken for an effect and banned).
- **The source's own sound** where it helps: a speaker's own voice, the wind or the crowd of the footage, low under the narration.
- Placed from the composition's own times, never by ear: `videos/<video>/score/cues.py` with `pal(name)` (score.py refuses unrated
  sounds), `autocues.py` for markers, stamps and counts from the gate probe, score.py's report read after every mix.

### 1.9 The music bed

- **One sound world for the film, under the voice.** Instrumental, no lyrics, never two beds at once; a bed per chapter or real turn,
  changing with a fade at the turn on the next bed's downbeat; the voice ~22 dB over the bed while it speaks; a designed stop never
  digital silence (a tail rings under it). The music is the creator's own tracks or music made in code (`standard/MUSIC.md`); a bed
  the creator rejected never comes back.
- **In the opening, the music is chosen first and cut first, and the picture is edited on it.** The bed is picked for the arc the
  opening needs, measured bar by bar (`EDIT tools/sound/analyze_tracks.py`: energy and the share in the voice's 1-4 kHz band, lower
  sits better; `EDIT tools/sound/grid.py`: the downbeats): for example a drumless pulse rising under the hook, the drums entering on
  the story's first turn, a drumless stretch under the trouble, the drums back on the promise. Edited in whole bars on downbeats with
  20-ms joins, re-made from the word times whenever the voice moves; the cuts on its eighth notes as in 1.2. Its events are the
  story's turns, never a hype drop: the level under the voice stays where it is, each event heard (a hit on the drop's downbeat under
  -7 LU), and the bed blooms after the last word and fades with the picture.
- **The body's beds are steady ambience** (`standard/SOUND_AND_VOICE.md`, "Music: the mixing rules"): a bed's own builds evened out, a
  new bed only where the story really turns.
- **The duck follows the voice itself**, not only the word times: a hole in the word times once let the music jump up for 1.5 s
  (`tools/sound/qa_word_holes.py` lists every hole after a voice lands).

### 1.10 The voice under it all

One person from the first word to the last: warm from the first syllable (a tired, breathy opening is the first thing a viewer hears
and was flagged), no word swallowed, stretched or clipped by a cut, pauses at about 0.25 s between sentences and 0.12 s inside them,
no audible inhale, any silence over ~0.75 s with breath or dead air a fault; -14 LUFS through the voice chain; names said the way the
audience says them. The method and its checks: `standard/SOUND_AND_VOICE.md`, `standard/VOICE_LOCK.md`.

---

## 2. The 60-second prototype at the finished look: two worked openings

Every long video starts as its first ~60 seconds built exactly as the finished film will be: the real words, the real voice, the
pictures, graphics, sound and music, through the gate. It goes to the creator before the rest is built; once they pass it, it is the
reference every section is held to side by side. How one at the bar is made (`standard/WORKFLOW.md` has the order and what blocks each
step):

1. The opening's words final and voiced (the voice lock), so every time below is the real voice's.
2. A storyboard, `videos/<video>/STORYBOARD.md`: per line the picture (file and span, why it beats the others), the subject's box, the
   move, the marks, the sound. The casebooks are checked against it before anything renders.
3. An options board per line (`videos/<video>/options/`), every source scanned whole first.
4. The look written down before any graphic: kit3's tokens and any of the video's own pieces, each with a reference still.
5. The bed chosen and cut first; the picture cut on it.
6. The build (kit3, kit3d, house, `lib.tsx` `Clip`), proof stills of every graphic at its first frame and its end state.
7. The cue sheet: every action with its sound; the mix.
8. The gate, the coherency read, the render, the render scan; the watchable copy to the creator the minute it exists.
9. The creator's notes taken as classes (every instance in the film, not only the one named), each verdict into its casebook.

The prototype ends on a finished sentence with the bed's tail: never cut mid-word, never on a black last frame.

**Both examples below are invented to teach the level:** the companies, people, places, numbers and sources are placeholders. In a
real video every fact comes from the research with its receipt, and every picture from the options board. The two are deliberately
different in kind (a story documentary at an opening's full pace; a technical explainer a little slower, because a technical point
needs its picture held long enough to read) and share no device by design. Times are seconds on the film. **Sound:** E = an effect
from the house pack, M = the music.

### Example A: "the rise and fall of a phone maker" (a story documentary)

*The promise in the notes: how the phone in every pocket went to nothing, year by year. Norvane, a phone maker; Ada Lindqvist, its
chief executive. Bed 1: an instrumental at ~90 bpm (a bar 2.67 s, an eighth note 0.33 s), picked of twelve for its arc: a drumless
pulse rising for ~10 s, the drums, a drumless breakdown, the drums back. Bed 2: calm, for the founding years. 27 shots (30 pictures
with the burst's four) in 60 s: an opening's pace.*

**A1 · 0.00-1.55 · "On March 31st, 2021,"** Screen: news drone footage of the headquarters at night, the roof sign lit, the camera
creeping toward it; "March 31, 2021" types itself into the dark sky above the roof, each key on its letter's time. Why: the first
words are a date, so the date is the picture; frame 0 already has a subject (the lit sign, moving), never an empty sky waiting for
text. Build: kit3 `TypedShot` (the keys from the word times; the kit pulls them in so the line is whole 0.3 s before the cut), the
clip through `Clip` at 1.0. Sound: E `typing_keyboard` cut to the typing's length; M bed 1's drumless pulse, rising.

**A2 · 1.55-4.20 · "every Norvane phone still in use"** Screen: a burst of four owners' phones in four places, 0.66 s each: on a
taxi's dashboard, in a nurse's breast pocket, in a fisherman's wet hand, beside an office keyboard (news footage and owners' own
videos; one credit line across the burst). Why: "every ... still in use" means many, the one job of a burst; four on the bed's quarter
notes so each registers. Build: kit3 `Burst` (cuts on the quarter notes). Sound: no effect, the cuts are the music.

**A3 · 4.20-6.15 · "lost its signal for good."** Screen: an owner's own video from that night, full frame at 1.0: the phone's status
bar, the bars dropping out one by one, "No service". Why: the words name an action, so the picture is that action on the thing itself;
found on the board among the people who filmed the last night, where general phone footage was the weaker pick. Build: kit3 `Foot`.
Sound: E `error` on the frame "No service" appears.

**A4 · 6.15-8.70 · "The company had switched its network off."** Screen: the maker's own end-of-service page, captured at phone width,
cut in on its whole lines, the camera moving once onto them; on "switched" the page stops and "switched off on March 31, 2021" is
exposed, the rest dimmed to a fifth of its light. Why: the claim's proof is the maker's own words, lit only where they are the point.
Build: `capture_page.mjs --mobile --mark "switched off"`, kit3 `Page` (the mark snapped to the ink, the spot look); credit "Norvane ·
Source: norvane.com, March 2021". Sound: E `marker` on the light's first frame; M the pulse at its top, its last bar a riser into A5.

**A5 · 8.70-10.80 · "Twelve years earlier,"** Screen: 2009 news footage of a queue around a city block on the flagship's launch day,
people holding up the box. Why: the time jump shown as the era itself, at its height: the stakes begin. Build: `Foot`. Sound: M **the
drums in** on the cut, the story's first turn; E `reveal_boom` on the drop's downbeat (under -7 LU).

**A6 · 10.80-14.20 · "one in every four smartphones sold on Earth was a Norvane."** Screen: four real phones of 2009 (cut-outs from
their makers' press photos) slide in as ONE centred row on one floor, one height, 64 px apart, contact shadows, kicker "Smartphones
sold worldwide, 2009"; on "Norvane" its phone's name chip lights in the accent and the three others dim to 45%; the ground is A5's
queue running on, defocused and dimmed. Why: a share shown literally as one of four, readable in two seconds with the sound off; the
row's gaps and centring measured, never set by hand. Build: kit3 `Stage` + `Row` (`floor`, `litAt`, `dimAt`); credit "Press photos ·
Source: <analyst firm>, 2009". Sound: E `chapter_card` on the row's one slide; E `marker` as Norvane lights.

**A7 · 14.20-15.45 · "Presidents carried one."** Screen: an agency photo of a head of state stepping off a plane, the phone in hand,
whole, a gentle push. Why: the people named, caught in the act; a still is one beat. Build: kit3 `Still`. Sound: none.

**A8 · 15.45-17.00 · "Bankers slept next to theirs."** Screen: a 2009 trading floor, a trader in a loosened tie thumbing the phone
between two screens. Why: the claim played straight by real people; the joke is in the words. Build: `Foot`. Sound: none.

**A9 · 17.00-19.30 · "In 2009 it sold fifty-one million phones,"** Screen: the flagship's real retail box (its press-kit photo under a
glossy sleeve) turns once toward the camera; beside it "51" stands up digit by digit on "fifty-one" and turns to the accent; "million
phones / sold by Norvane in 2009" under it. Why: a number beside the thing it counts, made an object because the words are about the
object: the opening's one 3D piece. Build: kit3d `CaseNumber3D` (unit and subject required). Sound: E `number_land` as the last digit
lands.

**A10 · 19.30-21.60 · "and Norvane was worth more than eighty billion dollars."** Screen: a 2009 business news broadcast, full frame
and playing: the anchor and the broadcast's own graphic "NORVANE $80 BN", muted under the narration. Why: a second number in a row
gets another device (never two number cards close together): its real receipt alive, the broadcast's graphic already its biggest
thing, so no mark. Build: `Foot`. Sound: none.

**A11 · 21.60-23.35 · "That same year its chief executive, Ada Lindqvist,"** Screen: Lindqvist on stage at the 2009 keynote holding
the flagship (the maker's own keynote video); the chip "Ada Lindqvist · chief executive" lands on her on "Ada". Why: a person named is
shown the first time they are named, doing the job the words give her. Build: kit3 `TagShot` (`on` her). Sound: E `pop` on the chip.

**A12 · 23.35-25.40 · "went on TV to talk about the new touchscreen phones."** Screen: the touchscreen phones themselves: a rival's
2008 launch video, a finger swiping glass. Why: the thing she is about to judge is on screen first, so her words land on a picture the
viewer already holds. Build: `Foot`. Sound: none; M the groove.

**A13 · 25.40-28.80 · HOLD: her own words** Screen: her 2009 TV interview, her face, mouth moving, her own sound: "Ada Lindqvist:
Nobody serious is going to type an email on a piece of glass." subtitled above the broadcast's lower third. Why: the line before
teased it without saying it, so this is the payoff, in her voice; it starts right on the narration's last word. Build: the script's
HOLD beat, `hold_insert.py`, `Foot` with its own audio, the start matched by audio, the subtitle from the broadcast's captions. Sound:
her voice; the bed ~32 dB under it.

**A14 · 28.80-30.50 · "Within three years,"** Screen: a 2012 subway carriage, every passenger swiping a touchscreen. Why: three years
passing shown as the world switching to the thing she dismissed. Build: `Foot`. Sound: M **the drums stop** on the downbeat nearest
"Within": the fall begins in the drumless breakdown.

**A15 · 30.50-33.00 · "the papers were calling Norvane the slowest company in tech."** Screen: the real 2012 business-weekly cover
(the flagship drawn melting like a clock under the headline), whole at its own shape, framed on A14's subway footage defocused, a
gentle push. Why: a receipt that is itself a picture: the cover says it big, so no crop and no mark. Build: `Stage` + `PhotoFrame`
(caption "Business weekly, May 2012"). Sound: none.

**A16 · 33.00-35.40 · "Its own engineers were leaking memos that said the same thing."** Screen: the leaked memo, a real document,
slides on whole; it stops and its one line "we have become too slow to win" is exposed on "the same thing". Why: the trouble came from
inside, proved by its own paper; one line lit (lighting most of a page is no mark). Build: kit3 `Page`. Sound: E `paper` on the slide;
E `marker` on the light.

**A17 · 35.40-38.00 · "By 2013 it had lost ninety-five percent of its sales."** Screen: news footage of unsold boxed phones bulldozed
in a warehouse; on "ninety-five" the stamp "-95% SALES" lands straight over it (the footage dims to 50%) and stands 1.5 s to the cut.
Why: the opening's statement: a number said as a statement is stamped, landing on its word and standing past its reading time. Build:
kit3 `StampShot`. Sound: E `bass_drop` on "ninety-five", the opening's statement drop, heavy in the drumless quiet (it stands in for
the stamp's own sound: one action, one sound).

**A18 · 38.00-42.10 · "So in this video I'm going through the whole thing, year by year:"** Screen: the maker's whole life at true
distances, 1996 to 2021, drawing itself over the headquarters footage dimmed: founded, the first phone, the peak, -95%, the last
phone, the network off; one move along it; the span lights in the accent on "year by year". Why: the promise made visible: the viewer
sees the whole road the video will travel. Build: kit3 `Timeline` on a `Stage`. Sound: E `chapter_card` as the line draws; M **the
drums back** on "So".

**A19 · 42.10-43.70 · "the phone everyone wanted,"** Screen: the 2007 flagship turning on its pedestal in the maker's own 4K launch
film, its keyboard lighting. Why: each item of the list its own picture, from its sharpest source. Build: `Foot`. Sound: none.

**A20 · 43.70-45.30 · "the bet that sank it,"** Screen: the 2011 keynote, Lindqvist unveiling the maker's own touchscreen system to a
half-empty hall. Why: the bet shown as the moment it was placed; the empty seats carry "sank" with no word on screen. Build: `Foot`.

**A21 · 45.30-47.00 · "and the comeback that almost worked."** Screen: the 2015 comeback model sliding open in its launch film,
reviewers' cameras flashing. Build: `Foot`.

**A22 · 47.00-49.10 · "To see how a company that big"** Screen: the headquarters at night in 2009, every window lit, from a drone.
Why: "that big" in one picture.

**A23 · 49.10-51.30 · "disappears that fast, we have to go back to"** Screen: the same building in 2021, a crane lifting the roof sign
away. Why: the change shown with both real pictures of one place, the thing that changed in action. Build: `Foot`. Sound: M the bed
rings out into its tail.

**A24 · 51.30-52.60 · (silence)** Screen: black. Why: a designed stop before the flashback, the one in this video; the viewer leans
in. Never digital silence: the tail and a low note ring under it. Sound: E `black_cut` on the cut to black.

**A25 · 52.60-54.00 · "1996."** Screen: the founders' own 1996 home video (4:3, full height with its own side bars, never stretched),
"1996" landing in display size on its word. Why: the date said into the black lands on the era's own picture; A1's typing isn't used
twice in a minute. Build: `Foot` + kit3 `Headline` (display); the year shown once, so the captions hide it there. Sound: E
`number_land`; M bed 2 enters on its downbeat: calm, a new colour for the founding years.

**A26 · 54.00-57.10 · "Two engineers in a basement workshop in Lahti"** Screen: the same home video: two young engineers soldering at
a bench, one laughing into the camera. Why: the story's people in their own footage, before they are named. Build: `Foot`.

**A27 · 57.10-60.00 · "wanted a pager that could answer back."** Screen: the real 1996 prototype pager (a museum photo, cut out) lands
whole and centred on the bench footage dimmed, on one floor with its shadow, captioned "Norvane's first prototype, 1996". Why: the
thing the story starts from, named and shown; the prototype ends on a finished sentence. Build: `Stage` + kit3 `Cutout`. Sound: E
`pop` as it lands; M bed 2's tail, the mix fading with the picture.

*A, measured as a whole: 30 pictures in 60 s; pages 8% of the time (A4, A16); 14 effects plus the typed keys, none two of a kind
within 1.5 s; one 3D piece, one stamp, one designed stop, one statement drop; every person named shown on their name; the promise said
and shown at 0:38.*

### Example B: "how a city's tallest tower was built" (a technical explainer)

*The promise in the notes: how they built it, from the hole in the ground to the last bolt. The Calder Spire in Port Calder; Ravi
Okonkwo, its project director. One bed at ~96 bpm with a slow build (a low pulse, strings, then the full beat), placed so its biggest
entrance lands on the promise, not on the hook. 28 shots in 60 s: slower than A by design.*

**B1 · 0.00-1.70 · "On a windy day,"** Screen: the construction firm's own 4K drone film circling the Spire's needle in fast-moving
clouds, lit by low sun. Why: frame 0 is the subject, big, lit and moving, and the wind of the words is in the picture. Build: `Foot`
(push 1.00-1.03). Sound: the footage's own wind, low under the voice; M the bed's low pulse.

**B2 · 1.70-3.00 · "the top of the Calder Spire"** Screen: the whole tower over the harbour city (wide drone); the chip "Calder Spire
· Port Calder" lands on it on "Calder". Why: a thing the viewer can't name gets its name on its first naming, on the thing. Build:
kit3 `TagShot`. Sound: E `pop` on the chip.

**B3 · 3.00-5.25 · "moves more than a meter. (Nobody)"** Screen: the engineers' storm footage, the needle through a fixed long lens
drifting against the frame's edge; on "meter" the stamp "MORE THAN 1 METER" lands and stands 1.3 s. Why: a number said as a statement
is stamped; it lands near the line's end, so its reading time wins and the next picture starts on "up there", not on "Nobody". Build:
kit3 `StampShot`. Sound: E `stamp` on the landing frame.

**B4 · 5.25-6.50 · "up there feels it."** Screen: visitors on the observation deck sipping coffee at the glass, the city far below.
Why: the calm the words promise, in people. Build: `Foot`. Sound: none.

**B5 · 6.50-8.00 · "That's because of a steel ball"** Screen: the construction firm's press photo of the damper, a steel ball in its
chamber with a worker in orange at its foot; it opens on the whole photo and moves once onto the ball, centred, within 1.3x its
pixels. Why: the thing named, whole first, then the move to it; never opening on a crop. Build: kit3 `Still` (`from` the whole,
`region` the ball, the box from `tools/motion/automark.py`). Sound: none (no whoosh on a glide inside one picture).

**B6 · 8.00-9.30 · "as big as a bus,"** Screen: news footage of the ball's night delivery on a flatbed through the streets, a city bus
passing beside it. Why: a size comparison in real life beats a drawn one: the bus is there. Build: `Foot`. Sound: the truck's own low
rumble under the voice.

**B7 · 9.30-10.60 · "hanging near the top."** Screen: the architect's real section drawing of the whole tower; it stands still, the
damper's chamber near the top is exposed with the rest dimmed, and the picture zooms quickly (0.45 s) onto it. Why: where the ball
hangs is a detail people would miss, so it gets the mark; it is small, so it is zoomed into from the frozen whole. Build: kit3 `Still`
`marks` (spot look, `zoom`; the box measured by `automark.py` and drawn on the file before use). Sound: E `marker` on the light.

**B8 · 10.60-12.40 · "It's called a tuned mass damper."** Screen: the chamber's own camera in a storm (posted by the tower's
operator), the ball swinging slowly; "Tuned mass damper" lands as a chip on the ball on "tuned". Why: a term most people don't know is
written as it is said and shown at work; the next line gives its plain meaning. Build: `TagShot`. Sound: E `pop`.

**B9 · 12.40-15.40 · "When the wind pushes the tower one way, the ball swings the other."** Screen: the explanation built on the real
drawing: the drawing as the board; the tower's own outline, cut from the drawing, leans right on "one way" and the ball's cut-out
swings left on "the other", one eased move each, nothing else moving. Why: an explaining line gets an animation made of the real
material, one idea, centred; no arrows and no drawn tower. Build: kit3 `Stage` (`img` the drawing) + two `Cutout` layers on
`EASE.move`, each under one transform. Sound: none: a slow lean has no sound to name, and the voice carries it.

**B10 · 15.40-17.90 · "The Spire is six hundred and twelve meters tall,"** Screen: the tower's photo whole and tall in its frame
beside 612 rolling on "six hundred", "meters tall / Calder Spire, base to tip". Why: the number beside its thing, with unit and
subject. Build: kit3 `NumberBeside` (`picture` the photo). Sound: E `count_up` under the roll, cut to it; E `number_land` on its
landing.

**B11 · 17.90-20.30 · "almost twice the height of anything else in the city."** Screen: the city's four tallest at true scale as real
cut-outs from one skyline photo, on one floor, names under them; on "twice" the Spire's name lights, the other three dim. Why: a
comparison of real sizes at true scale, fitted, nothing overlapping. Build: kit3 `Row` (`k` = the real heights, `litAt`, `dimAt`) on a
`Stage`. Sound: E `chapter_card` on the row's slide; E `marker` on the light.

**B12 · 20.30-21.55 · "It took nine years,"** Screen: the construction firm's own nine-year time-lapse from one fixed camera, the
tower rising floor by floor at its own speed; the stamp "9 YEARS" lands on "nine" and stands 1.2 s to the cut. Why: nine years seen
passing, the number stamped as a statement. Build: `StampShot` on the time-lapse (never slowed). Sound: E `stamp`.

**B13 · 21.55-22.70 · "eleven thousand workers"** Screen: the dawn shift change, hundreds of hard hats streaming through the site
gate. Why: a number in a list shown as what it counts; the picture carries it, no second stamp. Build: `Foot`. Sound: none.

**B14 · 22.70-24.30 · "and four billion dollars."** Screen: the city council's approval document, captured at phone width; it stops
and "$4.1 billion" is exposed on "four billion". Why: the sum on its receipt. Build: kit3 `Page`. Sound: E `marker`.

**B15 · 24.30-26.20 · "And for a while it looked like it would never get finished."** Screen: 2017 news footage: the tower a concrete
stump a third of its height, the cranes still in the fog. Why: the trouble's picture: a site that should be loud, standing still.
Build: `Foot`. Sound: M the drums fall away to the bed's pad on the downbeat nearest "never".

**B16 · 26.20-28.00 · "In year three, the city's own engineers said"** Screen: the 2017 press conference, the engineers at a podium
before a settlement chart (muted under the narration). Build: `Foot`. Sound: none.

**B17 · 28.00-29.70 · "the ground under it was sinking."** Screen: news footage at the tower's base: a surveyor at a level, a crack
running across the plaza's paving, the camera following it. Why: the action named, on the ground itself. Build: `Foot`. Sound: E
`bass_drop` on "sinking", the opening's statement drop, heavy in the quiet pad.

**B18 · 29.70-31.60 · "The man in charge of the build put it like this:"** Screen: Okonkwo on site in a hard hat, pointing into the
pit (the construction firm's own documentary); the chip "Ravi Okonkwo · project director" lands on him. Why: the speaker named and
shown before the quote plays; the line teases the quote and never says it. Build: `TagShot`. Sound: E `pop`.

**B19 · 31.60-35.10 · HOLD: the director's own words** Screen: the documentary interview, face and mouth: "Ravi Okonkwo: Every week we
were pouring concrete into a hole that was getting deeper." above the film's own lower third. Build: HOLD beat, `hold_insert.py`,
`Foot` at 1.0 in its own sound. Sound: the director's voice; the bed ~32 dB under it.

**B20 · 35.10-37.30 · "So in this video I'm going through how they built it,"** Screen: the construction firm's photo of six workers
on a beam at the top, the city far below, with depth: the workers hold their place as the city turns slowly behind them. Why: "how
they built it" made present by the people who did; a photo with a clear subject before a deep scene is this opening's one place for
3D. Build: kit3d `Parallax25D` (its layers from `tools/motion/kit3d_assets.py`: depth, matte, the background filled from its own
pixels, no generated pixel). Sound: M **the bed's full beat enters** on "So": its biggest section, kept for the promise.

**B21 · 37.30-39.30 · "from the hole in the ground"** Screen: 2015 excavation footage, a pit the size of a stadium, diggers, pumps
throwing water. Build: `Foot`.

**B22 · 39.30-40.70 · "to the last bolt,"** Screen: the construction firm's film of the topping-out, a gloved hand tightening the
final bolt at the tip, the crew cheering behind. Build: `Foot`.

**B23 · 40.70-43.60 · "and the three times it almost stopped."** Screen: three real photos (the sinking base, a fallen crane across a
street, the empty site in 2020) arrive in ONE move as a centred row of framed pictures with their years under them, over B22's footage
defocused. Why: "three times" made countable and real; the words don't name them yet, so they arrive together and nothing lights.
Build: kit3 `Row` of `PhotoFrame`s on a `Stage`. Sound: E `chapter_card` on the one move.

**B24 · 43.60-46.40 · "And it starts with a problem nobody had solved before:"** Screen: 2014 test drilling, a core pulled from the
ground and wet grey sand sliding out of the tube (the survey firm's own video). Build: `Foot`. Sound: none; M the beat.

**B25 · 46.40-49.40 · "putting six hundred meters of tower on wet sand."** Screen: the line acted out on real material: the tower's
own cut-out lowers from the top of the frame onto the photo of the wet core and lands on "wet sand" with the video's one shake. Why: a
line that is an image is acted out on its picture, the real things landing with weight. Build: `Stage` (`img` the core photo) +
`Cutout` on one transform + the house `useShake` (once a video). Sound: E `cinematic_hit` on the landing.

**B26 · 49.40-52.60 · "In 2014, Port Calder was a flat harbour town."** Screen: 2014 footage of a ferry passing the low harbour town,
warehouses and fishing boats; the chip "Port Calder, 2014" top right. Why: the place before, in motion. Build: `TagShot`. Sound: E
`pop`.

**B27 · 52.60-55.80 · "The tallest thing on its skyline was a grain silo."** Screen: the 2014 skyline photo from the harbour wall,
whole; it stands still, the silo (small, in the right third) is exposed and zoomed into in 0.45 s. Why: the before's tallest thing,
found at a glance on a phone. Build: kit3 `Still` `marks` (spot look, `zoom`). Sound: E `marker`.

**B28 · 55.80-60.00 · "Ten years later, this was standing next to it."** Screen: the 2014 and 2024 photos from the same spot, whole,
side by side, labelled with their years; on "this" the Spire's own cut-out lifts out of the 2024 photo, flies across and lands in the
2014 one beside the silo, exactly where it stands today. Why: a change between two pictures shown with both real pictures and the real
thing travelling; "this" points at the screen because the screen shows it. Build: two `PhotoFrame`s on one board under one camera, the
cut-out on its own transform (nothing twitches). Sound: E `whoosh_fast` on the flight (a real flight across the screen); E
`reveal_boom` on the landing; M the bed's tail, fading with the picture.

*B, measured as a whole: 28 shots in 60 s; one page (3% of the time); 18 effects, at most three markers in any 5 s; one 3D piece, two
stamps on two statement numbers, one acted-out metaphor, one shake, one statement drop; the speaker named and shown before the quote;
the promise said at 0:35 and its road shown in three real pictures.*

### What the two share, and what they don't

They share no device on purpose: a typed date, a burst, a share as a row of products, a boxed number in 3D, a broadcast as a receipt,
a timeline, a black stop in A; a stamp that delays the next cut, a section drawing lit and animated, true-scale cut-outs, a
time-lapse, a depth photo, an acted-out landing, a before-and-after carried across in B. What they share is the level: the first frame
has a subject; every shot starts on its word and shows that word's thing in action; every name has a face or a chip; the speaker says
their own words; every claim has its receipt and every receipt is lit only where it is the point; numbers sit on their things; built
graphics are made of real material in one look; every action is heard and nothing else is; the music's turns are the story's turns;
the promise is said and shown before 0:40; the minute ends on a finished sentence.

---

## 3. What makes a finished long video hit

- **The title's promise is the spine.** Before the outline the promise is written in one line ("how the phone in every pocket went to
  nothing, year by year"). It gets most of the minutes; what led up to it is a 30-60 s recap; the video confirms the promise in its
  first 30 s and shows its road by ~40 s. Every point is asked "how does this serve the promise?" and goes when it doesn't. A video
  that spent its first four minutes on what came before the promised span, then rushed the span itself, lost its viewer before the
  story began: it scratched the surface where the title promised depth. The promised span is researched exhaustively, every item with
  its story and an honest depth mark, never called complete (`tools/script/research_pack.py`).
- **The opening does four jobs, in its own way each time:** it puts the viewer in the world now, shows what is at stake with real
  numbers, hints at the trouble with real receipts, then turns into the story. The retention curve shows why: the big exit is the end
  of the intro, and after it a good video loses only a few points a minute.
- **The story is told in the order a viewer would ask it**, one point a line, every turn following the line before, each line making
  sense alone; a name or term most people won't know is explained in plain words and shown; known things said plainly, never announced
  as news; the creator's own opinions (from the interview after the script) blended in, never invented: they are the measured lever
  that makes a script read human (`standard/SCRIPTS_AND_PACKAGING.md`).
- **Chapters are the story's turns.** Each opens on its most engaging real moment (a rescue at its tensest, never a still of the
  aftermath); a documentary marks its turns with a chapter card or a typed year (`chapter_card`, the keyboard) and a new bed on its
  downbeat; an argument video turns in spoken lines, with no cards. The description lists chapters from 0:00, at least three, each 10
  s or longer.
- **Length follows the story:** never padded, never cut to fit, no ceiling; a long video is at least 8:00, measured on the script
  before the voice and reached from the research (mid-roll ads need 8:00). At a calm narrator's pace (~3.8-3.9 words a second;
  the creator's own in `config/tts.toml` `words_per_second`) 8:00 is about 1,870 words.
- **The middle holds the opening's level.** The passed prototype is the reference: every section is built against its stills side by
  side, and what falls short is rebuilt, not patched. It is a level, not a template: the numbers get the thing they count or their
  receipt, varied, never the same card twice close together; no device spreads across the film; footage never repeats inside it. A
  version 1 should already be the finished video: pictures on their words and the voice's pauses are craft and checkable, so they
  never reach the creator wrong; taste (a song, a look) is the creator's to judge.
- **The end:** the subscribe ask at a real break, its card popping on the ask's own first word; the video ends on its strongest fact,
  then the like and comment sign-off with the house SignOff on screen (LIKE pressed on "like", the comment card on "comments"; gate
  B26 OUTRO), then a fade to black and silence.
- **What sank videos below the bar:** one source frozen for most of the length (13.9 cuts a minute, 51% of shots 4 s or more); a
  promised span skimmed; text cards and number cards where the thing existed as a picture; graphics drawn from shapes; zooms into
  nothing and shots opening on crops; one effect on every number until the ears hurt; clips cut half a second long; marks drifting on
  moving pictures; a template look repeated across a film. Each is in `cases/PICTURE.md` and `cases/COHERENCE.md` with the line it
  drew, and each has its check in the gate.
- **Notes are classes.** A note on one shot is a sample of what to look for everywhere: every instance in the film is found and fixed,
  each fix as a sample where it is a judgement call. A film whose every note was fixed across its class passed in one round.

---

## 4. The creator's own bar videos

When the creator signs a long video off as their new standard, it is added here: its title, where its export, code, cue sheet and
notes are, what it does at that level (the numbers of §1 measured on it with `tools/qa/measure_edit.py`), and the creator's words on
it as a plain line. The newest one is studied before every long video, beside this file.

(none yet)
