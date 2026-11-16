# The reviewer's eye: the creator's notes, predicted before they watch

*Part of `STANDARD.md`. A reviewer agent (`.claude/agents/reviewers-eye.md`) watches a finished video, a prototype or a built section
through a packet of frames, words and numbers, holds it against the creator's rules (`rules/`) and casebooks (`cases/`), and writes the
notes the creator would give, with times, in plain words, each with the rule behind it, so they are fixed before the creator sees it.
No model is needed to build the packet; the reviewer is the only model step.*

## How far to trust it (measured)
Blind on a finished long video (its rules cut before the creator's review of it), scored against the creator's real notes on it: it found
about 3 in 10 of their notes, and about 1 in 5 of the judgement ones (taste, pace, picture choice), with two model sizes alike. What it
does flag at high confidence is almost always a real fault on the frames (46 of 47 such notes), but mostly not what the creator says. On
a video the creator had already passed it wrote about 150 notes: 18 high (real slivers the flash scan had missed, restatements of the
creator's own polish points, small faults they let pass) and over 130 medium and low ones the creator would never give. A Short's framing
notes it found at high confidence.

So it is a pre-read that catches real faults, never a stand-in for the creator's watch: fix its high and medium notes, read the low
ones, and expect the creator to find what it misses. Nothing in the line waits on it. Once the creator's own notes on a video exist, it
is calibrated on them (below), and trusted only as far as it measures.

## Where it runs
The rule is in `rules/LONG_FORM.md`: on a prototype and on every built section before the creator sees them; the first full render's
watchable copy goes to the creator the minute it exists, with no eye round of the whole film between the render and them (their watch is
the fix list, `standard/PIPELINE.md`).

## Standing checks: every eye round, whatever rules it is given
The faults that pass every machine check and still cost a viewer. Every round, whoever runs it, goes through the whole video for each and
writes a note on every spot (the full text: the agent's "Standing checks"; the machine behind each runs in the gate):

| # | The fault | The machine beside it |
|---|---|---|
| 1 | A text card standing in for something the words say you can see | `qa_cards.py` (gate B19), `qa_still_words.py` CARD_FOR_MOMENT and STILL_UNDER_ACTION (B20) |
| 2 | A sound effect the creator hasn't approved (the mix report names each effect's source) | `score.py` refuses unrated sounds; the eye reads the report's effects list |
| 3 | A still where the words move; a mark too small or in a corner | `qa_still_words.py` STILL_UNDER_ACTION, MARK_SMALL, MARK_CORNER (B20); B25 MARK_SMALL |
| 4 | A logo or emblem off the frame's centre left to right, measured on the frame | `qa_centred.py` LOGO_OFF_CENTRE (B21) |
| 5 | The thing the words name not found at a glance (off-centre, small, dim) | `qa_shots.py` SUBJECT_LOST (B22) |
| 6 | Artwork where the real subject could be shown, artwork close together, face icons off their circle | `qa_shots.py` ART_OVER_REAL, ART_CLOSE (B22); `qa_centred.py` ICON_FACE_OFF, ICON_NOT_REAL (B21) |
| 7 | A murky picture where a brighter pick says the same (a scene meant to be dark stays) | `qa_shots.py` DARK (B22) |

## The parts

| Part | What it does | Where |
|---|---|---|
| Packet (no model) | One decode of the MP4 (GPU when there is a CUDA card, else the CPU): every cut found; per shot its first frame, the frame 3 frames in, the middle and the last, on a shot sheet beside the words said over it and what is on screen (from the asset ledger when its delivered file is this MP4); a contact sheet per 30 s (a Short: per 15 s); the transcript with its times; loudness per shot; the script's beats; the QA gate's report. `packet.md` is the index | `tools/eye/eye_packet.py` |
| Close looks (no model) | one frame at full size; every frame of a short window, tiled, to check a flash or a cut frame by frame | `tools/eye/eye_frame.py`, `tools/eye/eye_strip.py` |
| Rules | the creator's rules and casebooks (`rules/`, `cases/`: every past verdict on a craft, passed and flagged), or a rulebook distilled from them; a blind test cuts them at a point in time so the rulebook sees nothing the creator said about the video under test (`tools/eye/eye_sources.py`) | `rules/`, `cases/` |
| Reviewer | the agent: reads the rules, then the packet shot sheet by shot sheet, and writes notes the way the creator gives them: the time, what's wrong in plain words, the fix, the rule, a confidence | `.claude/agents/reviewers-eye.md` |
| Scorer (no model) | merges the parts' notes into one list; matches predictions with the creator's real notes; recall and precision per confidence cut | `tools/eye/eye_score.py` |

## How to run it on a video

1. **The packet** (about 100 frames a second on a GPU; a 9-minute 4K film in about 6 minutes):
   ```
   EDIT tools/eye/eye_packet.py MEDIA/videos/<video>/export/<name>_v<N>.mp4 --ledger <video> --script videos/<video>/script.md --qa videos/<video>/QA_v<N>.md --out MEDIA/videos/<video>/eye/v<N>
   ```
   `--ledger` only when the asset ledger's delivered file is this MP4 (another version's shot list would mislead); a Short needs
   `--words <build/captions/words.json>` (the default is the `.srt` beside the MP4); `--reuse` rebuilds the sheets from an earlier decode in
   seconds; a blind test reads the script as it was with `--script git:<rev>:videos/<video>/script.md`.
2. **The reviewers** (the Agent tool, with `.claude/agents/reviewers-eye.md` as the agent, model sonnet unless the task needs opus): a long
   video in parts of about 15 shot sheets each plus one whole pass, launched together; a Short or a video under about 4 minutes in one
   pass. The exact task texts are at the end of the agent file. Each writes `<run>/part<k>.json|md`, `whole.json|md` or `all.json|md`.
3. **One list:** `PIPE tools/eye/eye_score.py merge <run>/notes.json <run>/part*.json <run>/whole.json` -> `notes.md`, in time order, each note
   with its time, the creator's kind of words, the fix, the rule and a confidence. Fix the high and medium ones before the creator sees the
   video; read the low ones.
4. **Calibration** (when the creator's real notes on a reviewed video exist): a key (`key.json`: each of their notes with its time, their
   words, whether it is a judgement note and which tool, if any, catches it), `eye_score.py candidates <key.json> <notes.json>` to match by
   eye (the same spot within about 5 s and the same issue: the fix would be the same), a match file, then `eye_score.py score <key.json>
   <match.json> ... [--md <out.md>]` for recall over all their notes, over the judgement notes and over the ones no tool catches, and
   precision strict and judged, per confidence cut. Every miss becomes a case in `cases/`, so the next round's rules hold it.
