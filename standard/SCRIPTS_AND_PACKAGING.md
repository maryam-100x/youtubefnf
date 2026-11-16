# Scripts, titles and the upload pack: the standard

*Part of `STANDARD.md`. The main chat reads all of it; the Shorts chat reads the whole script craft and the Shorts parts. The bar is
the newest script the creator signed off (`cases/SCRIPT.md` names it; `standard/BAR_LONG_FORM.md` and `BAR_SHORTS.md` say what a video
at the bar does): match its quality, never copy its moves. How to learn all of this, with worked examples and the measuring sticks
built at setup: `standard/SCRIPT_TRAINING.md`. When the creator's note contradicts a rule here, the rule is rewritten in place
(`CLAUDE.md` office rule 2).*

## 1. Scripts that read human (read this first)

The commonest viewer complaint on AI-voiced videos is "AI script". A study measured why, against the captions of 100 real videos from
68 channels, with blind tests in which fresh judge agents (Claude models) label unlabelled passages mixed among real creators' (about
235 judge runs in the first rounds, hundreds more since; the tools are in `tools/script/`, section 5). What it proved:

- **A tidy explainer style is itself the tell.** Scripts written the compressed way (short one-fact lines, a definition on every
  term, a role on every name, stat ladders, tidy closers) score P(AI) 0.70-0.85; real YouTubers 0.05-0.25. A real tech creator's
  passage (0.15) rewritten only into that style scores 0.66.
- **The creator's own words read human.** Their interview answers, cleaned of restarts only, score 0.12-0.42. The same takes blended
  into narrator lines get flagged. Every paragraph that carries the creator's view scores 0.20-0.45; fact-only paragraphs 0.55-0.80.
- **One judge, audited.** The two Claude judges used (Opus and Sonnet) agree at r = 0.93-0.98, so they are one reading, not two bars.
  The judge is stable (the same passage in another packet: r = 0.87-0.96), valid (it tells known AI narration from 28 human passages
  perfectly, AUC 1.00) and does NOT punish scripted writing: human scripts written before 2022 and read by their writers score
  0.16-0.23, creators talking 0.15-0.21, a niche's scripted voice-over channels 0.32-0.42 (the biggest of them about 0.2). Project
  context in the judge's head changes little (clean against primed: r = 0.98). The company a passage keeps does: the same passages
  scored 0.55 among other writers and 0.74 among their own sibling versions, so the gate judges each passage alone among humans. A
  judge from another model family reads differently (r 0.5-0.7 with Claude, easier on the explainer style, unstable when a packet is
  mostly AI): a second opinion at most, never the gate.
- **What passes:** where the creator's interview answer runs through a section, 7 of 8 judgments pass (0.20-0.45); fact-only
  sections the chat writes stay at 0.55-0.65 whatever the method (about forty-six methods tried: imitating human scripts, other or
  smaller writer models, the spoken grammar register, de-polishing, quoting the sources, random plans, composing in another language
  and translating, a persona). A full script written the explainer way: 0.61, none of ten sections passing; the method below:
  0.47-0.52, four or five of ten (all of them sections with the creator's view). The research says why (Sun et al., ICML 2025: a
  model's fingerprint survives rewording, translation and paraphrase; it is in the choices, not the words).
- **Wording doesn't fix it; what the narrator does does.** Humans reason out loud, show their own work, quote real people, digress, say
  a thing twice, leave a thought unfinished; a model presents information in tidy, compressed, self-contained units.

So every script is written this way, the gate runs before any voice, and the part that keeps improving is the chat's own lines.

**What the judges flag (never write these):**
1. A run of short one-fact declaratives ("The app uses X. It does Y. That's called Z."). Humans spread: sentence-length SD 7.5-12
   words, 7-32% of sentences 25 words or more.
2. A definition tacked onto every term ("a feature called X. X does Y", "which is called X") and a role on every name ("Dana Reyes,
   one of the three people leading the redesign").
3. Stat ladders and number density (the explainer scripts: 54 numbers per 1,000 words; humans 11-35); "X says" on everything (5.5-6.9
   per 1,000 words; humans 0.3-3.1).
4. Textbook analogies, "isn't X, it's Y" reveals, setup-then-punchline pairs, triplet flourishes.
5. Paragraph architecture: a framing line in, a tidy summary or a punchline out ("which might be the most on-brand thing in the whole
   story" is a punchline closer).
6. **Compression** (named on nearly every passage): every sentence a tidy, compressed fact with no filler or hesitation.
7. **Devices:** casual words, jokes, hedges or "moves" laid on top of an explainer read as planted, performed, staged casual. Anything
   written into a writer's brief as a technique comes back as the next tell (taught "a question, then 'Well,'", it becomes a
   "self-posed rhetorical question"; taught "point at the footage", it becomes "screenshot-caption narration").
8. Explaining for a blank viewer in every sentence ("every sentence pre-explains"): explain what a casual viewer needs once, in plain
   words, and let the rest ride.
9. **What viewers themselves call an AI script** (a widely shared viewer thread listing the giveaways): "it's not X, it's Y" and its
   cousin "the X of Y isn't A, it's you"; **"no X, no Y, just Z"**; "and honestly?"; a question the narrator answers ("and (thing)?
   that's (adjective)"); mirrored template lines ("they (verb) and (verb), but they never (opposite)", "(thing) first, (other thing)
   later"); groups of three; "here's the part that surprised me"; made-up "it's like..." scenarios; **intensifier stacks as humour**
   ("it's not just hard, it's a complete ... nightmare"); **the same point again in new words** (so "said twice" in "How to write it"
   below means a real repeat a person makes on purpose, never a reworded restatement); **no em dash or "--"** in a voice line or the
   captions. One alone rarely gives a script away; the stack does. Search every script for each before the gate.

**The style method (the wording: the primary check).** What wording is judged on is the niche's lingo, the sentence structure and the
natural way of talking, not who has opinions: the chat chooses every word either way. It is measured by **the pair test**
(`tools/script/pair_test.py`): a real creator's passage and ours on the same content, side by side; a clean judge picks the human
(0.50 = can't tell; two different humans on the same content: 0.60). Measured: explainer wording 0.79; the method below 0.69-0.70 in
its first round, 0.59-0.60 against scripted voice-over; **but judged again beside two newer methods it scored 0.79**: rounds move a
method by about 0.1, and inside one round every wording method sits within 0.04 of the others. **The wall:** the judges pick the
human by live-speech slips, non-native turns and a creator's own idioms, which a script doesn't have; imitating real passages in
context (0.77) and closing every measured gap number by number (0.79) didn't move it. The steps stay as practice for the ear (they
keep the wording inside the human ranges and never scored worse), not as a proven lever:
1. **Draft** the section in plain words (section 2, "Scripts: the bar").
2. **The spoken edit, as its own pass by a fresh agent** (writing and editing in one head measured 0.77): how the niche's voice-over
   creators say it: the same plain words reused instead of varied; the small glue words (just, you, this, that, really, pretty,
   stuff); sentences that run on with "and" and "so" and change direction; now and then a loose or redundant phrase or a
   self-correction; the register's numbers (sentence spread, connectors, openers: `tell_lint.py --style` prints them against the
   corpus); no written constructions ("it's not X, it's Y", "what X is, is", "here's the thing", colon set-ups, neat closers, lists of
   three for rhythm). Never by inserting stock phrases (a phrase bank mined from real creators measured worse, 0.74: "inserted
   fillers"). The creator's banned words stay banned.
3. **Measure the wording:** `PIPE tools/script/tell_lint.py videos/<video>/script.md --style` (the eight features that predicted the
   judges in 80 pairs: content-word share, word variety, word length, "just", "you", sentence length and its spread, written
   constructions, each against the middle half of real creators) and `PIPE tools/script/tell_lint.py videos/<video>/script.md` (the
   named giveaways).
4. **The pair test for a new writing method** before it is used (content points from real passages, the method writes them, judges
   pick): pass at or under 0.60 against the scripted voice-over pairs.
5. **The content gate (below) as the second check:** it measures whether a person's view is in a section, which wording can't change.
   It runs before every voice and its numbers go in the script's header; after its one loop it doesn't block a script.

**The content method, step by step** (worked example: `standard/SCRIPT_TRAINING.md` section 2.2):
1. **Map the creator's views onto the sections before writing.** For every section of the outline, find their take on that topic in
   the video's `OPINIONS.md`, earlier videos' `OPINIONS.md` on the same topic and `creator/PROFILE.md`. The interview after the script
   (section 3, step 10) picks its spots among the sections that have no take yet: questions for their opinion, never for lines. A
   section they have no view on stays fact-only and is expected to land at 0.55-0.65 (said plainly). Never a view they didn't give.
2. **Write each section lean, with their view running through it.** The voice carries the story and the creator's view in the first
   person ("for me the first version was the best this app ever got"), written new in clean spoken English (a fresh agent checks every
   such line against `OPINIONS.md` for kept spoken phrasing); the precision goes on screen (exact numbers, dates, full names and roles
   as captions and name cards), so the voice uses the four or five facts that matter; at most one explanation of a term per section,
   inside a sentence; start where it gets interesting, not on the date.
3. **Lint the named giveaways:** `PIPE tools/script/tell_lint.py videos/<video>/script.md` (glosses, date openers, stat ladders, colon
   set-ups, restatement fragments, callback closers, "from X to Y" turns, triplets, teaser endings, nobody in it). Rethink a flagged
   sentence; never swap the flagged words.
4. **The gate** (below): each section alone among seven calibration humans, a clean Opus judge; pass at or under 0.47 per passage.
5. **One loop** on the sections that fail: rethink each from its judge's tells, judge it again; then settle, with every section's
   number in the script's header, told to the creator plainly. A question to the creator is never the fix for a flagged passage, and a
   view is never invented to make one pass.

Measured and left out: composing in another language and translating (worth about 0.02 on fact-only sections, and its literal
English isn't channel quality), imitating human scripts (0.76), other or smaller writer models (0.77-0.78), a random plan per section
(0.73), quoting the sources with "I went back to the thread" (0.76, "planted first-person").

If the creator chose narration without "I" (`creator/PROFILE.md`), their view still runs through the section, said as the video's
own verdict ("the first version was the best this app ever got"). The measured lever is a real person's choices and view, measured
in the first person: if the numbers come out higher without it, say so plainly.

**How to write it:**
1. **The creator's opinion first, our words.** The interview answers give the opinion and its reasons; every line is written new in
   clean spoken English (a good sentence of theirs may stay, never blindly). Before every voice a fresh agent reads every changed line
   against `OPINIONS.md` and flags any line that keeps their spoken phrasing, broken grammar or words meant for the chat; nothing is
   voiced with a flag open.
2. **Write the rest the way the creator talks.** Before a section, read their raw interview answers (`videos/*/OPINIONS.md`, the
   newest first) for how they think out loud: the order their thoughts come in, how they start a point ("Okay, so ..."), their
   connectors, how they say they're unsure ("I'm not sure, but I think ..."), how they say a thing twice, where they go on a short side
   path. Then write the section the way they would talk it over the clips, and clean it the way their answers are cleaned. Never put
   an opinion, feeling or experience in their mouth they didn't give; where the facts need reasoning, reason the way they do, as a
   guess, said straight (no "probably"). This is the one first-draft method a fresh writer passed the lenient judge with (0.48, 2 of 4
   judged human; the strict judge 0.65).
3. **Talk it, don't compress it.** Fewer facts per sentence; a point can be said twice on purpose, the way a person repeats
   themselves (never a reworded restatement: the tells above); a short aside is fine (0.46, 2 of 4 judged human). Never pad the
   video: this is how a sentence is said, not how long the video is.
4. **A guess with its reason** in most paragraphs, when the facts call for one ("the same supplier makes the screens for both, so I'd
   bet the cheaper one gets it next year"): every passage judged human had one; a paragraph of sourced facts and tidy cause-and-effect
   chains reads AI however casual its words.
5. **Point at what matters on screen** ("up in the top right here"), never caption each shot ("here's the box sitting on a white
   counter" reads as screenshot-caption narration).
6. **Precision on screen, the voice loose:** a caveat about a picture is its caption, a role sits on the name card, the whole set is
   on the graphic; the voice says it once, in passing ("the price, the size, that kind of stuff").
7. **Our own work, only if true** (what the channel measured, counted or checked); **real people's words as quotes** where they said
   them, never paraphrased into narrator facts.
8. **Rhythm by meaning:** a mix, never one shape; repeat a word rather than vary it; let a paragraph end on the fact or the creator's
   take, never on a button.

**Never ask the creator for lines.** Their takes are for subjectivity, never for humanizing the script: the lingo and the sentence
structure are the chat's craft, and subjectivity comes from the interview questions. A question asks for their take, never for a
hook or a section in their words, and never as the fix for a flagged passage. When the chat's lines don't pass, the numbers go to
the creator plainly.

**The script reads human by itself; the interview only adds the creator's view.** Every line the chat writes (a script, a rewritten
hook, one new sentence) goes through the gate before any voice or sample goes to the creator, and a script changed after its gate is
gated again (its changed sections): a change that skips the gate is where the tells come back.

**What the strict judge (Opus) measures:** a passage reads human in proportion to how much of it is a real person's own thinking: the
creator's answers with the facts inside their own sentences 0.32; mostly their answer 0.55-0.60; the chat's lines plus their answers
0.62-0.67; the chat's lines alone 0.62-0.71 however they are written (compressed or talked, own work, open questions, viewers'
questions, the creator's manner, any writer model). So a fact the creator left out goes inside the sentences that carry their view
("it launched at four hundred and now it's five fifty, and the beans keep getting more expensive for every roaster, so I really
don't see it getting cheaper"), never as the chat's line in front of their take (fact lines first pulled the creator's answer to
0.62-0.68); real people speak in their own clips where they said it (a `HOLD`, section 3 step 12); the chat's own lines between them
stay few, short and plain. The interview spots are for the creator's opinion, never a way to get the facts said by them, and
inventing their speech is off limits: only words they really said go in as theirs.

**Measured and not worth repeating:** worked examples handed to a writer (0.69-0.73); writing over a shot list (0.72); building each
paragraph on a real paragraph's skeleton (0.65); cutting the attributions alone (0.73); a joke in each paragraph (0.66: jokes stay
where they're actually funny, never as the fix); a de-compressed rewrite with the precision moved on screen (0.66). Each moved the
lenient judge a little and the strict one not at all.

**Argument sections are the hardest.** Descriptive and explanatory sections can pass the lenient judge on the chat's own lines
(written talked 0.46; in the creator's manner 0.48). Argument sections plateaued at 0.66 after three loop rounds, and three more ways
stayed above the bar: reasoning toward the point (0.68-0.78), picking the lowest of six drafts from four writers and plans (best
0.60), retelling a real viewer's argument with credit (0.68-0.85: "X says" becomes the tell). The strict judge holds every line the
chat writes at 0.62-0.72. So argument videos are written with the fewest stacked sources and balancing turns, gated, and their
numbers said plainly. **When the rounds stop moving the numbers, settle the best version:** there is no point in trying again and
again; the video goes on, the numbers in the header and told to the creator plainly.

**The gate (before voicing):**
1. Put the sections to judge in a text file, one section per line (whole beats, about 130-200 words; a long video: every section that
   changed, or one per section), e.g. `videos/<video>/gate_sections.txt`.
2. `PIPE tools/script/judge_panel.py gate <video>_gate --ours videos/<video>/gate_sections.txt`: each passage alone in a packet among 7
   of the about 28 calibration humans (built at setup from the creator's niche: `standard/SCRIPT_TRAINING.md` section 1). A second run
   on the same set packs only its new passages, so saved verdicts still match their keys (`--reshuffle` re-packs everything and
   orphans them).
3. Judge every packet with a **clean** agent (the Agent tool, subagent type Explore, model opus: it carries no project files, and it
   can't write, so the chat saves its answer): the prompt from `PIPE tools/script/judge_panel.py brief <video>_gate g_pNN --judge
   opus_clean --clean`; save the JSON answer as `MEDIA/script/panel/<video>_gate/verdicts/g_pNN__opus_clean.json`.
4. `PIPE tools/script/judge_panel.py score <video>_gate --items gate_sections` (the kind is the sections file's name): every passage
   with its number and the tells its judge named, and the humans of the same packets beside it (scripted human narration about 0.2,
   a niche's voice-over about 0.4).

**Pass: every passage at or under 0.47.** Then **the loop** (rethink each failing section from its tells, never swap the flagged
phrase) and judge it again; then settle with the numbers in the script's header. A judge costs one agent run per section: never skip
the gate to save usage.

**Shorts:** a timeline Short (dates, then a callback closer) scores 0.8-0.9 whatever the wording; human Shorts in a niche argue one
point or point at one find (measured 0.03 and 0.09-0.21; scripted theory Shorts 0.35-0.56). **A Short built on the creator's take
passes:** their interview answer, cleaned, with two price facts woven in, scored 0.08 on the lenient judge and 0.32 on the strict one,
all four judgments human, below the human Shorts beside it. So a Short with a take is the creator's take with the facts inside it; a
Short without one is built on one claim or one find and its reason, never a chronology. The gate takes whole Shorts: the Short's VOICE
text as one line in a text file, among whole human Shorts of the niche (the corpus group `shorts`, 7 or more):
`PIPE tools/script/blind_test.py make <short>_gate --ours <short>.txt#para --human <id>#all <id>#all ... --split`; a clean Opus judge
on each packet (`MEDIA/script/blind/<short>_gate_<k>/packet.md`; save its answer as `<short>_gate_<k>__opus_clean.json`, the
packet's name in the file name); then `PIPE tools/script/blind_test.py score <short>_gate <the verdict files>`. The same pass line,
0.47.

**The lingo (measured):** a script is more than what is said: it is also the lingo. Measured against a niche's real creators, the
explainer scripts said "this" (this guy, look at this) a third as often, "we / we'll / let's" a quarter as often and "will / going to
be" a fifth as often; they said the subject's full name five times the real rate (14.9 per 1,000 words against 1.35: real creators
say "it", "this one", the short name), twice the numbers, seven times the "says", and the official titles in full. Heavy slang is
nearly absent from real narration (0 in 213,509 words): a slang word only where the creator would say it. The niche's own plain words
(what its creators say far more than scripts do, and the reverse) are measured at setup into `kb/LINGO.md`: read it before writing.
The stock list stays banned: "literally" more than once, "And honestly", "favorite line", "wild", "crazy", "the funny part" (plus
every line the creator flags, in `tools/script/niche.json` "flagged_lines"). **The subject's name** opens a topic or goes where
anything else could be meant; once it is the subject, "it", "this one" or the short name; never a vague "a product" or "the new
one" where the name belongs.

**Writing it is the chat's to learn:** no voice drafts from the creator, no extra questions. The blind gate is how the chat knows it
has learned it, script by script; the strict judge's number says how far there is still to go.

## 2. Scripts: the bar

- **A point is made once**, never as a statement and again as a demonstration. **A set the source shows is named whole** and checked
  against the footage (all six sizes on the official chart, not the three in the first shot). **General lines cover everyone
  watching** ("on a phone or a laptop", never one brand where all are meant) and say "screen", not "TV". **A forecast or opinion keeps
  the channel's stance from earlier videos** (`kb/` holds it): never a new date or verdict without the evidence that changed it.
  **"A lot of people" only when it is a lot**, else "some people speculated". **A number word right after a name that ends in a
  number is heard as part of it** ("the Pro 6 years from now" is heard as "six years"): reword.
- **Every line specific and simple** (vague and eloquent is bad; simple words and specific is good: the audience is worldwide): every
  number says what it counts and whose ("two million units" -> "the new model to sell two million units in its first month"); every
  change says what changed ("nearly doubled in size" -> "nine hundred people work there now, almost twice as many as five years ago");
  every person who matters has a name and a plain role, said once, in passing or on the name card ("Ana Ruiz, who runs the company"),
  and someone viewers don't know, whose name adds nothing, is said by company and job ("one of the engineers who built it"); every
  thing its name (never "a product" where the name belongs; once it is the subject, "it" is fine); words a non-native speaker knows.
- **In a technical breakdown** the technical term is said, then explained in plain words right after, with a picture that
  demonstrates it where one exists (the same clip at full speed and in slow motion, side by side); nothing is left out for being
  nerdy; what everyone knows from daily life (a screen resolution, a phone's storage) is said plainly and never explained.
  Behind-the-scenes material (the makers at work) goes in as stylized transitions, never as the subject. For what the maker hasn't
  said: its closest official words, what credible sources say, then our best guess, said as ours. Outside technical breakdowns, nerd
  detail that isn't the topic stays out, which never means hiding a name.
- **A thing new to the video is named the first time it's said**, with what it is, inside the sentence ("the company's own design
  tool, which they call Atlas"), never "that tool" before its name; a line that turns to a new topic says how it follows from the line
  before (read every seam after inserting a beat, the creator's view beats included). **A name or term most viewers won't know** gets
  a plain "meaning ..." or "known for ..." in its line and its picture on screen; what the niche's audience already knows is never
  glossed (tell 2 above). "This", "these", "here" only over the thing itself on screen.
- **The hook:** the first words hook: say something that triggers people, in a good or a bad way (both work); it names what people
  know and takes the widest frame anyone gets; it never answers itself (a hook that gives away the punchline makes people swipe
  away); in a Short, keep the how for later: edge people so they stay (`standard/SCRIPT_TRAINING.md` 3.1;
  `standard/research/SHORTS_CRAFT.md` section 2; `standard/research/LONGFORM_CRAFT.md` section 1).
- **Write for a casual viewer anywhere:** background in a few plain words; history in one sentence or one quick rundown said as one
  ("before we get to what's next, here's the company in a nutshell"), then what's happening now (where the history is the topic, an
  era or a story, it is told in full); one number that sounds crazy, no units, no mechanism; no number to decode; something most
  people never used gets one plain line on how it works (`standard/SCRIPT_TRAINING.md` 3.2).
- **Calm, real interest, from the viewer's side:** what would a person in this niche want to know? Facts serve that, with our takes;
  never a neutral analyst's report, never put-on excitement. Chapters only when the video tells a story in parts; a topic video runs
  as one piece.
- **One point per line, never restated, no filler facts** (Shorts don't like stalling); a long video delivers the title's promise
  itself, told fast; a script that reads like a newspaper has failed.
- **No AI tells:** no "X? Y." beats, no question the narrator answers, no line that announces the next ("here's the crazy part"), no
  stock lines ("everyone's losing their minds", "that's the energy", "my favorite line was"), "literally" at most once, never "And
  honestly,", no writerly turns or tidy wrap-up clauses, fragments only when each carries a fact ("The bridge closed for repairs. Twice.").
  **No quip tails:** no little comment tagged onto a fact ("which, from up there, you kind of need", "which I guess is their way of
  saying ..."): say the fact and move on.
- **Said like a person:** counts said the way you'd tell a friend ("close to five thousand people work there now", never "around
  4,711"); a long time gets its starting point; "that same X" only for the same thing; a quote comes with what happened around it; an
  example earns its place by doing something few do (a common feature is no example of being ahead); no stock phrase repeated across
  videos; the sub ask said like a person, never "if you like videos like this"; the line names its subject, and the creator's message
  is its own clear sentence; foreign names respelled the way an American says them (otherwise the voice reads them in the name's own
  accent).
- **Say it the way the creator talks:** their openers, closers and everyday comparisons (`creator/PROFILE.md`, their interview
  answers); opinions start the way theirs do ("I think", "In my opinion"); a joke is a person reacting; grant what's fair, then push
  back; slang only in its real meaning; direct and current, no coy phrasing, no swearing in the voice. Learn the structure, never paste
  their phrases (`standard/SCRIPT_TRAINING.md` section 5).
- **Who is talking:** the creator as `creator/PROFILE.md` describes them (their age, their history with the niche, their mood): always
  a cool, relatable YouTuber, never a narrator reading.
- **On the viewers' side, with a take, said calmly:** never so neutral that nobody is in the video; the channel's take and theories
  said boldly with the higher true number ("my bet is", never "who knows"); when the narrator is in the story, a shrug, never a
  declaration (`standard/SCRIPT_TRAINING.md` 3.9). **The opinions are the creator's:** a script with no take of theirs reads too
  neutral; after each script the chat interviews them and blends their answers in (section 3, step 10); the chat never makes one up:
  the creator is the opinion. **An argument video argues only the creator's points:** every point of its outline carries where they
  said it (`videos/<video>/VISION.md`, the interview); a point they never said is asked first or dropped, however well it fits the
  material; an interview answer that contradicts a point removes it the same turn. **Criticism says why:** every claim or act the
  video shows and argues against is followed by the problem in one specific, direct sentence (the creator's reason, asked before the
  voice when it's missing), never a vague hint line. **Advice, not orders:** a tip is the creator's advice ("my advice would be to
  maybe ..."); a warning is about overdoing, never "don't at all".
- **A viral YouTuber, not a fact checker** (`CLAUDE.md` office rule 6): what the creator sends is the story, told straight, no
  "reportedly"; the only brakes are measured costs: no false fact, no leaked material shown or told as fact (at most that a leak
  happened), no testimony from random social accounts, never an ad for someone who leaks or steals material.
- **Research said in our own voice:** what the research found (measurements, analysts, outlets) is a plain statement in our words,
  never "the magazine said"; never claimed as ours either ("I measured" only when the channel did); the credit sits small in a corner
  of the picture showing their material, or in the description. A source's own original content that the video reads or shows (an
  article, an interview, a post) is named and quoted ("the review says ..."), because then it matters whose words they are. A name
  stays in the voice when who said it gives the words their weight (the maker's leaders, the company's boss: "the important thing here
  is that the CEO is saying it"). A common experience is told as the viewer's own ("you'd wait about forty minutes for a table"),
  never "one customer did X": viewers lived it too. Search every script for says/said/according to/found before the voice.
- **Say what a careful AI wouldn't:** the boldest true reading, straight and in the niche's plain words; no hedging, softeners, formal
  phrasing or both-sides padding ("it's worth noting", "arguably"). Down to the single word: no "it looks/seems", "basically", "kind
  of", no euphemism ("went under") where the plain word exists ("bankrupt"): "The chain spent four years and two hundred million
  dollars on its own delivery app, and it never even launched", not "... and it seems to have quietly gone away". Only the measured
  brakes stay (a false fact, a policy cost); opinions stay the creator's.
- **Every sentence makes sense on its own:** read each sentence alone, as a normal person hears it: does it make sense at all? An
  obvious thing is said as obvious, never dressed up as somebody's find ("someone actually counted the four windows"), and no "at
  least" on a number the viewer can see. **Serious theories only:** a mystery or theory video takes only the theories with something
  real behind them; jokes, puns, number coincidences and reactions are sorted out by common sense before the voice.
- **What the channel already covered is said plainly:** a fact earlier videos explained comes in as a fact in a line, in new words, no
  reveal and no "by the way" (`script_lint.py` flags lines shared with earlier scripts; read the last videos on the topic too).
- **Questions get full stops:** a row of separate questions or claims is written as separate sentences, each with its own full stop
  or question mark (or a colon after the opening words), never joined by commas: commas keep the voice's pitch up, like a run-up to
  one point ("So two things. Does it really last ten years? And who fixes it when it breaks?"). No commas inside one question either:
  a question is one clause said in one breath ("Is the corner bookshop finished for good?", not "Is the corner bookshop, the one every
  town used to have, finished?"), and a short last word after a long clause gets a fuller ending ("finished for good").
- **Timeless and safe:** no "just" meaning recently, no yesterday/today/this week/breaking (give a date); no "kill" in the title or
  the voice; words YouTube won't like stay out, even by accident (a softer word for sexual words, the way creators say "corn" for
  porn; a word like "naked" gets the bass-boom censor or stays out, never a beep); the primary source's own dialogue in its clips is
  never censored.
- **One mood; humour only where it's funny** (a callback or a person's reaction lands; a forced joke or a meme doesn't).
- **The title's promise is the spine:** before the outline, write the promise in one line and give it most of the minutes; what led
  up to it is a 30-60 s recap. The promised span is researched exhaustively (every event, person, record and controversy with its
  story, never a list of names), and the script picks the interesting part.
- **Length and endings:** length follows the material: did we make an extensive, high-quality video with all the interesting
  information there is, or not. Length is never a danger: nothing is left out to make a video shorter, no filler is added, no range is
  set and no minute estimate is written down; a topic is covered whole (a list is a start, never a cap); a documentary (an era, a
  history) covers its subject whole, researched in full before the chat picks what goes in. The one floor: a long video is 8:00 or
  more, checked on the script (section 4). A Short ends on its payoff (a loop where the story allows, or a real question). A long
  video asks for the sub at a real break, ends on its strongest fact, then the creator's sign-off (`creator/PROFILE.md`) with the like
  and comment ask, then a fade.
- **The rhythm:** varied by meaning, never held to a band (model sentence lengths cluster; humans spread). A sentence the voice can't
  carry in one breath (about 45 words) gets split.

## 3. Scripts: the method

1. **The creator's idea, their material:** their intuition picks the video (no idea research they didn't ask for). A new video starts
   with a talk about its vision (what it is, who it's for, what it must answer, how it should feel), their answers verbatim in
   `videos/<video>/VISION.md`, before any research; the questions they name there show the depth they want, never the outline (the
   outline is the chat's, from the research and everything the title holds). What they send is the story and the source, read in
   full; what they say is material, written into our own lines (ask when a voice-to-text slip changes the meaning). When they ask for
   ideas: the chat's own, creative, timeless, mainstream, each with how it would be made.
2. **The research and the fact table first:** research is never called complete (every item with its story and a depth mark, an
   honest "not researched yet" list, and a fresh agent reading the pack against the subject and naming what's missing). The fact
   table: claim, source, date read, grade (A official, B reputable, C unverified); facts against `kb/`; the source's own lines from its
   official captions and a broadcast speaker from the broadcast's captions, never a speech-to-text guess; a leak only as an event; the
   top of a true range.
3. **Angle and shape:** the viral angle and the widest frame, the one-line promise in the notes. A long-form opening does what the
   bar's openings do (`standard/BAR_LONG_FORM.md`): puts the viewer in the world now, shows what's at stake with real numbers, hints at
   the trouble with real receipts, then turns into the story. Each video finds its own devices for that (never a worked opening's
   device copied); an argument video turns in spoken lines, no chapter cards; a Short is built for Shorts (a known name, short beats
   that hold back the how, the payoff last).
4. **The pipeline format** (`tools/dj/script.py` parses it; `standard/PIPELINE.md` has every key): a header (what it is, the facts
   and their sources, each version's change and why, the gate numbers); `## Voice` (which voice settings: long form or `[tts.short]`
   in `config/tts.toml`); `## Beats` in a fenced `text` block with `# ===== SECTION =====` labels, `[S01] VOICE:` lines,
   `[S05h] HOLD: 2.3` where a real person's clip speaks (0.3-10 s), `CONFIG:` lines; in Shorts one `*key phrase*` per beat (its key
   word in the look's caption key colour in the captions).
5. **Draft the way the creator talks** (section 1, "How to write it" 1-4): read their newest `OPINIONS.md` answers first; a list
   becomes separate beats, one picture each; cut what a casual viewer doesn't need.
6. **Every line against `standard/SCRIPT_TRAINING.md` section 3:** would someone who only casually follows the niche get it? Would a
   friend say it like that?
7. **Lint:** `PIPE tools/script/script_lint.py videos/<video>/script.md` (`--all` lists clean beats too; `PIPE
   tools/pipeline/pipe.py <video> script` runs it with `--strict` as the line's script gate); fix every flag or keep it with a written
   reason; announcer phrases 0-0.4 per 1,000 words, one opener on at most about 15% of lines.
8. **Search the script** (script_lint prints the counts): "a <thing>", "the <thing>", "someone", "a company"; just, now, yesterday,
   today, this week, recently, latest, breaking; literally, "And honestly", favorite line, wild, crazy, "the funny part"; every "?" (a
   self-answered question goes); kill; says, said, according to, found; every comma-joined row of questions; every quip tail.
9. **Fresh-listener test:** an agent with no context gets only the VOICE lines and says, line by line, what each number counts, who
   each person is, what each "it/they/that" means, which line needs a second listen and which line doesn't follow from the one
   before; after inserting beats, read every seam yourself too; rewrite every line it trips on (it catches a date with no year, a
   figure of speech a non-native speaker misreads, a connector that changes the meaning, as an "Instead" that makes a new thing sound
   like it replaced the old one, a slipped tense).
10. **The creator's view, by interview** (each chat asks its own: the main chat for its long videos, the Shorts chat one question at
    most for a Short with a take): with the script drafted, pick the few spots where their take gives the video personality (a long
    video 3-6): a verdict on a decision, who was right, what they would have done, how it felt to them. **Plus a few more at the spots
    with the most facts:** each question gives them those facts in one or two plain lines and asks one concrete thing about them ("The
    old recipe used butter, the new one uses oil and less sugar: which tasted better to you, and why?"), never "what do you make of
    that" (it can't be answered). **Only questions where their take is open and adds something:** never one whose answer is a fact
    (state it), one the subject forces on everyone, one already talked through, or one the chat could answer from the research (then
    it is the chat's line); a question about material they haven't seen comes with that material, one plain line each; would a friend
    who loves the niche actually ask it? Fewer, better questions. Ask short, concrete questions in the final message of a turn, each
    with one line of context so they can answer by voice; save their answers verbatim in `videos/<video>/OPINIONS.md`; **only what
    makes a point for the viewer goes in** (a reply to the chat's question, "of course", "I buy that", an echo of the question stays
    out); write them into the beats in our own words from their opinion, with any fact they left out put inside their own sentences,
    never as the chat's line in front of their take (section 1, "What the strict judge measures"). Never an opinion of the chat's in
    their place. While they answer, start the pictures.
11. **The style method, then the gates** (section 1): the spoken edit as its own pass, `tell_lint.py --style` and `tell_lint.py`; the
    pair test for any new writing method; then `judge_panel.py gate` with a clean Opus judge, every passage at or under 0.47; rethink
    each failing section from its tells and judge it again; every section's number goes in the script's header. No script is voiced
    before the gate has run and its numbers are told to the creator.
12. **Ready for the voice:** sentence ends that land; numbers as words, years as digits; a line set in another country or a quote can
    pull the voice into another accent: casual wording, contractions in quotes, a fresh request at the turn
    (`CONFIG: tts.fresh_at=[...]`, `standard/VOICE_LOCK.md`); foreign names respelled; real people's words as their own clips in a
    `HOLD`.
13. **Build without waiting for the creator to read it:** they never need to read a script; they judge the video; the interview is
    questions, not a read. Then `standard/SOUND_AND_VOICE.md` and `standard/VOICE_LOCK.md` for the voicing.

## 4. Before a script is voiced

- [ ] **Long form: 8:00 or more, measured on the script** (the length YouTube's mid-roll ads need): VOICE words at the voice's rate
      plus every `HOLD`'s seconds. `tools/voice/voice_full.py` prints it on every run and refuses a long script under 8:00 unless
      given `--under-floor "<why>"`; it counts the voice's own rate (`config/tts.toml` `words_per_second`: 3.9 until it is measured on
      the creator's first finished narration; at 3.9, 8:00 is about 1,870 words, 10:00 about 2,340). Under 8:00 the script goes back to the research, never to the voice. Every research point is listed as used or
      left out with its reason; what's left out is only what doesn't serve the title's promise.
- [ ] **Said like a person in the niche, in words a kid gets:** never "a fan" or "fans" for people ("someone", "a guy", "people", the
      niche's own word for its people, their name); "I"/"my" for what the channel did ("I measured it myself"), "we" only for the viewer
      and the narrator together; every line in the plainest words ("some recipes only work once the dough has rested overnight", never
      "won't even come together until it's had its overnight rest"); no hedges on our points ("probably"). The same on every on-screen
      label ("my measure", "by her math"). Foreign names respelled for the voice.
- [ ] The hook names what people know, takes the widest frame, doesn't answer itself; a long video confirms the title's promise in
      30 s.
- [ ] Every number says what it counts and reads right to a casual viewer; every person who matters has a name and a plain role (said
      once, or on the name card); no "it/they/this" opens a topic.
- [ ] `script_lint.py` run, every flag fixed or kept with a reason; the word searches of section 3 step 8 done; `tell_lint.py` and
      `tell_lint.py --style` run.
- [ ] Every line the fresh listener tripped on is rewritten.
- [ ] One point per line, nothing restated, history in one sentence or one quick rundown (unless the history is the topic).
- [ ] Every fact in the table with source and grade; leaks only as events; no random social accounts; no ad for a scheme.
- [ ] Every theory serious; every sentence read alone makes sense.
- [ ] The interview done: the answers in `OPINIONS.md`, blended in where they fit, said calmly; no opinion of the chat's, no hedge, no
      suspicion line, no boast; a fresh agent checked every changed line against `OPINIONS.md` (spoken phrasing, grammar, words meant
      for the chat), no flag open.
- [ ] The gate ran: every section's number in the header and told to the creator.
- [ ] The ending: a Short stops on its payoff; a long video has the sub ask at a real break and the sign-off last.
- [ ] Ready for the voice: numbers as words, ends that land, comma-joined questions split, accent-risk lines reworded with a
      `fresh_at` break, real bites as `HOLD`s.
- [ ] Read aloud once as a first-time viewer; rewrite any line that needs a second listen.

## 5. The script tools (`tools/script/`, run with PIPE)

Creators' words (the corpus, every packet and verdict) stay in MEDIA, never in git. The repo ships none: the creator's niche builds
them at setup (`standard/SCRIPT_TRAINING.md` section 1).

| Tool | What it does | How it runs |
|---|---|---|
| `script_lint.py` | The script gate: flags the lines that sound like AI narration, a reporter or a vague writer, each flag with its reason. Its checks: **wording** (announcer lines, "X? Y." beats, stock lines, writerly irony, boasts, hedges, "literally" twice, sentences over 45 words, nerd and finance words), **vague** (a count without its noun, a role where a name belongs, a bare pronoun opening a section, a number with no owner, a money word with no figure), **point** (a big number with no comparison, rate or consequence), **opinion** (a take that lands after an unrelated line; a long video with no take of the creator's), **copies** (a line shared with an earlier video's script), **time** (recency words), **shape** (the sub ask before 35% of the words, a reporter's share of said/says lines over 25%, nobody in the room, a long video not ending on the sign-off word, one opener on over 15% of lines), **search** (the counts of section 3 step 8). The niche's own words come from `tools/script/niche.json`. Tests: `tools/script/tests/test_script_lint.py` | `script_lint.py <script.md> [--all] [--strict] [--json <out>] [--ignore 12,15] [--against earlier\|all] [--format long\|short]`; `--strict` exits 1 on a flag (pipe.py's `script` step) |
| `tell_lint.py` | The habits blind judges name on AI narration, counted per paragraph: gloss, date_open, stats, colon, fragment, bookend, turn, triplet, teaser, no_person. It can't make a passage pass: over 287 judged passages its flag count tracked the judge at r = 0.30 (no flag 0.53, one or more 0.67-0.72; with first person or a stance 0.58, without 0.70); a screen for the named giveaways, not a pass. `--style`: the eight wording features against 160-word windows of the corpus's `voice` and `talk` groups, flagged when on the caught side of the human middle half | `tell_lint.py <script.md> [--para]`; `--style [--per-para]`; `--validate` (its flags against every passage the judge panel scored) |
| `voice_metrics.py` | How a narration's words are shaped (per 1,000 words), the same way on the corpus and on the scripts; tell_lint and pair_test use its features | `voice_metrics.py compare [--ours ...] [--groups ...]`, `voice_metrics.py one <file>` |
| `pair_test.py` | Style only: a real creator's passage and ours on the same content; the judge picks the human. Pass at or under 0.60 on every content | `make <set> --content content.json --ours <file>@<method> [--validation validation.json]`, `brief <set> <packet>`, `score <set> [--features]` |
| `judge_panel.py` | The calibrated blind panel and **the gate** (section 1) | `pool`, `packets` (normal, or sparse with `--test-per`), `gate`, `brief`, `score [--items ...]` |
| `blind_test.py` | The simple blind test (one packet, or `--split`: one of ours per packet among every human given) and the clean-up every judge tool shares (numbers as digits from eleven up, quotes straightened, caption noise decluttered), so number spelling and speech-to-text slips are never evidence; `--human <id>#all` takes a whole text (a Short) | `make <name> --ours ... --human ... [--split]`, `score <name> <verdict files>` |
| `human_corpus.py` | The niche's real creators' words, captions only | `fetch <ids> --group <g>`, `clean`, `list` |
| `lingo_corpus.py`, `lingo_measure.py` | The lingo study behind `kb/LINGO.md`: what the niche's creators say far more than the scripts do, and the reverse | `lingo_corpus.py [--ours ...]`, `lingo_measure.py [--groups ...]` |

## 6. Titles and the upload pack (in short)

- **When:** only after the creator calls the video done: title, description and tags, then each Short's title and tags.
- **Who picks:** the creator, often naming it themselves. When they ask, give many genuinely different options that read like real
  YouTube titles, one line each.
- **Plain English, simple and enticing:** a short general promise, the way a person would say it out loud; never a line of the
  script; no clever turns or slogans. Read each title cold before sending it.
- **Long-form titles:** general and mainstream (a casual viewer gets the subject without the niche's background). For a big-picture
  subject the default shape is a plain statement of about 5-7 words naming one big subject, no CAPS word, no "you", no brackets, no "?"
  or "!" (on the channel this comes from, 5 of 6 such titles hit against 2 of 9 others; across a niche the shape alone measured flat,
  0.96x, so it rides with a big-picture topic). It opens a question it never answers ("The Real Cost of Cheap Coffee": what cost?);
  a title that states the answer ("Cheap Coffee Hurts Farmers") has no bait. Bait is welcome when the first 30 s pay it off. The
  method: 20+ titles in six families (verdict, discovery, comparison, a list with a unique promise, explainer, disproval), pushed to the
  most exaggerated version, then pulled back to what the video delivers; the subject and the hook early, one concrete noun, no
  trailing "...", never "kill", no possessive apostrophes ("The First Year of the Company", not "The Company's First Year").
- **Capitals:** the first word capitalised, the small words in the middle lowercase (the, a, of, for, to, and, in, on), so the
  important words stand out ("Breaking Down the Science Behind Sourdough"); capitalisation itself measured no effect.
- **Testing:** every long video goes up with three titles in YouTube's Test & Compare: close variations of the creator's general main
  title (offer about ten near variants to pick from), never other angles (curiosity, hooks, CAPS bait). In a measured test the plain,
  general title took the largest share of watch time (37% against 31-32% for two story titles): a lean, not a rule.
- **Shorts titles:** in Shorts the title is a small lever (measured: title features explain about 4-5% of the differences in a
  Short's lift; most views come from the feed, where the viewer sees the video, not the title): spend the effort on frame 1 and the
  loop. Still: 1-2 CAPS words for the key word, never 3 or more; name the concrete thing, no vague hype ("something", "everything",
  "changes everything"); 6-12 words (about 40-60 characters); a list leads with its count; a comparison says it ("A vs B"); when the
  maker did it, the maker is the subject; say what frame 1 shows; general, not the clever detail. A series keeps one title and one set
  of tags. Say which of these the title follows.
- **Long-form description:** two hook lines (the title's promise in search words, the subject's name in the first ~100 characters);
  chapters from 0:00 (at least three, each 10 s or more); one sourcing line, never a list; credits (every CC BY or BY-SA photo by its
  author and licence; a logo under a licence too); then exactly three hashtags (the subject's main spellings plus one), always the last
  line. No AI-voice line and no footage or affiliation disclaimer: not required. Upload with our own `.srt`, the language set to
  English.
- **Studio's details questions** (check the current YouTube Help pages before relying on this; policies change): **Paid promotion**
  stays blank, except on a sponsored video (long or Short), where it is **Yes** (required: it puts YouTube's "Includes paid promotion"
  label on the video). **Altered or synthetic content** stays blank for an AI narrator and AI help with scripts and titles: those are
  not among its cases (a real person made to say or do something they didn't, real footage altered, a realistic scene that never
  happened, AI music as the main focus); it turns Yes only if a video shows a realistic AI-made picture of something that didn't
  happen.
- **Tags:** spelling variants and search phrases word for word (the subject's names and spellings, the topic's phrases), about 8-12.
- **Shorts:** a title and tags each; no description except the photo credits a licence asks for (each author and licence, checked on
  the photo's own page).
- **Delivery:** each piece in its own code block in the final message of the turn; plain words; never a pack file for the creator to
  open (`videos/<video>/post.md` holds the chat's notes only).
- **Live numbers:** re-read any live number in the script (views, prices, counts) before upload and report it in one line.
- **When it goes up is the creator's alone:** the pack never names a time, a day or "schedule it".

## 7. Read before writing

1. `CLAUDE.md` office rules 3, 5 and 6; `creator/PROFILE.md` ("Their voice and words"); `rules/SHARED.md` and your own rules file.
2. `cases/SCRIPT.md` (the creator's verdicts on scripts and lines, and the line each draws), then the newest signed-off script it
   names (`videos/<video>/script.md`).
3. `standard/SCRIPT_TRAINING.md` in full.
4. The creator's raw answers, newest first (`videos/*/OPINIONS.md`, `creator/interview/`).
5. `kb/LINGO.md` (how the niche's creators talk, measured).
6. `standard/research/LONGFORM_CRAFT.md` sections 1, 6 and 10; `standard/research/SHORTS_CRAFT.md` sections 2 and 6.
