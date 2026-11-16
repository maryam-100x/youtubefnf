# Packaging craft: what wins titles in 2025-2026, what descriptions, hashtags, chapters and tags do, and how every video is packaged

*The question: by the evidence, what makes a YouTube title win the click and the watch time, what the description, hashtags, chapters
and tags actually do, and one repeatable process for packaging every video. Thumbnails are not covered here: they are the creator's
own work, and a title is written knowing the thumbnail it travels with. The creator's taste outranks any study: these findings are the
starting point, and YouTube's Test & Compare measures. Read with: `standard/SCRIPTS_AND_PACKAGING.md` (the packaging rules),
`standard/research/SHORTS_CRAFT.md` (Shorts), `standard/research/AI_TELLS.md` (wording that reads as machine-written).*

**How it was done:** ~25 web searches; pages read with curl (WebFetch where curl was blocked: vidIQ, Social Media Today, Simon
Willison); YouTube Help pages fetched at the time of research; for one niche, yt-dlp searches over 15 queries plus YouTube's own "sort
by views" filters (898 unique videos), metadata for 182 of the top 260 (§4 gives the method so it can be repeated in any niche).
**Grades:** A = primary or measured, B = method visible, C = opinion, a small sample, or a vendor selling the answer, D = anecdote or
incentivised. Every study below is correlation unless it says RCT.

---

## 0. The short version

| # | Rule | Evidence | Strength |
|---|---|---|---|
| 1 | **The idea is the lever; the styling is table stakes.** One idea a stranger gets in a glance, plus one thing they didn't expect. | Eden (507,478 videos): breakouts and flops look near-identical in thumbnail styling; the biggest gaps are outside it (video length, title specificity). Paddy Galloway: "familiar but unexpected". A well-performing long video of ours with a mainstream angle held 7.8% CTR on 2.5M impressions | Medium (B/C + our A) |
| 2 | **Titles: state it, never ask it. No "?" in long-form titles.** | In one niche we measured, 0 of the 62 top English titles of the last 90 days had a "?"; a 588-video study of the same niche: "?" 0.78×, lost in 9 of the 9 channels that used it | Medium-High (one niche) |
| 3 | **Title length isn't a lever. Write the clearest, strongest line; keep the hook early.** | Within-channel studies find nothing (ytgrowth r = 0.0046 on 28,947 videos; OverseerOS the same median 58 characters for breakouts and normal uploads); the niche study flat; the published "sweet spots" (30, 30-50, 70-100 characters) contradict each other | High that length is null |
| 4 | **Tension beats cheer: negative or conflict words, when true.** | RCT on 105,000 Upworthy headlines: each negative word +2.3% CTR, each positive word −1.0% (Nature Human Behaviour 2023); 1of10: negative framing +20%. In the niche measured, 7 of the top 20 titles carry a negative or conflict word ("Pathetic", "slop", "Fake", "DOOMED") | Medium-High (an RCT, outside YouTube) |
| 5 | **When the big channels share one template after a big event, be the specific one.** | Within a day of the biggest official announcement in the niche we measured, three channels all titled "Everything/Every Detail You Missed", and the biggest channel's packages were one template. The counter is one specific discovery as the promise | Medium (observed) |
| 6 | **Every long video gets Test & Compare with 3 *concepts*, and the test runs to YouTube's verdict.** | YouTube picks by watch-time share; tests run days to 2 weeks; early impressions skew to viewers who already know the channel. Four of our tests ended at 28-39% each; two were stopped after 3.5-5 h, so none gave a verdict | High (A) |
| 7 | **The first 30 s pays off the title.** | YouTube: the winner is the most watch time; clickbait is a high CTR with a low view duration. On two long videos of ours, retention fell from 74% to 52% at 0:23-0:41 and from 66% to 51% at 0:32-0:49 | High (A + ours) |
| 8 | **Shorts: the first frame and the topic are the package; the title barely matters.** | 99.9% of Shorts views come from the Shorts feed, where no thumbnail shows (YouTube's Shorts lead, January 2025); title features explain ~4-5% of Shorts lift (our study of 3,557 Shorts in one niche) | High |
| 9 | **SEO is a search-only lever: the title's words, description line 1, 3 hashtags, chapters; tags barely count.** | YouTube Help: tags "play a minimal role"; search ranks by relevance, engagement and quality. One of our videos got 5.3% of its views from search; another, titled on a debated search phrase, 21.9% | High (A) |

---

## 1. What YouTube itself says (grade A)

- **Test & Compare** (Help 16391400): up to 3 titles, thumbnails or title-and-thumbnail pairs; the one with the highest **watch time**
  wins; desktop Studio, advanced features; not for Shorts. Results: Winner, Performed Same, Inconclusive; variants that are too similar
  run longer; low impressions make a winner less likely; a small control group sees only the default. Early impressions come mostly
  from viewers who already know the channel, later ones from new viewers.
- **Rene Ritchie, "Top Five" (YouTube blog, 2024-06-14):** watch time is used because it holds both the click and the retention; test
  right away for the core audience, then again 72+ hours in for the wider one; start with big differences, then smaller ones.
- **Title testing** went global to all creators with advanced features (Search Engine Journal, ~December 2025, quoting Creator
  Insider): "Winner" means the most watch time per impression. **No aggregate win-rate data is published** (searched; none found).
- **CTR** (Help 7628154): half of all channels and videos sit between 2% and 10%; Home-heavy impressions push CTR down; don't judge
  early or on small changes.
- **Performance FAQ** (Help 141805): changing a title or thumbnail re-ranks a video only through how viewers react; "don't change
  what's working"; avoid misleading, sensational, or "Loud" (ALL CAPS, !!!!!) titles and thumbnails.
- **TV** (YouTube via Social Media Today, 2024-11-26 and 2025-10-29): over a billion hours a day are watched on TV sets; Shorts on TV
  grew 100% in a year. Nothing official says how many title characters show on a TV home grid: **unverified**.

## 2. What the pros say (grade C: testimony from people whose results are real)

- **MrBeast's thumbnail lead Chucky Appleby** (YouTube interview via Social Media Today, 2024-03-08): the title and thumbnail come
  before filming, ~50 concepts per video; a viewer must get it instantly; the intro must confirm the promise.
- **Paddy Galloway** (Colin & Samir, 2025; resource page and an edited transcript): YouTube is "click-and-watch": if they don't click,
  they don't watch; then respect their time; then make them want more. Most views come from Home and the sidebar, so ask which video
  the viewer is watching now that would make them click yours. Be **familiar but unexpected**. The curiosity gap is "the most
  important thing"; superlatives and "versus" are reliable frames; a list works only when its items feel unique. Top creators spend
  ~30% of their time on ideas and packaging, small ones ~5%. A Red Bull video's packaging was, in his estimate, the difference between
  a couple of million views and 28 million; a better package on an old video took one creator to ~40× daily views.
- **"Jimmy" (MrBeast), as quoted by Paddy:** push the packaging to its most exaggerated version, then pull it back to what you're
  comfortable with. The house line is the same: the boldest version the video truly delivers, and never a false fact.
- **A vendor getting the basics wrong:** 1of10's own A/B guide says YouTube's test picks the winner by CTR. YouTube's page says watch
  time. That's why vendor pages are C at best.

---

## 3. Titles: what the evidence says

| Source | Sample | Finding | Grade |
|---|---|---|---|
| **Robertson et al., "Negativity drives online news consumption"**, Nature Human Behaviour 7 (2023-03-16) | RCTs on ~105,000 Upworthy headline variants, ~5.7M clicks, 370M+ impressions | For an average headline (~15 words), **each negative word +2.3% CTR, each positive word −1.0%**; sadness raised clicks, joy and fear lowered them, anger flat. Causal (same story, different headline) | B (peer-reviewed RCT; news, not YouTube) |
| 1of10 data report 2025 (via Quasa) | ~323,000 "viral" videos, 50,000+ channels, outlier score = views ÷ channel median | Negative/conflict titles +20% median views; ~30 characters +60%; numbers −11% | C (vendor, secondary summaries only) |
| Eden, "What makes a good YouTube thumbnail?" (Dan Koe, 2026) | 507,478 long-form videos, 8,691 channels; breakouts (≥2× own channel baseline) vs underperformers | Breakout rate rises with title length: under 30 characters 26.1%, over 75 characters 35.9% (more specific titles). Videos over 40 min break out 41.1% vs 26.9% under 5 min | B/C (vendor, method published, n large; observational) |
| ytgrowth.io (2026) | 28,947 videos, 707 channels, normalised per channel | Length vs performance r = 0.0046 (none); numbers, brackets, colons, caps, emoji: no effect; a year tag +9.5% | C (method visible) |
| OverseerOS (undated) | 2,622 uploads, 59 channels, breakout vs normal within channel; 6,878 million-view titles | Same median length (58 characters, 10 words); 76% of breakouts within ±25% of their channel's usual length. ALL CAPS titles are 4.3%, mostly from three channels; Title Case vs other within channel 1.003 | C |
| AIR Media-Tech (2026-06-12) | 18,080 channels, 11 niches; **metric = engagement rate**, not CTR | Curiosity language is the one positive across niches; 90+ characters weakest | C (weak metric) |
| Our niche study (588 long uploads, 49 channels, lift vs own channel median, blind labels) | one niche | Number-led lists 1.40×; "missed" 1.42×; "vs" 1.23×; "?" 0.78× (lost in 9 of 9 channels); trailing "..." 0.76×; length flat; where the topic's name sits in the title: flat | A/B |

**What we take:**
1. **Length:** not a lever (the within-channel studies and ours agree). Mobile truncation is real but its character count is
   unverified, so the hook goes in the first few words.
2. **Curiosity and tension, delivered:** AIR's one cross-niche positive is curiosity language; the RCT says negative words pull. One of
   our title tests (a "disproving" title with a time box 36.3%, a flat counter-claim 35.5%, and a "stop calling it that, you're making
   it worse" title 28.2%) was stopped early: no verdict either way.
3. **Numbers:** the global studies disagree; in our niche study a count worked for list videos (1.40×). Paddy: only when the items
   feel unique.
4. **Caps:** 1-2 CAPS words at most (positive in our niche study; YouTube warns against all-caps "Loud" titles).
5. **Title and thumbnail:** two lines of copy for one promise. Eden: thumbnail text repeats the title on only 6.3% of videos, and 39%
   share no word with it; our niche study: repeating the hook 1.00× vs complementing it 0.92×. In the niche's top 20, "details"
   videos repeated the hook word (MISSED, EVERYTHING) and commentary videos complemented it (a mocking speech bubble over a short
   verdict title). Write the title knowing the thumbnail's words, so the two carry one promise without either being a copy of the
   other.

---

## 4. Measuring a niche's titles now (the method, and what one niche showed)

**The method (repeat it for the creator's niche before writing titles for a big topic):**
- yt-dlp `ytsearch50` for ~15 queries (the topic's name, "<topic> news", "<topic> details", "<topic> explained", "<topic>
  breakdown", "<topic> review", "<topic> worth it", "<topic> history", "<topic> things you missed", "<topic> vs", the name's
  other spellings), plus YouTube's sort-by-views with this-week/this-month/this-year filters. One run gave 898 unique videos.
- Metadata (upload date, subscribers, duration) for the top ~260 by views. Expect failures: age-gated videos need sign-in, and
  YouTube's bot check stops long runs (78 of 260 failed in one run; a few big videos may be missing from the sample).
- Keep: English, creator or outlet long form ≥3 min, about the topic. Drop: the maker's official uploads and re-uploads of them,
  music, multi-hour livestreams, non-English channels.
- **This is YouTube search's view of the niche, not a census.**

**What one niche showed (90 days, 62 top English titles; counts, not lift):**
- **Big channels dominate raw views:** one big personality-commentary channel had 5 of the top 10; one big niche news channel had
  11 of the top 25. Raw views mostly measure channel size.
- **Small-channel outliers** are found by views ÷ current subscribers. Caveats: subscriber counts are today's (they include the
  subscribers the video itself brought), so the ratio is crude and not the channel-median lift of the niche study; a new channel's
  ratio is inflated.
- **"?" in the title: 0 of 62.** Questions exist, but rarely at the top.
- **A negative or conflict word** (pathetic, slop, fake, doomed, worse, hates, threat and the like): 12 of 62, **7 of the top 20**. The
  biggest commentary titles were a short verdict, 19-41 characters: the thing plus one judging word ("<the product> is Pathetic",
  "Everyone Hates <the product>").
- **A hype word** (missed, everything, impossible, huge, wild, massive, rare...): 20 of 62, 11 of the top 20. "Missed" 5 of 62.
- **A digit** (not counting a digit in the topic's own name): 22 of 62; number-led 8. One news channel's update titles list the
  contents (a count of new pictures, then the features one by one).
- **1-2 CAPS words:** 15; **3+:** 6. **A "<Topic>:" prefix:** 15 (mostly one channel). **The maker (the company) as the subject:**
  11. **First person:** 6 (access or an experiment: an early look behind the scenes; testing something on themselves).
  **"vs":** 4. **Trailing "...":** 8.
- **Median length 43 characters; median video 15 minutes.**
- **The day of the biggest official announcement:** within a day, three channels titled "<announcement>: ... Everything You
  Missed!", "NEW <announcement>! Everything You Missed", "<announcement>: Every Detail YOU MISSED!" (the first did 721K views in ~1 day). A title in the same
  family has to win on its other half of the package.
- **The promise is one thing, not a list.** "Everything" packages are about the channel (its viewers already chose it); the small
  channels' outliers were each about one thing: a comparison, one detail with a stake, a concept, a technical word, a consequence for
  the world. That is Paddy's "familiar but unexpected", measured in one niche.

---

## 5. What our own channel's numbers taught (YouTube Studio)

- **A mainstream idea in a few words** held a high click rate while its impressions grew into the millions, mostly on Home (the
  click rate normally falls as Home impressions grow, Help 7628154). Our hits sat well above the videos that stalled.
- **A niche-only topic stalls at the package:** a video named by a word only the niche's news followers know got a low click rate
  and YouTube stopped offering it. Package for someone who doesn't follow the niche's news.
- **Search matters only when people search the topic:** a debated phrase brought a fifth of its views from search; the mainstream
  video only a few percent.
- **Tests stopped after a few hours never reach a verdict:** every one of ours ended with the shares within a few points. YouTube's
  own page says early impressions come from familiar viewers and a test needs days.
- **Long videos are watched largely on TV**, by adults 25-44, mostly in the US and UK: titles in plain words travel better than
  niche slang.
- **The intro is where the promise is checked:** retention fell hardest between about 0:20 and 0:50 on the videos that lost viewers.

---

## 6. Shorts packaging

- **Where Shorts are watched:** YouTube's Shorts product lead put views from the Shorts feed at **99.9%** (January 2025, via PPC Land,
  2026-07-25); on our Shorts, nearly all views came from the feed. In the feed there is no thumbnail and the title is a small caption. So
  the package is **the topic + the first frame + the first second's sound**. Title features explain ~4-5% of Shorts lift (our study of
  3,557 Shorts in one niche, A/B).
- **The measure:** "Stayed to watch" vs "Swiped away". On our Shorts, a stayed rate in the mid-50s was the baseline and the best reached the 70s. Since
  2025-03-31 every start or replay counts as a view (third-party, consistent across sources; YouTube's own page not fetched): engaged
  views are the honest count.
- **The first frame:** the payoff already visible, bright and full-bleed, the subject centred, the flash open alone on frame 0
  (`standard/SHORTS.md`); no black, letterboxed or "full video on channel" frames (in our niche study the bottom four Shorts opened on
  exactly these).
- **Titles** (our 3,557-Shorts study): no "?" (0.82× in that niche), 1-2 CAPS words, a concrete noun, "vs" for comparisons, a count for
  lists, 6-12 words; hype words neither help nor hurt in Shorts.
- **No A/B test for Shorts** (Help 16391400).
- **Link every Short to its long video** (Related Video, Help 14075157).

---

## 7. SEO: what YouTube says, and what it means

**YouTube's pages (A):**
- **Search** (Help 16090438): relevance (how well the title, tags, description and the video match the query), engagement (watch time
  for that query), quality (expertise, authoritativeness, trustworthiness); personalised by history.
- **Descriptions** (Help 12948449): the first lines are what viewers see; 1-2 main words in both title and description; unique per
  video; 5,000 characters.
- **Tags** (Help 146402): "minimal role" unless the topic is often misspelled; excessive tags break the spam policy.
- **Hashtags** (Help 6390658): up to 3 of the description's hashtags show above the title; over 60 and all are ignored; over-tagging
  can remove the video from search.
- **Chapters** (Help 9884579): 00:00 first, at least 3, each ≥10 s; creator chapters override automatic ones.
- Studies on years in titles (+9.5%, ytgrowth) are weak; a year only when freshness is the point.

**What it means:**
1. **Browse first.** The well-performing video was 92% recommendations, and Home doesn't read descriptions. The title is written for
   Home; SEO is the description and the tags around it.
2. **When the topic is searched** (a beginners' guide, a debate, a named event), put the searched phrase in the title verbatim (check
   YouTube's search autocomplete for the exact wording) and in line 1 of the description.
3. **Every upload:** the topic's searched name in the title; description line 1 restates the promise in search words; chapters; the
   topic's main hashtag in its common spellings + one topic hashtag (3 show above the title); 8-12 tags of spellings and verbatim
   phrases; the video language set; our own captions; a Correction block if something was wrong. It costs ten minutes and doesn't need
   polish (the template: `standard/SCRIPTS_AND_PACKAGING.md`).

---

## 8. The packaging process (every long video)

**Principle:** the package is designed with the script, before the edit (Appleby, Paddy), and judged where it will be seen: a feed of
real neighbours, at a glance from across a room. The creator's taste decides; the test measures.

**Step 1. The one sentence (at script time).** Write what a stranger gets from the video in one sentence, then answer Paddy's
question: which video is the viewer watching right now (the top 2-3 videos on the same topic this week), and why would they click ours
instead? If the answer is "it's the same but ours", change the angle, not the wording.

**Step 2. 20+ titles in 6 families** (neutral examples of each family's shape):
1. **The verdict / claim** (often negative, short): "<The phone>'s Pro Model Is Pathetic", "<The festival> Is a Disaster".
2. **The discovery** (missed, hidden, a count when it's real): "CRAZY Details You Probably MISSED in <the documentary>".
3. **The comparison** ("vs", years, then/now): "<This year's> vs <Last year's> vs <The original> - Side-by-Side Comparison".
4. **The list with a unique promise:** "10 Things From <the old recipe> That You WON'T Taste In <the new one>".
5. **The explainer with authority or an experiment:** "Explaining <the telescope>'s Mirror", "I Tried Every Viral Money-Making
   Scam".
6. **The disproval / ironic claim:** "Proving <X> Wrong In 10 Minutes" (a claim taken apart against a clock).

Push each to its most exaggerated version, then pull back to what the video delivers (Jimmy, via Paddy): bold wording is data, and the
only brakes are a false fact and a payoff the video doesn't give.

**Step 3. Score the titles** (keep the top 3, from different families):
- A stranger to the niche's news gets it (the insider-word video stalled; the mainstream one held).
- One concrete noun; no vague "something/everything" unless it is the promise.
- No "?" in the title; no trailing "..." in long form; 1-2 CAPS words; the topic's searched name in it; the hook in the first words.
- A tension or negative word if it's true (+2.3% per word in the RCT).
- The video pays it off in the first 30 s.
- Different from the 3-5 competitor titles on the same event (search the event the day of upload).

**Step 4. Pair each kept title with its thumbnail** (the creator's): one promise in two lines of copy; the title states, the thumbnail's
words complement or partly echo it (§3, point 5).

**Step 5. The creator's review:** the three titles side by side with their thumbnails; the creator's pick is the default (the first
uploaded is the one shown if the test is inconclusive).

**Step 6. Test & Compare on upload:** "Title" when the three titles are different concepts and the thumbnail is fixed; "Title and
thumbnail" when the creator made three thumbnails too. Let it run to YouTube's result (days, up to 2 weeks); stop early only for a real
problem. Log the shares and the verdict in the video's notes (`videos/<video>/`) the day it ends, with the CTR and impressions at that
time.

**Step 7. After upload:** read CTR only after substantial impressions and next to the traffic mix; compare with the channel's hits and
stalls. If a video stalls in its first days, repackage with a new **concept** (not a tweak),
then test again; never touch a package that's working. Old videos can be re-tested any time (Rene: weeks, months later).

**Step 8. The Short version of the same video:** the strongest moment as frame 0, a Shorts title by §6, and the Related Video set to
the long one.

**Time budget:** Paddy's top creators spend ~30% of their time on the idea and the packaging. For a two-day long video that's about
half a day on the idea and the package.

---

## 9. Open and unverified
- **TV titles:** how many title characters show on a TV home grid: not found in any YouTube source.
- **1of10's original report** sits behind an email form: only summaries were read.
- **Mobile title truncation length:** only blog estimates (AIR: ~60-70 characters); unverified.
- **The Shorts view-count change (2025-03-31):** third-party only; YouTube's page not fetched.
- **Missing niche videos:** in the niche run, 78 videos had no metadata (age gate, bot check); a few big ones may belong in the top 25.

## Sources
| Source | Published | Grade |
|---|---|---|
| YouTube Help 16391400 (A/B tests), 7628154 (CTR), 141805 (performance FAQ), 146402 (tags), 16090438 (search), 12948449 (descriptions), 6390658 (hashtags), 9884579 (chapters), 14075157 (Related Video) | current pages | A |
| YouTube blog, "Rene's Top Five" (Test & Compare launch, watch time, testing advice) | 2024-06-14 | A (older than 18 months, consistent with the current Help page) |
| Search Engine Journal, title A/B testing rolls out globally (quotes Creator Insider) | ~2025-12 | B |
| Social Media Today, YouTube's TV updates | 2025-10-29 | B |
| Social Media Today, YouTube's TV tips for creators | 2024-11-26 | B |
| Social Media Today, YouTube interview with MrBeast's thumbnail lead Chucky Appleby | 2024-03-08 | C |
| PPC Land, Shorts packaging (Creator Insider, Rene Ritchie; the 99.9% feed figure; no A/B testing for Shorts) | 2026-07 | B |
| Robertson et al., Nature Human Behaviour 7:812-822 (PMC10202797) | 2023-03-16 | B (RCT, peer-reviewed) |
| Eden, "What makes a good YouTube thumbnail? We analyzed 507,478 videos" (its title and length findings) | 2026 | B/C |
| Quasa, summary of the 1of10 323K-video study | 2026-03-23 (updated 2026) | C (secondary of a vendor) |
| 1of10 blog: A/B testing guide (wrong on the metric) | 2026 | C/D |
| ytgrowth.io, title length (28,947 videos) | 2026 | C |
| OverseerOS, title length (2,622) and capitalisation (6,878) studies | undated | C |
| AIR Media-Tech, titles across 11 niches (engagement-rate metric) | 2026-06-12 | C |
| Colin & Samir, "The New Rules of YouTube" with Paddy Galloway (resource page + edited transcript, The Transcript Desk) | 2025 | C (testimony) |
| Simon Willison on the MrBeast production memo (excerpts; the "first minute" lines are his commentary, not the memo) | 2024-09-15 | C |
| One niche, measured: yt-dlp searches + metadata (182 videos) | at the time of research | A (measured; a search sample) |
| Our own videos' YouTube Studio numbers | at the time of research | A |
| Our niche studies: 588 long uploads (49 channels), 3,557 Shorts | at the time of research | A/B |
