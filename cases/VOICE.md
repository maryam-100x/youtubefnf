# The voice: the casebook

Every verdict of the creator on the voice goes here: the takes, the accent, pronunciation, pauses and joins. What the words say is
`SCRIPT.md`; the effects and music are `SOUND.md`. Read in every voice round. Method and entry format: `README.md`. The seed lines
below are the starting taste; the creator's cases join them under each heading and replace any line they contradict.

## Every word lands whole
**VO1** FLAGGED, in review after review: swallowed first words ("and", "so", "now"); missing final sounds (a plural s, the t of
"but", the k of "peak", the first letter of a brand name); swallowed syllables; an unintelligible word; a name mispronounced, or
spelled out letter by letter; a two-word name slurred into one -> the line: every word lands whole; a flagged word is regenerated
(fresh takes), never processed.

**VO2** FLAGGED: "they can hand bags to each other" heard as "they can handbags to each other" -> the line: a phrase that can be heard
as another word is voiced with the stress that makes its meaning (the stressed word in capitals in the take's text).

**VO3** FLAGGED: the s of one word running into the s of the next across a comma ("walks, cycling" heard as "ssscycling"), flagged again
after a fix that left an 80 ms dip between them -> the line: a comma pause can't separate two s sounds, and a dip is not a pause to the
ear; the words are reordered so no s or z sound meets another across a comma.

**VO4** FLAGGED: a respelling that fixed a name in one test sentence put a pause inside the name in the full script; a pronunciation fix
that turned into inserted pauses -> the line: a pronunciation fix is tested in its place, in the full script.

**VO5** PASSED: a name voiced from its written spelling, captioned right -> the line: no re-take needed.

**VO6** FLAGGED as a bugged voice: a word whose pitch leapt up ~x1.8 onto its unstressed second half (the stress thrown onto a
compound's second syllable), passed by every check -> the line: a leap like that onto a syllable that takes no stress is a broken
generation to the ear; a rise on a one-syllable word or a stressed syllable is emphasis.

**VO7** FLAGGED: a sentence-end word drawn out and warbling, its last sound running into the next sentence -> the line: a broken
generation; no measure catches it yet, so a flagged word is re-voiced (fresh takes, laid into the old slot), never argued.

**VO8** FLAGGED: a word's own fade muted to silence by a gap-closing pass (the word "five" cut off); PASSED: the words laid back from
the original take -> the line: a word's own fade is never muted, by any pass; a side whose level only falls away from the word (or only
rises into the next) is kept.

**VO9** FLAGGED: a word-final stop cut short (its release dropped as if it were the pause after it); a doubled stop release ("night-t")
-> the line: a word-final stop keeps its release (the burst ~30-100 ms after its closure), once.

## Tone
**VO10** (long form) FLAGGED: lines that broke the level: over-excited, screamed, high-pitched, whispered, creepy-whispery, sounding
like horror narration, disappointed and sad, a complaint where excitement was meant, robotic at a line's end, a big number
over-emphasized; PASSED: the flat, calm, matter-of-fact read across a whole video -> the line: long form has one calm, matter-of-fact
narrator from the first line to the last.

**VO11** (Shorts) FLAGGED: a whispered hook; a last line slower than the rest; a sped-up hook that sounded robotic; a read that felt too
fast; PASSED: a quick hook, set as the speed for every hook -> the line: Shorts get a faster, louder, excited creator read; the hook is
as quick as the rest, the pace between normal and fast; the speed comes from the generation, never from stretching the audio.

**VO12** FLAGGED: a standard take picked on its own and reused (a subscribe ask, an intro line), disliked once heard in the video -> the
line: a take is judged in its place, with the seconds around it.

**VO13** PASSED: a natural, real-creator delivery among voice tests; FLAGGED: a clone that cut off mid-sentence with an uneven tone and
unnatural pauses; sentence ends that didn't sound like a period; a voice pitched down artificially; a clone carrying the low quality of
the headset recording it was made from -> the line: the voice sounds like a person talking; the clone is made from the cleanest
recording there is; nothing is pitched or processed into shape.

## Accent
**VO14** (long form) FLAGGED: a British accent from one point to the end; the section still accented after only the flagged lines were
re-voiced; every re-take of a last section still accented -> the line: an accent slip means the whole section re-voiced from fresh
takes until one is clean.

**VO15** (Shorts) FLAGGED: a second half accented to the ear while the accent guard read it at 0.20-0.28 and the gate passed it as a
"maybe" -> the line: a Short's section the guard reads at 0.15 or more is accented to the ear; every such section is re-voiced whole
before the sound gate.

**VO16** FLAGGED: takes stretched 1.07-1.15x to fit the old picture's lengths -> the line: a take is never stretched to fit a slot; the
picture follows the voice.

## Cuts, joins and artifacts
**VO17** FLAGGED: a splice cut at a loudness dip inside a word (half the word left, its rest heard after the next phrase); a name
clipped mid-word at a splice; a patched section that sounded inserted; sounds left over after a fix -> the line: a cut's edges come
from the speech model's word spans, never a loudness dip; every join is read back before the creator hears it; a patch sits on word
edges, or the section is re-voiced whole.

**VO18** FLAGGED: a constant hum tone in a take; a click before a word; a loud word peaking and clipping; a de-esser dulling the voice;
voice-enhancer passes that changed the voice (one passed) -> the line: a fault is regenerated, never processed; nothing that dulls the
voice.

**VO19** FLAGGED: a re-voiced line much quieter than the line after it; narration uneven, its opening almost piercing -> the line: every
line at the same loudness; the whole voice levelled.

**VO20** FLAGGED: a processing bug that dropped 0.1-0.45 s of the voice around a name -> the line: the voice in every render is checked
whole against its take.

## Pauses and flow
**VO21** (long form) FLAGGED: 0.46 s between two sentences with a 0.22 s inhale inside, passed by a check that read the speech model's
word boxes (it had stretched the next word back over the breath); PASSED: the inhale muted, the pause cut to 0.25 s -> the line:
between sentences the pause is ~0.25 s and holds no inhale, measured on the audio's own onsets, never on word boxes.

**VO22** (long form) FLAGGED: a line coming in too early after the one before; PASSED: the version with a bigger gap -> the line:
sentences never run into each other.

**VO23** (long form) FLAGGED: ~7 s with no narration -> the line: a long stretch with no talking reads as if something broke.

**VO24** (Shorts) FLAGGED: 0.29 s between two sentences, far too long for a Short; gaps between lines everywhere; breaths and "um"s left
in; a Short opening on an "um"; a one-second gap inside a name; PASSED: the pause cut to 0.14 s by the measured tool, the word's own
creak kept -> the line: in a Short a pause between sentences is cut like every other gap, to ~0.07 s, by the measured tool only; the
creak is part of the word.

**VO25** PASSED: a held pause lengthened by silence alone -> the line: invisible to the creator.

**VO26** FLAGGED: a list's end not heard (the next sentence read on as part of the list) -> the line: the list audibly ends ("and
fireworks."), and the next sentence starts as a new one.
