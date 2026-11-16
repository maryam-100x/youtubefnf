# Self-review before anything reaches the creator

*Part of `STANDARD.md`. Every line is a fault that a first build got wrong and a check caught. Run it on every render, in this order; the
tools do the counting, the eyes do the rest. `qa_render.py` can't see a wrong picture: the frame sheets are not optional. The line's own
gates (`standard/PIPELINE.md`) run before this; the QA report's delivery checklist (`videos/<video>/QA_v<N>.md`) is ticked from it.*

## 1. The tools (minutes)
- [ ] `EDIT tools/qa/qa_render.py <mp4> --format long|short --words <words.json> [--voice <narration.wav>]`: every FAIL fixed, or kept with
      `--allow a-b` and the reason written next to it (a real interview bite in a HOLD, a designed black). Shorts: always `--voice`
      (Whisper's word gaps are not pauses: without it a Short reads many false "no talking" fails).
- [ ] `score.py`'s report: voice over music about 22 dB in long form (the band 20.5-24.0) or about 17-18 in a Short (16.0-19.5); "silences
      outside the designed ones: []"; each effect's "400Hz+ vs rest": on a Short, anything about 95% sub-bass is gone on a phone speaker,
      so give it a bright layer.
- [ ] `cd tools && PIPE voice/rhotic.py --sections ../videos/<video>` on every voiced section, and `rhotic.py <take.wav>` on every take:
      American 685-1100 Hz of F3 dip; under about 260 Hz is British. A story set in England pulls the accent: casual wording and a fresh
      request (`[tts] fresh_at = ["S03"]`).
- [ ] `PIPE tools/script/script_lint.py <script.md>` before voicing (`pipe.py <video> script` runs it as the gate).

## 2. The frames (2-fps sheets of the whole render, then 30 fps around every flag)
- [ ] Frame 0 shows what the first word names (never a generic establishing shot before the picture the first words are about).
- [ ] Every clip's span stays clear of its source's own cuts: check 30-fps sheets at both edges (the next scene's first frames after the
      subject, a single frame of another shot before the cut, the source's logo card after its last line, a news channel's wipe, a crowd
      shot after a speaker).
- [ ] Bars: a Short shows no letterbox bars (fill the frame: measure the rows) unless the bars are the point; long form shows a letterboxed
      source whole with its own bars, never cropped and blown up (gate B4 LETTERBOX_CUT).
- [ ] Pages read at the size they're watched: a TV for long form, a phone for Shorts (capture a Short's receipts with
      `node tools/footage/capture_page.mjs <url> <out.png> <selector> --mobile 1 --width 360`); the quote lit as it's said; no depth blur
      over it; nothing cut at the frame edge; page to page is a cut, never a fade from black.
- [ ] Stamps and overlays sit on clean areas, never over body text; one line (a stamp that wraps reads as two).
- [ ] Subtitles clear of a broadcast's own lower third.
- [ ] Nothing held still: long form 2 s, Shorts 0.8 s (a drift must be visible at feed size; a slow push on a wall of small text reads as
      frozen).
- [ ] No face under type.

## 3. The sound
- [ ] Never digital silence: a designed stop has something under it; the music's designed stops are listed in the cue sheet's `SILENCES`.
- [ ] A real person's voice keeps its own sound, the bed pulled out under it, and a "Name: words" subtitle.

## 4. Shorts only
- [ ] The first frame is the package (the payoff visible, bright), the flash open alone on frame 0.
- [ ] A new picture every 0.5-2.2 s, each on the word it shows.
- [ ] Captions: Whisper's spellings fixed in script.md's `## Caption fixes` (`- "17 -year -old" = "17-year-old"`); one key phrase per beat
      marked in the VOICE line (`*key*` in the look's caption key colour, `**hero**` for a hero pop); no big on-screen number that repeats the caption.
- [ ] It ends right after the last word (the bar about 0.4 s; the QA gate's band 0.15-0.8 s).

## 5. Packaging
- [ ] The title is the creator's pick or scored by `standard/SCRIPTS_AND_PACKAGING.md`; a Short's title by its Shorts title rules there.
