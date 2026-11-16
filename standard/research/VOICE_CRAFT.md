# Voice craft: natural, consistent YouTuber narration from a voice clone

*The question: how to get natural, consistent, YouTuber-sounding narration out of a cloned voice on ElevenLabs, what causes the faults
a clone shows (a British accent drift, whispery takes, clipped consonants, tone changes between sections, lines that sound AI), and
whether another provider is better. It builds on an earlier pass of our ElevenLabs notes, our voice QA records and the voice code in
`tools/dj/tts.py`.*

*Read with: `standard/SOUND_AND_VOICE.md` ("Voice: the bar" and the voice guard: the house rules; where this file and the standard
differ, the standard wins), `standard/VOICE_LOCK.md`, `standard/research/VOICE_OPENINGS.md`, `standard/research/SOUND_CRAFT.md`,
`config/tts.example.toml` (the house voice settings) and `cases/VOICE.md`.*

*Grades: **A** = the vendor's own docs or page (or YouTube's), **B** = independent benchmark, paper or established outlet,
**C** = blog, forum or aggregator, **M** = our own measurement. Sources are [V#] at the end. No TTS credits were spent on this study:
two free read-only API reads (`/v1/models`, `/v1/user/subscription`), no key printed or copied. Web search hit its cap near the end,
so a few post-production numbers rest on fewer sources than wanted (marked).*

**Who decides:** audio judgement is the creator's. Everything measured here *screens* takes and *proposes* tests; tone, accent and
"does it sound AI" are decided by the creator's ear on the finished video.

**Where the house standard decided differently** (the evidence below stays as found; the rule lives in the standard):
- **Tags:** the house prefix is `[flat, calm, even tone] [American accent]` on every long-form request and `[American accent]` alone on
  Shorts; no other tag, ever. A stronger accent tag (`[strong American accent]`) made the voice shout with unnatural pronunciation; a
  patched line voiced without the flat tag woke up but no longer sounded like the same voice, so the tags stay. The tag tests and the
  `[normal speaking volume]` line tags proposed in §1.1 and §2.1 are not in the house method.
- **Openings:** a request with no context gets the unspoken `lead_in`, and the video's first section is voiced after a spoken,
  cut-away `warmup` (`standard/research/VOICE_OPENINGS.md`, `standard/VOICE_LOCK.md`).
- **Patches:** every re-voiced line is voiced inside its section after the two lines before it (`tools/voice/span_takes.py --before
  2`), never alone or unlinked.
- **Sections:** the house voices ~220-word sections linked by request id (`[tts] section_words`), above the vendor's 800-900-character
  advice (§2.2); the accent tag on every request and the screens (`tools/voice/rhotic.py`, `tools/voice/accent_id.py`, the voice
  guard) hold the accent, and a British spot re-voices its whole request.
- **Takes:** the machine picks them (autopick, the voice guard); takes are never sent to the creator to rate.
- **Post:** dry, as it is: no de-esser, no EQ chain, no high-pass of the research's §1.4; beats levelled at generation (at most 6 dB);
  a fault heard gets a regeneration, never a repair tool; to loudness through chain D. Gaps are cut to 0.12 s between sentences and
  0.07 s at commas (`[tts] gaps`); the breath and room-tone tests of §1.4 are not in the house chain.

---

## 0. Headline

1. **Stay on ElevenLabs `eleven_v4`.** It is #1-2 of all models with each provider's own voices (Elo 1329) and #4 with cloned
   voices (1159), one point behind its own Turbo variant [V20][V21] (B). Nobody is *clearly* better for a cloned YouTuber voice: the two
   models above it on the cloned board (HeyGen Voice 1198, Qwen-Audio-3.1-TTS-Plus 1186) would win only about **56% and 54%** of blind
   pairs on that Elo gap, on short clips, and both lack features this pipeline leans on (audio tags, request stitching) (§6).
2. **Most of a clone's faults are content- and process-driven, not random.** v4 reads emotion from the text and *carries a tone
   forward* [V3][V5] (A). Measured on our own files: the British drift follows UK/Australia content (6 of 6 and 5 of 5 takes British; 16
   re-draws stayed British) and the whispery takes follow hushed scene descriptions (fog drifting over a lake, a candle guttering out,
   an empty hallway at night). **Re-rolling does not fix a content-driven fault; changing the text, the tag or the context does** (§2).
3. **The house direction tag is low-arousal.** `[flat, calm, even tone]` sits in the vocabulary ElevenLabs files under "Calm and
   reflective" and next to its own example of a hushed narrator, `[hushed and reverent, like a nature documentary narrator]` [V5] (A). On
   a quiet, intimate or suspenseful line the model has every cue to go soft. The research proposed a tag that keeps "even" but asks for
   normal projection (§1.1); the house kept its tags (above).
4. **Long-form chunks above ElevenLabs' own advice for accent stability.** Its troubleshooting page says keep a TTS generation under
   800-900 characters for a consistent accent [V9] (A, a general page, not v4-specific); 40% of the characters in our own long-form
   requests went out in requests over 800 characters (M). The research proposed one paragraph per request (~350-800 characters), linked
   by request ids.
5. **PVC on v4 was not available to us.** `GET /v1/models` at the time of research: `eleven_v4` `can_be_finetuned: false` (M), although
   the v4 page announced it as rolling out within days of launch [V1] (A). A PVC costs **$0 extra on Creator** (1 slot included [V12]);
   the real cost is 30 min to 3 h of clean recording and a decent mic. It is the upgrade with the best expected effect on exactly these
   faults (accent, tone variance) [V11] (A). Record the dataset, train on v4 the day it flips to `true`.
6. **v4 measured at about 0.44 credits per character via the API** (incl. the 24-character tag prefix) after the launch promo, 0.12
   during it (M, our usage log), which matched Creator's "275k characters of TTS (v4) included" for 121k credits [V13] (A). Pricing
   changes: read the `character-cost` header dj logs.
7. **Post: less is more, and it is measured.** One long narration of ours already sat at -14.0 LUFS with a loudness range of **1.7 LU**
   (M): a compressor would add nothing. The research proposed level matching + loudnorm, a high-pass at 80 Hz, a *conditional* de-ess
   only on lines whose 4-8 kHz band is >5 dB above the video's median, and a room-tone test under gaps (§5). A broadband de-esser and an
   EQ/bandwidth chain were both rejected in review; both stay off unless the creator's ear picks them.
8. **Automatic QA can catch most faults before anyone hears them:** ASR fidelity, edge clipping, accent (`tools/voice/rhotic.py`:
   American takes 509-1108 Hz, the British ones 32-256 Hz, M) plus an MIT accent classifier as a second opinion, and a hushed/whisper
   screen (level, F0, CPPS per sentence against the video's median) whose features separated the one labelled whispery take we had (§7).

---

## 1. The recipe the research proposed

### 1.1 Long form
| Item | Setting | Why |
|---|---|---|
| Model | `eleven_v4` (not Turbo: Turbo is the real-time variant over the dialogue WebSocket; same cloned-board Elo within the error bars) | [V1][V2][V21] |
| Voice | The creator's clone (an IVC) until a v4 PVC exists and wins the creator's blind test | §6.1 |
| Settings | The house setting: stability 0.95, similarity 0.75 (`config/tts.example.toml`); a different pick only by the creator. v4 has **only** these two; style/speed/speaker boost are ignored and SSML is not supported | [V1] (A) |
| Direction tag | One tag at the head of every request. The research proposed a test (the creator's ear deciding): `[flat, calm, even tone]` vs `[steady, even tone, normal speaking volume]` vs `[casual, even tone, talking to camera]`, avoiding low-arousal words in the head tag (calm, soft, quiet, gentle, relaxed, reflective). The house kept its tags | §2.1; [V3][V5] |
| Line tags | Proposed: only where the content itself invites a hush or a drama voice, `[normal speaking volume]` (or the head tag again) at the start of that sentence. One tag per clause; never sound-like tags. Not in the house method | [V3][V5] (A) |
| Chunk size | Proposed: one paragraph per request, **~350-800 characters** (2-6 sentences), cut at topic turns, never mid-thought. Not under ~250: short requests clip their ends (a lone "now?" ended early, M) | [V9] (A); M |
| Linking | `previous_request_ids` = the last 1-3 sections' ids, same model and settings, all **under 2 hours old** (render a whole video in one sitting). When re-rendering a middle section, also send `next_request_ids` | [V6][V7] (A) |
| Fresh starts | Start an unlinked request after any paragraph that names UK/Australian places or British topics (`[tts] fresh_at`), and keep that paragraph short | §2.2 (M) |
| Seed | One base seed per video for take 1; takes 2-3 use seed+1, +2. A seed buys repeatability for A/B tests, not quality or consistency ("determinism is not guaranteed") | [V7] (A) |
| Takes | Take, then QA (§7). A flagged section: 3 new takes linked both ways, auto-scored. Still flagged after 3: it's content-driven, so change the text or the context, not the seed. An accent fault is a whole-section fault | §2; [V8] |
| Text | Numbers and abbreviations written as spoken; names through a v4 pronunciation dictionary (phoneme rules work on v4) or inline IPA `"/.../"`, each tested over several takes in the full script (house: respellings measured by `tools/voice/saycheck.py`) | [V4][V10] (A) |
| Output | `wav_48000` (measured: works on Creator); log the `character-cost` header | M |
| Speed | atempo 1.04 after generation (the house tempo). v4 has no speed control | [V1] |

### 1.2 Shorts (the house Shorts voice: stability 0.5, `[American accent]` only, the hook sped)
- Keep the whole Short in one request (our Shorts measured 260-1,250 characters): seam problems came from splitting.
- The same content rules apply: a Short's hook voiced in the flat long-form tag voice was heard as whispered, and the untagged Shorts
  voice fixed it (M, §2.1).

### 1.3 The QA gate the research proposed (details §7), in order, all automatic
1. Every sentence said: Whisper large-v3 + normalised WER per sentence; names and numbers cut out and transcribed alone.
2. No tag spoken (the tag text must not appear in the transcript).
3. Edges: no beat starts or ends mid-sound (`edge_faults`, `swallowed`, `weak_endings`, `first_sound` in `tools/dj/tts.py`).
4. Accent: `tools/voice/rhotic.py` per section (< 400 Hz = flag; American measured 509-1108 Hz, British 32-256 Hz), plus CommonAccent
   P(england) as a second screen once calibrated (built: `tools/voice/accent_id.py`).
5. Hushed/whisper: per sentence, level ≤ -3 dB **and** (F0 ≤ -1.5 semitones **or** CPPS ≤ -1.0) against the video's median
   (`tools/qa/breathy.py`).
6. Section consistency: each section's median F0, level, CPPS and syllable rate within 1.5 st / 2 dB / 1.0 / 10% of the video's.
7. Only then the creator's ear, on the finished narration in the video.

### 1.4 Post chain the research proposed (numbers; details §5)
1. Cut beats in measured silence, 5 ms fades; splices crossfaded 10-20 ms inside silence.
2. Per-beat level match (`[tts] level_beats`, ≤ 6 dB).
3. atempo 1.04.
4. High-pass 80 Hz, 12 dB/oct (a male clone's sentence F0 sat at 99-141 Hz, p5-p95, M; iZotope puts speech HPF at 80-100 Hz [V30]).
5. Conditional: split-band de-ess 5-8 kHz, at most 3-4 dB of reduction, **only** on lines whose 4-8 kHz band is >5 dB over the video's
   median (the lines heard as piercing measured 5-10 dB over, M). Never the broadband ffmpeg `deesser` rejected in review.
6. No compressor (LRA 1.7 LU already, M). A true-peak limiter only.
7. Two-pass loudnorm to -14 LUFS integrated, -1.5 dBTP.
8. Test: a room-tone bed at about -62 dBFS under narration gaps where no music plays (the gaps are digital zeros), and keeping the
   model's own in-breaths at -8 to -10 dB instead of cutting them, on long form only. Both to the creator's ear as A/B; Shorts keep
   constant talking.

(The house chain: see "Where the house standard decided differently" above.)

### 1.5 Upgrade decision
- **No new provider, no plan change.** Fix the process (§1.1-1.4). Pro ($99/month, 600k credits) only if credits run out: its only
  other gain, 44.1 kHz PCM, is matched by 48 kHz WAV on Creator.
- **Next: a PVC on ElevenLabs** ($0 plan cost). The creator records 60-120 min of clean, single-style narration with a better mic; train
  on v4 the day `can_be_finetuned` turns `true`; blind A/B vs the IVC. The same dataset also works for HeyGen (20+ min) and Cartesia
  (30+ min) PVCs.
- **Optional cheap test: HeyGen Voice IVC** (free to create during its preview; ~$30 per 1M characters [V21]): one 60-s passage, blind
  against v4, the creator's ear. It needs the creator's own HeyGen account and key. No tags and no stitching, so only worth switching if
  the creator clearly prefers it.

---

## 2. Five faults: cause and fix

### 2.1 Whispery / "creepy narrator" takes
- **What happened (a reviewer's verdict on one of our builds):** the narration turned into a whispering, creepy storyteller on hushed
  scene descriptions (a close-up of fog drifting over a lake, a candle guttering out, an empty hallway at night). A Short's hook voiced in the flat
  long-form tag voice was heard as whispered too.
- **Evidence:**
  - v4 interprets emotion from the text itself ("The models interpret emotional context directly from the text input") [V4] (A), and
    a tone that opens a sentence carries across the line [V5] (A).
  - ElevenLabs' tag list files calm words under "Calm and reflective" and "Low energy", and gives `[hushed and reverent, like a nature
    documentary narrator]` as an example direction [V5] (A). The head tag `[flat, calm, even tone]` is low-arousal, and stability 0.95
    holds the delivery close to that baseline [V1] (A). The scene text (drifting fog, a dying candle, a dark hallway, "horrifying
    readings") supplies the intimacy or suspense.
  - ElevenLabs' troubleshooting: volume drops and whispering are "most likely a stability issue or a voice issue", worse with wide dynamic
    range, low rumble and weaker samples [V9] (A, a general page).
  - **Measured (M, `tools/qa/breathy.py`):** a Short's hook in the flat long-form voice (heard as whispered) against the same hook in the
    Shorts voice: level **-4.0 dB**, F0 median 118.5 vs 130.4 Hz (**-1.7 semitones**), F0 range 10.2 vs 12.8 st, CPPS 9.54 vs 10.39,
    4-8 kHz/0.1-1 kHz ratio +2.6 dB. One labelled pair only, so the thresholds in §7 are a starting point, not a law.
  - Across one long narration's 293 sentences (M) the same screen ranks dramatic lines highest (lines like "Please tell me you're
    kidding.", "And the engineer said the readings were horrifying.", "And with that, he's inside the bank's vault."), as the
    hypothesis predicts. **Not checked by ear.**
- **Fixes proposed:** (1) the tag test in §1.1 (keep "even", drop "calm"; ask for normal volume); (2) a `[normal speaking volume]` line
  tag on sentences that describe intimate, quiet or eerie scenes; (3) write those lines as a commentator, not a storyteller (§4); (4) the
  §7 screen; (5) longer term, a PVC trained on the creator's normal-volume delivery (PVC is "more consistent across different speech
  types" [V11] (A)). The house keeps (3) and (4) (`tools/voice/voice_check.py` WHISPERED, `tools/qa/breathy.py`) and its tags as they are.

### 2.2 Accent drifting British
- **Measured in our logs (M):** a line about Australia pulled British in 6 of 6 takes (rhotic 32-256 Hz) and was rewritten with an
  American place, which the fact allowed; text set in England pulled 5 of 5 renders British; 16 re-draws of two British sections at
  stability 0.5 and 0.72 with an `[American accent]` tag all stayed British; lines about the UK and Australia pull the accent and carry
  it into the linked section after; splitting the request at 0.3-s pauses fixed it.
- **Evidence:** "The AI can sometimes switch languages or accents throughout a single generation, especially if that generation is longer
  ... keep text generations under 800-900 characters" [V9] (A). Request stitching conditions the next request on the previous audio [V7]
  (A), which explains the carry-over. In same-language generation v4 preserves the clone's accent [V1] (A), and an IVC "may struggle
  with uncommon accents"; if an instant clone doesn't capture the voice or accent well, ElevenLabs points to Professional Voice Cloning
  [V14] (A). `language_code` only takes a language (ISO 639-1, "en"), not a region [V7] (A), so it can't pin American.
- **Fix:** paragraphs ≤ 800 characters; any paragraph with UK/Australian content is short, unlinked to what follows (`fresh_at`), and
  screened; an accent tag alone is not enough (it helped only half the time, M); rewriting the content (an American place for an
  Australian one) is a valid fix when the fact allows; a PVC later.

### 2.3 Consonants clipped at beat edges
- **Measured (M):** ElevenLabs' character times run 30-60 ms behind the sound; the head tag can delay the first character's time by up
  to 0.9 s; a short line voiced alone comes back with its last word clipped ("now?" ended 0.08 s early in 3 of 3).
- **Fixed in code:** cuts in measured silence (`sound_start`, `sound_end`, `first_sound`, `gap_between` in `tools/dj/tts.py`), the build
  refuses a beat that starts or ends mid-sound, single lines voiced inside a longer request (`tools/voice/voice_context.py`).
- **Keep:** never cut on vendor timestamps alone; never send a lone short line; 5 ms fades; transcribe each cut beat alone and compare its
  first and last word (§7).

### 2.4 Tone changing between sections
- **Evidence:** stitching exists for exactly this: "abrupt changes in prosody from one chunk to another" [V6] (A); ids must be under 2 h
  old; best with the same model; up to 3 ids; `next_request_ids` when regenerating a middle clip [V6][V7] (A). v4 "may shift over time"
  as it is retrained [V1] (A), and ElevenLabs offers no dated snapshot (Cartesia does [V24], for comparison).
- **Open (unverified):** what the API does with request ids older than 2 h (ignored or an error). A cache of approved sections can be
  days old; if its ids are re-sent as `previous_request_ids`, store the request time with each take, drop ids over ~110 min, and fall
  back to `previous_text` (≤ the paragraph before).
- **Fix:** render a whole video in one sitting; same voice, model, settings, tag and seed family throughout; re-render a middle section
  with both previous and next ids; the §7 section-consistency screen; once a month, one fixed reference paragraph re-rendered to catch
  model drift (~500 characters ≈ 220 credits).

### 2.5 Lines sounding AI-like
- **Two different causes.** (a) *Wording*: the lingo problem (`standard/research/LINGO.md`, `standard/research/HUMAN_SCRIPT_STUDY.md`),
  out of scope here except §4. (b) *Delivery*: stability 0.95 + "flat" gives every sentence the same melody; ElevenLabs: higher
  stability "can result in a monotonous voice with limited emotion" [V7] (A). The flat delivery is the house choice for long form, so it
  stays; but it is a known trade-off, and any "sounds AI" note on a long-form line is first checked against the tag finding in §1.1.
- **What helps without changing the house voice:** sentences written the way the creator talks (§4), the clone's own small reactions in
  the text (they carry prosody), no CAPS and no "!" in long form (a CAPS emphasis on a money figure read as overdone in review), a PVC
  later (it copies stylistic tendencies an IVC cannot reliably reproduce [V11] (A)).

---

## 3. ElevenLabs evidence

### 3.1 Models
| Model | What it's for (ElevenLabs) | Limits | Cloned-voice arena | Notes |
|---|---|---|---|---|
| `eleven_v4` | "highest-quality ... content creation, audiobooks, character voiceovers" [V1] | 10,000 chars; stability + similarity only; no SSML [V1][V2] | 1159 ±14, #4 [V21] | tags, IPA, dictionaries with phoneme rules, stitching |
| `eleven_v4_turbo` | real-time agents, Text to Dialogue WebSocket [V1][V2] | | 1162 ±14, #3 | API list $0.04/1K vs $0.08 for v4 [V13]; latency is not the problem here |
| `eleven_v3` | previous generation | 5,000 chars; **no request stitching**; PVCs "not fully optimized" [V3][V6] | 1073, #11 | |
| `eleven_multilingual_v2` | "Most stable on long-form generations" [V2] | 10,000 chars; SSML breaks | 996, #29 | PVCs auto-train on it; can_be_finetuned true (M). The house uses no fallback model: it sounds like computer speech |
| `eleven_flash_v2_5` | low latency, 50% cheaper on the API [V2] | 40,000 chars | 986 | |
- Measured on our account (M): `eleven_v4` and `eleven_v4_turbo` `can_be_finetuned: false`, no style, no speaker boost, 10,000
  characters per request; multilingual v2 and Flash v2.5 `true`.
- The changelog [V8] added `audio_effects` (filter preset, distance, reverb, background noise, pan; no extra cost) to TTS. Not for this
  pipeline (the voice stays dry). The deprecated `seed` there belongs to the effects object; the TTS `seed` stays [V7].

### 3.2 Settings
- **Stability** (default 0.5): lower = "broader emotional range"; higher = "monotonous voice with limited emotion" [V7] (A). On v4: "Higher
  values keep the performance closer to a fixed baseline" [V1] (A).
- **Similarity** (default 0.75): higher values hold closer to the reference, which can cost some naturalness [V1].
- **Style, speaker boost, speed:** not available on v4 [V1] (A); measured ignored (M).

### 3.3 Tags and direction (v4)
- Tags go before the words they affect; the emotion carries forward until the next tag; combine inside one bracket `[whispering, playful]`;
  "Use one tag per clause"; give the model a full scene, since v4 performs better with context [V5] (A).
- Write tags that clearly describe the voice quality you want (e.g. `[low, gravelly voice]`) rather than something that could be read as
  a sound cue; tags can be rendered as sound effects [V3] (A).
- Tags land more readily when the delivery is already in the voice's training data: a meditative voice shouldn't shout, a hyped voice
  won't whisper convincingly [V3] (A).
- Free-text directions work: `[like a sports commentator, speeding up]`, `[starting calm, then losing patience]` [V5] (A).
- Plain descriptive text ("she said excitedly") is **spoken** [V4] (A): directions must be in brackets.
- The "Enhance" prompt's own rules: never change the words; tags describe only the voice, never music or effects [V3] (A).
- `[strong X accent]` is an "experimental" tag [V3] (A); `[American accent]` alone helped only half the time against content-driven
  drift (M).

### 3.4 Punctuation and pauses (v4)
- "Ellipses (...) add pauses and weight", "Capitalization increases emphasis", "Text structure strongly influences output with v4" [V3] (A).
- Dashes cut a speaker off mid-sentence, and exclamation marks add intensity [V5] (A).
- v4 and v3 do not support SSML `<break>`; pauses come from punctuation and structure [V3] (A). Measured: a full stop places a pause
  exactly where a joke needs it; "..." landed it on the wrong word (M).

### 3.5 Pronunciation and normalization
- Normalization is on by default; `apply_text_normalization` auto/on/off [V7] (A). Writing numbers, dates, units and acronyms out as words
  is the reliable route; ElevenLabs even publishes the LLM prompt it recommends for it [V3] (A).
- v4 reads inline IPA in slashes, `"/təˈmeɪtoʊ/"`, with stress marks; results can still vary, so generate more than once and select the
  best result [V3] (A).
- Pronunciation dictionaries: up to 3 per request, case-sensitive, first match wins; **phoneme rules work only on `eleven_v4`,
  `eleven_flash_v2` and `eleven_v3`**, alias rules everywhere [V10] (A).
- The method that holds: test a respelling in the full script, over several takes, each instance cut out and transcribed alone (house:
  `tools/voice/saycheck.py` measures every take that says a respelled name).

### 3.6 Long-form consistency
- Stitching: `previous_text`/`next_text` or `previous_request_ids`/`next_request_ids` (max 3 each; ids win over text when both are sent);
  best when the same model is used; ids no older than two hours; not on v3; zero-retention mode disables it [V6][V7] (A).
- The official stitching example uses `eleven_v4` [V6] (A).
- ElevenLabs: degradation and accent drift grow with generation length; break text into sections under 800 characters [V9] (A, a
  general troubleshooting page; whether v4 still needs this is unverified, but our accent logs agree).
- v4 launch blog: preserves speaker identity more reliably across generations, dialogue, narration and regenerated lines [V15] (A,
  vendor claim).
- Free regenerations solve roughly half of quality issues, website only [V4] (A). That figure is for random faults; the accent and
  whisper faults we measured were not random (M).

### 3.7 Instant vs Professional clone
| | IVC (instant) | PVC |
|---|---|---|
| How | conditions on the sample at generation time, no training [V11] | fine-tunes the model on the voice [V11] |
| Audio | 1-2 min; more than 3 minutes can even be detrimental [V16] | ≥ 30 min; at least an hour, ideally close to three hours [V12] |
| Behaviour | generalises less well across speech styles; quality ceiling = the reference audio [V11] | "substantially higher" quality, more consistent across speech types, better emotional range [V11] |
| Copies | speed, inflections, accent, tonality, breathing, noise, mouth clicks [V16] | a near-perfect clone of what it hears, artefacts included [V12] |
| Style | consistent performance throughout the sample [V16] | one speaking style [V12]; v4: stick to a single speaking style [V1] |
| Levels | RMS -23 to -18 dB, true peak -3 dB [V16] | same [V12] |
| Plan | Starter and up | Creator: 1 slot; Scale 3; Business 10 [V12] |
| Time | seconds | fine-tune 3-6 h typical (status page: 6-24 h) [V12] |
| v4 | works | `can_be_finetuned: false` on our account at the time of research (M): re-check `GET /v1/models` |
- Recording kit ElevenLabs suggests: an XLR mic into an interface (AT2020 or Rode NT1 into a Focusrite), pop filter, about two fists from
  the mic, a deadened room [V12] (A). Prices not checked.
- Verification uses the same equipment and delivery as the samples [V12] (A).

### 3.8 Cost (measured)
- v4 via the API: ~0.44 credits per character including the head tag after the launch promo (110 credits for 225 + 24 characters; 67
  for 129 + 24), 0.12 during the promo (M, usage log). It matched 121k credits ≈ "275k characters of TTS (v4)" on Creator [V13].
  Pricing changes; the `character-cost` header is the truth.
- One long video of 2,500 words (5.46 characters per word, M) ≈ 13,650 characters ≈ **6,300 credits per pass** at that rate, ~8,200
  with 30% retakes.
- Creator: $22/month, 121k credits on the pricing page (our account showed 131,000), rollover up to 2 months; Pro $99 for 600k [V13] (A).

---

## 4. Writing for TTS so it sounds like a YouTuber

The main source is our measured corpus of real creators' captions (41,242 words, in the niche we studied); ElevenLabs and broadcast
guides agree where they overlap. The chat measures the creator's own niche the same way (`standard/research/LINGO.md`).
- **Talk in sentences of 12-18 words on average with real variety** (creators: mean 16.8, median 14, M). Broadcast guides say the same:
  one idea per sentence, about 15-20 words [V31] (C). Long run-ons joined with *and / so / 'cause* sound human; a string of 6-word
  fragments sounds like an ad.
- **Start plenty of sentences with And / So / Now / But** (28% of creators' sentences, M).
- **Punctuation is direction** [V3][V5] (A): full stop = a real pause exactly there; comma = a breath-group break; "..." = weight *and*
  hesitation (keep it for comic timing); dash = a cut-off; "!" = intensity; CAPS = emphasis. For the flat long-form voice: no CAPS, no
  "!", "..." only when the joke needs the pause. No colons, semicolons or em dashes in the voice column (`standard/SCRIPTS_AND_PACKAGING.md`).
- **Numbers as spoken:** "four hundred seventy-five million", "twenty twenty-six", "iPhone 17", "Model 3" [V3] (A); round them when the
  exact figure doesn't matter (broadcast guides [V31], C).
- **Contractions** (88% in real speech, M): it's, don't, that's, gonna where the creator says it.
- **Write as a commentator, not a storyteller, on quiet scenes.** "Look at the fog on that lake, you can see every swirl" keeps the
  presenter voice; "Look at how the fog drifts over the lake." invites the narrator voice. Same for suspense lines. This is the text half
  of the §2.1 fix (inferred from v4's documented behaviour plus our measured flags; the creator's ear confirms).
- **Watch place words.** A paragraph naming UK/Australian places or British topics is short and stands alone (§2.2).
- **No spoken stage directions** outside brackets [V4] (A).
- **Read-aloud check** and the script checklist before voicing (`standard/SCRIPTS_AND_PACKAGING.md`, `standard/CHECKLIST.md`); the
  creator's own phrasing patterns (`creator/PROFILE.md`) for reactions.

---

## 5. Post-processing TTS

| Step | Number | Evidence |
|---|---|---|
| Cut and splice | cuts in measured silence, 5 ms fades, 10-20 ms crossfades for patches | M; dialogue-editing practice: hide seams [V33] (C) |
| Level match | per beat, voiced level, ≤ 6 dB correction (`[tts] level_beats`) | louder lines heard as almost piercing in one of our builds (M) |
| Match patched takes | short-term loudness of the voiced span within ±0.5 LU of its neighbours; F0 median within 1 semitone, else a new take (don't pitch-shift) | M practice; pitch-shifting a clone is untested |
| High-pass | 80 Hz, 12 dB/oct (proposed) | iZotope: speaking voices have little energy below ~85 Hz; HPF 80-100 Hz [V30] (B); a male clone's sentence F0 p5 = 99-111 Hz (M) |
| De-ess | split-band 5-8 kHz, ≤ 3-4 dB, only lines >5 dB over the video's 4-8 kHz median (proposed) | iZotope: sibilance 4-9 kHz, over-de-essing makes a lisp [V30] (B); M: piercing lines 5-10 dB over; a broadband ffmpeg `deesser` at i=0.5 audibly lowered the voice's quality in review |
| EQ | none by default. Only a measured, static correction when a patch differs >1.5 dB in a 1/3-octave band from its neighbours | an EQ/top-band chain read as robotic in review; v4 copies the sample's EQ [V1] |
| Compression | none (LRA already 1.7 LU on one long narration, M); if ever needed: 2:1, 2-3 dB of gain reduction | iZotope's 2:1 starting point [V30] (B) |
| Breaths | test: keep the model's in-breaths at -8 to -10 dB on long form instead of cutting to 0.12 s gaps | breaths raised naturalness MOS in one listening test (40 raters, VITS) [V32] (B, single study) |
| Room tone | test: a constant bed at about -62 dBFS under gaps that have no music; the gaps are digital zeros | "holes of digital silence" sound switched on/off [V33] (C) |
| Tempo | atempo 1.04 (WSOLA), the house tempo | a rubberband stretch at 1.28x sounded robotic in review |
| Loudness | narration -14 LUFS integrated, -1.5 dBTP; final mix -14 LUFS, ≤ -1 dBTP, LRA ≤ 7 LU | YouTube's reference is widely measured at -14 LUFS, not officially published [V34] (C); AES TD1008 suggests -18 LUFS for speech-only streaming [V35] (C summary), not this case since YouTube only turns loud videos down |
- Not verified (search cap): concrete de-esser attack/release values and an independent source for room-tone levels. The -62 dBFS
  figure is a starting point for an A/B, not a sourced standard.

---

## 6. Alternatives

### 6.1 The cloned-voice arena (Artificial Analysis "Controlled Voice": every model clones the same 8 voices, 4 US + 4 UK; blind pairs) [V21] (B)
| # | Model (maker) | Elo ±95% | Price per 1M chars (AA) | Cloning | Fit |
|---|---|---|---|---|---|
| 1 | HeyGen Voice (HeyGen, 2026) | 1198 ±15 | $30 | IVC from ≤3 min (free in preview); PVC from 20+ min, paid slot [V22] (A) | plain prose only (no tags), 5,000 chars, no stitching documented, 44.1 kHz WAV, character timestamps; seed/speed/pitch only on PVC [V23] (A). Worth one blind test |
| 2 | Qwen-Audio-3.1-TTS-Plus (Alibaba) | 1186 ±14 | $19.3 | clone API details and pricing **unverified** (sources conflict) | low priority |
| 3 | Eleven v4 Turbo | 1162 ±14 | $40 | as v4 | real-time variant |
| 4 | **Eleven v4 (the house model)** | **1159 ±14** | $80 | IVC now, PVC pending | tags, stitching, timestamps, IPA |
| 5 | Sonic 3.6 (Cartesia) | 1149 ±14 | $49 | IVC on Pro ($5/mo); PVC on Startup ($49/mo, 1.25M credits; training free; 1 credit/char) [V25] (A) | **dated snapshots that never change** [V24] (A); PVC speed/volume fixed by the dataset [V26] (A) |
| 6 | Realtime TTS-2 (Inworld) | 1144 ±13 | $20.8 | not researched | |
| 14 | Fish Audio Drama 3 Preview | 1059 ±15 | $15 | bracket directions [V27] (A); weights under a research licence [V28] (A) | below v4 |
| 24 | Fish Audio S2.1 Pro | 1015 ±14 | $15 per 1M UTF-8 bytes [V29] (A) | IVC + PVC | below v4 |
| 29 | Eleven Multilingual v2 | 996 ±13 | $100 | PVC trainable | below v4 |
| 39 | Chatterbox (Resemble) | 930 ±14 | $25 | | well below; Resemble's pricing page lists detection products only [V36] (A) |
| 42 | XTTS v2 (Coqui, open) | 830 ±17 | | | bottom; non-commercial weights |
- **Reading it:** an Elo gap of 39 means ~56% preference, 27 means ~54% (M, computed). Short single lines, 8 voices, half of them British:
  it says nothing about 10-minute consistency, accent drift or PVCs. With each provider's own voices, v4 is #2 at 1329, above every rival [V20].
- **Open weights:** the best on the cloned board is Fish Drama 3 (1059, research licence); every open model sits ≥100 Elo under v4 [V21].
  An earlier licence screen ruled out F5-TTS and XTTS-v2 weights for commercial use; the local VoxCPM fallback
  (`tools/voice/voice_cli.py`) is not ranked.
- **OpenAI:** custom voices are limited to eligible customers through its sales team and need a consent recording [V37] (A). Not
  available to a typical creator.
- **PlayHT:** acquired by Meta (2025-07) and shut down, the platform ending 2025-12-31 [V38] (C, secondary sources only).
- **HeyGen launch claims** (#1 debut, PVC add-on "$99 a month") come from secondary coverage [V39] (C); HeyGen's own price for PVC slots
  sits behind its dashboard (unverified).

### 6.2 Verdict
No provider is clearly better for this use. The upgrade with real expected gains is **the creator's own PVC on v4** (free slot, more
consistent, better accent capture [V11][V14]), blocked only by ElevenLabs' rollout at the time of research (M). A HeyGen IVC blind test
costs almost nothing and is the creator's call. Cartesia's dated snapshots are the one feature ElevenLabs lacks for long-run
consistency; not worth switching for (lower arena score, $49/mo).

---

## 7. Automatic QA of takes

| Check | Tool | Threshold (start) | Status |
|---|---|---|---|
| Every word said | faster-whisper large-v3 + jiwer with Whisper's normaliser and a name map (the house tools default to small.en) | any content-word error; names/numbers cut out and transcribed alone | method; large-v3 to install for it |
| Tag not spoken | same transcript | tag words absent | built |
| Edges | `edge_faults`, `swallowed`, `weak_endings`, `first_sound` in `tools/dj/tts.py` | last consonant > 28 dB under the take's others | built |
| Accent | `tools/voice/rhotic.py` (F3 dip at written post-vocalic r, Praat) | flag < 400 Hz (American 509-1108 Hz, British 32-256 Hz, M) | built |
| Accent, second opinion | SpeechBrain CommonAccent XLSR, 16 accents incl. `us` and `england`, MIT [V40] (A model card), ~95% on Common Voice [V41] (B) | P(england) per 5-10 s; calibrate first on the creator's real sample and on known British takes | built as `tools/voice/accent_id.py` (CommonAccent's ECAPA variant); its behaviour on synthetic speech **unverified** |
| Hushed / whisper | `tools/qa/breathy.py`: per-sentence level, F0 median, F0 range, CPPS (Praat), 4-8 kHz/0.1-1 kHz ratio | level ≤ -3 dB **and** (F0 ≤ -1.5 st **or** CPPS ≤ -1.0) vs the video's median. One long narration's spread: level sd 1.6 dB, CPPS sd 0.88, F0 p5-p95 111-141 Hz (M) | built; one labelled pair only |
| Section drift | per-section medians of F0, level, CPPS, syllables/s | > 1.5 st, > 2 dB, > 1.0 CPPS, > 10% rate from the video median | proposed |
| Voice identity | WavLM-base-plus-sv cosine to the creator's centroid (measured: the speaker's own real clips 0.991-0.997, another speaker 0.51-0.62) | below the video's p5 | the voice guard carries speaker embeddings (`tools/voice/voice_guard.py`) |
- Literature support for the whisper screen: whispered speech lacks F0 and harmonics, strongest in the lowest quarter of the spectrum
  [V42] (B). CPPS as a breathiness measure is standard in voice science, but its source was not re-checked (search cap): treat it as
  unverified here; our own pair supports it.
- Alignment for QA can also use ElevenLabs' Forced Alignment API (priced like speech-to-text) [V43] (A); local Whisper is free and enough.

---

## 8. Open questions (unverified)
1. What the TTS API does with `previous_request_ids` older than 2 hours (ignored, error, or used).
2. Whether the 800-900 character advice [V9] still applies to v4 (our logs say accent drift does; a controlled test would settle it).
3. Whether a non-"calm" head tag removes the hushed takes without losing the flat delivery (the house keeps its tags).
4. When v4 PVC fine-tuning reaches the creator's account (re-check `GET /v1/models` before planning the recording).
5. HeyGen PVC slot price and whether its clone beats v4 on the creator's voice (blind test).
6. Room-tone level and breath handling (the creator's A/B).
7. CommonAccent's and the whisper screen's error rates on the creator's clone (calibrate on labelled takes before trusting either).

---

## Sources
*Vendor pages are current pages, read as they stood at the time of research.*
- [V1] A · Eleven v4 (models, settings, PVC rollout, accents, "may shift over time") · https://elevenlabs.io/docs/overview/capabilities/text-to-speech/eleven-v4.md
- [V2] A · Models · https://elevenlabs.io/docs/overview/models.md
- [V3] A · TTS best practices (pauses, IPA, dictionaries, normalization, prompting v4, Enhance prompt) · https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices.md
- [V4] A · Text to Speech overview (prompting from text, spoken descriptions, seed, free regenerations, audio effects) · https://elevenlabs.io/docs/overview/capabilities/text-to-speech.md
- [V5] A · Blog: Audio Tags list (tag groups, one tag per clause, full scene, free-text directions) · https://elevenlabs.io/blog/elevenlabs-audio-tags-list ; Blog: directing v4 (a tone carried across the line) · https://elevenlabs.io/blog/emotional-text-to-speech-with-eleven-v4
- [V6] A · Request stitching guide (v4 example, not for v3, 2-hour ids) · https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/request-stitching.md
- [V7] A · API: Create speech with timing (seed, previous/next text and ids, normalization, language_code, voice settings) · https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps.md
- [V8] A · Changelog (audio effects) · https://elevenlabs.io/docs/changelog/2026/10/12.md · https://elevenlabs.io/docs/changelog/2026/10/5.md
- [V9] A · Help: whispering, accent, tone · https://elevenlabs.io/docs/help-center/troubleshooting/why-does-my-voice-start-whispering-change-accent-change-tone-or-break.md ; Troubleshooting (800-900 characters, accent drift, degradation) · https://elevenlabs.io/docs/eleven-creative/troubleshooting.md
- [V10] A · Pronunciation dictionaries guide · https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries.md
- [V11] A · Voice cloning: how it works (IVC vs PVC) · https://elevenlabs.io/docs/eleven-api/concepts/voice-cloning.md
- [V12] A · Professional Voice Cloning (audio length, style, equipment, slots, statuses) · https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/professional-voice-cloning.md
- [V13] A · Pricing (plans, credits, rollover) · https://elevenlabs.io/pricing ; API pricing (v4 $0.08/1K, Creator 275k v4 characters) · https://elevenlabs.io/pricing/api
- [V14] A · Help: voice or accent not correct after cloning · https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/why-does-my-voice-or-accent-not-sound-correct-after-cloning.md ; adding models to a PVC · https://elevenlabs.io/docs/help-center/product/voices/voice-cloning/how-do-i-add-or-upgrade-the-models-used-to-train-my-professional-voice-clone.md
- [V15] A · Blog: Introducing Eleven v4 (2026) · https://elevenlabs.io/blog/eleven-v4
- [V16] A · Instant Voice Cloning · https://elevenlabs.io/docs/eleven-creative/voices/voice-cloning/instant-voice-cloning.md
- [V20] B · Artificial Analysis, TTS leaderboard, providers' own voices (v4 Turbo 1330, v4 1329) · https://artificialanalysis.ai/text-to-speech/leaderboard
- [V21] B · Artificial Analysis, Controlled Voice leaderboard (8 cloned voices; Elo, prices, open-weights flags) · https://artificialanalysis.ai/text-to-speech/leaderboard/controlled-voice
- [V22] A · HeyGen Voice model (instant vs professional, slots) · https://developers.heygen.com/docs/models/heygen-voice.md ; Instant clone · https://developers.heygen.com/docs/voices/heygen-voice-instant-clone.md ; Professional clone · https://developers.heygen.com/docs/voices/professional-voice-clone.md
- [V23] A · HeyGen Text to Speech (fields, 5,000 chars, 44.1 kHz WAV, timestamps) · https://developers.heygen.com/docs/voices/heygen-voice-speech.md
- [V24] A · Cartesia Sonic 3.6 (GA, dated snapshots) · https://docs.cartesia.ai/build-with-cartesia/tts-models/latest.md
- [V25] A · Cartesia pricing (plans, PVC training free, overage) · https://cartesia.ai/pricing ; https://docs.cartesia.ai/pricing.md
- [V26] A · Cartesia Pro Voice Clone (30+ min, speed/volume fixed, recording tips) · https://docs.cartesia.ai/build-with-cartesia/capability-guides/clone-voices-pro.md
- [V27] A · Fish Audio Drama 3 · https://docs.fish.audio/features/text-to-speech/drama-3.md
- [V28] A · Hugging Face model card fishaudio/drama-3 (licence) · https://huggingface.co/fishaudio/drama-3
- [V29] A · Fish Audio pricing · https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits.md
- [V30] B · iZotope: 10 tips for a great sounding podcast (HPF 80-100 Hz, 2:1, de-ess) · https://www.izotope.com/community/blog/10-tips-for-a-great-sounding-podcast ; How to EQ vocals (over-de-essing) · https://www.izotope.com/community/blog/how-to-eq-vocals ; Crafting a basic vocal chain · https://www.izotope.com/en/learn/crafting-a-basic-vocal-chain.html (read via search summaries, not opened in full)
- [V31] C · Media Helping Media, how to write a radio news script · https://mediahelpingmedia.org/how-to/how-to-write-a-radio-news-script ; UF/IFAS writing for the ear · https://edis.ifas.ufl.edu/publication/wc193 (search summaries)
- [V32] B · Yang, Koriyama, Saito, breath detection and insertion for TTS, MOS test (arXiv 2402.00288) · https://arxiv.org/abs/2402.00288
- [V33] C · Frame.io workflow guide, room tone · https://workflow.frame.io/guide/roomtone (search summary)
- [V34] C · Meterplugs (Ian Shepherd), YouTube changes loudness reference to -14 LUFS (2019) · https://meterplugs.com/blog/2019/09/18/youtube-changes-loudness-reference-to-14-lufs.html
- [V35] C · Telos Alliance, understanding loudness for streaming audio (AES TD1008 summary) · https://docs.telosalliance.com/docs/understanding-loudness-for-streaming-audio
- [V36] A · Resemble AI pricing · https://www.resemble.ai/pricing/
- [V37] A · OpenAI custom voices · https://developers.openai.com/api/docs/guides/custom-voices
- [V38] C · PlayHT shutdown write-ups · https://texttolab.com/blog/play-ht-shutdown-alternatives · https://cognitivefuture.ai/elevenlabs-vs-playht-alternatives/
- [V39] C · HeyGen Voice launch coverage · https://alphasignal.ai/news/heygen-voice-beats-elevenlabs-and-alibaba-to-top-tts-rankings · https://www.orcarouter.ai/blog/heygen-voice-tops-controlled-voice-arena
- [V40] A · Model card Jzuluaga/accent-id-commonaccent_xlsr-en-english (16 accents, MIT) · https://huggingface.co/Jzuluaga/accent-id-commonaccent_xlsr-en-english
- [V41] B · CommonAccent paper (INTERSPEECH 2023, arXiv 2305.18283) · https://arxiv.org/abs/2305.18283
- [V42] B · Whisper vs normal speech from spectral envelope (arXiv 2408.14777) · https://arxiv.org/abs/2408.14777
- [V43] A · ElevenLabs Forced Alignment · https://elevenlabs.io/docs/overview/capabilities/forced-alignment.md
- Own data (M): the read-only `GET /v1/models` and `/v1/user/subscription`; our TTS usage log (1,211 requests); one long narration's
  loudness (`ffmpeg ebur128`); per-sentence features on one long narration's 47 sections and a Short's six (`tools/qa/breathy.py`);
  accent and edge measurements from our build logs.
