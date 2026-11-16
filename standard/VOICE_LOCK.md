# The voice lock: the voice made once, then frozen

*Part of `STANDARD.md`. Why: a voice changed after it "passed" moves the timing every time, so the gate re-probes, the mix runs again and
the picture re-anchors (hours per change); accent rounds by ear eat days; and most voice faults a viewer hears (a cut word, a stray
syllable, an accent slip, a name said the foreign way) sit in classes that already had a rule. Rules didn't hold; machines that block do.
So every stage below is a tool that refuses, not a line to remember. The voice's craft (its sound, the house chain, the accent, how a line
is written to be said) is `standard/SOUND_AND_VOICE.md`; what each sound check catches and its numbers: `tools/sound/SOUND_GATE.md`; how
the steps run in the line: `standard/PIPELINE.md`.*

## The idea in one line
The voice is made ONCE, after everything that can change its words is final, by a stage that cannot finish while any check fails;
after that its timing is frozen, and a later fix is laid into the old slot without moving time.

## Words used here
- **The lines-before way**: a span of lines voiced as ONE ElevenLabs request with the script lines before it voiced inside the same
  request and cut away (two lines, more until they reach 10 s of speech), and the head of the line after it voiced too and cut away. An
  accent and a tired start live in a whole request, and a request's last word comes back clipped when nothing follows it: voiced this
  way, a span starts warm, in the voice's own flow, and ends whole. It is the way the ear passed; every take below is made so.
- **The warm-up**: the video's first section has no lines before it, so it is voiced after `[tts.elevenlabs] warmup` (`config/tts.toml`:
  two lines in the house register, spoken and cut away the same way; never heard in the video).
- **The layout**: the picked takes laid out as one narration (`tools/voice/proto_narration.py`: the house tempo, the house chain, the
  slots), kept as `build/voice/narration_laid.wav` and `build/beats_laid.json`: the reference every later check holds the final against.
- **Chain D**: the house narration chain (`tools/sound/voice_level.py --chain mb`, -14 LUFS; `standard/SOUND_AND_VOICE.md`).
- **The voice guard**: the accent and tone screen (`tools/voice/voice_guard.py`), calibrated on the creator's own verdicts (below).

## The tools

All in `tools/voice/` unless named; EDIT unless named. `PIPE tools/pipeline/pipe.py <video> voice` runs stage 0's `require`, stage 2 and
stage 3's `lock` in one step.

| Stage | Tool | What it blocks |
|---|---|---|
| 0 ready | `voice_ready.py <video> status / require [tool] / names [--measure] [--k 2] [--stamp]` (reads `tools/workflow/stages.py`) | the first take: `dj tts`, `span_takes.py`, `section_takes.py`, `voice_patch.py`, `voice_versions.py`, `autopick.py` refuse (exit 5) until script, facts, coldread, bites and names are stamped on the CURRENT script.md |
| 1 takes | `autopick.py <video> <first beat> <last beat> [--k 3]`; the whole film: `voice_full.py <video>` (sections, k=1, a new take only where one fails, then the layout) | a section is never kept with a hard or maybe accent, a name not measured American, a word neither recogniser hears, or a tired opening; exit 2 = reword and voice again |
| 2 chain + gate | `bash tools/sound/voice_chain.sh <video>` (starts every run from the layout) then `tools/sound/gate_sound.py <video>` A1-A13 + LOCK | A10 fragments, A11 a hard accent and A12 a tired opening (both never allowable), A13 a word's end lost at a cut, a broken lock (never allowable); the chain stops (exit 5) and puts the narration back if script.md changed while it ran |
| 3 lock | `voice_lock.py <video> lock [--note] / verify / status / unlock --why "<reason>" / refuse <tool>` | every narration writer (the chain tools, both chains, `dj tts`, `dj captions`) refuses (exit 4) while `videos/<video>/voice_lock.json` exists; `verify` (and the gate's LOCK line) catches any write that went around them |
| 3 fix | `voice_layin.py <video> <beat> <k...> [--from W --to W] [--apply]` | the only way to change a locked voice: a clean take laid into the old slot, every anchor within 2 frames, nothing else moves |

**Shared ears:** `ctcalign.py` (word times and free letters from the audio: a wav2vec2 CTC model), `saycheck.py` (was a name said the
American way: a phoneme CTC model, competing hypotheses), `accent_take.py` (the voice guard's accent verdict as JSON, PIPE), `asr_words.py`
(Whisper's words, the second recogniser, PIPE), `opening.py` (does a request open tired).

**The voice guard's reference** is the creator's own voice: narrations they approved in `MEDIA/voice/guard/approved/` and takes with a
fault they heard in `MEDIA/voice/guard/flagged/` (each with its `<name>.spans.json` of `[t0, t1, "<kind>"]`, kinds ACCENT, CLOSE, WHISPER,
BREATHY, TIRED, SWALLOWED), `short/` subfolders of both for the Shorts voice. It is filled at setup and grows whenever a fault is heard;
after every change it is rebuilt: `ACCENT tools/voice/voice_guard_embed.py MEDIA/voice/guard`, `PIPE tools/voice/voice_guard_tone.py
MEDIA/voice/guard`, `PIPE tools/voice/voice_guard_calib.py` (the model it writes, `MEDIA/voice/guard/voice_guard_model.json`, is the
creator's alone). Until the flagged set holds about 10 s of British speech, the guard's accent score is CommonAccent's P(UK) alone, and the
calibration report says so.

## Credits: never a blocker
The voice's credits are spent as the work needs them, never asked for or announced as a cost per take. A low balance is never a reason to
stop the other work. A quota error mid-run is first a top-up on its way: keep the other work going, re-check (`PIPE
tools/voice/voice_credits.py`) every few minutes for at least half an hour and retry the same request (`voice_full.py` does this by
itself: every 3 minutes for 30 minutes, then it stops and says so); only a balance still empty after that goes to the creator, with the
times checked. The key is the file `MEDIA/secrets/elevenlabs_api_key.txt`, read only by `dj` and never printed.

## Stage 0: ready to voice (`voice_ready.py`)
One source of truth for the stamps: `videos/<video>/stages.json`, written by `PIPE tools/workflow/stages.py <video> stamp <stage> --note
"<proof>"`, each script-hashed (an edit to script.md after a stamp makes it stale). `voice_ready.py` reads it through stages.py's own
`load`, `state` and `script_hash` and writes nothing of its own but the evidence of the one stamp a machine earns by itself:
- **names:** A6 (`EDIT tools/sound/names.py <video>`: every proper noun of the script has an entry in `tools/sound/names.json`, a respelling
  or "as is") and every name whose respelling is phonetic ("Mah-ree-bel Kahs-tee-yoh"; a split into plain words like "Mac Book" needs
  nothing) **measured** on a lines-before test take of the beat that first says it (`names --measure`: span_takes, k=2, about 300 credits a
  take; `saycheck.py` judges; evidence in `<dj>/build/voice/names_measured.json`); `--stamp` writes the names stage through stages.py when
  every one is AMERICAN. A respelled name needs an `"ipa"` pair in names.json to be measured (below), or `"measure": false` with the reason.
- facts, coldread, bites, script: stamped by whoever did them, with the proof in the note.
- **Before any voice exists:** `names --measure` runs its span_takes with `VOICE_READY_NAMES_MEASURE=1`, so `require()` asks for every stamp
  but `names` (the stamp those takes earn), and span_takes voices the takes alone when there is no `build/beats.json` or narration to set
  them in (no `_0_now` listening file, no level match). A6 needs the video's `video.toml` with its `dj` path. A6's word pattern reads plain
  letters only, so a name with an accented letter ("Muñoz") is never flagged: such a name gets its entry by hand.
Shorts (video.toml `kind = "short"`) are not held: the stages are the long form's.

## Stage 1: the machine picks the take (`autopick.py`)
Every section is voiced the lines-before way K times (K=3; `span_takes.py`, the names table's respellings in both the span and its lines
before; the video's first section after the warm-up). The whole film: `voice_full.py <video> [--plan] [--jobs 3] [--tries 2] [--words 150]
[--max-words 200] [--min-words 60] [--only S10-S20] [--no-layout]` cuts the script into sections (its chapters, about 150 words each, beats
never split, a chapter under 60 words joins the next), voices each with K=1 and a new take (a new seed) only where a take fails a check, up
to the tries, each autopick run inside a heavy.py `score` ticket, then lays the picks out (`proto_narration.py` over the whole script:
narration.wav, beats.json and the layout's copies narration_laid.wav / beats_laid.json); it resumes where it stopped. Each take is judged
by four ears:
- **accent:** the voice guard on the whole take (`accent_take.py`); a hard ACCENT or a maybe ACCENT? rejects it (British stretches hide in
  sections kept "by measures": every British stretch heard by ear on a flagged narration sat in a section kept so);
- **names:** every name with an `"ipa"` pair said in it (`saycheck.py`): anything but AMERICAN rejects it;
- **words:** the CTC letters and Whisper, each against the script: a script word neither hears, or speech the script doesn't have (3+
  letters), rejects it;
- **opening:** `opening.py` on the take: an opening whose pitch peaks stay under the take's own rejects it where a cold start can be (the
  video's first section, or a request with under 10 s spoken before its span); with its lines before, a request is warm by construction and
  a low reading is reported, never a reject (the sentence's own intonation: below).
A name with a known `"hit_rate"` in names.json (the share of lines-before takes measured American) raises K until a clean take is 90%
likely (1 - (1 - rate)^K >= 0.9, at most 8: a name at 0.3 gets 7 takes). The pick is the clean take with the lowest accent score. No clean
take after K: exit 2, never kept; it names the British-pull phrases in the span and the lines before and the names that failed, and the
section is voiced again with the cue reworded (`standard/SOUND_AND_VOICE.md`, the method). `--score <stem> <k...> [--first B --last B]`
judges takes already on disk (`build/voice/patch/span_raw/<stem>_<k>_span.wav` + `.align.json`); `--say WORD=SAYING` sends a respelling
for these takes only. Writes `build/voice/autopick/<first>-<last>.json` (every take's verdicts, the pick, script.md's hash); the pick is
recorded only if script.md is the same at the end as at the start. Splicing a pick in is the chain's step: `cd tools && PIPE
voice/voice_patch.py ../videos/<video> <beats> --keep-old --use <beat>=<k> ...` (refused on a locked voice: use the lay-in).

`span_takes.py` (`cd tools && PIPE voice/span_takes.py ../videos/<video> <first beat> <last beat> <first take> <last take>`): `--before 2`
lines before, `--before-min-s 10` (more lines until they reach 10 s at 3 words a second, the warm-up in front where the script runs out),
`--warmup ''` (the first section voiced cold, for a test), `--tail` (the head of the next line, default its first three words), `--around
3.0` (seconds of the narration each side in the listening files), `--seed`, `--name`, `--no-prev`, `--prev-text`, `--say`, and the
pronunciation switches (`--language-code`, `--dict ID:VERSION`, `--plain NAME`: off by default, see Research). Every call is logged in
`MEDIA/voice/elevenlabs_usage.csv`. `dj tts` does not send the warm-up (its cache key ignores it).

## Stage 2: the chain and the gate
`voice_chain.sh` refuses on a locked video (exit 4); it starts every run from the layout (narration_laid.wav and beats_laid.json: a hand
edit or an earlier run's output is never its input, so A1's reference, `narration_prechain.wav`, never holds a cut); it records script.md's
hash at its start and, if the script changed while it ran, puts narration.wav and beats.json back as they came in and stops (exit 5). It
checks the laid voice's words (A5) right after the first captions pass and stops there on a misread word (exit 6: re-take those sections,
lay out again), and stops on a failed `dj captions` (exit 7). Its order and its clean-up (fixmutes, `tails.py --fix`, `hisstails.py
--fix`, up to 3 rounds of the A3 fix, then the gate, exit 3 while anything is flagged): the script's header. A fix after the chain is a tool
on its output (`cut_pause.py`, `relay.py`, `tails.py --fix`, `fixflags.py` ...), then `gate_sound.py`; never a cut by hand.

**Chain D streams.** `voice_level.py --chain mb` (the layout's last step, and every lay-in take's) runs in 60-s chunks with 3 s of real audio
on each side, the chunks on the detectors' decimation grid, and measures loudness exactly as pyloudnorm does (`StreamLoudness`); `--whole`
keeps the whole-array way as the reference. Null test: the two outputs are bit-identical and read the same LUFS. A full-length run of any
whole-narration tool waits for memory commit under 60% with nothing heavy beside it (`tools/hooks/commit_guard.py` holds it there; the
windowed modes below at the 85% model-load line).

The sound gate's checks are in `tools/sound/SOUND_GATE.md`; the four the lock added, and LOCK:
- **A10 fragments** (`tools/sound/fragments.py`): around every join (beats.json), every lay-in edge (voice_lock.json) and every voiced run
  Whisper's boxes leave bare (pitch present, 60 ms or more, peak -30 dB or louder), a window of the script's words is forced onto the audio
  by the CTC model and decoded freely; letters it hears that the script doesn't have (a whole extra word of 2+ letters, or 4+ inside a word,
  never beside a word said letter by letter), over 60 ms+ of voiced sound 40 ms clear of every aligned word, are a fragment (a take's
  context tail left at a splice, a doubled syllable, a word's head at a join). A doubled syllable is placed on the copy Whisper left bare.
  Numbers and abbreviations are read as said ("Dr." as doctor, "16th" as sixteenth), so the script's spelling against the voice is no
  fragment. Decodings are cached per window (`<dj>/pipeline/gate_sound/a10_cache.json`).
- **A11 accent** (`accent_take.py` on the final narration): a hard ACCENT fails and can't be allowed; maybe-British is printed as a report
  (on an approved voice it marks about a fifth of the sections the ear passed: as a gate it would be wrong that often; per take, in
  autopick, it rejects). The guard's embeddings are cached per window by content (`voice_guard_embed.py`): after a lay-in only the changed
  windows are recomputed.
- **A12 opening** (`opening.py`): every request's opening in the final narration (the narration's first beat and the first beat of every
  section autopick picked), against its own request's pitch peaks: TIRED fails and can't be allowed on the video's first request and on any
  request whose picked take had under 10 s spoken before its span (the section is voiced again); on a request warm by construction it is
  printed as a report. A short request is read against 45 s of the narration around it.
- **A13 hiss** (`tools/sound/hisstails.py`): every word end the final goes quiet after, held against the layout: a hiss the layout still has
  and the final lost (15 ms or more, its loudest frame -40 dB or louder, broadband or in 4-12 kHz) is a word cut off. A1 and A13 both read
  the layout (gatelib's `raw` is narration_laid.wav when it exists, else narration_prechain.wav).
- **LOCK:** with a voice_lock.json, the narration and word files must hash as locked; can't be allowed.
- `--span T0 T1`: only flags in those seconds count (A10 and A11 then listen only there): the lay-in's gate.

## The opening and the tails

**The opening.** A request with nothing spoken before it starts cold: its first sentences keep the voice's pitch peaks down (the same text,
3 takes each way: the first word at 159-160 Hz cold against 190-195 warm; the cold take caught up by its fifth sentence). It sounds
exhausted at the very start, and none of the accent, name and word checks hears it.
- *Generation:* every section after the first has its lines before inside the request; the first is voiced after the warm-up.
- *Screen:* `opening.py`: peak_gap = the mean of three semitone ratios, the F0 95th percentile over the opening's first 6 s of speech and
  the 98th over its first 4 s and its first 6 s, each against the request's own (Praat pitch, voiced speech frames). Under 0.0 = TIRED.
  On takes with a known way of voicing: cold -0.49 to -1.10, warm +0.06 to +2.90. It needs 12 s of speech in the request and 6 in the
  opening, else UNKNOWN (never a pass by default). **It is a verdict only where a cold start can be:** the video's first request, and any
  request with under 10 s spoken before its span (the take's align.json `before_end`: the warm-up is about 11 s, lines before 15-23 s). On a
  request warm by construction the reading is the sentence's own intonation, not a cold start (a calm aside voiced the lines-before way read
  -0.58 to -1.42 in 6 of 6 takes, and across all sentence starts of a narration the reading is under 0 for 39-54%): there it is reported
  (autopick's `opening_note`, the gate's report line), never a reject, since rejecting it re-voices a good section for nothing.
- *Octave jumps can't pass an opening:* a pitch tracker can put a few frames an octave up right where the 98th percentile is read, and
  lift a tired take over 0. `opening.py` takes a second reading with the jumps out (a voiced frame over x1.5 or under /1.5 the median of
  its 31 voiced neighbours) and calls TIRED when either reading is under 0: the jumps can only make a take tired, never pass one. The clean
  reading alone shifts the calibration (cold takes rise toward 0), so it is never used alone.
- *Where:* autopick's fourth ear (per take: `opening_rejects`) and the gate's A12 (per request in the final narration), the same rule.
- `EDIT tools/voice/opening.py <wav> [--span T0 T1 ...] [--json]` (no span: the whole wav is one request, as a take from span_takes.py).

**The tails.** A word's final hiss (an s: about 100 ms after the closure, nearly all of it over 4 kHz) is lost three ways: a pause cut by
hand off Whisper's end of the word (Whisper boxes the hiss into the next word), a declick that fades the 40 ms before a drop into silence,
and a second chain run that starts from the cut narration, so A1's reference holds the cut too. The locks:
- `voice_chain.sh` starts every run from the layout, so an edit between runs can't become the reference; gatelib's raw is the layout.
- `breath_cut.declick` never fades a drop that comes on sound (the last 5 ms over -40 dB): a cut through a word stays visible, listed by
  breath.py, and the gate names it.
- `span_takes.py`'s cut between two lines moves past the line's last hiss (to the first 10 ms under -45 dB broadband and -50 dB in 4-12
  kHz) when the quietest point sits on sound; `proto_narration.py` refuses a beat whose end still sounds (the same bars).
- A13 in the gate; every cut after the chain is a tool's, never a hand's. The chain runs `hisstails.py --fix` after `tails.py --fix`: a
  lost hiss is laid back from the layout where the final has room (the chain's own cut undone, levels only); one with no room stays a flag.
A13 reads only the sound: a frame is hiss when its 4-12 kHz band is within 5 dB of its whole level and over -50 dB (a breath's spectrum
sits lower: an inhale at -28 dB reads -34 in the band); the stretches from 60 ms before a run's end to 120 ms after it (a stop's closure
before a final s) are held against the final, and frames where the final's band sits 6+ dB under are lost. Proven: on a prototype against
its layout, 1 flag in 163 speech runs (the one hiss heard cut, 65 ms at -17 dB); on a whole chained narration against its own pre-chain
input, 0 in 1,315 runs; 6 of 6 hiss tails cut 20 ms into the hiss flagged and 0 of 6 breaths muted exactly.

## The locks the final narration needs
A narration whose every take was clean by autopick's four ears can still fail the gate, in two classes no allow passes and a class of the
gate's own false flags. Each has its machine:
- **The accent in place (A11).** A take can end British exactly at its join into the next take and read clean alone, because the guard's
  2-s windows stop a second before a file's end and the 5-window median thins what is left. `accent_take.py --in-place T0 T1 [--grid-t0
  G]` judges a piece where it sits, with the narration's own seconds around it, on all four 0.125-s offsets of the 0.5-s grid: a British
  stretch on any offset, or a maybe-British one on the gate's own grid, overlapping the piece by over 0.3 s, rejects the take.
  `voice_layin.py` runs it on its preview (the narration as it will be, 6 s around, lined up on the gate's grid); `autopick.py` runs it on
  span_takes' listening file when a narration exists (a re-take; the full voice has no neighbours yet, and there the gate's A11 judges the
  joins). Proven: on the gate's own offset it gives exactly the gate's flag, and two other offsets flag it too.
- **The lines before reach 10 s (A12).** A section voiced after two short lines (under 6 s spoken) opened tired in 3 of 3 takes.
  `span_takes.py --before-min-s 10` (the default) adds lines before the span until they reach 10 s at 3 words a second (the warm-up in front
  where the script runs out), so every request is warm by construction.
- **Octave jumps** (above).
- **Numbers said in digit groups (A5).** The take check's reader reads digits in groups ("four eighty-two" 482, "six one two" 612, 98.4,
  210), joins "and" only after hundred or thousand, keeps a number that opens a compound ("two sixteen-year-olds" is 2 and 16) and a
  comma's break, and puts the captions' split "$20,000" back together; adding the parts ("four eighty-two" as 86) was a false flag class.
- **Mutes with time kept, when the picture is already fitted.** `fixflags.py` mutes A3's breaths and A2's "scrap after a mute" between
  quiet edges (`--reach-ms` for an inhale longer than the gate's 50-ms measure); `cut_pause.py <video> <t> --give-back T` cuts a long pause
  inside a sentence and puts the same time back into the sentence's end pause (or an earlier one), so only the words between move, and
  `--words` moves the captions' words with the sound (no new Whisper pass: its word boxes change from pass to pass, and every pass brings
  new A3/A5 flags). A cue or chunk spanning a cut ends where its last word went. Lay-ins replace whole beats in their old slots.
- **A mute must not take a word's voiced tail (A13 "voiced:").** The chain's pause mutes can take the creak at the end of a word ("second.",
  "button.", "gone.": 40-180 ms under 1.2 kHz at -16 to -46 dB, to digital silence); A1 reads releases and hiss, and A13's hiss band misses
  it. A13 also counts the layout's voiced frames (over -45 dB, centred under 1.2 kHz) from the run's last 60 ms to 250 ms after it, where the
  final is silenced (under -90 dB: a mute, never a level change), with the take never resting 20 ms under -50 dB between the mute's start and
  them; 30 ms is a flag, and `hisstails.py --fix` or `tails.py --fix --span` lays it back.
- **Windowed fixes.** `tails.py --span/--show` read about 3 s of the final and the layout (`WinPair`: the run before the span matched near
  where the beats put it) and write back only the span's samples (null test against the whole-file run: no sample differs, the same
  offset). `voice_layin.py` reads a ±15-s window (`WinArray`) and writes back only the slot (its dry run and apply byte-identical to the
  whole-file version's). commit_guard holds the windowed modes to the 85% model-load line, the whole-file jobs to 60%.

## Stage 3: the lock and the lay-in
`voice_lock.py <video> lock` writes `videos/<video>/voice_lock.json`: the sha256 of `build/voice/narration.wav`, `build/captions/words.json`,
`build/beats.json` and the edit's `src/<src>/words.json` and `beats.json`. From then on the picture anchors on those words, every writer
refuses (one guard line at the top of each; a shell script's first line is `voice_lock.py <video> refuse <tool>`), and `verify` fails on any
change made around them. A real re-voice (new script lines, a whole section) is `unlock --why "<reason>"` (kept in
`voice_lock.unlocked.json` with the time), the normal stages, and a new lock.

**The lay-in** (`voice_layin.py <video> <beat> <k> [<k> ...] [--from WORD --to WORD] [--anchor "phrase" ...] [--narration F] [--takes-dir
D] [--inserts SCRIPT] [--no-checks] [--apply] [--reworded] [--skip-anchor "phrase" ...]`): for one beat or a piece of it, from takes voiced
the lines-before way (`span_takes.py ... <beat> <beat> k0 k1`: `build/voice/patch/<beat>_<k>.wav` + `.align.json`):
1. the old piece measured from the audio: its words forced onto the narration by the CTC aligner, each edge snapped to the sound (onset:
   the dip before the word, then the first 10 ms 8 dB over it; end: the first 16 ms under -48 dB after the last frame over -30 dB); the slot
   = its first sound to the next sound;
2. each take at the house tempo (1.04x, `[tts] tempo`) and through chain D (`voice_level.py --chain mb --lufs -14 --ceil -1.5`), its words
   forced on the same way (never ElevenLabs' times: they can run up to 0.5 s late), the piece cut from its first sound to its last, its pauses
   inside the sentence at 0.12 s except the ones that land an anchor;
3. the anchors: every phrase the picture or the cue sheet hangs on inside the piece, read from the code (`w('S12', 'first heard')`,
   `at(t0, 'S12', 'middle of')`, `F.w("S12", ...)` in `tools/motion/src/<src>/*.ts*` and the video's `score/cues*.py`), plus `--anchor`; the
   pause before each anchor set so it lands where it was (measured once in the take as voiced and moved by arithmetic: re-measuring on the
   cut piece drifts); every anchor within 2 frames (fps from video.toml), else ANCHOR OFF; `--skip-anchor "<phrase>"` lets one move, on
   record;
4. each take judged by autopick's ears (the accent on the whole take and in place, names and words on the piece); the pick = the clean take
   that fits with the least anchor drift;
5. `--apply` (refused if script.md changed while it ran): narration.wav rewritten in place (the old piece silenced up to where the next
   word's onset ramp starts, the new one at the old piece's loudness, 5-ms fades, a backup in `build/voice/layin/<stamp>_<beat>/`),
   `sync_words.py` (byte-identical words: the time is kept), the inserted copy rebuilt (`--inserts` or video.toml `[voice] inserts`) and
   checked to hold the new piece, voice_lock.json re-stamped with the lay-in on record, and the sound gate on the changed span (A2 A3 A4 A7 A8
   A10 A11).
Without `--apply` it writes only previews (`build/voice/layin/<beat>/preview_<k>.wav`, 3 s around, and `preview_old.wav`) and
`layin_report.json`.

**A reworded line after the lock** (`--reworded`: the beat's words changed in script.md, a sentence cut from it). The old piece's words
can't be found in the take, so the whole beat's new words go into the old slot from its first sound (script.md first, the stamps redone,
takes by `autopick.py <video> <beat> <beat>`). Its pauses are the house's (a sentence end at most 0.25 s, inside one 0.12 s, the take's own
when shorter), and a pause set to land an anchor stays within them. An anchor the new words still say keeps its time where they allow; an
anchor they no longer say is GONE: either moves only by `--skip-anchor`, on record for the picture's owner (w()/at() read the new times; a
GONE phrase finds nothing). `--apply` also writes the beat's text into beats.json and its captions' words, cues and chunks (the words forced
onto the narration as laid, starts moved to their sound only after a pause as dj captions does; no Whisper pass), then sync_words.py. A
shorter piece leaves a longer pause after it: `--apply` prints the call that closes it; the voice is unlocked (`unlock --why`) and the pause
cut back to the old join's quiet with `cut_pause.py <video> <t> --keep <s> --words` (repeated: it reads 0.8 s at a time); every later word
moves back by the cut, the gate's time-keyed allows move with them, the bites' placement script runs again, and the shift is written in the
new lock's note. A longer piece doesn't fit (time would have to open, which no lay-in tool does): another take or a shorter wording. The
takes are raw (tempo and chain D, no breath pass): an inhale the take kept in a short pause stays in the piece, so the pauses are read with
A3's own measure before the gate, and an inhale is muted (`fixflags.py --span`, its frames read first) and its pause cut to 0.12 s
(`cut_pause.py --keep 0.12 --words`).

**Time moved by a cut changes the gate's frame grids.** A3 and A4 read 20-ms hops and A11 0.5-s windows from the file's start, so a shift
that isn't a multiple of them reads the same audio on another grid: a pause at the 0.20-s bar can read 0.21, a word's decay can become an
80-ms A4 run, a float boundary can move A5's END onto the next word's onset, and A11's maybe-British reports move, all on samples proven
bit-identical to the locked narration. Such flags are allowed with that proof (gate_allow.json).

## The name check (`saycheck.py`), for any respelled name
A phoneme recogniser (`facebook/wav2vec2-xlsr-53-espeak-cv-ft`: CTC over 392 espeak phonemes from 53 languages, so the Spanish tap ɾ and
trill r, the American ɹ, e and ə, a+j and aɪ are separate symbols) reads the name's span (from the CTC word aligner, padded 0.1 s); the CTC
loss of every American pronunciation is compared with every native (or wrong) one over the same frames (GOP-SF); margin = best native -
best American, per frame. AMERICAN at +0.05 or more, NATIVE at -0.05 or less, UNSURE between (a fail). names.json per name:
`"ipa": {"us": <patterns>, "native": <patterns>}`, phonemes space-separated from the model's own symbols, `{a|b}` where either is fine,
written as MINIMAL PAIRS that differ only in what the ear judges (for a name with an r: ɹ against ɾ or r, the vowels open in both, since a
take with a plain vowel can pass the ear while a vowel-strict pair calls it UNSURE). A name whose contrast is subtle (a vowel, no r) gets
its own cut-offs in its entry (`us_at`, `native_at`), checked against the ear and a formant measure first. It prints what it heard ("m a ɾ i
s o l"): the reason in plain symbols.
- `EDIT tools/voice/saycheck.py <wav> --name "<name>" --text "<what the wav says>"` or `--at <t0> <t1>`;
  `saycheck.py --video <video> [--beats S12 S13] [--final F]` (every respelled name with "ipa" in the narration).
- Tempo and chain D move a margin by about 0.04: a take near the line can flip, so the measure is made on the take as it will sit.

## Wiring into the line
- Before `render`, `patch`, `score` and `finish`, `pipe.py` runs `voice_lock.py <video> verify` when `videos/<video>/voice_lock.json` exists;
  exit 1 refuses the step.
- `gate.py`'s sound half calls `gate_sound.py <video>` without `--only`, so A10-A13 and LOCK run in it. A11's first pass on a new narration
  is the slow one; `voice_chain.sh` ends with the same gate, so the guard's per-window cache is warm by the time `pipe.py gate` asks.
- stages.py's `voice` stage is done only when voice_lock.json exists AND `voice_lock.py <video> verify` passes.
- `pipe.py <video> voice`: `voice_ready.py <video> require` -> `bash tools/sound/voice_chain.sh <video>` -> `voice_lock.py <video> lock --note
  "<the gate's PASS line>"`.

## Proof (what the tools were held to)
- **The lay-in**, dry run on two re-voiced names with six takes each: it picked the take the ear had passed both times, rejecting the
  others by the name check (NATIVE or UNSURE) or by an anchor landing more than 2 frames off. It found an anchor a hand-made fix had never
  checked (a page mark on a phrase the new take said 160 ms early: without `--skip-anchor` it refuses every take). `--apply` on a scratch
  copy reproduced the hand-made lay-in within 0.48 ms and 0.16 dB (residual -84 dB), everything outside the piece bit-identical, the lock
  re-stamped and verifying after.
- **A10**: on a narration with one doubled syllable heard by ear, exactly one flag, on it (A1-A9 had passed it); on an approved hour-long
  narration, 0 flags in 304 windows once numbers and abbreviations were read as said.
- **A11**: on an approved narration, PASS with 0 hard ACCENT (no false fail). On a narration flagged by ear for four British stretches, all
  four sat inside its hard flags, each one "allowed" by keeping its section; A11 can't be allowed, so all four would have stopped the gate.
  The price: two extra sections re-voiced that the ear did not call.
- **The lock**: on a scratch video, 15 writers run against it all refused with exit 4 before touching a file (read-only modes ran); a write
  made around them (a plain numpy write) was caught by `verify` (exit 1) and by the gate's LOCK line.
- **The name check**: 6 of 6 ear verdicts sorted (both native readings rejected); the same accept/reject call as the r-colour formant
  measure on 45 takes of one name (American margins +0.085 to +0.134, NATIVE -0.052 or lower); and it found one native reading in a
  delivered narration that nobody had flagged.
- **autopick**: takes once kept "as is" with British stretches: all REJECT, NO CLEAN TAKE, exit 2, never kept; after the rewording the exit
  asks for, it picks a clean take. Live, three takes voiced and judged in about 4 minutes: the native name reading rejected, a clean one
  picked, the splice printed.
- After any change to fragments.py, ctcalign.py, saycheck.py, names.json or the accent guard, the checks are run again on the creator's
  takes with known verdicts (`MEDIA/voice/guard/approved/` and `flagged/`, each flagged span with its kind): every verdict must hold.

## What it does not catch (open risks)
- **The opening screen** rests on a few verdicts and the same-text test (cold 3 of 3 TIRED, warm 3 of 3 OK). Its reading is content-driven,
  so it judges only where a cold start can be; a lines-before request is trusted to its construction. A first section whose hook is calm by
  its words can read low after the warm-up too: it is voiced again up to 4 times, and a section that still reads low is said in the report,
  never kept silently. It reads pitch peaks only: a cold start that keeps its pitch but goes breathy passes.
- **A13 reads hiss and voiced tails only**: a stop's release or a vowel cut mid-sound stays A1's, against the same layout. A cut into the
  NEXT word's opening hiss ("of [th]em") is flagged too, under the word before.
- **A13 can't see inside a lay-in**: the layout never held the new piece, so its runs don't line up with the reference and are skipped; a
  lay-in's edges rest on voice_layin.py's own end search (the first 16 ms under -48 dB after the last frame over -30 dB, which keeps a hiss
  louder than -48) and its span gate. The joins inside the layout are held at the layout instead (span_takes' cut past the hiss,
  proto_narration.py refusing a beat that ends on sound).
- **A cut word end (missing sound) is A1's class**, not A10's: A10 hears extra speech, not lost speech. The lock removes most of its cause
  (no chain re-runs after the voice is final), not the detector.
- **A11 misses what the guard misses**: short British stretches, a date said British inside an American line. It is only as good as the
  creator's flagged set: every accent heard by ear goes into `MEDIA/voice/guard/flagged/` and the guard is rebuilt.
- **The name check knows only names with an "ipa" pair**; a new foreign name needs its pair written before its video's names stamp (or
  `"measure": false` with the reason), and a pair with no audio yet is proven by its first take. The 0.05 cut-off was set on one name's
  judgements; a subtle contrast gets its own cut-offs.
- **No fix at the source works yet**: a hard foreign name can come out American in only about a third of takes, so its sections cost about
  7 takes; a new respelling or a dictionary phoneme rule, measured, is the next lever.
- **Anchors come from the code by pattern** (`'S12', '...'` in `src/<src>/*.ts*` and `score/cues*.py`): an anchor written another way (a
  computed phrase, a frame number) is not seen; `--anchor` adds it by hand.
- **Speed**: the gate's A10 takes minutes on a long narration (cached per window after that, seconds for a lay-in's span), A11's first pass
  on a new narration the longest (incremental later); the lay-in judges a take in about a minute (Whisper, the guard and the phoneme model
  load per take).
- **The lock is a hash, not a wall**: a tool without the guard line can still write the narration; `verify` (the gate's LOCK and pipe.py)
  is what stops a render on it.

## Research (sources; what was adopted and why)

**1. Word times from the audio (the lay-in's anchors, A10's windows).**
- *Adopted:* `torchaudio.functional.forced_align` with `WAV2VEC2_ASR_LARGE_LV60K_960H` (MIT, 1.18 GB, 20-ms frames), each edge then snapped
  to the measured onset/offset. torchaudio had planned to drop forced_align in 2.9 (pytorch/audio#3902, 2025-04-24); the 2.10 release
  (2026-01-21) keeps it ("preserved and will remain"); it runs in torchaudio 2.11 with no warning. Its free decoding hears a stray doubled
  syllable plainly, and the forced words land within 20-24 ms of a hand-measured lay-in.
- *Rejected for anchors:* ElevenLabs' character times (0.04-0.08-s steps, and up to 0.5 s late: a sentence's last word can sit on the breath
  after it); Whisper / faster-whisper word times (F1 64.0 at 50 ms against 79.9 for WhisperX's wav2vec2 alignment and 91.0 for MFA, arXiv
  2509.09987; a word boxed 155 ms after its first sound); Qwen3-ForcedAligner (arXiv 2601.21337, 2026-01-29: an 80-ms output grid, can't
  hold 33 ms; its package pins transformers 4.57); MMS_FA and ctc-forced-aligner's default model (CC-BY-NC 4.0, torchaudio docs 2.11); NeMo
  Forced Aligner (77 ms mean boundary error on TIMIT, Aligner-SUPERB, 2025-05-07).
- *Kept in reserve:* Montreal Forced Aligner, the most accurate (18 ms mean boundary error on TIMIT against 27-46 ms for CTC aligners,
  Aligner-SUPERB 2025-05-07; 72.8% of boundaries within 25 ms against 52.7% for WhisperX, arXiv 2606.10675, 2026-06-09), but it needs conda
  + Kaldi. Every anchor is snapped to the onset in the audio and compared old against new by the same method, so the CTC frame is only the
  search's start; MFA comes in only if a lay-in's anchors measure worse than 2 frames on a proof.

**2. Was a respelled name said the American way.**
- *Adopted:* `facebook/wav2vec2-xlsr-53-espeak-cv-ft` (Apache-2.0, 392 espeak phonemes incl. ɾ, r, ɹ, ɚ, ə, e, aɪ, oʊ, ʝ: read from its
  vocab.json) with Goodness-of-Pronunciation by competing hypotheses (GOP-SF: the difference of two CTC losses over the word's frames; AUC
  0.91 on real errors, arXiv 2507.16838). Its phoneme error on accented English is within about a point of the best open models (10.8
  against 8.4-11.2, arXiv 2603.29042, 2026-07-13). No espeak needed: the tokenizer decodes with `do_phonemize=False` (with the default it
  raises ImportError for phonemizer), so the patterns are written by hand in names.json.
- *Rejected:* free phoneme decoding alone as the verdict (it is printed as the reason only); POWSM (17.5 PER, same source); accent-ID
  classifiers (one verdict per utterance, can't isolate one word); the formant trick as the general method (it needs an r in the name; kept
  as the cross-check).

**3. ElevenLabs (its docs carry no dates).**
- Pronunciation dictionaries: phoneme rules (IPA/CMU) "only work with eleven_v4, eleven_v4_turbo, eleven_flash_v2 and eleven_v3"; other
  models skip them (alias rules only); up to 3 dictionaries a request via `pronunciation_dictionary_locators`; PLS is case-sensitive and
  "only the very first replacement is used" (elevenlabs.io/docs, pronunciation dictionaries; best practices, prompting, pronunciation).
  Inline IPA between slashes on v4 is "more consistent than previous models" but "results can still vary": generate more than once and
  pick. **Tested, rejected for now:** a two-word foreign name sent as inline IPA, 3 takes: the second word came out American in 2 of 3, but
  the first word was swallowed in all 3 (both recognisers lost it), so autopick rejected all three.
  **Tested at the source**, on one line that says two respelled names, 5 lines-before takes an arm, each name judged by saycheck and by its
  formant check (they agreed on all 40 judgements):

  | arm (5 takes) | name A American | name B American |
  |---|---|---|
  | control: names.json respelling | 2 | 4 |
  | respelling + `language_code="en"` | 1 | 1 |
  | plain names + an ElevenLabs alias dictionary (alias = the respelling) | 0 | 3 |
  | plain names + `language_code="en"` | 0 | 1 |

  **Neither makes the American reading reliable, so neither is a default**: `language_code="en"` does not stop v4's native reading (worse
  than the control on both names), and the alias, which hands the model the same respelled text, did no better. The two names flip
  independently. The switches stay available, off: `[tts.elevenlabs] language_code` / `pronunciation_dictionaries` (dj tts),
  `span_takes.py --language-code en --dict ID:VERSION --plain NAME`, `PIPE tools/voice/eleven_dict.py create|list|archive`. What is reliable
  is the measure: every take judged, and enough takes (names.json's `"hit_rate"`). A dictionary phoneme (IPA) rule stays untested.
- Request stitching: `previous_request_ids` / `next_request_ids` (up to 3 each, ids under 2 h old) override `previous_text`/`next_text`;
  "not available for the eleven_v3 model" (its stitching guide). *Not adopted:* the lines-before way is what the ear passed; stitching
  changes the request and would need its own blind round.
- `seed` is "best-effort ... determinism isn't guaranteed" (API reference): takes are judged, never assumed equal across runs.

**4. Automatic checks before a human listens.**
- *Adopted:* two recognisers of different families against the script (Whisper + the CTC letters), since one family judging its own errors
  is biased; mixed verifiers with rank averaging cut WER 12% relative at N=10 with no loss of speaker similarity (arXiv 2607.08256,
  2026-07); free CTC output outside the aligned words as the extra-speech check (an alignment-based detector of skipped, repeated or
  invented words caught about 95% of errors at about 49% precision, arXiv 2609.12855: a high-recall screen, so A10 fires only on whole
  extra words or 4+ letters over voiced sound, its rules set on an approved voice to 0 false alarms); every threshold calibrated on the
  creator's own approved and faulty takes (no source publishes a production cutoff: seed-tts-eval, NeMo Curator's UTMOS 3.5/4.0 "from the
  distribution").
- *Rejected:* UTMOSv2 as a gate (different scores on repeated runs of the same audio, arXiv 2603.10904); stock Whisper alone for stray
  syllables (it tidies disfluencies away: CrisperWhisper had to fine-tune it for verbatim text, arXiv 2408.16589, 2024-08-29).
