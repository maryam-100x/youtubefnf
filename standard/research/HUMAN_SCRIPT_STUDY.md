# Human script study: why a chat's narration reads as AI, and how to write it so it doesn't

*The question: what makes a narration script written by the chat read as AI, what makes it read like a popular, relatable, likeable
human YouTuber, and how far each method gets, proved by blind tests against real creators' passages. Working notes, round by round;
the newest results close each section, and where a later round corrects an earlier number, it says so. The method that came out of
it is in `standard/SCRIPTS_AND_PACKAGING.md` and `standard/SCRIPT_TRAINING.md`. The tools: `tools/script/human_corpus.py` (the
corpus), `tools/script/voice_metrics.py` (the measures), `tools/script/blind_test.py` (the first blind tests),
`tools/script/judge_panel.py` (the panel and the content gate), `tools/script/tell_lint.py` (the named giveaways) and
`tools/script/pair_test.py` (style only). Read with `standard/research/AI_TELLS.md`, `standard/research/VIEWER_AI_TELLS.md`,
`standard/research/LINGO.md` and `standard/research/LINGO_MEASURED.md`.*

*How to read it:*
- *The evidence is our own measurement: blind judges' scores on passages whose authorship only the key knows. A score is P(AI), the
  judge's probability that a passage is AI (an "AI" verdict at 80 = 0.80, a "HUMAN" verdict at 80 = 0.20).*
- *Judges are fresh Claude agents with no tools (Opus and Sonnet; Haiku is too weak to use), and in round 2 also GPT models through
  the Codex CLI.*
- *The literature in §8.2 is graded: **A** = primary or peer-reviewed, **B** = preprint or reputable, **C** = blog or vendor.*
- *Creators in the niche we studied are described by kind ("a scripted voice-over channel in the niche"), not named; creators outside
  it keep their names. Our own scripts are described ("Script A, a technical breakdown of ours"), never numbered. Every example line
  from our niche is a neutral stand-in with the same feature as the original.*

---

## 1. Why rules and banned phrases never fixed it

Answering each complaint with a new rule or a banned phrase failed again and again: the next draft produced a new tell nobody had
named yet ("full-on chaos", "honestly", "a world that never stops moving"). The way the lines were written never changed.
- **The measures were surface statistics** that can't tell AI from human here. Words a sentence: a faceless channel its viewers call
  AI, 13.5; fern, human, 13.8.
- **The sentence-length target flipped four times.**
- **The reference "language models" were documentary narrators** picked for their editing, not their words.
- **Nobody ran a blind test.**
- **The creator's interview answers were blended in "in their meaning, not their wording"**, so a human's own words were rewritten
  into the house style, which (§4) is the AI signature.

## 2. The corpus

`tools/script/human_corpus.py`: captions only, a spare account's cookies, a few seconds apart. The words stay in the media root
(`MEDIA/script/human_corpus/`), never in git. About 100 videos, ~400,000 words, in groups:

| Group | What it holds |
|---|---|
| `talk` | personality creators talking to the camera |
| `voice` | scripted voice-over channels in the niche |
| `tech` | technical explainers (e.g. Corridor Crew) and a technical-analysis channel |
| `doc` | documentaries (ColdFusion, John Coogan, a journalist covering the niche) |
| `ref` | the reference channels (fern, Nexpo, LEMMiNO, Patrick Cc:, Wendover, and the niche's top creators) |
| `script` | native-English scripted creators whose captions are their scripts (Linus Tech Tips, Half as Interesting, and design, history and comedy explainers) |
| `faceless` | channels that may be AI-written |
| ours | our own uploads' captions |

**Caveats found on the way:**
- Older auto captions have no punctuation, so they are kept for word counts only.
- Auto captions carry "uh", stutters and mishearings, and the blind judges used those as human evidence. So `blind_test.py` strips
  them (`declutter`) before a human passage goes in.
- Many big channels carry AI dubs in other languages. Their English is still the original audio.

## 3. The measurements (`tools/script/voice_metrics.py`)

Two of our scripts against 32 punctuated human narrations (the voice, ref, tech and doc groups), per 1,000 words. The human column
gives the 10th percentile / median / 90th percentile.

| | Script A (ours, a technical breakdown) | Script B (ours, a well-performing long video) | humans |
|---|---|---|---|
| sentence length spread (SD, words) | 4.9 LOW | 8.5 | 7.5 / 8.5 / 11.9 |
| sentences of 25+ words | 0% LOW | 23% | 7% / 15% / 32% |
| numbers | 54.5 HIGH | 54.5 HIGH | 11 / 20 / 35 |
| "X says / according to" | 6.9 HIGH | 3.2 HIGH | 0.3 / 1.4 / 3.1 |
| "called / which means" glosses | 2.9 HIGH | 1.1 | 0.3 / 1.2 / 2.5 |
| "even" | 4.3 HIGH | 4.3 HIGH | 0.8 / 1.9 / 3.9 |
| questions | 0 LOW | 0 LOW | 0.5 / 3.8 / 8.1 |
| "we" | 1.1 LOW | 3.2 | 1.8 / 7.8 / 16.2 |
| discourse markers (so, like, I mean, basically, okay...) | 7.4 | 27.8 | 3.7 / 13 / 19.7 |

The research on LLM text says the same (`standard/research/AI_TELLS.md`): sameness is the strongest measured signal, and the newest
GPT models hold sentences to an 8-20 word band. A house bar of "about 10 words a sentence, none over 23" sits inside that band.

**Discourse moves.** An Opus annotator labelled every sentence of 27 unlabelled passages. Share of sentences:

| move | humans | ours | AI controls |
|---|---|---|---|
| plain fact | 23% | 38% | 42% |
| attribution ("X says") | 6% | 15% | 13% |
| comparison | 7% | 14% | 20% |
| reaction (the speaker's feeling) | 14% | 3% | 4% |
| pointing at the screen | 23% | 1% | 0% |
| joke, irony, playful aside | 17% | 4% | 4% |
| aside, tangent, self-correction | 5% | 1% | 6% |
| texture (1 clean statements .. 5 loose talk) | 3.6 | 1.7 | 2.0 |
| presence (1 nobody .. 5 a distinct person) | 3.7 | 2.5 | 2.0 |

## 4. The blind tests (`tools/script/blind_test.py`)

**The set-up:**
- Passages of ~170-190 words, with numbers and punctuation normalised the same way for every source, shuffled, no labels.
- Fresh judges with no tools (Opus and Sonnet).
- Humans in every packet sit at 0.10-0.21.

| test | what | P(AI) of ours | humans |
|---|---|---|---|
| pilot1 | five of our scripts as they went out | 0.85 (Script A), 0.80, 0.78, 0.59 (Script B), 0.32 (an argument video, mostly the creator's own takes) | 0.11 |
| pilot1 | AI controls: an agent writing Script A's facts plainly / "like a relatable human YouTuber" | 0.85 / 0.80 | |
| r1 | Script A rewritten looser: longer sentences, fillers | 0.82 | 0.17 |
| r2 | + pointing at the screen, reactions | 0.75 | 0.20 |
| r3 | as a cleaned transcript of someone talking | 0.70 | 0.17 |
| r4 | documentary voice, idioms, fewer definitions | 0.72 | 0.15 |
| r5 | a design-explainer channel's style: show your work, the term after the explanation | 0.79 | 0.21 |
| r6, r7 | the creator's own idiolect (their usual fillers and hedges) | 0.77, 0.74 | 0.16, 0.19 |
| cal1 | **the creator's own interview answers, lightly cleaned** | **0.27, called AI 0%** | 0.21 |
| diag1 | **human passages paraphrased by the chat: their content and order, the chat's words** | **0.44, 2 of 3 judged human** | 0.14 |
| r8 | a "reason out loud" structure | 0.73 | 0.14 |

**What the judges named on ours, every round:**
- a definition tacked onto every term ("a trick called X. X does Y", "which is called X")
- an appositive on every name ("Dana Reyes, one of the three people leading the product's development")
- stat ladders (5,000 / 40,000 / 90,000)
- textbook analogies (a cell as a tiny factory)
- "isn't X, it's Y" reveals
- a paragraph that opens on a framing line and closes on a tidy summary or a clipped one-liner ("Which isn't exactly a yes.",
  "I get it.")
- casual words, jokes and opinions that feel "bolted on", "planted", "performed"

**The human passages they trusted:**
- real expert jargon left unexplained
- first-person work ("I've got the original version running in this window")
- reasoning out loud with a stake ("So what would fix it? Well, more competition, probably")
- quotes from real people
- wit about specifics
- digressions
- the creator's own rambling, hedged answers

**Later rounds** use single-passage packets: one of ours among seven humans, so the judge can't match "the same author four times".
That changed nothing: r3 0.68, r10 0.77, the original Script A 0.81 on their own.

| test | what | P(AI) of ours | humans |
|---|---|---|---|
| r9 | human paragraph skeletons (the move orders of a technical-analysis channel, a scripted voice-over channel in the niche, and LTT), our words | 0.79 | 0.15 |
| r10 | built on specific shots of our own footage catalogue and our own file measurements | 0.76 | 0.15 |
| r11 | argument framing on the niche's debates, with the creator's documented takes | 0.72 | 0.18 |
| r12 | original contributions: our own file measurement, a reasoned guess at a date, the creator's buying advice on a new device | 0.72 | 0.18 |
| ab | **a real LTT passage (0.15) rewritten only in our house style (short tidy declaratives, symmetric pairs, "there is some good news, though")** | **0.66** | |
| ab | r12's measurement paragraph: as is 0.82; de-staged 0.82; with a digression 0.75; **with spoken disfluency ("uh", "I was like wait", run-ons) 0.60** | | |
| hc | **real human passages cleaned of transcription errors only:** a comedic explainer 0.08, a personality news channel in the niche 0.14, **two scripted voice-over channels in the niche 0.47 and 0.62** | | |

**Two results that change the target:**
1. **Our house style is itself the AI signature.** The same human content flips from 0.15 to 0.66 when it's written our way.
2. **The judges can't separate clean scripted human narration in the niche from AI either.** Cleaned of mishearings, the two scripted
   voice-over channels score 0.47 and 0.62. The humans that score 0.1-0.2 are personalities talking, comedians (a comedic explainer,
   Internet Historian) or experts riffing (a technical-analysis channel, LTT). So the fair bar for a scripted narration looked like
   about 0.5, and our scripts as they went out sat at 0.7-0.85. *(§8.1's audit corrects this bar to about 0.4.)*

| test | what | P(AI) of ours | humans |
|---|---|---|---|
| r13 | written in the creator's dictation register (run-ons and their usual fillers) | 0.68 | 0.17 |
| hy | **a section of Script A made of the creator's own interview answers (cleaned of restarts), with a few fact lines added** | **0.50 (one passage judged human)** | 0.10 |
| r14 | a fresh descriptive section (three paragraphs on an old house: the light, the garden, the locks) with everything combined: no tidy units, the measured lingo, "the <thing>" instead of the full name | 0.66; **the locks paragraph judged human (0.45)** | 0.12 |

**r14's lessons:**
- **The paragraph that passed** opens on a plain statement ("We haven't seen that much of the locks yet."), chains what's known
  loosely ("and then older locks you open with a hairpin"), points at the clip, and ends on a reasoned guess.
- **Flagged in the others:** a "the old version ... the new one ..." frame, list-item openers ("The garden is a whole thing too"),
  a closing aphorism.
- **Cleaning the creator's words can make them AI.** A loose spoken sentence tidied into a compact aphorism was flagged (the pattern:
  "and that's good, because that's why people care" becoming "Scarcity is why people care."). Clean only the restarts and slips; keep
  the speaker's order and connectors.

| test | what | P(AI) of ours | humans |
|---|---|---|---|
| r15 | r14's flagged paragraphs again, with r14's lessons; the creator's answer on one topic kept in their order | **0.52**: the creator's paragraph judged human (0.12), garden 0.60, light 0.85 | 0.12 |

**The descriptive section, best of r14 and r15: mean 0.50, with two of four paragraphs judged human** (Sonnet, one judge each). That
is at the gate.

What still fails is a paragraph that is only a list of features stated as fact, with nobody in it. The judge on r15's light
paragraph: "an even run-on of tidy concrete details presented as fact". **Every paragraph needs a person in it:** the viewer doing
something, the narrator pointing at the clip, or the creator's take.

| test | what | P(AI) of ours | humans |
|---|---|---|---|
| r16 | the light paragraph two ways (the viewer in it; pointing at the windows) | 0.72-0.74 ("tidy and-chained details", triplets) | 0.11 |
| t1 | **transfer: a fresh Opus agent, given only the standard's section and a fact list, writes a descriptive section** | **0.68** | 0.11 |
| t2 | transfer again, with the fixed rhythm item | **0.63, one of four judged human** | 0.13 |
| t3 | transfer with two more standard items added | **0.73** (worse): plain short declaratives, a worked example, restating | 0.18 |

**t2's flags:**
- a technical term explained mid-sentence (glossed inline)
- a set listed as a tidy run (the old house's clocks). The house rule wants the whole set named, so it needs a looser form: some
  named while pointing at them, "and a few more".
- comma-chained clauses

**The lesson from t1-t3: every rule added to the brief pushes the writer into a new uniform habit** (t1 run-ons, t3 short
declaratives).
- Writer-to-writer variance is about 0.05-0.1, and single-judge noise is about the same.
- So: give the writer worked examples (the paragraphs that passed: r14's locks, r15's answer, the paraphrases of real passages)
  instead of more rules, and judge each passage twice.
- The written method works partly (0.68 against our old 0.80) and over-teaches one thing: "long loose sentences" made every sentence
  a comma-chained run-on, a new uniform style. So the standard asks for a mix of sentence shapes.
- Pure description (the light) is the hardest kind of paragraph. What passes has a mind at work in it: a guess with its reason, an
  unknown.

**Where it stood after these rounds:**
- The method in `standard/SCRIPTS_AND_PACKAGING.md` ("Scripts that read human") takes our scripts from 0.80 to 0.60-0.68 when the
  chat writes alone. That is better than every script that went out, but still above the bar (~0.5).
- Only the creator's own words pass outright (0.12-0.27), and the creator's words with our facts land on the bar (0.50).
- Hence: drop the house style (measured), and gate on the blind test.

**What that means:** the words are not the main giveaway (diag1). The giveaway is what the narrator does, paragraph by paragraph.
- **We** present information in tidy self-contained units: frame, fact, definition, comparison, summary, closer.
- **Humans** think out loud inside a story or an argument, and don't close every unit.
- Changing the wording, the rhythm or the tone of a catalogue of facts doesn't move the judges (r1-r8 all 0.70-0.82).

## 5. More rounds: what transfers, and the stricter judge

**The set-up for every round below:**
- One passage of ours per packet, among 7 cleaned human passages (`--split`).
- Two pools of human passages from different creators: scripted explainers, documentaries, personality talkers, and scripted
  voice-over in the niche.
- Sonnet judges unless said.

| round | what | P(AI) | judged human |
|---|---|---|---|
| t4 | transfer (a fresh Opus writer): the standard + worked examples that passed | 0.69 / 0.73 | 1 of 8 |
| t5 | transfer: + "write over the footage" and a shot list | 0.72 / 0.73 ("screenshot-caption narration") | 0 of 8 |
| t6 | transfer: + "every paragraph turns on a guess" | 0.64 / 0.70 (the taught "question, then 'Well,'" flagged as a device) | 1 of 8 |
| **t6r** | **t6 revised once by a fresh writer from the judges' tells (the loop)** | **0.64 / 0.49 = 0.565** | 1 of 8 |
| r17 | the chat's own, same brief, the guess move, one quote of the creator's | 0.57 / 0.62 = 0.60 | 1 of 8 |
| r18 | the chat's own, each paragraph on a real paragraph's skeleton (three human creators) | 0.59 / 0.70 | 1 of 8 |
| r19 | r17's two attribution-heavy paragraphs without the "X said" | 0.73 (r17's same two 0.70): "page by page, line by line" unattributed reads as our flourish | 0 of 8 |
| r21 | r17 + one joke a paragraph about what the footage shows | 0.66 (r17's same three 0.66): "punchline closer" | 1 of 12 |
| **r20** | **a story section, the chat's own, with two of the creator's interview answers in** | **0.55 / 0.48 = 0.515: passes Sonnet's gate** | 4 of 10 |
| Short | a finished Short of ours as it went out, among human Shorts in the niche | 0.88 | 0 |
| r22, r23 | that Short rewritten (spoken; then built on a reason instead of a timeline) | 0.83, 0.79 | 0 |

**Human Shorts in the niche** scored 0.03, 0.09-0.21, 0.21 and 0.35-0.56. The last is a scripted Shorts channel, the closest to ours,
and it still reads more human: it argues one theory with "might ... because", where ours is a dated timeline with a callback closer.

**The Opus proof round (o1-o2):** r17 0.70, r20 0.67, t6r 0.71, none judged human. Opus is the sharper judge. Across every round in
this study (both judges on the same passages):

| | Sonnet | Opus |
|---|---|---|
| real creators (LTT, Internet Historian, Nexpo, LEMMiNO, and design, technical-analysis, personality and voice-over channels) | 0.05-0.23 | 0.10-0.26 |
| clean scripted human narration (a voice-over channel in the niche) | 0.51 | 0.43 |
| the creator's own interview answers, cleaned | 0.12 | 0.42 |
| the chat's paraphrases of human passages | 0.50 | 0.38 |
| an argument video of ours, mostly the creator's takes | 0.20 | 0.44 |
| Script B (the well-performing one) as it went out | 0.64 | 0.64 |
| Script A as it went out | 0.82 | 0.81 |
| the chat's best new sections (r17, r20) and the loop-revised transfer (t6r) | 0.52-0.60 | 0.67-0.71 |

**What Opus names on ours, almost every time, is compression:**
- "Every sentence a tidy, compressed fact with no filler or hesitation"
- "no real stumbles"
- "no voice or asides"
- casual words that "feel inserted for voice"

It even flags one of the creator's own lines inside r20, because the chat's compact sentences around it set the paragraph's feel.

**Lessons of these rounds:**
1. **Paragraph type decides more than wording.**
   - Paragraphs carrying the creator's words: 0.2-0.45 (Sonnet).
   - Fact-only paragraphs: 0.55-0.8 whatever the style. Eight styles were tried (examples, footage-first, guesses, skeletons,
     de-attribution, jokes), and all landed there.
2. **Fact density is not the tell; personality is.** Fact-dense human passages score like any other human passage (0.16). They carry
   a joke that grew out of the content, a stance, a personal note.
3. **Every device written into a brief becomes the next tell:**
   - t3: short declaratives
   - t5: "screenshot-caption narration"
   - t6: "self-posed question then 'Well,'"
   - r21: "punchline closer"

   So the written method should name what to avoid and why, and leave the moves to the writer.
4. **The loop is what transfers.** One revision from the judges' tells took a fresh writer from 0.67 to 0.565 (Sonnet). Opus still
   called the revision AI (0.71).
5. **Calibration caveat.** A scripted voice-over channel's low scores came partly from its captions' transcription errors (misheard
   names). Another's clean captions (Sonnet 0.51, Opus 0.43) are the honest anchor for clean scripted narration.
6. **Shorts are the hardest format.** A timeline Short scores 0.8-0.9 whatever the wording; human scripted Shorts argue one point.

**After the Opus round (o3-o7):** five more ways to write the descriptive section, judged by Opus (and by Sonnet where shown).

| round | what | Opus | Sonnet |
|---|---|---|---|
| r24 | the chat's own, talked rather than compressed (restating, small asides, "okay so", a point said twice) | 0.69 | **0.46, 2 of 4 human** |
| r25 | r24 with the precision moved on screen (a source caveat as the caption, roles on name cards) | 0.66 | - |
| r26 | the chat's own, written the way the creator talks (from their interview answers) | 0.67 | - |
| **t7** | **a fresh Opus writer: study the creator's interview answers, write it the way they'd talk it over the clips, clean it like their answers** | **0.65** | **0.48, 2 of 4 human (first draft)** |
| t8 | the same brief, a Fable writer | 0.68 | 0.53, 2 of 4 human |

Opus names "staged casualness", "evenly sprinkled fillers" and "pre-explains for a blank viewer". The creator repeats content words
twice as often as the chat does, but repetition doesn't separate the corpus (creators' median 23.9 per 450 words; our old scripts
22-34), so it stays out of the lint.

**Where it stood after these rounds:**
- **Sonnet's gate is met on first drafts.** The descriptive section written the way the creator talks passes (t7 0.48, by a fresh
  writer, so the method transfers), as do talked rather than compressed (r24 0.46) and the story section with the creator's answers in
  (r20 0.515).
- **Opus is not met.**
  - Fourteen ways of writing and three writer models (Opus, Sonnet, Fable) all land at 0.65-0.71.
  - For comparison: Script B 0.64; the creator's own words 0.42; the chat's paraphrases of real creators' passages 0.38; the clean
    scripted voice-over 0.43.
  - What has gone under 0.45 is always a thought sequence a human had; how the chat words its own sequence doesn't move it.
  - Readers who use LLMs a lot detect AI text about as well as Opus (Russell et al. 2025, §8.2), so this gap is real, not a quirk of
    the judge.
- **Shorts:** a timeline Short fails under both judges (0.79-0.88). **A Short built on the creator's take passes both** (r27: the
  creator's answer on a new device's price, with two price facts woven in: Sonnet 0.08, Opus 0.32, all four judgments human; the
  human Shorts beside it 0.30-0.35).
- The lever left is more of the creator's own thinking per script, which is the creator's call.

## 6. What the strict judge reads

**The dissection (x1, Opus, two judges each).** Two of the chat's paraphrases that Opus believed (a design explainer's memory trick,
and LTT's passage on a new device's price), each in four versions:

| version | design explainer | LTT |
|---|---|---|
| as is: the human's thought sequence in the chat's words | **0.41, human** | **0.27, human** |
| tidied: the same sentences in a neat order | 0.41, human | 0.59, AI |
| voice stripped: no "I", no own work, no asides, no questions | 0.60, AI | 0.73, AI |
| the chat's own: only the facts, written its way | 0.71, AI | 0.61, AI |

**What it called human, in its words:**
- "first-person hands-on claim 'I grabbed the original source code, rewrote a few parts'" (strip it, and the passage reads AI)
- "'Now: I should point out...' self-correcting aside"
- "hedged spoken reasoning 'Well, more competition, probably. I mean, if ...'"
- "hedged personal take 'it looks to me like'"

Tidying LTT's reasoning into conclusions ("What would fix the pricing is more competition") turned it AI.

**So the strict judge reads two things:**
1. Real first-person work: the narrator did something and says so.
2. A genuinely open question worked out loud: a tentative answer, "I mean, if ...", a turn. Not settled facts presented.

For a channel that really does the work (looks at every shot, pauses frames, reads the small print, measures files), both are
honest.

**r28** is the descriptive section built that way, with own work done for it:
- the old house's clocks read frame by frame across three scenes of the source's video: which ones run, which stop, and one change
  nobody has explained, so the script says so and guesses
- a close-up of a prop read for its small text
- one kind of shot counted in our shot list of the whole source video

| round | what | Opus | Sonnet |
|---|---|---|---|
| r28 | the section with own work (the clocks frame by frame, the prop read, one kind of shot counted) and open questions | 0.69 | - |
| o9 | r28, t7, r24 and r17 cut into 170-word windows across paragraphs, the way the human passages are cut | 0.62-0.70 | - |
| proto | a prototype minute (the clocks, the chat's own work, told scene by scene in the source's order) | 0.64 / 0.65 | 0.60 / 0.65 |
| proto2 | the minute as discovery (the unexplained change first, then back through the scene) | 0.65 / 0.65 | 0.68 |
| proto3 | the minute on the creator's interview answer about a technical choice (a battery size), with the chat's question and a technical outlet's test result in front | 0.60 / 0.55 | **0.08, human** |
| proto4 | the chat's fact lines first (our own check of the maker's files, the outlet's test), then the creator's answer | 0.62 / 0.68 | 0.60 |

**What these rounds showed:**
- **Windowing ours like theirs changes nothing** (0.62-0.70): the paragraph shape was not the confound.
- **The written test is a fair stand-in for the heard script.** Captioning a cloned voice's read of a script with Whisper gives back
  the script almost word for word: the clone speaks too cleanly for caption errors.
- **Off limits:** a test writer asked to write a made-up raw voice-to-text "recording" of the creator was stopped by a safety check.
  Inventing a real person's recorded speech is fabricating their words, so it is never tried in any form. The creator's real
  interview answers are the only words of theirs that go in.
- **Own work told in the subject's order reads as an inventory** ("tidy sequential beats", "staged hedge"). The design explainer tells
  his own work in the order he did it ("I grabbed the source code, rewrote it, now you can watch").
- **Facts in front of a view sink it.** On proto3, Opus read the loose opinion talk (the creator's words) as human and flagged the
  chat's opening question and the stat. On proto4, the chat's fact lines in front made it call even the creator's answer a "staged
  rambling-opinion section". In r27 (Opus 0.32), the facts sat inside the creator's own sentences, never as the chat's lines around
  them.
- So no prototype went out yet: every minute with the chat's own lines in it failed both judges.

**Where it stood:** Sonnet's gate is met by the chat's writing (0.46-0.515). Opus, the target, is not, after more than twenty
approaches. What passes Opus is a human's thinking:
- the creator's answers, with the facts woven into their own sentences (0.32)
- real creators' thought sequences in the chat's words (0.27-0.41)

**The next steps tried, inside the same procedure:**
1. Choose the 3-6 interview spots so the creator's answers cover the fact-heavy sections, with the facts woven into their sentences
   (r27's way).
2. Build the rest from real viewers' own questions in the order they asked them (comments under the source videos): a human thought
   sequence the channel can use honestly.
3. The loop with Opus as the critic, several rounds per paragraph, to see if it converges.

| round | what | Opus | Sonnet |
|---|---|---|---|
| r29 | a paragraph built on a real viewer's question (a comment under a breakdown video), with what the chat checked in the footage: three details that answer it, one of them against the maker's own word | 0.65 / 0.68 | 0.58 / 0.58 |

The viewer's thought sequence doesn't carry through the chat's telling of it ("staged human framing", "tidy 'maybe X, maybe Y, I
don't know' hedge triplet").

**The rule the numbers give** (written into the standard): under Opus, a passage reads human in proportion to the share of it that is
a real person's own thinking. Inside the procedure, that means:
- choosing the interview spots where the creator's answers can carry the facts
- the facts inside their sentences
- real people in their own clips
- the chat's own lines few and short

| round | what | Opus | Sonnet |
|---|---|---|---|
| proto5 | the prototype minute built that way: the creator's interview answer carrying the minute, the technical outlet's test inside their sentences | **0.45 / 0.45, both human** | **0.07 / 0.07, both human** |

**The prototype** (62.6 s on the source's own clips, the creator's voice clone, -14.1 LUFS) passed the creator's review, and the
method became the way to write the next videos.

## 7. An argument video: the chat's own lines must pass by themselves

**The case:** an argument video of ours (why not to wait for a book's paperback).
- Drafts 1-4 went from Sonnet 0.76 to 0.66 on the body, with Opus at 0.70 and 0 of 5 judged human, after three rounds of the loop.
- Every judge names the argument's shape: "tidy point-by-point argument", "concede-then-reject", "stacked sourced examples".

**Test (ia/ib):** two flagged passages (one on spoilers, one on a workaround) were rewritten to reason toward the point, the
difference the dissection found in LTT's passage (§6):
- one concrete example told as a small story
- the takeaway arriving last
- no stacking, no concede-then-reject

| passage | Sonnet | Opus |
|---|---|---|
| spoilers, inductive | 0.70 / 0.68 | 0.72 |
| the workaround, inductive | 0.70 / 0.78 | 0.72 |

No gain: "tidy anecdote-to-thesis arc", "polished closing antithesis", "tidy rebuttal structure". That made twenty-six approaches of
the chat's own writing:
- Opus scored 0.62-0.72 every time.
- Sonnet passes came only on descriptive or explanatory sections written talked (r24 0.46) or in the creator's manner (t7 0.48),
  never on an argument section.

**The untried options, cheapest first:**
1. **Selection, not revision.** Write 6-8 genuinely different drafts of each flagged paragraph (different openings and orders, one
   example or none, with and without the source named), give each one Sonnet judge, keep the lowest, and confirm it with two more
   judges. Judges vary by about ±0.1, so a single low score can be luck. Revision rounds plateau because each rewrite keeps the same
   plan.
2. **The sources speak, not "X says".** Where the evidence is someone's words (a technical outlet, a forum post, a commenter), their
   own clip or screenshot carries it on screen and the voice only reacts. Fewer of the judged words are then the chat's.
3. **An argument told as one case.** Follow one buyer's situation through (a real commenter's, quoted as the screen shows it) instead
   of a list of reasons; the reasons come up as they hit that person.

**Selection, tested (sel1).** Six genuinely different drafts of the spoiler passage, from four writers and plans:
- the chat: one case, plain
- Opus: one case, talking a friend out of it
- Fable and Sonnet: their own plans

One Sonnet judge each gave 0.60, 0.60, 0.62, 0.64, 0.70 and 0.74, all called AI ("tidy antithesis", "stacked examples", "staged
YouTuber voice ('Bro,' 'man')", "punchy fragments"). Different writers and plans land in the same band, so picking the lowest of N
doesn't reach 0.55 on an argument passage either.

**The bar the study works to:** a fresh chat's own lines pass, without the creator writing them. It was not reached here. What has
passed so far is always a human's sequence of thoughts: the creator's answers, or real creators' passages retold. One untested way
remained to bring a human sequence in honestly without the creator: follow a real person's own reasoning (a long viewer post or
comment, a creator's argument), credited on screen, retold in our words in its order.

**Credited retelling of a real person's argument (fa).** A long comment under a breakdown video (a viewer underwhelmed by an announcement),
retold in the chat's words in the commenter's order and credited ("one guy ... says"):
- Sonnet 0.68 / 0.85, Opus 0.65 ("a repeated 'X says' reported-opinion structure").
- Retold reasoning passed only when written as the narrator's own (§6), which is not honest for someone else's opinions.
- So no honest way has been found to bring a human's sequence of thoughts into an argument section without the creator. After
  thirty-odd approaches of the chat's own writing, Opus sits at 0.62-0.72, and Sonnet passes only descriptive sections.

## 8. Round 2: the judges audited, the research back-checked, sixteen more methods, the gate proof

*The aim: a method that, 10 times out of 10, writes sections that score far better with the blind judges, is backed by research, and
needs no approvals from the creator. The test material: ten sections (T01-T10, 113-183 words each) of one of our long scripts as it
shipped. Every packet, key and verdict stays in the media root (`MEDIA/script/panel/`: creators' words, never in git). The tools:
`tools/script/judge_panel.py` (the panel and the gate) and `tools/script/tell_lint.py`.*

### 8.1 The judge audit

**The pool:** 65 passages.
- **28 human:**
  - 9 scripted narrations from before ChatGPT existed (2016-2019): LEMMiNO, Internet Historian, Business Casual, Half as
    Interesting, and history, design and comedy explainers
  - 8 personality creators talking
  - 7 scripted voice-over passages from channels in the niche
  - 4 recent documentaries: a journalist, John Coogan, Alex Webb, and a top creator in the niche
- **20 known-AI controls:** the same ten sections written from the fact list by a Sonnet agent and by GPT-5.6 Terra, each with a
  plain "engaging, conversational YouTube narration" brief.
- **10** of our shipped script, **3** of our old uploads, and **4** "faceless" channels (unknown authorship).

**The packets and judges:**
- Packets of 13, every passage judged twice (rep 2 in a new order and new company).
- Judges: Opus and Sonnet (agents); GPT-5.6 Terra and GPT-5.6 Luna (Codex CLI, in an empty folder with no project context).

Mean P(AI) / AUC against all humans (0.5 = can't tell):

| kind | Sonnet | Opus | Opus, clean context | GPT-5.6 Terra | GPT-5.6 Luna |
|---|---|---|---|---|---|
| human, scripted before 2022 | 0.10 / 0.48 | 0.17 / 0.48 | 0.19 / 0.44 | 0.21 / 0.39 | 0.30 / 0.46 |
| human, talking | 0.09 / 0.32 | 0.15 / 0.34 | 0.17 / 0.37 | 0.24 / 0.39 | 0.31 / 0.46 |
| human, scripted voice-over in the niche | 0.22 / 0.72 | 0.32 / 0.75 | 0.36 / 0.77 | 0.49 / 0.74 | 0.32 / 0.58 |
| human, documentary | 0.10 / 0.52 | 0.16 / 0.43 | 0.17 / 0.43 | 0.27 / 0.55 | 0.20 / 0.56 |
| **AI controls (Sonnet-written)** | 0.81 / **1.00** | 0.81 / **1.00** | 0.80 / **1.00** | 0.79 / 0.89 | 0.62 / 0.72 |
| **AI controls (GPT-written)** | 0.80 / **1.00** | 0.77 / **1.00** | 0.76 / **1.00** | 0.77 / 0.89 | 0.62 / 0.72 |
| our shipped script | 0.73 / 0.99 | 0.72 / 1.00 | 0.70 / 1.00 | 0.58 / 0.81 | 0.38 / 0.59 |
| faceless channels (unknown) | 0.30 | 0.35 | 0.37 | **0.79** | 0.75 |

**What the audit settles:**
1. **Stable.** The same passage, the same judge, another packet: r = 0.87, verdict flipped 8%, mean difference 0.09 (Opus alone in
   the gate format: r = 0.96).
2. **Valid.** Every Claude judge separates the known-AI controls from all 28 humans perfectly (AUC 1.00), and does NOT call scripted
   human writing AI: pre-2022 scripts typed by their creators (a history channel's chronicle, two scripted explainers) score
   0.05-0.24.
   - **So the judge is not punishing "scripted narration".**
   - §4's anchor (two scripted voice-over channels at 0.47 and 0.62 as the bar) came from single-judge runs. Decluttered, the first
     scores 0.17-0.24 here. The niche's voice-over group averages 0.32-0.42; the second channel alone sits at ~0.6.
3. **Opus and Sonnet are one judge, not two** (r = 0.93-0.98 over passages). "Two judges, two bars" was the same reading twice; a
   second opinion needs another model family.
4. **Project context barely matters.**
   - Agents of the general type carry CLAUDE.md and the memory (they know the repo makes AI-written scripts); Explore-type agents
     carry neither (checked by asking both).
   - Clean Opus against primed Opus on the same packets: r = 0.98, with the primed one ~0.05 stricter on ours.
   - So the earlier gates were not an artefact of priming.
5. **The company a passage keeps moves its score.**
   - Two versions of one section in a packet get spotted ("a parallel rewrite of P9").
   - The same ten g3 passages scored 0.55 among other methods (r3) and 0.74 among their own sibling versions (r4).
   - The fix, in the tool: never two versions of a section in a packet, and the gate puts each passage alone among 7 humans (as
     `blind_test.py --split` does).
6. **GPT-5.6 Terra is a different judge** (r = 0.5-0.7 with Claude).
   - It catches generic AI (AUC 0.89) but goes easy on our house style (our shipped script 0.41-0.61).
   - It calls the faceless channels AI where Claude calls them human.
   - It is unstable when a packet holds mostly AI: its human scores jumped to 0.88-0.94 in two such rounds.
   - Luna is too weak (AUC 0.72 on known AI).
   - The GPT account hit its usage limit, so the final proof is Claude-only, and the cross-family check is still open.
7. **What the judges call human, in their words** (Opus on the 28):
   - "first-person research trail ('I searched nearly 200GB')"
   - "so I reached out to him"
   - "personal jokes", "sarcastic asides"
   - "self-interrupting gag 'Wait, that's the actual title?'"
   - "tangled spoken syntax", "translated/awkward phrasing", "non-native phrasing"
   - "stock YouTuber clichés ('did not disappoint')"
   - "personal 'I grew up with guys like this'"

   A person with quirks and a stake is in every one.

### 8.2 The research back-check (A primary or peer-reviewed, B preprint or reputable, C blog or vendor)

**Detectors and their limits:**
- DetectGPT (Mitchell et al., ICML 2023, A), Fast-DetectGPT (Bao et al., ICLR 2024, A), Ghostbuster (Verma et al., NAACL 2024, A).
- Binoculars (Hans et al., ICML 2024, A): over 90% of ChatGPT text caught at 0.01% false positives.
- RAID (Dugan et al., ACL 2024, A): 12 detectors and 6M texts; simple attacks cut accuracy by up to 32-76 points.
- DIPPER paraphrasing (Krishna et al., NeurIPS 2023, A): DetectGPT falls from 70.3% to 4.6%.
- Sadasivan et al. (TMLR, v4 2025-01, A): recursive paraphrasing evades detectors; the ceiling is how far apart the two text
  distributions are.
- Liang et al. (Patterns, 2023-07, A): perplexity detectors flag plain non-native writing as AI.
- GPTZero says it stopped deciding by perplexity and burstiness in autumn 2023 (C).

**Humans and LLMs as judges:**
- Russell, Karpinska, Iyyer (ACL 2025, A): five heavy LLM users, by majority vote, got 299 of 300 right, paraphrased and "humanized"
  text included. Non-experts were near chance; prompted GPT-4o got 78%.
  - The experts' clues: vocabulary, lists of three, overly clean grammar, blandness, quotes, over-explaining, formulaic conclusions.
- Clark et al. (ACL 2021, A): untrained people at chance on GPT-3.
- Jakesch et al. (PNAS 2023, A): lay heuristics (first person, contractions, family) can be exploited, so surface markers fool lay
  readers, not experts.
- Bhattacharjee and Liu (SIGKDD Explorations 2023, A): each judge model leans its own way.
- Panickssery et al. (NeurIPS 2024, A): models recognise their own text. Davidson et al. (EMNLP Findings 2024, A): not in general.

**What differs:**
- Reinhart et al. (PNAS 122, 2025, A): GPT-4o uses about 5.3x the present-participle clauses, 2.1x the nominalizations and 1.9x the
  phrasal coordination of human text. Instruction-tuned models sit further from human style than base models, and grammar features
  alone tell human from one LLM at 93-98%.
- Kobak et al. (Science Advances 2025-07, A): excess style words ("delves" 28x).
- **Sun et al., "Idiosyncrasies in Large Language Models" (ICML 2025, A): a classifier tells five chat models apart at 97.1%, and the
  fingerprint survives rewriting, translation and summarising by another model. Part of it is in what is said, not how.**
- Muñoz-Ortiz et al. (AI Review 2024, A): LLM sentence lengths cluster at 10-30 tokens.
- Herbold et al. (Scientific Reports 2023, A): fewer discourse and stance (hedge, epistemic) markers in LLM essays.
- Padmakumar and He (ICLR 2024, A) and Doshi and Hauser (Science Advances 2024, A): LLM help makes different writers' texts alike.
- Wang et al. (EMNLP Findings 2025, A): given examples, LLMs fail to imitate a person's informal style.
- Biber (1988, A, features checked via secondary sources): the spoken "involved" register is private verbs (think, feel), I and you,
  and contractions. The written "informational" register is nouns, prepositions and long words, and the features LLMs overuse are the
  written ones.

**Practice:**
- Paul Graham, "Write Like You Talk" (2015-10, C).
- NPR radio-writing guides (2025-05, B): short, simple, read aloud.
- Technology Connections reads each script aloud about a dozen times (Cortex ep. 175, 2026-01-15, C).
- MKBHD and Ali Abdaal talk from bullet points (secondary sources only, C).
- Documentary "paper edits" build the script from interview transcripts (C).

**Humanizers:**
- Perkins et al. (IJETHE 2024, A): detector accuracy fell from 39.5% to 17.4% after simple edits.
- But trained detectors and expert readers still catch humanized text (Russell et al.; Masrour et al., "DAMAGE", 2025-01, B).

**Viewers and the platform:**
- YouTube demonetizes "inauthentic", templated mass content, not AI help with scripts (YouTube Help, policy update 2025-07-15, A),
  and AI-written scripts need no disclosure (A).
- Pew (2025-09-17, A): 76% say telling AI from human work matters, and 53% aren't confident they can.
- No peer-reviewed study of viewers and AI-written narration was found.

**What it means for us:** the judges we use behave like Russell's expert readers (AUC 1.00 on known AI). So surface tricks are not on
the table, and they wouldn't fool the viewers who matter either. The literature's one durable difference is content: a person's own
stance and selection.
- Sun et al.: the fingerprint survives rewording.
- Herbold: fewer stance markers.
- Doshi and Hauser: sameness.

That is what §6 measured, and what §8.3 measures again.

### 8.3 The experiments (Opus, mean P(AI) over the ten sections; human passages beside them 0.15-0.20, the niche's scripted voice-over 0.3-0.4)

| round | method (each wrote all ten sections from the same facts and rules) | Opus | GPT-5.6 Terra |
|---|---|---|---|
| audit | our shipped script | 0.72 | 0.58 |
| audit | plain AI controls, Sonnet / GPT | 0.81 / 0.77 | 0.79 / 0.77 |
| r1 | m2: written after studying eight human scripts the judges believed (attitude, one thing a sentence, odd details) | 0.76 | 0.65 |
| r1 | m3: the same brief, GPT-5.6 Terra writing | 0.78 | 0.74 |
| r1 | m4: the shipped script with the grammar moved to the spoken register (Reinhart's features: finite verbs, no participles or nominalizations, fewer glosses) | 0.68 | 0.43 |
| r1 | (anchor) the shipped script | 0.68 | 0.44 |
| - | m1: talk it off the cuff with fillers, then clean it like a caption: **stopped by a safety check** (a simulated raw recording; as in §6, never tried again) | - | - |
| r2 | a: the sources speak (real posts and statements quoted, "I went back to the thread") | 0.76 | 0.46 |
| r2 | b: the shipped script de-polished (YouTuber idioms, a clumsy run-on, a dry aside, fewer glosses) | 0.69 | 0.27 |
| r2 | c: a random plan per section drawn by a script (the opener, the fact that gets room, a dropped fact, sentence lengths taken from a real human passage) | 0.73 | 0.49 |
| r2 | (anchor) the shipped script | 0.73 | 0.44 |
| r3 | g2: GPT-5.6 Luna writing | 0.77 | 0.67 |
| r3 | **g3: composed in another language, spoken, as a young native YouTuber of the niche, then translated literally into English by GPT** | **0.55** | 0.55 |
| r3 | g5: the creator's real interview takes run through four sections (our words) | 0.65 | 0.46 |
| r3 | (anchor) the shipped script | 0.70 | 0.57 |
| r4 | g3 literal / g3b lean draft in the other language / g3c correct non-native English / g3f fluent native translation (all four g3 kinds in one set of packets) | 0.74 / 0.69 / 0.76 / 0.72 | 0.45 / 0.32 / 0.46 / 0.43 |
| r5 | (4 test passages a packet) the shipped script / g3 / g3f / k: the persona writing English directly | 0.72 / 0.65 / 0.72 / 0.75 | 0.61 / 0.70 / 0.64 / 0.63 |
| r6 | (3 a packet) the shipped script / g3 / **x1: a lean draft in the other language (4-5 facts, precision on screen, no glosses, no date opener, no wrap-up) + the creator's takes on four sections, GPT translation** | 0.67 / 0.60 / 0.60 | - |

**The gate proof**, in the production format:
- each section alone in a packet among 7 calibration humans
- a clean Opus judge (an Explore agent)
- pass = 0.47 or under
- the humans in the same packets: pre-2022 scripts 0.23, talking 0.21, documentary 0.19, the niche's scripted voice-over 0.42

| section | the creator's view in it? | the shipped script | x3 (x1's method, Claude only: the flagged five rethought from their tells, Claude translation) | x1 (GPT translation) |
|---|---|---|---|---|
| T01 | no | 0.55 | 0.60 | **0.45** |
| T02 | yes | 0.60 | **0.43** | **0.30** |
| T03 | yes | 0.55 | **0.35** | **0.20** |
| T04 | no | 0.60 | 0.60 | 0.65 |
| T05 | yes | 0.65 | **0.45** | 0.55 |
| T06 | no | 0.62 | 0.55 | 0.65 |
| T07 | yes | 0.64 | **0.40** | **0.30** |
| T08 | no | 0.60 | 0.65 | **0.40** |
| T09 | no | 0.65 | 0.60 | 0.55 |
| T10 | no | 0.68 | 0.60 | 0.62 |
| **mean / passed** | | **0.61 / 0 of 10** | **0.52 / 4 of 10** | **0.47 / 5 of 10** |
| sections with the creator's view / fact-only sections | | 0.61 / 0.62 | **0.41** / 0.60 | **0.34** / 0.55 |

**The tell lint** (`tell_lint.py --validate`, run on all 287 judged passages of ours) is a screen for the named giveaways, not a pass:
- flag count against the Claude judges' P(AI): r = 0.30
- passages with no flag: 0.53 (n = 13); with one or more: 0.67-0.72
- passages with first person or a stance in them: 0.58 (n = 27); without: 0.70

### 8.4 What it proves

1. **The lever is a real person's view, again.**
   - Where the creator's interview answer runs through a section, both versions pass: 7 of 8 judgments at 0.20-0.45, at or under the
     niche's scripted voice-over humans' 0.42.
   - On fact-only sections nothing written moves the clean judge much: the shipped script 0.62, the best method 0.55-0.60. That holds
     across sixteen more methods this round, about forty-six with §5-§7.
   - Composing via another language, the strongest new idea in mixed packets (0.55 in r3), is worth about 0.02 on fact-only sections
     in the gate format (x3 0.60 against the shipped script's 0.62). Its literal English isn't channel quality either (stiff turns
     such as "he took the decision to go"), so it is not part of the method.
2. **Why the wall is there** (the research and our numbers agree): the judge reads who chose and ordered the content.
   - A paraphrase keeps a person's choices (Sun et al.; §6's paraphrases 0.27-0.44).
   - A model composing from a fact list makes a model's choices, whatever the wording, register, persona, language, plan or writer
     family (0.55-0.78 here).
3. **10 of 10 is not reached with the chat's lines alone, and the evidence says wording can't get there.** It is reachable the way
   the four sections with the creator's view got there: a view of the creator's on every section (an interview question per section
   of a long video, the interview procedure of `standard/SCRIPTS_AND_PACKAGING.md` carried further). That is the creator's call, and
   the numbers go to them.
4. **The bar, corrected.** The fair target is not §4's 0.47 but the niche's scripted voice-over humans' ~0.4 (the channel that scored
   0.47 there scores ~0.2 here). The gate keeps 0.47 per passage as the pass line and prints the human controls beside every result.

**Still open:**
- a judge from another model family on the final
- whether real people's own words as held interview bites lift fact-only sections in the gate format (only tried in mixed packets:
  round 2's "a", 0.76)
- a listening test (a viewer hears the clone, not the text)

## 9. Round 3: style only, the pair test, and a long script written with it

**Why a style-only test:** §8's gate mixes content with wording, because a first-person view reads human whoever wrote it. But what
the writing has to get right is the lingo, the sentence structure and the natural human way of talking: whoever's views are in it,
the chat still chooses the words and composes the script. So the wording gets its own measure, **the pair test**
(`tools/script/pair_test.py`).

**How it works:**
1. Take ten real passages: five scripted voice-over passages from channels in the niche, three documentary (a journalist, Alex Webb,
   a top creator in the niche) and two personality talkers.
2. Clean them of caption noise only (misheard words, stutters); every other word is kept.
3. Take their content out as neutral points, in order. Views, jokes and first-person remarks become points too, so ours says the same
   things.
4. Our writer writes the same points.
5. A clean judge (an Explore agent: Opus, then Sonnet in a new order) sees the two side by side, same content, in random order, and
   picks the human one with a confidence.

0.50 means the wording can't be told apart.

**Validation:** five pairs of two different human creators on the same content: LTT vs ShortCircuit on a new device's price, three
pairs of creators in the niche on the same stories, and ColdFusion vs another documentary channel on the same old scandal.
- The "first" one was picked 0.60 on average, but unevenly (0.26-0.82).
- The judges call the messier speaker human, so a clean human loses to a messy one too.
- The test's floor for two humans is about 0.5-0.6, not 0.5 on every pair.

| method (each wrote all ten from the same points) | P(human picked) | passed (at or under 0.60) | voice-over pairs C01-C05 |
|---|---|---|---|
| p0: the standard's wording rules (how we wrote) | 0.79 | 0 of 10 | 0.70 |
| p1: poured into a real human passage's sentence skeleton (lengths, first words) | 0.79 | 1 of 10 | 0.70 |
| p2: matched to the register's measured numbers (sentence spread, connectors, openers, contractions) | 0.75 | 0 of 10 | 0.69 |
| **p3: p2 + a separate spoken edit by a fresh agent** (words reused, glue words, run-ons that change direction, a loose phrase, no written constructions) | **0.70** | **2 of 10** | **0.59** |
| **p4: p0 + the spoken edit + the register's numbers** | **0.69** | 1 of 10 | **0.60** |
| p5: p4 + phrases from a bank mined from 100K words of the niche's creators ("to be honest", "when it comes to"...) | 0.74 | 0 of 10 | 0.71 |
| p6: a long script's writer brief (write and edit in one pass) | 0.77 | 0 of 10 | 0.71 |
| p7: p6 + the separate spoken edit (that script's actual pipeline) | 0.74 | 1 of 10 | 0.66 |
| validation: two humans | 0.60 | | |

**Which wording differences predict being caught** (80 pairs, ours minus the human's, against P(human picked); `tell_lint.py --style`
checks them):

| difference in ours | r |
|---|---|
| more content words and fewer glue words | +0.56 |
| fewer "just" | -0.54 |
| more word variety | +0.53 |
| shorter sentences and less spread | -0.45 to -0.49 |
| longer words | +0.42 |
| fewer "you" | -0.40 |
| written constructions ("it's not X, it's Y", pseudo-clefts, "here's", "so that's") | +0.31 |
| fewer "So" openers | -0.31 |

**What the judges name on the human side:**
- run-ons that change direction, and self-corrections
- odd or non-native turns ("if I may say so", "limitation of technical support")
- slang and idioms ("brass tacks", "cuz", "laundry list")
- redundancy ("a small little touch")
- sarcasm

Inserting phrases (p5) reads as inserted ("A adds fillers").

**What it proves:**
- Wording alone moves the judges by about 0.10 (0.79 -> 0.69) with a separate spoken-edit pass.
- Against the niche's scripted voice-over, the edited text sits at the threshold (0.59-0.60, half the pairs passing).
- Against talkers and spontaneous speakers it stays caught (0.77-0.89), because their transcripts carry live-speech slips no script
  has.
- The edit must be its own pass by a fresh agent: writing and editing in one head (p6) gets 0.77.
- The target (at or under 0.60 on 10 of 10) was not reached. The honest bar for a script is the scripted voice-over pairs, where the
  method is at the line.

**A long script written with it** (several hundred beats, over ten thousand words, a feature-length film):
- **How it was written:** four writers by chapter from a few hundred researched facts (all covered once, checked against the coverage files),
  then a lint-fix pass, then the separate spoken edit.
- **The checks:**
  - `script_lint` went from 149 to 108 flags; 81 of them are the known "number with no owner" false positive, and 0 lines were
    shared with older videos after the fixes.
  - `tell_lint.py --style` put it inside the human middle half on most features. "You" was far above it: 56 per 1,000 words against
    6-30.
  - The pair test of its pipeline (p7): 0.74, 1 of 10.
  - The content gate (Opus, 3 sections a packet among 9 humans): 73 sections, mean 0.73, 0 of 73 at or under 0.47, with the humans
    beside them at 0.21.
- It did not pass.

**Still open:** a method that passes against talkers; more validation pairs (the human-vs-human floor is uneven); a GPT judge.

### 9.1 The last round and the stop (the stop rule: two methods in a row not beating the best by 0.03)

**The untried methods, back-checked:**
- **In-context style transfer** with many real passages of the same register. The literature is against it: Wang et al. (EMNLP
  Findings 2025) found LLMs fail to imitate an informal personal style from examples.
- **An editor that closes the measured gaps number by number**, with `tell_lint.py --style --per-para` as its meter.
- **A human passage's rhythm as a template** (already tried as p1: 0.79).
- **Another model family as the editor** (not available).

Both runnable ones went on the pair test, with **p4 judged again in the same packets as the anchor**:

| method | all ten | voice-over C01-C05 | talkers and documentary C06-C10 |
|---|---|---|---|
| p4 (the best, judged again in this round) | 0.79 | 0.73 | 0.85 |
| p8: p4 rewritten after studying 5-8 real passages of its register | 0.77 | 0.69 | 0.85 |
| p9: p4 edited until all eight measured features sat inside the human middle half (10 of 10 paragraphs did) | 0.79 | 0.71 | 0.86 |

**The stop.** Neither beats the anchor by 0.03 (p8 by 0.02, p9 by 0.00). That is two in a row, so the work stopped here.

**What the anchor shows that the earlier table hid: the same p4 text scored 0.69 in its first round and 0.79 in this one.**
- The company a pair keeps and the judge's order move a method by about 0.1. That is the size of every gain this round measured
  across rounds (p0 0.79 -> p4 0.69).
- Compared inside one round, every wording method sits within 0.04 of the others (the first pair-test round: 0.75-0.79; this round:
  0.77-0.79).
- Hitting every measured human number (p9) changes nothing.

**The wall, and why:** the judges pick the human by things a script can't have: live-speech slips, non-native turns, garbled restarts,
and a creator's own idioms (their tells, every round).
- A clean or "loosened" script is still a script.
- The scripted voice-over pairs are the realistic target. There ours sits at 0.59-0.73 depending on the round: near the line, but not
  reliably under 0.60.
- The spoken edit stays in the method as good practice for the ear, not as a proven lever. It costs nothing, keeps the measured
  features in the human range, and never scored worse.
