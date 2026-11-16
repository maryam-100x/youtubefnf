# Verifying the cut candidates by eye

The strips: `FOOTAGE/index/brain/strips/<key>_cuts_NNN.jpg` (made by `brain_cuts.py strips <key>`), twelve candidates a sheet, one
row each. A row shows six consecutive frames: the three BEFORE the candidate frame, a red bar, then the candidate frame (its number in
yellow) and the two after it. The header gives the candidate's frame number (`#1194`), its kind, its time, the two measures (`hd`
colour-histogram distance, `d1` pixel difference to the frame before) and a note.

Kinds: `cut` (a measured jump), `black` (the first of a run of black frames: a fade-out's end), `flash` (a white frame), `dissolve?`
(a gradual change over ~12 frames with no single jump), `ext` (an edge the footage catalogue noted, nothing measured here: usually not
a cut).

## The one question per row

Is the frame right of the red bar the FIRST frame of a new shot (a different camera take), with the frame left of the bar the last of
the old one?

- Yes → nothing to write (the default is "ok").
- The new shot starts one or two frames earlier or later than the bar → `"+1"`, `"-1"`, `"+2"`, `"-2"` (the sign moves the cut
  forward in time: `"+1"` = the new shot's first frame is the one right of the yellow-numbered frame).
- The six frames are one continuous shot (a pan, a zoom, a fast move, a title fading in over the same picture, a social clip's
  caption changing, a person moving) → `"no"`.
- A dissolve (two pictures blended over several frames) → `"dissolve <first blended frame> <last blended frame>"` using the frame
  numbers printed over the tiles; when the blend runs past the six frames, give your best reading of its span.
- A `black` row: write nothing (the fade is handled); `"no"` only when the frames are not black at all.
- A `flash` row: write nothing when the frame right of the bar is indeed a white or near-white frame; `"no"` when it isn't.

## Write

`FOOTAGE/index/brain/work/<key>_verdicts.json`: `{"<candidate frame>": "<verdict>", ...}` with ONLY the rows that are not "ok".
Frame numbers as the header prints them (`#1194` → `"1194"`). Then `brain_cuts.py apply <key>`.

Also list, in your report, any row where you saw a cut the strips did NOT propose (two different shots inside one row with no
candidate between them cannot happen by construction, but a row whose first three frames already show two different shots means a
missed cut: report its frame numbers; the verdict `"cut"` on that frame adds it).

Read every sheet of your range in order; look at all six tiles of a row before deciding. The measures are hints: a `cut` with a low
`hd` between two similar shots is still a cut when the frames show a different take; an `ext` with high measures can be real.

## Library sheets (`LIB1_cuts_NNN.jpg` and the like)

A clip library's sheets (`brain_cuts.py strips_lib <CODE>`) hold the candidates of many clips in a row; each row's header starts with
the clip's name and the frame, `street_market_a#288`. Write the verdicts into `FOOTAGE/index/brain/work/<CODE>_verdicts.json` keyed
exactly that way (`{"street_market_a#288": "no", ...}`); only the rows that are not "ok", as above, then `brain_cuts.py apply_lib
<CODE>`. Clips at 25, 29.97, 50 or 60 fps show six consecutive frames of their own rate.

## Long takes

A house tour can run a minute or more with no cut. After the verdicts, `brain_cuts.py beats <key>` splits every take over 12 s into
beats at the catalogue's moment edges (`cont_in` / `cont_out`, no cut). A long take is also scanned for cuts the candidates missed
(`brain_cuts.py longscan <key>`: a pixel-difference spike 3.5x its neighbourhood, read in strips like these; most spikes are flashes, a
screen inside the picture changing, or a fade, and only a real camera change gets `"cut"`). A frame the eye wants as a beat edge (a
screen inside the picture changing) gets the verdict `"beat"`.
