# The footage brain: building it for the creator's own sources

A one-time, vision-built index of every shot the creator owns (their source videos, their clip libraries, their stills), searched
afterwards with no model at all. Building it is the heavy part (a decode of every file, detections, a description pass by a model
with eyes); after that every search runs on the CPU in seconds. The tools live in `tools/footage/`; this folder holds what the creator
fills (sources, names, synonyms, the catalogue) and what the build writes (`brain/`).

`PIPE` and `EDIT` below are the two pythons (`python tools/common/paths.py` prints them); `VISION` is the vision python (YOLO).
`FOOTAGE` is the media root's footage folder (`config/paths.toml`); `WORK` is `FOOTAGE/index/brain` (frames, strips, sheets, scratch:
never in git).

## What the creator fills

| File | What |
|---|---|
| `sources.json` | every source, a list (it starts as `[]`; the entry below shows the fields) |
| `names.json` | `{"alias as written, lower case": "the name records use"}`: every pass writes one name per person (`{}` until someone is named) |
| `synonyms.json` | `{"a word of the niche": "the plain word records use"}`: find_shot.py maps a script's words onto the records' (`{}` to start) |
| `catalogue.json` | the footage catalogue by theme (`{}` to start; `tools/footage/catalogue.py` has its schema; `kb/FOOTAGE.md` is its guide) |
| `brain/EVAL_LINES.txt` | the test: real script lines, one a line, a tab, a note on the shot it should find (`brain_eval.py`) |

A `sources.json` entry for each kind (paths relative to FOOTAGE, or absolute):

```
{"key": "A1", "kind": "video", "file": "sources/launch_film.mp4", "title": "The launch film (4:12)", "pic": [0, 0.0556, 1, 0.9444]}
{"key": "LIB1", "kind": "library", "folder": "clips/street"}
{"key": "IMG", "kind": "stills", "folder": "stills/press", "skip_copies_of": ["KIT"]}
{"key": "ART", "kind": "stills", "folder": "stills/artwork", "variants": true, "art": true}
```

- `key`: a short code (letters and digits); record ids start with it (`A1@712.93`, `LIB1/<clip stem>@3.20`, `IMG:<path>`).
- `pic` (video, optional): the picture inside the frame when it is letterboxed, as fractions (x0, y0, x1, y1); measure the bars with
  `ffmpeg -i <file> -vf cropdetect -f null -` and write them in, so a 9:16 window stays inside the picture.
- `proxy` (video, optional): where its 480p proxy lives; the default is `FOOTAGE/index/proxies/<stem>_480p.mp4`.
- `variants` (stills): one record per artwork, its `_portrait`, `_phone`, `_square`, `_tablet`, `_ultrawide` files listed beside the
  `_landscape` one. `art`: illustrated art, ranked lower unless a line asks for art. `skip_copies_of`: stills keys whose files (same
  name and size) this key leaves out, so a picture is never indexed twice.

Face labels: `FOOTAGE/people/<Name>/*.jpg`, one folder per person the creator wants named (clear, front-facing pictures; a folder
whose name holds " and " is a pair picture and is skipped). The names those folders give go into `names.json` as their own entries,
plus every short form a script uses. When the people keep recognisable outfits, write the cues here once, so every describer reads
the same ones (DESCRIBE.md, "What matters most", item 4).

Models: `MODELS/yolo/yolov8s.pt`, `MODELS/yunet/face_detection_yunet_2023mar.onnx`, `MODELS/sface/face_recognition_sface_2021dec.onnx`
(put there once), and two Hugging Face models the first embedding run downloads into its cache: all-MiniLM-L6-v2 (text) and
clip-vit-base-patch32 (pictures). Everything runs locally; nothing leaves the machine.

## Building it, one source at a time

A source video (`A1`):

1. `EDIT tools/footage/brain_cuts.py proxy A1` (its 480p proxy), then `features A1`, then `candidates A1`.
2. `EDIT tools/footage/brain_cuts.py strips A1`: the cut strips, read by eye (`tools/footage/VERIFY_CUTS.md`); the verdicts go into
   `WORK/work/A1_verdicts.json`; then `apply A1`.
3. A source with long continuous takes: `longscan A1` (missed cuts inside long takes, read by eye) and `beats A1`.
4. `EDIT tools/footage/brain_frames.py A1` (the frames every pass reads).
5. `VISION tools/footage/brain_detect.py yolo A1`, `EDIT tools/footage/brain_detect.py faces A1`, `EDIT ... text A1` (side by side).
6. `EDIT tools/footage/brain_sheets.py A1`: the description sheets.
7. The description pass: a model with eyes reads the sheets and writes `WORK/desc/A1_desc.json` (`tools/footage/DESCRIBE.md`); for an
   on-screen interface it reads `brain_zoom.py A1 <frame>`. Check it: `EDIT tools/footage/brain_check_desc.py A1 WORK/desc/A1_desc.json`.
8. `EDIT tools/footage/brain_build.py A1`, then `EDIT tools/footage/brain_embed.py --only A1`.

A clip library (`LIB1`): the same per clip with `--lib` (`brain_cuts.py features/candidates` per clip key `LIB1/<stem>`, then
`strips_lib LIB1`, the verdicts in `WORK/work/LIB1_verdicts.json`, `apply_lib LIB1`; `brain_frames.py LIB1 --lib`,
`brain_detect.py <mode> LIB1 --lib`, `brain_sheets.py LIB1 --lib`, the description pass into `WORK/desc/LIB1_desc.json`,
`brain_build.py --lib LIB1`, `brain_embed.py --only LIB1`).

A set of stills (`IMG`): `EDIT tools/footage/brain_stills.py prep IMG` (that key only: prep rewrites a key's shots file),
`brain_detect.py yolo|faces|text IMG`, `brain_sheets.py IMG --tile 960 --rows 4`, the description pass, `brain_build.py --stills IMG`,
`brain_embed.py --only IMG`.

These are heavy jobs (full decodes, detections, model loads): run them one at a time, never beside a render. "Used in" refreshes
itself from `kb/ASSET_LEDGER.json` on every build. Then the test: `EDIT tools/footage/brain_eval.py`, its sheets read by eye, the
verdicts (hit / near / miss per line) written into `brain/EVAL.md`.

## What the build writes (brain/)

| File | What |
|---|---|
| `<KEY>.json` | every shot of one source (or every clip of a library, or every still of a stills key): its records |
| `embeddings.npz` | MiniLM text embeddings of every record and CLIP picture embeddings of its frames (CPU, local) |
| `EVAL.md` | the test's verdicts, by hand |

A record:

```
id        A1@712.93             src, file, fps
in/out    712.933 / 714.933     seconds: the shot's first frame and the next shot's first frame; f_in/f_out = frame numbers (f_out inclusive)
clean_in/clean_out              the span to cut from: after a fade-in or a flash, before a fade-out or the next shot
desc, who, what, action, setting, time, mood, flags, subject{label, start, mid, end}
v         {cx, cy, h, cx1, cy1, fit}   the 9:16 window in curate.py's terms; fit ok | tight | no
faces, text, cat[[star, theme/group, note]], used_in[videos], moments[{t, note}], text_from, facts[{via, fact, ids}], ui{frame, read}
```

**Beats**: a take over 12 s is split at the catalogue's moment edges (`brain_cuts.py beats`), so a record is one moment with its own
frames, picture embedding and 9:16 window. `cont_in` / `cont_out` in `flags` say the edge is no cut: a cut placed there starts
mid-take (fine for an edit, the picture just keeps moving). **`ui`**: `{frame, read}`, what an on-screen interface shows, read on the
full-resolution frame (`brain_zoom.py`), searched by find_shot.py and printed under each hit; `read` names only what was legible.

Times to frames: a seek with `ffmpeg -ss t` lands on the first frame whose own time is >= t, so `t_for_frame(f) = f/fps - 0.3/fps`
(`brain_lib.py`); `brain_to_shot.py` writes `t` that way.

## Using it

```
EDIT tools/footage/find_shot.py "the moment the lid comes off" --vertical --min-dur 1.5 --exclude-used v11,v12 --sheet out.jpg
EDIT tools/footage/brain_to_shot.py A1@712.93 --key lid --at "lifts the lid" --dur 1.6
EDIT tools/footage/pick_boards.py boards videos/<video>/script.md <out dir>
PIPE tools/footage/cands.py out.jpg lid kitchen                (keywords only, a contact sheet of every match)
```

`find_shot.py` ranks every shot by the line's words (who/what count double, the catalogue's notes and the OCR'd words count too),
plus the meaning of the record's words (MiniLM) and what the picture shows (CLIP); `--no-embed` is keywords only and instant.
`--vertical` puts shots whose subject a 9:16 window holds first (`fit ok`), wide shots last. The sheet shows each hit's start, middle
and end frame with the window in red (and, with `--vertical`, the window itself), so the pick is still made by eye, just from the right
options. `brain_to_shot.py` prints a curate.py shot entry (`src`, `t` on the clean span's first frame, `cx`/`cy`/`h`, `cx1`/`cy1` for a
moving subject, `lift` for a dark shot, a `framed` note) and, for long form, a CLIPS entry, the ffmpeg cut (letterboxed masters filled
to 16:9) and the Foot line. `pick_boards.py` draws one board per script line with its top candidates and the first one's scene, and
cuts the picks.

## Keeping it current

A new source video: its entry in `sources.json`, then the steps above for that key. New clips in a library: the library steps (a
clip with a work file already is skipped by the frames and detections). A new set of stills: its entry, then the stills steps.
