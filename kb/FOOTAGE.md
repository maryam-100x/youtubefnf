# FOOTAGE: where to find what (the creator's sources)

The permanent map of every picture the creator has: their source videos, stills and clips, sorted by subject. The chat builds it once
by looking at every shot (the footage brain's records corrected by eye) and keeps it current as sources are added. Use it before
picking any shot, so the pick is the best moment that exists, not the first one that roughly fits. Example of the difference: for "the
lid comes off" the answer is the close-up at A1 11:52.95 where the lid lifts off the pot, not three shots of the pot on the stove.

How the chat builds it (once, then per new source):
1. The footage brain first (`kb/footage/README.md`): every shot of every source has a record with its description and frames.
2. Themes: the subjects the channel's scripts keep naming (people, places, objects, actions, moods), each with groups inside it.
   Write them into `kb/footage/catalogue.json` as the creator's niche needs them; one moment may sit in several themes on purpose.
3. Every shot is looked at (the brain's description sheets, `tools/footage/scan.py` for a short moment) and filed: the exact span
   (for an action, the action itself, scanned at 0.25 s or finer; for a calm shot, the shot), a one-line note of what happens, the
   crop note, the flags, and a star on the best picks.
4. `PIPE tools/footage/catalogue.py md` writes the theme files and the block at the end of this file; `catalogue.py sheets` the
   contact sheets; `catalogue.py coverage` lists every shot and still of the brain not yet in a theme, until none is left.

## How to use it

1. Open the theme file below (`footage/<theme>.md`). Entries are grouped by sub-subject, best picks first (★).
2. Open its contact sheet `FOOTAGE/index/catalogue/<theme>.jpg` (and `_2.jpg`, ... for big themes): every entry as 3 frames
   (20/50/80 % of the range) or the still, with source, time and note. One picture shows all the options.
3. Search across all themes: `PIPE tools/footage/catalogue.py find <word> [<word> ...] [--sheet out.jpg]` (one moment that sits in
   several themes is listed once, with all its themes). Ranked search over every shot: `EDIT tools/footage/find_shot.py "<the line>"`.
4. Need a single frame inside a range: `PIPE tools/footage/scan.py <video> <from s> <to s> <out.jpg> --step 0.25` (or 0.033 for
   frame-exact at 30 fps).

## Sources and how times are written

The codes are the keys of `kb/footage/sources.json`. Fill one row per source:

| Code | What | File (under `FOOTAGE/`) | Note |
|---|---|---|---|
| A1 | (the source's title and length) | `sources/<file>.mp4` | size, fps; letterboxed? (measured with cropdetect, never assumed); what it is mostly |
| IMG | Stills | `stills/<folder>/...` | its sub-folders; a watermark that must stay |
| ART | Artwork | `stills/artwork/...` | the `_landscape` file is listed; the `_portrait` / `_phone` one is the 9:16 pick |
| CLIP | A clip file | `clips/...` | length and shape |

- Times are `m:ss.xx` in that video (e.g. `A1 11:52.95-11:54.93`), seconds in brackets (`712.95-714.93 s`).
- 480p proxies for fast looking: `FOOTAGE/index/proxies/<stem>_480p.mp4` (the same timeline frame for frame).
- Every entry ends with a crop note for Shorts: `9:16 left / centre / right` = where the subject sits, `wide` = no single subject (a
  9:16 crop loses it). Flags: `dark`, `overlay baked in` (a social, news or camera frame inside the picture), `text on screen`,
  `letterboxed`, `on-screen interface`, `very short` (under 1 s), `quiet`, `action`.
- A social-media clip inside a 16:9 frame with blurred side bars crops to 9:16 almost perfectly: note it as such.
- Anything that looks like one thing and is another (a TV ad inside the footage, a reflection, a poster) is filed for what it is,
  with that said in its note.

## Searched and not found (do not waste time looking)

The list of subjects the chat looked for and did not find, each with how it was searched, so nobody searches again. A subject goes
here only after every shot and still was checked, and never "not in the material" without a frame-by-frame scan of the exact spot
someone remembers (`scan.py --step 0.033`): a first catalogue pass misses quick moments. When a later look finds it, the entry turns
into a FOUND line with its span.

- (empty until the first search that finds nothing)

## Keeping it current

- The data is `kb/footage/catalogue.json` (theme -> entries with src, in/out, start_s/end_s or path, note, star, crop, flags). The
  theme files and the block below are generated: edit the json, then run `catalogue.py md`; after adding entries run
  `catalogue.py sheets <theme>`. When you correct a note, fix every copy (`catalogue.py check` lists moments whose copies disagree,
  and paths that no longer exist).
- New material (a new video, new stills): add it to `kb/footage/sources.json` and the footage brain first, then add its entries here
  and run `catalogue.py coverage` until it reports nothing missing. Write a dated line here for each addition (what came in, where it
  sits, how many entries), and a "Not catalogued yet" line for anything held but not filed, so the next chat knows.

<!-- catalogue:start (generated by tools/footage/catalogue.py md; edit catalogue.json, not this block) -->

## Themes

| Theme | Entries | ★ | Sheet |
|---|---|---|---|

## Best of: the hero moments for the most common subjects

| Subject | Hero moments | Theme |
|---|---|---|

<!-- catalogue:end -->
