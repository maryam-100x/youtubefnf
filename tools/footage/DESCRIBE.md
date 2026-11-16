# The description pass: how a shot is written into the brain

Read by whoever (a model with eyes) fills `WORK/desc/<key>_desc.json` from the sheets in `FOOTAGE/index/brain/sheets/<key>/`
(WORK = `FOOTAGE/index/brain`). One sheet holds six shots, one row each: the shot's frames left to right (the clean span's start,
middle, end; more for a long shot), a 10% grid with its numbers (yellow along the top = x in tenths, cyan down the left = y in tenths),
the machine's boxes (yellow, numbered `0:person`, `1:car`...; green = a face with the name SFace gave it and its similarity), and a
header: the id, the frame numbers, the times, the length, the measured edge flags, the OCR'd words (`OCR:`) and the footage
catalogue's notes on that span (`CAT:`). `index.json` beside the sheets lists every sheet's shots (ids, frames, catalogue notes), so
the records can be written against it. Check a finished file with `EDIT tools/footage/brain_check_desc.py <key> <desc.json>`.

## The record, one per shot (JSON, a list of these per key)

```json
{"id": "A1@2.67",
 "desc": "Aerial over a hillside vineyard at dawn: mist in the valley, a tractor between the rows, cypress trees, a stone farmhouse far off",
 "who": [],
 "what": ["vineyard", "tractor", "cypress trees", "morning mist"],
 "action": "the camera drifts over the rows",
 "setting": "hillside vineyard, outside the village",
 "time": "dawn",
 "mood": "calm, warm",
 "flags": ["wide"],
 "subject": "the vineyard rows",
 "subject_boxes": {"f82": [0.05, 0.55, 0.95, 0.95], "f114": "b0", "f147": "f0"},
 "fit916": "no",
 "text_from": null,
 "missed_cut": null,
 "moments": [{"t": 1.5, "note": "a flock of birds lifts off the vines"}]}
```

- **desc**: one or two plain sentences a search would match: who does what, where, with the things in the frame named by their plain
  names (a "convertible", a "food truck", a "stand mixer", a "scoreboard overlay"). Specific over general ("the chef flips the omelette
  onto the plate" beats "cooking"). Say what is visible, never what you assume happens off screen.
- **who**: the named people when the face or the outfit says so, written as `kb/footage/names.json` names them (the people folders'
  names). The green face labels are evidence, not truth: a similarity under ~0.45 is a guess; a person in a cap, a mask or sunglasses
  is still that person when the outfit and build say so. Unknown people stay out of `who` and are described in `desc` ("a tall man in
  a grey apron").
- **what**: the nouns a script line could name (5-10): objects, vehicles by type, animals, places, signs, weather. Include the brand or
  sign text when readable (`OPEN 24 HOURS`, `MAIN ST`).
- **action**: the verb phrase; "quiet" shots get the camera's move ("slow push toward the window").
- **setting**: where; **time**: day / night / sunset / dawn / dusk / indoor / unclear; **mood**: two or three words.
- **flags** (only the ones that apply): `dark` (hard to read, would need a lift), `lowres` (soft or upscaled picture), `letterbox`
  (bars inside the frame), `ui` (an on-screen interface over the picture: a scoreboard, a menu, an app's screen, a camera's viewfinder readout),
  `text` (words or a logo on the picture), `blocked` (a fence, a window frame, foliage or an object between the camera and the
  subject), `blur` (heavy motion blur or defocus), `wide` (no single subject: an aerial, a landscape, a crowd with no one in front),
  `quiet` (no action), `action`, `social` (a social-media clip inside the frame with blurred side bars), `tv` (a TV or news broadcast
  picture inside the footage), `cinematic` (a staged camera with no interface on screen).
- **subject**: the one thing a 9:16 window should centre: the person the shot is about, the runner in the race, the animal. For a `wide`
  shot write the most interesting part of the frame anyway (the arena, the tower) so the window has something to hold.
- **subject_boxes**: the subject's box in the FIRST, the MIDDLE and the LAST frame shown on the row, keyed by the frame's number as the
  tile shows it (`f82`): either a machine box's number from that tile (`"b0"`, `"f1"` for the green face box) when it is the subject
  and tight on it, or a box read off the grid as `[x0, y0, x1, y1]` in tenths-based fractions (two decimals). The box holds the whole
  subject (a person head to feet when visible; a boat bow to stern). When the subject is not in a frame, that frame's key is left out.
- **fit916**: `ok` when a 9:16 window of at most the picture's height holds the subject whole with room; `tight` when it just holds it
  (zoomed out to the full height); `no` when the thing the shot is about cannot be held (two people far apart, a wide landscape).
- **text_from**: seconds into the shot when text or a logo appears over the picture (a title card, a social caption that pops in),
  null when text is there from the first frame or there is none.
- **missed_cut**: the frame number (from the tiles) where the picture changes to a different shot inside this record's span, when the
  tiles clearly show two shots; null otherwise. (The measured cut list can miss a cut between two similar shots.)
- **moments** (optional, long shots): sub-moments worth finding on their own, each with its second into the shot and a short note.
- **facts** (optional): the research facts the shot shows, `[{"via": "RESEARCH.md:184", "fact": "<the heading>", "ids": ["F-014"]}]`.
  `via` says where the link comes from: a research file's line (`FILE:line`), or `ours` (matched by eye, with a `note` and the fact
  base's `ids`). find_shot.py searches their words and prints the ids.
- **ui** (optional, a shot with an on-screen interface): the interface read exactly off the full-resolution picture, never off the
  sheet's tile: `{"frame": 41983, "read": "top right: score 2-1, clock 74:12. bottom left: a caption 'LIVE'. a banner 'TAP TO
  JOIN'"}`. `frame` is the file's frame the reading was made on (inside the shot); `read` names only what is legible on the zoom (a
  part that isn't says "unreadable"), with numbers, words and icons as printed. Zooms: `brain_zoom.py <KEY> <frame>` (the four
  corners at full-resolution pixels). find_shot.py searches and prints it.

## Beats: a long take cut into moments (cont_in / cont_out)

A long continuous take (a house tour that runs minutes in one take) is split into beats (`brain_cuts.py beats`): each record covers
one moment, but its edges are no cuts. The header's edge flags say `cont_in` (the take was already rolling) and `cont_out` (it rolls
on). Describe what the beat itself shows; `missed_cut` stays for a real camera cut.

## What matters most (the mistakes this brain exists to stop)

1. **The right moment for the words**: a "splash" entry must show a splash; a "cake collapsing" entry must show the cake collapsing. If a
   catalogue note claims an action the frames do not show, describe what the frames show.
2. **The subject whole and centred in 9:16**: the subject box is what the window is built from; a sloppy box makes a cut-off subject.
3. **Quality flags honest**: dark, soft, blocked, text, interface: the editor reads them before picking.
4. Names only with evidence; outfits count as evidence when the creator's footage keeps its people in recognisable outfits (write the
   outfits that identify each named person into `kb/footage/README.md` once, so every describer reads the same cues).
