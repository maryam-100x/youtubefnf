# Long-form craft: how top commentary and documentary editors edit for retention

*The question: how do the best long-form YouTube editors (2025-2026) edit narrated commentary and documentary videos of 8-20 min,
and what does that mean for a narrated commentary/documentary channel built in Remotion + ffmpeg? Sources are keyed [S#], and the
table at the end gives each one's URL, date and type. `@mm:ss` points into a video. Each claim is labelled by how strong it is:*
- **MEASURED**: a number from data (a retention figure, a cut count, a loudness reading), including measurements made by us.
- **DESCRIBED**: what a channel or editor demonstrably does, in their own words or an analyst's breakdown.
- **OPINION**: an editor's or creator's view. Some are very experienced, but it is still not proof.

## How this was researched, and its limits
- **Primary sources:** 32 YouTube talks and breakdowns by the editors and creators themselves, read as full transcripts
  (auto-captions via yt-dlp): Paddy Galloway, Hayden Hillier-Smith, Johnny Harris and his team, James Jani, Dodford, LEMMiNO,
  Internet Historian, the Michelle Khare and Colin & Samir editors, YouTube's own staff, and others. Claims were extracted from the
  transcripts and the key numbers spot-checked against them (Galloway's 88%, the 10-15% TV figure). The 2026 Creator Insider
  interview, the MrBeast production document and the transcripts of the top creators we studied were read in full.
- **Web pages, read in full:** YouTube Help, W3C, Tubefilter, Gigazine (summarising the Washington Post), Ian Shepherd, Cutting et al.
  (PMC), Motion Array, PremiumBeat, vidpros.
- **Measured by us:** a full measurement of a 36-min commentary documentary by a top creator we studied ("top creator A", [S44]), and
  of a 9.5-min narrated commentary hit together with its channel's own analytics ("the 9.5-min hit", [S45]).
- **Couldn't reach:**
  - Reddit (r/editors, r/NewTubers) blocks both automated search and curl, so this research has no Reddit evidence.
  - Midway through, YouTube's bot check blocked further transcript and metadata downloads. So most of the reference videos in
    section 9 have no transcript or upload date yet; their views and lengths come from YouTube's channel listings.
  - The Washington Post original (2024-03-30) is paywalled. It was read through Gigazine's summary [S7].
- **Thin evidence:** nobody publishes measured SFX-per-minute, music-change counts or cut rates for documentary YouTube. Those numbers have
  to come from your own measurements of the reference list (section 9). Vendor blogs ("a pattern interrupt every 10-20 s",
  "70% at 30 s is good") repeat each other without data. They are flagged where they appear and not used to build anything.

---

## 0. What the evidence agrees on (the short version)
1. **The first 30-60 s decide most of the loss.**
   - YouTube measures the "intro" as the share still watching at 0:30 [S1].
   - MrBeast's team lost 21M of ~60M viewers in one video's first minute [S5].
   - Galloway puts the typical loss at 30-40% by 0:30, and got a video to 88% by moving its strongest section to the front [S8 @00:31].
   - The 9.5-min hit lost 48 points by 0:41, then only ~3 points a minute [S45].
2. **Confirm the click immediately, then open a bigger question.** The thumbnail's promise is restated or partly delivered in the first
   seconds; the full answer waits for the end. Sources: [S9 @17:20], [S19 @03:35], [S23 @12:54], [S27 @00:30], [S37 @02:01].
3. **Fast is not the goal; meaning is.** Since 2023 the most experienced editors have been telling creators to slow down.
   - Galloway has told "nearly every client" to slow down [S8 @16:20].
   - Hillier-Smith and the Khare team say the same [S13], [S17].
   - MrBeast publicly dropped "overstim" pacing in March 2024 [S6], [S7].
   - The measured hits still run 25-28 cuts a minute (top creator A and the 9.5-min hit [S44], [S45]). The difference is that every
     cut there carries a new piece of information, and the holds are real clips playing.
4. **A picture for every line, planned in the script.** Two-column scripts (words left, visual right) are standard at Johnny Harris's
   company and James Jani's, and Dodford writes hyperlinked montage scripts [S23 @17:00], [S21 @09:40], [S20 @11:44]. The picture
   either proves the line (evidence) or carries its mood [S23 @44:46].
5. **Sound carries the emotion, and the voice is sacred.**
   - Music is chosen per video and changes with the tone [S12], [S16 @03:03], [S34].
   - SFX mark on-screen events but never compete with the narration [S30].
   - Silence after a big moment is a tool [S14 @04:07], [S18 @05:42].
6. **TV is now the main screen for long form.**
   - 64.7% of the 9.5-min hit's watch time was on TV [S45].
   - Galloway's clients see ~10-15% longer views per video on TV [S9 @02:34].
   - YouTube says TV viewers pull longer videos [S4 @16:24].
   - What this means for the edit: readable (not full-width) text, a little more room to breathe, and premium-looking craft [S9 @04:39].
7. **Re-hook on a plan, not by gimmick.** Plan the moments where interest is renewed:
   - MrBeast's 3-minute and 6-minute "re-engagements" [S5];
   - Galloway's "danger zone" 10-20 s after each payoff [S9 @26:00];
   - Jani's countdown cards [S21 @06:37].
8. **End on the strongest fact or a payoff, with no tail.**
   - MrBeast: abrupt endings [S5].
   - Galloway: no long resolution [S9 @29:04].
   - Top creator A ends on the last fact, then music: 2 of 2 videos read [S44], [refs].
   - Johnny Harris and Hillier-Smith prefer a short reflective close with music [S23 @31:25], [S13 @35:51]. The common ground: nothing
     after the payoff that asks for patience.

---

## 1. The intro (first 30-60 s)

### Measured / evidenced
- **What YouTube measures (official):**
  - "Intro" = the percentage of viewers still watching after the first 30 seconds.
  - A high intro means the first 30 s matched what the thumbnail and title promised.
  - YouTube's advice: change the packaging or the first 30 s, and "experiment with different styles". If the top moments sit late,
    introduce the compelling content earlier, because audiences shrink over the length of a video.
  - The report compares each video with your own last 10-30 videos of similar length ("typical retention").
  [S1] (help page, undated), [S2] (2021-09-30).
- **Galloway, MEASURED:** a sports-myths video opened on a slow golf test. He moved a stronger section from later in the video to the
  front and stitched it to the intro, and got 88% retention at 0:30. He gives the average as a 30-40% drop by 0:30 [S8 @00:31, @04:08].
  The golf-style segments had already failed on that channel's earlier videos; it was first only because it was filmed first [S8 @05:40].
- **MrBeast's internal production guide, MEASURED:** one video lost 21M viewers in the first minute and kept ~39M at the 1:00 mark, a loss
  of ~35%. The guide calls that retention above average compared with other channels, and says every video loses the most in its
  first minute [S5]. (The guide dates to ~2022 and leaked in September 2024; two former producers confirmed it to Passionfruit [S5b].)
- **The Editing Podcast host's own video, MEASURED:** 67.6% retention at the end of a ~1-min intro and 65% at 1:44. It lost viewers in the
  first 15-20 s, then held flat from 0:30 to 2:00 [S9 @23:27].
- **The 9.5-min hit, MEASURED:** 95% at 0:00, 74% at 0:23, 52% at 0:41 (the one big exit), then about 3 points a minute down to 29% at
  9:00 [S45]. The intro is where the loss is, so it's where the craft pays most.
- **Third-party "benchmarks", not verified:** vendor blogs call 70% at 0:30 "solid". A "Retention Rabbit 2025" report is quoted as 55% gone
  by 60 s. Only secondary copies of both were found, and neither publishes a method. Not used.
- **How the genre's reference intros are built.** The auto-caption transcripts of the first 60-90 s of three commentary documentaries
  about failed big product launches were read [refs]:
  - **Top creator A, a product failure told as chaos:**
    - 0:00 a sponsor line.
    - "The year is <launch year>": the bet stated with its numbers (years in the works, a nine-figure budget).
    - An ironic "nothing could go wrong".
    - The flashback, "The year is <years earlier> ...", naming the rival's hit that started it.
    - Then a dated chronology: the flashback year, then a year five years later at ~1:00.
    - All of the above, irony and flashback included, falls inside the first 30-s caption block. The transcripts are timed in 30-s
      paragraphs, so finer timing needs the video.
  - **Top creator A, a second product failure:** the state of the world (a bleak year for the industry), then the bet with numbers
    (hundreds of millions, hundreds of staff, the better part of a decade, billed as "the next" market leader), then at 1:08 "It's
    <year>" starts the story with one scene. It runs ~68 s before the story starts [S44].
  - **Top creator B (the same story as the second, a different editor):** the industry's history told with jokes, then "this man"
    withheld across four sentences. The name comes at ~1:10. That is a curiosity gap built from repetition.
  - **The shared shape:** the world, then the bet (with numbers), then a hint that it will go wrong, then a dated flashback that starts a
    story. None of the three has a "coming up in this video" teaser, a logo or a subscribe ask.

### Editors' practice and opinion
- **Confirm the click, then go beyond it.**
  - Write the opening line like a title. Galloway starts scripts with "This" or "So", never with "hello and welcome" [S9 @17:52].
  - His "statement + intrigue": say what the video is (in words or pictures), build on the title rather than repeat it, then add
    specific intrigue. Cheap teases ("some picks will shock you") cost trust [S9 @18:22].
  - Rene Ritchie (YouTube's creator liaison): on YouTube the story structure flips, and the first act has to be a reward [S19 @03:35].
  - Kallaway and Vega (on MagnatesMedia) give the same rule [S37 @02:01], [S27 @00:30]. OPINION
- **MagnatesMedia's opening, DESCRIBED by an analyst:**
  - Its first 5 s recreate the thumbnail image, and the first sentence repeats the title words.
  - Within ~20 s come the context (the name on screen), the stakes (crushed rivals, bribed governments) and a curiosity gap (a
    teased rivalry). Together they lay out a ~49-min video's whole plot [S27 @00:30-03:02].
- **Lead with the strongest material.**
  - Galloway's "time to action" (seconds until the thing people clicked for) and "time to satisfaction" (seconds until the payoff) are
    tracked across videos [S9 @15:50].
  - Hillier-Smith: sometimes the best part must open the video, because 50-60% may be gone by the end [S19 @04:36].
  - Johnny Harris puts his strongest visual evidence first. In an analyst's count, the first ~3 min of his ~8-min Venezuela video are
    concrete things on camera, against PBS's context-first version [S25 @01:03]. DESCRIBED
- **Start inside the story, not with a promise of it.**
  - Galloway dislikes "coming up in this video" teasers after studying thousands of retention curves. He prefers starting in the action
    [S9 @15:20]. OPINION
  - The Khare team dropped vague teaser-montage cold opens: viewers had no reason to trust a montage would pay off 20 min later. They
    now tell the story clearly in the first seconds [S17 @23:03].
  - **The conflict:** MrBeast's guide says to "front load" the best stuff into minute one [S5]. The two agree on substance (show the good
    material early) and differ only on whether to *announce* it. The evidence favours showing it.
- **Six cold-open types top editors use:**
  - **State of the world, the bet, a hint of doom, then a flashback:** top creators A and B [refs], [S44].
  - **An out-of-context moment that is replayed at the end with full meaning:** Dodford's Sandler doc [S20 @07:09]. DESCRIBED
  - **Build the video's motif, then break it:** Jani's FTX video assembles puzzle pieces and then breaks them apart. The rest of the
    video rebuilds them, which gives a felt sense of progress [S21 @05:04]. DESCRIBED
  - **Praise over over-optimistic music, then a hard turn:** Jani's "this is not one of those stories" line, then the music darkens and
    a tweet card says something is wrong [S21 @02:32]. DESCRIBED
  - **A dry question, then "we need to go back":** the Vox style. The music starts *after* the question so it lands alone [S30 @03:04].
    DESCRIBED
  - **News clips as the cold open:** mainstream TV assumes no prior knowledge, so it sets the scale for newcomers [S18 @03:05]. DESCRIBED
- **Open by challenging a belief** ("you probably think X, but..."), placed in front of the context you still need [S9 @21:56],
  [S39 @03:33]. Galloway's best hook played a goofy MrBeast clip under a line saying you'd laugh if told he was a genius [S10 @05:04].
  OPINION
- **Sound in the cold open is scripted.** Johnny Harris writes it into the script (e.g. a gunshot, then epic suspense, then slow-mo) to
  drop the viewer straight into a tone [S23 @19:07]. DESCRIBED
- **Title card timing (the only direct advice found):**
  - Hillier-Smith: no title card in a ~10-min video. In an hour-long documentary, a slower, confident intro followed by a title card
    works like a stamp of quality. Fast cutting at the very start warns of an aggressive, tiring watch [S13 @10:39]. OPINION
  - One creator's retrospective on 100+ uploads: no logo or branding card [S36 @00:00]. OPINION
  - The 9.5-min hit put its title over a night view of the Earth as the last shot of its first ~53 s [S45]. For top creator A the timing
    is unmeasured; it has to be measured (section 9).
- **Process:**
  - Galloway writes 3-4 versions of an intro, records them and listens back. He tests them on someone outside the niche (his dad didn't
    get one, so he rewrote it) [S11 @03:33], [S10 @11:11]. He has rewritten one intro 12 times [S10 @04:03].
  - Johnny Harris's team finds the hook while reviewing the assembly cut with a "fresh brain" reviewer [S24 @60:26].
  - Galloway's test: the first ~30 s should work as a Short on its own [S10 @12:14]. OPINION

---

## 2. Pacing

### Measured / evidenced
| What | Cuts a minute / shot length | Source |
|---|---|---|
| Top creator A, a 36-min commentary documentary, measured by us | 25.7 cuts/min, median shot 1.78 s | [S44] |
| The 9.5-min hit (9:35), measured by us | 28.2 cuts/min, median 1.87 s, quartiles 1.25-2.60 s; minute by minute 33, 22, 37, 20, 33, 34, 23, 31, 23, 14 | [S45] |
| MrBeast, one minute from the middle of a 2023 video vs. a 2024 video | 38 cuts → 23 cuts (one minute each; tiny sample) | [S6] (2024-03-04) |
| "Retention editing" as practised in 2024 | a new cut every 1.3-1.5 s (an editor quoted by the Washington Post) | [S7] (2024-04-03) |
| Internet Historian (self-report) | about one shot per 3-4 s = 15-20 a minute | [S32 @46:03] (2019) |
| Hollywood films, 160 titles 1935-2010 | average shot length ~10 s in the 1930s-40s, under 4 s after 2000 | [S43] (2011) |
| MagnatesMedia (analyst's rule, OPINION) | change the shot at least every 3-5 s | [S27 @03:33] (2023) |

- **MrBeast's shift, MEASURED, with causation unproven:**
  - On 2024-03-03 he posted that over the past year he had slowed his videos down, focused on story, let scenes breathe and made them
    longer, and that views had "skyrocketed". He told creators the overstimulated style "doesn't even work".
  - Tubefilter's data in the same piece: his long-form videos' average 90-day views rose from ~60M (August 2022) to ~150M.
  - Tubefilter itself notes it can't prove the pacing caused the rise [S6], [S7].
- **TV viewing, MEASURED:**
  - Galloway: on his clients' channels, TV views run ~10-15% longer per video, and some videos get 80%+ of their views on TV
    [S9 @02:04].
  - Drew Binsky: 65% of his views come from connected TV [S13 @34:21].
  - The 9.5-min hit: 64.7% watched on TV [S45].
  - YouTube (Todd Beaupré, 2026-09-01): longer videos are growing because TV viewers want them. YouTube is following the audience, not
    pushing length. On TV, viewers don't want to pick a new video every 5-10 min [S4 @16:24, @17:57].
- **Dodford, self-reported:** a 3-4-film cross-cut montage building to a climax is one of the flattest, best-held stretches of his
  retention graph [S20 @04:36].

### How pace varies through a video
- **Top creator A (measured by us):**
  - Machine-gun montage bursts of 0.1-0.3-s shots in the cold open (cuts #20-#33 inside 3 s), then back to 2-5 s.
  - Deliberate 15-30-s holds on real people's clips, and on deadpan contradictions with no narration.
  - The two lowest stretches of the most-replayed graph are the setup (company structure, the product's pitch) [S44]. MEASURED
- **The 9.5-min hit:** bursts of 0.2-0.4-s shots on lists and big claims. Holds of 4-10 s only on real clips playing or one key visual.
  Shots over 4 s are 8% of the total [S45]. MEASURED
- **MrBeast's guide, minute by minute:**
  - minute 1 is frontloaded;
  - minutes 1-3 are "crazy progression" (cover ground fast);
  - a re-engagement at ~3:00;
  - minutes 3-6 bring "quick scene changes" and highly stimulating, simple content;
  - another re-engagement at ~6:00;
  - after that, viewers are invested and in a "lull".
  [S5] DESCRIBED (his own production rules, ~2022)
- **Energy cycles:** Dodford's Jim Carrey video runs in 2-4-min cycles, each a new life stage. Each opens on a high-energy dramatic quote,
  then drops into the lower-energy events that led to it [S27 @06:04]. DESCRIBED
- **Johnny Harris's rhythm:** short context "bridges" pulsed between bursts of concrete visual evidence ("anchors"). PBS, by contrast,
  runs long context with sparse evidence [S25 @00:32]. DESCRIBED
- **Galloway:**
  - Cut faster at the transitions. You can be slower while the viewer is waiting for something already set up [S9 @28:02].
  - Enter a scene as late as possible and leave as early as possible [S9 @28:02].
  - When one storyline ends, go straight into the next [S8 @19:54]. OPINION
- **Hillier-Smith:**
  - Deep into a long video, everyone who was going to leave has left, so that is the place to slow down: music in, then hold [S13 @32:18].
  - "There must be dialogue at all times" is the outdated 2018 fast meta [S13 @33:50]. OPINION

### When to hold a shot (what editors name)
- **Emotional beat:** ~3 s on a grieving face before cutting [S13 @24:23].
- **A silence after the big moment:** in Khare's boxing doc it became the most important beat [S14 @04:07]. Colin & Samir rate the silence
  after their imagined-crowd cut as the best part of that moment [S18 @05:42].
- **A document the viewer should feel:** ~5-6 s, even if only partly readable [S13 @26:34].
- **A map, for the whole sentence that describes the distance:** cutting away early makes the trip feel shorter [S13 @07:07].
- **A real clip playing with its own sound:** top creator A holds them 15-30 s, the 9.5-min hit holds them 4-6 s [S44], [S45]. MEASURED
- **A Johnny Harris map:** a ~7-s keyframed zoom, a ~4-s hold with a slight pitch change so the frame never fully freezes, then the next
  zoom [S22 @18:03]. DESCRIBED
- **What fails, MEASURED by a review verdict:** holding frozen frames of one source. Two later builds that held freezes of one source
  video were judged worse than the 9.5-min hit, which kept real clips playing [S45].

### Opinion: the "slow down" consensus, and how it fits the measured numbers
- **What the experienced editors say:**
  - Galloway: "slow down" is his most frequent note in 3 years. Imitators copy MrBeast's surface speed, but MrBeast has slow moments
    [S8 @16:20, @17:22]. His first client note is often to add depth because the edit is too fast [S10 @19:22].
  - Hillier-Smith: efficiency means removing friction, not speed. He cites Walter Murch's image of an editor who changes shots too often
    as a tour guide who never stops pointing: let viewers look, then move them on [S12 @02:32, @22:24].
  - Khare's team, after 10 min of their own hyper-retention edit: they had seen images flash and learned, felt and remembered nothing
    [S17 @22:33].
  - Dodford: effectiveness, not speed [S20 @34:45]. Dodford also warns that dragging shots out just because long form allows it didn't
    work either [S20 @36:17].
- **How this fits the measured numbers:** the measured hits are fast (25-28 cuts a minute), but each cut is a *new* picture of what is
  being said, and the holds are earned. The editors' complaint is about cuts the eye can't read, not about cut count. The working rule,
  to be tested against the reference measurements: never cut before the viewer has read the picture. A face or simple object needs
  ~1 s, a headline or map needs the whole sentence.

### Pattern interrupts
- **No measured basis was found** for "an interrupt every X seconds". The vendor claims (10-20 s, 25-35 s) cite nothing.
- **What top editors actually use instead:**
  - contrast cuts (a sterile press panel, then the subject doing something wild) [S20 @03:03];
  - a side story around the midpoint [S27 @05:04];
  - a comic beat as a palate cleanser in heavy material [S13 @14:15];
  - a "but" turn (section 6).
  - Interrupts that carry no meaning (zooms, captions, sound hits without information) are exactly what the "slow down" camp criticises
    [S35 @00:32].

---

## 3. B-roll strategy

### Measured / evidenced
- **The 9.5-min hit, by eye on contact sheets [S45]:**
  - Literal real-world pictures for the nouns: "the market" was a stock-exchange facade, "the holidays" was a crowded airport hall.
  - The subject's own primary material (the maker's official videos) is about half the shots, used where the line is about the
    subject itself.
  - Press pages, with a cursor gliding and clicking the words being said.
  - Real TV clips (a sketch show, a cartoon, a parliament feed) of 4-6 s with their own subtitles and lower-third banners.
- **Top creator A [S44]:**
  - mixed media: the maker's own promo videos, users' own clips with their watermarks kept, news screenshots, tweets, film and TV
    memes (cartoon clips);
  - labels written on memes (a one-word "Customer" or "Company" over a figure) to make a point without a sentence;
  - the video's top replay moment is a real user's own clip of the failure.

### How top editors choose a picture per line (DESCRIBED unless marked)
- **Johnny Harris:**
  - A two-column script, with every sentence or two given its own visual direction [S23 @17:00].
  - "Evidence" lines get a picture that proves the claim (a document, a map). "Soul" lines get mood pictures [S23 @44:46].
  - Missing visuals are marked in red with a checkbox while he writes [S23 @43:14].
- **Johnny Harris's "anchors" (an analyst's breakdown):** "look at this" plus a concrete object the camera can point at (a purse woven
  from bolivar notes for hyperinflation), never a generic image. The anchors recur like characters, and context only ever follows an
  anchor [S25 @01:33-04:34].
- **James Jani:**
  - A storyboard with the script on the left and the visual direction on the right [S21 @09:40].
  - His edit order: narration, then the script's essential B-roll, then music, then the remaining clips shaped to the music, then
    black placeholder cards for motion graphics, then the mix last [S21 @09:40-12:14].
- **Dodford:**
  - Montages are scripted line by line in a Google Doc, with soundbites as hyperlinks and the on-screen action in brackets
    [S20 @11:44].
  - Every cut serves the thesis: in the Sandler video he chose the moments where Sandler looked out of place [S20 @02:31].
  - Abstract lines get a visual metaphor "pushed as far as it will go" [S20 @37:19]. OPINION
- **Isaac:** colour-code each script sentence by asset type (screen recording, image, video, animation...) and gather each category
  before opening the editor [S38 @05:04].
- **Hillier-Smith:**
  - Never cut B-roll just because it's B-roll; each shot needs a reason tied to the line. His critique of a rushed doc: the same shot
    used five times [S13 @23:22]. OPINION
  - Put the strongest shot on the strongest words: the worst destruction right after "people are dying" [S13 @06:37].
  - Order shots to follow the words [S13 @16:46].
  - For "a few tutorials later", show three different tutorials, because the repetition makes it land [S15 @03:13].
  - Show scale with a match-cut barrage of many examples rather than a VFX globe [S14 @02:04].
  - Cut wide to close, not wide-wide-wide (citing Dune's editor) [S13 @07:38].
  - Stock footage is fine; only editors notice it [S13 @08:38].
- **Galloway, for an educational point:** simple text, one example and a few arrows beat a barrage of cinematic B-roll [S8 @13:18].
  OPINION

### Articles, tweets and screen captures (how they're animated)
- **Browser point-of-view sequences:** clicking an article, then through to the tweet, Googling a name. This is a Jani signature; a
  written brief and After Effects templates go to his motion-graphics editors [S21 @11:13, @12:44]. DESCRIBED
- **The 9.5-min hit:** a cursor glides to and clicks the words being said [S45]. MEASURED by eye
- **Johnny Harris:** "look at this" in the voice is always paired with a motion that directs the eye: a circle, a zoom or a shine on the
  detail [S23 @60:42]. DESCRIBED
- **Vox style:** a highlighter wipe over the text, synced to a marker-writing sound [S30 @13:50]. DESCRIBED
- **Against:** in 2023 Dodford (or the host; the transcript doesn't make it clear who) said the yellow-highlighter-on-article look should
  be retired as overused, along with paper rips [S20 @21:58]. OPINION. **Implication:** a cursor or circle tied to the spoken words
  reads as fresher than a generic highlight.

### Maps
- **Johnny Harris's workflow, DESCRIBED in detail [S22 @12:53-26:48]:**
  - GeoLayers 3 in After Effects (about $200), styled in Mapbox Studio with labels and admin boundaries turned off, and his own labels
    added.
  - The camera is keyed with latitude, longitude, zoom, bearing and pitch. Keying bearing later than zoom creates an orbit.
  - Country outlines come from Natural Earth via the GeoLayers Data Hub.
  - He blocks the move on low-res tiles, then finalises at high-res.
  - He renders a draft and times it in Premiere.
  - Older method: an Illustrator world file in After Effects, with anchor-point zooms.
- **Characters as icons on the map:** each icon is "loaded with motives", the distance between two icons is the tension, and one icon
  creeping toward the other builds anticipation [S23 @24:13]. DESCRIBED
- **Hold the map for the whole sentence** [S13 @07:07]. OPINION

### Archival, real-world footage and old material
- **Dodford:** archive interviews composited into a period TV set rather than left between black bars, so they feel watched live at the
  time [S20 @22:29]. DESCRIBED
- **Johnny Harris:** a per-video "art ingredients" sheet sets how archival stills and video are treated (framing, symbols, text style).
  There is no fixed channel look [S23 @37:38]. DESCRIBED
- **Internet Historian:** his format is stitching scattered clips, attendees' vlogs and news segments of an internet event into one
  sequence, told in a grave news-anchor register so the absurdity lands [S32 @02:38, @21:40]. DESCRIBED
- **Not for this build:** Dodford and Jani use Midjourney stills for scenes with no footage [S20 @23:31], [S21 @11:43]. The house rules
  (rules/) ban AI-generated pictures in the videos.

### Memes, film and TV clips
- **Top creator A:** memes labelled with on-screen words, and black title cards for the turns ("However", "In fact") [S44]. MEASURED by eye
- **The 9.5-min hit:** real TV and cartoon clips play with their own sound and subtitles, the narration paused, each 4-6 s [S45].
- **Borrow from film and TV:** a transition from The Marvelous Mrs. Maisel, sound design from Batman [S16 @05:06], [S38 @04:04]. OPINION
- **Contradiction as the joke:** a claim said straight, then the picture contradicts it [S44]. Internet Historian's grave delivery
  over absurd events works the same way [S32 @21:40]. DESCRIBED

---

## 4. Visual devices

### Zooms and punch-ins
- **Isaac:**
  - Scale and position keyframes with eased curves.
  - Keep the point of focus in the same screen spot across cuts and zooms (rule of thirds, eye line or centre) so the eye doesn't hunt
    [S38 @12:13]. DESCRIBED
  - His text-pop preset: scale 70% to 110% over ~7 frames, then back to 100% over ~5 frames [S38 @13:14]. DESCRIBED
- **Colin & Samir's editor:** cut on the eyes, keeping the subject's eyes in the same place across cuts [S18 @38:26]. OPINION
- **Hillier-Smith:** keep camera movement going the same direction across consecutive shots; a switch from left-right to right-left
  jars [S13 @05:36, @20:48]. OPINION
- **Johnny Harris's photo slide-in (from a tutorial, secondary):** the photo slides into its final position over ~8 frames with an eased
  graph curve, plus an old-camera or projector sound [S40] (2022).

### Text on screen
- **MEASURED (one anecdote):** the Editing Podcast host's retention dipped exactly where on-screen text appeared after a "wait, what"
  beat and had to be read. Galloway warned against concluding "never use text" [S9 @24:29].
- **TV legibility:** full-width text is unreadable on a 60-inch TV (film subtitles are small because the screen is big). Time the
  captions properly [S9 @04:39]. OPINION
- **Isaac's three places for text:**
  - captions on important lines only, because text popping every second irritates;
  - centre text for emphasis, in its own colour or glow;
  - text built into the scene (on a screen or wall).
  [S38 @12:44] OPINION
- **Top creator A:** labels on memes, a chalkboard card ("Years in the Making"), black cards for the turns [S44]. MEASURED by eye
- **Hillier-Smith:** subtitles that tell the story beat a character-name card; subtitle any scene with poor audio [S13 @13:13, @15:15].
  OPINION
- **Lower thirds:** the 9.5-min hit kept the real broadcasts' own banners [S45]. No editor in this research gave a lower-third rule.

### Chapter cards and structure markers
- **Jani:** recurring countdown cards ("10 months left") were added in draft 2 as a re-hook. The host calls the effect a
  "pre-apocalypse" feeling [S21 @06:37]. DESCRIBED
- **Johnny Harris:** cryptic symbols before chapter titles in the Mormon video [S23 @44:46]. DESCRIBED
- **Top creator A:** black text cards at the turns [S44].
- **YouTube chapters:** YouTube shows them on the retention graph [S2]. Their effect on retention is **unproven**: the vendor numbers
  (8-10%, "up to 50%") have no primary source.

### Speed ramps, freeze frames, split screens, picture-in-picture
- **No editor in this research gave a rule for these, and no data was found.**
- **Related remarks:**
  - Slow motion is used for melodrama, with the editor as a character [S12 @28:41], or just before a music swell [S17 @13:18]. OPINION
  - Unmotivated slow motion and drone montages make viewers leave [S16 @01:32]. OPINION
  - Our own evidence against long freezes: the review verdict in section 2 [S45].

### Looks: grain, LUTs, textures, letterbox, 3D
- **Dodford:** a 35mm, grainy, analog 70s-80s look, with contemporary editing tricks deliberately removed [S20 @20:58]. DESCRIBED
- **Johnny Harris:**
  - textured overlays, film burns, light leaks, noise and grain on graphics and photos [S40];
  - a per-video title style, e.g. a "Chernobyl fuzz" template copying HBO's Soviet-TV titles [S23 @40:41].
  DESCRIBED
- **Vox:** motion graphics rendered at 12 fps inside a 24-fps edit for a stuttered, hand-made feel [S47] (2021). DESCRIBED (secondary)
- **LEMMiNO:** months of 3D environments for the JFK video, edited and rendered at 1080p30 and upscaled to 4K60 with Topaz (26 h)
  [S26 @11:42]. DESCRIBED
- **Isaac:** overlays (light leaks, dust) on black, set to Screen blend; light leaks as his main transition [S38 @14:47]. DESCRIBED
- **Hillier-Smith:**
  - "Jurassic Park theory": use an effect only if it serves the story, a character or a theme. Try a plain cut first [S14 @01:03].
  - Screen wipes are dated, and graphics must match the tone [S13 @15:15].
  - Match cuts must mean something; an accidental one implies a link that isn't there [S13 @29:40].
  OPINION
- **Letterboxing:** no YouTube-specific evidence found, for or against. The general argument (forum, OPINION) is to add bars only to
  footage framed for scope. **An inference, unverified:** on TV, where most long-form watch time now is (section 2), bars cost picture
  height on source footage that wasn't framed for it.

---

## 5. Sound in long form

### Measured / evidenced
- **YouTube playback loudness:** YouTube normalises playback to -14 LUFS (exactly -14 since a 2019 change, measured through "Stats for
  nerds"). It turns loud videos down and does not raise quiet ones [S42]. YouTube itself publishes no figure.
- **Top creator A:** -16.7 LUFS integrated, loudness range 5.5 LU. The music is public-domain and library tracks (Mozart, Kevin MacLeod,
  Scott Buckley), with classical against chaos as part of the irony [S44]. MEASURED
- **The 9.5-min hit:** momentary median -14.5 LUFS (10th-90th percentile: -21.6 to -11.9) [S45]. MEASURED
- **Voice against music:**
  - **WCAG 2.2 SC 1.4.7 (W3C, Level AAA):** background sound at least 20 dB below the foreground speech (about four times quieter)
    [S41]. An accessibility standard, not a YouTube rule.
  - **A practitioner blog:** music -18 to -25 dB under narration, -12 to -14 dB where nobody speaks. It also suggests a 3-6-dB EQ cut in
    the music at 800-3,000 Hz to clear room for the voice [S46] (2026-05-21). OPINION
- **SFX per minute and music changes per video:** **no published figure found** for documentary or commentary YouTube. These are to be
  measured on the reference list (section 9) and on your own best video (its cue sheet: `videos/<video>/score/cues.py`).

### Editors' practice and opinion
- **Sound gets more time than picture:**
  - Hillier-Smith spends more time on sound than visuals: adjusting the track, picking the SFX style, a swell, a song change, or ending
    a song to land a point [S12 @30:44].
  - When a scene feels wrong, his first fix is the music, not the colour [S12 @38:26].
  - His library is hundreds of thousands of sounds, bought over ~8 years for about $30-40k and filed by type. He auditions 200-300
    candidates for a single sound [S12 @35:18]. DESCRIBED
- **SFX kinds and placement:**
  - **One sound per on-screen event:** an engine on a car's first appearance, a shutter on a vintage photo, pencil scratching on a
    draw-on, relay clicks on each collage image (varied so they don't repeat), a whoosh per passing object [S30 @06:42-14:20].
    DESCRIBED
  - **Trim the start of a sample** so its most ear-catching part hits on the cut [S30 @12:50]. DESCRIBED
  - **The basic kit** is whoosh, riser and impact, plus topical sounds (keyboard, clicks, meme sounds), layered. Do the SFX pass with the
    voice and music muted, then lower the SFX until they don't annoy [S38 @15:50]. OPINION
  - **Never compete with the narration:** better that a viewer misses a sample than that it masks a word [S30 @07:14]. OPINION
  - **Unexpected sounds** beat literal ones: sci-fi gun-reload sounds under retro TVs switching on, instead of TV static [S12 @36:54].
    OPINION
  - **The intro is denser:** in one creator's retrospective on 100+ uploads, every movement in the intro gets a sound, and the density
    eases afterwards; a low-energy voice with no SFX drains the viewer [S36 @03:36]. OPINION
- **Music:**
  - **Chosen per video, never one generic bed.** Music shapes the feeling more than anything else [S16 @03:03], [S28 @10:11]. OPINION
  - **No lyrics and no recognisable tracks** under a voice; low-pass the music if it still intrudes [S34 @01:00-04:33]. OPINION
  - **Track switch = a change of tone or subject; a sudden music cut = something funny or unexpected just happened** [S34 @04:33].
    OPINION
  - **Change tracks at a musical drop-out**, and keep the same composer for consistency [S30 @02:33]. DESCRIBED
  - **Johnny Harris's in-house composer scores every minute.** The conclusion gets its own "conclusion energy" cue, and tone changes
    are carried by music, picture and wording together [S23 @31:56, @53:29]. DESCRIBED
  - **Music first or last? The editors disagree:**
    - The Khare team cuts everything without music first (except montages and set pieces) so a track doesn't dictate the cut
      [S17 @16:20].
    - Jani and Isaac drop the music in early and shape the clips to it [S21 @10:11], [S38 @06:36].
    - Hillier-Smith adds music at around version 4-5 [S12 @39:27].
    DESCRIBED. **For a narrated video:** the voice sets the timing, so cutting picture to the voice first, then scoring and
    adjusting cuts to the musical phrases, fits both camps (to test).
  - **Less music in raw moments:** Khare's team removed ~75% of the music from one video and the dry scenes played better
    [S17 @15:49]. At a marathon finish they used a drone and a few claps instead of triumph, to make the win feel hollow [S17 @09:10].
    DESCRIBED
  - **Build, drop out over a slow-mo, come back on the big shot** (like a movie trailer) [S17 @13:18]. DESCRIBED
  - **A motif callback:** one stem of the entrance song returns softly at the end [S18 @09:16]. DESCRIBED
  - **Music against the picture:** classical or opera over a stunt, high-society music over trading-card deals [S12 @29:13].
    DESCRIBED
  - **Half the job is music editing:** shortening songs, finding the sting, moving a verse up to the crescendo [S12 @33:16]. OPINION
- **Silence as an effect:**
  - Top creator A runs 30-s stretches with no voice over users' own clips [S44]. MEASURED
  - The Vox style starts the music only after the opening question [S30 @03:04].
  - The silence after a big moment [S14 @04:07], [S18 @05:42].
- **Clarity checks:** listen as a viewer in a noisy room or on AirPods [S8 @08:43]. Bad audio makes people click off; subtitle it if it
  must stay [S13 @13:13]. OPINION

---

## 6. Story and script craft editors rely on
- **"But / therefore", not "and then":** Trey Parker and Matt Stone write the connecting word between outline beats and check that it is
  "but" or "therefore" [S31 @01:02]. (A 2011 NYU class, filmed for mtvU; clip uploaded 2017.) OPINION
- **Open loops:**
  - Keep a loop open as long as you can, and open a new one whenever you close one [S39 @01:01].
  - Every intro line should make the viewer want the next [S37 @07:06].
  - Don't close the reveal early: the cubes were hidden under clutter rather than shown in plain view [S15 @10:31].
  OPINION
- **Plant and pay off:** ask a question at the start and answer it at the end, or start a sentence early and finish it later
  [S20 @07:39]. Find the ending first, then make the film earn it [S20 @16:53]. DESCRIBED
- **Re-hooks:**
  - MrBeast's guide plans re-engagements at ~3 min and ~6 min [S5].
  - Galloway's danger zone is the 10-20 s after a payoff you've built up to; plant the next seed there ("the first of a few")
    [S9 @26:00].
  - Kallaway's mini-hook between points: this point matters, but it falls apart without the next one [S37 @15:44].
  - The Khare team: TV puts a teaser before every ad break, and YouTube needs them more often [S17 @22:02].
  - Jani's countdown cards [S21 @06:37].
  - A side story around the midpoint [S27 @05:04].
  - Mostly OPINION; the MrBeast item is DESCRIBED.
- **Order of material:**
  - Galloway's "skeleton": list the ~8 progressions at the top of the script and ask what should move earlier [S8 @15:50].
  - Kallaway: second-best point first, best second, then the rest (by Kallaway's own account untested) [S37 @12:41].
  - YouTube's own help: if the top moments are late, bring compelling content earlier [S1].
  - A first body point that repeats what viewers already know makes them check the timestamps and leave [S37 @11:39].
- **Experience first, explanation second:** visual evidence, then a context bridge (the reverse of how school teaches). Once anchors make
  viewers curious, they sit through ~4 min of history [S25 @04:34]. DESCRIBED
- **Pick the story's shape:**
  - Turn events into a story with a winner and a loser, or a protagonist and an antagonist [S32 @09:15].
  - Mystery framing grips; debunk-first framing is like being told a novel's ending [S26 @08:11].
  - Spectacle needs a human element: a victim's interview recurs in Jani's video and ends it [S21 @14:47].
  - A low point before the comeback (Dodford's three acts) [S20 @15:21].
  OPINION
- **Language:**
  - Use active agents: "they fled", not "the migration of". Concrete sentences let the viewer's visual brain picture each line
    [S23 @22:10].
  - Aim at about a 6th-grade reading level and stay rigorous [S24 @71:18].
  - Sound like a curious human, not a voice-of-God newsreader [S24 @27:56].
  - "Let me show you" works as a running promise of more to come [S23 @55:31].
  OPINION
- **Top creator A's engine:** a claim said straight, then the picture contradicts it, then a hold. Short sentences (median 9 words)
  delivered slowly (~132 wpm in the full measurement; ~147 by auto-caption word count in two of the creator's videos, which includes
  clip dialogue) [S44], [refs]. Top creator B tells the same story faster: ~181 wpm by the same count [refs]. MEASURED
- **Endings:**
  - MrBeast's guide asks for a satisfying payoff and an abrupt ending to protect retention [S5].
  - Galloway: no long resolution; viewers start looking for the next video once they sense the end [S9 @29:04].
  - Top creator A ends both videos read on the final hard fact (how fast it ended, against how many years and dollars went into it),
    then a clip and music, with no outro or subscribe ask [refs], [S44].
  - Johnny Harris ends with a contemplative zoom-out and a "where are they now" [S23 @31:25].
  - Hillier-Smith: don't hard-cut the outro, let it breathe with music [S13 @35:51].
  - YouTube's Beaupré: watch time that ends in a video "that didn't deliver" the hoped-for payoff isn't treated as valuable. That is why
    YouTube adds satisfaction surveys, likes and dislikes to watch time [S4 @11:15-12:17]. **Implication:** pay the title off in full
    before the end.

---

## 7. Common mistakes that kill retention
Each line is an editor's opinion unless marked.
1. **Opening on the weakest or slowest segment** because it happened or was filmed first. Galloway's 88% fix is the counter-example
   [S8 @05:40]. MEASURED
2. **An intro that doesn't match the packaging, or confirms it too late** [S1], [S27 @00:30], [S13 @03:02].
3. **Vague teaser-montage cold opens and "coming up" teasers** that promise without showing [S17 @23:03], [S9 @15:20].
4. **An opener that apologises or centres the creator** instead of the subject [S13 @03:02].
5. **Cutting faster than the eye can read**: "insecure editing", montages too quick to scan [S8 @16:51], [S13 @05:36].
6. **The opposite error: dragging shots** because long form allows it [S20 @36:48].
7. **Unmotivated B-roll, or the same shot reused** [S13 @23:22], [S16 @01:32].
8. **Explaining context before showing any evidence** (PBS against Johnny Harris) [S25 @03:04].
9. **Freezes held on one source with no new information.** Our own side-by-side review [S45]. MEASURED by a review verdict
10. **Text that has to be read during a key beat**, or full-width text unreadable on a TV [S9 @24:29, @04:39].
11. **Effects to show off:** screen wipes, meaningless match cuts, graphics in the wrong tone [S14 @01:03], [S13 @15:15, @29:40].
12. **Music too loud, with lyrics, or recognisable; one generic bed for the whole video** [S34], [S28 @10:11], [S16 @03:03].
13. **SFX that compete with the narration, or cliché samples** [S30 @01:31, @07:14].
14. **Small silences left at jump cuts.** Butt the syllables together and use J-cuts [S16 @01:02].
15. **Lingering after a storyline ends** instead of moving straight to the next [S8 @19:24].
16. **A call to action or a cheap tease in the middle of a strong hold** [S9 @27:01].
17. **A first body point the viewer already knows** [S37 @11:39].
18. **Manufactured stakes resolved in one cut** (hollow over-stimulation) [S35 @02:04].
19. **A long tail after the climax, or a hard, unsatisfying end.** The payoff must actually be delivered [S9 @29:04], [S4 @11:46].
20. **Overreacting to small dips:** a 2% drop that pays off later is fine [S8 @20:56].

---

## 8. Where the sources disagree (to settle by measuring, not by taste)
| Question | One side | Other side | How to settle it |
|---|---|---|---|
| How fast? | 25-28 cuts/min in the measured hits [S44], [S45] | "Slow down" [S8], [S12], [S17]; MrBeast 38→23 [S6] | Measure every reference minute by minute; compare with their most-replayed graphs |
| Teaser in the intro? | Frontload / tease the best [S5] | No "coming up" talk; start in the action [S9 @15:20] | Measure where each reference first *shows* its best material |
| Title card? | Yes for long, slow docs [S13 @10:39]; the 9.5-min hit at ~0:50 | None in ~10-min videos [S13]; no logo card [S36] | Log the title-card time in each reference |
| Music first or last? | First, cut to it [S21], [S38] | Last, so it doesn't dictate [S17], [S12] | This repo's pipeline (standard/PIPELINE.md): picture to voice first, then score, then nudge cuts to phrases |
| Ending | Abrupt, on the last fact [S5], [S44] | A short reflective close with music [S23], [S13] | Compare end-retention in the channel's own analytics |

---

## 9. Reference videos to download and measure
*Views and lengths from YouTube channel listings at the time of research. Upload dates are given where fetched; YouTube's bot check
blocked the rest of the metadata, so fetch it with the download.*
**Measure on each:** cuts a minute (minute by minute), shot-length spread, holds over 4 s and what they show, the intro's beats and
where the title card falls, re-hook moments, SFX a minute, music cues and changes, voice and music loudness, how much text is on
screen, and the ending.

| # | Video | Channel | Length / views | Why it's on the list |
|---|---|---|---|---|
| 1 | https://www.youtube.com/watch?v=J4qqIJ312zI "1955 vs 2025, who actually had it better?" | Johnny Harris | 24:09 / 4.1M (2025 by title; date not fetched) | Anchors and bridges, maps, data graphics, "look at this" eye-direction, custom score |
| 2 | https://www.youtube.com/watch?v=I2O7blSSzpI "Cicada 3301: An Internet Mystery" | LEMMiNO | 17:54 / 42M | An internet mystery told through posts, screenshots and motion graphics, with his own music: the top-tier "slow and premium" pole (alternate, newer: "The Unbreakable Kryptos Code", https://www.youtube.com/watch?v=jVpsLMCIB0Y, 47 min / 9.3M) |
| 3 | https://www.youtube.com/watch?v=-q2n5DkDoMQ "OpenAI is Suddenly in Trouble" | ColdFusion | 22:10 / 2.2M (recent upload; date not fetched) | **News-commentary documentary**, the closest format to a niche news channel: press pages, clips and charts over a calm narrator |
| 4 | https://www.youtube.com/watch?v=7u0_nrsfxXs "Why Japanese Railways Win" | Wendover Productions | 20:51 / 1.85M | Maps and explanatory motion graphics paced to narration; how long graphics hold |
| 5 | https://www.youtube.com/watch?v=LNYkor8IDoA "How Andrew Carnegie Became The Richest Man In The World" | Business Casual | 14:00 / 4.0M | Archival photos animated (2.5D, parallax, newspaper pages): the model for company-history segments |
| 6 | https://www.youtube.com/watch?v=Ju6Yj5QvIjY "The Adam Sandler Paradox" | Dodford | 19:34 / 8.4M | A soundbite-led doc with under 90 s of narration [S20]; montage cross-cutting, opener replayed at the end; the editor's own breakdown exists (S20) |
| 7 | One of SunnyV2's commentary docs at 8-11 min (pick it from the channel's listing) | SunnyV2 | 8-11 min | A commentary doc at **8-11 min**: the short end of the range, and the sleek essay house style (read with Pinely's critique [S29]) |
| 8 | https://www.youtube.com/watch?v=GPF4lm75NcI "Why Comedy Movies Died" | Patrick Cc: | 24:38 / 2.9M | Commentary doc built on film and TV clips and memes: how real clips, labels and narration interleave |

**Alternates:**
- James Jani, "The Fake Genius" (https://www.youtube.com/watch?v=w3EYKuFGJ5c, 65 min / 10M; the editor's breakdown is [S21]): browser
  sequences, countdown re-hooks.
- Moon, "Your Favorite Movies Are CIA Propaganda" (https://www.youtube.com/watch?v=Yootr6Vf7E0, 23 min / 2.6M).
- One MagnatesMedia company documentary (its formula is broken down in [S27]: thumbnail-matched first frame, 3D and archival, dramatic
  score).

**Fill these slots from your own niche** (the niche's knowledge lives in kb/). The most useful rows of the list are niche
ones: a top creator's standard at your target length; **the same story told by two different editors** (a natural experiment in
pacing, jokes and B-roll on identical facts: top creators A and B ran 181 vs ~147 wpm on one story); the leading competitor's video on
the exact subject you are making; and a long history documentary of the niche (how it handles decades of archival material, dates and
interviews; measure its first 20 min).

---

## 10. Checklist: 25 concrete practices (each one traced to its evidence above)
1. **Confirm the click within ~5-10 s.** The first picture echoes the thumbnail and the first line builds on the title, without
   repeating it [S27], [S9 @18:22].
2. **First line written like a title**: a statement plus specific intrigue. No greeting, logo or subscribe ask in the intro [S9 @17:52],
   [S36].
3. **Use the genre's proven cold open**: the world, then the bet (with numbers), then a hint of doom, then a dated flashback scene that
   starts the story by ~0:20-1:10 [refs], [S44].
4. **Put the strongest real material (clip, fact, image) inside the first 30 s.** If the best moment is late, move a piece of it up
   [S8 @00:31], [S1].
5. **Write and record 3-4 intro versions, listen back, and test them on someone outside the niche**, before building the picture
   [S11 @03:33].
6. **Two-column script:** every sentence gets its visual (evidence or mood) before editing starts, and missing assets are flagged
   [S23 @17:00, @43:14], [S21].
7. **Every noun the viewer can picture gets its own real picture.** The subject's own primary material where the line is about the
   subject; real-world footage, press or people where it isn't [S45], [S25].
8. **Never cut before the eye has read the picture:** ~1 s for a face or object, the whole sentence for a headline, map or document.
   Then cut on the next idea [S13 @05:36, @07:07], [S8 @16:20].
9. **Aim at roughly 20-30 cuts a minute** (the measured hits: 25.7 and 28.2, median ~1.8 s). Use 0.2-0.4-s bursts only for lists and
   big claims [S44], [S45]. Confirm against the references.
10. **Hold 4-30 s only on something live:** a real clip with its own sound, a moving map, a silence after a big moment. Never on a
    freeze [S44], [S45], [S14 @04:07].
11. **Cut fast at transitions; slow down while the viewer is waiting on a set-up thread**, and later in the video once the leavers have
    gone [S9 @28:02], [S13 @32:18].
12. **Plan re-hooks:** a new question within 10-20 s of each payoff, a re-engagement near 3:00 and 6:00, and a side thread near the
    middle [S9 @26:00], [S5], [S27].
13. **"But / therefore" between every beat**: write the connectors out and cut any "and then" [S31].
14. **Show, then explain:** visual evidence first, a short context bridge second. Never a long context block before any evidence
    [S25].
15. **Press pages and tweets get a motion tied to the spoken words** (a cursor click, circle, zoom or shine on the exact phrase), not a
    generic yellow highlight [S23 @60:42], [S45], [S20 @21:58].
16. **Maps:** a fly-in of ~5-7 s, a hold for the whole sentence with slight drift, icons for the people in the story. Build in
    GeoLayers-style layers or a Remotion map component [S22], [S23 @24:13], [S13 @07:07].
17. **Real people's own clips at the peak moments**, played with their own sound and subtitles while the narration pauses
    [S44 (top replay)], [S45].
18. **On-screen text sized and timed for a TV:** short labels, never full-width paragraphs, and never during the beat the viewer must
    hear [S9 @04:39, @24:29], [S38 @12:44].
19. **Keep the focal point in the same screen area across cuts and zooms**, and keep camera moves in one direction within a sequence
    [S38 @12:13], [S13 @20:48].
20. **One effect rule:** try a plain cut first, and use any transition, effect or match cut only if it means something [S14 @01:03],
    [S13 @29:40].
21. **Voice first in the mix:** music 18-25 dB under narration (WCAG asks for at least 20), EQ the music's 0.8-3 kHz band, deliver
    around -14 LUFS integrated [S41], [S46], [S42], [S45].
22. **Music chosen per section:** change track at a musical drop-out when the tone changes; no lyrics, no recognisable songs under the
    voice; cut the music for a joke or a shock [S34], [S30 @02:33], [S23 @53:29].
23. **SFX mark on-screen events** (a click on a click, a shutter on a photo, a whoosh on a move), are layered, and are set with the voice
    playing so they never mask a word. Make the intro denser and ease off after [S30], [S38 @15:50], [S36].
24. **Use silence on purpose:** a music drop before the big line, a beat of nothing after the big moment, a no-voice hold when the
    pictures tell the joke [S17 @13:18], [S18 @05:42], [S44].
25. **End on the strongest fact or the payoff of the title's promise, then music:** no recap, no outro, no subscribe ask
    [S5], [S9 @29:04], [S44], [S4 @11:46].

---

## Sources
| Key | Source | Date | Type |
|---|---|---|---|
| S1 | YouTube Help, "Measure key moments for audience retention", https://support.google.com/youtube/answer/9314415 | undated | Official |
| S2 | Creator Insider, "Key Moments in YTA: Introducing Typical Audience Retention!", https://www.youtube.com/watch?v=zNy3jxmT26o | 2021-09-30 | Official |
| S3 | Creator Insider (Matt Koval), "6 Tips for Better Audience Retention!", https://www.youtube.com/watch?v=b8RT5w-QISY | 2020-11-13 | Official, opinion |
| S4 | Creator Insider and YouTube Creators (Rene Ritchie with Todd Beaupré), "YouTube Algorithm 2026 - What Creators Need to Know", https://www.youtube.com/watch?v=rHLjxrbXmmY | 2026-09-01 | Official |
| S5 | MrBeast, "How to Succeed in MrBeast Production" (internal guide, ~2022), full text at https://www.alexanderjarvis.com/?p=90492 | leaked 2024-09 | Primary (top creator's rules) |
| S5b | Passionfruit, leak provenance (two former producers confirm), https://passionfru.it/mrbeast-leaked-document-81151/ | 2024-09 | Press |
| S6 | Tubefilter, "MrBeast says to stop using his editing style (because he did, too)", https://tubefilter.com/2024/03/04/mrbeast-editing-style-number-of-cuts-per-video/ | 2024-03-04 | Press, small measurement |
| S7 | Gigazine, summary of the Washington Post's "retention editing" piece (WaPo: https://www.washingtonpost.com/technology/2024/03/30/video-editing-mrbeast-retention/, paywalled), https://gigazine.net/gsc_news/en/20240403-retention-editing-beastification-may-be-end | 2024-04-03 (WaPo 2024-03-30) | Press, secondhand |
| S8 | The Editing Podcast, "Paddy Galloway Reveals The #1 YouTube Editing Error To Avoid", https://www.youtube.com/watch?v=Q0zRBsYQnA0 | 2022-10-11 | Primary interview |
| S9 | The Editing Podcast, "Paddy Galloway Tells Us How To Edit YouTube For TV", https://www.youtube.com/watch?v=t2M0C2tuHK8 | 2023-11-30 | Primary interview |
| S10 | Jon Youshaei, "Meet MrBeast's Secret YouTube Consultant (Paddy Galloway Interview)", https://www.youtube.com/watch?v=AX3dEGjBg6w | 2023-04-02 | Primary interview |
| S11 | Jay Clouse, "Meet The Godfather of YouTube Strategy (Paddy Galloway Interview)", https://www.youtube.com/watch?v=UHhTKwclHCs | 2023-06-12 | Primary interview |
| S12 | The Editing Podcast, "Optimize Your Editing for YouTube With HillierSmith", https://www.youtube.com/watch?v=eboQ7R34Ums | 2022-12-07 | Primary interview |
| S13 | HillierSmith, "When Editing Ruins Your Video, MasterClass on What NOT to Do" (with Drew Binsky), https://www.youtube.com/watch?v=IROKEjmIIlM | 2025-07-18 | Primary, editor |
| S14 | HillierSmith, "3 Editing Secrets I Wish I Knew Earlier", https://www.youtube.com/watch?v=XIVSa3wo0JU | 2023-07-12 | Primary, editor |
| S15 | HillierSmith, "The Editing That Makes Your Story 10x Deeper", https://www.youtube.com/watch?v=mPhhBgTIG2Y | 2025-12-11 | Primary, editor |
| S16 | HillierSmith, "5 MORE Editing Mistakes YouTubers Do That I Hate...", https://www.youtube.com/watch?v=QR8LxximqWI | 2021-03-31 | Primary, editor |
| S17 | The Editing Podcast, "She Hates Retention Editing, And It's Working" (Michelle Khare's team), https://www.youtube.com/watch?v=DbHuZjpwHjQ | 2022-11-01 | Primary interview |
| S18 | The Editing Podcast, "Colin and Samir Edited a Slow MrBeast Video. And It Worked.", https://www.youtube.com/watch?v=uOTd4tAJ8DA | 2023-03-01 | Primary interview |
| S19 | The Editing Podcast, "This YouTube Employee Has The Keys To The Algorithm" (Rene Ritchie, Hayden Hillier-Smith), https://www.youtube.com/watch?v=-7kswv-tWH0 | 2023-08-09 | Primary interview |
| S20 | The Editing Podcast, "How to Edit Documentaries like Dodford", https://www.youtube.com/watch?v=nUswBhWr7lY | 2023-10-01 | Primary interview |
| S21 | The Editing Podcast, "How To Edit Documentaries like James Jani", https://www.youtube.com/watch?v=bwz-jLZz2w8 | 2024-03-29 | Primary interview |
| S22 | Johnny Harris, "How I Make My Maps", https://www.youtube.com/watch?v=GsojLuJpe_0 | 2020-12-11 | Primary tutorial |
| S23 | David Perell, Johnny Harris interview on storytelling, https://www.youtube.com/watch?v=zq4b96m1AvM | 2025-03-12 | Primary interview |
| S24 | Colin and Samir, "An Honest Conversation with Johnny Harris", https://www.youtube.com/watch?v=mFRMvhY9ajE | 2025-03-04 | Primary interview |
| S25 | David Mora, "Why every Johnny Harris video goes viral", https://www.youtube.com/watch?v=dIKsEhX-vyU | 2022-03-06 | Analyst breakdown |
| S26 | LEMMiNO, "5,000,000 - Q&A", https://www.youtube.com/watch?v=nx4V9Uh_FW0 | 2023-10-01 | Primary |
| S27 | Vega, "How magnatesmedia FORMULA BROKE Youtube, Storytelling & Editing BREAKDOWN", https://www.youtube.com/watch?v=pw19xMIfAnA | 2023-12-06 | Analyst breakdown |
| S28 | MagnatesMedia, "How James Jani Beat The YouTube Algorithm", https://www.youtube.com/watch?v=WQN2Gcn7PMg | 2021-01-09 | Analyst (peer creator) |
| S29 | Pinely, "How SunnyV2 Ruined Video Essays", https://www.youtube.com/watch?v=VgPDhTypO70 | 2023-05-02 | Critique |
| S30 | Lilly's Tech Tips, "How to SOUND DESIGN your Documentary, Vox Style", https://www.youtube.com/watch?v=pVRW1GGTNZc | 2025-05-07 | Tutorial |
| S31 | Matt Stone & Trey Parker at NYU (mtvU "Stand In", 2011), https://www.youtube.com/watch?v=vGUNqq3jVLg | clip uploaded 2017-01-25 | Primary |
| S32 | Changer for Creators, "The INTERNET HISTORIAN // YouTuber Interview", https://www.youtube.com/watch?v=gi8k2KKcMEg | 2019-07-25 | Primary interview |
| S33 | Film Booth, "Sneaky Tricks YouTubers Use To Hook You", https://www.youtube.com/watch?v=Nb9cQmHFLTs | 2022-08-01 | Analyst |
| S34 | Aidin Robbins, "Guide to BACKGROUND MUSIC", https://www.youtube.com/watch?v=-4S1HgiFqPY | 2019-05-04 | Creator opinion (affiliate) |
| S35 | Cutting Concepts, "The Terrible Truth About Retention Editing", https://www.youtube.com/watch?v=nlWcTZwKsas | 2023-03-30 | Critique |
| S36 | A YouTube creator's retrospective on what 100+ uploads taught him (a talk to camera; not linked here) | 2022-08-12 | Creator opinion |
| S37 | Kallaway, "How To Write A Killer Script That Keeps Viewers Hooked", https://www.youtube.com/watch?v=7I50PECz7SU | 2025-02-19 | Creator opinion |
| S38 | Isaac, "How I Actually Edit Viral Videos", https://www.youtube.com/watch?v=ciAywjey0cY | 2025-07-13 | Editor tutorial |
| S39 | heyDominik, "I Studied 1,000 Hooks, Here's How to ACTUALLY Go Viral", https://www.youtube.com/watch?v=Xqy9L-88wcw | 2025-07-07 | Creator opinion (short form) |
| S40 | Motion Array, "Edit Documentaries in Premiere Pro: 3 Johnny Harris Style Tips", https://blog.motionarray.com/learn/premiere-pro/edit-documentary-in-premiere-pro/ | 2022-02-08 | Tutorial, secondary |
| S41 | W3C, Understanding WCAG 2.2 SC 1.4.7 Low or No Background Audio, https://www.w3.org/WAI/WCAG22/Understanding/low-or-no-background-audio.html | current version | Standard |
| S42 | Ian Shepherd (Production Advice), YouTube loudness, https://productionadvice.co.uk/youtube-loudness/ | updated after the 2019 change | Mastering engineer's measurement |
| S43 | Cutting et al., "Quicker, faster, darker: Changes in Hollywood film over 75 years", i-Perception, https://pmc.ncbi.nlm.nih.gov/articles/PMC3485803/ | 2011 | Peer-reviewed |
| S44 | Our measurement of a 36-min commentary documentary by a top creator we studied (top creator A): every cut, shot lengths, loudness, the most-replayed graph | — | Measured by us |
| S45 | Our measurement of a 9.5-min narrated commentary hit (cuts, loudness, a by-eye log of every picture) with its channel's own analytics (retention curve, TV share), plus a side-by-side review of two later builds that held freezes | — | Measured by us, and channel analytics |
| S46 | vidpros, "Music Is Too Loud: How to Fix Your Video Audio Mix", https://vidpros.com/fix-background-music-too-loud-video/ | 2026-05-21 | Practitioner blog |
| S47 | PremiumBeat, "Replicating Vox motion graphics", https://www.premiumbeat.com/blog/replicating-vox-motion-graphic/ | 2021-03-08 | Tutorial, secondary |
| refs | Our reading of the auto-caption transcripts of three commentary documentaries about failed big product launches: two by top creator A, one by top creator B (the same story as A's second). Words per minute = caption words / runtime, including clip dialogue | — | Measured by us |

*`@mm:ss` positions come from timestamped auto-caption transcripts (one paragraph per ~30 s); re-check any claim against the video at
that point.*
