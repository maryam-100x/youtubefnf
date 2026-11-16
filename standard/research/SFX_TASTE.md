# Sound taste by job: the Sound Test, and what the house rounds taught

*The question: how to pick sound effects that a creator hears as right, instead of library picks that sound "fine" to the chat. The
method: the creator rates each effect blind, for what it is trying to represent, one job at a time. Their fits are the only effects
placed for that job; a job with no fit yet goes into the next round, never a pick of the chat's. The house set
(`assets/house_sfx.zip`, its `manifest.json` names one sound per job) came out of three such rounds with one reviewer and the reviews
of the videos that used them: it is the starting taste, and the creator's own rounds replace its picks.*

*Read with: `standard/SOUND_AND_VOICE.md` ("The house effects and the palette", "The creator's taste": the procedure as the house rule),
`tools/sound/palette.json` (built from the house set by `tools/sound/palette_from_manifest.py`; every verdict recorded by
`tools/sound/sfx_verdict.py`), `standard/research/SOUND_CRAFT.md` and `cases/SOUND.md`.*

*Evidence: one reviewer's blind verdicts on 391 sounds in three rounds, and on the effects of the builds that used the fits (the taste of
one person: a starting point for another creator, never a law), plus our measurements of the sounds (length, spectral centroid,
loudness, the share of energy above 400 Hz). No sound ids or library names are kept here.*

## The method, and why each part is there
1. **By job, not by sound.** A job is what the sound stands for ("a system says no", "a message lands"); the reviewer rates each sound
   for what it is trying to represent. A sound that is good in itself can still be wrong for its job.
2. **Blind and levelled.** Previews are numbered, never named, and levelled alike (95th-percentile 50-ms RMS at -18 dBFS, peaks under
   -1 dBFS), so the loudest sound doesn't win.
3. **6-12 candidates of clearly different kinds** per job: a round of near-identical sounds teaches nothing about the taste.
4. **Every verdict recorded at once** with the reviewer's reason in a word or two, and each sound's length, centroid and loudness
   beside it: the lessons below come from reading verdicts against those measures.
5. **The creator's own pack is rated whole**, when they have one: sorted into jobs by file name, compilations split into single sounds,
   Keep or Delete per sound with the file names shown.
6. **The test is not the last word.** A fit is checked again in the real cut: the review of a video can turn it down there (below).

## Round 1 (68 sounds, 10 jobs)
| Job (what it stands for) | Fits | Rejected | What it tells us |
|---|---|---|---|
| glitch: a logo or a screen glitching, "signal lost" | a radio-interference burst (the closest to a glitch the reviewer could imagine); two crackles (more static than glitchy); a connection-failure sound (okay) | designed glitch transitions, data/sci-fi computing sounds, a pitch-down, digital static | a glitch is a short, dirty burst like a signal breaking up, not a designed whoosh-transition |
| error: a system says no | a redesigned Windows error; a bass error tone; a futzed walkie-talkie beep | buzzers, quiz-style "wrong" sounds | real-device errors, not quiz-show buzzers. The first two are 93-97% sub: they vanish on a phone (one measured -15 dB above 400 Hz against the mix even with harmonics), so the walkie beep carries a Short |
| notification: a message lands | a phone's own notification tone (the best of the set), and three others | bright, tinny UI tones, menu blips | a phone's own tone, mid-range (centroid 750-1,300 Hz) |
| notification burst: many messages at once | none (all four rejected, even the burst of a tone whose single version was a fit) | | many messages = one good tone, never a spammed burst (the reviewer's own idea, tested and dropped) |
| impact | a sudden heavy percussive hit, a cinematic deep boom, a dark small stinger, a fast short sci-fi hit | a simple hit, a thin reverb thud, a whoosh-to-impact, a glitch impact | deep and clean; thin, whooshy or glitchy hits are out. A fit in the test is not a fit everywhere: the deep boom on a date popping up was a bad one |
| pop: an item appears | four soft, rounded pops | four others | soft, rounded, low-mid pops (centroid ~500-2,100 Hz); bright digital or squeaky pops out |
| whoosh | two (one for the faster moves) | bright flybys, wide designed swooshes, harsh noise | soft and airy |
| click | a real mouse click (the best of the set), and one other | heater-fan clicks, a double click, a tiny plastic button | a real mouse click |
| stamp | a heavy, distant wood thud (weak but doable) | both rubber stamps, the hollow wood thumps | nothing good yet: round 2 |
| typing | one take for phone texting, one for a mechanical keyboard | two generic PC typing takes | one take per device |

## What the reviews of the videos added (in context)
- **The fits beat the guesses.** In one build the logo glitch, the no-internet error, a staff notification and a glitching year were
  all bad; the next build put the round's fits there and the reviewer heard it as much better. Still not right: two word-slams each
  built from two fits layered (a glitch tear + a dark stinger; a radio burst + a heavy hit). Two good sounds together on a word slamming
  in don't make one: a slam is its own job.
- **Good and bad in one review.** Good: a mark at ~46 s (a marker sound, synced, heard as right for marking) and a low note on the cut
  to black (a suspense stinger, liked like a bass drop). Bad: the phone ring (it hurt the ears), TV static on a cut and a rubber stamp's
  click (no purpose heard), a notification used as a mark, a cash register on a billion, a deep boom on a date popping up. The
  reviewer's idea for the date: mechanical keyboard typing, with the date typing itself.
- **Sync:** a highlight's mark came 1-2 s before the highlight and a second stamp 0.24 s before it landed: an effect sits on the frame
  its action starts, measured from the composition's own timings, never placed by ear.
- **Context counts:** a glitch rejected in the test passed once under a word slam (only its quiet build-up played: its peak is 1.0 s
  into the file and the cue cut it at 0.45 s), and failed in the next build. Judge the sound that actually plays.

## Round 2 (37 library sounds; previews levelled as above)
| Job | Fits | What it tells us |
|---|---|---|
| slam: a big word slams in and glitches | a dark, cinematic designed boom (the probable best); the cut-to-black note (unsure which of three was best) | all 11 punches, glitch hits and braams rejected; then in the next build the boom was called a last resort, not a good one. It is also 99% sub: on a phone it measured 14-21 dB under the mix. Open: round 3 |
| phone_ring: a desk phone rings | a cordless-handset ring (the best and least annoying), two digital rings | a soft modern ring, not a loud bell |
| money | none (all 8: bells, a register, coins, counters, slots) | the reviewer pointed to their own pack instead |
| stamp: an "APPROVED" stamp lands | a low-end punch (the best), a low deep punch | a stamp sounds like a low punch, never paper or a rubber stamp |

## Round 3 (the reviewer's own editing effects pack, 286 sounds)
The reviewer pointed to an editing effects pack already on the PC that held very good sounds. All 198 files were sorted into 19 jobs by file name, the four compilations split into 92 single sounds, and rated Keep
or Delete with the file names shown.
- **93 Keeps, 193 Deletes.** The Deletes left the pack (the compilations after their kept parts were cut out as files of their own). A
  sound marked Delete with a note that it was good got one question: the note was the mistake, it was bad. A verdict that contradicts
  its own note is asked about once, never guessed.
- **Every Keep went into `palette.json` under `pack_jobs`, with its note:** a reveal (a big boom), a question drop, the statement drop,
  a plot twist (an evolving brass boom, an incoming crash), a dramatic change, a crash, punch and slap, a glitch (the pack's best), the
  classic whoosh, a dramatic stamp, "caught", the meme drops (a Vine boom: jokes only, never in a serious moment), risers, money (a cash
  register: the best money sound), digits counting up, data, desktop-OS sounds, error (all on par with a no-internet beep), correct,
  phone notifications, calls, a file received, the subscribe click, typing (a mechanical keyboard: the best of its kind), writing (very
  good), camera, pops (the best pop), clocks, tape (rewind and fast forward: used quietly), paper, heartbeats, and the
  memes (one only fit for a serious video).
- **Used at once:** in a Short, the pack's best glitch on both glitching slams and its pop on each of five days in a list; in a long
  video, a quiet rewind under a rewind montage, the big boom on a forty-million figure, and no sound on a billion.

## What the next review added
- **No sound can be right:** on a one-billion figure, no effect at all was right; even the good money sound would have been out of
  place.
- **The sound matches the action:** a riser under a rewind montage didn't match what happened on screen; the forty-million figure had a
  hit rejected in round 1, and it was bad again there.
- **A mark you hear must be seen:** a line under a year sat low on the frame; the whole card got crossed out instead, the sound on each
  stroke.

## Where the picks went: the house set
The rounds' fits and Keeps became the house set (`assets/house_sfx.zip`; the setup unpacks it and `palette_from_manifest.py` makes one
`pal('<job>')` per sound). `manifest.json` gives each sound's job, its level against the voice, where on the picture it goes, and how
many finished long videos and Shorts placed it. Two house sounds (`click`, `phone_ring`) were made in code, which is a third source of
candidates beside the creator's own effects and licence-clear libraries. What the rounds teach, by house sound:

| House sound | What the rounds taught for its job |
|---|---|
| `glitch`, `glitch_slam` | a short, dirty burst, like a signal breaking up; a word slamming in is its own job, never two sounds layered |
| `error`, `fail` | a real device's error, never a quiz buzzer; mostly-sub errors vanish on a phone |
| `notification`, `join` | a phone's own mid-range tone; many messages get one tone, never a burst |
| `cinematic_hit`, `bass_drop`, `reveal_boom`, `black_cut` | deep and clean; thin, whooshy or glitchy hits out; a sub-only boom is big on a TV and faint on a phone |
| `pop` | soft, rounded, low-mid |
| `whoosh_fast`, `chapter_card` | soft and airy; a whoosh only on a real flight across the screen |
| `click`, `key_press` | a real mouse click; one key |
| `stamp` | a low punch, never paper or a rubber stamp |
| `typing_keyboard`, `writing` | one take per device; under a date that types itself; cut to the action's length |
| `phone_ring` | soft and modern, never a shrill bell |
| `money` | only on money shown (a price, cash, a sale), never on a big number that isn't money |
| `fast_forward` | time skipping; used quietly |
| `marker` | a highlight's mark, from the light's first frame |

## How to use this
1. **A recurring action:** `pal(name)` in the cue sheet (`tools/sound/score.py` reads `palette.json`). Never a different sound for the
   same action.
2. **A new job:** 6-12 candidates of clearly different kinds (the creator's own effects first, then licence-clear libraries or a sound
   made in code), a Sound Test round, and wait for the creator's ratings (`standard/SOUND_AND_VOICE.md`, "The Sound Test").
3. **Place it on its frame:** from the composition's timings (a highlight's sweep start, a stamp's `at`), then check it on the render
   (`EDIT tools/sound/sfx_sheet.py <cues.py> <finished.mp4> <out.jpg>`).
4. **Phones:** a fit with most of its energy under 150 Hz needs the mix report's "400Hz+ vs rest" checked; if it vanishes, use the
   creator's other fit for that job rather than distort their pick.
