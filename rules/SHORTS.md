# Rules for Shorts (the Shorts chat)

*The creator's rules for Shorts only; the Shorts chat reads them with `rules/SHARED.md`. The Shorts chat never reads
`rules/LONG_FORM.md`: where Shorts and long videos differ, the rule here holds for Shorts.*

**How these rules change.** They are the starting taste. When the creator gives a note that contradicts a rule, rewrite that rule to
their version in place, without comment (no "was X, now Y", no mention of the old rule). A new note becomes a new rule in the section
it belongs to, with the creator's own words beside it on the line under it (`> creator: "..."`), and takes the next free id of its
file; a note about both kinds of video (the voice, the creator's way of talking) goes into `rules/SHARED.md` instead. When two rules
really clash, the newest one wins and the older one is rewritten to it. Every rule lives in one file only; others point to it and never
restate it.

**Format.** `**SH12 · Title.** What to do. Why.` SH = this file, AL = `rules/SHARED.md`, LF = `rules/LONG_FORM.md`.

## Workflow

**SH1 · One Short at a time; the standard Short is a level, never a template.** What carries over from the standard Short: every
element with a written reason; the hero dead centre and a pan only with a job; the words acted out with built graphics, never a zoom or
a highlight as the act; every sound on the thing it shows happening; a voice take that sounds off replaced whole; the gate passing
before every render. The standard Short's own devices were its answers to its words: the next one finds its own, entirely different
where its words call for it. Process: the script gate, a shot plan with every reason, research where it helps, proof stills, framing
sheets, the gate, none rushed; one Short built and sent before the next build starts; while one is watched, the next one's facts and
script may begin, so the notes reach it before its pictures. Every Short is at least as quick, as dense and as polished as the best
Short the creator signed off, with its own ideas, never a copy of its graphics. Shorts made back to back carry one Short's faults into
the next.

**SH2 · The first Short is reviewed until it is perfect, then it is the Shorts bar.** The Shorts chat builds one Short the normal way,
the creator reviews it to the pixel, every fix a sample, round after round until they call it perfect; that Short becomes the Shorts
bar (`standard/BAR_SHORTS.md`) and the other picks wait until then. Everything after is measured against it.

**SH3 · A news Short is ready within about an hour of its script.** Read `standard/SCRIPT_TRAINING.md` before the first draft; one
builder that checks its own frames; a separate audit round only when the creator asks. Three hours on one Short (an hour of untrained
script versions, 1 h 45 of build iterations, an hour of separate audit and fix rounds) is the failure.

**SH4 · Shorts from a long video: the material sets the number.** When the creator points at a long video, the chat picks what is
Short-worthy: the number comes from the material, never a quota, and each pick is justified by what measurably works in Shorts
(research and our own Shorts' results). A long video can also get one Short on its whole topic: not a cut-down, but the topic told anew
as a Short, with the few points a viewer of the niche cares about most, built for engagement; the mechanics, business and history that
only explain stay out, and every line still comes from the sources. Each Short stands on its own for a viewer who never saw the long
video and leads to it (the creator adds the Related Video link); a second or third angle on the same story is out unless it is new
news. A Short that is just noise on the channel costs it reach.

## Script

**SH5 · For casual viewers, for every viewer.** Never assume the viewer has background knowledge: give mainstream viewers what they
need within a few seconds so they get the Short. Pick the angle that matters to every viewer of the wider category (their wallet, their
everyday), understandable by basically anyone, never too technical. A Short is watched by people who never heard of the niche.

**SH6 · Shorts never stall.** One point per line, never restated ("not just X, every Y" after the point is made is redundant); one
thing after the other, quickly and compressed; stick to the topic. A stall is a swipe.

**SH7 · A Short is an extensive topic broken down fast, never one fact stretched.** An idea needs enough substance for 30-60 s of
crucial points (a why with its causes, a comparison with its numbers, a list); a single fact, however striking, is a hook, not a Short.
Check the channel's past Shorts so the idea isn't a repeat. Stretching one fact means filler.

**SH8 · The hook opens a question the viewer wants answered.** The first line puts what viewers hope for or fear on the table (a
feature, a price, a rule), as an open question or as a tease that holds back the payoff (a stake, a threat, a "might"), and the Short's
end answers it; a known fact as the opener gives no reason to stay. Check every hook: what does a viewer want to find out after this
line, and does the end answer it? A hook without a question loses the swipe.

**SH9 · Edge them to the end.** Every Short holds something the viewer wants until the end; when the topic is something people want to
do, the body piles up what is possible (free, on your phone, in ten minutes) in the present tense and never names the tool, the site or
the steps; the catch comes only in the last lines. What the viewer wants keeps them watching.

**SH10 · A Short cut from a long video keeps its stance.** Its script is tested against the long video's stance before building (and
never advertises someone who leaks or steals material). A Short once sold the very thing its film criticised.

## Voice

**SH11 · The Shorts prefix.** Shorts send only "[American accent]" (`config/tts.toml`'s `[tts.short]` prefix). Shorts keep their fast,
excited delivery.

**SH12 · The voice at the middle speed.** Each line gets half the speed-up it would get (`tempo_share = 0.5`: atempo 1 + (f - 1) / 2,
the rate halfway between the take's own and the target hook rate of 5.65 syllables a second), and the hook gets the same share as every
other line (`hook_like_rest = true`), so the whole Short runs at the middle speed. The full speed-up felt too fast.

**SH13 · No pauses in a Short: ~0.07 s everywhere, sentence ends and bites too.** One flow of voice from the first word to the loop:
every gap between words, sentence ends and commas included, is cut to about 0.07 s before the render, breaths with it
(`tools/sound/shorts_tighten.py`: every cut proved, edges quiet, the removed peak a breath, word fades kept), and the pauses between
sentences by `tools/sound/inner_gaps.py --ends --target 0.07 --over 0.12`, measured the gate's way (A3), never off a raw level, since
at -30 dB a word's own voiced end (a creak down to -40 dB) reads as pause and muting it loses a tail (A13); a pause is cut only by the
measured tool. The check measures gaps under -35 dB, not only silence, because faint breaths (-35 to -45 dB) pass a silence check: a
Short with no silence over 0.18 s still held 0.2-0.55 s gaps. Other people's talk is tightened the same way: a bite's own pauses are
cut to ~0.07 s at the speech model's word edges (never at a loudness dip), the pictures over it are cut to the tightened words, and the
render scan's "no talking" over a bite is a fault, never a pass. A Short talks constantly.

**SH14 · An unfinished-sounding sentence is fixed by its wording, never by a pause.** A sentence that sounds unfinished is reworded
("and a lot of paperwork.") and voiced in a take that ends it in pitch, never padded with 0.35-0.4 s of silence. Pronunciation and pauses are
different problems.

## Sound

**SH15 · Every Short opens on the white flash, with flash_open alone.** The first frame comes in with the white flash-in animation and
the house `flash_open` sound, whatever tool builds it; frame 0 is flash_open only, with no slam or metal hit layered on top. The flash
is the Shorts' signature open.

**SH16 · Sounds on every key moment.** A bass drop plus an instant zoom on a punchline claim, drops on claims and reveals, pops on
things appearing and a fitting effect where the line invites one. A Short without its hits feels flat.

**SH17 · Shorts keep their music level: ~17-18 dB of voice over music.** Shorts stay at ~17-18 dB in speech (UNDER 10, GAP_MIN 19.5,
DUCK 6, CARVE 5, effects 7 dB down) until the creator says otherwise. The creator called that mix right for Shorts.

**SH18 · Risky words: a bass-boost censor, never a beep, or out.** A word the platform may hold against a Short is either left out or
covered: the voice says it, a bass-boost hit replaces the word's span at 6 dB under the voice (`tools/sound/censor.py`'s defaults; or
the word itself bass-boosted and clipped past recognition, `censor.py --distort`, at the voice's loudness, never louder), the caption
masks it (N*KED), and the same word on screen gets a bar; whether to use the word is the chat's call. A beep sounds amateur, and an
uncovered word can limit the Short.

## Music

**SH19 · Every Short gets its own music.** Each Short gets music that fits it, never one house song for all Shorts. One song on every
Short makes them blur together.

## Picture

**SH20 · In a Short, text is never the hero.** No shot's hero is text (no page, post, headline, email, notice, statement or card of
words as the picture, no words lit as the act): the thing named becomes the main visual (a cover popping in over the background clip, a
clip from another source: the niche's own footage is not the only footage allowed), and every line gets frames, clips or our own
animation that acts it out (a phone rising out of its box; a cursor on a Buy button and the product shattering). Text that merely sits
somewhere in a frame or clip is fine (a map, an ad, when it is the point), and on-screen text of ours appears only when it adds what
the voice and captions don't (a quote, a price, a year), never a label, stamp or slogan that repeats the line; the captions carry the
words, ideally the only text on screen; emojis are rare and iPhone-style when used. Measured from the shot plans, pages and cards once
filled 66% of a Short's time (16 of 23 shots), others 58%, 35% and 22%, because Shorts viewers want to see, not read.

**SH21 · Every element of a Short has a written purpose; the words are acted out.** Before a Short is built, each shot gets one line in
its shot plan saying what it shows, why that picture, why that move (or why it holds), why that animation and that sound; a line with
no reason is cut. The words are acted out with designed elements (logos, cut-outs, objects that land on their word), not only footage
and page captures: a verb in the line (buy, sell, lock, delete) is acted out with designed motion (a cursor that moves and clicks, a
button that greys and locks, an object that shatters) with its own sound on the frame it happens, never a quick zoom with a click
sound. Research on short-form editing is encouraged. An element without a reason is noise.

**SH22 · A story Short is a short film.** Every line is acted out on screen as a scene with real photos and cut-outs moving like a
story (a card refused at a till, prints and cash splitting three ways, a calendar torn through six months, an exit sign, the quote
typed on a note with the music stopped, the company's own filing words, a gavel, a sealed envelope), each scene with its own light (a
cold night, warm gold, a red cast), callbacks (the silhouette and the calendar come back), and the QA loop run until no FAIL; never a
slideshow of pages. What made a Short's pictures the bar: a new picture on the word that names it about every 1.7 s; real objects made
into graphics (an old radio cut out of its public-domain photo landing on a real room's shelf, a row of numbered lockers, a wall of
portraits with a dot on every face, the note typed out, a padlock over a shop's front door); held shots that still move (a push the feed
can see); the end on the last word. A slideshow is not a story.

**SH23 · Not a single frame looks messy; one focal thing, readable without pausing.** The background clip shows something you can
actually see (never a cut-off title card behind the captions), the main thing is centred in 9:16, pop-ins sit in the top third over the
clip with the captions running and never pile onto graphics; one focal thing per screen, readable at a glance, never a clogged screen.
The simpler the better, and a frame that needs a pause to read fails.

**SH24 · Backgrounds are footage, filling the 9:16 frame.** The background is footage (the niche's footage by default, blurred only
behind a card; a product's own art blurred behind its cover), never an abstract animated gradient; the footage fills the whole 9:16
frame (no blurred bars, no sharp strip in a blurred field), its main part around the centre, chosen to show what is said. A cut-out, a
print or a card fills the frame too: the important thing is big, with no plain background around a small picture (a cut-out about 1.2x
the frame's width with its cut edge off the bottom, a document full bleed); a shot where nothing can be made out (a dark corridor) is
replaced, never kept for its words. Shorts viewers swipe away after one boring second.

**SH25 · The subject in the middle, placed by hand on its frames.** No 16:9 shot keeps the default framing (the middle of the picture
at full height: cx 0.5, cy 0.5, h 1.0): each 9:16 window is cropped and zoomed so its subject (the people, the thing the line is about)
sits in the middle of the frame, vertically too, placed on its own source frames over the shot's own seconds (faces by YuNet,
everything else by eye), zoomed in when the subject is small, a person shown whole with the head in frame (never a window of floor). A
moving subject is kept in the middle by a camera that moves with it the whole slot long (the Shorts kit's place() `path` `[[t, fx, fy,
s?], ...]`, placed key by key on `tools/motion/frame_review_at.py <id> --cols 6`): one framing right at one moment is not enough. Two
people talking: start on the one the words are on, then pan to the other, never frame the gap between them; whoever says a line is in
the middle while saying it. Picking the right picture is half the job and where the window sits on it is the other half: people named
in the words and then barely seen, cropped off, or a crop on the blank wall between two people, is the repeat failure.

**SH26 · A pan only when it has a job; a centred subject stays still.** A 9:16 window on a wide picture pans only (a) from one thing
the words need to the next when both can't fit, or (b) along a subject that moves (the framing kit's `path`, key by key); one subject
that fits stays put, a slight push at most; a pan across the whole picture for no reason is a fault. No gate check can know a pan's
reason (the gate's B11 PAN is off for Shorts), so each shot's move is written with its reason in the Short's shot plan and read on the
framing sheet. A pan without a job makes the eye chase nothing.

**SH27 · The hero dead centre, on a quiet ground.** A pan's last frame and every frame of a hold put the hero dead centre; a ground
behind a text is the document itself in shadow or nothing busy (a spotlight), never a dim menu screen. The eye goes to the centre of a
phone first.

**SH28 · Shorts use white and the caption key colour only.** Every designed colour in a Short (stamps, counts, crosses, marks, name
dashes, bars) is the caption key colour (a yellow, a `brand.ts` token) or white, whatever a long video's colour theme. A theme colour
plus one odd accent word looks off.

## Graphics

**SH29 · Everything centred; things compared are the same size.** Every asset and text is centred on the screen's axis (x 540), and
things compared are the same size. Off-axis things look like mistakes on a phone.

**SH30 · Few assets, clean objects with depth.** The few assets are clean objects with depth (a logo, a phone, a printed photo), never
floating strips or saturated stickers. Stickers look cheap.

**SH31 · No credits on screen in a Short.** A Short draws no source label on any shot (the Shorts kit's credit option left off every
picture, background and card); where a licence needs attribution (a CC BY photo), it goes in the upload's description lines
(`post.md`), never on the picture. Credits distract from the hook.

## Edit

**SH32 · Modern Shorts standards, with the long-form craft inside them.** Every Short has animations, one-to-one captions, many cuts,
music and sound effects, and no static text bar at the top (which looks amateur); build to modern Shorts standards, not to older
pipeline defaults, with the full craft (every cue on a word, kinetic type, measured marks, real footage) inside the Shorts rules (the
flash-in, the safe area, the phone-view check); every review adds to the editing standard. Old defaults look old.

**SH33 · A new picture every ~2.2 s, through other people's clips too.** No shot in a Short runs past ~2.2 s without a cut or a
cut-away to a new picture; a zoom-in or punch-in never counts as a cut; a long beat gets a second real picture, and props drift after
they land (never freeze). Someone's own clip gets the same pace: a new picture every 2-3 s over their words, each crisp and showing the
thing they talk about (the real material in its best source, their face where it helps), never a soft slide or a frame with nothing to
look at held for seconds (a 720p slide once held ~7 s). Spans are checked against the source's cuts (scene 0.08), and
`tools/motion/audit_short.py` runs before every render (`standard/SHORTS.md`, "Before it goes to the creator"); the render check
`tools/motion/qa_holds.py` (no stretch without a change longer than 2.6 s) counts any big change, punch-ins too, so the shot plan is
what holds the pace. Shorts viewers swipe away after one boring second, and Shorts that passed proof stills still held receipts 4-4.6
s, froze after props landed and crossed source cuts (a 67-ms flash).

**SH34 · Every cut shows something new.** Variety, not just cutting: every cut shows something new that matches the words (3-4
different pictures for one fact, picked by eye from all the footage), never the same picture twice in a fact, never a punch-in posing
as a cut; the chat reads every Short's frames before it renders, and a pixel checker is never the proof. A cut to the same picture
isn't a cut.

**SH35 · End where the content ends.** A reference's length or grid is not a quota: a Short stops when its material is used up, never
stretched on a frozen image. Stretching loses the viewers who stayed.

**SH36 · A bite reused from a long video takes both its numbers.** The clip's start and the sound's offset both come from the long
video's cut, and the Short's bite is checked against the long video's at the same moment before rendering. A bite once played with the
voice off its lips (the sound offset copied, the clip's start not).

## Captions

**SH37 · Captions show the spoken text, once.** A Short's captions show the full spoken text ("viewers prefer visuals" never thins the
captions), except where on-screen text shows the words being said: when a stamp, count, label or any on-screen text shows them, those
words come out of the captions for that stretch (`videos/<video>/captions_hide.json`, read by `tools/motion/finish_short.py`), and a
clip's own speech in a hold is captioned once, by the house captions (`captions_bites.json`), never by a second text layer; only a very
rare word is swapped for a visual (a word that could get the video restricted). The gate checks it before the render (B10
CAPTION_TWICE). The same words twice on screen are redundant.

**SH38 · Captions dead centre.** The house captions sit at y 960, exactly in the middle. The Shorts that do well have the captions
exactly in the middle.

**SH39 · Text that replaces the captions takes the caption line.** A text that replaces the captions sits centred on the caption line
(y ~960) while it replaces them, never in a numbers zone below (the Shorts kit's stamp, count and cross centre there by default; its
tag takes `top`), and the gate's B10 flags a replacing text off the line. While a stamp, count, name, logo or title card is on the
caption line, no caption shows at all (the small words around it go too: `tools/motion/finish_short.py` clears every caption under a
`data-gate="stamp"` item centred on the line, read from the gate's probe); a logo or title that names what is said lands clean and
whole on its word in the centre on that line; a stamp may carry the little word that makes it read ("SINCE 2015"); an action is shown,
not captioned ("He left the company": its logo struck through). Captions are for the words nothing else on screen says, and replacing
them means literally taking their place.

**SH40 · A name on screen is spelled as the script writes it.** The burned captions are the speech recogniser's words, and it spells
names its own way (a brand written in capitals turned into a plain word, a name's accent dropped, a person's name spelled by sound), so
`tools/motion/finish_short.py` puts every `tools/sound/names.json` name back as the script writes it; a gate A5 allow for a respelled
name speaks for the voice only, never for the captions. A misspelled name on screen is a visible error.

## Review

**SH41 · A Short's text is checked on the phone.** A frame that looks right in the file can be wrong in the app: nothing sits above y
260 (the status bar covers it), and the phone-view check (the creator's real phone UI laid over our frame,
`tools/footage/phone_view.py`) runs on every Short before it goes to the creator; well-performing Shorts keep most text in the middle
of the screen, then the top but well below the status bar. The app's own interface covers the edges.

**SH42 · Every shot's 9:16 crop is read against its words, the whole Short, every time.** Before any render that goes to the creator,
run `tools/motion/frame_review_at.py` on the whole Short and read every row in its crop column (`tools/motion/short_visual_check.py`
before the gate): the thing the words name, whole and centred; text and logos whole or out; nothing dark or blurry that shows nothing
(an archive clip that shows nothing is replaced by relevant footage). The sheet is read for "does the window follow the subject and
fill the frame?", never only for "is the subject inside the window?" at three moments; after every fix, the sheets again, and a sheet
read only for the shots that changed is no read. One look at one frame once missed a dozen framing faults.

## Packaging

**SH43 · A Short's title and tags.** A finished Short goes to the creator with one title and its tags as copy blocks, no description
(the creator has a standard one). Every Shorts title starts from the Shorts title research (`standard/SCRIPTS_AND_PACKAGING.md`): 1-2
CAPS words, the maker as the subject, count-led for lists, 40-60 characters, no vague "everything/something", and general, never the
clever detail (a news Short's title says what dropped in plain words, "NEW picture + NEW info", never one fact from inside it); the
message says which rules it follows. Titles built from one example miss what the research found.
