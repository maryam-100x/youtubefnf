# Script training: learning to write the way the creator's niche talks

*Part of `STANDARD.md`. The rules live in `standard/SCRIPTS_AND_PACKAGING.md`; this file is how to learn them: the measuring sticks
built at setup from the creator's niche (section 1), two worked examples (section 2), the patterns behind the rules (section 3),
before -> after pairs (section 4) and how to learn the creator's own way of talking (section 5). Every example here was written for
this file, in niches picked only to teach the lesson; the creator's own corrections replace them as they come in (section 6).*

**How to use it.** Read section 0, then sections 1 and 2 once, then the patterns and the pairs. Write the script, then check it line
by line against section 3 and the checklist in `standard/SCRIPTS_AND_PACKAGING.md` section 4. **The newest feedback wins:** learn
from the most recent scripts the creator approved, because each one improved on the last; what matters in them is the human spoken
language they used.

---

## 0. Read this first

1. **The bar is the creator's newest approved script** (`cases/SCRIPT.md` names every approved script and what it is a reference
   for) and `standard/BAR_LONG_FORM.md` / `BAR_SHORTS.md`. A script that reads like an AI assistant has failed, however correct it is:
   it has to sound like a human YouTuber talking. An old script is never a language reference just because it was published.
2. **Write it the way the creator talks** (their interview answers, section 5): spoken sentences that run on and change direction,
   one point each, plain words, their own opinion, an everyday comparison. Then cut anything a casual viewer wouldn't need.
3. **The hook opens a question, the end answers it**, and a looping Short's last line runs back into the hook.
4. **Every line passes three questions:** would someone who only casually follows the niche get it? Would a friend say it like that
   out loud? Does it say something new, or is it restating the last line?
5. **The target, in one paragraph:** the script reads like the creator talking. Spoken sentences, one point each, never restated; no
   name a casual viewer wouldn't know unless it matters; everyday comparisons; their opinion in the first person; jokes as a person
   reacting; the ending cut the moment the point or the joke lands.

## 1. The measuring sticks, built at setup from the creator's niche

The repo ships no human words. Every bar the script tools measure against is built from the creator's own niche (`SETUP.md` step
12), so "reads human" means "reads like this niche's real creators". The chat builds it with the creator once and adds to it as the
channel grows. Everything here lands in `MEDIA/script/` (creators' words stay out of git).

### 1.1 The human corpus (`tools/script/human_corpus.py`)
1. **Pick the creators.** Start from the ones the creator named in the setup interview (`creator/PROFILE.md`, "Creators they
   admire"), then add the niche's top creators: the biggest channels making the kind of video we make (search YouTube for the niche's
   main topics, sort by views, note who keeps coming up, and the channels the creator's own viewers also watch). Real people only,
   talking to the camera or reading their own script. Leave out faceless channels whose authorship is unknown: a judge can't use
   them as humans (in the audit they scored between the humans and the AI).
2. **Pick the videos, across the groups** (the labels the tools' defaults use): `voice` (a scripted voice-over read by its writer:
   the realistic target for our scripts), `talk` (off-the-cuff talking to the camera), `doc` (documentary narration), `tech`
   (technical explainers), `ref` (the channels the creator wants to sound like), `script` (other read scripts), and `shorts` (whole
   Shorts of the niche, for the Shorts gate). Include several scripted narrations from before 2022, written before chat models were
   public: the sure-human control. A few videos per channel. Captions the creator of the video added themselves are best
   (punctuated); newer auto captions are punctuated too; older auto captions are one run of words and count for word numbers only.
3. **How many:** 15-30 videos are enough for the calibration set and the gate; grow toward about 100 videos from 60 or more channels
   (about 200,000 words) for the lingo numbers to settle.
4. **Fetch, group by group:** `PIPE tools/script/human_corpus.py fetch <id> <id> ... --group voice`, then `clean` and `list`. Captions
   only, never the video: yt-dlp with a spare account's cookies (`MEDIA/secrets/yt_cookies.txt`, which the creator exports; the chat
   never opens it), a few seconds between videos, and it stops at the first sign-in or bot prompt. The texts land in
   `MEDIA/script/human_corpus/text/`, one per video with its channel, title, date and group.

### 1.2 The calibration set (the gate's humans, `tools/script/judge_panel.py`)
`PIPE tools/script/judge_panel.py pool calibration --human <id>#1 <id>#1 <id>#2 ...`: about 28 human passages of about 160 words:
about 9 scripted narrations from before 2022, 8 creators talking, 7 of the niche's voice-over channels and 4 recent documentaries.
Every gate puts each of our sections alone among 7 of them.

**Check the judge once, before the first gate.** The chat writes 10 known-AI passages from a plain fact list with a plain "engaging,
conversational YouTube narration" brief (one per line in a text file) and pools them with the calibration humans in a check set:
`pool check --human <the calibration ids> --ours controls.txt#para@ai_control`, then `packets check --size 13 --reps 2`, a clean Opus
judge on every packet (`brief check <packet> --judge opus_clean --clean`), `score check`. The judge works when it separates the AI
controls from the humans (AUC near 1.00), the same passage in two packets gets about the same number (test-retest r near 0.9), and the
humans land where the audit found them: scripted and talking creators about 0.15-0.25, a niche's voice-over 0.3-0.4. The gate keeps
0.47 as its pass line and prints the humans of the same packets beside every result, so the bar is always read against this niche's
own people.

### 1.3 The pair-test sets (style only, `tools/script/pair_test.py`)
In `MEDIA/script/panel/<set>/`:
- `content.json`: 6-12 passages of about 160 words from the corpus (different creators, mostly the `voice` group), each cleaned by
  hand of caption noise only (misheard words, stutters; every other word kept), each with its content written as neutral notes in
  order ("points": views, jokes and first-person remarks are points too, so ours says the same things). The writer under test gets
  only the points and writes one passage per line, in the content's order.
- `validation.json`: pairs of two different human creators on the same content (the same story told by two channels). Their "first
  one picked" share must sit near 0.5-0.6: measured, it averaged 0.60 but unevenly (0.26-0.82), because the judges call the messier
  speaker human, so a clean human loses to a messy one too. The floor for two humans is about 0.5-0.6, not 0.5 on every pair.
Then `pair_test.py make`, a clean judge per packet (an Explore agent with model opus, then sonnet in a new order; the prompt from
`pair_test.py brief`; save each answer as `<packet>__<judge>.json` in the set's `verdicts/`), and `pair_test.py score [--features]`.

### 1.4 The lingo and the niche's own words
- **The lingo study:** `tools/script/lingo_corpus.py` (the niche's captions in `MEDIA/script/lingo/`, the creator's own words in
  `MEDIA/script/lingo/creator/`: their interview answers and messages, blocks of 40 words or more) and
  `tools/script/lingo_measure.py` (the words and 2-3-word phrases the niche's creators use far more than the scripts, and the reverse,
  ranked by a z-score so a rare word doesn't top the list by luck; then slang, fillers, and how numbers, dates and people are said).
  The result goes into `kb/LINGO.md`; run it again every few videos.
- **`tools/script/niche.json`:** filled at setup and kept as reviews come in: `niche` (a few words for the judges' brief), `names`,
  `subject_names` (its rate is checked: real creators say the main name about 1.35 times per 1,000 words), `things`,
  `audience_roles`, `site_kinds`, `nerd_words`, `flagged_lines` (each stock line the creator flags: it fails the script gate from
  then on), `channel_lines` (the channel's own intro, sub ask and sign-off), `universal`, `sign_off_words`, `source_names`,
  `gloss_nouns`.
- **After the first few gates:** `PIPE tools/script/tell_lint.py --validate` (does the lint's flag count still track the judge in
  this niche?).

## 2. Two worked examples

**Why it works (the research behind the study).** Expert readers of model text (five heavy users of chat models, by majority vote)
got 299 of 300 right, paraphrased and "humanized" text included; their clues: vocabulary, lists of three, overly clean grammar,
blandness, over-explaining, formulaic conclusions (Russell, Karpinska, Iyyer, ACL 2025). The judges used here behave like those
experts (AUC 1.00 on known AI), so surface tricks are off the table. Instruction-tuned models use about 5.3 times the
present-participle clauses and 2.1 times the nominalizations of human text (Reinhart et al., PNAS 2025); model essays carry fewer
stance and hedge markers (Herbold et al., 2023); model help makes different writers' texts alike (Doshi and Hauser, 2024); given
examples, models fail to imitate a person's informal style (Wang et al., EMNLP Findings 2025); and a model's fingerprint survives
rewriting, translation and summarising (Sun et al., ICML 2025): part of it is in what is said, not how. What the judges name on the
human side: a first-person research trail, reaching out to someone, personal jokes, sarcastic asides, a self-interrupting gag,
tangled spoken syntax, non-native phrasing, the niche's own stock clichés, a personal memory. A person with quirks and a stake is in
every one.

### 2.1 The style method: the spoken edit
What the edit does, in the order the numbers rank it: more small glue words and fewer content words ("just", "you", "this", "that",
"really", "pretty", "stuff"); the same plain words reused, not varied; longer sentences that run on with "and" and "so" and change
direction, with a real spread of lengths; shorter everyday words; no written constructions ("it's not X, it's Y", "here's the thing",
colon set-ups, neat closers, lists of three for rhythm); now and then a loose or redundant phrase or a self-correction. Inserting
stock phrases does not work (74%: "inserted fillers"). Measured with the pair test: explainer wording caught 79% of the time; a draft
then a separate spoken edit by a fresh agent 69-70%, and 59-60% against the niche's scripted voice-over (two different humans: 60%).
**The caveat:** judged again in a later round, the same edited text scored 79%, like the plain wording; inside one round every
wording method sits within 4 points of the others. Good practice for the ear, not a proven lever: the judges pick humans by
live-speech slips a script doesn't have. Check it with `tell_lint.py <script.md> --style` (`--per-para` for every paragraph's gaps).

Example (a home-coffee channel; written for this file):

Draft:
> Most home grinders struggle with espresso. Their burrs are small, which makes fine adjustments difficult. A change of a few
> microns can turn a sour shot into a bitter one. That is why serious hobbyists spend more on the grinder than on the machine.

After the spoken edit (a fresh agent, its own pass):
> So most of the grinders people have at home just aren't really made for espresso, the burrs are pretty small and you can't really
> make the tiny changes you need, and with espresso a tiny change is the whole thing, you move the dial one click and the shot that
> was sour is bitter now, or on some of them it's not even a full click. And that's why people who are really into this stuff end up
> spending more on the grinder than on the machine.

What changed: glue words in ("so", "just", "really", "pretty", "this stuff", "you"); the same plain words reused ("tiny", "really")
where the draft varied them ("fine adjustments", "a change of a few microns"); one long sentence that runs on with "and" and turns,
with a self-correction in it ("or on some of them it's not even a full click"); the written "which makes" and the formal "That is
why" gone; the exact microns moved to the screen; the paragraph ends on the fact, with no closer. The facts are the same four.

### 2.2 The content check: the creator's view in the section
**The finding, in one line:** the blind judge reads who chose and ordered what's said. A real person's view running through a section
takes it from 0.55-0.65 to 0.20-0.45 (human level); on a section with no view of the creator's, no way of wording it moved the clean
judge below about 0.55 (about forty-six methods). So: map their views onto the sections first, write each section lean with their view
in it, lint the named giveaways, gate each section alone (`standard/SCRIPTS_AND_PACKAGING.md` section 1, "The content method").

Example (a fast-food channel; written for this file to show the change; the measured sections it mirrors went from 0.55, called AI,
to 0.35, called human):

Before (the explainer way):
> The chain's sales were falling that year. What customers wanted most was the spicy chicken wrap, a tortilla filled with fried
> chicken and hot sauce, which the chain had cut two years earlier. In February the chain said it would return in the spring, and in
> May it posted: "Good things take time." The chain's marketing chief later admitted that sales "dropped in every region" that year.
> To fill the gap, the chain ran a new limited item almost every month, mostly holiday desserts like a pink shake for Valentine's Day
> and a pumpkin pie in the fall. The wrap finally came back on October 2nd.

After (the creator's interview answer in `OPINIONS.md`: the wrap was the best thing on the menu, and why; written in our words):
> The chain's own marketing chief said later that sales "dropped in every region" that year, and the one thing people kept asking
> for was the spicy chicken wrap, which they'd cut two years before. And for me that wrap was the best thing on the whole menu, I
> used to get two of them after practice every Friday, and nothing they put out since came close, the new stuff is fine but it's just
> not the same. But they dragged it out. First it was coming back in the spring, and then in May there was a post that said "good
> things take time". In the meantime there was a new limited item almost every month, mostly desserts for the holidays, a pink shake
> for Valentine's and a pumpkin pie in the fall. The wrap was back in October.

What changed: the creator's view is in it, in the first person, with its reason; the section starts on the most telling fact (the
chief's admission) instead of a framing line ("sales were falling that year"); the gloss on "wrap" is gone (everyone knows what a
wrap is); the date is said once, plainly; the paragraph doesn't close on a line. What still happens before the voice: the
`OPINIONS.md` check (a phrase that keeps the creator's spoken wording, "after practice every Friday" if that is how they said it, is
said another way), every memory and feeling in it is one they gave, and any turn that reads translated or odd goes back to plain
English.

The measured test's other sections: with the creator's view in them 0.60 -> 0.43, 0.65 -> 0.45 and 0.64 -> 0.40; the six fact-only
sections 0.62 -> 0.60 (the creator said nothing about them, and nothing else moves the judge).

---

## 3. The patterns

### 3.1 Hooks

**H1. News: say what's new, plainly.** No clever angle, no side story: the thing itself, and that it comes with a lot ("The full
menu for the new place is out, and it comes with prices nobody expected."). Not those words, but that core. Timeless wording still
holds: never "just" meaning recently.

**H2. Opinion or hot take: a claim people want to fight, in a few words, with the answer held back.** The first words are there to
hook: say something that triggers people, in a good or a bad way (both work). A hot take ("The most copied pasta recipe online is
wrong."), drama ("The two biggest bakers online aren't talking anymore, and it started with one croissant."), a debate ("Is a
twenty-dollar knife really worse than a three-hundred-dollar one?"), an explainer for everyone ("One bad harvest in one country sets
the price of every coffee you buy."). Bait is welcome when it's paid off.

**H3. The hook never contains its own answer.** A hook gets people in and keeps them; the punchline is stretched across the video.
"The most copied pasta recipe online is wrong. It uses way too much water." gives the answer away, so people swipe: the hook is the
first sentence alone, and the water comes at the end. For a twist: treat the claim as true at the start, built on real facts, and the
"but" comes at the very end.

**H4. A hook that only describes the picture is not a hook.** "Here's the kitchen of the city's oldest restaurant" describes; "This
kitchen has one rule that gets new cooks fired on their first day" makes people curious. A promise works too: "and I'll show you
exactly where it is at the very end" keeps people to the end.

**H4b. Edge them to the end.** When people want to do the thing (try a free tool, find a place), keep talking about what's possible,
in the present tense, without saying what it is or where to get it: no name, no site, no steps; the catch only in the last lines.
The people who want it stay to find out how.

**H5. Short and fast, the voice on frame 1.** The hook is one short sentence, done in 2-3 seconds, the voice from the first frame. It
names what people know and the widest frame (`standard/SCRIPTS_AND_PACKAGING.md` section 2, "The hook"), which isn't always the
subject's own name first.

### 3.2 For a casual viewer, not the niche's insiders

**M1. Background in a few plain words; history in one sentence, then the news.** Never assume people know the background: a few
seconds of it lets them follow. Three lines of backstory before the news is too much: give it in one sentence (or one quick rundown,
said as one) and move on to what's happening now. Where the history is the topic, it is told in full.

**M2. The names and details the viewer needs, nothing more.** A person who matters gets their name and a plain role; someone viewers
don't know, whose name adds nothing, is said by company and job ("the owner of another big grocery chain", never a name nobody has
heard of with their company spelled out). A source everyone already saw needs no credit in the voice ("everyone who saw the ad saw the
price", not "a news site spotted the price"); a source is named in the voice only when it is the reason to believe the claim,
or when its own material is what's shown.

**M3. One crazy-sounding number, no units, no mechanism.** "The first model took eight minutes a cup and this one takes fifteen
seconds" is a sum for the viewer to do; "this one is about thirty times faster" just sounds crazy.

**M4. Simpler words, always; say the plain reason.** "due to supply constraints" -> "because they couldn't get enough parts"; "you're
on a limited timeline" -> "you only have two days".

**M5. Titles for casual viewers too.** A date the niche knows means nothing to everyone else: name the thing. Niche topics work for
anyone when the title and the content are interesting and easy to follow. Bait is wanted (`standard/SCRIPTS_AND_PACKAGING.md`
section 6).

**M6. The widest frame in the hook; the niche inside it.** Reach as many people as possible: a hook about the niche's one big name
already loses everyone who doesn't care about it. Make the video about the story everyone gets ("a free program that turns any laptop
into a recording studio"), with the niche's big name as the hype beat in the middle.

**M7. No number the viewer has to decode.** A number stays only if it lands with nothing explained ("a burger that costs twenty
dollars"); a per-unit value, or a then-and-now that needs the mechanism to make sense ("one share in the club was worth two hundred
dollars, and now it's worth three"), is out.

### 3.3 Human YouTuber phrasing, not AI phrasing

**A1. No topic-fragment questions ("X? Y.").** "Their reason? Costs." / "The result? A disaster." is a very AI way of talking: be
literal and explanatory, the way you'd talk to a friend ("They say it costs way more to make now."). A full sentence that voices the
viewer's thought is fine ("You might be thinking this is just about the price", "So it should still count, right?"); a bare topic
plus "?" and then the answer is the tell.

**A2. No stock phrases and no announcer lines.** AI-sounding: "everyone's losing their minds over", "and yeah, that's the energy",
"and the whole internet instantly went", a critic's label as a joke ("Lazy design."), "and nothing you don't", "and that meeting got
wild", "here's a detail I love", "so think about what that means" (a close like it on every claim), "and the funny part is". A
writerly turn ("... and that's the smallest way X is going to change Y") is the tell: say the next thing plainly. A line that
announces the next line (it's wild, it's crazy, here's the funny part) is out: say the thing itself. If a line sounds like a headline,
a slogan or a reviewer, rewrite it as what a person would say to a friend.

**A3. Direct and current, not coy or old-fashioned.** "a rather interesting outfit, if you know what I mean" sounds old and nerdy:
say what the outfit is, plainly (inside the safe-words rule, 3.8).

**A4. Don't make a plain fact sound special; tell the cool part.** "and the screen actually dims" (said as if it were special) ->
"the old model's screen had one brightness; on this one it dims on its own as the room gets darker". A fact worth mentioning that
isn't special is said plainly.

**A5. Say it the way the creator would.** A countdown in exact days -> "not even two months away". The creator's own phrases are
lessons in structure, never templates: learn how they build a sentence, never paste their lines.

### 3.4 Structure and pace

**S1. One point per line; never restate a point to make it stronger.** "The recall covers two million strollers. Two million. That's a
lot of strollers." -> "The recall covers two million strollers." Shorts don't like stalling: once the point has come across, go to the next.
Filler facts count as stalling too (a famous sales number nobody needs here). **Not a contradiction:** holding the *answer* back is
wanted (the art of stalling for retention: "You might be wondering why." before the reason). Delay the answer, never repeat the point.

**S2. Two points can carry 50 seconds.** Depth on one topic beats a list of topics.

**S3. Debates go back and forth:** an argument for one side, then the counter-argument, then the next one, never all of one side and
then all of the other.

**S4. One mood and one style, start to end.** A mysterious video stays mysterious: a meme joke in the middle ruins the vibe, and so
does a switch halfway from the mystery to a feature list.

**S5. End where the interest ends; cut dead tails.** If a viewer would swipe after a line, the video stops there. A long video has no
target length either way: never squeeze something in so it's shorter.

**S6. Timeless wording.** "Nothing is official yet" stops making sense the day it's official; "the menu drops today" is wrong
tomorrow: word things so they are true before and after.

**S7. A pointing word sits right after what it points to.** A "he" or an "it" whose person or thing is three lines back is lost: move
the line right after the first mention.

### 3.5 Opinions, theories, content

**O1. On the viewers' side, and say "I".** Never so neutral that nobody is in it; the creator puts themselves into lines ("including
me"); predictions are said boldly ("my bet is ..."), never "but who knows".

**O2. Theories must sound plausible, and be serious.** Only theories with something real behind them; more of them is better when each
is plausible; read the evidence fairly (a picture that seems to break a theory may confirm it once you look at the whole of it).
Jokes, puns and number coincidences are not theories.

**O3. Content from what people really ask, never made up.** The questions a video answers come from the research (what people
actually search, ask in comments and forums), never a forced question nobody asks.

**O4. News: only what's new; never overclaim who or when.** The narration is new too, not only the pictures. Say exactly what's known
("there's a pop-up shop going up on the main square right now"), never more ("the company is opening a store" when nobody said who's
behind it, "it opened days ago" when it opened this morning). Be specific about the now: what is actually there right now (what's on
offer, what it costs, what they say the money is for), not the history around it.

**O5. The viral angle, not the fact checker's.** Pick the hype or drama angle (a race, a side to take); keep every fact true but
framed the exciting way, and leave out the deflating details nobody needs.

**O6. No hedges, no suspicion.** News from the community is told straight: no "reportedly", no "nobody confirmed who did it", no
caveats about what we can't prove (`CLAUDE.md` office rule 6).

### 3.6 Jokes

**J1. A joke only where something is actually funny; a fact plus a real question beats a forced joke.** "and that's when I knew I'd
be living there all summer" is a weak try at humour: say the fact, and maybe the real question it raises ("how long would that even
take?"). Calling something "kind of hilarious" (with a laugh) when nothing about it is funny is out.

**J2. A joke is a person reacting, never a critic's label.** "A gym with a donut shop in the lobby. Bold choice." -> "Why is there a
donut shop in the gym lobby? I'd walk in for the donuts and walk right back out."

**What lands:** a callback; a reaction in the creator's own manner; the plain-word euphemism the audience itself uses; an everyday
comparison ("like charging steakhouse prices for a sandwich"); a short, dry line that ends the video. **What doesn't:** a forced joke,
a meme reference that breaks the mood, a critic's label, "and the whole internet instantly went", "that's the energy", "which is kind
of hilarious" plus a laugh, "you know exactly what I mean".

### 3.7 Endings and loops

**L1. If it loops, the last line finishes into the hook, in words and picture.** An ending that makes sense neither as a loop nor as
an ending is the worst of both. A loop line runs on into the first line ("... and I don't think that's a coincidence, because" -> the
hook), and the frame after the last frame is the starting frame. A loop where the story allows; a real question for the comments is a
fine ending too.

**L2. The loop line keeps the same pace.** A pause before it, or a slowed sign-off ("let me know in the comments... because. I. need.
to know."), breaks the loop: write the last line so it can't be read as a slow sign-off.

**L3. Pointing to another video: one natural line** ("If you want the full story behind it, it's in this video.").

**L4. Long form: the sub ask at a real break, a real sign-off at the end.** A quick sub ask at a real break, not before about a third
of the way in, and never one that makes people feel the video is over; at the end the creator's sign-off, then a like ask and a
comment prompt (whether it helped, any questions, which get answered in the comments). An ending that just stops is too abrupt.

### 3.8 Words and the voice

**W1. Words YouTube won't like stay out, even by accident.** Read for accidental pairs (two harmless words that sound like a slur or
a threat together); "corn" for porn; a softer word where a sexual word would go; titles too ("wild" instead of "illegal"). Talking
about edgy things is fine; it can be edgy. **Censor, don't beep:** a word like "naked" is avoided, or covered with the bass-boom
censor creators use, never a beep.

**W2. Write for the voice.** Sentence ends that sound like ends ("... then the lights went out. Show over.", not a run of commas); a
list says "and" before its last item ("drums, guitars, lights, and smoke."); a word the voice keeps glitching on is reworded, not
retried; a line meant calm must not read as shouting (an exclamation mark or a word in capitals can make the voice scream).

**W3. The creator's rewrite is the script; the chat only fixes facts, and says so.** When the creator rewrites a line as script, keep
their words and change only what is false (a word for accuracy, a claim narrowed to who really said it), each change flagged in one
line. An answer they give as opinion in an interview is different: it is material, written new in our words
(`standard/SCRIPTS_AND_PACKAGING.md` section 1, "How to write it" 1). What they hand over from their sources is the story
(`CLAUDE.md` office rule 6).

### 3.9 The narrator in the picture: a shrug, not a declaration

Cringe: "And I'm absolutely going to be one of those people lining up at five in the morning." / "I'm definitely going to be one of
those people who tries every flavor."
A shrug: "Half the city is going to be in that line, me included." / "I'll probably try that too." / "I can see myself doing that."
Neutral, relaxed, plain.

---

## 4. Before -> after pairs (written for this file; each teaches one lesson)

**1. Backstory and a number nobody can decode** (a personal-finance channel)
- Draft: "If you don't know, the fund started in 2015 as a small club for teachers. Then it opened to everyone in 2019, and in 2021
  it changed its name." / "Back then one share was worth two hundred dollars, and now the whole new offer works out to about twelve
  dollars a person."
- The note: three lines of history before the news is too much; a per-share value then and now means nothing to someone who doesn't
  know how the shares work; and it still doesn't say what's going on right now.
- Final: "The fund that started as a teachers' club now wants every member to pay a yearly fee to stay in." Then what is actually on
  the table: what the fee is, what you get for it, what they say the money is for.
- Lesson: M1, M7, O4.

**2. The casual viewer's payoff first** (a tech channel)
- Draft: "Developers online are building a free app that turns an old laptop into a home media server, and a post about it with
  over a million views says it's nearly finished."
- The note: the post and its views are nobody's payoff; look at it as a casual viewer: what excites them is what they get.
- Final: "There's a free app that turns the old laptop in your closet into your own streaming service, and it's nearly finished." /
  "So instead of paying for three subscriptions, you might not need any."
- Lesson: M6, O5.

**3. A hook that's about something else** (a music channel)
- Draft (hook): "The band once recorded a whole album in a lighthouse to get the sound right."
- The note: a nice side fact isn't the hook; the hook is what's new.
- Final: "The band's first new song in six years is out, and it came with a lot of news about the album."
- Lesson: H1.

**4. A name nobody knows** (a grocery-business channel)
- Draft: "And the head of Brightfield Provisions said they plan to try the same checkout-free stores in their own regions next
  spring."
- The note: almost nobody knows that company; leave out the details and say what matters to the viewer.
- Final: "And the owner of another big grocery chain already said they're trying the same thing next spring."
- Lesson: M2.

**5. The question rhythm** (a car channel)
- Draft: "Their reason? Parts cost more now. But the best part? The CEO doesn't even drive."
- The note: a topic plus "?" and then the answer is the AI rhythm.
- Final: "They say parts cost way more now, so the cars have to cost more too." + the creator's take: "And if a new car costs as much
  as a small house, I'm driving mine until it falls apart, and I really don't think I'm the only one."
- Lesson: A1, O1.

**6. The proof line, with an everyday comparison** (a fitness channel)
- Draft: "And it's already happening. One gym chain charges ninety a month."
- The note: said the way the creator would say it, it carries a comparison and a verdict.
- Final: "And you can already see it, one chain is charging ninety a month now, which is like paying hotel prices to sleep on a
  bench."
- Lesson: A5, J (an everyday comparison).

**7. An ending that loops** (the same Short)
- Draft ending: "So if this works, your gym might cost ninety too. Would you pay it?"
- The note: the Short loops, so the last line has to run into the hook.
- Final: an opinion beat in the creator's manner ("Honestly, half these places can't even keep the showers working.") and then
  "And that's why it's so annoying that" -> the hook: "Your gym might start charging ninety a month."
- Lesson: L1.

**8. A boring ending and a dead tail** (a kitchen-gadget channel)
- Draft: "So that's the new kettle. It comes out in March, and we'll see how the reviews turn out."
- The note: boring, and the last half-sentence is a dead tail.
- Final: "It's a kettle with Wi-Fi. For three hundred dollars. I need one immediately." (and the video stops there)
- Lesson: J2, S5.

**9. A word the voice can't say** (a travel channel)
- Draft: "Flip-flops. On a glacier. Unbelievable." (the voice glitches on "Unbelievable" in every take)
- The note: reword the line instead of retrying the word; the fragments were the AI rhythm anyway.
- Final: "This guy is hiking a glacier in flip-flops, and his toes are just out there."
- Lesson: W2, A1.

**10. Who spotted it, and a stock close** (a home-appliance channel)
- Draft: "A tech site noticed the new oven has a camera inside, so yeah, priorities."
- The note: everyone who looked at the oven saw it, the site adds nothing; "so yeah, priorities" is a critic's quip.
- Final: "The new oven has a camera inside."
- Lesson: M2, A2.

**11. Four flagged lines in one review** (an explainer)
- "this is everything you need to know about it, and nothing you don't" -> "this is everything you need to know about it, from zero"
  (the add-on makes the listener stop and work out what it refers to).
- "the dog gets a little bow tie, which is kind of hilarious." -> "the dog gets a little bow tie." (nothing about it is hilarious)
- "because you're on a schedule" -> "because the store closes at six" (the plain reason).
- "Nobody knows the opening date yet, so we'll find out soon." -> "Nobody knows the opening date yet." (stop there)
- Lesson: A2, J1, M4, S5.

**12. A filler fact in a debate** (an electric-car channel)
- Draft: "Electric cars might be the last cars you ever buy." ... "And the first electric car sold in this country, back in 1997, is
  still on the road."
- The note: the hook should be the argument people are actually having; the 1997 car stalls.
- Final: a hook people want to fight about ("Half the people who bought an electric car this year want a gas car back."), then the
  lines going back and forth: for, against, for, with the creator's side said plainly.
- Lesson: H2, S1, S3.

**13. A boring first line** (a phone channel)
- Draft: "The new phone comes out in March, and it already looks so good that a lot of people think they won't need another one for
  years. I honestly think that's wrong."
- The note: the first words are boring; say something that triggers people.
- Final: "This is the most overrated phone of the year."
- Lesson: H2.

**14. A hook that answers itself** (a baking channel)
- Draft: "The famous no-knead bread recipe doesn't work. Because nobody waits the full eighteen hours."
- The note: the hook already gives the punchline away.
- Final: "The famous no-knead bread recipe doesn't work." The eighteen hours come in the last lines.
- Lesson: H3.

**15. A stock phrase and a nerd number** (a phone channel)
- Draft: "And I know, everyone's losing their minds over how sharp the new screen looks, but we've been here before." / "The old one
  had 326 pixels per inch and this one has 460."
- The note: the stock phrase is AI; the pixel numbers are too nerdy.
- Final: "And yes, the screen looks amazing, but the last three phones looked amazing too." / "This one packs in about forty percent
  more detail, and your eyes can't even see most of it."
- Lesson: A2, M3.

**16. Repeated fragments** (a product-review channel)
- Draft: "The price? Too high. The size? Too small. The color? Gray."
- The note: three topic fragments in a row: the AI rhythm and a triplet at once.
- Final: "It costs way too much for how small it is, and it only comes in gray."
- Lesson: A1, tell 4.

**17. A line that breaks the mood** (a mystery Short about old photos)
- Draft: "Coincidence? I think not."
- The note: a meme line in a mysterious video ruins the vibe; keep going in the same style with the next find.
- Final: "But the clock in the background shows a different time in every one of these photos."
- Lesson: S4, A1.

**18. Sentence ends for the voice** (a concert channel)
- Draft: "... then the lights went out, show over." / "... drums, guitars, lights, smoke. A concert with no crowd would break that."
- The note: the voice runs "show over" on without an ending, and "smoke" sounds unfinished.
- Final: "... then the lights went out. Show over." / "... drums, guitars, lights, and smoke. A concert with no crowd would break that."
- Lesson: W2.

**19. A drama hook and timeless lines** (a film-news channel)
- Draft: "The magazine put its big story about the new film behind a paywall, and now it's reportedly free." / "... the story drops today,
  but only for subscribers." / "Nothing's official yet, but readers are already calling the director the good guy."
- The note: the hook needs drama; "reportedly" is a hedge; "today" and "nothing's official yet" won't make sense next week.
- Final: "A twelve-page story about the new film is locked behind a forty-dollar subscription, and the director is not happy about
  it." Then what happened, told straight, with the creator's guess as a guess ("my guess is so many people tried to read it at once
  that the site just broke").
- Lesson: H2, O6, S6.

## 5. Learning the creator's way of talking

**Where their speech is:** the setup interview (`creator/interview/round-01.md`), every `videos/*/OPINIONS.md` answer, and their
messages to the chat. Read them raw: the ums, restarts and dictation slips are not the pattern; the order of their thoughts, their
connectors and their comparisons are. When they send a dictated sample of how they imagine a video ("not the script, just how I
talk"), it is a representation of their talk, never the script: learn its order of thoughts, its connectors and its comparisons, and
write the script new.

**The shapes to look for** (how people argue out loud; collect the creator's own version of each into `creator/PROFILE.md`, "How they
talk", and learn the structure, never paste the lines):
- **Answering a claim with a question back, then a flat verdict:** "How is that expensive? It's normal."
- **Taking a claim to where it lands, then dismissing it:** "So they're saying a cheap knife is a scam. All right."
- **Granting what's fair before pushing back:** "This one I actually agree with. It looks great. But you can't call it practical."
- **Putting themselves in it, plainly:** "Me personally, I cook like this every day, and I'm not a chef."
- **The flip that shows a critic can't be pleased:** "If it was cheaper, they'd call it cheap junk."
- **Quick comparisons with a famous name:** "like he thinks he's a race driver".
- **Short closers:** "That's all there is to it." / "It's that simple."
- **Openers:** "I mean, ...", "Well, ...", "In my opinion, ...", "At the end of the day, ...".
- **Scale in plain words:** "probably like half the people I know".
- **Swearing:** in a chat message as emphasis on their own feeling; never in the voice.

The script uses these as the creator would, where they would, never as devices laid on top (a planted device is the next tell:
`standard/SCRIPTS_AND_PACKAGING.md` section 1, tell 7).

## 6. Keeping this file current

- Every verdict of the creator on a script or a line, passed or flagged, goes into `cases/SCRIPT.md` the same turn, with the line it
  draws.
- A correction that teaches a new pattern becomes a pattern in section 3 and a before -> after pair in section 4, made from the
  creator's own case (it replaces a written-for-this-file pair that teaches the same lesson); the rule itself goes into
  `standard/SCRIPTS_AND_PACKAGING.md` or `rules/`, replacing what it contradicts.
- When the creator approves a script, `cases/SCRIPT.md` names it and what it is a reference for, and section 0 point 1 points there.
