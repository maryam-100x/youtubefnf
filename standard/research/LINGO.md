# Lingo: how to learn the way a niche's real creators talk, from their captions

*The question: how do the niche's real YouTubers, the creator and the creator's scripts phrase things, and how is a script brought
to the niche's spoken lingo without inventing it? The only way to learn it is to listen: to the creator speaking and to the niche's
real creators speaking. Nothing is invented. The aim is to understand the general lingo and how sentences are built, not to paste
phrases. This file is the method, with what a first pass of it found in one niche. The creator's chat runs it on their own niche, and
its results go to `kb/LINGO.md`.*

*Read with:*
- *`standard/research/LINGO_MEASURED.md`: the word-level measure that follows this first pass.*
- *`standard/research/HUMAN_SCRIPT_STUDY.md`: the blind tests. Where they refine a lesson here, §8 says so.*
- *`standard/SCRIPTS_AND_PACKAGING.md` and `standard/SCRIPT_TRAINING.md`: the method in use.*
- *`creator/PROFILE.md`: how the creator talks.*

*Creators in the niche we studied are described by kind, not named; creators outside it keep their names. Every example line is a
neutral stand-in with the same feature as the line it replaces.*

---

## 1. Build the corpus

**Who goes in:**
- **The niche's real creators:** about a dozen of the channels the creator's viewers also watch (the ones the creator admires,
  `creator/PROFILE.md` "Taste"), across kinds: personality creators talking to the camera, scripted voice-over channels, documentary
  narrators, and one or two top creators of the niche.
- **The creator's own words:** messages they typed or dictated, and interview answers. This is how they talk.
- **The scripts:** the VOICE lines of every finished script.

**The steps** (all files in the media root, never in git: creators' words stay on the PC):
1. Captions of the creators' videos (captions only, never the video):
   `yt-dlp --write-subs --write-auto-subs --write-info-json --skip-download <url>`, saved into `MEDIA/script/lingo/`
   (`*.vtt` + `*.info.json`; rolling auto captions are de-duplicated by the tool).
2. A plain transcript where a top creator's captions are poor (e.g. a speech-to-text run of the video), one file per video in
   `MEDIA/script/lingo/transcripts/*.txt`.
3. The creator's words as `MEDIA/script/lingo/creator/*.md|*.txt` (blocks of 40+ words count).
4. Run it:

       PIPE tools/script/lingo_corpus.py [--ours 12,13,...]

   It writes `MEDIA/script/lingo/corpus/<name>.txt` (the creator's words as `CREATOR_dictated_.txt`, which `lingo_measure.py`
   reads) and prints the comparison table of §2.

**Caveat:** auto captions carry no punctuation, so sentence numbers exist only for sources that have it: the scripts, the creator's
words, manual captions and speech-to-text transcripts. The others report word rates only.

**The bigger corpus** for the blind tests is `tools/script/human_corpus.py` (about 100 videos in groups). `tools/script/lingo_measure.py`
ranks words and phrases across both corpora (`standard/research/LINGO_MEASURED.md`).

## 2. The numbers to read

For every source, the table gives:

| Column | What it shows |
|---|---|
| words / sentence | how long a thought runs before a full stop |
| contractions / 100 words | how spoken the register is |
| I / you / we per 1,000 words | who is in the room: the narrator, the viewer, the two together |
| questions per 1,000 words | real thoughts said aloud (or the AI's self-answered beat) |
| announcer lines per 1,000 words | phrases that announce the next line ("here's the crazy part", "this is where it gets", "not just X, it's Y", "and honestly", "let that sink in"...) |
| top sentence openers | the habits of each speaker ("And", "Then", "So") |

**What the first pass measured** (one niche: about a dozen reference creators, a top creator's speech-to-text transcript, 127,786 of
the creator's dictated words, and five of our scripts):

| Source | words | words/sentence | contractions /100 w | I /1k | you /1k | we /1k | questions /1k | announcer lines /1k |
|---|---|---|---|---|---|---|---|---|
| a top creator in the niche (speech-to-text) | 4,724 | 12.6 | 4.4 | 1.1 | 7.0 | 3.0 | 7.0 | 0.21 |
| a personality creator (manual captions) | 1,645 | 12.8 | 4.6 | 22.5 | 29.2 | 4.3 | 12.2 | 0 |
| a list-video creator | 3,278 | 14.0 | 2.7 | 7.0 | 38.1 | 0.9 | 3.7 | 0 |
| a scripted voice-over channel | 2,550 | 14.1 | 2.6 | 1.2 | 10.2 | 0.4 | 2.4 | 0.39 |
| fern | 8,652 | 13.8 | 2.0 | 5.9 | 9.0 | 2.5 | 3.7 | 0 |
| LEMMiNO | 2,408 | 17.2 | 0.3 | 5.0 | 3.3 | 2.9 | 5.4 | 0 |
| Nexpo | 6,510 | 17.4 | 2.9 | 7.4 | 7.7 | 5.1 | 4.8 | 0.15 |
| a faceless channel its viewers called AI narration | 1,149 | 13.5 | 2.7 | 2.6 | 3.5 | 0.9 | **0** | **2.61** |
| five more channels, incl. Barely Sociable | auto captions | n/a | 1.3-3.5 | 0-14 | 1.3-12 | 0.7-7 | n/a | 0-0.41 |
| **the creator, dictated (127,786 words)** | | 20.5 | 3.4 | 22.9 | 29.1 | 8.9 | 3.8 | 0.13 |
| ours: Script B (a well-performing long video) | 1,837 | 18.4 | 3.4 | 3.3 | 4.9 | 0 | **0** | 0.54 |
| ours: an argument video | 2,594 | 14.7 | 4.9 | 3.5 | 12.0 | 1.2 | 5.4 | 0.39 |
| ours: a how-to video | 1,830 | 15.4 | 3.3 | 0.5 | 43.2 | 0 | 0 | 0 |
| ours: a long history video | 5,236 | 14.8 | 2.7 | 0.8 | 4.6 | 1.5 | 1.5 | 0.57 |
| ours: a breakdown video | 1,913 | 19.3 | 3.9 | 7.3 | 14.6 | 2.6 | 1.0 | 0 |

**The one number that separates:** announcer lines. Real creators run 0-0.4 per 1,000 words; the channel its viewers call AI
narration runs 2.6. Words a sentence does not separate (the AI-called channel 13.5, fern 13.8).

## 3. What the real ones do (read in the corpus)

Read the texts, not only the numbers. In the first pass:
- **Short sentences, scene-like, concrete** (the top creator: 12.6 words a sentence). A name, a number, a place, a verb, and no
  summary sentence: "And they expect arrests to follow shortly." "The parade is called off before it even starts."
- **Fragments as beats,** each carrying a fact: "A chance to properly see the new library." "Finally, in its place, a bargain-bin
  kettle."
- **Play-acting what people said or thought, without quotes:** "sorry, that's not happening, here's some more urgent work".
- **Deadpan asides on facts, not on announcements.** The joke is the next fact said straight.
- **Talking with the viewer:**
  - guessing out loud ("maybe a million, nah that's probably too high")
  - "you" when the viewer is in the scene (the list-video creator, 38 per 1,000: "if you ... at this point ...")
- **Questions only as real thoughts** (the top creator 7 per 1,000, the personality creator 12). Script B had none, which suits a
  claims video.

## 4. How the creator talks (read their own words)

From the creator's dictated words (the corpus file `CREATOR_dictated_.txt`), write into `creator/PROFILE.md` ("Their voice and
words"):
- their top sentence openers (the table prints them)
- how they start an opinion (one fixed phrase or several), and whether they commit to a guess
- how long their sentences run when they explain
- the comparisons they reach for (everyday ones, like a home kitchen next to a restaurant kitchen)
- where they swear (only in chat, or on camera too)
- how they think out loud and correct themselves
- how they grant a point before they push back ("This one I actually agree with ... But")

The structure is what transfers, never their phrases pasted in.

**What one creator's words showed:**
- **Explaining runs long and loose:** 20.5 words a sentence, against 12.6-17.4 in the creators' narration.
- **Opinions always start on the same phrase.**
- **Fillers run at about three times the narrators' rate** (`standard/research/LINGO_MEASURED.md` §2).
- So a creator's raw talk shows how their thoughts are built, and the narration takes it at a narrator's dose.

## 5. Our scripts against them (first read)

**Tells that a first read found:**
- **The best script read close to the top creator in places** (year stamps, small scenes, names). The tells there were subtler:
  - writerly irony built as a clause ("like that was the good news")
  - lines opening on "And" again and again (its top openers: "and the", "and in", "and that", "and a")
  - announcer phrases at 0.5-0.6 per 1,000 words, twice the real ones' ceiling
- **Script B had no questions and long sentences (18.4) but a fast picture:** the picture carried it.

## 6. Complaint kinds, and what `tools/script/script_lint.py` catches

A reviewer's lingo notes fall into a few kinds. Each kind gets a check where a check can work. Stock lines the creator flags go into
`tools/script/niche.json` (`flagged_lines`), and each one then fails the gate.

| Complaint kind | Caught by `script_lint.py`? | How |
|---|---|---|
| Sounds AI-written: "and honestly", "you can already see it happening", "that's the energy", "my favorite line", "they just got it wrong", "everyone's losing their minds", "lazy writing", "actually holds up" (about 40 such lines across long videos and Shorts in one pass) | Yes, by phrase | the announcer, stock-AI and filler rules. On one of our scripts it flagged exactly the two lines the reviewer had flagged |
| The self-answered "X? Y." beat (Shorts) | Yes | the topic-fragment rule. A top creator uses it rarely, with irony ("Her budget? Well, it was considerable."); the complaint is the mechanical use. Real questions to the viewer are fine (the personality creator: 12 per 1,000) |
| Vagueness: "a product that isn't even out yet", "one company", "a famous brand" (the most repeated complaint in one pass) | Partly | stock vague phrases only; a read is still needed for every "a man", "a company", "a song" |
| Hard-to-follow sentences | Partly | long sentences for the voice (over 45 words); a read for meaning |
| Lists that read like a list (one script opened 18 lines on "Then") | Yes | one opener on over 15% of lines |
| Self-insert boasts ("like I did", "one of the 31 million") | Yes, by phrase | the creator's opinions stay; boasts about the creator's habits go |
| Time-bound wording ("just dropped", "yesterday") | Yes | |
| Wrong or invented facts, nerd detail, a weak hook, the ending | No | a read against the footage and the rules; the lint can't judge these |

## 7. The practice: 30 lines rewritten

*The exercise: take 30 lines of the scripts (long form and Shorts), write the rewrite under each, and give the reason. Facts are kept
exactly as the original had them; nothing new is invented. The pairs below are neutral stand-ins (invented topics) that each keep the
lesson of the real pair. In the creator's exercise, the lines are their own scripts' lines.*

**Long form**
1. "And honestly, after the final, more companies are just gonna give people the day off, because if half your workers call in sick
   anyway, you might as well."
   -> "I think more companies are just gonna give people the day off. If half your staff calls in sick anyway, you might as well."
   *"And honestly," is a flagged cringe opener; the creator's own way to give an opinion is "I think".*
2. "And you can already see it happening. The band's half-hour concert film premiered on a streaming service, and it became the
   number one movie on the service worldwide, number one in eighty-seven countries."
   -> "And I'm not just saying that. The band's half-hour concert film went up on a streaming service, and it was the number one
   movie in eighty-seven countries."
   *Back the claim with the fact instead of announcing it.*
3. "...So I can totally see people walking laps around the new park listening to podcasts, like it's their actual commute. And I'm
   definitely gonna be one of them."
   -> "...I can totally see people walking laps around the new park with a podcast on, like it's their commute."
   *The boast goes (nobody needs to know it); the picture of the idea stays.*
4. "So yeah, that's how I think this eclipse is gonna take over the country. And on eclipse day, I'm definitely gonna be one of those
   thirty million people."
   -> "So that's how this eclipse takes over the country. Thirty million people, on the same day, all looking up at the same sky."
   *End on the strongest fact, not on the narrator.*
5. "The rival museum has been planning its show for twelve years, and it just got pushed to next year. Its curator literally said it
   was to avoid the attention buzz saw of this opening. Like, you've been working on a show for twelve years, and you're still scared
   to open in the same month."
   -> "The rival museum has been planning its show for twelve years, and it got pushed to next year anyway. The woman behind it said it
   was to avoid the attention buzz saw of this opening. Twelve years of work, and they still won't open the same month."
   *"just" dates it; "literally" cut; the joke is the fact said again, flat.*
6. A 44-word sentence naming a principal and a councillor who both spoke against a campaign:
   -> "The posters aren't even up yet, and the school's principal, Ana Ruiz, already came out against them at the bus stops. A
   town councillor, Paul Grant, even read one of the posters out in the middle of a council meeting."
   *Two sentences, each a name, a role and a deed.*
7. "Because ever since the company showed more of its new mascots, there's been videos and posts all over the internet saying the
   brand has gone soft, that it's corporate slop, and that the mascot is a joke."
   -> "Ever since the company showed more of its new mascots, YouTube and X have been full of videos saying the brand has gone soft.
   That it's corporate slop. That the mascot is a joke."
   *Name the platforms; the claims as fragments, one picture each.*
8. "And apart from that, in that clip, the cyclist is riding no-hands and waving at the crowd in the middle of a sprint finish,
   right on the line, where any rider could hit him."
   -> "In that same clip, the cyclist is riding no-hands, waving at the crowd in the middle of a sprint finish. Right on the line,
   where any rider could hit him."
   *The filler opener goes; one long sentence becomes a sentence and a fragment that carries a fact.*
9. "...Imagine them putting that ad out today. These people would lose their minds."
   -> "...Imagine the comments if the company put that ad out today."
   *"lose their minds" is a flagged stock line; "the comments" is a concrete picture.*
10. A 65-word list of everything that went wrong in nine years:
    -> "In those nine years, one of the two founders got locked out of his own kitchen. A second shop swallowed all the money. The
    baker behind every recipe walked away. A flood shut the old site for a whole winter. A rival copied the menu word for word. Half
    the staff quit in one summer. And three weeks before the reopening, the big oven caught fire."
    *A list becomes beats, one sentence per picture; "And" only on the last, as the climax.*
11. "...A big change, and sad in a way."
    -> (cut the last sentence; end on "something he'd worked on for twenty-odd years.")
    *A writerly feeling clause; the fact already carries it.*
12. "...The company's president called it an unprecedented third launch, like that was the good news."
    -> "A month later, the same blender comes out again, in a new colour. The same 2019 blender, on its third launch. The company's
    president called that unprecedented."
    *Deadpan: the fact is the joke; the ironic clause goes.*
13. "And some people at the company complained that it was too many cooks in the kitchen, that decisions took forever, and that the
    three of them didn't always want the same thing."
    -> "Some people at the company called it too many cooks in the kitchen. Decisions took forever, and the three of them didn't
    always want the same thing."
    *That script opened 30% of its lines on "And"; this one doesn't need it.*
14. "In March 2019, twelve days before it opened, Mark Ellis, the restaurant's head chef and the guy who wrote basically every
    menu, said in an interview that they'd been testing dishes until three in the morning."
    -> "Twelve days before the second restaurant opened, Mark Ellis, the man who wrote basically every menu, told an
    interviewer they'd been testing dishes until three in the morning."
    *"it" named; one subordinate clause instead of three.*
15. A 45-word list of a first report's details:
    -> "At the end of that month, a trade paper reports the first real details. A new town for the festival. Two headliners at the
    top of the bill. And a plan that started as three stages and got cut down to one."
16. "...And some of the questions they got stuck on were things like, if you go into a store for a drink, do you walk to the fridge,
    take it out, carry it to a till and scan it yourself? Or does the app just charge you when you walk out?"
    -> "...They got stuck on questions like this one. You walk into a store for a drink. Do you open the fridge, carry it to a till
    and scan it? Or does the app just charge you when you walk out?"
    *Real questions stay (they are the designers' own questions); the scene is set in short steps.*
17. Two sentences of 43 and 52 words about a chef's past:
    -> "The restaurant's own bio says the chef went to work on cruise ships to get away from a troubled youth. In this interview, he
    talks about getting into some trouble there and not leaving on the best of terms. To me, that sounds like he was dismissed.
    Basically, he got thrown off the ship. And with this many ship photos in the documentary, I think it covers his years at sea,
    maybe even the moment he got thrown off."
    *Long sentences become steps, and the theory is said as the narrator's own ("To me", "I think").*
18. "...or maybe it opens with the backstory, like the first film did with its prologue. Who knows."
    -> "...Or it opens on the backstory, like the first film's prologue. My bet is the prologue."
    *"Who knows" is the vague-future dip (a top channel in the niche ran it at 0.02 per 1,000 words); a theory is said with
    confidence.*
19. "Then a band on a green float with a spider-web paint job and gold trim. They're painted all over..."
    -> "A band on a green float, spider-web paint job, gold trim. They're painted everywhere, even on their faces, and the woman at
    the front of the float is filming everything on her phone."
    *That script opened 24% of its lines on "Then"; the picture already says "next".*
20. A 53-word sentence about a crowded street in the footage:
    -> "There's a marathon through the old town, and if you pause on any frame, the sidewalks are packed. A guy walking a pink poodle.
    A woman filming the runners on her phone. Someone with a suitcase. And every one of them is cheering for someone different."
21. "But I'm wondering how sharing a table even works. Like, do you go up to the host and ask her, is it where you sit when you first
    come in, or was this just staged for the ad? Or if she's already seated, can you just sit down?"
    -> "But how does sharing a table even work? Do you walk up to the host and ask? Is it where they seat you when you come in? Or was
    it just staged for the ad?"
    *Real questions to the viewer, one per beat, the way the creator thinks out loud.*
22. "Then the pilot climbs out onto the skid of a helicopter..."
    -> "The pilot climbs out onto the skid of a helicopter, way above the stadium, in the same outfit as on that helipad. So I think it's
    the same shoot, and this is the helicopter that lands behind him."
    *"Then" goes; the guess is said with its reason.*

**Shorts**
23. The hook: "This school has its own observatory, and that's not even the craziest part."
    -> "This school has its own observatory."
    *The hook names the thing and stops; "not even the craziest part" announces instead of delivering (the AI-called channel's
    pattern).*
24. "And that pan? Everything's bubbling over, butter's sliding off the steak, and the flame licks up the sides."
    -> "Everything's bubbling over, butter's sliding off the steak, and the flame licks up the sides."
    *The "X? Y." beat, a flagged AI pattern.*
25. "Honestly? It just looks like last year's model with a new case."
    -> "\"It just looks like last year's model with a new case.\"" (said as the critic's own words, their clip on screen)
    *Play-act what people said (§3), no "Honestly?".*
26. "Now think about what that means for the new model, because it only comes in two colours, and the last one took over a year
    and a half to get a third."
    -> "And the new model only comes in two colours. The last one took over a year and a half to get a third."
27. "And the craziest part is the shared mode: you and your friends can all edit the same playlist from different phones at the same
    time."
    -> "And it has a shared mode. You and your friends can all edit the same playlist."
28. "And what I mean by that is, the platform isn't really one shop, it's a place where sellers build their own shops, and the best
    ones make real money from it."
    -> "The platform isn't really one shop. It's a place where sellers build their own shops, and the best ones make real money."
29. "So if two out of three of the forty-eight million people expected to stream the finale on its first night do the same, that's
    over thirty million people not showing up..."
    -> "Forty-eight million people are expected to stream the finale on its first night. If two out of three do the same, that's over
    thirty million people not showing up..."
    *The number first, then the math: a viewer can't hold a conditional and a number in one breath.*
30. "So imagine the platform a few years from now, whole courses taught by its users, live classes every night, and people making
    real money just from what they teach..."
    -> "Now imagine the platform a few years from now. Whole courses taught by its users. Live classes every night. People making
    real money from what they teach."

## 8. What the exercise taught

These are the working lessons. Where the later blind tests (`standard/research/HUMAN_SCRIPT_STUDY.md`) refine one, the refinement is
part of the lesson.
1. **One fact per sentence, the length by meaning.** A list becomes beats, one per picture, with "And" only on the last item, as its
   climax. Fragments go in only when each carries a fact. The blind tests found that a narrow band of short, tidy sentences is itself
   a measured AI tell, so the lengths are a mix, never one shape.
2. **Opinions start the way the creator talks** (in the first pass, "I think" and "To me"). Then commit ("my bet is"); never "who
   knows" or "remains to be seen".
3. **No line that announces the next one.** The next fact is the hook. If a sentence only says "this is crazy", delete it.
4. **The joke is the fact said straight.** No clause that tells the viewer it's ironic ("like that was the good news").
5. **Name everything:** the product, the person and their role, the platform, the number. "It" and "a product" get replaced the first
   time; once the thing is the subject, "it" and "the <thing>" are what real creators say (`standard/research/LINGO_MEASURED.md`).
6. **Openers:** drop "Then" and "And" when the picture already moves on. "But" marks a turn, "So" a conclusion (but / therefore).
7. **No boasts about the channel;** the creator's opinions and theories stay.
8. **Shorts:** the hook is the name or the claim with no set-up; critics are quoted in their own words; numbers come before the math.
9. **Long-form scenes can be set with a date and a place inside a spoken clause** ("It's 2014, and at the company ..."). A sentence
   that opens on a bare date ("June 2016, the update ...") is a judged AI tell, counted by `tools/script/tell_lint.py`.
10. **Timeless:** no "just", "this week", "today".

Every script goes through `tools/script/script_lint.py` before it is voiced (`PIPE tools/script/script_lint.py <script.md>`), then a
read against points 1-10 and the creator's rules.
