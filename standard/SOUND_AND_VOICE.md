# Sound, music and voice: the standard

*Part of `STANDARD.md`. Re-read before every voicing and every mix. The creator's ears judge audio: the screens and checks below catch
what a listener would name before anyone hears it, and every verdict of the creator on a sound or a voice (`cases/SOUND.md`,
`cases/VOICE.md`) rewrites the line here it touches. Making the music: `standard/MUSIC.md`. The voice lock's stages in depth:
`standard/VOICE_LOCK.md`. The sound gate's checks and their numbers: `tools/sound/SOUND_GATE.md`.*

## The bar, in words

- **The quality, never the moves.** A passed long-form opening of 71 seconds held two music beds by one artist (one sound world); 12
  effects, each nameable in three words and each on the frame of the action it stands for; the real speaker's own line played in its
  own sound with the bed out; and one designed stop: the bed stopped dead as the picture cut to black after a line, a low note rang, a
  date typed itself, and the next bed came in on a downbeat on the date's last key. A passed Short had a track of its own, cut dead on
  its key line and slammed back in on a downbeat, 19 effects in about 37 s, the livelier Shorts voice talking constantly (gaps of
  ~0.07 s), the mix at -14 LUFS through chain D. A new video reaches that level with its own sounds and music for what it shows.
- **Everything sits under the voice.** Music ~22 dB under it in long form (~17-18 dB in Shorts), no effect louder than it, nothing
  crowding its band (1-4 kHz).
- **The voice is one person from the first word to the last:** warm from the first syllable, no word swallowed or cut, the same tone
  across every splice, American English throughout.

## Effects: the rules

- **One sound per action, on its frame.** Each effect stands for an action the picture shows at that moment; its audible start sits on
  the frame the action starts (a marker at `sync=0.0`). The time comes from the composition (a stamp's `at`, a sweep's start, the gate
  probe's frame), never by ear: placed by ear, marks landed 1-2 s early and a stamp 0.24 s before it hit. A hit lands on the contact the
  viewer sees, never on a shot that opens after it (a kick heard while the shot only shows the leg coming down) or on a near miss. A cross
  is two strokes one word apart: "*cross. cross.*", never one blurred "*crocross*".
- **One house sound per recurring action**, across every video: `pal(name)` from the palette (below), never a different sound for the
  same action. Things that appear one by one get the same sound each time.
- **Every effect names itself in three words.** Its `note` in the cue sheet says what it stands for; an effect that can't be named in
  three words is out.
- **No effect louder than the voice, and the line's mood.** score.py's "effects against the voice" measures each effect over 1.5 s
  from its impact against the voice's integrated loudness: none over -7 LU. The loudest effect of a passed long video measured -8.1 LU
  (a stamp), of a passed Short -11.7; booms at -2 and -4 LU hurt the ears. The QA gate fails a loud one. A sound the creator calls
  memey is for jokes only (its note says "joke"; score.py flags one outside a joke): a meme-like punch under a serious narration breaks
  the film.
- **Every effect is heard on every speaker.** score.py's "400Hz+ vs rest" (the effect above 400 Hz against the rest of the mix, 200 ms
  from its impact): passed effects sit between -12 and -3 dB; a count-up at +3.4 was too loud and came down; an effect that is 93-99%
  sub-bass measured -14 to -21 and vanished on a phone. score.py adds harmonics (150 Hz-2 kHz) to sub-heavy files; if one still
  vanishes, use another rated sound for that job, never alter the rated one (no bright layer laid on top). `pal('reveal')` is pure sub:
  big on a TV, faint on a phone.
- **A sound under the voice for seconds sits low.** An effect that runs under the narration (typing under a message on screen) sits
  about 10 dB under a one-shot of its kind: subtle in the background, still heard. 10 dB louder, it shadowed the voice (the level was
  picked from three samples).
- **Every highlight gets the marker, and only the marker.** `pal('mark')` starts on the light's first frame (the file is loud from its
  own first frame), one per lit phrase; highlights lighting together share one. No other sound lands on lit words: a page swoosh there
  read as a strange marking sound.
- **A number is heard.** A number that rolls gets `pal('count_up')` from its first frame, cut to the count's length (only under digits
  that visibly roll), and `pal('number_land')` where it lands; a number or a date that appears whole gets `number_land`.
- **Restraint where nothing fits.** A moment no sound fits stays clean: a huge number said with weight landed harder with no sound at
  all (even the money sound would have been out of place there), and a plain span of time said aloud gets none. The effect matches the
  action: a riser under a montage it didn't match, TV static on a cut, a cash register on a big number that wasn't money on screen, a
  deep boom on a date popping up were each wrong. A date that types itself gets the keyboard; money shown (a price, cash, a sale) gets
  `pal('money')`.
- **No quota.** Effects follow the picture, never a number per minute (12 in the passed 71-s opening, 19 in the passed ~37-s Short);
  autocues.py never places 4 inside any 5 s, so they never turn into a patter.
- **Every Short opens on `pal('flash_open')` alone at frame 0.**
- **An arrow gets `pal('ping')`** on its landing; a callout gets no pop of its own.
- **One house bass drop.** `pal('bass_drop')`, the heavy impact hit at -7, is the house sound for every statement drop (a bed stopping dead on a
  line, a reveal that lands), on the statement's key word. No other boom does that job. `pal('black_cut')`, the low
  stinger, stays for cuts to black.
- **Real voices play in their own sound,** music and all: the narration stops, the bed drops (about 32 dB under the speaker), the line
  is subtitled "Name: line" from its own captions, only while the mouth moves. A clip under the narration is muted. A clip's own sound
  is not an effect (its note says "own sound" or "own voice") and is not judged as one.
- **A moved or removed visual takes its sound with it.**
- **A risky word in the creator's own voice gets a bass-boost hit, never a beep:** `PIPE tools/sound/censor.py <video dir> <beat>
  <heard word>` mutes the word from its measured onset and lays the hit there (the house bass drop by default), 6 dB under the voice,
  so the line keeps its rhythm. The speech in a clip's own sound is never censored. Before `dj captions` runs again,
  `narration_uncensored.wav` goes back over `narration.wav` (Whisper can't hear a muted word).

## The house effects and the palette

The house set is `assets/house_sfx.zip`: 29 effects, each named by its job. Its `manifest.json` gives each one its job, its level
against the voice and where it goes, with how often finished videos placed it (a guide to what gets used, never a quota). The setup
unpacks it into `SFX/house/` (`sfx/<job>.wav|mp3`, `manifest.json`, `README.txt`) and writes `tools/sound/palette.json` with
`PIPE tools/sound/palette_from_manifest.py` (`--check`: every palette file exists and decodes). A cue sheet takes a house sound by its
name: `pal('mark')`, `pal('reveal')`, `pal('<job>')`. `db` is the effect's peak against the voice's peak as the cue sheet places it:
where a sheet starts, which score.py's measures above then confirm or move.

| `pal(...)` | Stands for | db | Placement |
|---|---|---|---|
| `pop` | an item appears (a picture, a word, a list item) | -9 | on the frame it appears |
| `mark` | a highlight lights (a phrase or a thing marked) | -14 | on the light's first frame, `sync=0.0`; one per lit phrase |
| `count_up` | a number counting up | -10 | only under digits that visibly roll, cut to the count's length |
| `number_land` | a number or date landing on screen | -10 | on the landing frame |
| `flash_open` | a Short's frame 0, the white flash open | 0 | alone at frame 0 |
| `reveal` | a big reveal (pure sub) | -13 | on the reveal |
| `bass_drop` | a statement drop, a heavy percussive hit (the same one for every drop) | -7 | on the statement's key word |
| `black_cut` | a low suspense stinger on a cut to black | -8 | on the cut to black |
| `cinematic_hit` | a dramatic beat | -10 | on the beat |
| `stamp` | a stamp landing (a passage's headline claim) | -2 | on the landing frame |
| `chapter_card` | a chapter card cutting in (a soft airy whoosh) | -10 | on the card's cut-in |
| `whoosh_fast` | a real fast flight across the screen | -12 | only on a real flight, never on a plain cut |
| `glitch` | a screen or logo glitching | -13 | on the glitch |
| `glitch_slam` | a word or logo slamming in with a glitch | -4 | its impact is 0.44 s into the file: `sync=0.44`, `t` on the slam |
| `paper` | a document or page sliding onto the screen | -10 | on the slide |
| `money` | money: a price, a sum, a sale | -8 | on the number or the cash |
| `error` | a system says no (denied, failed to load) | -10 | on the error showing |
| `fail` | a verdict that something failed | -10 | on the verdict |
| `ping` | an arrow or callout pointing | -10 | on the arrow landing |
| `click` | a real mouse click (a button, a cursor) | -10 | on the press frame |
| `key_press` | one key pressed | -12 | on the press |
| `typing_keyboard` | typing on a keyboard | +5 | under the typing, cut to its length |
| `writing` | handwriting or a pen stroke | -12 | under the stroke, cut to it |
| `notification` | a phone notification: a message lands | -10.5 | on the message landing |
| `phone_ring` | a phone ringing (soft, never shrill) | -12 | under the ringing phone, cut to it |
| `join` | someone joining a call or a chat | -12 | on the join |
| `camera` | a camera taking a picture | -10 | on the shutter |
| `glass_shatter` | something shattering | -10 | on the break |
| `fast_forward` | time skipping forward | -16 | under the skip, cut to it |

**Sounds with a length are cut to it.** `count_up`, `typing_keyboard`, `writing` and `fast_forward` are refused whole: they need
`Sfx(..., dur=<seconds from the impact to the action's end>)`, so a sound never plays on past the action it stands for.

**The rest of the palette is the creator's ratings** (palette_from_manifest.py keeps them when it rebuilds the palette):
- `pack_jobs`: the creator's own effects pack (its files in `SFX/pack/`), the sounds they kept, by job, with their note:
  `{"<job>": [["<file name>", "<their note>"], ...]}`; a job or note with "meme" in it means jokes only.
- `_sound_test_fits`: a Sound Test fit, by its file name, with the creator's note.
- `_creator_picks`: a sound the creator said yes to (`sfx_verdict.py yes`).
- `_banned`: a sound the creator said no to (`sfx_verdict.py no`), refused by its file name whatever path or name brings it.
- `pending`: the jobs in a Sound Test now.

**The rating lock.** score.py refuses every effect the creator never rated, when the cue sheet builds it and again at the mix. Rated
means a house sound (`pal(name)`), a pack Keep, a Sound Test fit, a creator's pick, or a clip's own sound. A cut of a rated file names
it: `Sfx(<the cut>, ..., of=<the rated file>)`. A sound that slipped into a finished video is not rated by that: a library sound that
went through unnoticed twice was still the one the creator called horrible the third time. `EDIT tools/sound/sfx_rated.py <cues.py>`
lists a sheet's sounds and where each one's rating comes from (exit 1 on an unrated one).

## The creator's taste: new and replaced sounds

- **The house set is the starting taste; the creator's verdicts replace its picks.** The creator's ear picks the effects, each rated
  for what it is trying to represent; their own effects come first among the candidates.
- **A replaced house sound:** the creator's pick goes into palette.json under the same name (file, db, job, use, and their words), and
  the old file is banned (`sfx_verdict.py no`). A house sound the creator rejects in one place may only be wrong there (context
  counts); at the second no it leaves the palette and is banned.
- **New sounds are welcome, never forced:** only where a moment needs a sound the rated set lacks, never to fill. A new sound reaches
  the creator first, one of two ways:
  - in the real cut: a sample, `Sfx(..., test=True)` mixed with `score.py --test-sounds` (never delivered: the pipeline's score step
    refuses a test sound), or `EDIT tools/sound/sfx_demo.py <cue module> <jobs.json> <out dir>`: the same few seconds of the real cut
    once per candidate, labelled A, B, C, with the real narration and music;
  - for a job the palette lacks: a Sound Test round (below).

  The creator's yes: `PIPE tools/sound/sfx_verdict.py yes <file> --words "<their words>" --for "<the job>"` (a recurring action also
  gets its palette entry); their no: `PIPE tools/sound/sfx_verdict.py no <file> --words "<their words>"`. Each verdict also goes into
  `cases/SOUND.md` the same turn.
- **The Sound Test** (a job no rated sound covers):
  1. 6-12 candidates of clearly different kinds for one job: the creator's own effects first, then sounds whose licence allows use in
     videos (the licence kept beside the file), or a sound the chat makes in code (two of the house sounds were made that way).
  2. The previews levelled alike (95th-percentile 50-ms RMS at -18 dBFS, peaks under -1 dBFS), numbered, no names: the creator rates
     blind, each for what it is trying to represent.
  3. One job at a time, sent as numbered files (`SendUserFile`); their answer per number (fit or no, a word on why) is recorded at once:
     a fit into `_sound_test_fits` (a recurring action: its palette entry), a no into `_banned`.
  4. The creator's own pack, when they bring one: copied into `SFX/pack/` and rated in one round, sorted into jobs by file name,
     compilations split into single sounds, Keep or Delete per sound with the file names shown; the Keeps go into `pack_jobs` with their
     notes, the Deletes leave `SFX/pack/`.
  5. A fit in the test is not a fit everywhere (a deep boom rated a fit was wrong on a date popping up), and the sound that actually
     plays is the one judged (a cut can play only a file's quiet build-up): a new sound's first placement is checked on the render and
     gets the creator's verdict like any other.
- **What the house picks teach** (the starting taste for choosing candidates; the creator's verdicts replace it):
  - a glitch is a short, dirty burst, like a signal breaking up; never a designed whoosh transition, a data or sci-fi computing sound;
  - an error is a real device's error sound, never a quiz-show buzzer;
  - a notification is a phone's own tone, mid-range (centroid 750-1,300 Hz), never a bright, tinny interface blip; many messages at
    once get one good tone, never a spammed burst;
  - an impact is deep and clean; thin, whooshy or glitchy hits are out;
  - a pop is soft, rounded and low-mid (centroid ~500-2,100 Hz); bright digital or squeaky pops are out;
  - a whoosh is soft and airy, never a bright flyby or harsh noise;
  - a click is a real mouse click;
  - a stamp lands like a low punch, never paper or a rubber stamp;
  - a phone ring is a soft modern ring, never a loud bell (a shrill ring hurt the ears);
  - typing has one take per device (phone texting, a mechanical keyboard);
  - a slam (a word slamming in) is its own job: two good sounds layered on it don't make one.

## Music: the mixing rules

- **Music is ambience.** One sound world for the film; one bed per chapter, a second only where the story really turns; mood changes
  between chapters are welcome inside that world. No drops, risers, swells, euphoric, comic or newsroom-ident tracks, no hype intro
  followed by a sad piano, no lyrics ever, never two beds at once, a steady level. Too much is the failure: a long video with 29 beds
  was overcooked and lost its viewer. Keep it simple; less is better than too much. The one bed with a shape is the opening's (its
  arc: `standard/BAR_LONG_FORM.md` 1.9, and for music made in code `standard/MUSIC.md` section 2), at a steady level under the voice.
- **Changes are gentle.** A change happens at a chapter card or a real turn, never mid-thought (score.py `HANDOFF_STYLE = "smooth"`):
  the old bed fades out (1.2 s) to its own beat inside the narration's pause, the new one fades in (1.5 s), and they touch for 0.3 s at
  low level at most. A new bed never arrives more than 2 dB louder than the one before (it settles over 8 s); a chapter card's music
  never jumps more than 6 dB over the bed before it (`CARD_JUMP`); each bed's own builds and drops are evened out (`LEVEL_BEDS = 0.6`;
  a bed made in code is written steady and keeps its designed moves: `code_beds` gives it level 0).
- **The voice over the music, measured.** score.py's "voice-music" per cue during speech is the bar (the measurement, not the
  setting): **long form ~22 dB, Shorts ~17-18 dB.** Where a sheet starts, long form: `UNDER = 13` (each cue's `under`), `GAP_MIN = 22`
  (under speech the music is held at least that far under the voice, in 250-ms windows), `DUCK_DB = 5`, `CARVE_DB = 8` (the voice's
  band, about 0.9-4.5 kHz, carved out of the music), `SIDE_DUCK_DB = 2.5`. A bed that still measures short of 22 gets more (one
  measured 17.6-18.7 dB at 13 and needed 17). Shorts: `UNDER = 10`, `DUCK_DB = 6`, `CARVE_DB = 5`, `SIDE_DUCK_DB = 2`, `GAP_MIN`
  17-19.5, and the effects lower than a long video's (of four levels tried as samples, the right one put every effect 7 dB under the
  first build's); at ~13 dB the music and effects drowned the voice. The Shorts level stays where it is until the creator changes it.
- **A bed stays out of the voice's way.** Judged with analyze_tracks.py before it is used: most of its energy under 1 kHz and under 3%
  of it at 1-4 kHz. The beds rejected by ear were the brightest (centroid 2.7 kHz) and the most crowded in the voice's band (13% at
  1-4 kHz). Steady energy (a flat 8-s energy line), no big drop in the stretch used. Tags and measures pick candidates and the ear
  decides (two picks that passed every measure, a news ident and a big electronic drop, failed by ear): stay inside the sound world the
  creator approved.
- **Stops land on words and on the track's own beats.** A bed can stop dead on a line and come back on a downbeat (grid.py's downbeats;
  `Cue(..., align=(track time, film time))`). Every stop goes in `SILENCES`, and the mix never drops to digital silence outside them: a
  silence meant as the effect means no effect, never dead air.
- **A joke gets the room to land:** the bed stops on the joke's first word (a 60-ms fade that ends on the voice's own onset), the
  clip's own sound plays out, and the bed picks up where it stopped.
- **Every Short gets its own music**, never one shared Shorts track.
- **The songs of a final video are kept and reusable**, never deleted.
- **Music rotates from what worked.** `KB/MUSIC_USED.md` (`EDIT tools/sound/music_library.py`, built from every final cue sheet: tempo,
  tags, which part of each song sat under the voice and how far under, the creator's yes and no from `KB/music_library.json`) is the
  first place to look; new music for a new feel; no song twice inside a video, and preferably none of the last video's; a song the
  creator said no to, never again.
- **Mono-safe:** no second of the mix with its left/right correlation under 0 (score.py narrows a bed's stereo where it would cancel).
- **Loudness:** a narrated mix at -14 LUFS integrated, at most -1 dBTP: `MIX_LUFS = -14`, `MIX_CEIL = -1.2` (a safety net over the
  voice chain's own -1.5 limiter, not a second limiter), `VOICE_COMP = None` (the voice comes in through chain D at -14 and is never
  compressed again); the upload's finish at `--lufs -14 --gain-only`.
- **Every level choice goes to the creator as samples** at each candidate level, the house setting always among them (a first round of
  samples once left out the very level the creator then picked).

## Music sources

- **Where the music comes from is the creator's choice** (asked at setup, written in `creator/PROFILE.md`, changeable any time; both
  can sit in one video): music the chat makes in code (`tools/music/`; how it is made: `standard/MUSIC.md`), or the creator's own tracks
  in `MUSIC` (only music they have the rights to, in any folders).
- **Whatever the source, a track is measured before it is used:** `EDIT tools/sound/analyze_tracks.py [<file or folder>]` (tempo,
  energy shape, brightness, the 1-4 kHz share; writes `MUSIC/analysis/`) and `EDIT tools/sound/grid.py <file>` (the `.grid.json`
  downbeats the cues align to; detection is approximate, so a downbeat is checked before a cue aligns to it). Each track's source and
  the right to use it are logged in the video's notes.

## Voice: the bar

- **Long form: the house voice.** The creator's voice (their own clone, or the stock voice chosen at setup) on `eleven_v4`, stability
  0.95, similarity 0.75, the prefix `[flat, calm, even tone] [American accent] ` on every request, played at 1.04x (`[tts]` and
  `[tts.elevenlabs]` in `config/tts.toml`). No fallback model: the older multilingual one sounds like computer speech. A different
  voice or setting only when the creator picks it, as `CONFIG:` lines in the script.
- **The accent tag is on every request:** without it the model picks the accent from the words and slips into British.
- **Shorts: the Shorts voice** (`[tts.short]`): faster, louder and more excited than the long-form read: stability 0.5, no flat tag,
  `[American accent]` only, the hook sped to 5.65 syllables a second; constant talking, every gap cut to ~0.07 s.
- **No other tag, ever.** A stronger accent tag (`[strong American accent]`) made the voice shout with unnatural pronunciation;
  American is no reason for it, and the delivery stays the voice's own. An accent is fixed by how the text is sent (the method, step 4).
- **Warm from the first word, nothing swallowed.** A request with nothing spoken before it starts cold: low, flat, breathy, a tired
  half-whisper. So any request with no context gets the unspoken `lead_in`; the video's first section is voiced after the house warm-up
  (`[tts.elevenlabs] warmup`, spoken and cut away, as every other section gets its 2 lines before); autopick rejects a take whose
  opening never reaches its own pitch peaks (`tools/voice/opening.py`), and the gate's A12 fails a tired opening in the final narration
  (never allowed). voice_check.py ends with no OPENING or WHISPERED flag.
- **No word cut off.** The chain starts from the layout, never from a cut by hand, and the gate's A13 (`tools/sound/hisstails.py`)
  fails a word's hiss lost at a cut (`standard/VOICE_LOCK.md`, "The opening and the tails").
- **American from start to end.** A British spot means the whole request is re-voiced: an accent lives in a whole request, not in one
  line. It can hide in lines with no r's (accent_id.py and the guard hear it; rhotic.py can't), and a story set in Britain pulls the
  accent British.
- **Foreign names said the American way.** Respelled in what ElevenLabs reads (`span_takes.py --say Saoirse=Sersha`, any length; the
  stored take spells the script, the captions keep the real spelling), never a tag. **Measured, never trusted to the spelling:** a
  respelled name can still come out in its native language in some takes, so every take that says one is measured by
  `tools/voice/saycheck.py` (a phoneme recogniser weighs the American pronunciation against the native one, from names.json's `"ipa"`
  pairs; on a name with an r it agrees with the formant measure, an r-coloured F3 under 1750 Hz), and only an AMERICAN take is used
  (autopick.py and voice_ready.py hold it). Forcing `language_code="en"` or an ElevenLabs alias dictionary made it worse, not reliable
  (`standard/VOICE_LOCK.md`, "Research"): the measure and enough takes are the fix. The lines before in the request get the same
  respellings (a context line voiced with the name unspelled pulled 15 takes into the native pronunciation).
- **A fix after the voice is locked keeps the time:** `EDIT tools/voice/voice_layin.py <video> <beat> <k...> --apply` lays the new
  piece into the old slot from its first sound, every anchor the picture or the cues hang on within 2 frames (`standard/VOICE_LOCK.md`).
- **A sign-off is never sent alone or last.** Inside a long ending it came out overexcited; sent alone it came out whispery and
  exhausted. `span_takes.py --tail "<text>"` voices a line after the sign-off (cut away) so it isn't the request's last word;
  `--prev-text` sets the context.
- **No sound lost at a cut** (a cut on the model's times once left a line saying only the end of its first word): cut in measured
  silence, never on ElevenLabs' character times (30-60 ms late, at worst up to 0.5 s).
- **The creator's ear judges the finished video; the machine picks the takes.** Takes are never sent to the creator to rate: the
  measures pick them (autopick, the guard), and a spot the creator names is voiced again.
- **Dry, as it is.** No de-esser (`[tts] deess = 0`: it audibly lowers the voice's quality), no EQ chain. Beats are levelled to each
  other at generation (`dj tts`' level_beats, at most 6 dB: the generation's own step, not a repair). A fault heard in a take gets a
  regeneration, never a gain change or a repair tool.
- **To loudness through chain D, from the untouched takes, nothing limited twice.** An ElevenLabs voice peaks 21-22 dB over its
  loudness; one gain to -14 LUFS and a fast limiter squashed every line (artificially gained up, it hurt the ears against the raw take
  at the same loudness). Long form: `CONFIG: audio.voice_chain="multiband"` and `audio.loudness=-14` (dj tts hands its last step to
  `tools/sound/voice_level.py --chain mb`: only the vowel band, 400-2500 Hz, held back on its loud moments, the lows and consonants
  untouched, a light limiter at -1.5). The narration reaches it unlimited (`tools/sound/raw_rebuild.py` after splices, at a -28 LUFS
  working level; every line it rebuilds from a shortened take is checked by transcript before the render). The mix: `MIX_LUFS = -14`,
  `MIX_CEIL = -1.2`, `VOICE_COMP = None`. A Short goes the same way: -14 through D.

## The method

**The voice lock runs this method (`standard/VOICE_LOCK.md`): the voice is made once, by machines that refuse.** In order:
(0) `EDIT tools/voice/voice_ready.py <video> status`: the first take is refused until script, facts, cold read, bites and names are
stamped on the current script.md (`tools/workflow/stages.py`; names by `voice_ready.py <video> names --measure --stamp`); (1) the voice
(step 1 below), every take and re-take through `EDIT tools/voice/autopick.py <video> <first> <last>` (K takes the lines-before way, the
machine picks; no clean take = reword, never kept); (2) the chain and the gate (step 2: A1-A13 and LOCK; A11's hard accent, A12's tired
opening and a broken lock can't be allowed); (3) `EDIT tools/voice/voice_lock.py <video> lock` before the picture anchors on the
words; after that every narration writer refuses and a fix is `voice_layin.py`. The line runs 0-3 as one step:
`PIPE tools/pipeline/pipe.py <video> voice`. Credits: `standard/VOICE_LOCK.md`, "Credits" (the chat's to spend, never asked for, never a
blocker); a take costs about 0.45-0.5 credits a character with the prefix, and `PIPE tools/voice/voice_credits.py` tells the balance.

**The lines-before way** (the "J way" in some docstrings): a span is voiced as one request with the two script lines before it spoken
first inside the same request and cut away (`span_takes.py --before 2`, the default), and the head of the line after voiced and cut
away too, so the span starts warm and its last word is not the request's last.

1. **Voice.** `cd tools && PIPE -m dj tts ../videos/<video>`, then `PIPE -m dj captions ../videos/<video>`. Long form reads `[tts]`
   and `[tts.elevenlabs]`, a Short `[tts.short]`; per-video settings are `CONFIG:` lines in script.md (e.g. `CONFIG:
   tts.fresh_at=["S05", "S06", "S07"]`: a fresh request at those beats, free of the context before them). The API key only through
   `dj.tts.elevenlabs_key()`: never opened or printed.
2. **The chain.** Long form: `bash tools/sound/voice_chain.sh <video>`: from the layout (`narration_laid.wav`), captions, the early
   word check (A5), the safe breath pass, the raw takes kept as `narration_prechain.wav`, the 0.25-s cap, the hiccup pass, the pause
   fix, every pause inside a sentence to 0.12 s, close_gaps, captions again, the word times (`PIPE tools/motion/sync_words.py <video>
   <src folder>`: words.json and beats.json in `tools/motion/src/<video>/`), the clean-up (fixmutes, `tails.py --fix`, `hisstails.py
   --fix`, the A3 fix), then the sound gate (`EDIT tools/sound/gate_sound.py <video>`, A1-A13, `tools/sound/SOUND_GATE.md`). A Short:
   `bash tools/sound/short_chain.sh <video> <src folder>` (captions, the guard and its retake, the pause fix, every gap to ~0.07 s,
   captions, the word times, the gate).
3. **Screens, every narration.** Copy `narration.wav` to `narration_unlifted.wav`; `EDIT tools/voice/voice_check.py
   narration_unlifted.wav <words.json> --starts <beats where a request starts cold> --fix narration.wav`; `cd tools && PIPE
   voice/rhotic.py --sections ../videos/<video>` (the median dip of F3 at every written r after a vowel: American takes measured
   685-1100 Hz, approved Shorts 735-822, British ones 70-450; under ~400 Hz is British for sure, and a take over it can still sound
   British); `ACCENT tools/voice/accent_id.py <wav>` (CommonAccent, window by window); the voice guard (below). The numbers flag a take
   for a re-take; the chat picks the take by the measures, never by sending versions to the creator.
4. **Fix the cause** (new seeds don't help: three seeds of a tired opening measured within 0.3 dB of each other):
   - an accent: re-voice the whole section the lines-before way (`autopick.py`, or `cd tools && PIPE voice/span_takes.py
     ../videos/<video> <first beat> <last beat> 1 4`), plus casual wording, contractions or a respelling (`--say`) where the text pulls
     it. `section_takes.py` voices a whole section the same way, its lines before inside the request; its `--cold` (the section alone)
     is a test only: cold takes came out exhausted and breathy every time;
   - a tired or whispered beat: its section voiced again the lines-before way, or the line rephrased;
   - a line the creator names: versions that differ (`cd tools && PIPE voice/voice_versions.py ../videos/<video> <spec.json>`: about 5
     versions of wording, punctuation or context, one line per round; never the same request five times, which repeats the same
     mistake five times), picked by the measures.

   **A word that pulls the whole request British:** take the cue out of what ElevenLabs reads. "studio" (said the British way,
   "styoodio") was reworded; "pound" was sent as "pownd" (`--say pound=pownd`: the stored take spells the script, the
   captions keep "pound"; Whisper had heard "one pound" as "£1"). With the cue in, 28 takes over three rounds came out British; with it
   out, 19 of 20 came out rhotic (an r-dip of 730-1400 Hz where the takes before sat at 70-450). Rewording the rest of the span made it
   worse, moving the word to the end of its sentence didn't help, and a stronger accent tag made the voice shout.
   **A British phrase is the same cue:** a span with "straight away" came out British 3 of 3 times (r-dip 75-141 Hz); with the phrase
   reworded to "right away", 3 of 3 American (821-855). Before any accent re-take, read the span and its two lines before for British
   phrasing (straight away, whilst, rubbish, brilliant, proper, reckon, mate, cheers, fancy, queue) and reword it to the plain American
   word first.
   **A context line can pull it too:** a word came out British right after a British place name in the line before; the beat was
   split after the name and the rest voiced with no context (`span_takes.py --no-prev`).
   **After the creator watches:** every spot they name is voiced again as its natural chunk (3 takes, never repaired), and the machine
   picks. Before the lock: `span_takes.py ../videos/<video> <first beat> <last beat> <k0> <k1>` (one request in its place, the lines
   before as context); move `narration_final.wav` aside, splice with `cd tools && PIPE voice/voice_patch.py ../videos/<video> <beats>
   --keep-old --use <beat>=<k> ...`, rebuild every line from its untouched take (`raw_rebuild.py`), then `dj tts` (through D) and the
   word times again; a line `voice_cut.py` shortened gets a transcript check before the render. After the lock: `voice_layin.py`.
5. **Music** (the sources above, `standard/MUSIC.md`): every track measured (`analyze_tracks.py`), gridded (`grid.py`) and logged.
6. **Effects.** `EDIT tools/sound/autocues.py <video>` writes the effect list from what the picture really does (the gate's probe:
   marks, lit phrases, stamps, rolling numbers, landings), each line citing the probe frame that proves it and anchored on the voice's
   own words, with the density rules (one sound a beat, never 4 inside 5 s); its lines go into the sheet's `SFX`. Left to the chat (no
   rule sees them): the statement drop, whooshes on real flights, pops, impacts, fails, clicks, money, the shutter, typing, and a
   highlight a component draws without `data-gate="mark"` (such a component should mark itself; then autocues finds it). Every sound
   from `pal(name)` or the creator's ratings; a job with none gets a Sound Test round.
7. **Cue sheet** `videos/<video>/score/cues.py` (start from the newest finished video's sheet): `FILM = Film(words.json, beats.json)`;
   `CUES` of `Cue(id, path, t0, t1, src or align=(track time, film time), under, fin, exit="stop"|"fade"|"button", fout, auto=[(t,
   under)], hold_in)`; `SILENCES`; `SFX` of `Sfx(path, t, db, sync, dur, note, of, test)` with `t` from `FILM.w(beat, phrase)`
   (`FILM.we` for a phrase's end) or the composition's own times, and `db` from the palette's; the mix settings from "Music: the mixing
   rules". `Film.w(beat, phrase, nth)` has no offset argument (add it outside).
8. **Build.** `PIPE tools/pipeline/pipe.py <video> score` (`build/score/mix_v<N>.wav` with its report), or `EDIT tools/sound/score.py
   <cues.py> <out.wav> [--stems <dir>]` / `<out.mp4> --picture <render>`; a Short's finish burns the captions in first (`pipe.py
   <video> finish` runs it in order). **A sound fix after the render is a remux, never a re-render:** mux the new mix onto the render
   (`ffmpeg -i <picture.mkv> -i <mix.wav> -map 0:v -map 1:a -c copy <mux.mkv>`), then `PIPE tools/motion/finish_long.py <mux.mkv>
   <upload.mp4> --video-from <the delivered upload.mp4> --lufs -14 --gain-only` copies the finished picture and redoes only the sound
   (minutes, against hours for a render). A sample of the fix goes to the creator first.
9. **Read the report:** the handoffs and level jumps; "voice-music" per cue (the measurement, not the setting); silences "outside the
   designed ones: []"; "400Hz+ vs rest" and "effects against the voice" for every effect; mono "seconds under 0: []". With `--stems`,
   scan the music stem in 2-s steps for rises over 6 dB: only the title and the chapter cards may show one.
10. **Measure the MP4:** `EDIT tools/qa/qa_render.py <mp4> --format long|short --words <words.json> [--voice narration.wav]` (the
    pipeline's finish and `qa` steps run it).

## The voice guard: the screen before anyone hears a narration

What eats a review is finding where the voice turns British, until when, and where its tone turns into another one.
`tools/voice/voice_guard.py` finds those first, calibrated on the creator's own verdicts.

    cd tools && PIPE voice/voice_guard.py ../videos/<video> [--out report.md]
    cd tools && PIPE voice/voice_guard.py <narration.wav> --words <words.json> [--beats <beats.json>]
    cd tools && PIPE voice/voice_guard.py ../videos/<video> --retake [--cap 3000] [--max-takes 3] [--dry]

- **What it flags,** per section and beat with times: ACCENT (a stretch of 4 s or more that sounds British to a probe on the accent and
  speaker embeddings plus CommonAccent, trained on the creator's flagged spans: a re-take); ACCENT? (maybe: a re-take if the section has
  one left, else the chat's pick by the measures); CLOSE/DEEP and WHISPER (the beat's pitch, voiced share, CPP, harmonicity, low band
  and level against the narration's own and the approved voice, or a beat 6+ MADs from the narration's own voice in the embedding);
  TONE JUMP (the voice changes from the beat before; any beat voiced alone as a patch); TIRED OPENING (a request's first beat, long
  form); SWALLOWED WORD (report only: a content word 4+ dB under, or whispered, with no pitch and its energy above 2.4 kHz; never a
  sentence's last word, which falls 7-12 dB in a natural delivery).
- **Its reach and its limits,** on the voice it was first calibrated on (each video left out of training when scored): it caught every
  wholly British take, the British stretches a listener had marked (one a minute long), a chapter's cold start and a tired opening; a
  few spots reached it only as "maybe"; it missed a short phrase with a date, a few lines right after a foreign clip, four British
  seconds in a Short (the Shorts voice had too few verdicts: **for Shorts the guard is a hint, not a gate**), the breathy spans (no
  measure separates them), and most patches voiced alone (caught by structure instead: TONE JUMP and the lines-before rule). No hard
  accent false alarm on 67 minutes of approved long-form voice; about 4 of 35 sections of an approved long video still get a tone flag.
  The creator's own calibration rewrites these numbers.
- **The retake** (a flagged section is re-voiced before anyone hears it): `--retake` voices each flagged section again whole (the
  section's own text, settings and links, its lines before inside the request, a new seed; never a patch, never EQ or gain), screens
  every take the same way plus rhotic.py and the final-consonant check, keeps the first clean take, then runs `dj tts`, `dj captions`
  and `sync_words.py`, and screens the result again; in long form autopick.py on the section does the same inside the voice lock.
  Credits first (`voice_credits.py`; a long-form section take costs ~450 credits); `--cap` stops it, never more than `--max-takes` a
  section; the takes wait in `VIDEOS/<video>/review/voice_guard_takes/`. The chat picks the best by the measures, never a choice for
  the creator: the voice should be good on the first run. The creator's ear stays the judge of the finished video.
- **Its model is the creator's own,** never shipped: approved narrations (wav + words.json) in `MEDIA/voice/guard/approved/`
  (`approved/short/` for the Shorts voice), takes with faults heard in them (wav + spans.json, `[[t0, t1, "<kind>"], ...]`) in
  `flagged/`; then `ACCENT tools/voice/voice_guard_embed.py MEDIA/voice/guard`, `PIPE tools/voice/voice_guard_tone.py
  MEDIA/voice/guard`, `PIPE tools/voice/voice_guard_calib.py` (the model, with its report CALIB.md beside it). Without a model the
  guard stops and prints these commands.
- **Keep it true:** every verdict of the creator on a voice goes into `flagged/` (the take, their start and end, the kind) or
  `approved/`, then the calibration runs again and rewrites the thresholds from the data. The ears' caches sit next to each wav
  (`*.guard_embed.json`, `*.guard_tone.json`) and renew themselves when the wav changes; the embedding runs in the accent environment
  on 2 torch threads (about 0.5 s per 2-s window on a busy PC).

## Patched lines: inside their section

A line re-voiced alone came out tired and breathy. Holding everything else and changing one lever a take (the end of the paragraph,
unspoken or spoken text after it, an awake lead-in, stability, wording) made no audible difference; dropping the `[flat, calm, even
tone]` tag lifted it but changed the voice too much, so the tags stay. Voicing the line after the two lines before it in the same
request, cut out after, fixed it. `span_takes.py --before 2` is the default: every line is voiced inside its section, never alone or
unlinked.

## Splicing a take and the gaps between lines

- **A take goes in whole** (`EDIT tools/voice/voice_edit.py span <build dir> <first> <last> --pieces ...`): one piece across its lines,
  its own pauses kept, the line boundaries at its own gaps. One piece per line laid into its old slot brought back the old silence
  (0.55 s after a word where the picked take had under 0.12 s) and ended a piece on a lip smack into silence: a click.
- **Every inhale and exhale between words goes, before the pause cap:** breaths between the pauses are what a listener notices first,
  even when the voice itself is fine. The chain's safe breath pass (`tools/sound/breath.py`, on `breath_cut.py`'s regions: each word
  kept from its voiced frames with spelling-aware guards and its own decay) mutes only regions of kind sentence or comma at -24 dB or
  quieter, and only where the word before has died away (under -45 dB): the full pass silenced real word ends. Every word is diffed
  by Whisper before and after. Then the 0.25-s cap (`shorts_tighten.py --cap 0.25`), the words shifted by its cuts.
- **Then the hiccup pass** (`EDIT tools/sound/hiccup_breaths.py <in.wav> <words.json> <out.wav>`): the cap cuts through inhales the
  safe pass left and leaves their edges as blips around a cut (hiccupped breaths); in every gap, from the word's own decay to the next
  word's spelling guard, it silences the gap where a blip remains (a 20-ms frame at -50 dB or louder): mute only, the timing kept.
- **Every pause inside a sentence, commas and lists included, to 0.12 s** (`tools/sound/inner_gaps.py`, right before close_gaps): only
  the pause's digital silence is cut (a cut that chose quiet or breath frames by level took word ends with it); its `--breaths` first
  mutes an inhale left inside such a pause, which no silence cut can take. Between sentences the gap stays 0.25 s. That pacing is the
  one that sounds natural; the gate's A3 flags a pause inside a sentence over 0.20 s.
- **Then close the gaps, always the chain's last step:** a breath cut out takes its gap with it (a breath muted with its pause left
  open is still a fault). The cap trusts Whisper's word edges, which take in parts of breaths, so a breath silenced after it leaves a
  pause longer than the set gap (up to 0.47 s). `EDIT tools/sound/close_gaps.py <in> <out> --gap 0.25 --beats <build>/beats.json
  --shoulders` cuts every no-speech stretch (10-ms RMS under -42 dB) down to the set gap inside its silence and moves dj's beat slots
  (the chain runs it at `--gap 0.2`, heard as ~0.25 s); then `dj captions` and `sync_words.py`. Always with `--shoulders`: a breath
  the cap cut through leaves a quiet half on both sides of the cut, and both are muted first. **Only a real breath half:** a side whose
  level only falls from the word into the silence, or only rises from it into the next word, is that word's own fade or onset and is
  kept; a split breath dips and rises again on each side (muting a word's own fade once cut off a spoken digit, which has no letters for
  the spelling passes to guard). A chain traced file by file (each `narration_*.wav` the chain keeps) names the step that lost a sound.
- **A word end cut with its pause, no room to lay it back** (the gate's A1 "NO ROOM": a stop's released burst sat in the pause after
  the word, the pause was cut, and the next word now starts where the burst was): `EDIT tools/sound/relay.py <video> --word-end <t>
  --take <a> <b> --at <t>` inserts the take's span (lined up as `tails.py <video> --show <t>` prints it), and every later word moves by
  its length; then `dj captions`, `sync_words.py`, the gate. Insert at the word's own end, the pause after it kept, when the lost sound
  is the word's tail (laid in right before the next word, it sounded crammed). A flag `fixflags.py` can't fix is said, never skipped.
- **A take split inside a word** (A7's "a scrap before" a word: the word's first burst at the end of one beat file, the rest after the
  splice's silence): `EDIT tools/sound/cutspan.py <video> <a> <b>` cuts that silence (it refuses a span with sound) and moves the beats
  back; `EDIT tools/sound/splitcheck.py <video> --fix` mends the beat files for any later run.
- **Before a breath flag is fixed, map the word letter by letter:** an s, sh, f, th or t is a 4-8 kHz hiss inside the word, not a
  breath. A fix touches only what comes after the word's last sound, is made by a tool (never by hand), and is read back by Whisper on
  the edited window, with the word's level compared, before any sample goes out. Read breath_cut's "left alone" stretches too: real
  words Whisper timed badly, or a word the list lacks. A sample of the first minute's mix goes to the creator while the build goes on.
- **Lost words, late line starts, hidden inhales.** `voice_patch.py --keep-old` moves a patched slot's edge that sits inside a word to
  the pause next to it (a beats.json can hold most of its boundaries 25-50 ms inside words, and patches once replaced a line's short
  first word with their slots). The gate's A5 flags a word Whisper wrote with no length (it heard no sound for it). After every `dj
  captions`, `EDIT tools/sound/linestarts.py <video>` moves a line's first words that Whisper timed late and squashed to the voice's
  onset (one line ran 1.05 s late; the chain's captions step runs it). A3's breath search starts at the word's first frame under -45 dB
  (an inhale right after a word is otherwise walked over as its fade), and a stop's release (60-80 ms right after the closure) is the
  word's own. `tails.py --fix` can lay an inhale back as a word's "lost hiss" after a mute: read what it laid back.
- **Line gaps, before the voice is locked:** every gap between lines of 0.75 s or more is read by its levels every 40 ms; a real inhale
  or long dead air is cut to a 0.25-s pause (`EDIT tools/voice/voice_edit.py cut`; a breath running into the next word: `--c2` after
  it, silence put back). Each cut is proved in the original audio: both edges near silence (-47 dB or lower), the loudest thing removed
  a breath (well under the quietest speech), the next word's start after the cut. A word's own fade is never cut. `EDIT
  tools/sound/gap_scan.py <video> <motion src folder> [--dry]` is the scan and the proved cuts (it starts 0.15 s inside each line's last
  word: Whisper can run a word past the dip after it, and a scan from the word's end missed an inhale that way); locked, it runs only
  `--dry`. If the picture is already fitted to the timing, the same frames are dropped right before the next line's first shot
  (`PIPE tools/voice/captions_shift.py <build dir> <cut start s> <frames>` per cut: words, cues and chunks together, the narration
  re-signed; then `sync_words.py`), and a before/after video of each cut goes to the creator.
- **A new take gets the scan too:** a line laid in from a fresh take brings its own tail; its gap to the next line is measured before
  the version goes out.
- **The subtitles stay on the words:** `cd tools && PIPE voice/captions_regroup.py ../videos/<video>` rebuilds the subtitle lines from
  the words after cuts that moved only the words; `EDIT tools/voice/srt_check.py <srt> <words.json>` checks every cue against its words
  before an .srt goes out (subtitles once ran 0.6-0.85 s late after two cuts had moved only the words).
- **A patch after a cut:** shifted word times can round a shot boundary one frame earlier in the code than in the frame-dropped
  picture; check a patch's first and last frames against the picture before the finish.

## Before it goes to the creator

- [ ] The voice lock's stages, each a machine that refuses (`standard/VOICE_LOCK.md`): the ready stamps on the current script; every
      section's take picked by `autopick.py` (no hard or maybe accent, every respelled name AMERICAN, no word lost or added; a section
      with no clean take re-voiced with the cue reworded, never kept by measures); `gate_sound.py` PASS with A10 (fragments), A11 (a
      hard accent, never allowed), A12 (a tired opening, never allowed) and A13 (a word's hiss lost at a cut); `voice_lock.py <video>
      lock` before the picture anchors, `verify` before every render and mix.
- [ ] `voice_guard.py` run on the narration: no ACCENT, CLOSE/DEEP, WHISPER, TONE JUMP or TIRED OPENING left (a flagged section
      re-voiced whole); the "maybe" and word flags read and settled by the chat (a re-take, or its pick by the measures), never sent to
      the creator to rate.
- [ ] voice_check.py: no OPENING or WHISPERED flag; rhotic.py and accent_id.py clean on every section.
- [ ] No beat starts or ends mid-sound; Shorts: every gap ~0.07 s in narration.wav.
- [ ] Every effect's `note` says in three words what it stands for, and the picture shows that action; every recurring action uses
      `pal(name)`; no new kind of sound skipped the creator's ear (score.py refuses an unrated sound on import and at the mix; a
      `test=True` sample is mixed only with `--test-sounds` and never delivered).
- [ ] Each effect's audible start on its action's first frame, checked on the render; cross strokes one word apart.
- [ ] Every highlight has the marker from its light's first frame; things appearing one by one share one sound; a moment no sound fits
      stays clean.
- [ ] `EDIT tools/sound/sfx_sheet.py <cues.py> <finished.mp4> <out.jpg>` read row by row (the frames 0.12 s before, at and 0.2 s after
      each impact): each effect's action is on screen at its impact; a hit on the contact the viewer sees, never on a shot that opens
      after it or on a near miss; on lit words only the marker.
- [ ] score.py: voice-music ~22 dB in long form, ~17-18 dB in Shorts; no silence outside `SILENCES`; every effect -12 to -3 on
      "400Hz+ vs rest"; none over -7 LU on "effects against the voice" and no memey effect outside a joke (the QA gate fails a loud
      one); no mono second under 0.
- [ ] One sound world; beds overlap 0.3 s at most; no switch more than 2 dB louder; a Short has its own track.
- [ ] A moved or removed visual took its sound with it.
- [ ] A speaking clip plays its own sound with the bed out, subtitled "Name: line" from its own captions, only while the mouth moves.
- [ ] Loudness: on a finished render finish_long checks it itself; qa_render.py: no FAIL (long form -15 to -13 LUFS, Shorts -16 to
      -12, at most -1 dBTP). Every level choice went to the creator as samples at each candidate level, the house setting among them.
- [ ] Shorts: `flash_open` alone on frame 0. Long form ends on the sign-off, picture and sound fading out together.
- [ ] Each track's source and rights logged; each re-voiced take is the machine's pick, at the narration's level.

## Read before doing sound or voice

1. `cases/SOUND.md` and `cases/VOICE.md`: the creator's lines, flagged and passed.
2. The newest finished video's cue sheet (`videos/<video>/score/cues.py`) next to its render, once one exists: how a sheet is built
   here.
3. `tools/sound/palette.json` and `SFX/house/manifest.json`.
4. `tools/sound/score.py`: the docstring, `Film`, `Cue`, `Sfx`, `rating`, `pal`, `checks()`; `tools/sound/SOUND_GATE.md`.
5. `standard/VOICE_LOCK.md`; the comments in `config/tts.toml`; the docstrings of `tools/voice/voice_check.py`,
   `tools/voice/voice_guard.py` and `tools/dj/tts.py`.
6. `standard/MUSIC.md`.
7. The sound and voice files in `standard/research/` (its README lists them): the craft, sourced; the creator's ear overrides it.
8. `standard/CHECKLIST.md`.
