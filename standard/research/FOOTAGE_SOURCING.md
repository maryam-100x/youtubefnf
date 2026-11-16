# Footage sourcing: where real footage comes from, how to find it fast, how to grade it

*The method for finding, testing, grading and logging source material for a video in any niche: news archives, stock libraries and
their licences and prices, public-domain and government archives, Creative Commons searches, YouTube search with yt-dlp, the primary
source's own channels, press kits and investor material. The map of the creator's own material lives in `kb/FOOTAGE.md` and
`kb/footage/`; this file is how to fill it. No footage was downloaded for this research; only metadata, page text, API answers, HEAD
requests, one caption file and one storyboard.*

**Grades.** **[T]** = tested here (command run, page fetched, API answered). **[P]** = read on the primary source's own page.
**[S]** = secondary source (aggregator, blog, news), dated where possible. **[U]** = unverified: from general knowledge or blocked from
here; don't build a decision on it until it's checked.

**Limits of this research.** (1) After ~25 back-to-back yt-dlp metadata lookups, YouTube answered every per-video request with "Sign in
to confirm you're not a bot" for most of the session; flat searches kept working, and the block had cleared within about an hour. So
per-video facts (upload date, top resolution) are the rate-limited part of any hunt (§3.4, §6.1). (2) The web-search budget ran out
near the end, so the last questions (AP/Reuters licence prices, British Pathé, Videvo) stay open (§9).

---

## 0. What matters most (the short version)

1. **The TV News Archive is the news source a plain web search misses.** An earlier hunt had written "no broadcast packages found" on
   several news moments of one story. The Internet Archive's TV News Archive is searchable **by what was said** (closed captions, US
   channels since 2009 plus BBC News), and any window of a broadcast downloads as an MP4. On the same story it returned business and
   news packages on every moment (CNBC, BBC News and **Bloomberg** among them), including a **TV report filmed inside a place the
   subject had never filmed itself**. [T] (§3.3, §7)
2. **A big feature article's video can be a talking head.** A long paywalled feature came with the journalist's own YouTube video
   about it. The storyboard (one frame every ~5 s, §3.1) showed the video was **the journalist talking to camera the whole way**: none
   of the footage its title suggested [T]. Its usable part is the audio and the quotes. The article itself answered 403 to curl [T]:
   the creator opens it in a browser; the author's video description carried a gift link past the paywall. The article's own photos
   are the pictures [U].
3. **The primary source's channel gets new material the catalogue doesn't have.** The maker's YouTube channel carried two new official
   videos that the catalogue of its material didn't list yet [T]. Check the primary
   source's newest uploads (`/@channel/videos`) before every hunt and add what's new to `kb/FOOTAGE.md`.
4. **A yt-dlp setup falls behind quietly.** An install with **no JavaScript runtime and no `yt-dlp-ejs`**, and no `curl_cffi`, still
   worked, but: since yt-dlp 2025.11.12 YouTube is meant to run with a JS runtime; without one, running is "deprecated" and "format
   availability will be limited" [S: Gigazine 2025-11-13, quoting the yt-dlp maintainers]. On one 1080p video both setups listed the
   same 32 formats [T], so it isn't broken today. 720p-only results came from forcing H.264 (§5.1), not from the missing runtime.
   TikTok failed ("Unexpected response") until `curl_cffi` was added and `--impersonate chrome` used; then it listed all formats [T].
   With Node + `yt-dlp-ejs`, YouTube answered normally once the bot block had lifted [T]. The fix is in §6.1.
5. **Stock: the free APIs are enough for generic B-roll.** Pexels (200 req/h, 20,000/month) and Pixabay (100 req/60 s) give 4K files
   with free keys [P]. Storyblocks (€18-25/month billed annually, unlimited 4K, now with an "MCP" for AI agents [P]) is the one paid
   library worth testing. It covers breadth, not news.
6. **The legal line:** commentary with short clips is normal practice. The measured cost is Content ID. In **Shorts (1-3 min) any
   active claim blocks the video, whatever the claimant's policy**; in long videos a monetize/track claim leaves it up [P: YouTube
   Help]. So claim-prone clips (network TV, film studios, music) go in long form, not Shorts.

---

## 1. Sources by type

### 1.1 Free stock (generic B-roll: offices, cities, crowds, money, phones, servers)

| Source | Access | Cost | Licence | API | Notes |
|---|---|---|---|---|---|
| **Pexels** | Site (Cloudflare check: curl got "Just a moment..." [T]); direct files on `videos.pexels.com/video-files/<id>/...` work (60 files pulled that way in one batch [T]) | Free | Pexels License: free commercial use, no attribution required [U: the licence page was blocked by Cloudflare; the API guidelines ask for credit "when possible" [P]] | Yes, free key. 200 req/h, 20,000/month, higher on request; `GET https://api.pexels.com/v1/videos/search` (`query`, `orientation`, `size`, `per_page` max 80) [P: docs, archived 2026-07-10] | 4K files are common; frame rate is mixed. A pull of 72 stock files (Pexels/Pixabay/Mixkit): **31 at 25 fps**, 17 at 30, 9 at 29.97, 6 at 24, 5 at 23.976, 3 at 50, 1 variable, none at 60 [T], so the frame-rate rules in §5.2 matter. The site's Cloudflare check hits "after a few searches" from a script: the API avoids that. |
| **Pixabay** | Site + CDN `cdn.pixabay.com` | Free | Pixabay Content License (free, commercial) [P: named in API docs; terms not re-read] | Yes, free key. **100 req/60 s per key**; responses must be cached 24 h; "systematic mass downloads are not allowed"; videos in `large` (usually 3840x2160, empty if absent), `medium` (1920x1080), `small`, `tiny`; max 500 results per query [P] | Videos may be embedded or downloaded; images must be downloaded, no hotlinking [P]. |
| **Mixkit** (Envato) | Site, direct `assets.mixkit.co` | Free | Two licences: **Video Free License** (commercial incl. YouTube, no attribution) and **Video Restricted License** (personal, non-commercial only): check each clip [P: mixkit.co/license lists both; FAQ wording via search] | No public API [U] | The 1080p files of 4 clips answered "Access Denied", so 720p was used [T]. |
| **Coverr** | Site | Free (Coverr+ paid tier exists) | Free for commercial use; **attribution not required** [P] | Yes, but the API page says access is free "as long as you don't... re-sell or use the videos for commercial use" and requires the Coverr logo in your product [P]. That conflicts with a monetized channel: download from the site, not the API. | Small library; has an MCP server listed in its developer docs [P]. |
| **Videvo** | Site | Free + paid tiers | [U] (pricing page answered 403 to curl) | [U] | Not checked. |
| **Wikimedia Commons** | Site + API | Free | **Per file**: CC0 / public domain / CC BY / CC BY-SA. BY and BY-SA need author + licence credit (in the description is the creators' norm) | Yes, no key; descriptive User-Agent with contact required or requests get blocked; use `maxlag` for batch jobs [P] | Best source for **real photos of buildings and people**: e.g. a recent photo of an office building, **CC0, nearly 4K wide** [T]. |
| **NASA** | images.nasa.gov, nasa.gov | Free | NASA media "generally are not subject to copyright in the United States"; acknowledge NASA; no implied endorsement; the insignia/logos are protected [P] | images-api.nasa.gov [U: not tested] | Space/Earth shots (e.g. an Earth-at-night map). |
| **Internet Archive (general)** | archive.org | Free | **Varies per item**: many uploads are other people's copyrighted videos (a search for a popular product's name returns viewers' own uploads and recordings [T]). Treat like YouTube clips, not like stock. | Yes (§3) | Viewers' own recordings of an older product can be the only real footage of something the maker never published [T]. |

### 1.2 Paid stock

| Service | Price (EUR as the pricing pages showed them; check again before buying) | What you get | API / automation | Licence catch |
|---|---|---|---|---|
| **Storyblocks** | Essentials **€18/mo billed annually**; Unlimited All Access **€25/mo** (adds music + SFX); Small Business €35/mo; "Save €216 annually" on Essentials implies ~€36/mo month-to-month [P] | Unlimited downloads, 8K/4K/HD footage, templates, photos; AI credits | Every plan lists **"Storyblocks MCP" (new)** and an Adobe plugin; a separate Storyblocks API is a business product (`/business-solutions/api`) [P]. MCP details (search+download from an agent?) not read [U] | Individual licence: **after you cancel, downloaded assets can't go into new projects**; work made before stays covered [P] |
| **Envato** (Elements) | Core **€14.50/mo billed annually, or €29 monthly**; Plus €33/mo annually (€49 monthly) adds AI credits [P] | Unlimited downloads of 29M+ assets: stock video, templates, music, SFX, fonts | No public API [U] | Page says "**Lifetime commercial license** for all stock assets" [P]; third-party reviews say no new projects after cancelling [S]: read the licence terms before buying |
| **Artlist** (footage, ex-Artgrid) | Footage & Templates "Creator" **€29.99/mo**; "Pro" €49.92/mo (€599/yr); Max Pro (everything) €39.99/mo (€479.88/yr); plan data embedded in artlist.io/pricing [P, read from the page's JSON] | Cinematic stock, LUTs, templates | No [U] | Licence generally doesn't survive cancellation for new projects [S] |
| **Adobe Stock** | 10 credits/mo **€29.99** = **1 video a month**; 40 credits €89.99 = 6 videos; unlimited stock + AI Studio €129.99/mo; cancelling after 14 days costs half the remaining annual commitment [P] | Huge library incl. editorial | Adobe Stock API exists [U] | Far too expensive per clip at a channel's weekly volume |
| **Pond5** | Editorial collection (with Reuters, Cover Video, Newsflare) launched 2019 "from $79 a clip" [S 2019]; one 2024 blog: $49 standard / $149 premium [S] | Royalty-free editorial news clips | [U] | Site answered 403 to curl; prices unverified |
| **Getty Images** | Editorial video priced per use (quote) [S: Getty help]; resellers cite $125-500 a clip [S] | Broadcast news/archive | Getty API (enterprise) [U] | Rights-managed; out of a small channel's range |
| **Newsflare** (viral/UGC news) | **£180 per video** (Growing Publishers: editorial, one post on up to 3 owned digital channels incl. YouTube, worldwide, post within 30 days); £280 for established publishers [P] | Eyewitness/viral clips | — | One post per purchase |

**Reading:** the paid libraries buy **breadth of generic B-roll** (offices, late-night work, servers, money, crowds) in 4K with
consistent quality. They don't sell what a story about a real company or person needs most: news broadcasts, interviews, real
interiors, the real people. Those come from §1.3-1.5 under commentary use.

### 1.3 News and archive footage

| Source | Access | Licence norm | Notes |
|---|---|---|---|
| **Internet Archive TV News Archive** | Caption search + MP4 window download (§3.3) [T] | Copyrighted broadcasts ("This material may be protected by copyright law", item notes [T]); used as short commentary clips like any news clip | **US news channels at 1280x720** (CNBC, Bloomberg, Fox, CNN, MSNBC, local affiliates), **BBC News** at 640x360 (2018 mp4) to 1024x576 (2022 mp4) [T]. Each item is a whole programme with captions; the TV logo and lower thirds are baked in. |
| **AP Archive / British Movietone** (YouTube) | Two channels with 550,000+ stories, 1895 to present [S 2015] | Uploaded to **promote licensing**; commentary clips of them are like any YouTube news clip | Mostly historical. Licence prices via aparchive.com [U]. |
| **Network YouTube channels** | CNBC Television, Bloomberg Television / Bloomberg Tech, BBC News, BBC Click, BBC Archive, Channel 4, Sky News, CBC News, local stations... [T: all turned up in real hunts] | Commentary use; many networks run Content ID [U per network] | The simplest source. Use `/@channel/search?query=` (§3.4). |
| **C-SPAN** | c-span.org video library; custom clips with a free login [S] | Terms effective 2025-12-15: personal, **non-commercial** use; commercial uses need a licence; AI use prohibited [P]. House/Senate floor feeds are said to be public domain, special sessions excluded [S] | For congressional hearings on a topic. The TV Archive also holds C-SPAN [T]. |
| **Wayback Machine** | `web.archive.org` + CDX API (§3.6) [T] | Screenshots of archived pages = "receipts" | One capture a year is enough to show how an old site changed (§3.6) [T]. |
| **Government / courts** | courtlistener.com dockets, parliamentlive.tv (UK Parliament video) | Court documents are public; UK Parliament footage has its own licence [U] | Documents for on-screen "receipts". |

### 1.4 The primary source, its industry and its people

| Source | Access | Notes |
|---|---|---|
| **The primary source's own YouTube channel** | `https://www.youtube.com/@<channel>/videos` [T] | The newest uploads first: new official videos land here before any catalogue has them (§0.3). Older material is on the channel too, but a few pieces exist only on the maker's own site [T]. |
| **The primary source's site / newsroom** | Its newsroom and product pages | Such sites are often JS apps (curl gets a ~4 KB shell [T]): capture article pages as receipts with a headless browser, and download the press kit (screenshots, artwork) into FOOTAGE once. |
| **Investor relations** (any listed company) | The company's IR "quarterly earnings" page [T] | Per quarter: a **webcast** (e.g. the Q4 platform `events.q4inc.com/attendee/<id>`, audio + slides), the **earnings presentation (PDF slides)**, the **earnings release** and the **prepared remarks (PDF)** [P]. The next call's date and link are on the page [P]. No transcript on the IR site [T: zero hits]; the Q&A part exists only in the webcast audio. Viewers re-upload the calls in full on YouTube [T]. |
| **Industry conference channels** | The conference's YouTube channel and its paid archive site | Talks by the makers themselves are rare but deep (a long talk on how one feature was built [T]); whether a talk is free or paid-only must be checked per talk [U]. |
| **The niche's own documentary channels** | YouTube, sometimes with a second channel of raw archive material [S] | A long history documentary of the subject's beginnings, office tours filmed decades ago, old press conferences in 1080i [T]. No reuse licence found [S]: treat as commentary clips. |
| **Long interviews** | Press outlets' and podcasts' YouTube channels, TV business channels | The people behind the subject talking at length (§7). A podcast's clips channel often cuts a long episode into topic clips, which is the fast way to a moment [T]. |
| **Other companies' channels** | Peers of the subject | Real office B-roll of peers: office tours, recruiting "life at <company>" videos, culture features [T]. When the subject publishes no footage of its own offices, the inside shots come from TV news (§7) [T]. |

### 1.5 YouTube clips, X, TikTok, film and TV

| Source | Access | Norm |
|---|---|---|
| **YouTube videos** (creators, podcasters, news) | yt-dlp (§6) | Short clips inside commentary; keep their watermark and name the creator. Never leaked or stolen material: a news package about a leak can carry the leaked frames, so log the banned spans per file. |
| **X (Twitter)** | yt-dlp with guest token works on public posts with video. The two posts tested had no video ("No video formats found") [T]. Text posts = page captures or X embeds. | Credit the account on screen. |
| **TikTok** | yt-dlp **needs `curl_cffi` + `--impersonate chrome`**: with it, a viral clip an earlier hunt couldn't get listed 576x1024 H.264 formats [T]. Without it: "Unexpected response from webpage request" [T]. | "download" format is watermarked; the h264 ones aren't (per yt-dlp's format note [T]). |
| **Film / TV lines** | **PlayPhrase.me** (search a spoken phrase across films/TV; free tier 5 clips per search, ~$3/mo for unlimited [S]); **Yarn** (getyarn.io: 403 to curl [T], use in a browser) | A short clip of the line is normal. Studio clips (NBCUniversal, Disney) are Content-ID-prone [U per studio]: long form, not Shorts. |

---

## 2. Licence and legal practice (what creators actually do)

**YouTube's own position** [P: support.google.com/youtube/answer/9783148]: fair use is a US-court question with four factors.
Commentary, criticism and news reporting are the classic examples. "Transformativeness is usually key." **Credit doesn't make
something fair use**, and neither do disclaimers ("no infringement intended", "I do not own"). So: credit on screen is a courtesy and a
signal of good faith, not protection.

**Content ID** [P: answer/6013276]:
- A match lets the claimant **block, monetize or track**, per country.
- **Videos longer than 3 minutes:** a monetize/track claim leaves the video up. **Shorts of 1-3 minutes: blocked whenever a claim is
  active, whatever the policy.**
- A claim isn't a strike. Fixes: trim the segment, mute/replace the claimed audio, or dispute it.

**What follows (practice, not law):**
1. **Use it as commentary.** The clip illustrates what the voice says (or plays for a few seconds as the receipt), then cuts away. In
   one finished video we counted, the real clips ran 4-6 s each with the narration paused [T].
2. **Shorts:** prefer sources with low claim risk: the primary source's own videos, creator clips, stock, the TV Archive's local news,
   photos. Avoid network-TV packages, film clips and any music. Under 1 minute, a claim's handling isn't stated on that page [U].
3. **Long form:** news packages, interviews and film lines are fine. If a claim lands, trim that segment in Studio rather than fight.
4. **Credit**: a small source tag (e.g. "BBC NEWS", "CNBC", "@creator") when the logo isn't already in the frame, plus a source list in
   the description (keep `author_outlet` per file for exactly this, §6.2).
5. **Hard brakes:** no leaked or stolen material (a news package about a leak can carry the leaked frames: list its banned spans
   per file), and no copyrighted music bed from a clip playing under our voice. The house lines themselves live in
   `rules/SHARED.md`.
6. **Licences that need a line in the description:** Wikimedia CC BY / BY-SA (author + licence), NASA ("NASA"), Pixabay/Pexels/Coverr
   none required (credit "when possible" for Pexels API use).

---

## 3. Search techniques

### 3.1 Inside a long video: find the exact moment
- **Captions with timestamps (yt-dlp):**
  `yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "en.*" --sub-format json3/vtt -o "subs/%(id)s.%(ext)s" URL`
  then search the text for the phrase and read its start time (keep the files in the video's `subs/`). Manual (uploaded) captions beat
  auto captions for exact wording: use the uploader's own captions when they exist. No captions → local Whisper (faster-whisper).
- **Chapters:** `yt-dlp --print "%(chapters)j"`; `--download-sections "<chapter-regex>"` downloads only matching chapters [T: --help].
- **Most-replayed:** `yt-dlp --skip-download -O "%(heatmap)j" URL` returns YouTube's heatmap as `{start_time, end_time, value}`
  segments (value 1.0 = the most replayed) [T: a long podcast episode came back as 100 equal segments]. Peaks = the moments people rewatch.
  New or small videos may have none.
- **Storyboards (cheapest preview):** `-F` lists `sb0` (320x180) to `sb3` (48x27) [T]. `yt-dlp -f sb1 -o "%(id)s.%(ext)s" URL`
  downloads a ~150 KB `.mhtml` of WebP grids (sb1 = 160x90 tiles; about one frame every 5 s, so a half-hour video fits in about
  7 grids) [T]. A 15-line script stacks them into one sheet (the email parser pulls the `image/*` parts, PIL pastes them). One look
  told that a journalist's long video was a talking head with none of the footage its title suggested [T]. For frame-exact picks, a 360p video-only "scan"
  copy of the shortlisted videos, sheeted, stays the tool.

### 3.2 Across all of YouTube by spoken words
- **Filmot** (filmot.com) indexes YouTube subtitles: "720 million captions across 645 million videos" [S, AlternativeTo]. From here it
  answers with a captcha ("Patrons don't need to solve captchas"; one developer, hosting $1,490/month, 99% donor-funded) [T]. An API runs
  through RapidAPI [S: the `filmot` PyPI wrapper's README]; plan prices not found [U]. Use: "who said '<a company's name>' on camera?"

### 3.3 Across TV news by spoken words (TV News Archive) [T]
- Endpoint (JSON, no key):
  `https://archive.org/services/search/beta/page_production/?user_query=<query>&service_backend=tvs&hits_per_page=50&page_type=collection_details&page_target=tvnews`
  → `response.body.hits.hits[]` with `fields.identifier`, `fields.start` (seconds into the programme), `highlight.text` (the caption
  around the match, terms in `{{{ }}}`), `fields.__href__` (`/details/<id>/start/<s>/end/<s+60>`). Quotes work (`"<exact phrase>"`).
  The plain `advancedsearch.php` does **not** search captions (0 hits for the same phrases) [T].
- **Download a window:** `https://archive.org/download/<id>/<id>.mp4?t=<start>/<end>` → 302 to a datanode with `?start=&end=` →
  `video/mp4` (60 s = 15.4 MB at 1024x576; a 240-s window answered too, 65 MB at 720p) [T]. Whether long windows are capped is
  unverified. yt-dlp can't do it: it reads the item as an empty playlist [T].
- Metadata: `https://archive.org/metadata/<id>` gives fps (BBC 25), source size, programme, subjects, `closed_captioning` [T].
- Item ids read as `<CHANNEL>_<YYYYMMDD>_<HHMMSS>_<Programme>` (e.g. `CNBC_<date>_<time>_<Programme_Name>`), so a hit's `start`
  plus its id is a complete log line (§7).

### 3.4 YouTube search operators (tested through yt-dlp)
- **4K only:** `https://www.youtube.com/results?search_query=<q>&sp=EgJwAQ%253D%253D` returned only 4K walk videos [T].
- **Date window:** `before:YYYY-MM-DD after:YYYY-MM-DD` inside the query returned videos from the chosen month [T]. That's unofficial,
  so confirm with each hit's upload date.
- **Sort by upload date:** `sp=CAI%253D` [U: the result order wasn't verifiable from flat output]. `ytsearchdate` no longer exists
  in this yt-dlp (only `youtube:search` and `youtube:search_url`) [T].
- **Inside one channel:** `https://www.youtube.com/@BBCNews/search?query=<q>` [U: standard yt-dlp tab URL, not run].
- Upload dates in flat output are `NA`, so dates need a per-video lookup (`-O "%(upload_date)s"`), which is the call YouTube rate-limits.

### 3.5 Pictures: reverse image search and better copies
- **Google Lens / Bing Visual Search / Yandex / TinEye** in a browser (the creator's job, or a page capture for public results). The Bing
  Search APIs (Visual Search too, per secondary sources) were **retired 2025-08-11** [S: Microsoft's lifecycle notice as quoted in
  search results, not fetched; Visual Search specifically only in third-party pages]. **TinEye API**: prepaid bundles from 5,000
  searches for $200 [S: TinEye blog, undated].
- Use: find the original (largest, no watermark) of a press photo, or which video a frame comes from.
- **Highest quality copy:** prefer the original uploader (the maker, the network) over re-uploads; `yt-dlp -F` to see the ladder; for
  stock pick the `uhd`/`large` file; for Wikimedia the original file URL (not the thumbnail).

### 3.6 Dead pages and old websites (Wayback)
- CDX API: `https://web.archive.org/cdx/search/cdx?url=<site>&output=json&from=2005&to=2015&collapse=timestamp:4` → one capture per
  year [T]. Open `https://web.archive.org/web/<timestamp>/<url>` and capture the page.
- `https://archive.org/wayback/available?url=<url>&timestamp=<YYYYMMDD>` gives the closest capture (empty if none) [T].

### 3.7 Web operators (Google) [U: general knowledge, not tested]
`site:bbc.co.uk "<company name>"`, `site:<the company's IR domain> filetype:pdf "<product name>"`, `"<company>" inurl:newsroom`,
`before:2018-12-01`. Useful for finding articles to capture as receipts and for finding the original broadcaster of a re-upload.

---

## 4. APIs for automated search and download

| API | Key | Limits | Search call | What comes back | Status |
|---|---|---|---|---|---|
| Pexels | Free (account needed: the creator creates it) | 200/h, 20,000/month; unlimited on request with attribution shown [P] | `GET https://api.pexels.com/v1/videos/search?query=&orientation=landscape&size=large&per_page=80` with header `Authorization: <key>` [P] | `video_files[]` (each `link`, `width`, `height`, `fps`), `video_pictures[]` (previews), `user`, `url` | Docs read [P] |
| Pixabay | Free (account) | 100 per 60 s, cache 24 h, no mass downloading [P] | `GET https://pixabay.com/api/videos/?key=&q=&video_type=film&min_width=1920&per_page=200` [P] | `videos.large/medium/small/tiny` (`url`, `width`, `height`, `size`, `thumbnail`), `tags`, `duration`, `pageURL`, `user` [P] | Docs read [P] |
| Wikimedia Commons | None; descriptive UA with contact [P] | Be gentle: serial requests, `maxlag` [P] | `https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch=<q>&gsrnamespace=6&prop=imageinfo&iiprop=url|size|extmetadata&iiextmetadatafilter=LicenseShortName|Artist` | URL, size, licence, author per file | **Tested** [T] |
| Internet Archive search | None for reading | Not stated [U] | `advancedsearch.php?q=&fl[]=identifier&output=json`; scrape API `services/search/v1/scrape`; metadata `archive.org/metadata/<id>`; TV captions §3.3 | JSON | **Tested** [T] (the scrape endpoint returned the same list for different queries; quoting/encoding issue, use advancedsearch) |
| Wayback | None | — | CDX / availability (§3.6) | Captures | **Tested** [T] |
| YouTube Data API v3 | Free key (Google Cloud project) | **~100 searches a day**: Google's overview (as quoted in search results) gives new projects "100 search.list calls" plus 10,000 units/day for other endpoints; 2026 guides put `search.list` at 100 units; quota resets at midnight Pacific; more only via Google's form [S] | `search.list` (`q`, `publishedBefore/After`, `videoDefinition=high`, `channelId`) | IDs, titles, dates | Not needed: yt-dlp search costs nothing. The API's value is exact `publishedAt` dates without per-video scraping. Caption download through the API works only for videos you own [U]. |
| yt-dlp | — | YouTube's bot check after rapid per-video calls [T] | `ytsearchN:`, results URLs, channel tabs | Everything | **Tested** [T] |
| NASA Images | None [U] | [U] | `https://images-api.nasa.gov/search?q=&media_type=video` [U] | — | Not tested |
| Storyblocks | Plan / business API | — | MCP in all plans [P]; API docs behind login [S] | — | Unknown until bought |
| Coverr | Free key | — | REST + MCP [P] | — | Its API terms bar commercial use [P]: skip |

---

## 5. Quality: resolution, frame rate, audio

### 5.1 Resolution
- Pull the **highest real resolution** that exists (4K stock, 1080p news) and let the timeline scale. Never upscale SD as if it were HD:
  BBC captures from the TV Archive are 640x360-1024x576 [T]. Use them small (a TV frame, a picture-in-picture, a phone mock) or accept
  the softness with the logo visible, which reads as "real broadcast". Re-uploads are often worse: a re-upload of an old radio feature
  was 480p at 12 fps (audio use only) [T]; an old behind-the-scenes clip existed only at 360p24 [T].
- Prefer **the top height in any codec** (H.264/VP9/AV1): `-f "bv*[height<=2160]+ba/b"`, then let the conform step make the edit
  file. Preferring H.264 capped results at 720p, because YouTube served H.264 only up to 720p for those videos [T].

### 5.2 Frame rate into a 60-fps timeline
Measured: how many 60-fps output frames each source frame is held with nearest-frame conversion (`fps=60` in ffmpeg, "Nearest" in an
editor):

| Source fps | Hold pattern at 60 | What you see |
|---|---|---|
| 60 / 59.94 | 1,1,1,1... | Native. |
| 30 / 29.97 | 2,2,2,2... | Clean (every frame doubled); most official product videos and most YouTube. |
| 24 / 23.976 | 3,2,3,2... | Regular 3:2 cadence, the way films look on any 60-Hz screen. Fine. |
| 25 (UK/EU TV, BBC, much stock) | 2,2,3,2,2,3,2,3... | Slightly irregular (12 output frames per 5 source frames). Invisible on static shots and talking heads; a faint stutter on slow pans. |
| 50 (EU broadcast, deinterlaced 25i) | 1,1,1,1,2 | One held frame in every five: a faint hitch on pans. |

Practice:
1. **Don't conform by changing speed** (25→30 = 20% fast, voices go wrong). Keep real time.
2. **Nearest-frame is the default** for talking heads, news anchors, static B-roll and anything under ~3 s.
3. **Slow pans/drone shots at 25 or 50**: try an optical-flow retime (DaVinci Resolve's Retime "Optical Flow"; Speed Warp needs
   Studio) or pick a 24/30/60 alternative. Forum reports say optical flow can leave visible artefacts and frame blending ghosts
   [S: Blackmagic forum threads]: judge each shot on a sheet. ffmpeg's `minterpolate=fps=60:mi_mode=mci` exists but is slow and warps
   edges [U: not tested]. Frame interpolation isn't AI-*generated* footage, but it does invent in-between frames; use it only where the
   stutter is worse than the artefacts.
4. **Interlaced broadcast** (1080i/576i: old TV, old press-conference uploads labelled "1080i" [T]): deinterlace with
   `bwdif=mode=send_field` (one output frame per field: 25i→50p, 29.97i→59.94p). Then 29.97i becomes native 60.
5. **Variable frame rate** (screen recordings, phone clips, some TikToks): convert to constant first (`-vf fps=<target> -fps_mode cfr`;
   `-vsync` is the old name) or the edit can drift against the audio [U: general practice, not tested here].
6. Keep clips at their own frame rate (mezzanine x264 CRF 16, no B-frames) and let the timeline conform them; the pipeline in §6 only
   fixes interlace and VFR.

### 5.3 Audio from clips
News and interview clips play with their own sound. Normalise loudness per clip before the mix (`standard/SOUND_AND_VOICE.md` sets the
targets). Strip a clip's background music when it plays under our voice.

---

## 6. Proposed pipeline (search → preview → download section → conform → catalogue)

### 6.1 Setup fixes (cheap, do first)
1. `PIPE -m pip install -U "yt-dlp[default,curl-cffi]"` → brings `yt-dlp-ejs` and `curl_cffi` (both install cleanly [T]).
2. A JS runtime: **Deno** is yt-dlp's default [S] (install e.g. `winget install DenoLand.Deno` on Windows, `brew install deno` on macOS
   [U: package ids not checked]). Node, which the motion stack already needs, works too: `--js-runtimes node` with `yt-dlp-ejs`
   handled formats, captions, storyboards and heatmap [T]. Either is fine; Node needs no install.
3. **Pacing for YouTube:** one process at a time, `--sleep-requests 2 --sleep-interval 3 --max-sleep-interval 8` [U: values]; flat
   searches first (they kept working during the block [T]); per-video lookups only for the shortlist. 3-s gaps between per-video calls
   got through after a wait [T].
4. **Cookies** (`--cookies-from-browser firefox` or an exported cookies.txt) clear age gates and the bot wall [S: yt-dlp's error text],
   but they act as the creator's account: only the creator's own cookie file (config, never shared), and only with their go.
5. Free API keys (the creator creates the accounts): **Pexels**, **Pixabay**; optional **YouTube Data API** key for exact dates. Keys go
   in SECRETS (config/paths.toml), never in the repo.

### 6.2 The tool (proposed: `tools/footage/hunt.py`, not built)
Each script beat gets a **need** line: the noun/claim and the kind of picture (e.g. `need: "the company's headquarters" | real | building`).

1. **`hunt.py search "<need>"`**: fans out in parallel to Pexels + Pixabay (stock), Wikimedia (photos), TV News Archive captions
   (news), yt-dlp flat search (YouTube, with the 4K and date operators), channel-scoped searches (BBC News, CNBC Television, Bloomberg,
   the niche's press channels, the primary source). Writes `candidates.jsonl`: source, url, title/caption hit, start time if known,
   duration, resolution, fps, licence class (`stock-free`, `cc-by`, `pd`, `commentary`), claim risk (`low` stock/official/creator, `high`
   network TV/film/music), and a `leak_check` flag for anything showing the primary source's unreleased material that the maker didn't
   publish itself.
2. **`hunt.py moments <video>`**: captions → phrase hits with timestamps (manual captions first, auto second, Whisper last); chapters;
   heatmap peaks.
3. **`hunt.py preview`**: one contact sheet per need with every candidate's thumbnail/3 frames, source, time, resolution and licence
   (the sheet style of `tools/motion/curate.py`). Stock and TV items have preview images from the APIs (TV: the item's `thumbs`);
   YouTube gets its storyboard (`-f sb1`, §3.1) plus caption hits and heatmap peaks marked on it; a 360p scan only for the shortlist.
   **The pick is made by eye on the sheet**, from all the options.
4. **`hunt.py get <candidate> <in> <out>`**:
   - YouTube/X/TikTok: `yt-dlp -f "bv*[height<=2160]+ba/b" --download-sections "*<in-2>-<out+2>" --force-keyframes-at-cuts`
     (2 s of handle each side) with `--impersonate chrome` where needed; keep the `.info.json`.
   - TV Archive: `archive.org/download/<id>/<id>.mp4?t=<in-5>/<out+5>`.
   - Stock: the direct file URL from the API (largest), whole file.
   - Wikimedia/NASA: the original file URL.
5. **`hunt.py conform`**: ffprobe → deinterlace if interlaced (`bwdif=mode=send_field`), VFR → CFR, keep native fps otherwise;
   x264 CRF 16, no B-frames, AAC 48 kHz (the mezzanine); loudness measured and stored, not changed.
6. **`hunt.py catalogue`**: one row per file in the video's `MEDIA/videos/<video>/SOURCES.tsv` with these columns: `file_path`,
   `media_url`, `page_url`, `author_outlet`, `license`, `resolution`, `fps`, `duration`, `description`, plus `credit` (the on-screen
   tag), `claim_risk`, `leak_check`; then a theme sheet. Reusable real-world clips (the subject's building, its people's interviews,
   the big news story) go in a **shared real-footage catalogue** in `kb/footage/`, next to `kb/FOOTAGE.md`, so the next video starts
   from the map, not from search.

Order of sources per need (fastest good result first): the catalogues (`kb/FOOTAGE.md`, `kb/footage/`) → the primary source's own
material (the maker's official videos, press kit, site, investor relations) → TV Archive (news) → network YouTube channels →
Pexels/Pixabay (generic) → Wikimedia (photos) → other creators → paid stock.

---

## 7. What real hunts taught (worked lessons for any niche)

How to log a find, one line each: **ID or URL · what · date · length · max quality**, plus `[T]` when its metadata (upload date and top
resolution) was fetched; a row seen only in search results has title, length and channel and nothing more. What's on screen isn't
known until someone looks: look before cutting, and scan every news package for leaked material.

1. **The primary source's channel first, every time.** New official videos appear there before any catalogue lists them (§0.3); some
   older pieces exist only on the maker's site [T].
2. **Investor material is a footage source.** For a listed company: the quarterly webcasts, slides and prepared remarks are on its IR
   page; the Q&A exists only in the webcast audio; the next call's date and link are posted ahead [P]. TV business channels (CNBC,
   Bloomberg) carry the chief executive's interviews around the results, in 1080p [T].
3. **A paywalled feature: the creator opens it, the receipts are screenshots.** The author's own video description can carry a gift
   link past the paywall, while the article answers 403 to curl [T]. A TV segment that interviews the journalist can tell the same
   story with pictures [T].
4. **Check the storyboard before trusting a title.** A long video whose title promised a visit was a talking head with no footage of
   the visit [T] (§3.1).
5. **The inside of a private place comes from TV news.** When the subject publishes no footage of its own insides, a TV report filmed
   on a visit has it, and so can a tech or business show's segment from the same visit [T]. **A report often reruns in several
   bulletins the same day and the next morning**: each rerun is its own archive item, so pick the best copy.
6. **TV Archive phrasing: exact phrases, not generic words.** A generic query buries the few right hits under unrelated ones [T]; a
   product's full name, an organisation's name or a quoted line works. **A person's name can return 0 hits** in captions [T]:
   captions misspell or never say names, so try the descriptive words (a role such as "the chief executive", the organisation)
   inside a date window.
7. **A viewer's compilation is a finder, not a source.** A compilation of "all footage" of a subject's people points to the
   originals; a re-upload of a broadcaster's interview means the broadcaster's own upload should be found and used instead [T].
8. **Podcasts and long interviews:** a long episode's heatmap (§3.1) points at the moments people rewatch, and the podcast's clips
   channel has often cut the episode into topic clips already [T]. Talk-show and radio appearances often survive only as re-uploads:
   find the station's own copy.
9. **Old material is soft:** a broadcaster's own archive channel can carry a restored copy (1080p25 in one case), while viewers'
   re-uploads of the same era sit at 360p, or at 480p and 12 fps (audio use only) [T] (§5.1).
10. **Photos of real places:** Wikimedia Commons often has several photos of one building, each under its own licence (CC0, public
    domain, CC BY-SA), plus organisations' logos as SVGs [T]; cut-outs come from the CC0 or public-domain ones (§1.1). The Wayback
    Machine shows an old site year by year (§3.6) [T].
11. **The people's own words:** interviews and press videos of the people behind a subject are on the news outlets' and the
    organisations' own channels, usually in 1080p [T]: use those uploads, not re-uploads.
12. **For "the industry" (peers, offices, the wider business):** peers' official channels (office tours, "life at" recruiting
    videos), regional broadcasters' reports, and a niche documentary channel's archive (old office tours, old press conferences in
    1080i) [T]; generic offices and desks from stock.

---

## 8. Paid services: what's worth buying (the creator decides; check prices again before buying)

| # | What | Price | What it improves | Call |
|---|---|---|---|---|
| 1 | **Storyblocks Unlimited All Access** (or Essentials without music/SFX) | €25/mo (€300/yr) or €18/mo (€216/yr), billed annually [P] | Unlimited 4K generic B-roll with consistent quality; **an MCP meant for AI agents**, which could make step 1 of the pipeline one call | **Worth a test month** once the pipeline exists: run 20 real "needs" from a real script through Pexels+Pixabay vs Storyblocks and count where the free set fails. Buy only if it fills real gaps. Note: no new projects with old downloads after cancelling [P]. |
| 2 | **Envato Core** | €14.50/mo annually, €29 monthly [P] | Stock video + **motion templates, SFX, music, fonts** in one | Overlaps with the sound and motion choices (`standard/SOUND_AND_VOICE.md`, `standard/research/MOTION_CRAFT.md`): decide together; "lifetime commercial license" on the page [P]. |
| 3 | **Filmot Patreon** | Patreon tier price not checked [U] | Search **all of YouTube by spoken words** without captchas: the fastest way to find "the clip where someone says X" | Cheap if the tier is a few dollars; check the tier on Patreon. |
| 4 | **PlayPhrase.me** | ~$3/mo [S] | Film/TV line search for meme/quote cuts | Only if film-line cuts become frequent. |
| — | Artlist footage (€29.99/mo), Adobe Stock (€29.99 for 1 video/mo), Pond5 / Getty / Newsflare (£180 a clip) | [P]/[S] | Cinematic stock / licensed editorial | **Not worth it**: news comes free from the TV Archive and network YouTube under commentary use. |
| — | Free: Pexels + Pixabay API keys, Deno, `curl_cffi`, `yt-dlp-ejs`, YouTube Data API key | €0 | §6.1 | **Do now.** Accounts are the creator's to create. |

Nothing here is needed to make a first video; #1 is the only candidate with a clear upside, and only after a measured test.

---

## 9. Open questions
- Channel-scoped search URL (`/@channel/search?query=`) through yt-dlp; date-sorted search (`sp=CAI%253D`).
- TV News Archive: maximum window length; whether 1080 US sources exist after some date.
- AP Archive / Reuters / British Pathé licence prices for YouTube; Videvo's licence; Pond5 current prices (all blocked or out of search
  budget).
- Storyblocks MCP: what it can do from an agent (search + download?), and which licence applies to MCP downloads.
