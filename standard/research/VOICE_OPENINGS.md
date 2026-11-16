# The tired, whispered opening and the swallowed word

*The fault: a cloned narration opens with an annoyed, exhausted half-whisper, and single words come out far quieter than the rest,
swallowed. It recurs from video to video, so it needs a lasting fix in how the voice is requested, not retakes. This file is the
evidence behind the house fix: the unspoken `lead_in` (`config/tts.example.toml` `[tts.elevenlabs]`) and the screen
`tools/voice/voice_check.py`.*

*Read with: `standard/SOUND_AND_VOICE.md` ("Voice: the bar": warm from the first word, nothing swallowed), `standard/VOICE_LOCK.md`
("The opening": the spoken warm-up and `tools/voice/opening.py`), `standard/research/VOICE_CRAFT.md`. Every number here is our own
measurement (M) on our own narrations, against a reviewer's marks of where the voice sounded tired or swallowed.*

## What it is (measured)
- **It sits where a voice request starts cold.** dj voices a long video in sections, each linked to the ones before by request id; the
  first section (and a `fresh_at` section, and a single-beat patch) has nothing before it. In one of our builds the three requests
  started at S01, S06 and S14, plus single-beat patches of S03 and S06; the soft starts were S01 (the opening sentence: CPPS 1.5 under
  the narration's median on average, pitch sinking to 87 Hz), S03's first word (a company's name: CPPS -6) and S06's "But" (-11 dB).
- **"Analysts expect":** "Analysts" 4.4 dB under the median level (it came out 5.5 dB under again in the next build: this voice says
  the word softly), "expect" with no voicing at all (0.00 of its energy in pitched frames), 5-7 dB under the figure said right after it.
- **Seeds don't fix it.** At stability 0.95 (the house setting) three seeds of the same request measured within 0.3 dB and 0.2 CPPS of
  each other: retaking until it passes doesn't work, the cause has to change.

## What fixes it (tested on one build's S01-S02, the house settings)
| Way | First sentence: CPPS | Pitch (median) | Level |
|---|---|---|---|
| A: no context (what dj did), 3 seeds | 8.70 | 117 Hz | -23.3 dB |
| P: unspoken context, `previous_text` "Alright guys, so here's what's going on, and it's actually pretty crazy." | **9.24** | **125 Hz** | -22.8 dB |
| S: the same lead-in spoken, then cut | 9.27 | 125 Hz | -22.6 dB |
| P2: "What is up guys! ..." (more hyped) | 9.34 | 119 Hz | -23.9 dB |
| P3: "And that is exactly why everyone is talking about it right now." | 9.02 | 117 Hz | -24.2 dB |

P is as good as S without the cut. In the pipeline: `config/tts.toml` `[tts.elevenlabs] lead_in`, sent as `previous_text` on any
request with no context (`tools/dj/tts.py`, `elevenlabs()`); kept out of the cache key so nothing approved re-voices; blank for Shorts
(`[tts.short]`: the Shorts voice was never flagged). The next build voiced with it: S01 opened clear (CPPS +1 to +6 over the median), no
tired-opening flag. Write this `lead_in` the way the creator talks: it steers the delivery, it is never heard.

The house goes one step further for the video's first section: a spoken warm-up (`[tts.elevenlabs] warmup`) voiced before it and cut
away, and `tools/voice/opening.py` screens every opening's pitch peaks against the request's own (`standard/VOICE_LOCK.md`, "The
opening").

## The screen: `tools/voice/voice_check.py`
Per word, against the narration's medians: level, voiced energy (whispered words have none), CPPS (breathiness). Flags QUIET (4+ dB
under, 7+ for a sentence's last word, words of 0.25 s or more), WHISPERED (under 0.25 voiced energy) and OPENING (the first sentence,
and each request's, 1.0+ under the median CPPS or 2+ dB under the level). On the build it was calibrated on, it flags exactly the
reviewer's marks: the opening, "Analysts", "expect". `--fix` lifts each QUIET word to 1.5 dB under the median (at most +6 dB, 15-ms
ramps): a vocal rider, gain only. (The tool's docstring has its later flags and options: LOUD, `--soften`.)

Run after `dj tts` + `dj captions` + `tools/motion/sync_words.py`, on every narration, long form and Shorts:

    EDIT tools/voice/voice_check.py <build/voice/narration_unlifted.wav> <words.json> --starts <request-start beats> --fix <build/voice/narration.wav>

(copy the narration to `narration_unlifted.wav` first and pass that as the input). A WHISPERED content word or an OPENING flag left
after that: re-voice the beat with context (inside its section, after the lines before it), or rephrase the line; then
`tools/voice/accent_id.py` as always.

## Limits
- Whisper's word times run up to ~0.15 s off on short words (a "four" read -12.6 dB on the breath before "thousand"): the level check
  skips words under 0.25 s.
- A sentence's last word falling ("room.", "mode.") is how sentences end; no reviewer flagged one. Only a 7+ dB drop counts.
- The screen is calibrated on one video's marks; every new note of the creator's on the voice gets measured here and the thresholds
  checked.
