# Sound craft for narrated YouTube videos and Shorts: effects, music, narration, mix

*The question: how top YouTube editors and sound designers do sound design and audio engineering for narrated commentary and
documentary videos and for Shorts, and what that means for this pipeline (an ElevenLabs voice, music that is the creator's own or made
in code, numpy + ffmpeg mixing, -14 LUFS delivery). It builds on, and corrects where needed, an earlier pass of this research (cited
below as **P**, its sources as **P-S#**) and our own measured studies of reference videos. Nothing here is authoritative: older files
are evidence and are graded like any source.*

*Read with: `standard/SOUND_AND_VOICE.md` (the house rules: where this file and the standard differ, the standard wins),
`standard/MUSIC.md`, `standard/research/SFX_TASTE.md` (how the house effects were picked), `standard/research/VOICE_CRAFT.md` and
`cases/SOUND.md`.*

**Where the house standard decided differently** (the evidence below stays as found; the rule lives in `standard/SOUND_AND_VOICE.md`):
- Effects: one house sound per recurring action, never rotating variations (§2.2, §7); no quota a minute (§2.5); no effect louder than
  -7 LU against the voice (§2.4's booms over the voice are out).
- Music: no drops, risers or swells in the beds; the voice ~22 dB over the music in long form, ~17-18 dB in Shorts (§3.4, §4.4).
- Real voices in their own sound: the bed drops about 32 dB under the speaker (§5).
- Narration: dry, no de-esser and no EQ chain, to loudness through chain D (§9 is the research's proposal, not the house chain).
- Music source: the creator's own tracks or music the chat makes in code; no stock library is part of the pipeline (§3, §6.1).

**Method.**
- Web search (about 30 queries, until the search budget ran out); pages read with curl and converted to text (list in Sources).
  YouTube transcripts with yt-dlp auto-subs. YouTube's bot check (HTTP 429, "confirm you're not a bot") blocked 8 of 18 transcript
  requests and every watch-page read for a stretch; it was not bypassed. 10 transcripts were read in full or in the parts that matter.
- Our own measured studies of reference videos and of our own builds are used as evidence and named as such (**I#**). Reference
  channels in the niche we studied are described, not named or linked; their findings stay as our own observations.
- No media downloaded, no browser tool. Quotes from sources are under 15 words; everything else is paraphrased.

**Grades:** **A** = specs, product docs (for what the product does), creators' own words about their own work, YouTube Studio data.
**B** = peer-reviewed studies, trade press, established professionals showing their own work, and our own measurements (checked by eye).
**C** = vendor blogs, sponsored or product-selling tutorials, forums, anything seen only as a search excerpt. Every section separates
**Evidence** (measured, documented) from **Practice / opinion** (what working editors say they do).

---

## 0. The answer in 15 lines

1. **Effects mark meaning, not cuts.** In 8 of 9 + 3 of 3 measured reference Shorts, plain cuts carry a sound only at chance rate; sounds
   sit on visible events (pop-ins, flashes, clicks, slams) and on new information (a date, a name, a reveal) [I5, I6, I1].
2. **Density, measured:** long-form references 0.2-4 confirmed effects a minute (a fast commentary reference ~4, a well-performing long
   video of ours 3.2); Shorts 5-14 a minute. Machine counts of "12-30 a minute" were uncalibrated detector candidates, about 6x too
   high (§1).
3. **Front-load:** the hook is the densest stretch (a 13-minute explainer reference: 18 of 23 effects in the first 3.5 min [I2]; a
   tutorial sound-designs every on-screen event in its 30-s intro but not every text in the body [N5]).
4. **A small vocabulary does most of the work:** whoosh (motion), riser (anticipation), impact/boom (emphasis), click/pop (UI, lists),
   plus the music cut-out (silence before the point) [N2, I1, N1].
5. **Layer and commit to one style:** a big moment = 2-4 layers across the spectrum (low boom + mid hit + bright transient or riser);
   one sonic palette per video [N3, N4, N2].
6. **Timing, measured:** hits start ~1 frame early and peak ~1 frame after the picture event (onset median -18 ms, peak +27 ms);
   whooshes start 70-320 ms early and peak 50-110 ms after the cut; risers end on the reveal frame [I5, I1].
7. **Levels vs the voice:** small UI sounds 8-16 dB under, whooshes 8-14 under, hits and booms at voice level (up to +3 dB on 1-3 moments
   a video), ambience at least 15 LU under [I5, I7, I2, P-S19].
8. **Music:** one sound world per video, a bed per chapter or turn (~every 1-1.5 min), 17-22 LU under dense narration and 12-15 LU under in
   the hook, big moments and Shorts; ducked ~6-8 dB under speech, carved 3-6 dB at 1.5-4 kHz [I8, I3, I2, I5, N11].
9. **Silence is the strongest effect:** music out 0.5-3 s before a turn or punchline, back on the next line (all five long-form refs;
   Shorts: 1.5-2 s dry, slammed back within ~15 ms of the cut) [I2, I5, N1].
10. **Narration chain:** clean takes, per-section level match, HPF ~70-80 Hz, small corrective EQ, de-ess (male 3-6 kHz), gentle 3:1
    compression (3-5 dB), phrase-level gain riding, no reverb; master -14 LUFS / -1 dBTP [N15, N12, N13, N11, P-S14].
11. **Real clips keep their own sound** (music and all), cut with the picture, levelled by their speech to the narration, the bed out
    under them (the house rule) [I11, I14, I8].
12. **Translate:** 64.7% of a well-performing long video's watch time was on TV [I9]; sub-only booms need harmonics; check mono and a
    phone [P-S38, P-S39].
13. **Premium = intent + consistency + contrast:** every sound has a reason, one style, frame-exact, quiet before loud, steady loudness.
    Cheap = a whoosh on every cut, mixed random packs, music fighting the voice, jumps in level [N1, N3, I10].
14. **Tools:** the free Sonniss GDC archive (200 GB+) is the best free effects library; the one paid tool with clear value is iZotope RX
    12 Standard ($399); FabFilter only if an A/B wins (§10).
15. **Unverified and worth testing:** whether Shorts are loudness-normalized like long videos (no primary source found); the creator's
    ear on any narration EQ (their call, never a measurement's).

---

## 1. Cautions: claims you will meet, and what the evidence says

| # | Claim | What the evidence says | Grade |
|---|---|---|---|
| 1 | Long-form references run **12-30 effects a minute** (three references measured 12, 30 and 23) | These are a transient detector's **candidates**, not confirmed effects. The same detector on the same 9-minute fast commentary reference, checked by eye: **~40 placed effects in 9.3 min (~4/min)**; the detector's hits were diluted by music hits (drum loops). So the machine numbers are ~6x too high for that video and unconfirmed for the other two. Confirm effect counts by eye | B [I1, I3] |
| 2 | Effects "about one a minute" | No basis. Confirmed long-form references span 0.2-4/min; fast commentary ~4; **a well-performing long video of ours had 31 placed effects + 6 real-voice bites in 9:35 = 3.2/min** (3.9 with bites) [I8]. One a minute fits slow mystery documentaries (LEMMiNO ~0.3, Nexpo ~2.3), not fast commentary | B/A [I1, I4, I8, I11] |
| 3 | "No hype devices: no drops, risers, swells" | Right for **music**: a future-bass drop, a newsroom ident and a sad-piano jump each broke one of our builds in review. Not supported for **effects**: the fast commentary reference uses risers 0.6-3 s into reveals; every tutorial read uses riser into impact. Risers as effects stay possible inside the video's sound world, sparingly; the creator's ear decides | A/B [I10, I1, N1, N2] |
| 4 | Music "about 16-18 dB under speech" (one number) | Consistent with one of our mixes (voice over beds 17.1-18.7 dB) and below the references' body levels (19.6, 19.0, 22.9). But the references **set the bed per section**: ~14 dB under in cold opens and big moments, 20-25 under in dense explanation; Shorts 8-18.5 under | B [I8, I3, I2, I5, I6] |
| 5 | "Give each story beat its own cue; don't stretch a few beds" | Read as licence for 29 tracks in 21 min with genre jumps, one of our builds read as overcooked and lost its reviewer. The **rate** was not the problem (the documentary channel fern: 53 tracks in 47 min; a well-performing long video of ours: nine beds in 9.6 min): the jumps out of one sound world were. Restated: a bed per chapter or turn, all from one sound world (that video's nine beds were all by one artist) | A/B [I10, I8, P-S60] |
| 6 | "Whoosh peak on the cut: only vendor guides say this" | Measured on reference Shorts: whoosh onset 6-320 ms early, **peak +53 to +106 ms after** the cut; hits onset median -18 ms, peak +27 ms. The peak lands 1-3 frames after, not on the cut | B [I5] |
| 7 | No source gives rules for UI clicks, typing, paper, shutters | Still no A/B standard, but practitioner sources and our own measured mixes give a usable taxonomy and levels (§2.1) | C/B [N5, N6, N2, I8] |
| 8 | "-14 LUFS; no YouTube page states it" | Still true. Ian Shepherd (2017) adds that YouTube's own "content loudness" (Stats for nerds) is the real measure, and that aiming at -14 is not the method. -14 stays a sound delivery (no turn-down). **Shorts normalization: no primary source found** | B [N24, P-S14] |
| 9 | Placed effects 0.2-4 a minute, on new information, none in explanation stretches | **Right**: confirmed by eye, and it matches the Shorts data (effects on events, not cuts) | B [I2] |

---

## 2. Sound effects

### 2.1 The kinds, and what each one marks

| Kind | What it marks | Length | Evidence (B, A) | Practice / opinion (C) |
|---|---|---|---|---|
| **Whoosh** (air, heavy, whip, wind) | Something moving in, out or across the frame; a camera move; a cut that should feel like one continuous moment | 0.25-0.8 s (fast commentary reference); heavy 0.6-1.5 s | The fast commentary reference: noise whoosh or glitch 0.25-0.8 s when the picture changes space [I1]; Shorts refs: onset early, peak after the cut [I5]; one of our long videos: tiny swooshes on five people's photos [I8] | Light/high = fast, fun, comedy; heavy/deep = big objects, close to camera, serious; whip = whip pans, sudden action; wind = aerials [N2]. Keep 7-10 fast and 7-10 deep ones ready [N5] |
| **Riser** (noise, cymbal, low rumble) | Anticipation: before a reveal, an answer, a big scene change, or a smash cut into silence | 0.6-3 s (fast commentary reference); tutorials 2-10 s | The fast commentary reference: riser into a drop or reveal (0:25.5, 5:56-6:00, 9:11) [I1]; a long documentary reference: a riser filling a "what if" pause, ~10 dB under [I2] | Riser = tension, the hit = release; stack a low rumble riser with a bright cymbal riser [N2]; end the riser as the next sentence begins, a low boom on its end [N1] |
| **Reverse / suck-back** | A pull into the next moment or into a big hit | 0.3-1.5 s | | Reverse an impact to make a riser [N4]; reverse a song's tail as a swell into the next track [N10]; reverse the next song's first beat as its lead-in [N3]; "suck-in" before an impact [N5] |
| **Impact / hit** (sharp, cinematic) | "Pay attention to this": the end of a build, a physical hit, a striking new shot, a claim | 0.2-2 s | The fast commentary reference: short broadband hit or click on each new card, logo, photo or list item [I1]; Shorts: shatter 22 ms after "loud" (the cat explainer), 11 of 13 colour flashes get a hit (the call edit) [I5] | Deep trailer-style with long tail vs sharp object-on-object [N2]; whoosh into impact makes a cut stand out [N2] |
| **Boom / sub drop** | Dates, names, reveals, dark turns, chapter cards, the last word | 0.5-2.5 s tail | The fast commentary reference: boom on every date and name of its history ladder, first frame and last word [I1]; long-form refs: first frame boom, last word boom [I2]; sub-only booms vanished on TV speakers in one of our builds [I10] | "Longer, deeper" than a hit, for dramatic moments [N5]; a chapter card + a really solid boom makes the cut feel intentional [N1] |
| **Stinger** | A recurring structure point (chapter card, title), a sonic brand | 1-4 s | LEMMiNO: one identical sting on every chapter card [I4] | |
| **Glitch / static** | Errors, data, "it broke", a glitch transition, cutting into TV footage | 0.2-1 s | The fast commentary reference: a 0.25-s noise burst on its RGB-split glitch transition [I1] | Glitch and "electrical" sounds for glitchy text and channel-not-found moments [N5] |
| **UI click / mouse** | A cursor clicking a real page, a toggle, a CTA, a button | < 0.2 s | One of our long videos: a click on each of 15 real press pages, timed to the cursor [I8] | Clicks on 3-4 quick related shots make an edit feel alive [N2]; clicks for text appearing and faceless content [N5] |
| **Pop / ping** | An icon, avatar, list item or cover popping in; an arrow callout | < 0.15 s | Long-form: pops 6-12 dB under the voice on list items and covers [I2]; the house rule: an arrow lands with the ping [I11] | |
| **Typing / spacebar** | Text typed on screen; word-by-word reveals | per keystroke | Typing 15-27 dB under the voice (two long-form references, at 0:01.9 and 1:18.8) [I2] | A spacebar sound per word only in the intro, never on every text (the viewer gets annoyed) [N5]; typing under a number counter [N5] |
| **Marker / highlight** | A highlighter sweep, a line drawn, an underline | 0.3-1 s | Our marker sits ~16 dB under the voice (measured on the stems) [I7] | Marker strokes for line animations and highlights [N5] |
| **Paper / page** | Documents, bills, posters, patents, court papers handled or sliding in | 0.3-2 s | | Three layered paper tracks for one bill in a broadcast spot [N6] |
| **Camera shutter / flash** | A screenshot appearing, a photo, a sudden reveal; archival strobe | 0.2-1 s | The industry-analysis reference: white strobe flashes over archival photos [I3]; one of our long videos: a flash sound on five archive strobes, a shutter on a selfie [I8] | Shutter or flash for screenshots and on-screen reveals [N5] |
| **Counter / clock / heartbeat** | A number running, time passing, a countdown, the wait before a payoff | loop | Two long documentary references run counters in silence (a choice, not a rule) [I2] | Clock ticks build suspense (challenge videos); digital data or a cash-printer sound under counters; a heartbeat before something big [N5] |
| **Money** (register, coins) | Money figures appearing | 0.5-2 s | | A cash register or printer when money is said or counted [N5] |
| **Swell** | A soft lift into a calm reveal or a new section | 1-4 s | A science Short (6Cwn): a low drone swells in over 0.35 s with Einstein's picture and stops on the cut back [I6] | Swells and suck-backs layered under a song's entry [N3] |
| **Ambience / room tone** | The world the voice sits in; a scene's place; the "air" under a music stop | loops | Ambience at least 15 LU under narration (listening test) [P-S19] | Build ambience first, then dialogue, then effects, then music; ask what the sound of the shot is [N6]; ocean and wind under a cliff dive [N1] |
| **Literal / Foley** | What the picture shows: a slam, a hit, a car, footsteps, cloth | event | The explainer reference: a robot slam, a knock-out; slams at or over the voice [I2] | Clothes rustle, a thunderclap between two lines (Oppenheimer) [N6] |
| **Meme / comic** (record scratch, bass boost) | A comic stop, a contradiction, a censored word | < 1.5 s | The house censor for a swear in the narration: the meme bass-boost hit, 6 dB under the voice [I11] | A record scratch at the end of a stopped music cue [N1] |

### 2.2 Layering

**Evidence:** Murch's rule of thumb: listeners follow about two and a half layers of the same kind of sound; up to ~5 when spread across
the spectrum [P-S30 B]. Impacts built from a main hit, a texture and a low-end sweetener [P-S32 B].

**Practice (C, consistent across sources):**
- Think of layers like a cake across the spectrum: a single whoosh is fine for a small move; a big move gets a deeper layer and a
  bright one [N3].
- One shot in Artlist's tutorial carries five layers (radio chatter, an intro impact, breathing, a second impact); one pool-ball hit is
  three impacts plus a riser; low-pass filters turn chewing and bone cracks into a "wet" texture [N4].
- The go-to stacks: riser into impact; low rumble riser + cymbal riser; whoosh into impact on the new shot [N2].
- If the exact sound doesn't exist, break it into two searches and layer the parts [N6].
- **Commit to one style per video** instead of mixing random packs: gritty bass hits don't fit a corporate piece, clean dings don't fit a
  streetwear promo [N3].

**For us:** at most 2 of a kind at once and ~5 layers in any 5-s window (an earlier check, P's C11, stands). Practice keeps 3-8
variations per category so identical samples never play back to back; the house standard instead gives each recurring action one
sound everywhere (`standard/SOUND_AND_VOICE.md`), so the viewer learns it.

### 2.3 Timing: to the frame, and the pre-roll

**Evidence:**
- ITU-R BT.1359: early sound is noticed from 45 ms, late sound from 125 ms [P-S1 A]. Two to three frames off reads as sloppy [P-S32 B].
- Our Shorts references, measured on spectrograms and frames (n=14 hits): **onset median -18 ms, peak median +27 ms** (IQR +2 to +36).
  Heart pop -8/0 ms, TV shatter -71/+2, outro slam -38/+36. Ramped flashes: the sound peaks on the brightness peak (-22, +7, +41 ms).
  **Whooshes and risers: onset 6-320 ms before, peak +53 to +106 ms after**; under a highlight wipe the swell peaks ~50 ms after the
  motion ends [I5 B].
- A 20-year broadcast editor turns on sub-frame editing to put impacts exactly on the frame [N6 B].

**Rule set (ours, from the above):**

| Sound | Where its parts go |
|---|---|
| Hit, pop, click, shutter, slam | Onset 0-1 frame before the event frame; peak within +40 ms; never more than ~40 ms early |
| Whoosh | Start 70-320 ms before the cut (longer whoosh = earlier); peak 50-110 ms after it (~2-3 frames at 30 fps) |
| Riser | Ends exactly on the reveal frame or word; the impact (or the silence) starts there |
| Flash sound | Peak on the flash's brightest frame |
| Boom on a word | Onset on the word's measured onset (not the transcriber's word start: ElevenLabs character times run 30-60 ms behind the audio) [I12] |

`tools/sound/score.py` already places every effect by its measured impact (first point within 6 dB of the peak) [I13]; keep it.

### 2.4 Levels relative to the voice

**Evidence:**
- Shorts references: effects from -8 to -23 dB under the voice (a news Short in the niche we studied), +1 to +4 dB (the cat explainer),
  -8 to +6 dB (the call edit) [I5].
- Long-form references: booms at or slightly over the voice; pops 6-12 dB under; whooshes and glitches 10-17 under; typing 15-27 under;
  slams at or over [I2].
- Our own first Short (measured, 50-ms RMS on the stems): whoosh -15, pop -10 to -14, marker -22, hit ~-2 dB vs the voice; after a
  reviewer asked for louder effects: whoosh ~-9, pop ~-8, marker ~-16 [I7].
- WCAG's 20 dB rule exempts sounds of 1-2 s [P-S9 A].

**Practice (C):** a stock-music vendor's mixing guide, in peak-meter terms: dialogue -9 to -18 dBFS, effects -10 to -20 dBFS, music under
dialogue -30 to -35 dBFS [N9].

**Recommended (voice-relative; effect's peak 50-ms RMS vs the narration's median 50-ms RMS during speech):**

| Class | Level vs voice |
|---|---|
| Boom on a date, reveal, title, last word | 0 to +3 dB, on 1-3 moments a video above 0 |
| Cinematic hit, slam, literal impact | -6 to 0 dB |
| Riser | rising to -6..0 dB at its end; ~-10 dB when it runs under speech |
| Whoosh, glitch, static | -8 to -14 dB |
| Pop, click, ping, shutter | -8 to -14 dB |
| Typing, marker, paper, UI motion | -14 to -22 dB |
| Ambience, room tone | at least 15 LU under (-18 to -25 dB) |

(The house measure is different and stricter: each effect over 1.5 s from its impact against the voice's integrated loudness, none over
-7 LU; `standard/SOUND_AND_VOICE.md`.)

### 2.5 Density per minute: long form vs Shorts

| Video | Effects a minute | How counted | Source |
|---|---|---|---|
| A fast long-form commentary reference in the niche we studied (9:17) | **~4** (~40 in 9.3 min) | confirmed by eye on storyboards | [I1] |
| same video | 23 | detector candidates (unconfirmed) | [I3] |
| A long-form industry-analysis reference | 12 | candidates (unconfirmed) | [I3] |
| A long-form story video from a large commentary channel | 30 | candidates (unconfirmed) | [I3] |
| **A well-performing long video of ours** (9:35) | **3.2** (31 placed) + 6 real-voice bites | cue sheet | [I8] |
| An explainer reference (13:24) | 1.7 (18 of 23 in the first 3.5 min) | confirmed | [I2] |
| Three longer documentaries (17:44 / 28:52 / 28:31) | ~1 / ~0.3 / ~0.2 | confirmed | [I2] |
| LEMMiNO, Cicada 3301 / Nexpo / Barely Sociable | ~0.3 (5 in 18 min) / ~2.3 / ~0.2 (4-5 in 27 min) | confirmed | [I4] |
| Shorts: a cat explainer (s1c1) / a call edit (5eu7) / a news Short in the niche / LrCU | ~10 / ~14 / ~8 / ~5 | confirmed on spectrogram + frames | [I5] |
| A music-edit Short (cwaj) | 0 (the music is the edit) | confirmed | [I5] |
| A science Short (6Cwn, Brian Cox, 46 s) | ~4 big ones (~5/min) | by eye | [I6] |

**External:** no published per-minute effect count was found for any channel. MrBeast coverage counts only cuts (38 a minute in an older
video, 23 in a 2024 one) [N46 B, excerpt]. A vendor blog's "3-5 key beats per video" for Shorts [N45 C] is contradicted by the measured
5-14 a minute; the measurements win.

**For us:**
- **Long form:** ~3-5 placed effects a minute in the body, 2-3x that in the first 30-60 s; none under explanation stretches (the fast
  commentary reference has none at 5:00-5:56 and 7:30-8:00 [I1]).
- **Shorts:** 8-15 a minute, on every emphasis event (pop-ins, flashes, hero words), never on plain cuts.
- (The house standard sets no quota: effects follow the picture, and never 4 inside any 5 s; `standard/SOUND_AND_VOICE.md`.)

---

## 3. Music

*In this pipeline the music is the creator's own tracks or music the chat makes in code (`standard/MUSIC.md`). The findings below are
about how music is used, whatever its source.*

### 3.1 Choosing beds by section

**Evidence:**
- Beds under 95-97% of the runtime (three long-form references) [I3]; 80-97% in four of five long-form refs [I2].
- A new track per chapter, roughly every 1-2 min: the fast commentary reference 10 in 9 min, two longer documentaries ~20 in 17.7 and
  ~16 in 13.4 [I2]; a well-performing long video of ours nine beds in 9.6 min, one artist [I8]; LEMMiNO 36 tracks (20 of them from one
  stock library) in a film of at least 57 min [P-S58 A].
- A reviewer's verdict on one of our builds: the music is there for ambience, keep it simple; a dated future-bass drop and a jump to sad
  piano broke the film [I10 A].

**Practice:**
- Pick by the emotion you want the viewer to feel, decided before searching: hype, uplifting, dark/tense, sad, chill, cinematic, comic [N5].
- Almost never one track for a long edit; switch with the section [N5].
- Build ambience, dialogue and effects first and add music last, because music can hide what's missing; the cut has to work with the
  music off (a mentor's test) [N6 B].

**For us:** spot the video by chapter, then choose all beds inside one sound world (one artist or one sub-genre), with mood changes only
at chapter turns. Test every finished mix once with the music muted: if the effects and voice don't carry the edit, the edit isn't done.

### 3.2 Cutting music to the edit

**Evidence:** two to three frames off already feels sloppy; cut just before a transient with a ~2-ms crossfade, or just after the beat
with a fade of 3 frames or less [P-S32, P-S33, P-S34 B]. The narrated reference Shorts do **not** cut on the beat (0 of 4), while the
music-driven Short cuts 69% of its cuts within 60 ms of a beat (chance 24%) [I5]; a storytelling Short (Yj7) lands 54% of its cuts on the
song's bass onsets (chance 24%) [I6].

**Practice (C):**
- To overlap two songs, match their BPM; cut the incoming track just before its beat and sweep a high-pass filter open so it "arrives"
  on the beat [N10].
- Turn the outgoing song's reverberant tail around as a swell into the next song's first beat [N10].
- To end a song early: cut before the next beat, put a big reverb (a "Great Hall" preset) on the last beat, layer a swell or impact [N3].
- To start a song without a lead-in, reverse its first beat as a riser [N3].
- Trim whole phrases; cut on downbeats or phrase boundaries; don't cut picture on every beat [search excerpts, C].
- A track's length is fitted to the chapter: music made in code is made to length; a fixed track is back-timed, its real ending placed
  on the cut (an earlier pass, P).

### 3.3 Stingers, risers into drops, silence

**Evidence:**
- **Music cut-outs:** all five long-form refs cut the music for 0.5-3 s before a turn or under a punchline, slamming it back on the next
  line (one 17-min documentary 19 times, the explainer reference 10) [I2].
- **Silence in Shorts:** the call edit fades its bed to -60 dB after the setup line, 1.9 s dry voice, music back 13 ms after the whip
  cut [I5].
- **Dip before a reveal:** Short LrCU dips ~8 dB for 1.3 s and comes back up on the reveal word [I5].
- **Branded sting:** LEMMiNO uses the same sting on every chapter card [I4].
- **Title break:** the fast commentary reference's music-only title break is its most replayed stretch (0.93-0.99) [I3].

**Practice:**
- A chapter card + a solid boom; for a key point, stop the music abruptly with a crash zoom and resume after the point, optionally with
  a record scratch at the stop [N1].
- Riser into a smash cut that drops into silence: the contrast hits harder [N2].
- Lower the music for a 1-s pause before a reveal, with a low vibrating sound as a riser [N5].
- MrBeast drops the music entirely for a sad moment (cited by [N5]).

**For us:** risers into drops in the **music** stay out (the house standard keeps drops, risers and swells out of the beds). Designed
silence (a real stop, not a quiet bed) is the main contrast device: YouTube's Stable volume may lift quiet beds, but it cannot lift
digital silence [P-S10].

### 3.4 Ducking: how far, how fast

**Evidence:**
- A listening test: at least 10 LU between speech and music, 15 LU for ambience; non-experts wanted ~4 LU more than experts [P-S19 B].
- WCAG's strictest level: 20 dB [P-S9 A].
- Our references: Shorts beds duck ~7 dB under speech [I5]; one long documentary's bed rises ~8 dB in the gaps [I2].
- A well-performing long video of ours: each bed set 10 dB under the voice by loudness, then ducked 6 dB and carved 6 dB in the voice
  band under speech (sides 3 dB); measured voice over beds 17.1-18.7 dB [I8].

**Tool defaults (A):** Resolve's Fairlight compressor defaults, per its manual as quoted in a 2026 tutorial: threshold -15 dB, ratio 2:1,
attack 1.4 ms, hold 0, release 93 ms; Resolve 19+ also has a one-click Ducker track effect (Duck Level, Rise Time, Recovery) [N26 C].
ffmpeg `sidechaincompress` defaults: ratio 2, attack 20 ms, release 250 ms, RMS detection [N21].

**Practice (C):** 12-18 dB duck for general YouTube (when the music sits loud in the gaps), rise 100-300 ms, recovery 300-600 ms;
cinematic cues 6-12 dB with slower rises [N26]. A release that is too fast makes the music pump between phrases [N26].

**For us (offline, from the word times):** the bed's level is set per section first (17-22 LU under in dense narration, 12-15 in the
hook, big moments and Shorts); under speech it drops another 6-8 dB, starting 100-150 ms before the first syllable, holding through pauses
shorter than ~0.7 s and recovering over 300-600 ms. Never let the bed rise more than ~8 dB in a gap. (The house bar is the measured voice
over the music: ~22 dB in long form, ~17-18 dB in Shorts; `standard/SOUND_AND_VOICE.md`.)

### 3.5 EQ carving of the voice band

- **Evidence:** the 1, 2 and 4 kHz octave bands carry ~72% of speech intelligibility weight (ANSI S3.5) [P-S27 B].
- **Practice:** a static 1-4 kHz cut in the music makes it sound muffled when no voice is present. The fix is a multiband compressor (or
  dynamic EQ) on the music's 1.5-4 kHz, keyed by the voice, so the cut only happens under speech and follows the voice's level [N11 C].
  A creator's trick: a de-esser on the music used as a dynamic mid-range carve [N3 C].
- **Automatic tools:** Trackspacer (inverse EQ from the sidechain) [N33]; smart:EQ 4 (cross-channel unmasking of up to 10 tracks) [N34].
- **Ours:** `tools/sound/score.py` carves 0.9-4.5 kHz in the bed's mid channel under speech [I13]: the right method. The depth is the
  creator's ear (the house setting is in the standard).

### 3.6 Stems

- Fast, low-register music masks speech most [P-S22 B], so thin drums and bass under dense lines and bring the full mix back for
  montages and reveals (inference from P). Music made in code can be rendered as stems from the start.
- iZotope RX 12's Music Rebalance splits any finished track into vocals, bass, percussion and other [N29 A].
- **Never** apply this to real clips: a clip's voice stripped from its music sounds weird (the house rule) [I11].

### 3.7 Music in Shorts

- Beds sit 10-20 LU under the voice (Shorts batch 2) and 8-18.5 LU under (batch 3; one Short has no music) [I5, I6].
- On our own first Short, a bed ~22 LU under read as too quiet to its reviewer (the house Shorts level is in the standard: the voice
  ~17-18 dB over the music) [I7].
- Some Shorts run a loud bed with no ducking and a music-only montage (LrCU) [I5].
- A music-driven Short cuts on the beat; narrated ones don't [I5, I6].

---

## 4. The narration chain, loudness and translation

### 4.1 What an ElevenLabs voice brings (measured on our takes)

- **Format:** the API defaults to 128-kbps MP3 at 44.1 kHz. Per the docs, 192 kbps needs the Creator tier and PCM/WAV at 44.1 kHz the
  Pro tier [N17 A] (measured: `wav_48000` worked on Creator). ElevenLabs Studio can normalize to audiobook distributor standards
  [N18 A]. Eleven v4 adds expressive audio tags like [sarcastically] and [long pause] [N19 A].
- **Faults we have measured** [I12]:
  - accent slips into British, whole sections at a time;
  - steady tones under the voice (the "bottle" sound);
  - lines that start or end mid-sound;
  - dropped final t/d/k/p;
  - a stray click before a line;
  - character timings 30-60 ms behind the audio.

  None of these is fixed by EQ or compression. They are take-selection and editing jobs (`tools/dj` tts, `tools/voice/rhotic.py`,
  `tools/voice/voice_patch.py`).
- **AI-vocal practice (C, written for singing):** AI vocals carry more low end than needed (high-pass 80-100 Hz); add presence at
  2-5 kHz only if missing; narrow cuts of 2-4 dB at 800 Hz-1.2 kHz for boxiness; 1-2 dB of air above 8 kHz; 3:1-4:1 compression [N16].
- **Who decides:** audio judgement is the creator's. Measurements propose; the creator's ear decides tone and accent.

### 4.2 The chain's numbers, by source

| Stage | Numbers | Source |
|---|---|---|
| High-pass | 80-120 Hz general vocal; 80-100 Hz for AI voices | C [search excerpts; N16] |
| De-ess | **Sibilance in male voices 3-6 kHz, female 5-8 kHz**; find it with an analyzer | A/B [N15] |
| De-ess | Detector high-passed at ~4 kHz; attack under 1 ms, release ~10 ms; overdoing it makes a lisp; fix the worst esses by hand | B [N12] |
| De-ess | Cubase's de-esser centres: 6 kHz (male), 7 kHz (female) | B [N13] |
| Compressor | 4:1 soft knee, threshold ~-20 dB, ~6 dB maximum gain reduction, fast attack, ~250-ms release | B [N13] |
| Compressor | 2:1-4:1, ~10-ms attack, 50-100-ms release, at most ~5 dB on peaks | B, excerpt [N14] |
| Compressor | 2:1-5:1, 1-3 ms attack, 250-350 ms release, about 4 dB for subtle work | B, excerpt [N14] |
| Compressor | Dialogue: no more than 6 dB of compression; ride clip gain up at the ends of fading phrases instead | C [N11] |
| Bus limiter | No more than ~2 dB of gain reduction | C [N11] |
| Consistency | Dialogue loudness range 7 LU or less (Netflix v1.0) | B [P-S7] |

The full proposed chain is in §9.

### 4.3 Loudness targets

| Target | Integrated | True peak | Source |
|---|---|---|---|
| YouTube playback reference | ≈ -14 LUFS, louder uploads turned down, quieter not turned up | — | B [P-S14] (measured, not published by YouTube) |
| YouTube "content loudness" | The offset from YouTube's reference, in Stats for nerds; not about aiming for -14 LUFS | — | B [N24] |
| Frame.io guide | YouTube tends to shoot for -12 to -14; YouTube releases no exact values | — | C [N25] |
| AES TD1008 (AES77), speech streaming | -18 LUFS | -1 dBTP | B [P-S17] |
| Apple Podcasts | -16 LKFS ±1 | -1 dBFS | A [P-S8] |
| EBU R 128 broadcast | -23 LUFS | -1 dBTP | A [P-S2] |
| ACX audiobooks | RMS -23 to -18 dB, peaks under -3 dB | — | C [N48, excerpt] |
| YouTube upload audio | AAC-LC, 48 kHz, stereo 384 kbps | — | A [P-S12] |

**Shorts:** no YouTube document and no controlled test was found; third-party sites only assert -14 [search excerpts, C]. Unverified.

**Measured masters:**

| Group | Integrated | True peak |
|---|---|---|
| Reference Shorts | -5.3, -6.7, -8.2, -13.3, -20.3 LUFS | three over 0 dBTP [I5] |
| Two Shorts of batch 1 | -15.2 / -15.3 LUFS | [I7] |
| Four long-form references in the niche we studied | -14.8 (the fast commentary reference), -15.9, -16.7 (a top creator in the niche, LRA 5.5), -12.7 | the last at +1.6 dBTP [I2, I15, I16] |
| Three quieter long-form references | -20.0 to -22.7 | [I2] |

**Test (cheap, decisive):** read Stats for nerds' "content loudness" on one of the creator's Shorts (a known -14 to -15 master) and on the
call edit (-5.3). If the call edit shows about +9 dB and is turned down, Shorts are normalized like long videos and hot masters only lose
punch. YouTube refused the watch page to curl, so this needs a read in the creator's own browser.

### 4.4 Balance: voice, music, effects

| Element | Long form | Shorts | Basis |
|---|---|---|---|
| Narration | The anchor: short-term loudness within ±2-3 LU of its median | same | B [P-S7]; ours |
| Music bed, dense narration | 17-22 LU under (refs 19-23) | 10-15 LU under | B [I3, I8, I5, I6, I7] |
| Music bed, hook / big moments / close | 12-15 LU under | 8-12 LU under | B [I2, I5] |
| Duck under speech | 6-8 dB, plus a 3-6 dB carve at 1.5-4 kHz | 6-8 dB | B [I5, I8]; C [N11] |
| Music-only moments (title, montage) | at or 2-4 LU below the narration's short-term level, never more than ~+2 LU over; a card at most ~6 dB over the bed before it | same | A [I10]: a card 19 dB over the bed in one of our builds read as the TV turned to full volume |
| Effects | §2.4 table | louder end of §2.4 | B [I5, I7, I2] |
| Ambience | at least 15 LU under | rarely used | B [P-S19] |

### 4.5 Translation: TV, phone, mono

- **TV first for long form:** 64.7% of a well-performing long video's watch time was on TV (YouTube Studio, its first ~3 days) [I9 A];
  TV is YouTube's main screen in the US by watch time [P-S13 A].
- **Phones:** microspeakers resonate at ~500-700 Hz and lose the sub [P-S39 B]. Booms need harmonics (150 Hz-2 kHz), which
  `tools/sound/score.py` adds [I13, P-S38].
- **Mono and phones lose panning** [N4 C], so impacts and the voice stay centred; only whooshes may pan with motion (inference).
- **Players change the mix:** Stable volume (on by default) narrows loud/quiet contrast, and Voice boost lowers background sound for
  viewers who turn it on [P-S10, P-S11 A].

---

## 5. Original-audio clips inside a video (the source's own videos, TV, streams)

**Evidence:**
- **The house rule** (`standard/SOUND_AND_VOICE.md`): a clip plays its real audio, its music included; never separated or carved (a
  separated voice sounds weird); subtitled "Name: line"; no sound running past the shot shown; the speech in a clip's own sound is never
  censored [I11 A].
- **One of our builds' clip-audio code** [I14]: each clip's own audio from the shown range, 30-ms fades, levelled to -16 LUFS integrated,
  the bed dipped out under it; only 1x-speed moments carry sound.
- **A well-performing long video of ours:** six real voices (TV news, a sketch show, an animated series, a politician, an official, a
  magazine); the music steps from 10 to 15 dB under over ~0.15 s inside the narration pause and back as the narration returns; the voices
  measured 10.5-19.2 dB over the music in the speech band; each voice synced to its picture's frame (QA found 51-150 ms drifts, fixed) [I8].
- **References:**
  - a top creator in the niche we studied: its most replayed moment (1.00) is a user's own clip in its own sound; it also holds
    30-s voiceless stretches of other people's clips [I15].
  - the industry-analysis reference runs financial-news soundbites over a 14-s music-only title break [I3].
  - a news Short in the niche brings meme clips' own audio in on the cut [I5].
  - a longer documentary's 15-s scene in its own sound sits at 0.84 replay [I2].

**Practice (C):** dialogue joins get short equal-power crossfades (room-tone fills under ~20 ms); room-tone pieces under ~10 frames cause
problems [P-S49; search excerpts].

**For us:**
1. Level each clip by its **speech**, not its whole: measure short-term loudness only where the clip's voice is active, and match it to
   within ±2 LU of the narration's median. An integrated -16 LUFS level can leave a quiet line under loud music in the clip.
2. If the clip's music peaks over the speech, a gentle peak limiter on the clip (no EQ, no stem stripping).
3. The bed dips ≥15 LU under the clip's speech or out entirely, the ramp inside the narration pause (100-150 ms). (House setting: about
   32 dB under the speaker.)
4. Clip edges: 10-30-ms fades, audio starts and ends with its picture.

---

## 6. Libraries and tools: prices and roles

*Prices at the time of research; re-check before buying. For music the house route is the creator's own tracks or music made in code
(`standard/MUSIC.md`): these libraries matter here for effects. The house effects set (`assets/house_sfx.zip`) covers the recurring
jobs already.*

### 6.1 Sound libraries

| Library | Price | What it gives | Source |
|---|---|---|---|
| Artlist (stock) | Music $16.58/mo, **Music & SFX $24.92/mo** billed annually; Max (AI + stock) separate | Music + SFX, 1 channel per platform (personal) | A vendor [N36] |
| Envato (Core) | €14.50/mo annual, €29 monthly | Unlimited downloads of 29M+ assets incl. music and SFX; lifetime licence for stock | A [N37] |
| Motion Array (Everything) | $24.99/mo annual, $39.99 monthly (excl. VAT) | Music, SFX, templates, plugins | A vendor [N39] |
| Splice | Creator $19.99/mo (~200 downloads; $4.99 first month); Sounds $12.99/mo yearly (~100) | 3M+ music-production samples (some FX); credits | A [N38] |
| Soundly Pro | price drawn as an image on the site, not read; older third-party figure $14.99/mo | Cloud library of **250,000 sounds**, strong local-library search; free tier 3,000+ | A features [N40]; C price |
| BOOM Library, Cinematic Trailers Designed | ~$113 (Best Service); Designed 2 ~$170 | 150+ designed impacts, whooshes, transitions, rises; 96 kHz / 24-bit | C retailer [N42] |
| **Sonniss GDC bundles** | **free**, no attribution | the latest bundle 7.47 GB+; archive of nine years, 200 GB+; media production only, no AI training | A [N41] |
| Freesound | free | CC0 (anything), CC BY (credit required), CC BY-NC (**no commercial use**: unusable on a monetized channel) | A [N43] |
| ElevenLabs Sound Effects v2 | 40 credits per second when a duration is set | Text-to-SFX up to 30 s, looping, 48 kHz | A [N20]; B [N20] |

### 6.2 Plugins (all usable offline from Python through pedalboard, if they load: §6.3)

| Plugin | Price | Role | Source |
|---|---|---|---|
| **iZotope RX 12** | Elements $99 · **Standard $399** · Advanced $1,399 | De-click, de-hum, de-clip (all editions); **spectral de-ess, Breath Control, Music Rebalance** (Standard+); Dialogue Isolate; Scene Rebalance (Advanced) | B prices [N28]; A features [N29] |
| iZotope Neutron 5 / Ozone 12 | $299 / $55-$499 | Mixing assistant / mastering suite; not needed (the master is gain + true-peak limiter) | A [N30] |
| FabFilter Pro-Q 4 / Pro-C 3 / Pro-L 2 / Pro-DS / Pro-MB | **€169 each**; Total bundle €899 | Dynamic EQ, compressor, true-peak limiter, de-esser: the standard for transparency; 30-day trial | A [N31] |
| TDR Nova | free (GE paid) | Parallel dynamic EQ, 4 bands + filters: a free de-esser/carver | A [N32] |
| Wavesfactory Trackspacer | €59 (list €79.20) | Automatic inverse-EQ carve from a sidechain | A [N33] |
| sonible smart:EQ 4 | €129 | AI tonal balance; cross-channel unmasking of up to 10 tracks | A [N34] |
| Airwindows | free, open source | Large free plugin set; not evaluated here | (page read, not assessed) |
| DaVinci Resolve 21 | free; Studio $295 | Fairlight; Ducker track FX (since 19); Fairlight Animator (an audio track drives Fusion animation) | B [N27]; C [N26] |

### 6.3 Python and ffmpeg equivalents (and their traps)

| Tool | Role | Trap or note | Source |
|---|---|---|---|
| **pedalboard** (Spotify) | Reads/writes WAV/FLAC/MP3; built-in Compressor, Limiter, HighpassFilter, Convolution, Reverb, Gain; **hosts VST3 plugins on Windows**; releases the GIL | FabFilter plugins worked in the maintainer's tests (2022); iZotope RX 10 Spectral Denoise is listed working on macOS, **Windows unknown**; sidechain input for VST3 unverified | A [N22] |
| **pyloudnorm** | ITU-R BS.1770-4 integrated loudness | No true peak: use ffmpeg `ebur128=peak=true` | A [N23] |
| ffmpeg `loudnorm` | EBU R128 normalisation | Defaults I=-24, LRA=7, TP=-2; linear mode needs all four `measured_*` values and **silently falls back to dynamic** if the target LRA is below the source's or the gain would break TP; upsamples to 192 kHz internally (set `-ar`) | A [N21] |
| ffmpeg `alimiter` | Look-ahead limiter | **`level` is on by default and normalises the output to 0 dB**: set `level=disabled` (score.py does) | A [N21] |
| ffmpeg `amix` | Mixing | **`normalize` is on by default and scales inputs**: use `normalize=0` and set weights | A [N21] |
| ffmpeg `sidechaincompress` | Ducking | Ratio 2, attack 20 ms, release 250 ms, RMS detection by default | A [N21] |
| ffmpeg `adynamicequalizer`, `deesser` | Dynamic EQ (de-ess, keyed carve), simple de-esser | | A [N21] |
| ffmpeg `ebur128`, `afftdn`/`arnndn`, `asubboost`/`aexciter`, `dialoguenhance` | Metering, denoise, harmonics, stereo-to-3.0 dialogue lift | | A [N21] |

---

## 7. What makes sound design feel premium vs cheap

**Premium (evidence or broad agreement):**
1. **Every sound has a reason.** What matters is not which effects you add but why [N1]. Measured: sounds land on visible events and
   new information, not on plain cuts [I5, I6, I1].
2. **One style per video, one sound world for the music** [N3; I10 A].
3. **Designed, layered big moments** (low + mid + bright; riser + impact) rather than one stock file [N3, N4, N2].
4. **Frame-exact placement**, sub-frame on impacts [N6, P-S32].
5. **A believable bed:** ambience or air under the voice, no dead air, room tone where a stop isn't designed [N6, P-S49].
6. **Contrast:** quiet before loud, music out before the point [N1, I2, I5, P-S32].
7. **The voice always wins:** music at least 10-15 LU under, carved rather than only turned down, no lyrics [P-S19, P-S21, N11].
8. **Steady loudness:** no section or card jumping out (a card +19 dB in one of our builds) [I10].
9. **Music edits on the beat and phrase**, ending on a button or a reverb tail, never mid-phrase fades [P-S33, N3].
10. **Translation:** booms that survive TV and phone speakers; nothing that cancels in mono [P-S38, I10].
11. **Variation (practice):** 3-10 versions per category, never the same file twice in a row [N5; inference]. The house standard holds
    one sound per recurring action instead (§2.2).

**Cheap (evidence or broad agreement):**
1. **A whoosh on every cut**: mechanical. Plain cuts carry sounds only at chance in good Shorts [I5, I6]; vendor guides warn the same
   [N47, search excerpts C].
2. **Random sounds from mixed packs** (style clash) [N3]; downloading thousands of files and hunting a "perfect" sound for every
   moment [N2].
3. **Music competing with the voice**, or lyrics under speech (the BBC's *Wonders of the Universe* complaints) [P-S45, P-S21].
4. **Hype devices outside the sound world** (in one of our builds: a drop, a newsroom ident, a sad-piano jump) [I10].
5. **Level jumps and over-loud masters.** Hot Shorts masters clip (+3.7 to +4.1 dBTP in two references) and, if normalized, gain
   nothing [I5, P-S14]; one of our builds, whose loudest 3 s hit -9.4 LUFS, hurt the ears in review [I10].
6. **Sub-only booms that vanish on TV speakers**; whooshes landing late (one of our builds: effects 0.06-0.9 s late) [I10].
7. **Pumping ducks and dead air** (music popping up in every breath; silence that sounds like a dropout) [N26, P-S49].
8. **Overused meme sounds where the moment isn't a joke.** Opinion: no source measures it; the house censor (a meme bass-boost hit)
   shows memes are fine when they are the joke [I10].

---

## 8. Recommended SFX categories (54)

*Build: the house set (`assets/house_sfx.zip`, its `manifest.json` names each sound by job; in a cue sheet `pal('<job>')`) covers the
jobs named in the last column. For a job it lacks, candidates come from the creator's own effects, a licence-clear library (§6.1) or a
sound made in code, and go through the creator's Sound Test (`standard/SOUND_AND_VOICE.md`; the method's evidence:
`standard/research/SFX_TASTE.md`). Per file, store its measured impact time, tail length, peak short-term loudness and whether it is
sub-heavy (so `tools/sound/score.py` can add harmonics). Levels are vs the voice (§2.4); the house set's own levels are in its
manifest.*

| # | Category | What it is for | Search term | Level | House sound |
|---|---|---|---|---|---|
| **Transitions and motion** | | | | | |
| 1 | Whoosh, short air (0.2-0.5 s) | Text, cards and graphics sliding in; small pans | "whoosh short air" | -10 to -14 | `chapter_card` (a soft airy whoosh on a card) |
| 2 | Whoosh, heavy cinematic (0.6-1.5 s) | Big camera moves toward the lens; chapter-level transitions | "whoosh deep cinematic" | -8 to -12 | — |
| 3 | Whip / swish (≤0.25 s) | Whip pans, fast cuts, comic snaps | "whip swish fast" | -8 to -12 | `whoosh_fast` (only on a real flight) |
| 4 | Whoosh-into-hit (designed transition) | A cut that must land on a new named thing | "riser transition" + "impact" | -6 to 0 | — |
| 5 | UI swipe / slide | UI panels, cards, menus, page scrolls | "UI swipe slide" | -12 to -18 | — |
| 6 | Reverse / suck-back | Pulling into a hit or the next scene; "rewinding" to a past event | "reverse cymbal, reverse whoosh" | -8 to -12 | — |
| 7 | Tape stop / power-down | A story or the music grinding to a halt ("the deal is off") | "tape stop" | -6 to -10 | — |
| 8 | Record scratch | A comic stop on a contradiction | "record scratch" | -6 to -10 | — |
| 9 | VHS rewind / fast-forward | Flashbacks ("back in 1998"); time skipping | "rewind VHS", "fast forward" | -10 to -14 | `fast_forward` (time skipping forward, quiet) |
| **Build and payoff** | | | | | |
| 10 | Short riser (0.5-2 s) | Into a reveal, an answer, a number | "riser short" | ends -6 to 0 | — |
| 11 | Long riser (3-10 s) | Cold-open build into the title | "riser long" | ends -6 to 0 | — |
| 12 | Low rumble riser | Felt more than heard; tension under a question | "riser low rumble" | -10 | — |
| 13 | Swell (pad, reverse swell) | A soft lift into a calm reveal or a new chapter | "swell" | -10 to -14 | — |
| 14 | Tension drone | Under a mystery or a dark turn when the music stops | "drone tension" | -18 to -24 | — |
| 15 | Braam / trailer horn | The one biggest reveal of a video (at most one) | "braam" | 0 to +3 | — |
| **Impacts** | | | | | |
| 16 | Low boom, clean sub + tail | Dates, names, reveals, chapter cards, the last word | "boom sub" | 0 to +3 | `reveal_boom` (a big reveal; pure sub) |
| 17 | Cinematic hit | A claim, a text slam, a striking new shot | "cinematic impact" | -6 to 0 | `cinematic_hit`; `bass_drop` (the one statement drop) |
| 18 | Stinger (one per video, reused) | The chapter-card sound brand; the title | "stinger" | music-only, by ear | `black_cut` (a low stinger on a cut to black) |
| 19 | Sub drop | A drop to black, a "this changes everything" beat (needs harmonics) | "sub drop" | 0 to +3 | `bass_drop` |
| 20 | Punch / thud | Literal hits, "slammed", knock-out gags | "punch impact" | -6 to 0 | `stamp` (lands like a low punch) |
| 21 | Metal / door slam | Something shut down, cancelled, locked; a lawsuit | "metal slam, door slam" | -6 to 0 | — |
| 22 | Glass shatter | "Broke records", "shattered" | "glass break" | -6 to 0 | `glass_shatter` |
| 23 | Flash / strobe pop | Archival photo strobes, paparazzi, a white flash frame | "camera flash" | -10 to -14 | `flash_open` (a Short's frame 0 only) |
| **Graphics and UI** | | | | | |
| 24 | Pop (small) | Icons, avatars, list items, covers popping in | "pop UI" | -8 to -12 | `pop` |
| 25 | UI click | Buttons, toggles, CTA animations | "UI click" | -10 to -14 | `click` |
| 26 | Mouse click | The cursor clicking real web pages and posts | "mouse click" | -12 to -16 | `click` |
| 27 | Typing / typewriter / spacebar | Text typed on screen, search bars, intro word reveals | "typing keyboard" | -15 to -22 | `typing_keyboard` (cut to the typing), `key_press` |
| 28 | Notification / message | Posts, DMs, chat messages, alerts appearing | "phone notification" | -10 to -14 | `notification`; `join` (someone joining a call or chat) |
| 29 | Ping (arrow callout) | Arrows on a detail (the house ping) | "ping, UI ding" | -10 to -14 | `ping` |
| 30 | Highlighter / marker | Highlighting a quoted phrase; lines drawn | "marker pen stroke" | -14 to -18 | `marker`; `writing` (a pen stroke) |
| 31 | Paper slide / page turn | Documents, articles, patents, court filings | "paper handle, page turn" | -14 to -20 | `paper` |
| 32 | Stamp | "CONFIRMED", "FAKE", label slams | "stamp" | -8 to -12 | `stamp` |
| 33 | Camera shutter | Screenshots, photos, a selfie | "camera shutter" | -10 to -14 | `camera` |
| 34 | Digital counter / ticks | Numbers running up (sales, views, years) | "digital counting, data" | -16 to -20 | `count_up` (cut to the count); `number_land` |
| 35 | Cash register / coins | Money figures on screen | "cash register" | -10 to -14 | `money` |
| 36 | Data / scanner / computing | Data processing, code on screen | "computer data processing" | -16 to -20 | — |
| 37 | Error / denied buzzer | "Wrong", a debunk, a fake claim | "error alert" | -10 to -14 | `error`; `fail` (a verdict that something failed) |
| 38 | Glitch | Corrupted files, "the internet broke", glitch transitions | "glitch" | -8 to -12 | `glitch`; `glitch_slam` (a word slamming in) |
| 39 | TV static / channel switch | Cutting into TV clips, old footage | "TV static, channel switch" | -10 to -14 | — |
| 40 | Bass-boost censor hit | Censoring a swear in the narration (`tools/sound/censor.py`) | "bass boost meme" | -6 | `bass_drop` (the censor's default) |
| **Human and reaction** | | | | | |
| 41 | Crowd gasp | A shocking reveal (sparingly, with irony) | "crowd gasp" | -10 to -14 | — |
| 42 | Crowd cheer / applause | Records, launches, a win | "crowd applause" | -10 to -14 | — |
| 43 | Crowd walla / murmur | "Everyone's talking about it"; event footage | "crowd walla" | -18 to -24 | — |
| 44 | Short laugh | Irony beats (rare) | "audience laugh short" | -12 to -16 | — |
| 45 | Heartbeat | The wait before a payoff (rare) | "heartbeat" | -12 to -18 | — |
| 46 | Clock tick / countdown | Deadlines, long waits, countdowns | "clock ticking" | -14 to -20 | — |
| 47 | Phone ring | A phone ringing on screen | "phone ring soft" | -10 to -14 | `phone_ring` (soft, never shrill) |
| **Ambiences and beds** | | | | | |
| 48 | City ambience (day, night) | City B-roll and real-world shots | "urban ambience" | -18 to -25 | — |
| 49 | Office / studio ambience | Office or studio footage, "inside the company" | "office ambience" | -18 to -25 | — |
| 50 | Convention / event crowd | Premieres, trade-show footage | "crowd walla convention" | -18 to -24 | — |
| 51 | Room tone / quiet interior air | Under a music stop where the voice goes on (no dead air) | "room tone interior quiet" | ≥ -25 (≥15 LU under) | — |
| 52 | Wind / night air | Mood under mystery or an empty landscape | "wind night ambience" | -20 to -26 | — |
| 53 | Sirens / helicopter (distant) | City flavour under B-roll | "police siren distant" | -18 to -24 | — |
| 54 | Car pass-by / engine / skid | Vehicles on screen without their own sound | "car pass by" | -10 to -16 | — |

---

## 9. The narration processing chain the research proposed, with numbers

*Proposals from the sources above, to be A/B'd by the creator's ear before any becomes a default. The house chain is different: the
voice stays dry (no de-esser, no EQ chain) and goes to loudness through chain D (`standard/SOUND_AND_VOICE.md`, "Voice: the bar").*

| # | Stage | Setting | Why / source |
|---|---|---|---|
| 0 | Generate | **PCM** if the plan allows, else MP3 192 kbps, never the 128-kbps default; resample to 48 kHz once (soxr). (Measured: `wav_48000` works on Creator) | [N17 A]; YouTube audio 48 kHz [P-S12] |
| 1 | Take QA | The existing checks: accent (`tools/voice/rhotic.py`, `tools/voice/accent_id.py`), steady tones, edge faults, dropped endings, lead clicks; Shorts: no gap over 0.18 s | [I12] |
| 2 | Section level match | Each section to the same speech-gated loudness (e.g. -20 LUFS ±0.5) **before** joining; joins in measured silence with 10-20 ms fades | TTS takes vary between requests (ours); [I12] |
| 3 | High-pass | 70-80 Hz, 18-24 dB/oct (male clone; keeps chest weight, removes rumble) | C [N16; excerpts]; SOS bass roll-off [N13] |
| 4 | Corrective EQ | Only by measurement against a reference narration the creator approved: -2 to -3 dB at 250-400 Hz if muddy; -2 to -4 dB narrow at 0.8-1.2 kHz if boxy; +1 to +2 dB at 3-5 kHz only if the voice sinks on TV speakers; nothing over ±4 dB | C [N16]; ANSI weights [P-S27] |
| 5 | De-ess | Split-band at ~4-7 kHz (male sibilance 3-6 kHz), detector high-passed ~4 kHz, attack <1 ms, release ~10 ms, 3-6 dB only on the worst esses (stop before the lisp) | A/B [N15, N12] |
| 6 | Compression | 3:1 soft knee, attack ~10 ms, release 80-150 ms, 3-5 dB on peaks (never over 6) | B [N13, N14]; C [N11] |
| 7 | Phrase gain riding | Offline: keep the voice's 3-s short-term loudness within ±2 LU of its median (narration LRA ≤ 5 LU; Netflix's dialogue limit is 7) | B [P-S7]; C [N11] |
| 8 | Space | Dry: no reverb, no added room on the narration | Documentary/YouTube narration convention (opinion); avoids an "AI in a room" effect (unverified) |
| 9 | Mix | Beds and effects per §4.4; duck 6-8 dB with 100-150 ms lead, carve 3-6 dB at 1.5-4 kHz in the bed's mid | §3.4-3.5 |
| 10 | Master | Linear gain to **-14.0 LUFS ±0.5**; true-peak limiter at **-1.0 dBTP**, 4x oversampled, at most ~2 dB of gain reduction (`level=disabled`) | B [P-S14]; C [N11]; [N21] |
| 11 | Verify | `ebur128=peak=true` **after** the AAC encode (codecs can overshoot); report integrated, LRA, max short-term, true peak; mono fold-down check | [P-S17]; [N21] |
| 12 | Encode | AAC-LC 48 kHz stereo at **384 kbps** | A [P-S12] |

**ffmpeg sketch of 3-6** (starting values to A/B, not a verdict):
`highpass=f=75:p=2,highpass=f=75:p=2,adynamicequalizer=dfrequency=5500:dqfactor=1.5:tfrequency=6000:tqfactor=1:attack=1:release=10:threshold=<set from measure>:ratio=3:range=6:mode=cutabove,acompressor=ratio=3:attack=10:release=120:threshold=<-18 to -22 dB>:knee=4`
(pedalboard + FabFilter Pro-DS / Pro-C 3 is the paid alternative if an A/B prefers it).

---

## 10. Tools worth paying for (prices, why), ranked

1. **iZotope RX 12 Standard, $399** (Elements $99 lacks spectral de-ess and Breath Control) [N28, N29].
   - Why: TTS faults (steady tones, clicks, harsh esses) are hand-repaired otherwise; RX's de-hum, de-click, spectral repair and spectral
     de-ess do it better than notch filters (measured: wide notches thinned the voice 1.5-8 dB).
   - Music Rebalance makes stems from any track, for thinning a bed under dense narration.
   - Its batch processor runs without a DAW.
   - Before buying: test on Windows in the trial, standalone and through pedalboard (Windows compatibility unknown).
   - (The house rule for a fault heard in a take is a regeneration, never a repair tool; RX would serve the creator's own recordings.)
2. **FabFilter Pro-DS + Pro-Q 4 + Pro-L 2, €507** (or Total €899) [N31].
   - Why: the most transparent de-essing, a dynamic EQ for a keyed carve, and a true-peak limiter.
   - Buy **only if** a blind A/B against the ffmpeg/numpy chain wins with the creator; the offline tools already do the same jobs.
   - 30-day trial; pedalboard has run FabFilter plugins in the maintainer's tests [N22].
3. **A designed cinematic SFX set, ~$113-170** (BOOM Cinematic Trailers Designed or Designed 2) [N42].
   - Why: the "premium" difference is concentrated in impacts, booms and risers.
   - Buy only if the house set and the free libraries sound generic.
   - Try the **free Sonniss GDC archive first** (200 GB+, royalty-free, no attribution) [N41].
4. **Soundly Pro (~$15/mo, unverified)** [N40]: only if searching a growing local library becomes the bottleneck.

**Not worth it now:**
- Artlist, Envato, Motion Array: their effects duplicate the house set and the free libraries; music is the creator's own or made in code.
- Splice: music-production samples.
- Ozone 12, Neutron 5: the master is gain + limiter; the mix already carves.
- Trackspacer, smart:EQ 4: automatic carving already done offline. Reconsider if the creator's ear hears the carve.
- Resolve Studio ($295) for Voice Isolation: it would strip clip music, which the house rule on real clips forbids.
- Freesound CC BY-NC sounds: not usable on a monetized channel.

---

## 11. Reference videos to study for sound

| # | Video | URL | Why |
|---|---|---|---|
| 1 | LEMMiNO, "Cicada 3301: An Internet Mystery" | https://www.youtube.com/watch?v=I2O7blSSzpI | The restraint pole: ~5 effects in 18 min and one branded chapter sting; music changes carry structure [I4] |
| 2 | Kurzgesagt, "We Finally Know More About Humanity's First Civilization" (2026) | https://www.youtube.com/watch?v=_y9JuojAIg0 | Composed score and sound effects on every motion-graphic move (Epic Mountain); the studio's own advice is to listen on headphones for the effects layer [N7, N8] |
| 3 | melodysheep, "TIMELAPSE OF THE FUTURE: A Journey to the End of Time" | https://www.youtube.com/watch?v=uD4izuDMUQA | Music, writing, edit and effects by one creator (per its description), 113M views: how score and sound carry scale with little narration; study its builds and stops |
| 4 | A call-edit Short (5eu7) | https://www.youtube.com/shorts/5eu7hfl5nNI | Picked as a reference for its animations, effects and music timing: ~14 effects a minute, a hit on 11 of 13 colour flashes, the silence punchline (1.9 s dry, back 13 ms after the whip) [I5] |
| 5 | A cat explainer Short (s1c1) | https://www.youtube.com/shorts/s1c1m9UB0cg | Picked for its effect use: effects illustrate words (shatter 22 ms after "loud", heart pop 29 ms after "love"), effects +1 to +4 dB over the voice [I5] |

**Also worth one pass:**
- **Two breakdowns that solo each layer** (watch with the sound on and off):
  - Tim Runia: https://www.youtube.com/watch?v=JOm_EqBoW0M [N2].
  - Clumzzy: https://www.youtube.com/watch?v=rwI5u8hMHqs [N5].
- **The creator's own niche:** the fast commentary, industry-analysis and story references above were measured in the niche we studied;
  the chat measures the same things (effects a minute confirmed by eye, bed levels, cut-outs, loudness) on the creator's own top
  references before the first video.

---

## 12. Open questions and tests (none decided here)

1. **Shorts loudness normalization** (§4.3): Stats for nerds on one of the creator's Shorts and on the call edit. Needs a read in the
   creator's own browser.
2. **Confirm by eye** the two dense references' effect counts (only machine candidates exist) and count a well-performing long video's
   first minute against its body, to set the front-loading ratio.
3. **A/B the proposed narration chain** (§9) against the house chain on two 30-s passages, the creator's ear deciding; measure first how
   the ElevenLabs voice's long-term spectrum differs from a reference narrator's.
4. **Trial RX 12 Standard and FabFilter** on Windows (standalone and pedalboard); keep only what wins a blind A/B.
5. **A job the house set lacks** (§8): the creator's Sound Test, each pick's measured impact, tail and loudness logged.
6. YouTube transcripts that the bot check blocked (HqPDRa7i97s "Master Viral Sound Design for Short-Form Content", 98CzEo5PIZ4
   "Everything You Need to Know About Sound Design in 2025", G7cKyq8BWek, 9jBic4IDfxA, JPDhd2c1Iro, OvKr6loCciE) can be read later for
   more Shorts practice.

---

## Sources

*"Excerpt" = seen only in a search result, not fetched. "Current page" = an undated page, read as it stood at the time of research.
Sources from the stock-music vendor are described without a link.*

### External sources

| # | Title | URL | Date | Grade |
|---|---|---|---|---|
| N1 | A stock-music vendor's channel with an editor, "Mastering Sound Effects in Video Editing: A 3-Step Sound Design Guide" (transcript) | (vendor channel) | 2026-04-24 | C (vendor channel) |
| N2 | Tim Runia, "The ONLY 3 Sound Effects You Need to Tell Any Story" (transcript) | https://www.youtube.com/watch?v=JOm_EqBoW0M | 2026-03-04 | C (sells a pack) |
| N3 | Herman Huang, "3 Sound Design Secrets That Feel Like CHEATING" (transcript) | https://www.youtube.com/watch?v=tzfzkTAQsnE | 2025-04-02 | C (sponsored) |
| N4 | Artlist, "How To SOUND DESIGN | Step by step tutorial" (transcript) | https://www.youtube.com/watch?v=8LV1bqf8ZVo | 2020-03-30 | C |
| N5 | Clumzzy, "How to Sound Design Viral Youtube Videos" (transcript) | https://www.youtube.com/watch?v=rwI5u8hMHqs | 2025-12-04 | C (sells coaching) |
| N6 | Austen Menges, "21 years of pro sound design knowledge in 72 mins" (transcript; broadcast commercial editor showing his own spots) | https://www.youtube.com/watch?v=s__fJSUZJfg | 2026-04-04 | B |
| N7 | Kurzgesagt, "How to Make a Kurzgesagt Video in 1200 Hours" (transcript) | https://www.youtube.com/watch?v=uFk0mgljtns | 2020-02-16 | A (own process) |
| N8 | P. Mosca (Kurzgesagt), Internetdagarna talk (transcript; her "30-40% higher impact" for composed music is unverifiable) | https://www.youtube.com/watch?v=Qy4OARwQuC8 | 2018-11-20 | A (process) / C (the figure) |
| N9 | A stock-music vendor's blog, "Audio mixing for video: What you need to know" | (vendor blog) | 2023-05-25 (mod. 2026-03-30) | C |
| N10 | A stock-music vendor's blog, "Transition between songs in your video" | (vendor blog) | 2022-08-23 (mod. 2024-08-26) | C |
| N11 | iZotope, "Mixing Audio for Video, Part 4: Mixing Techniques" | https://www.izotope.com/en/blog/mixing/mixing-audio-for-video-part-4-mixing-techniques.html | 2018-10-22 | C (vendor; practitioner author) |
| N12 | Sound On Sound, "Techniques For Vocal De-essing" | https://www.soundonsound.com/techniques/techniques-vocal-de-essing | 2009-05 | B |
| N13 | Sound On Sound, "Vocal Processing" (Cubase) | https://www.soundonsound.com/techniques/vocal-processing | 2008-12 | B |
| N14 | Sound On Sound, vocal compression guidance (two pages; which numbers belong to which page is unverified) | https://www.soundonsound.com/sound-advice/q-how-should-set-my-compressor-recording-vocals ; https://www.soundonsound.com/techniques/compressors | n.d. | B (excerpt) |
| N15 | Apple Support, "Reduce sibilance in Logic Pro for Mac" | https://support.apple.com/en-ae/102006 | ©2026 | A (product) / B (frequency claim) |
| N16 | Sonarworks, "Mastering AI vocals: EQ and compression tips" (written for AI singing) | https://www.sonarworks.com/blog/learn/mastering-ai-vocals-eq-and-compression-tips | n.d. | C |
| N17 | ElevenLabs API reference, Text to Speech (output formats and tiers) | https://elevenlabs.io/docs/api-reference/text-to-speech/convert | current page | A |
| N18 | ElevenLabs blog, "Audio normalization in Studio" | https://elevenlabs.io/blog/audio-normalization-in-projects | 2023-10-28 (upd. 2026) | A |
| N19 | ElevenLabs blog, "How to make text to speech sound less robotic" (Eleven v4 audio tags) | https://elevenlabs.io/blog/how-to-make-text-to-speech-sound-less-robotic | current page | A (product) |
| N20 | ElevenLabs docs, Sound effects; The Decoder, "ElevenLabs releases version 2 of its AI sound effects model" | https://elevenlabs.io/docs/capabilities/sound-effects ; https://the-decoder.com/elevenlabs-releases-version-2-of-its-ai-sound-effects-model-with-longer-clips-and-better-audio-quality/ | current page ; 2025-09-02 | A ; B |
| N21 | FFmpeg Filters Documentation (loudnorm, alimiter, amix, sidechaincompress, adynamicequalizer, deesser, ebur128) | https://ffmpeg.org/ffmpeg-filters.html | current page | A |
| N22 | Spotify pedalboard: README, COMPATIBILITY.md, issues #103 (FabFilter, 2022-05) and #390 (2025-01) | https://github.com/spotify/pedalboard ; https://github.com/spotify/pedalboard/issues/103 | current page | A / B |
| N23 | pyloudnorm README | https://github.com/csteinmetz1/pyloudnorm | current page | A |
| N24 | I. Shepherd, Production Advice, "YouTube Stats For Nerds" | https://productionadvice.co.uk/stats-for-nerds/ | 2017-09-29 | B |
| N25 | Frame.io Workflow Guide, "Loudness for Youtube" | https://workflow.frame.io/guide/loudness-for-youtube | ©2021 | C |
| N26 | tryuncle.com, "How to duck background music under dialogue in DaVinci Resolve" (Resolve 21.0.2; quotes the manual's compressor defaults) | https://tryuncle.com/learn/davinci-resolve/how-to-duck-background-music-under-dialogue-in-davinci-resolve | 2026-07 | C |
| N27 | CG Channel, "Blackmagic Design releases DaVinci Resolve 21.0" | https://www.cgchannel.com/2026/06/blackmagic-design-releases-davinci-resolve-21-0/ | 2026-04-14 (upd. at stable, 2026-06) | B |
| N28 | KVR Audio, "iZotope releases RX 12" | https://www.kvraudio.com/news/izotope-releases-rx-12-66802 | 2026-05-03 | B |
| N29 | iZotope, RX 12 product page (modules by edition) | https://www.izotope.com/en/products/rx.html | current page | A |
| N30 | iZotope store, dynamics collection (Ozone 12, Neutron 5 prices) | https://www.izotope.com/collections/dynamics | current page | A |
| N31 | FabFilter shop | https://www.fabfilter.com/shop | current page | A |
| N32 | Tokyo Dawn Records, TDR Nova | https://www.tokyodawn.net/tdr-nova/ | current page | A |
| N33 | Wavesfactory, Trackspacer | https://www.wavesfactory.com/audio-plugins/trackspacer/ | current page | A |
| N34 | sonible, smart:EQ 4 | https://www.sonible.com/smarteq4/ | mod. 2026-07-28 | A |
| N36 | Artlist blog, "Artlist pricing plans explained" | https://artlist.io/blog/artlist-pricing-and-plans-explained/ | mod. 2026-06-11 | A (vendor) |
| N37 | Envato pricing | https://elements.envato.com/pricing | current page | A |
| N38 | Splice plans | https://splice.com/plans | current page | A |
| N39 | Motion Array blog, "Which Motion Array plan is right for you?" | https://blog.motionarray.com/learn/motion-array/motion-array-plans/ | 2024-10-14 (mod. 2025-07-31) | A (vendor) |
| N40 | Soundly home page and subscription FAQ (price drawn as an image, not read; $14.99/mo from older third-party coverage) | https://getsoundly.com/ ; https://getsoundly.com/faq/what-are-the-differences-between-the-subscriptions/ | current page | A / C (price) |
| N41 | Sonniss, GameAudioGDC archive and the latest GDC audio bundle | https://sonniss.com/gameaudiogdc ; https://gdc.sonniss.com/ | current page | A |
| N42 | Best Service, BOOM Library "Cinematic Trailers - Designed" | https://www.bestservice.com/en/cinematic_trailers_designed.html | current page | C (retailer) |
| N43 | Freesound FAQ (licences) | https://freesound.org/help/faq/ | current page | A |
| N45 | Short-form editing vendor blogs (virlo.ai, capcut.com, clipcreator.ai, autoshorts.app) | e.g. https://virlo.ai/blog/short-form-video-editing-tips | 2025-2026 | C (excerpt) |
| N46 | Tubefilter, "MrBeast says to stop using his editing style" (cut counts) | https://tubefilter.com/2024/03/04/mrbeast-editing-style-number-of-cuts-per-video/ | 2024-03-04 | B (excerpt) |
| N47 | A stock-music vendor's pages, "Sound effects for YouTube videos" / "Transition sound effects" | (vendor pages) | n.d. | C (excerpt) |
| N48 | Auphonic blog, "RMS loudness normalization for Audible ACX" | https://auphonic.com/blog/2026/01/15/rms-loudness-normalization-for-audible-acx/ | 2026-01-15 | C (excerpt) |

### Sources reused from the earlier pass (P)

| # | Title | URL | Date | Grade |
|---|---|---|---|---|
| P-S1 | ITU-R BT.1359-1, relative timing of sound and vision | https://www.itu.int/rec/R-REC-BT.1359-1-199811-I/en | 1998-11 | A |
| P-S2 | EBU R 128 (V5) | https://tech.ebu.ch/docs/r/r128.pdf | 2023-11 | A |
| P-S7 | Production Expert on Netflix's loudness spec v1.0 | https://www.production-expert.com/home-page/2018/8/23/has-netflix-turned-the-clock-back-10-years-or-is-their-new-loudness-delivery-spec-a-stroke-of-genius | 2018-08-30 | B |
| P-S8 | Apple Podcasts, audio requirements | https://podcasters.apple.com/support/audio-requirements | n.d. | A |
| P-S9 | W3C, Understanding SC 1.4.7 | https://www.w3.org/WAI/WCAG22/Understanding/low-or-no-background-audio | current | A |
| P-S10 | YouTube Help, Stable volume and Voice boost | https://support.google.com/youtube/answer/14106294 | n.d. | A |
| P-S11 | YouTube Help, audio quality enhancements | https://support.google.com/youtube/answer/16619284 | n.d. | A |
| P-S12 | YouTube Help, recommended upload encoding settings | https://support.google.com/youtube/answer/1722171 | n.d. | A |
| P-S13 | YouTube Official Blog, "Our big bets for 2025" | https://blog.youtube/inside-youtube/our-big-bets-for-2025/ | 2025-02-11 | A |
| P-S14 | I. Shepherd, YouTube changes loudness reference to -14 LUFS | https://meterplugs.com/blog/2019/09/18/youtube-changes-loudness-reference-to-14-lufs.html | 2019-09-18 | B |
| P-S17 | I. Shepherd on AES TD1008 | https://productionadvice.co.uk/td1008/ | 2021-10-01 | B |
| P-S19 | Torcoli et al., preferred levels for background ducking, JAES 67(12) | https://cris.fau.de/publications/234640600 | 2019-12 | B (peer-reviewed) |
| P-S21 | Brouwer et al., lyrics and speech recognition, J. Exp. Psych.: Applied | https://doi.org/10.1037/xap0000368 | 2022 | B (peer-reviewed) |
| P-S22 | Ekström & Borg, hearing speech in music | https://doaj.org/article/80b075e743444f3fa4e9240229278888 | 2011 | B (peer-reviewed) |
| P-S27 | ANSI S3.5-1997 band-importance weights (R SII package) | https://rdrr.io/rforge/SII/man/sii.html | n.d. | B |
| P-S30 | W. Murch, "Dense Clarity - Clear Density" | https://transom.org/2005/walter-murch/ | 2005 | B |
| P-S32 | N. Metcalfe, Sound Design for Visual Media, Sound On Sound | https://www.soundonsound.com/techniques/sound-design-visual-media-radio | 2013-10 | B |
| P-S33 | N. Metcalfe, Designer Sounds part 2, Sound On Sound | https://www.soundonsound.com/node/4905347 | 2013-11 | B |
| P-S34 | M. Senior, Best ways of hiding the edit, Sound On Sound | https://www.soundonsound.com/techniques/reaper-best-ways-hiding-edit | 2011-01 | B |
| P-S37 | S. Inglis, 10 Essential Mix Checks, Sound On Sound | https://www.soundonsound.com/sound-advice/10-essential-mix-checks | 2022-12 | B |
| P-S38 | P. White, Waves MaxxBass review, Sound On Sound | https://www.soundonsound.com/reviews/waves-maxxbass | 1998-02 | B (old) |
| P-S39 | Tatarunis & Klasco, Microspeakers' anatomy, audioXpress | https://www.audioxpress.com/article/microspeakers-anatomy-how-to-design-audio-systems-with-very-small-drivers | 2019-07-16 | B |
| P-S45 | Broadcast, "Audio experts call for caution" (BBC, *Wonders of the Universe*) | https://broadcastnow.co.uk/audio-experts-call-for-caution/5025307.article | 2011-03-24 | B |
| P-S49 | Frame.io Workflow Guide, Room tone | https://workflow.frame.io/guide/roomtone | ©2021 | C |
| P-S58 | LEMMiNO, Shouting at Stars credits | https://lemmi.no/p/shouting-at-stars | 2025-10-31 | A |
| P-S60 | Our study of documentary creators' published credits (music used per film) | (our study) | — | A (credits) |

### Our own evidence (measurements and records, described)

| # | What | Grade |
|---|---|---|
| I1 | Our eye-confirmed effect log of a fast long-form commentary video in the niche we studied (9:17): every effect with its time and kind | B |
| I2 | Our synthesis of five long-form references in the niche we studied (13-29 min): effects, beds, cut-outs, levels, loudness | B |
| I3 | Machine counts and bed levels on three long-form references (effect counts unconfirmed) | B (effect counts unconfirmed) |
| I4 | Our study of three slow internet-mystery documentaries (LEMMiNO, Nexpo, Barely Sociable) | B |
| I5 | Reference Shorts, batch 2: timing, levels, density, loudness, measured on spectrograms and frames | B |
| I6 | Reference Shorts, batch 3, and a later study of reference Shorts | B |
| I7 | Reference Shorts, batch 1 (two Shorts), and the effect and music levels of our own first Short before and after review | B |
| I8 | The cue sheet and mix check of a well-performing long video of ours (9:35) | B |
| I9 | That video's watch time by device (YouTube Studio: 64.7% on TV) | A (Studio) |
| I10 | Reviewers' verdicts on three of our earlier builds (music jumps, a card too loud, effects late, a master too loud) | A (verdicts) |
| I11 | The house rules on real clips, arrows and censoring (`standard/SOUND_AND_VOICE.md`) | A |
| I12 | Voice QA of ElevenLabs takes (the faults measured) | B |
| I13 | The score engine and master chain (`tools/sound/score.py`) | A (our code) |
| I14 | The clip-audio levelling code of one of our builds | A (our code) |
| I15 | Our study of a top creator in the niche we studied | B |
| I16 | Our study of a facts-list long video in the niche we studied | B |
