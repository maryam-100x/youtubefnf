# Rules for long videos (the main chat)

*The creator's rules for long videos only; the main chat reads them with `rules/SHARED.md`. The Shorts chat never reads this file:
where long videos and Shorts differ, `rules/SHORTS.md` holds the Shorts rule.*

**How these rules change.** They are the starting taste. When the creator gives a note that contradicts a rule, rewrite that rule to
their version in place, without comment (no "was X, now Y", no mention of the old rule). A new note becomes a new rule in the section
it belongs to, with the creator's own words beside it on the line under it (`> creator: "..."`), and takes the next free id of its
file; a note about both kinds of video goes into `rules/SHARED.md` instead. When two rules really clash, the newest one wins and the
older one is rewritten to it. Every rule lives in one file only; others point to it and never restate it.

**Format.** `**LF12 · Title.** What to do. Why.` LF = this file, AL = `rules/SHARED.md`, SH = `rules/SHORTS.md`.

## Working with the creator

**LF1 · A new video starts with the creator's vision, before any research.** The first thing on a new long video is a talk with the
creator about its vision (what it is, who it is for, what it must answer, how it should feel), their words verbatim in the video's
`VISION.md`; research only after that. The questions the creator names in that talk are examples of the depth, never the outline: the
video's shape comes from the research and the chat's own thinking about everything the title holds, said and implied; some of their
questions may be in it, and much else besides; the bar is extensive, smart, professional, the whole title covered. Research without the
vision answers the wrong question.

**LF2 · The interview after the script.** Between the finished script and the voice, pick the few spots where a take gives the video
personality (a verdict on a decision, who was right, what they would have done, how it felt as a viewer) and ask the creator short
questions about them in the final message: the 3-6 questions for their takes, plus a few where a section is heaviest in facts, asking
for their opinion there. Ask only where their take is open and adds something a viewer wants (which one felt better, what they will do,
what they hope, their memories); never a question whose answer is a fact (state the fact), one forced by circumstance (everyone has to
adapt), or one already talked through; fewer, better questions beat a full list, and the test is whether a friend who loves the niche
would actually ask it. Save the answers verbatim in the video's folder (`OPINIONS.md`) and write them into the script in the channel's
voice ("I think ..."), in the creator's meaning; opinions are occasional, never the whole video, and no opinion of the chat's stands in
for theirs. The interview is questions, not a script read, and the pictures can start while the creator answers. The creator is the
human behind the channel, and their view gives it its personality.

**LF3 · Ideas come as 10 titles, one line each.** Every idea round is exactly 10 numbered titles (the creator's title style: general,
no apostrophes), one plain sentence each on the theme; the creator keeps or dismisses. The thinking and the "already on YouTube?" check
happen first, silently, and only titles that pass go in; lanes and numbers go into a research file, never into the message. A report
buries the ideas.

**LF4 · Tell the creator the final length range once there is a good one.** When the script is settled enough to measure (words ÷ 3.9 a
second plus the bites and holds), the range goes to the creator in the chat; it is information, never a target written into the script,
and nothing is cut or padded for it. The creator likes to know; the video doesn't change for it.

## Workflow

**LF5 · Build the long video fully, then one review.** Never ask the creator mid-build which option to take: pick the favourite and
move on; the creator sees the 60-second prototype (when they chose prototype first, `creator/choices.toml`), then the finished
video once the chat deems it ready to upload. A question mid-build
stops the build and asks the creator to do the chat's job.

**LF6 · New material is woven in, never attached.** Big news during a build triggers a structural pass over the whole film (the hook,
the chapters, the callbacks, the close), never an appendix; every change is decided on what makes the best film, with no limit on
re-voicing or re-rendering (the pass may also confirm the structure is already right). An appendix reads as an afterthought.

**LF7 · A 1440p review copy at once, the 4K finish beside it.** The review copy is the render's own 1440p H.264 picture stream copied
as it is (no re-encode) with the mix at -14 LUFS (kept for every copy, so the creator hears the real level) and AAC, +faststart:
minutes, sent the minute it exists. The 4K finish (`PIPE tools/pipeline/pipe.py <video> finish`: picture and mix muxed in seconds, -14
LUFS in about a minute, then the lanczos upscale 1440p -> 4K and the encode on the GPU, `tools/motion/finish_long.py --gpu`, ~27 min
for 17 min of film, ~80 min for 52) starts automatically the same minute on the same picture and mix; only a major issue in the
creator's watch cancels it (stop only its own PID, delete its output for good, run it again on the version they pass). The upscale adds
no detail, only the platform's 4K bitrate, so it belongs to the upload and never delays the watch.

## Research

**LF8 · A documentary is made current once, then built.** Refresh the research right before the script, then build without chasing the
news; while the creator reviews the finished film, a new research run checks what came out meanwhile, and anything new is woven in
then; big news before the creator's review goes into the film first. The chat studies the primary material itself (frames and audio)
and researches alongside; posts the creator shares are background for the general consensus, never a template: we make our own, better
video. A film chasing the news is never finished.

**LF9 · A topic is covered whole, never boxed into a number of parts.** The material sets the scope: a list the chat proposes is a
start, never a cap ("five threads", "three reasons"); side topics keep their place, with less room than the main ones. A cap leaves out
what the title promised.

**LF10 · An idea is a whole subject, grounded, that passes the mainstream test.** Before a title goes into the 10, it must hold a whole
world to explore for 10+ minutes (a story, a system to explain, a prediction built on evidence, a real debate); a single fact or number
the title already answers is a line inside a video, never a video; no claim viewers would call nonsense, no link to the core subject it
doesn't really have, nothing whose audience the title itself puts off (a spoilers title for people who don't want spoilers). Someone
who never touched the niche's subject would click it and watch to the end, and it is checked against the channel's own videos' scripts,
not only YouTube (one round once held seven insider-only questions and two repeats of the channel's own videos). The topic needs enough
to explain to fill a long video and real heat (people already asking or arguing about it, measured in what the community talks about)
before it goes to the creator.

**LF11 · An unknowns video's list is thought up, then cleared by the creator's questions.** (1) The chat thinks the list up itself from
everything known, half-shown things and the smallest details, never from a search for "unrevealed", and the creator picks what fits;
(2) the chat sends a big dump of the subject's information for them to read; (3) every question they have while reading is checked:
answered = dropped, can't be answered = it stays. Something the community treats as settled is not "hidden", even when the maker never
said it; and in a "what's still unknown" video about an upcoming story-driven series, the story's twists, villains, backstories and ending
are out (keeping them back is just not spoiling), a story element staying only for a part of how it works that the maker never
explained, said that way. A known thing sold as a mystery shows bad research.

## Script

**LF12 · Length follows the story; at least 8 minutes, checked on the script before the voice.** A long video has no target length and
no minute estimate written down: it is as long as it is when finished, with nothing added to reach a length and nothing cut to shorten
it (all the creator's theories plus the chat's own stay). Its floor is 8:00 (needed for mid-roll ads), measured on the script before
voicing (words ÷ 3.9 a second at 1.04x speed: 8:00 is ~1,870 words; re-measure the rate on the creator's voice); a script under 8:00
goes back to the research, never to the voice, because there is always enough to say once the research is used: every real point from
the research that serves the title goes in (a method's "my lines few and short" means short lines, not few points), never padding and
never off-title extras. A long-length note from the creator means paying off the title in full; the test: did we make an extensive,
high-quality video with all the interesting information there is. A video once got voiced at 6:48 with most of its research left out,
then patched with off-title extras.

**LF13 · The title's promise is the spine.** Before the outline, write the title's promise in one line and give it most of the minutes;
each point is argued as the title's promise (how it makes the title true), and a point that doesn't serve the title stays out, however
true. A title that promises change is told as the change itself, fast, with the news behind it only as its quick reason. A recap of
what led up to it is 30-60 s; the script picks what is interesting from exhaustive research, and its length follows the material (a
long span researched in depth easily carries 20-40 minutes); cutting an overlong recap without building the promised part up is the
lazy fix. Four minutes of background before the promised subject breaks the click's promise.

**LF14 · The intro is the hook.** A documentary's intro is the hook, built with the best scripting plus the highest-quality, most
immersive editing possible (a real historical parallel can open it: the maker's own words, the real period photos and print). The first
minute decides whether anything after it is watched.

**LF15 · One piece, one quick rundown; chapters only for a story told in parts.** A topic video runs as one piece, without chapters;
the background a viewer needs is one fast-paced rundown, announced as such ("before we get to X, a quick summary"), in a fraction of
the video, then the topic; where the past IS the topic (an era, a history), it is told in full, documentary style. A video that argues
a point opens on the core the title promises, then takes the turn ("but first, let's take their claims apart ... now that we cleared
that up"): the structure lives in spoken turns, never in on-screen chapter cards or a cinematic frame. Every change of subject has a
transition that says why the next thing follows (a screenshot -> the article and back). Jumping between topics without one reads as
incoherent.

**LF16 · A section's facts belong to its subject.** After a line sets a section's subject ("the kitchen keeps one cook just for the sauces"),
only facts about that subject follow, told fresh, with fresh footage where it exists; unrelated facts dropped in, or a list from an
earlier video reused one to one, read as copied filler. A side story that one of our videos already told is cut when it is only a side
story here.

**LF17 · The making-of goes into a technical breakdown only as transitions.** In a breakdown whose subject is the product's technology,
making-of facts (the tool's history, the teams, the people) appear only as short bridges between tech topics (a line with a quick burst
of pictures), never as a section of their own. A history that keeps going past one bridge line is the failure.

**LF18 · The subscribe ask sits at a real break.** The ask goes where one point is completely finished and the next starts something
new, so it never feels squeezed in or tears the video apart; the midpoint is no target. It is voiced in its place
(`tools/voice/voice_context.py`, with the line before as context), and its listening files hold a few seconds before and after it. A
squeezed ask breaks the flow at the worst moment.

**LF19 · Every long video ends on the creator's sign-off word, when they chose one.** The last word of every long video is the same
one-word sign-off the creator chose (recorded in `creator/PROFILE.md`; none chosen, none used). This is the spoken word, the
creator's own; the like-and-comment sign-off on screen (LF36) is the look's design. The channel's videos end recognisably.

## Voice

**LF20 · The long-form prefix.** Every long-form request starts with "[flat, calm, even tone] [American accent]" (`config/tts.toml`'s
long-form prefix). The tone tags keep the documentary delivery, and the accent tag stops the slips.

**LF21 · Pauses: 0.25 s between sentences, 0.12 s inside, no breath in them.** After the voice is final: the breath pass silences the
breaths between words in place (`tools/sound/breath_cut.py <narration> <words.json> <out> --mode mute`, only its sentence and comma
regions as `rules/SHARED.md` says, and the stretches it "left alone" are read: they were real words badly timed), then
`tools/sound/shorts_tighten.py <video> --cap 0.25` (every pause between sentences over 0.25 s cut to 0.25 s, breaths inside pauses out,
edges proved quiet), then the pauses inside a sentence (commas and lists) to 0.12 s by `tools/sound/inner_gaps.py`, then close_gaps
(0.25 s) and the re-timing at the chain's end (`dj captions`, then `tools/motion/sync_words.py`). The gate's A3 flags a pause inside a
sentence over 0.20 s. Before every render, besides the gap scan, an independent list of every silence over 0.7 s measured on the audio
itself is read, and every pause (inside lines too) with an inhale or dead air in it is cut (`tools/voice/voice_edit.py cut`, edges
proved quiet), designed holds named as such. Longer pauses (~0.37-0.47 s) made the narration drag (the creator picked 0.25 s over
0.37-0.47, 0.14 and 0.07 s), a gap inside a list sounds like a break, and a ~2-s pause with an inhale in it once got past the gap scan.

## Sound

**LF22 · The voice sits ~22 dB over the music.** Cue sheets set UNDER 13, GAP_MIN 22, CARVE_DB 8 (`videos/<video>/score/cues.py`), and
`tools/sound/score.py`'s report reads 22-23 dB of voice over music in speech. At 17-18 dB the music swallowed the voice (between 17-18,
~20.5 and ~22.5 dB the creator picked ~22.5).

**LF23 · Booms are never cut short.** A boom or impact plays out its tail, never cut at a picture cut. A clipped boom sounds like a
mistake.

## Music

**LF24 · Music is ambience: keep it simple.** One sound world for the film and few cues (about one bed per chapter); changes only at a
chapter or a real turn, and always as a fade (mood switches are good for variety, never as a jolt or a sudden loud entrance); a bed may
stop dead on a line that ends something, with a bass drop, and a short phrase can stand alone over a music pause; no hype devices
(drops as a style, risers, swells, euphoric or comic tracks, melodrama); music well under the voice and few effects. Less is always
better than too much, because viewers care about the content and the music is there for atmosphere.

## Picture

**LF25 · Text cards are rare: show the thing happening.** A line about what the subject does gets that action's picture (a clip, a
split screen, a before/after, a built picture of the thing: the old and the new model doing the same task side by side,
mid-task), never a headline, page or text card standing in for it. A page or text card only when the words are about that page or
text (the quote that is the story, the headline as proof, a number on a page) and nothing visual shows it better, then short and rare;
a page that only repeats the line before ("according to four industry sources") is left out, and its time goes to the page that
matters. For a system or a comparison the default is a built demonstration (split screens, before/after, 3D with kit3d, diagrams that
move, cinematic camera moves on real material: the real logo extruded in 3D and lit like a product shot with one camera move; a
route acted out on the real map under "the road climbs over the pass"), text the last resort. Gate B19 CARDS
(`tools/motion/qa_cards.py`) holds it: CARD_REASON (a card without a `// card: <why the text itself is the point and no picture shows
it better>` line), CARD_TIME (cards over 8% of screen time), CARD_CLOSE (two cards under 20 s apart); sampled every 8 s, a video is
never half article pages and number cards. Viewers watch for instant visual feedback, not to read, and a video of pages feels like a
newspaper read aloud.

**LF26 · Show the thing itself, its number as the receipt.** When the words name a specific thing that exists as a picture (a video, a
post, a page, a chart, a stream), the screen shows that thing, sharp and full frame; when a number about it is the point, the picture
is the receipt that shows the number (the video page or channel screenshot with the count, marked on a frozen frame), with the people
or thing themselves beside it or before it. A big-number card over a blurred or unrelated ground is only for a number with no picture
of its own, and every such card in the film is fixed without the creator naming each. The house number card had become the default for
every statistic.

**LF27 · The source's own footage shows how it looks; our graphics explain.** Show the primary source's own material when the point is
how the thing looks, and build our own graphics when they explain. Each does what the other can't.

**LF28 · Every clip whole, filling the screen.** Every clip (the primary source's, a stream's, another channel's video) plays its full
frame filling 1920x1080: no crop to hide an interface, overlay, live chat, webcam inset or label, no zoom into a part, no clip shrunk into a
panel on a blurred ground (a 720p source upscaled to fill is fine); a soft or ugly source gets a cleaner source, never a crop;
`tools/motion/qa_kept_area.py` holds it (every clip ~100% kept, filling the frame). A letterboxed source plays at its own framing with
its own black bars, never cropped and blown up to fill (1.25x or 1.125x): gate B4 LETTERBOX_CUT fails such a clip cut without its bars,
and `qa_kept_area.py` counts a bar crop as a CROP. Crops cut the material's own text, and zooms into nothing look worse than the whole
picture.

**LF29 · Pictures whole, never cropped to fill.** A cover, poster or photo is shown at its own shape, whole, with room around it; a
layout never cuts a picture to fill a panel or the frame's width; crops only remove what isn't the picture (letterbox bars of a still,
an allowed watermark). Forced filling always looks bad.

**LF30 · Credits on screen.** An on-screen credit names the source's channel (the uploader, read from the platform's own metadata),
with a person's name only when it is that channel's name; a credit line goes on others' material, small in a corner of the picture that
shows it (or in the description); a demonstration made by someone else is credited on screen; another creator's quote set on our
material carries their name and title as a small source line; a documentary names each source on screen (outlet, headline, date) when
it is used. A community-made picture always carries a small caption under it saying it is community-made. The uploader is the safe
credit, and guessing who is on screen goes wrong.

**LF31 · An article screenshot is an editing moment that shows the article.** A screenshot of an outlet's article appears as a short
editing moment: page captures of the exact passage, its words lit as the voice reads them, the marker sound on each mark (the receipt
look), the camera zooming to the quoted phrase; the voice quotes the article ("[Outlet] writes ...", the person's own words) instead of
retelling it, and our commentary follows; never a slideshow of pages read aloud, and the other facts are retold in our words. A
retelling with no page on screen sounds like rambling, and a slideshow of pages is a newspaper read aloud.

## Graphics

**LF32 · One brand accent; the other colours from the video's own subject.** The one accent colour of every long video is the channel's
brand colour (`tools/motion/src/brand.ts`, `BRAND`), where a Short uses its caption colours; the video's other colours are a few plain
ones taken from its own subject and footage (a video about a company in that company's colours plus black and white), plain enough not
to distract. A colour picked for one video is never carried into the following videos as a theme unless the creator makes it the brand. A
one-off pick silently becomes the look of every video.

**LF33 · The prototype is the finished look; premium means the real thing.** A prototype shows the final quality, never a sketch. Every
beat is the real thing or a faithful rebuild filled with real data (the maker's own news post, the outlets' real pages, a court's own
words re-set as filed, the social platform's player with the exhibit's watermark, polls from outlets' screenshots, a ledger explorer's
real interface with the real values, a chart site's real candles, the outlet's own logo in its own typeface), and real 3D where the
references use CG: never invented generic shapes on a black void (a white pill for a date, grey calendar cells, line icons, a card with
an outlet's name typed in mono). A storyboard of finished frames first, then the animation on the voice; per shot type, the reference
channel's frame beside ours on a sheet, judged before the creator sees it, and every still checked; each idea from our story, never
"where the reference creator does X". The work is design (cards, graphics, composition, icons, logos) made to a measured spec so it
feels thought out, premium and current; 3D enters only shots where it clearly reaches the reference's level. Long form takes the days
it takes, and a fast delivery is a warning sign: bad 3D is worse than good 2D, and the template look is the fault that keeps coming
back.

**LF34 · Crosses and maxed-out meters in the alert colour.** A cross is the look's alert colour (`tools/motion/src/look.json`), never
a shade beside it; a meter at 100% turns the alert colour and blinks (three blinks, then it stays), with the error sound. Maxed out has
to look maxed out.

**LF35 · A mark on a small thing zooms into it, fast.** Every mark on a small thing (a dashboard warning light, a small chart in a corner, a
button label, a settings row) zooms into it in about half a second from the freeze, the dark kept round it; a thing in a corner is
zoomed into in its corner (the frame's edge stays the frame's edge); the clip is cut from the 4K master so the zoom stays sharp; a claim
about a gauge or light is shown on the moment that proves it (the thing happening in the picture while the gauge shows none of it); a
blinking light keeps playing under its zoom (kit3 Foot's `zoom` and `live`). Gate B25 MARK_SMALL (a mark on a small thing whose picture
never grows 1.6x within 0.7 s) and B4 UPSCALE (a zoom showing its file's pixels past 1.3x) hold it. A mark on a speck can't be seen.

**LF36 · The outro elements on every long video.** The sign-off (the like-and-comment elements, in the look's design) shows on every
long video's last line; gate B26 OUTRO fails a last line that asks for a like and a comment with no sign-off on screen. After it, the
video ends at once with a fade to black and a fade of the audio, with no held end screen. A held end screen loses viewers before the end.

## Edit

**LF37 · Long form follows the reference long videos, never the Shorts timers.** The Shorts cut timers and the flash open are for
Shorts only; a long video is edited by the reference long videos the creator names (a fast commentary style runs about 25 cuts a
minute with a median shot under 2 s, mixed media and memes, montage bursts, and deliberate 15-30 s holds on real people's clips and
deadpan contradictions): cut on meaning and hold where the reference holds. The channel's own best-performing long video's look
(pictures not text, real voices in holds, real pages alive, an archive look for the past, the title break) is
the other measure. Shorts pacing in a long video exhausts the viewer, and no holds lose the human moments.

**LF38 · The opening's density is the bar for the whole video.** The real thing on every word (a real search-results wall of the people
discussed, their thumbnails landing with their real view counts, the primary source's footage on every word, a day plan as a burst with
the planner down the side, their quotes lit word by word, a card shown through its states: built, hours lit, copied), and that density
and variety held to the last minute, never only in the opening. A strong opening followed by a thin middle loses the viewer the opening
won.

**LF39 · No zoom without a reason; a showing zoom starts on the whole picture.** The default for every picture and clip is the whole
frame at full resolution with a gentle drift (the slow keep-alive push is fine); a crop or zoom only where the words point at a detail
the whole frame can't show, written above the shot as `// zoom: <why>`, and then the shot opens on the full picture and zooms onto the
subject while it plays, the subject centred at the end; a shot never opens on a crop. A zoom that only "adds motion" or "fills the
frame" is the fault, held by the gate (a clip drawn 1.15x+ the frame needs its written reason and subject box,
`tools/motion/qa_shots.py`). Pointless zooms look far worse than the whole picture.

**LF40 · Be the pro editor: what is said is demonstrated.** Each line of the script is read for this before it is built: a line that
states how the subject works (the door locks after ten seconds, a sensor pings) gets a graphic that demonstrates it; a statement word
or phrase is written on screen as it is said, over the picture (not a text card); the picture's subject is the thing said (on "an alarm
goes off" the eye must land on the alarm, not on a person on the floor); every clip starts where its thing starts, with no sliver of a
neighbouring shot and no promo card inside a footage span; smooth, never a length rule. Once the creator passes the reworked prototype,
it is the standard for the whole film, applied by predicting where to put what, nothing in bad quality. A line only narrated is half
shown.

**LF41 · A breakdown plays the shot first, then stops on it calmly.** In a breakdown of a source video, each moment plays once at its
own speed with its own sound and no narration (whole, or slowed when that shows an action best), then cuts back to or holds its best
frame while the voice points out what is in it, then plays on to the next thing and stops on its best frame; a shot plays as much of
itself as its stop frame allows (the whole shot when the detail is at its end), and a still holds only while the words are about that
frame and plays on once they move on. A zoom only to show the detail, the mark exactly on the thing and clean; no constant pushes, no
clip looping, replaying or running on into the source's next shot, never a fraction of a second of a clip then a long freeze, never a
stop on a frame mid-fade or with the subject cut off; a card goes ~3 s after its point is made. When the voice expounds without showing
one thing, the newest primary-source clips play (repeats allowed), never a held still or older material as filler. It is never rushed:
the source's cut times are measured frame by frame before the edit uses them and no slot crosses one (a line's length never decides how
long a clip plays); the script is checked line by line against what each frame shows (no shot-by-shot narration "First this shot...
then...", no meaning read into a shot that it doesn't show, no tangent the source doesn't raise, places, people and products named right, things
named the way the creator named them); highlights only from word boxes. A rushed breakdown once had ~30 slots running into the next
shots, clips starting 3-5 frames early, every shot pushed and rings off their subjects.

**LF42 · A mark finishes before any cut.** A marked page holds until its mark has run and been read. A cut mid-mark loses the point it
was marking.

**LF43 · A picture-set video runs from most to least interesting, in the creator's order.** The order the creator sends their notes on
a set of pictures in IS the video's order (most interesting first, descending, to keep retention); each picture's article part moves
with its picture; the article's opening goes up front and its ending with the last picture. Retention follows interest.

**LF44 · An original clip with its own sound plays as it was cut.** A clip played with its own sound (a bite, a moment shown as it
happened) runs as the source file has it, from its in-point to its out-point: its own cuts only, nothing inserted, the picture in sync
with its sound. Inserted cuts break the sync and the sense.

**LF45 · Picture and patches on the frame grid, matched by frame number.** Patches are laid in by frame number
(`tools/motion/finish_long.py`, `tools/motion/splice_patch.py`), and a patch's seams are checked frame by frame against the last
version. A render's timestamps drift up to 8 ms early by a film's end, which once landed a patch a frame late.

## Review

**LF46 · The first minute is watched as a viewer first.** Before anything else, watch the first minute as a viewer would: if it doesn't
hold, nothing after it matters (a first draft was binned after one minute). The first minute is where viewers leave.

**LF47 · The creator watches the first full render.** Once every section has passed its own reviewer's-eye round, the first full
render's 1440p review copy goes to the creator the moment it exists, with no full-film review of the chat's first; their notes are the
fix round (each fix a sample), only cheap tool checks run on the render (the render scan), and the 4K starts with it. The creator
watching as the audience finds what matters faster: they overlook minor things on a big video and name the major ones (an accent slip).

## Packaging

**LF48 · The title: a short plain statement with a spark.** A big-picture long video's title defaults to a short plain statement of 5-7
words (no CAPS word, no "you", no brackets, no "?" or "!"), most often "The [one big word] of [subject]" or "The [subject] [plain
verb]", naming one big subject, where it reads naturally; it rides with the topic and never works as a trick by itself. The spark test:
does reading the title leave you needing the video? A statement you can agree with from the title alone fails. A title you can nod at
gets no click.

**LF49 · Every long video goes up with an A/B test of three titles.** Three titles from different title families
(`standard/SCRIPTS_AND_PACKAGING.md`), picked by the creator, for the platform's test-and-compare. The audience picks the title better
than anyone.
