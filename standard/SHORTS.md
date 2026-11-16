# Shorts: the standard

*Part of `STANDARD.md`. Re-read before every Short. The bar in words, with worked example Shorts shot by shot: `standard/BAR_SHORTS.md`.
The Shorts chat's rules: `rules/SHORTS.md` and `rules/SHARED.md` (where a rule and this file disagree, the rule wins and this file is
rewritten to it). The research behind it: `standard/research/SHORTS_CRAFT.md` and `standard/research/SHORTS_EDITING.md`. The lines the
creator's verdicts drew: `cases/`.*

**A level, never a template.** The bar is a quality, never a set of moves. A second Short can look entirely different, with entirely
different elements, and still be at the same level: one Short opens on a company's wordmark alone on a plain ground with cut-outs
rising under it, the next on a moving subject in its own footage with the camera following it. "One thing centred on a clean ground,
the first name acted out, no captions under it" was one Short's answer to its words, not a rule for every Short. Copying a worked
example's devices (its opening, its props, its layout) is the template mistake; every Short answers its own words.

## The level, on every Short
- **Shown, never read: text is never a shot's hero.** No page, post, headline, email, notice, statement or card of words as the picture,
  and no words lit as the act. Every line gets footage, frames or the chat's own animation that acts it out, and the captions carry the
  words: viewers of a Short scroll past text and stay for pictures. Text that merely sits inside a frame or a clip (a sign in the
  street, the label on a box, a number on a price tag that is part of the act) is fine: it is not the hero of the image. The shot plan's
  picture column names footage, a frame or an animation on every row, and `PIPE tools/motion/short_visual_check.py
  tools/motion/src/<video>/<Short>.tsx` refuses a Short whose code draws a page card, uses a page capture as a picture or draws a credit,
  before the gate.
- **No credits on screen.** No credit label on any picture, ground or card: a credit pulls the eye off the story the viewer should be
  hooked on. A licence's attribution goes in the description lines of `videos/<video>/post.md`.
- **Everything has a reason**, written in the shot plan before the build: every cut, zoom, pan, asset, animation and sound. An element
  with no reason is cut.
- **The hero dead centre**: on a pan's last frame and on every frame of a hold. **A pan only with a job** (the bar, below).
- **The words acted out with built graphics, never a zoom or a highlight as the act.** A verb in the line is done on screen: "buy" is a
  cursor gliding to a real Buy button that lights on hover, presses and ripples, with the click on the press frame; "couldn't return
  it" is the Return button greying out as a padlock slams onto it; "no charger in the box" is the real object spinning in and
  shattering on "no". A quick zoom-in with a click sound is the cheap version of an act and below the bar; a word crossed out is the
  weak version of "no".
- **No highlights as the act.** No page is the picture, so no words get lit. Light may point at a thing inside a real picture as part of
  an act-out (the rest dimmed, kit3's spot look, `standard/KIT3.md`; the light closing on the one person the line is about while the
  others go grey), never as the whole act of a verb. Nothing busy behind a text.
- **Every sound lands on the thing it shows happening**, on the frame it happens.
- **The voice:** a take that sounds off is replaced whole (a new take of the whole read, never processed); the creator picks from
  samples mixed exactly as the final (`standard/SOUND_AND_VOICE.md`).
- **No effect the viewer can't read yet, nothing washed.** An effect is read from what has been said so far: a logo fading out of a pale
  "dust cloud" (a blurred, whitened copy of the shot before) twelve seconds before dust is ever mentioned reads as a render bug and a washed
  picture. A logo for a said name lands clean, whole and dead centre on a dimmed real ground, and owns the caption line.
- **No pause between sentences either.** Every gap ~0.07 s, sentence ends included: `inner_gaps.py --ends --target 0.07 --over 0.12
  --quiet -45` in the chain, measured the gate's way (`inner_gaps.py --ends`, A3), never off a raw level: at -30 dB a word's own voiced
  end (a creak down to -40 dB) reads as a pause, and muting it loses the word's tail (A13). A pause is cut only by the measured tool.
- **The gate passes before every render** (`PIPE tools/pipeline/pipe.py <video> gate`; `render` refuses code the gate hasn't passed).
- **Full effort, one Short at a time, none rushed:** the script gate, a shot plan with every reason, research where it helps, proof
  stills, framing sheets, the gate, the render, then the creator's rounds.

## The bar

- **Frame 0 is the package.** `flash_open` plays alone at frame 0 (a 0.25-s flash, `FlashIn` in the Shorts kits; no slam or metal
  hit layered on it) over a picture that already tells the story without being read: a company's wordmark alone on a plain dark ground,
  three lawyers' cut-out rising from the bottom on "lawyers"; a service's logo flickering like a failing bulb while the line says it
  nearly died. The first word is on frame 0. **Something to look at:** a subject the eye lands on at once, big enough, lit and moving,
  never an empty road, sky or vista, even when it is the exact picture for the words (viewers scroll past a frame with nothing to look
  at). An empty exact picture gives way to its own busiest moment or another real picture of the same thing.
- **The hook opens a question the viewer wants answered:** what viewers hope for or fear, put on the table, as a question or as a tease
  that holds back the payoff ("Unless the maker fixes this, the next model won't sell"), edging them to the last second; the end
  answers it. A known fact as the opener ("it comes out in March") gives no reason to stay. It names something people know and
  triggers them, and never answers itself; a casual viewer gets the background within seconds; the payoff waits for the end. The
  shape: "This kettle is in a million kitchens, and its maker is telling everyone to unplug it tonight."
- **The words:** one point per line, never restated; no question the narrator answers himself; everything by its name (the product's
  name, never "the device"); every number says what it counts; every person named with their job; no time words that date the Short
  ("just", "this week", "recently"). The script craft: `standard/SCRIPTS_AND_PACKAGING.md`.
- **A new picture lands on the word that names it, every ~1.4-1.7 s** (the signed-off Shorts: a shot every 1.45-1.6 s on average, the
  median 1.34-1.5 s). No shot held past ~2.2 s without a second picture or a big change inside it; no stretch over 2.6 s without a
  change (`qa_holds.py`); no slot so short it reads as a flash (none under 0.25 s; the shortest at the bar ~0.6 s); 3-4 different
  matching pictures per fact, none repeated inside a fact; a punch-in never counts as a cut. A text of ours a viewer must read (a number
  landing, a stamp) stands its reading time before any cut: 1.2 s, +0.03 s a character past 10 (gate B24).
- **Real things are the pictures, shown, never read:** footage and frames of the thing itself in its best source (1080p and up, 4K
  where it exists, the original resolution, never an AI-upscaled copy), photos of the people (official portraits, Wikimedia Commons),
  the subject's own logo, art and footage (the primary source's own material: the maker's official videos, press kit, site), people's
  own recordings of the moment, and the chat's own graphics that act the line out (a real plug going into a real socket and the screen
  waking on "plugged in"; three objects landing in three slots on their three words; a dot lighting on every face of a crowd on "every
  one of them"; a padlock shutting on "locked"). A real object from outside the niche is a fine prop when it acts the line (a server
  rack's lights dying on "the servers buckled", a kitchen timer ringing on "time ran out", an envelope sealed in wax on "a letter"). Outlets' pages are where facts come
  from, never the picture: a quote is said by the voice and acted out. A real person's words play as their own clip (cut like the rest,
  below). No stock filler, no AI images or AI footage, no material someone leaked or stole.
- **Nothing stands still:** every shot moves visibly at feed size: a still or a card pushes ~13% over ~2 s (a 5% push read as frozen);
  a hold on a subject that fits gets a slight push of 2-4% a second; props keep moving after they land (`drift`: 10% a second from 0.3 s
  after landing, at most +18%: props that landed and then sat still read as a frozen picture after 0.8-1.2 s); no picture still for
  0.8 s.
- **One clean, centred thing per screen, filling 9:16:** no blurred bars, no big empty areas; the subject centred vertically too; a logo
  centred on its visual weight, never its box (a lettering with a thin left arm sits right of its box centre: measure it, gate B21).
  **The camera follows the hero:** a subject that moves is kept in the middle by a window that moves with it the whole slot (`place()`'s
  `path` [[t, fx, fy, s?], ...], placed key by key on `frame_review_at.py <id> --cols 6`); one framing that is right at one moment is
  not enough. **A pan only when it has a job:** (a) from one thing the words need to the next when both can't fit in 9:16 (two people:
  start on the one the words are on, pan to the other; a mark on a product's name, then the product itself), (b) along a subject that
  moves. One subject that fits stays put, a slight push at most; panning across a whole picture for its own sake is a fault (no gate
  check can know a pan's reason, so gate B11 is off: each shot's move and its reason are written in the shot plan). Whoever says a
  line is in the middle while saying it; never the gap between two people; a person whole, head in, never a window of floor; a shot
  where nothing can be made out (a dark corridor, a blur) is replaced, never kept for its words. **Nothing important small:** a
  cut-out ~1.2x the frame's width with its cut edge off the bottom, a print, a product or a card full bleed (or a `Card9` at w 1000+),
  never a small picture on a plain ground where most of the screen shows nothing (gate B4 EMPTY). A ground behind a piece is
  real footage, dimmed but bright enough to count as a picture (opacity x brightness 0.28+), never the piece's own picture blurred.
  **Someone's own clip is cut like the rest:** its pauses closed to ~0.07 s at the speech model's word edges (10-ms crossfades, false
  starts cut), and a new crisp picture of what they say every 2-3 s over their words (their face where it helps, the real thing they
  talk about in its best source); never a soft slide or an empty frame held, and no moment without talking around it (the narration
  runs straight into their first word and out of their last). **No twitch:** a window that moves over a clip whose own camera moves
  steps with the clip's frames (`Pic` `lock`): a 30-fps clip in the 60-fps Short twitches back and forth under a smooth pan.
  **Nothing shakes:** a card, a board or a row that moves or zooms moves as ONE picture under one transform, laid out in constant px;
  per-frame fractional left/top/width makes each edge snap to the pixel on its own frame and the card jitters. **Zones:** nothing
  above y 260 (the phone's status bar and the app's top bar cover it); the upper asset at y 290-880; captions dead centre at y ~960;
  numbers and icons at y 1080-1410; everything inside x 180-900; a source under 1080p plays as a 16:9 `Card9` at or under its own size
  in the upper zone over a real ground, never blown up to fill (a 405-px slice blown up 2.7x is mush).
- **Captions:** full text, 1:1 with the voice, one size, 1-2 words per chunk, no punctuation except "?", one key phrase per beat in the
  look's caption key colour (`tools/motion/src/look.json`; `*like this*` in the script); a name and its number always one
  caption; no label, stamp or number card repeating the line. **The planner** (`tools/dj/ass.py` `plan()`, called by
  `tools/motion/finish_short.py`): it chooses the chunks that cost least (1 a chunk, +0.8 for ending a chunk on a weak word or a bare
  number: never "ONLY 30 | MINUTES"), keeps a `*key*` phrase whole while it fits the width (62% of the frame), pairs a name with its number
  (`[captions] pair_with_number` in the config: "Model 3" never "MODEL | 3"), never joins words across a beat, a sentence end or a gap
  over 0.3 s (a word a stamp took out leaves a gap, and a chunk joined over it would run under the stamp), holds each caption until the
  next when the gap is under 0.5 s (no flicker), never shows two texts at once, and drops every chunk mostly inside a stretch a graphic
  says (the quiet stretches). Whisper's words need reading before the burn: a name spelled two ways in two places, "thirty" next to
  "30", one number split over two captions ("48" and ",000"), "7" for "seven percent", a product name broken over three captions; each
  fixed in `videos/<video>/captions_fix.json` (`into` a new word, `into: []` drops one): numbers as digits, one number in one caption,
  a name whole. Read the burned `.ass` text (`MEDIA/videos/<video>/build/captions/<name>.ass`), never `chunks.srt`. **A name is the
  script's spelling:** `finish_short.py` puts every `tools/sound/names.json` name back as the script writes it (its log: "the name as
  written"); an A5 allow for a respelled name covers the voice, never the captions.
- **Text shows once; the caption line belongs to what replaces the captions:** a logo, stamp, count or title that says the words being
  said sits dead centre on the caption line (y ~960) and replaces those captions while it shows (`data-gate="stamp"` on it, or `own` on a
  `Pic` or `Card9`; `finish_short.py` clears every caption under it, the small words around it too, read from the gate's probe;
  `videos/<video>/captions_hide.json` for anything else); a logo shows on the line only while its name is said; a clip's own speech is
  captioned once, by the house captions (`videos/<video>/captions_bites.json`). A stamp of words is rare: only a number said as a
  statement, never a slogan or a label for what the picture already shows.
- **The captions' two colours only:** every designed colour in a Short (stamps, counts, crosses, glows, lines, rings) is the look's plain
  caption colour or its caption key colour, whatever the long videos' accent: a theme colour plus one odd accent word looks off.
- **The voice:** the Shorts voice (`[tts.short]` in the config: stability 0.5, the "[American accent]" tag and no other) at the middle
  speed (every line gets half the speed-up toward the hook rate of 5.65 syllables a second, `tempo_share`), the hook at the same speed
  as the rest, about 200 words a minute, no pause between words (every gap, breaths included, to ~0.07 s by
  `tools/sound/shorts_tighten.py`, measured under -35 dB, never as silence only: faint breaths at -35 to -45 dB pass a silence check
  and leave 0.5-s pauses), American from the first word, never a tired or whispered opening (A12). A sentence that sounds unfinished
  is reworded and voiced in a take that ends it in pitch, never padded with silence.
- **Sound:** every Short its own music (the creator's own files or music made in code, `standard/MUSIC.md`; never one house song for all
  Shorts) ~17-18 dB under the voice in speech (at ~13-14 dB the music and effects drown the voice); effects at most -7 LU under the
  voice. The music cuts dead on the story's turn (and under a real person's own words) and comes back on a downbeat at the next cut;
  a track's fuller half enters on a bar where the story opens up. Every effect is the house pick for its job (`pal("<job>")` in the cue
  sheet, from `assets/house_sfx.zip`'s manifest: pop, mark, click, stamp, money, whoosh...), on its action's frame, never before its
  picture; items that appear one by one each get the same sound (five pops for five days); a light that points at a thing gets the
  marker as it starts; one bass drop per video, on the payoff's key word; no sound on a plain cut to footage or for an event the viewer
  can't see; no sound outlives its picture; a new kind of sound reaches the creator first as a sample (`tools/sound/sfx_demo.py`,
  `sfx_verdict.py`). -14 LUFS. The voice reaches -14 through chain D, never one gain and a fast limiter (`EDIT tools/sound/voice_level.py
  --chain mb --lufs -14` on the untouched narration); the cue sheet's mix block: `under=10` on each music cue, `GAP_MIN = 17.0`,
  `DUCK_DB, CARVE_DB, SIDE_DUCK_DB = 6.0, 5.0, 2.0`, `MUSIC_TAME = (3.0, 8.0)`, `LEVEL_BEDS = 0.6`, `VOICE_COMP = None`,
  `MIX_LUFS = -14.0`, `MIX_CEIL = -1.2`, the designed stops in `SILENCES`.
- **The end:** it stops ~0.4 s after the last word, no end card; length follows the story (30-60 s), under 60 s while any clip could
  draw a claim. A Short ends on its payoff (`CONFIG: video.short_loop=false` in the script); the config's default (`short_loop = true`)
  is for a Short written as a loop, its last sentence running into its first.

## The method

1. **Choose, one at a time.** The creator's intuition picks; no idea research unless they ask. A Short stands alone for someone who never
   saw the long video. Besides a long video's Short-worthy moments, its whole topic can be one Short: told fresh for the niche's
   viewers, its most interesting points, no technicalities, never a cut-down of the long video. Picking the topic: below.
2. **Folder and facts:** `videos/<video>/script.md` with "short" in the folder name (`kind = "short"` in its `video.toml`; the pipeline
   treats it as a Short); the facts on top with source, date and grade; what the creator sends is the source; material someone leaked
   is named, never shown. Check whether the story is already told on YouTube: a Short needs its untold part, or it is dropped.
3. **Script** (`standard/SCRIPTS_AND_PACKAGING.md`): `[Sxx] VOICE:` beats with one `*key phrase*` each, `CONFIG:` lines as needed
   (`video.short_loop=false`, `tts.fresh_at` for a beat voiced as a fresh request); `PIPE tools/script/script_lint.py
   videos/<video>/script.md` and a fresh-listener agent; the creator never needs to read it.
4. **Voice:** `bash tools/sound/short_chain.sh <video> <src folder>`: the take (`dj tts` with `[tts.short]`), captions, the voice guard
   (a flagged section is voiced again), the raw take kept as `narration_prechain.wav` (A1 compares against it), pausefix,
   `shorts_tighten.py` (every gap to ~0.07 s), captions again, `sync_words.py` (`tools/motion/src/<src>/words.json`, `beats.json`),
   the sound gate A1-A13. Screen every section: `PIPE tools/voice/accent_take.py <narration.wav> --words <words.json> --beats
   <beats.json> --voice short` (its `accent_by_beat`; the bar is 0.15, item 7 below), `rhotic.py`, `ACCENT tools/voice/accent_id.py`;
   a British stretch is voiced again as a whole section (`tools/voice/section_takes.py`); where the story's words pull the accent,
   casual wording and `tts.fresh_at`. The voice is final before any picture work: every cut is anchored to a word.
5. **Words and timing:** `words.json` and `beats.json` in `tools/motion/src/<video>/`, a `timing.ts` beside the composition so every cue
   is a word (`w('S04', 'left')`: the start of that word in that beat, never a typed second; a phrase no longer in the script fails
   the render loudly instead of drifting); `EDIT tools/voice/voice_check.py <narration.wav> <words.json>`.
6. **The shot plan** (`videos/<video>/SHOTPLAN.md`), written before the build, one row per shot: the words (with their times), the
   picture, the move, the sound, and why each is so. Every row names footage, a frame or an animation; a row whose picture would be a
   page gets an act-out instead. The worked examples in `standard/BAR_SHORTS.md` show the depth a row needs.
7. **Pictures:** for every named thing, the most specific picture out of all the options: `kb/FOOTAGE.md`, `PIPE tools/footage/cands.py
   <out.jpg> <words>`, `scan.py`, `peek.py`; stills by image search first (official images, the maker's press kit, wikis) before frames of
   videos; three or more wordings before calling a picture unfindable, then ask the creator. Footage spans sit inside ONE shot of their
   source (its cuts at scene 0.08, 0.1 s inside them). Log every photo and logo with its source and licence
   (`PUBLIC/<video>/SOURCES.tsv`); the attributions a licence needs go in `post.md`.
8. **Build it yourself** (agents only for mechanical jobs): `tools/motion/src/<video>/<Short>.tsx`, registered as `gated(<Short>)` in
   `tools/motion/src/Root.tsx` at 1080x1920, 60 fps, ending 0.4 s after the last word (`frames` in `video.toml`); video only through
   lib's `Clip` (the gate sees only what goes through it). The pieces: the Shorts kits in `tools/motion/src/shorts/` (`kitS.tsx`: `Pic`,
   `Back9`, `Card9`, `Drop`, `Print`, `Box`, `Cash`, `Push`, `Grade`, `drift`; the framing under them: `Cover`, `place()`, `FlashIn`;
   the caption-line pieces `Stamp9`, `Count9`, `Crossed9`, `Logos9`), `tools/motion/src/lib.tsx` (`useT`, `kf`, the easings, `Clip`,
   `Glitch`, `Flash`, `LightBar`), kit3's dims and spot look (`standard/KIT3.md`), designed graphics from kit 2
   (`standard/GRAPHICS_KIT2.md`: built at 1920x1080, so placed inside the zones, one clean thing per screen, a different variant and
   palette from the last two videos). An act-out no kit piece builds is written for this Short in its own folder, at professional
   animation quality with real-looking assets and light (cut-outs of real objects, real textures), never flat shapes.
9. **Framing, every shot** (below, item 19 and the framing sheet): no shot keeps the default window (cx 0.5, cy 0.5, full height).
10. **Proof stills** first (`PIPE tools/pipeline/pipe.py <video> stills --every`, or `QA_COMP=<Id> node tools/motion/stills.mjs <dir>
   0.5 <frames>`): every shot read against its words, at full size where a detail matters.
11. **The gate:** `PIPE tools/pipeline/pipe.py <video> gate` (sound A1-A13, picture B0-B26 on every frame of the composition); every flag
   fixed, or allowed in `videos/<video>/gate_allow.json` with its reason and the frames that disprove it; one full gate with the fixes
   batched, then the one gate the render needs.
12. **Render:** `PIPE tools/pipeline/pipe.py <video> render` (one Remotion job at a time on the PC, through `tools/pipeline/heavy.py`;
   the config's GPU `angle`; concurrency 6); nothing heavy alongside.
13. **Finish:** `PIPE tools/pipeline/pipe.py <video> finish`: the captions burned in (`finish_short.py --picture-only`), the sound
   (`EDIT tools/sound/score.py videos/<video>/score/cues.py <export.mp4> --picture <picture.mp4>`), and the checks that read the real
   picture and sound (below). The cue sheet: music picked for this Short (`EDIT tools/sound/grid.py <track>` for its bars and
   downbeats), the mix block above, designed stops in `SILENCES`, effects by `pal(name)` on the frames of their events.
14. **The watchable copy goes to the creator the minute the finish writes it;** their watch is the fix list. A flag the finish's own
   checks raise is fixed (or disproved by its frames) and the fix goes to them as a sample.
15. **Deliver:** the MP4 in the final message of the turn; once the creator calls it done, one title (the Shorts title research in
   `standard/SCRIPTS_AND_PACKAGING.md`) and the tags as copy blocks; no thumbnail, no phone copy. Before sending, write the verdict you
   expect in `cases/PREDICTIONS.md`; after their answer, score it and put the verdict in its casebook.

## Framing: the sheet, before the render
Every Short gets the framing method, shot by shot. Each 16:9 shot is placed on its whole source frame at the start, middle and end of
its slot (faces by YuNet, people and the thing named by eye), zoomed when the subject is small, a pan (fx/fy to fx1/fy1, or a `path`)
only with its job, letterboxed sources zoomed to fill (a 1920x864 picture inside a 1080 file: push 1.26+ with fy 0.5, or `Card9`
`zoom` 1.25), titles and logos whole or not at all. The sheet: `EDIT tools/motion/frame_review_at.py <id> --cols 6` (every picture
placed with `Cover` at six moments across its slot, the 9:16 window in red, YuNet's faces in green, a 10% grid, the crop the viewer
sees, the words of the slot; `Card9` shows its picture whole, so it never crops), read shot by shot with four questions at each moment:
is the hero in the middle (the one moving, the one speaking; two people talking: start on one, pan to the other)? Is the hero whole
(head in, no window of floor)? Can you make out what happens (a dark or blurred moment is replaced)? Does the important thing fill the
frame (cut-outs, prints, products, cards big)? A moving hero gets a `path` placed key by key on that sheet, then the sheet is run again
to see the window follow. Read the sheet for "does the window follow the subject and fill the frame?", never only for "is the subject
inside the window?". What the sheet finds when framing is guessed: subjects on the window's edge, a face moving out, the gap between
two people, a title cut, letterbox bars, product photos wider than 9:16 (cut them out of their white ground and drop them whole), a
clip fading to black. Two more it doesn't draw, read at full size: **a poster or promo image whose logo is wider than the 9:16 window** goes whole into a
`Card9` (zoom past its dark borders) or gets a window with no logo at all, never half a logo; a cover with its title is a `Box`, whole.
**A face behind something drawn over the upper
zone** (cinematic shots put faces at 20-35% of the height) is fixed by the picture, never by moving the drawn thing: the subject below
it, a picture whose point is lower or has no face, or the face outside the window. A 1920 still is not zoomed past ~2.2x.

## Before it goes to the creator
Every item on every Short. **[before]** items are read before the render (on the composition, proof stills, sheets and the narration);
**[render]** items read the real picture and sound, which only exist after the render: `pipe.py <video> finish` runs 1, 2 and the 2-fps
sheet by itself on every render, `PIPE tools/pipeline/pipe.py <video> qa` adds the word sheet and the delivery checklist, and `bash
tools/motion/short_checks.sh <id> <folder> <export name>` the rest (a minute or two). Nothing catchable before the render waits for it;
a render-time flag is real until its frames disprove it, never waved through by an older rule (a flag of "7 s with no talking and no
change" on someone's own clip is exactly what a viewer sees).

1. **[render]** `EDIT tools/qa/qa_render.py <final.mp4> --format short --words <words.json> --voice <narration.wav>`: no FAIL; a kept
   flag gets `--allow a-b` with the reason written down.
2. **[render]** `PIPE tools/motion/qa_holds.py <final.mp4>`: nothing over 2.6 s without a change (a filter, never the proof: the shot
   plan holds the ~2.2-s rule).
3. **[render]** Every frame by eye: `EDIT tools/qa/word_sheet.py <final.mp4> <words.json> <out>` (a tile every 0.5 s with the word being
   said): frame 0 shows what the first word names; every cut a new matching picture; no flash frame; no clip running into its source's
   next shot.
4. **[render]** Crops on a 2-fps sheet (`ffmpeg -i <short>.mp4 -vf "fps=2,scale=180:320,tile=13x4" -frames:v 1 sheet.jpg`): every
   subject centred, vertically too; logos on their weight.
5. **[render]** `PIPE tools/footage/phone_view.py <final.mp4> <seconds> <out.png>` on frame 1 and on every shot with a logo or a number:
   nothing above y 260, nothing to read under the captions (an internal check; the creator never gets a phone copy).
6. **[before]** Captions against the voice word by word, on the `.ass` text before the burn; no caption for a click the voice didn't
   say; no card or label repeating the line; every name as the script spells it.
7. **[before]** **Every section's accent under 0.15:** `PIPE tools/voice/accent_take.py <narration.wav> --words <words.json> --beats
   <beats.json> --voice short` reads `accent_by_beat`; a section at 0.15 or more sounds British to a listener even when A11 passes it as
   "maybe", and is voiced again whole, never stretched to fit (regenerate, never process; the picture follows the voice's words). The
   bar is read in place, on the narration: a take alone reads higher (a take at 0.185-0.96 alone can read 0.10 in the narration), so
   when no take passes alone, build with the best and read it in place before rewording (rewording a section can make it worse). The
   narration passes `rhotic.py`, `accent_id.py`, `voice_check.py`; `EDIT tools/sound/shorts_tighten.py <video> --dry` lists no gap over
   ~0.1 s (the check's tolerance for the ~0.07 s target).
8. **[render]** `score.py`'s report: voice over music ~17-18 dB in speech; "silences outside the designed ones: []"; every effect audible
   on a phone ("400Hz+ vs rest" between -12 and -3; a hit that is 95% sub vanishes on a phone: use another house fit for its job).
9. **[before]** Every effect the house pick for its job, nameable in three words, on its frame; the flash alone at frame 0; no sound
   outlives its picture.
10. **[render]** The file ends ~0.4 s after the last word; no end card (`pipe.py qa` reads the gap: 0.15-0.8 s passes).
11. **[before]** True and safe: every number matches the voice; nothing leaked; no sexual or gory shot and no violence or weapon aimed
   at someone inside the first 7 s (ad suitability); no word a filter could misread (`tools/sound/censor.py` for a risky word).
12. **[render]** `EDIT tools/qa/measure_edit.py <final.mp4> <out dir>`: the cut rate, motion and loudness measured against the bar's
   numbers in `standard/BAR_SHORTS.md`.
13. **[render]** After the render and the captures: no headless browser left running (they hold memory and slow the next job).
14. **[before]** **Shown, never read:** `short_visual_check.py` clean on the Short's code; every row of the shot plan names footage, a frame
   or an animation; nothing on screen asks to be read but the captions.
15. **[before]** The thing a fact is about is on screen and big enough to read: a detail of a wide frame (an icon, a sign, a small screen)
   that a 9:16 crop cuts off or shrinks is frozen and zoomed onto (a zoom opens on the whole picture and moves to its centred
   subject), or shown big as an inset of the real region over the shot.
16. **[before]** After any change to the pictures, `PIPE tools/pipeline/pipe.py <video> link` before the render (a render dies on a clip
   the public dir lacks).
17. **[before]** Repeats: no line said again word for word, no graphic one to one, no clip or song twice inside the Short, preferably
   not the last video's; older reuse is fine where it shows what's said. `PIPE tools/motion/reuse_check.py <video>` lists what is
   shared, as information.
18. **[before]** **Every picture in its best quality:** the original high-res file over recordings of it; no ground blurred from a low-bitrate
   frame; check a video source's bitrate (`ffprobe -show_entries format=bit_rate`); the clearest picture of a thing is judged by how it
   reads on screen (face-on and big), never by its source's prestige or file size: when the clip the line names shows it clearly,
   freeze that clip and zoom in on its exact last view.
19. **[before]** **The built Short's clip audit:** `PIPE tools/motion/audit_short.py <id>`: 0 OVER before the render. Every footage span
   sits inside ONE shot of its source: `audit_short.py <id> --cuts` lists each play's source cuts (scene > 0.08; 0.25 misses dark cuts
   and lets a 67-ms flash of the next shot through; a cut in a play's first 0.1 s is a sliver of the shot before), then the frames by
   eye (motion, smoke, flashes of light and scrolling graphics fire the scene measure too), and its black (`blackdetect`: a clip fading
   out at its end). No scene over ~2.2 s: a long beat gets a second real picture (the person, the thing, an official image), a card
   ~2-2.5 s at most. Props keep moving after they land (`drift`; cards and logo cards push ~7% a second). A logo is the keyed PNG over
   its own art, never a letterboxed clip of the logo. `pipe.py render`'s frame check needs `frames` in `video.toml` (a built Short ends
   0.4 s after its last word). The word sheet runs on the editing python (cv2).
20. **[render]** One frame from the middle of every shot at 200x356, read by eye (`short_checks.sh`'s 1-fps sheet): the 2-fps sheet's small cells hide a head on the frame's edge.
21. **[render]** **The twitch check:** `EDIT tools/motion/qa_jitter.py <render.mp4> tools/motion/out/auditat_<Comp>.json` (the plays
   list item 19's `audit_short.py` writes) on every built Short: no shot flagged TWITCH (its shift changing sign on 25%+ of the frames). A flagged shot gets `lock` on its `Pic` (the window
   steps with the clip's frames), never a slower pan as the fix.

## Picking a Short's topic
An extensive topic broken down fast, 30-60 s of crucial points only: a why with its causes, a comparison with its numbers, a list, a
story with a turn. One fact, however striking, is a hook, not a Short: stretching it means filler. Check the channel's past Shorts
first (no repeats) and whether the story is already told elsewhere (a Short needs its untold part).

## Read before building one
1. `rules/SHORTS.md` and `rules/SHARED.md`; the Shorts cases in `cases/` (`PICTURE.md`, `COHERENCE.md`, `SOUND.md`, `VOICE.md`,
   `SCRIPT.md`): both sides of the creator's line, passed and flagged.
2. `standard/BAR_SHORTS.md`: the qualities every shot has, the worked examples, what fell below the bar.
3. The newest Short in `videos/` (its `script.md`, `SHOTPLAN.md`, review notes) and its composition in `tools/motion/src/<video>/`: the
   bar in this studio's own code.
4. The Shorts kits (`tools/motion/src/shorts/`), `tools/motion/src/lib.tsx`, `standard/KIT3.md`, `standard/GRAPHICS_KIT2.md`.
5. `standard/SOUND_AND_VOICE.md`, `standard/MUSIC.md`, `tools/sound/palette.json` (the house effects by job, built from
   `assets/house_sfx.zip`'s manifest).
6. `standard/research/SHORTS_CRAFT.md` (§2 hooks, §3 pacing, §4 captions, §7 framing, §11 the practices the evidence supports) and
   `standard/research/SHORTS_EDITING.md` (§0 the build rules, §1 acting out the narration, §2 the camera in a 9:16 reframe).
7. `standard/SCRIPTS_AND_PACKAGING.md` (the Shorts scripts and titles), `standard/SCRIPT_TRAINING.md`, `kb/FOOTAGE.md`.
8. `standard/CHECKLIST.md` and `standard/PIPELINE.md`.
