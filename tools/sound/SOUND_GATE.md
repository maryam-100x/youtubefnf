# The sound gate: what each check catches, and its numbers

`EDIT tools/sound/gate_sound.py <video>` runs every check below after the voice chain (`bash tools/sound/voice_chain.sh <video>`) and
before any render or sample. A flag is a fault until its own frames prove otherwise: it is fixed (the chain, a fix tool, a re-take) or
proven wrong and then allowed in `videos/<video>/gate_allow.json` with the proof in words. Every check takes `--final/--raw/--words/--script`,
so the same code runs on any saved state of the voice.

Levels are RMS dBFS of short frames (5, 10 or 20 ms as named); "digital silence" is under -60 dB unless a check says otherwise.

## A1 tails (`tails.py`): chopped word ends
Every word end of the final against the same point in the raw takes (normalised cross-correlation per speech run of the final; the chain
only cuts and mutes in pauses, so a run's offset holds for its words).
- Lost release: the take 6 dB or more over the final for 15-60 ms, at -38 dB or louder; a lost stop burst; a lost f/s/t hiss (over 3.5 kHz).
  A final c or "que" counts as a stop.
- "Lost" means frames over -48 dB with the final 6 dB under; a release whose peak the final keeps within 3 dB and half its core within
  6 dB is there.
- Not a release: a segment holding within 12 dB of its peak for over 60 ms (a breath; a release dies within 10-50 ms); anything past
  10 ms before the next word's onset in the take; "-ng" (a nasal, no release).
- A short word's point is its middle, inside the run that holds it; a word whose times sit in the pause before it goes back to its last
  sounding 5 ms, else it is listed as not found.
- Fix: `tails.py --fix` lays a lost end back from the take (up to 3 rounds, checked again each round); "NO ROOM" (the next word sits
  where the release was) goes to `relay.py` or `retime_room.py`, or a re-take.

## A2 clicks (`mutescan.py`, fix: `fixmutes.py`)
- SCRAP: after 30 ms or more of digital silence, a lone burst over -55 dB, 1-12 frames of 5 ms (60 ms at most), peak over -32 dB, quiet
  after. A scrap that is the take's own lone burst (correlation 0.8+, the take under -45 dB before it, after it only its decay 10 dB+
  under, dying under -45 dB) is a word's release and is left.
- CHOP: a mute (digital silence over 40 ms) that starts within 0.22 s after a word's end while the last 10 ms are still over -42 dB.
  Listed; whether a mute cut a word is A1's call.

## A3 pauses (`pauses.py`, fixes in the chain: `pausefix.py`, `inner_gaps.py`, `a3fix.py`)
- The pause runs from the end of the word's last sound (frames over -38 dB) to speech again near the next word (3 20-ms frames over
  -30 dB).
- LONG: over 0.20 s between two words of one sentence, commas included (the chain makes them 0.12 s; a release or a short sound left
  in the pause measures up to 0.19 s after it); over 0.30 s after a sentence end inside a beat, and between beats (holds and bites, over
  3 s, are skipped).
- BREATH: 50 ms or more over -45 dB centred 1.5-3.5 kHz, under -25 dB, inside the pause (after the word's own decay and spelling guard,
  before the next onset ramp). A typical inhale between words measures -32..-45 dB, 70-380 ms, 2.0-3.0 kHz.
- Not a pause: a closure dip inside a word, words running together, a word's own f/s, the next word's "s"/"f" ramping in.

## A4 noise (`noisescan.py`)
40-ms windows (20-ms hop), level and spectral flatness over 300-8000 Hz (1.0 = white noise, a vowel ~0.00-0.05, a breath or an s
0.05-0.30).
- NOISE: inside a pause (A3's inside, before the first word, after the last word's guard), 80 ms or more over -55 dB at flatness 0.35+.
- STATIC: anywhere, 200 ms or more over -25 dB at flatness 0.45+.
- Why these bars: single windows of a clean take's floor reach 0.35-0.55 but never for 80 ms; a word's own f is as flat but -29..-35 dB,
  and an "f" word can reach -19..-23 dB for 120 ms (the static bar is 200 ms). Buzz and hum are not checked.

## A5 takes (`takecheck.py`)
- WORDS: Whisper's words (captions/words.json) against script.md beat by beat, after normalising numbers, $, ordinals, numerals and
  "gonna"; a name in names.json heard in a spelling within 0.75 of it is not a difference. A misread word is a re-take.
- END: a phrase's last word that ends in v or f by how it is said needs 20 ms or more of frication (over -45 dB, centred 2.5 kHz+) within
  120 ms after its last vowel. s/z/th ends are not checked (too many clean ones read as cut by the same rule).
- LEVEL: sentence loudness (R128) against the median of the 3 sentences either side, bar 2 LU (a clean voice spreads ~1 LU at the 90th
  percentile, 1.5 LU at most). It guards gross jumps (a re-voiced line several dB off).
- WORD: a content word with 100 ms or more of sound on its span, 12 dB or more under its sentence (a whispered word; WORDS usually
  catches it first, as Whisper misses it).
- The chain runs A5 early on the laid voice (`--only A5`): a misread word stops the chain before the long passes.

## A6 names (`names.py`, `names.json`)
Every proper noun of the script's VOICE lines that isn't plain English needs an entry in `tools/sound/names.json` before any voice:
`"say"` (the respelling the TTS is sent) or `"as is"`. A proper noun: a capital that isn't only a sentence's first letter, an acronym,
letters with digits; plain English: used in lower case in the creator's own VOICE lines (every `videos/*/script.md`); a sentence's first
word only when it opens a run of names or is capitalised mid-sentence elsewhere. The table starts empty (`{"names": {}}`) and grows
with every video.

## A7 scraps (`scraps.py`, fix: `fixflags.py --only A7`)
A word's head left before the word at a join of two takes. An island of sound 30-200 ms, quiet (under -50 dB) 40 ms or more before it
and 40-120 ms after it, peak -20 dB or louder, no Whisper word over it, 80 ms or more after the word before, the next sound 150 ms or
longer, and the island's first 50 ms shaped like the next sound's (cosine of 24-band log spectra 0.90 or more).
A real short word with a silence after it can read the same (the captions model put it on the next word's start), so an A7 flag is
checked by its frames and by a second transcription of the window before anything is muted; `fixflags.py` mutes A7 islands only when
asked.

## A8 chain (`chainmatch.py`)
Every stretch went through chain D (`voice_level.py --chain mb`). Crest = the 99.9th percentile of the samples over the RMS of frames
within 25 dB of the loudest. A flag: a beat 2 dB over the narration's median crest, a 4-s window 3 dB over (the window bar is higher as
one loud sentence moves a window), loudness 4 dB off, or 3 or more samples at 0.999 of full scale (clipped).

## A9 inserts (`insertcut.py`)
Where an interview bite splits the narration: no 10-ms frame over -55 dB within 20 ms of the split (CUT); no sound over -45 dB shorter
than 0.2 s between the split and the next speech's onset ramp (LEFT: a word's release played after the bite).

## A10 fragments (`fragments.py`)
Voiced sound of 60 ms or more that no word of the script covers (a take's context tail at a splice, a doubled syllable): windows around
every join and every voiced run the word boxes leave uncovered (pitch present, 60 ms+, peak -30 dB or louder); the script's words forced
onto the window by a CTC model and the same model decoding it freely; a run 40 ms clear of every aligned word where the free decoding
hears letters is a FRAGMENT.

## A11 accent (`tools/voice/accent_take.py`)
The voice guard on the final narration. A hard ACCENT fails and can't be allowed (the section is re-voiced whole); an "ACCENT?" (maybe)
is reported only (on an approved voice it marks about a fifth of the sections, so the per-take pick rejects it instead).

## A12 opening (`tools/voice/opening.py`)
A request that opens cold keeps its pitch peaks down: peak_gap (semitones, the opening's F0 p95/p98 over its first 4-6 s against the
request's own) under 0.0 is TIRED. Judged only where a cold start can be; never allowed (the section is voiced again).

## A13 hiss (`hisstails.py`, fix: `hisstails.py --fix`)
Every place the final goes quiet after a word, held against the narration as laid out from the takes (`narration_laid.wav`, else
`narration_prechain.wav`). The final's sound end is the first 5-ms frame under -45 dB broadband and under -50 dB in 4-12 kHz; the
reference's tail is counted while it stays over either bar without a break; a flag is 15 ms or more lost with its loudest frame at -40 dB
or louder. Voiced tails too: 30 ms or more of the reference over -40 dB centred under 1.2 kHz where the final sits 12 dB under.

## LOCK (`tools/voice/voice_lock.py`)
With `videos/<video>/voice_lock.json`: the narration and the word files the picture anchors on must hash as locked. A changed file fails
the gate and can't be allowed: restore it, or unlock with a reason and run the writers again.

## What the gate does not hold
- The voice's delivery (too loud in feel, flat, rushed) when the measured level is within the bars: that is the creator's ear.
- A take's own cut s/z/th or stop: A1 sees only the chain's cuts, END only v/f. Such a take fails by ear and is re-taken.
- Buzz and hum.
