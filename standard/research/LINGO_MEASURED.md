# Lingo, measured: the niche's real YouTubers vs the scripts vs the creator's own words

*The question: a script is more than what is said; it is also the lingo. Which words and phrases do the niche's real creators use
far more than the chat's scripts, and the reverse? This file is the measure, with the patterns it found in one niche that are not
about that niche: they describe how AI-written narration differs from human narration, and they are the starting expectations for
any niche until the creator's own corpus is measured. The niche's own word lists are the creator's chat's to build (`kb/LINGO.md`).*

*Read with:*
- *`standard/research/LINGO.md`: the method and the first pass.*
- *`standard/research/HUMAN_SCRIPT_STUDY.md`: the blind tests.*
- *`standard/SCRIPTS_AND_PACKAGING.md`: the rules in use.*

---

## How it is measured

    PIPE tools/script/lingo_measure.py [--groups talk,voice,tech,ref] [--top 60] [--min 8]

**The three sides:**
- **The human corpus:** `tools/script/human_corpus.py`, in the groups talk, voice-over, tech and the reference channels.
- **The scripts:** every `videos/*/script.md`'s newest VOICE lines.
- **The creator's dictated words:** `MEDIA/script/lingo/corpus/CREATOR_dictated_.txt`, written by `tools/script/lingo_corpus.py`.

**The method:**
- **Ranking:** words and 2-3 word phrases are ranked by the log-odds ratio with an informative Dirichlet prior (Monroe, Colaresi &
  Quinn 2008). That gives a z-score per item, so a word that is rare everywhere can't top a list by luck.
- **Rates:** the tool also gives rates per 1,000 words for named families: slang and hype words, fillers, and how numbers, dates and
  people are said. In the tables below, rates read humans / ours / the creator's.

**Caveats:**
- YouTube's auto captions write "going to" for "gonna" and drop most "um", so those two can't be compared.
- Some creators' English is non-native, which inflates "however", "simply" and "of course" on the human side.

**The corpus behind the numbers below:** 213,509 words of real creators (talk, voice-over, tech, reference channels), 44,568 words of
our scripts (every video's newest VOICE lines) and 129,325 words the creator dictated. Rates are per 1,000 words unless the row says
per 10,000.

## 1. What our scripts said far more than the creators (cut it back)

| Ours | humans / ours / the creator's | What they say instead |
|---|---|---|
| **the subject's full name** (the one name most scripts are about) | 1.35 / **6.46** / 1.99 | "the <thing>" 2.5 vs ours 1.5, "this <thing>" 0.6 vs 0.07, and "it". Five times their rate: a "say the name, never 'a <thing>'" rule had been applied to every line, not only where the line would be vague |
| exact numbers (digits and number words) | 17.1 / **34.9** / 13.0 | fewer numbers, and the one that matters; spelled-out figures like "a hundred and seventy" (ours 0.34, theirs 0) |
| "says / said", "<the maker> says", "<the maker> hasn't said" | 0.33 / **2.36** (says), 0.02 / 0.61, 0 / 0.27 | state what's known; quote who it's from when they're the origin |
| official full titles (of a release, a product video, an outlet, a parent company) | 0.02 / 0.76 (the most used one) | the short plain name ("the video", "the ad") |
| dates in full ("in October 2019", "March 3rd") | 1.4 / **3.3** / 0.1 | a date where it matters; otherwise "back then", "a few months later" |
| "literally", "honestly" (per 10,000) | 1.95 / **5.75**, 1.62 / **6.44** | they're the right words, used three to four times less |
| "the whole", "the exact same", "and if", "and there's", "the other one" | 0.12 / 1.12 ... | habits of ours, with no human pattern behind them |

## 2. What the creators said far more than our scripts (the lingo that was missing)

| Theirs | humans / ours / the creator's | Use |
|---|---|---|
| **"this"** (this guy, this is, look at this, this <thing>) | 12.8 / 3.8 / 6.1 | talking about what's on screen |
| "we see", "here we see", "we saw", "in the video" | 0.64 / 0.02, 0.10 / 0, 0.32 / 0 | the narrator watching with you |
| **"we", "we'll", "we've", "let's"** | 5.8 / 1.3 / 8.8 | the narrator and the viewer together ("we'll see", "we've seen") |
| the future: "will", "going to be", "there will be" | 3.2 / 0.6 (will) | guessing ahead out loud |
| qualifiers: "a little", "a bunch of", "quite", "it seems (like)", "a lot of" | 0.59 / 0.16, 0.30 / 0.11, 0.33 / 0 ... | loose, rough sizing |
| the niche's own plain words for what viewers see (its everyday nouns, and its "massive", "crazy", "insane") | each 2-5 times our rate (per 10,000) | the plain words the niche uses; the measure finds them in any niche |
| "dude", "you guys", "guys" (per 10,000) | 3.0 / 0.2, 1.1 / 0.2 | addressing the viewer, rarely |
| fillers and markers (like, basically, actually, pretty, I mean, you know, okay) | 15.3 / 11.4 / **46.8** | the creator's own rate was three times the creators': narration takes their words at a creator's dose |
| hedges (I think, I guess, I feel like, probably, it seems) | 3.6 / 2.4 / 11.6 | "it seems like" 0.15 / 0 / 0.09; a creator usually has one signature hedge (here 1.03 per 1,000) |

## 3. What a brief may expect, and the numbers didn't show

- **Heavy Gen Z slang is rare in real narration.** "cooked", "goated", "glazing", "W <company>", "mid", "it's giving", "lowkey": 0
  per 10,000 words in the 213,509 words of creators (the creator's own dictation: "cooked" 0.16, "lowkey" once). The real lingo is
  the plain vocabulary in §2, not slang. A slang word goes in only where the creator would say it, and once.
- **Report-speak can be gone from the scripts and they still read as reports.**
  - "notably", "it's worth noting", "additionally", "furthermore", "moreover", "significant", "crucial", "essentially": 0 in our
    scripts (the bans held). The creators use some of them (0.3-2.7 per 10,000, mostly the non-native and the experts).
  - The report-speak left was the structure in §1: says, full titles, exact numbers, dates. It was not those words.

## 4. How to use it

- **Write with §2's words where they're true,** and cut §1's habits back to the human rate.
- **Check with `tools/script/script_lint.py`.** It flags the subject's name over 3 per 1,000 words (the name comes from
  `tools/script/niche.json` "subject_names"), numbers over 35 per 1,000, "says" over 3.1 per 1,000, and definitions over 2.5 per
  1,000.
- **`lingo_measure.py` reruns the lists as the corpus grows,** and the niche's findings go to `kb/LINGO.md`.
- **The subject's name:** it opens a topic or goes where anything else could be meant. Once it is the subject, "the <thing>", "this
  <thing>" or "it". Never "a <thing>" where the name belongs.
