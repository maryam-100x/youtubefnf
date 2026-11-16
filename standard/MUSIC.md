# Music: the standard

*Part of `STANDARD.md`. Read before the music of every video. How the music sits under the voice (the levels, the duck, the handoffs,
the checks of the mix) is `standard/SOUND_AND_VOICE.md`, "Music: the mixing rules"; where this file and that one meet, that one sets
the mix and this one writes the music. The evidence behind the sounds and the bar: `standard/research/MUSIC_SOUNDS.md`. The code:
`tools/music/`.*

## 1. Where the music comes from

- **The creator chooses** (asked once at setup, step 10; written in `creator/PROFILE.md`; changeable any time; both can sit in one
  video): **music the chat makes in code** (this file), or **their own tracks** in `MUSIC` (only music they have the rights to). Say
  it plainly when asking: the chat makes good, fitting music for each chapter itself, written on the narration's own words.
- **Their own tracks** are measured, gridded and placed as cues (`standard/SOUND_AND_VOICE.md`, "Music sources" and the cue sheet).
- **Music made in code** is written note by note for the video: every turn of the story lands on a downbeat, the music thins under
  dense lines and leaves room on the key words, and the whole score sits far under the voice. Surge XT (a professional synth, free)
  plays the notes offline; every bed is measured against a bar before the creator hears it; when the narration is voiced again, one
  command retimes every bed. What Surge renders is the creator's: no licence fees, no claims.

## 2. The film-wide rules (music made in code)

| Rule | How |
|---|---|
| **One sound world** | the kit's sounds (section 5) for the whole video; mood changes between chapters live inside it |
| **One bed per chapter** (a second only at a real turn inside a long chapter) | a bed runs from its chapter's first word to the next chapter's first word, exactly: the next bed begins there on its own first downbeat. **Never two beds at once** (`selftest` and `code_beds` refuse an overlap). The last bed runs to the film's end and rings out |
| **A downbeat on every turn** | inside a bed, a segment per turn: `clock([the bed's start, each turn's first word, the bed's end], bpm)`, every segment a whole number of 4/4 bars, so each turn's first word is a downbeat. Segments of 15 s or more round best |
| **Keys walk up a fourth a chapter; the end comes home** | e.g. A minor -> D minor -> G minor -> C minor; the last chapter returns to the open's key **and the open's chords**, its last chord under the last word's end, ringing out (pad and sub held to the film's end + 2 s) |
| **Minor keys throughout** | lighter passages borrow the relative major (III VII i VI); never a bright major bed under a serious line |
| **Tempo 92-106 bpm** | per mood (section 4); `fit_bpm(points, lo, hi)` picks the written tempo whose whole-bar rounding moves least at the joints (keep the range the mood's tempo +-4); a joint over 12% is flagged |
| **Entering and leaving** | the pad fades in from -3/-4 dB over ~2.4 s at a bed's start and down to -6 dB at its end (automation points); the mix fades the bed's last 0.3 s (`code_beds`) |
| **The opening has an arc; the body is steady** | the opening bed (the hook and the setup, to the first chapter card) is the one with a shape: the pulse from frame 0, the sub (and the drive) entering on the story's first turn, thinner under the trouble, back over the open's chords on the promise, growing in density and velocity (`grow` up to 14) into the first chapter card; the level under the voice stays where it is. **The body's beds are steady ambience:** one pattern per segment, `grow` 8 at most, changes only at the bed's real turns, no build into a card, no riser, no swell, no drop |
| **One sound per moment: the statement drop is an effect** | a low hit on a narration word is the cue sheet's statement drop (`pal('bass_drop')`, the same sound for every drop), never written into a bed. The bed leaves it the room: the pulse, the sub and the pad stop on the word (`until(notes, t_word)`: every note ends there and its reverb tail rings on; a drone may swell in from it), back on the next downbeat or turn. Never a level dip to silence: the mix flags any silence outside `SILENCES`. A chapter card's sound is its effect (`chapter_card`); the new bed's first downbeat sits under it |
| **The close** | the one hit a bed plays itself: a low hit (the 808, on the home key's tonic) on the last word's end, the last chord ringing out. `score.py` flags any bed hit within 0.3 s of an effect ("bed hits on an effect's moment") |
| **Thin under dense lines** | fewer parts, a sparser pattern, lower velocity; under a real person's voice in the video (an interview bite): pad and drone only (the mix also drops the bed ~32 dB under the speaker) |
| **A designed stop** | everything out on the line's last word, a tail ringing under it (a stop is never digital silence; it goes in the sheet's `SILENCES` only if it truly falls silent), and back on a downbeat |
| **Every bed its own seed** | `Rand(seed)`: velocity spread +-5 (pulse) / +-4 (drive), timing nudge up to +-3 ms; the same seed gives the same notes on every render |
| **Never a typed time** | every time comes from the word times (`W.first`, `W.word`, `W.word_end`, `W.last_end`), so a new voice moves everything |

**A Short's music:** one bed for the whole Short (every Short its own, never a shared one), `Bed(..., loop=True)`: exactly the Short's
length in whole bars from its first frame, its progression back on its first chord at the loop, its tail laid over its start (so it
runs on through the loop). Livelier: 100-106 bpm, the pulse in sixteenths from frame 0, the sub in; a stop on the key line and back in
on a downbeat ("slammed back in"); no hits (the effects carry them). It goes in with `PIPE tools/motion/finish_short.py <video>
<render.mkv> <name> 0 <the Short's length> --music <bed_X.wav>` (the Shorts levels: ~17-18 dB under the voice).

## 3. Making a video's music, in order

1. **When:** as soon as the narration's word times exist (the voice step writes `tools/motion/src/<src>/words.json`). The opening's
   bed first: the opening's picture is cut on the music (`standard/BAR_LONG_FORM.md`, 1.9), so its bed is rendered before the
   opening is edited, and the edit reads its beats from the bed's `.grid.json`.
2. **Plan the beds** from the script's chapters and turns: for each bed its span, its anchors (the turns' first words), its room
   for each statement drop, its mood (section 4), its key (up a fourth a chapter, home at the end). Write the plan as the docstring
   of the music file, one paragraph per bed (the example's docstring is the shape).
3. **Write `videos/<video>/score/music.py`** from `tools/music/example/film.py`: one function per bed taking the word times `W` and
   returning a `Bed`, and `BEDS = {"O": bed_o, ...}`. Keep the example's helpers, levels, filters and reverb per layer (section 5):
   they are what the bar was reached with.
4. **Check the logic:** `SYNTH tools/music/music.py selftest videos/<video>/score/music.py tools/motion/src/<src>/words.json` ->
   `ALL OK` (every anchor phrase found, every anchor a downbeat, every event on its word, no two beds at once).
5. **Render:** `SYNTH tools/music/music.py render videos/<video>/score/music.py --judge` (about 2 minutes of CPU for a 2.5-minute
   film; it waits its turn with the other heavy jobs). The beds go to `MEDIA/videos/<video>/build/music/` (`bed_<id>.wav`, 48 kHz
   24-bit, with `.wav.json` and `.wav.grid.json`). Read every line: anchors 0 ms off, events within 5 ms, joints within 12%, and
   **AT THE BAR** for every bed.
6. **Under the bar:** fix it by the rule it breaks (too much in 1-4 kHz: the pulse a register lower or `@-12`, a lower low-pass,
   fewer pulse notes; muddy or harsh: rebalance from the stems with `music.py mixdown <stems> pad=+1 pulse=-2 --judge`, then `--out`
   the bed with `--grid`), render again. A bed under the bar never reaches the mix. **Renders vary** (some patches have free-running
   LFOs): the same bed measured PQ 7.57 and 7.67 on two renders. So a bed within 0.1 of the bar is rebalanced from its stems until its
   worst window (`PQ_min` in `music.py mixdown --judge`) clears the bar too, and the winning balance goes into the music file (the
   example's bed S: pad +2, sub -1, worst window 7.43 -> 7.63).
7. **The cue sheet** (`videos/_template/score/cues.py` is the start): `CUES = code_beds(BUILD / "music", under=UNDER)`; the
   statement drops as effects on the words the beds left room for; the rest as `standard/SOUND_AND_VOICE.md` says.
8. **The mix** (the pipeline's score step) and its report: "voice-music" ~22 dB per bed, the level at each switch, "bed hits on an
   effect's moment: none", no silences outside the designed ones. Written beds are steadier than library tracks: on the first video,
   the level goes to the creator as samples (the sheet's `UNDER` and a quieter one: the method's own films sat at 25-27 dB
   voice-music with `under=22`), and their pick becomes the sheet's start for the next videos.
9. **The creator's ear decides:** the opening bed goes to them under the voice with the prototype, the rest with the full build.
   Their no on a bed is rewritten by their words (another mood row, other layers, another sound from section 6), never argued with
   scores. Their verdicts go into `cases/SOUND.md`.
10. **After any new voice** (a re-voice, a patched line): the same render command again; the anchors move with the words, the cue
    sheet needs nothing.

## 4. A chapter's mood -> its tempo, progression and layers

Chords are written one symbol per bar; most progressions hold each chord two bars (an 8-bar loop of 4 chords). Roman numerals are in
the bed's minor key (i the tonic minor; III, VI, VII the major chords on the 3rd, 6th, 7th; V the major dominant; bII the flat second).

| Mood or moment | Tempo | Progression | Example | Layers (pattern) | Moves |
|---|---|---|---|---|---|
| **The open / the story starts** (curious, forward) | 96-100 | i VI III VII | Am F C G; Em C G D; Dm Bb F C | pulse 16ths `[0,_,2,_,1,_,2,3, 0,_,2,_,1,2,_,3]`, pad (2-bar chords); the sub enters on the first turn | pulse from frame 0; velocity grows ~8-12 over the span |
| **Darker turn** (a problem appears) | same bed | i VI iv V | Am F Dm E; Em C Am B; Dm Bb Gm A | pulse thins to 8 steps `[0,_,1,_,2,_,1,_]` a register lower (45-64); sub one note a bar | the major V pulls back to i |
| **Crash / shock** (the floor gives way) | same or -2 | i bII iv V | Am Bb Dm E (Esus4 E); Gm Ab Cm D | after the drop: pulse 16ths `[0,2,0,1,0,2,0,3, 0,2,0,1,0,3,2,1]`, sub a bar, pad | a bar with the pulse out before the drop's word (the statement drop lands there) |
| **The question / unresolved** | same bed | i VI(maj7) i V(sus4), one chord a bar | Am Fmaj7 Am Esus4 | pad + a low drone only | suspended chords before a turn |
| **Build into a turn** (the opening only: "But...", "So...") | same bed | the open's chords back | Am F C G | pulse 16ths `[0,2,1,2,3,2,1,2]` x2, velocity grow 14, sub a bar, pad | building to the last line before the first chapter card |
| **Steady explanation / how a system works** | 100 | i VII VI VII or i VI III VII | Cm Bb Ab Bb; Fm Db Ab Eb | pulse `[0,2,1,2,0,2,1,3]` 8 steps gate 0.6, **drive** (root eighths, lp 600), sub every 2 bars, pad | the groove; velocity grow ~8 |
| **Tension / countdown / waiting** | 104-106 | i VI iv V | Dm Bb Gm A; Gm Eb Cm D | ticks: pulse `[0,_,0,_,0,_,0,1]` x2 16ths, gate 0.35, a register up (55-76); pad; sub every 2 bars | the drive joins when it gets live; a drone under the held breath; the ticks out before the release word |
| **Curious / warm / thoughtful** | 92 | i VI III VII | Gm Eb Bb F | pulse 8 steps `[0,_,2,_,1,_,2,_]` (velocity 60/42), pad, sub every 2 bars | gentle; the sequenced pluck (pulse2) suits it |
| **Lighter / relief / a practical aside** | same bed | III VII i VI (relative major first) | Bb F Gm Eb; C G Am F | pulse up a register (52-71), sparse `[0,_,2,_,1,_,2,_]`, lower velocity; drive out | |
| **Colder / the cost lands** | same bed | i VI iv V | Fm Db Bbm C; Cm Ab Fm G | pulse down a register (46-65) `[0,_,1,_,2,_,1,_]`; the pad an octave lower (notes >= 58 moved down 12) | |
| **Archival / history** | 92-94 | i VI III VII or i III VII IV | Cm Ab Eb Bb; Dm F C G | warm pad (reverb 0.45), slow pulse in eighths (58/40), sub every 2 bars | the drive as it spreads |
| **Hopeful / people push back** | 96 | VI III i VII | C G Em D (E minor) | pulse 16ths `[0,_,2,_,1,_,2,3]` x2, pad, sub | tension again before the end (i VI iv V), then home |
| **Lift, then sigh back** (hope that doesn't hold) | same bed | to the relative major, then back to i | F minor -> A-flat major -> F minor | fuller pad, pulse up | the sigh back on the line that undoes it |
| **Something stuck that won't move** | same bed | chords over a pedal: the sub holds the tonic | D pedal under Dm Bb F C | the sub holds one note | |
| **The end** (home) | the open's -2 to -6 | the open's chords | Am F C G | sparse eighths `[0,_,2,_,1,_,2,_]` (56/38), pad, sub; the last chord ringing | the close: a low hit on the last word's end |

## 5. The layers: registers, levels, sounds

Written MIDI notes; levels are each part's RMS where it sounds, before the bus (patches differ by 20 dB and more, so every part is
set to its level whatever the patch). The bus after them: a gentle compressor (-20 dB, 2:1, 30/250 ms), the peak to -3 dBFS, a
limiter at -1 dBFS; the bed's real level is set later, under the voice, by the mix.

| Layer | Sound (Surge XT library path) | Plays | Written register, helper | Level | Shaping (after Surge) |
|---|---|---|---|---|---|
| pulse | `Plucks/Diamonds` | an octave down (`@-12`) | voicing inside 45-76, `arp16` | -26 (-1/-2 for ticks and light passages) | hp 100-140 Hz, lp 1500-1800 Hz, reverb 0.2-0.25 |
| pulse2 (a sequenced pluck: warm, curious beds, the groove) | `John Valentine/Sequences/Crockett's Seq Filter Bass` | as written | 48-71, `arp16` | -26 (-1) | hp 120, lp 2000, reverb 0.25 |
| pad | `Kyurumi/Pads/Neverending` | as written | 48-71, `held` (2-bar spans) | -24 | hp 140-150, lp 1500-1700, reverb 0.40-0.45 |
| sub | `Vospi/Basses/Floored` | +12 (it sounds an octave under the written note) | the root nearest 29-41, `subs` (1- or 2-bar spans) | -20 (-2 when light) | lp 350-400 |
| subB (the second sub) | `Vospi/Basses/I Can Kinda Be Chordish` | +12 | as the sub | -20 (-2) | lp 350 |
| drive | `Basses/FM Bass 1` | as written (it carries a strong octave under) | the root nearest 36-41, eighths, `eighths` | -22 | lp 600 |
| drone | `Xenofish/Pads/Fireflies` | as written | the tonic, 38-45, one long note | -30 (-4 in an open) | hp 50-60, lp 700-900, reverb 0.4 |
| hit (the close) | `A.Liv/Basses/Bonsai 808` | as written (it sounds an octave under: it follows the note) | the tonic, 36-45 | -18, minus 4-6 | lp 900, reverb 0.25 |

Velocities: pulse accents 56-80 on each beat's first step, others 38-54; pad 56-62; sub 82-94; drive 80-90 on beats, 56-70 off; the
close's hit 100-110. **No setting inside Surge is changed:** every patch plays as shipped; all shaping happens after it. The kit is
`writing.KIT` (a music file may override it with its own `KIT`); why each sound won, and the file checks, are in
`standard/research/MUSIC_SOUNDS.md`.

## 6. Other sounds

Any Surge XT patch can take a layer, chosen the way the kit was: **measure** a role's patches alone (`music.py audition <role>
<out.json>`: level, centroid, the share under 1 kHz and in 1-4 kHz, under 80 Hz, attack, sustain, noisiness, width, pitch clarity;
keep clearly pitched patches, mostly under 1 kHz, little in 1-4 kHz, of the role's envelope); **pick in context** (`music.py pick
<music.py> <bed> <t0> <t1> <cands.json> <out.json> --words <words.json>`: every candidate plays its real part of a real 20-30-s
stretch at the part's fixed level with the other parts, through the bus, scored by the stand-in ear; a candidate over the bar's
voice band loses to every one inside it; try `@-12` variants near the voice band); **check** each winner (`music.py check "<patch>"
--role bass`: its real octave, fixed by a transpose, and its added tones: a bass that adds a third or a tritone to every note is
refused; a drum that doesn't follow the note is replaced by one that does). Then render the bed and check it at the bar. A new sound
in the kit goes to the creator as a sample first.

## 7. The bar

Nothing is chosen by ear first: every sound and every bed is measured against a bar taken from beds that passed a listening test, and
the creator's ears give the verdict at the end.

**The stand-in ear:** Audiobox Aesthetics (Meta; CC-BY 4.0), four scores 1-10 trained on human ratings: PQ production quality, PC
production complexity, CE content enjoyment, CU content usefulness. A bed is scored in 10-s windows (a last window under 3 s is
dropped), the median of each kept, and the worst PQ window. It catches a cheap, harsh or muddy render; it doesn't hear "wrong for this
video". CPU is enough.

| Measure | The reference beds (five licensed library beds that passed a listening test under a narration) | **The bar** |
|---|---|---|
| PQ (median of 10-s windows) | 7.6-8.0 | **>= 7.6** |
| CE | 6.9-7.5 | **>= 6.9** |
| CU | 7.6-8.0 | **>= 7.6** |
| energy under 1 kHz (whole bed, mono) | 98.8-99.9% | **>= 98.8%** |
| energy in 1-4 kHz (the voice's clarity band) | 0.1-1.2% | **<= 1.2%** |
| energy under 80 Hz | 5-76% | reported |
| median frame centroid | 417-764 Hz | reported |
| onsets a second | 4.1-6.5 | reported (beds written this way read calmer, ~3) |
| loudest minus quietest 8-s block | 4-12 dB | reported (the body's beds: steady, a few dB) |

Beds written this way for real narrated films measured PQ 7.73-8.17, CE 7.31-7.65, CU 7.82-8.02, 99.4%+ under 1 kHz, all inside the
voice-band bar; in a blind A/B under the same narration a listener could not pick them from licensed beds. The example film renders
every bed at the bar for both voices (`standard/research/MUSIC_SOUNDS.md`).

**The checks `music.py render` prints:** every anchor on a downbeat (within 1 ms, exact by construction); every event note on its
word (within 5 ms; hits are not nudged); each segment's real tempo and the change at each joint (over 12% flagged: move an anchor or
the tempo); the bands; with `--judge` the scores, the profile and **AT THE BAR / UNDER THE BAR** with the reasons. Under the voice, the
mix's report is the check (`standard/SOUND_AND_VOICE.md`).

## 8. Install (the setup's step 10, when the creator chose music made in code)

| Part | Version | Where |
|---|---|---|
| Surge XT | 1.3.4 (released 2024-08-11) | Windows: the official portable build `surge-xt-win64-1.3.4-portable-install.zip` (301,759,660 bytes, MD5 `30023479e71252e91a7b7a9a59cbaa7d`, from the release's `md5sum.txt`) from github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4, unpacked into `MEDIA/apps/surge-xt` (it holds `Surge Synth Team/` with `Surge XT.vst3` and `SurgeXTData/`; ~490 MB, 3,008 patches). macOS: `surge-xt-macOS-1.3.4.dmg` from the same release (MD5 `8d64166483e704f7b07fd1893b3c4dd9`); its installer (the creator clicks through it) puts the plugin in `/Library/Audio/Plug-Ins/VST3/` and the data in `/Library/Application Support/Surge XT`, where `tools/music` looks first |
| The SYNTH environment | Python 3.12, `tools/requirements/synth.txt` | `MEDIA/envs/synth`, built with uv like the others; torch from PyTorch's CPU index on Windows (the same flags as EDIT, `tools/requirements/README.md`); ~1.2 GB |
| The quality model | `facebook/audiobox-aesthetics`, 415 MB | downloads on its first use into `MEDIA/models/hf` |

Surge XT (covered by the creator's one go for the setup's installs, no new ask): `PIPE tools/setup/surge.py` downloads it, checks its size and MD5 against the release's, and unpacks it safely into the empty
`MEDIA/apps/surge-xt` (on a Mac it opens the installer for the creator, then `--check`). The environment: uv as for the others. Then
the test, in order:

1. `SYNTH tools/music/music.py selftest` -> `ALL OK`
2. `SYNTH tools/music/music.py patches Pads/` -> a list of pad patches (Surge's library found; its first start takes ~35 s)
3. `SYNTH tools/music/music.py judge --warm` -> `model ok` (downloads the model once)
4. `SYNTH tools/music/music.py render tools/music/example/film.py --judge` -> four beds, every one **AT THE BAR**, into `MEDIA/tmp/music`
5. Nothing goes to the creator: a sample made for no video tells them nothing. They first hear the music in their first video,
   written for it (under the voice with the prototype, section 3 item 9). Music for a vibe before that only when they
   ask for it.

On Windows this is tested; on macOS the same parts and steps (the Mac's installer locations are the ones Surge XT documents).

## 9. Known limits

- Renders are close but not bit-identical between runs: some patches have free-running LFOs or noise.
- The stand-in ear is a proxy trained on human ratings: it catches cheap and harsh, not "wrong for this video". The creator decides.
- `music.py check` reads a patch's pitch from its lowest strong spectral peak; pYIN beside it locks onto subharmonics for deep
  basses (marked "uncertain"), and a sequencer patch moves between octaves on its own: listen when it says so.
- The licences of the parts: `tools/music/NOTICE.md`.
