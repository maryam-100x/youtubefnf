# The production line: the machine's manual

*Part of `STANDARD.md`. Three gates around the making of a video, each one command, no model needed to run any of them: the **script
gate** before the voice, the **one-command build** in the middle, the **QA gate** before anything reaches the creator. Every video's
settings live in one file next to its script, `videos/<video>/video.toml` (the template with every key explained:
`tools/pipeline/video.example.toml`); no video gets its own copies of render, link, audit, finish or subtitle scripts. The craft stays in
`standard/LONG_FORM.md`, `SHORTS.md`, `SOUND_AND_VOICE.md`, `SCRIPTS_AND_PACKAGING.md`; the voice's own line is `standard/VOICE_LOCK.md`;
this file is how the steps run.*

PIPE and EDIT are the two pythons (`python tools/common/paths.py` prints them; ACCENT, the accent venv, runs only the voice guard's
embeddings). Every command runs from the repo root. Every step is `PIPE tools/pipeline/pipe.py <video> <step> [options]`; `<video>` is the
folder name under `videos/`, its number, or a path. `--version N` names the files (`parts_v2/`, `<name>_v2.mp4`, `QA_v2.md`): `render`
starts at 1, every other step takes the newest `render/v<N>_picture.mkv`'s version (by its date). Logs and machine outputs go to
`MEDIA/videos/<video>/pipeline/` (the video's media folder is `MEDIA/videos/<video>/`, or `[video] dj`). A step exits 1 when its gate fails.

## 0. The test render on a fresh setup

Before any video exists, the setup (`SETUP.md` step 5) proves the engine with a few seconds of the template composition
(`tools/motion/src/_template/`, registered in `tools/motion/src/Root.tsx` as `Template`):

```
cd tools/motion
npx remotion render src/index.ts Template MEDIA/tmp/test_render.mp4 --frames=0-179 --gl=angle
```

(MEDIA written out as the media root's path from `config/paths.toml`. In the setup's first chat, or in PowerShell, both commands run
through the studio's runner so they use its own Node and ffmpeg: `PIPE tools/common/paths.py --run --in tools/motion npx remotion
render ...`, `PIPE tools/common/paths.py --run ffprobe ...`.) It passes when the file holds all 180 frames:
`ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=width,height,nb_read_packets -of csv=p=0 MEDIA/tmp/test_render.mp4`
prints the composition's width, height and `180`. That proves headless Chrome (Remotion fetches it on the first render), the GPU
renderer and ffmpeg. If it fails on the GPU (a GL or driver error), run it again with `--gl=swangle`; when that one passes, this computer
renders in software for good: `Config.setChromiumOpenGlRenderer('swangle')` in `tools/motion/remotion.config.ts` and `gl = "swangle"`
under `[render]` in every `video.toml`. Delete the test file after. Nothing else runs during the setup, so this one render goes without
heavy.py's ticket; every later Remotion job takes one (section 2). The first real proof of the whole line is a video's own
`render --frames a-b` (a test range, below).

## 1. The script gate (before the voice)

`pipe.py <video> script` runs `tools/script/script_lint.py --strict` on `script.md`'s newest Beats block (its flags in
`pipeline/lint.json`) and stops the line on a fix-level flag (a named tell, a vague form, a time word, the subscribe ask too early, chapter
cards in a topic video, a long video not ending on its sign-off word); the look-level flags (a take's lead-in, a big number with no point,
long sentences, lines earlier scripts also have, a reporter's share of said/told lines) are read and kept or fixed by hand. `--force` goes
on past fix flags once each kept one is written down; `--ignore <ids>` passes named checks. What every check stands for: the lint's
docstring and `standard/SCRIPT_TRAINING.md`; the niche's own word lists: `tools/script/niche.json`. Tests: `tools/script/tests/`. The gate
can't judge a hook's pull, what a viewer wants to know, humor or a fact's truth: the fresh-listener test and the creator's interview stay
(`standard/SCRIPTS_AND_PACKAGING.md`).

## 2. The build (long form)

| Step | What it does |
|---|---|
| `voice` | the voice in one step (`standard/VOICE_LOCK.md`): `voice_ready.py require` (every stage the voice needs, names measured), the voice chain (`tools/sound/voice_chain.sh`: from the layout, the chain, the sound gate), then `voice_lock.py lock` with the gate's PASS line as its note. While `videos/<video>/voice_lock.json` exists, `render`, `patch`, `score` and `finish` run `voice_lock.py verify` first and refuse on a changed voice |
| `link` | the lean public dir of hard links (`[render] pub`, default `MEDIA/pub<id>`) from the full public dir `MEDIA/motion`: `[link] folders` whole, `files`, every path the `scan` sources name (`const C = 'dir/'` + `C + 'file.mp4'` pairs, quoted media paths, the video's code subfolders included) and every `src` of the receipt lists in `pages`. Remotion copies the public dir into its temp on every render, and the full one runs to tens of GB. A file the code names that isn't in `MEDIA/motion` fails here, not in the render. `--list-extra` lists files in the lean dir the sources don't name. `gate`, `stills`, `patch` and `render` run `link` first |
| `audit` | the static clip audit without a render (`tools/pipeline/audit.tsx` filled from `[audit]`, bundled with esbuild): OVER, a play asking past its file's length in `src/clipdurs.json` (the frozen seconds named); SHORT, a shot under `[audit] min_shot` (0.5 s: it reads as a flash); SHORT PLAY; SLOW, a play under 1.0x (a cut, never a slowed clip, outside a deliberate replay); files missing from clipdurs.json; CAPTION, an on-screen string that reads like a working note (an opinion label, a fact id, a rule or review number, a beat id, TODO, TBD, placeholder, XXX); MARK, a card mark over half its text (a mark on most of the text is no mark); BEAT, a spoken beat of 2 s or more with no shot starting in it (it plays under the shot before); `rate={0.` anywhere in the code; clips with B-frames (Remotion grabs wrong frames from them: cut with `-bf 0`). Then EDGE: both edges of every video play against its source's own cuts, fades and flickers within `[audit] edge` (0.5 s), by ffmpeg's scene score (`[audit] scene`, 0.3) and frame by frame (a cut between two dark shots scores only 0.15; a dissolve is 3+ hot frames in a row): a sliver of the shot before or after. Each hit is looked at on its frames (fast motion can score like a cut). `--no-edges` skips the scan, `--soft` reports without failing |
| `gate` | **the pre-render gate: `render` refuses code it hasn't passed** (section 6). Three halves: sound A1-A13 + LOCK (`tools/sound/gate_sound.py`, `standard/VOICE_LOCK.md`), picture B0-B26 (`gate.py` + `tools/motion/gate_probe.mjs` + `src/gate.tsx`: every frame probed with no video fetched), and, for a long video, coherency (`tools/pipeline/coherency.py check`: `videos/<video>/COHERENCY.md` carries the current stamp of a fresh read of this exact script and code, every flag closed). Needs the voice stage (`stages.py`; `--no-stages` skips). Report `pipeline/gate.md`, flags in `pipeline/gate/flags.json`; `pipeline/gate/passed.txt` holds the code's stamp only when all three halves pass. `--full` forces a full probe, `--reuse` keeps the last probe when the probe stamp is the same, `--reprobe a-b,c-d` probes given ranges into the last full probe, **`--scope a-b,c-d [--out <report>]`: the scoped gate** (section 9), every builder's and fixer's own loop, never a pass |
| `plays` | every clip play's first, middle and last frame on sheets in `pipeline/plays_v<N>/` (`plays_sheet.py`, from a fresh audit), plus a list of the plays with a black or card-on-black frame: a play can open on a disclaimer card, black, an end card or a stray logo for over a second, and neither the edge scan nor the proof stills look at it. Read every sheet before every render |
| `stills` | proof stills with one bundle (`stills.mjs`): `--frames 120,600`, `--shots 3,4` or `--every` (`--offset 0.5` s into each shot; `--ends` adds each shot's last frame, a graphic's end state), `--sheet` tiles them, `--scale` (0.5), `--out` |
| `render` | **the picture in parts at 1440p** (section 10): one lean bundle, one browser, parts of `[render] part_frames` (3000); the frame count is the composition's own, never video.toml's; each part whole or not at all; a failed part again at concurrency 4, then 2, alone, the rest go on; a lost frame re-encodes its clip and the part again; a kit3 refusal stops the line with its reason; a part stalled 5 minutes is killed and retried; the GPU guard after every run; **the render scan on every full render**. A full render needs the stages (prototype, the locked voice, the picture; `--no-stages`), the voice lock to verify and the gate's pass on this code (`--skip-gate` only on the creator's explicit word). `--only 3,4` redoes parts, `--changed` the parts whose shots changed since they were rendered, `--frames a-b` one test range into `render/test_v<N>/` (no gate, no stages), `--no-scan` skips the scan, `--concurrency`, `--chunks`, `--scale`, `--gl angle|swangle`, `--wait <minutes>` |
| `patch` | re-rendered frame ranges as segments with one bundle (`segs.mjs`): `--ranges 3600-3659,...` -> `render/patches_v<N>/patches.json` (merged with the earlier ones by file); `finish --patches` lays them in |
| `score` | the mix from the cue sheet (`[score] cues`, `tools/sound/score.py`, under heavy.py's `score` ticket) -> `build/score/mix_v<N>.wav`; the report's key lines printed, the whole report in `pipeline/score_v<N>.log`. Refused: a long video's bed under 20.5 dB voice over music in score.py's own voice-music column (about 22 wanted: the cue sheet's mix block GAP_MIN 22 / CARVE_DB 8 / UNDER 13 is missing), and a mix whose length is not the composition's within 0.1 s (the cue sheet's DURATION must be the picture's: the last word's end plus the tail, as the composition counts it) |
| `finish` | the upload file: the `.srt` and the chapters first (seconds, before the encode), then the mix muxed onto the picture, `tools/motion/finish_long.py` (4K60 on the GPU when `[finish] gpu`, its sound settings `[finish] args`: `--lufs -14 --gain-only`), under heavy.py's `finish` ticket; then the stutter check (`qa_cadence.py --stutter`) unless the render scan passed this picture, and the file's numbers. Refused: a picture whose frame count isn't the composition's (an older render's picture under the same name), a mix 0.5 s or more off the picture's length (another version's mix). `--patches <json>` lays segments in; `--video-from <delivered.mp4>` redoes only the sound; `--test 60-70` runs the whole chain on those seconds first, into `render/test_v<N>/`; `--out` writes elsewhere (the 4K beside the review copy); `--mix`, `--picture`, `--no-stutter`, `--loose` |
| `srt` | the upload subtitles: the captions' srt (`python -m dj captions` on the final voice, `[srt] captions`) with the `[srt] fixes` (each must still apply: a stale fix means a new voice, look; `--loose` writes anyway); every `tools/sound/names.json` name back to the script's spelling where Whisper wrote it as heard; the real voices' lines in the holds (`[srt] holds`: `[beat, from, to, "Name: line"]`); every cue lingers into the pause after it (up to 0.6 s, never into the next cue; the last 0.8 s, inside the film), so a one-word cue never flashes. `--captions` another srt, `--out` |
| `qa` | the QA gate (section 4) |
| `all` | link, audit, render, finish, qa |

**The order of a build:** `script` -> `voice` (`standard/VOICE_LOCK.md`; the edit's word times by `tools/motion/sync_words.py`) -> `link` ->
`audit` -> `plays` -> `stills` -> `score` -> `gate` (all three halves pass) -> `render` (its scan included) -> the watchable copy to the
creator the minute it exists -> the creator's watch is the fix list -> `finish` -> `qa`. Every builder and fixer runs `gate --scope` on their
own shots until it is clean before handing them back (section 9); the full `gate` then only confirms.

**The watchable copy** is the render's own 1440p stream with the mix, made in seconds, no review of the chat's between the render and the
creator: `ffmpeg -v error -y -i MEDIA/videos/<video>/render/v<N>_picture.mkv -i MEDIA/videos/<video>/build/score/mix_v<N>.wav -map 0:v:0
-map 1:a:0 -c:v copy -c:a aac -b:a 320k -ar 48000 -movflags +faststart MEDIA/videos/<video>/export/<name>_v<N>.mp4`. The 4K finish starts
beside it by default (`pipe.py <video> finish --version N --out MEDIA/videos/<video>/export/<name>_v<N>_4k.mp4`) and is cancelled only for a
major issue in the creator's watch; `qa --export` names the 4K file.

**After the creator's notes:** samples first for what is their judgement (`tools/motion/ab_samples.py <delivered.mp4> <new_mix.wav>
<items.json> <out.mp4>`: each spot twice, A as delivered, B fixed), one measured fix for a plain error; every sample through
`PIPE tools/pipeline/sample_check.py <old.mp4> <old_at_s> <sample.mp4> --claim a-b` (the spans that changed against the version the creator
watched; a claimed change with nothing changed in it fails) before it goes out. Then `patch` + `tools/motion/splice_patch.py <delivered.mp4>
<picture.mkv> <patches.json> <out.mp4>` into the delivered file (only the stretch around each patch re-encoded, keyframe to keyframe:
about a minute; `standard/LONG_FORM.md`), or `finish --patches` (a whole new encode), or `render --changed` for the parts whose shots
changed, or `finish --video-from` for a sound fix; a full render only when the timing moved everywhere.

**The audit sees only components named in `[audit] plays` whose call carries `src=`.** It walks each shot's element before the render: a
wrapper that builds its file path inside (`<Frame43 n="x">`, `<Wide n="x">`) is invisible to it, and its clips are never checked for
overruns. Every clip-playing component gets `src="<path>"` at its call and its name in `plays` (default Foot, VClip, VideoCard,
Clip; `[audit] bg` the components with `bg` + `bgStart`); the audit strips trailing digits from a name (`Frame43` is `"Frame"`). After adding
one, compare the clip names in the code with the audit's plays: none missing.

**One Remotion job at a time.** `render`, `stills`, `patch` and the gate's probes hold heavy.py's `render` ticket: they wait until no other
heavy job holds a ticket on the computer and no headless browser of another tool runs (`--wait <minutes>` gives up instead of waiting; the
default waits as long as it takes, saying so every 5 minutes). Two renders side by side kill each other. After every Remotion job the line
sweeps Remotion's leftovers in `MEDIA/tmp` (a browser profile and an assets folder per run), counts the headless browsers left and sizes
the bundle copies there. `PIPE tools/pipeline/heavy.py` shows what holds the computer now; a shell script takes its ticket through
`tools/motion/with_remotion_lock.sh "<what>" <command>`.

**Nothing heavy beside a render; a chain stops at a failed step.** heavy.py's kinds: `render` runs alone; `cutout` (a background-removal
cut-out, the matting models) never beside a render, never two at once; `finish` and `score` never beside a render, beside one cut-out at
most; and a job starts only while the tickets' memory plus its own stays inside the budget set in heavy.py for this computer (`BUDGET_GB`:
lower it on a smaller machine) and the system has that memory free (Windows: the commit headroom, RAM + page file; macOS: free RAM plus
free swap). A memory-heavy job beside a render starves Remotion's compositor ("No frame found") and kills a part. Light work beside a
render is fine (scripts, numpy layers, ffmpeg stills). The hook `tools/hooks/commit_guard.py` refuses to start a heavy job while memory is
at or over 85% (cut-outs and depth passes 70%, a whole-narration voice job 60%). While the creator uses the computer for heavy work of
their own, every heavy or GPU job waits for their go. A chain of steps reads each step's exit code (`pipe.py ... > out 2>&1; rc=$?`), never
through a pipe that hides it, and stops at the first failure.

## 3. The build (a Short)

A Short (`kind = "short"`, or "short" in the folder name) runs `link` -> `gate` (shots from the probe: a built Short is gated too) ->
`render` -> `finish` -> `qa` (`all`: link, audit, render, finish, qa). `render` is one Remotion render of the composition into
`render/p<id>_v<N>_render.mp4` (a browser that didn't come up, a lost frame, a GPU access violation or a stall gets one more try after
45 s; a finished file left as Remotion's temp by a failed rename is moved into place; the frame count is checked). `finish` burns the
captions in (`tools/motion/finish_short.py <video> <render> <name> --picture-only`), lays the score on (`score.py` with `[score] cues`
and `--picture`), runs `qa_render.py --format short --voice` and `qa_holds.py` and tiles a 2-fps sheet; ffmpeg and Python only, so it can
run while the next video renders. A Short's framing is checked before the line on `EDIT tools/motion/frame_review_at.py <id> --cols 6`
(`standard/SHORTS.md`).

## 4. The QA gate (before it goes to the creator)

`pipe.py <video> qa --version N` runs every check there is on the finished file and writes **one report**, `videos/<video>/QA_v<N>.md`
(pass/fail per check with its numbers and what it stands for, then the delivery checklist: the eye's part no tool can do, to tick before
delivery, and a place for every kept flag and its reason), plus `pipeline/qa_v<N>.json`. Exit 1 on any FAIL. A WARN is a filter's flag with a
sheet to look at. `--export <file>` checks another file than `export/<name>_v<N>.mp4`; `--deep` adds the whole-film flash scan;
`--no-edges` skips the edge scan.

| Long form | Shorts |
|---|---|
| the file's shape (3840x2160, 60 fps, the composition's length within 1 s) and loudness (-14 ±0.5 LUFS, true peak at most -1 dBTP) | the shape (1080x1920, 60 fps, the timeline's length within 0.6 s), loudness, and the end 0.15-0.8 s after the last word (the bar ~0.4 s, no end card) |
| `tools/qa/qa_render.py --format long` (flash shots, freezes, holds, repeats, bars, soft shots, loudness; `[qa] allow` ranges kept on purpose) | `qa_render.py --format short --voice` (plus the flash open on frame 0, the talking gaps) |
| the static clip audit (FAIL) and the clip edges (WARN, every hit listed), as in `audit` | `qa_holds.py`: nothing over 2.6 s without a change (FAIL) |
| on-screen strings that read like working notes; card marks over half their text (FAIL) | the word sheet (every 0.5 s with the word being said) and a 2-fps sheet, for the eye (INFO) |
| `rate={0.` in the code; broken characters in the code (`Â`, `Ã`, `â€`, a `\u` escape inside a JSX attribute, which prints as typed) (FAIL) | |
| the card cameras: `tools/motion/qa_camera.mjs`, 0 two-move cards (a card's camera makes one move, from its first frame) | |
| the stutter check on the picture (`qa_cadence.py --stutter`); short black frames (blackdetect: a black stretch under 0.2 s inside the film, a section's last frame rendered black: each one looked at) | |
| the subtitles present and inside the length | |
| the reuse check against the last three videos (`tools/motion/reuse_check.py --last 3`: a graph taken 1:1 from another video's code is a WARN; footage and stills are information) | the same |
| the score's report: no silence outside the designed ones; voice over music in the band **20.5-24.0 dB** (about 22); effects at -7 LU or under against the voice over 1.5 s (FAIL), no memey effect outside a joke (WARN) | the same, the band **16.0-19.5 dB** (about 17-18) |
| `--deep`: the whole-film flash scan (`qa_flash_scan.py`) | |
| no headless browser left after the job | the same |

The gate is a filter, never the proof: the sheets it writes are read by eye, and every note the creator gives on one video is checked
everywhere in it. A check a new tool adds goes into `tools/pipeline/qa_gate.py` with what it stands for. The reviewer's eye
(`standard/REVIEWERS_EYE.md`) and the self-review list (`standard/CHECKLIST.md`) are the eye's part.

## 5. Adding a video to the line

1. Copy `tools/pipeline/video.example.toml` to `videos/<video>/video.toml` and keep what the video needs: `[video]` (id, kind, name, comp,
   src, module, fps, dj, frames when the composition ends before the voice file's tail), `[render]` (pub, part_frames, concurrency, scale,
   preset, crf, parallel, image_format, jpeg_quality, timeout_ms, gl, scan), `[link]` (folders, scan, pages, files), `[audit]` (plays, bg,
   min_shot, edge, scene), `[gate]` (clips_json, sources, leads, `[[gate.signed]]`), `[score]` (cues, mix), `[finish]` (args, gpu), `[srt]` (captions,
   fixes from `build/warnings.txt`, holds), `[qa]` (allow), `[voice]` (inserts).
2. The composition (`tools/motion/src/<video>/`, started from `src/_template/`) exports `SHOTS` (`{at, el(dur)}[]`) and `<NAME>_SECONDS`,
   built on the edit's `words.json` and `beats.json` (`sync_words.py`). Clips are cut by the video's prep script
   (`tools/motion/prep_template.py`) with `-bf 0`, their last frames written into `src/clipdurs.json`, never straight into the public dir.
3. It is registered as `component={gated(X)}` in `src/Root.tsx` (or in its own `src/<video>/root*.tsx`, gated too, run with
   `QA_ENTRY=<its entry>`): the gate refuses one that isn't (B0). It plays video only through `lib.tsx`'s `Clip` or kit2's `SpeedRamp`.
   `[gate] clips_json` names the clips manifest (a file, a glob or a list: several prep files' manifests merge). Credits, name lines, stamps
   and connector labels carry `data-gate` (`"credit"`, `"name"`, `"stamp"`, `"mid"`) and may sit on pictures; a count-up's digit slots carry
   `data-gate="roll"`; a mark into a picture `data-gate="mark"` (a hollow outline counts without it); a face icon `data-gate="icon"`.
4. `pipe.py <video> link`, then `audit`, then `gate`: all must pass before the first render; the first `render --frames 0-299` proves the
   line on this video.
5. Tests: `PIPE -m pytest tools/pipeline/tests tools/script/tests -q` (the gate's by-design cases, the crash rule, the marks and rows checks,
   the incremental probe's pieces and the render scan on synthetic probes; the lint on its own cases).

## 6. The gate in detail

**How it sees.** `gate_probe.mjs` renders every frame of the composition in the gate mode (`src/gate.tsx`): no video is fetched; every clip
reports the source second it shows, every text, picture, clip pane and drawn mark its real box (with its blur and brightness). A full
probe takes roughly a minute per minute of film; after the first one the probe is incremental (section 7).

**The picture checks** (each flag is fixed, or allowed with proof; `--scope` runs B0-B23):

- **B0** the composition is `gated()` in `Root.tsx` (or a `src/*/root*.tsx`) and plays video only through `Clip`/`SpeedRamp`, else the
  probe can't see its clips.
- **B1** FREEZE: a clip asked past its file's last frame, in any graphic. STILL: a designed stretch (no clip on screen) standing still, by
  `qa_render`'s frozen test on the probe's own pictures (the frame's mean grey change at 90x160 under 0.45 on the probe's pictures, 0.35 on
  an export, for 2 s in long form, 0.8 s in a Short). HOLD: a held picture
  on a beat inside a play (24/25-fps footage stored as 30: a hitch several times a second).
- **B2** FLASH: a cut, dissolve or fade of the source within 0.3 s of a play's exact in or out point, each confirmed on the picture (a cut
  = the next frame unlike this one, far below the clip's own frame-to-frame likeness). FADE / DISSOLVE: a play that opens or closes inside
  a fade or a dissolve (to a viewer it is a flash frame).
- **B3** GAP: a frame inside a shot where a clip pane drops out and comes back. BLANK: 1-6 frames with nothing lit between pictures that
  fill the frame (an empty frame in the composition, or a delayRender released before what it waited for mounted). BLANK_LONG: 0.5 s or
  more with nothing to see (no lit picture, no text): a critical failure to a viewer.
- **B4** TEXT_CUT text cut by the frame or its card; MARK_CUT a lit phrase pushed past the frame; TEXT_ON_TEXT; CREDITS_STACKED;
  TEXT_CUT_BY_PIC a picture's edge through text; OFF_FRAME an object half off the frame; BOTTOM a big label under the player's controls;
  EMPTY_SLOT; PIC_ON_PIC two pictures drawn over each other. LETTERBOX (Shorts) a letterboxed source's black bars on screen;
  LETTERBOX_CUT (long form) a clip of a letterboxed source cut without its bars, so cropped and blown up (long form shows such a source
  whole, its bars kept); ASPECT a clip drawn at another shape than its file; UPSCALE a zoomed clip showing its file's pixels past 1.3x (a
  1080p cut zoomed is soft: the prep script cuts a zoomed clip from the 4K master). EMPTY (Shorts) a small picture on a plain ground, most of
  the screen nothing.
- **B5** MOVING_AT_CUT something still moving in a shot's last 0.25 s; MARK_LATE a highlight drawing in the last 0.6 s; SHAKES more shakes
  than impact sounds; YOYO a change that springs back; REVERSE a picture that travels 30 px or more one way and then 8 px or more back
  (one move, one way).
- **B6** SOUND_NOTHING_SHOWN an effect with nothing appearing, moving or cutting within -0.1/+0.2 s; MARK_SOUND_OFF a marker cue with
  nothing lighting on it while a mark lights within 1.2 s (and no other marker cue owns that light): named with the light's own time, the
  cue moves, **never allowable**. A count sound is cut to its count: `tools/sound/palette.json`'s `needs_dur` makes score.py refuse
  `pal('count_up')` without `dur`.
- **B7** OVERUSED a clip the creator named as overused (`tools/pipeline/gate_overused.json`, empty when the repo ships); TWICE the same
  stretch of a source shown twice in one video, under one clip name or two.
- **B8** CUTOUT chunks missing from a cut-out; CUTOUT_HALO a cut-out over its own blurred copy; CUTOUT_ON_CARD a cut-out on a box.
- **B9** CREDIT a clip credited to another source than its own.
- **B10** (Shorts) CAPTION_TWICE a stamp, count or label showing a word the captions show at the same time (the word goes into
  `videos/<video>/captions_hide.json`: text shows once); CAPTION_OFF_LINE a text that replaces hidden captions but sits off the caption
  line (its centre more than 130 px from y 960).
- **B11** PAN (Shorts) is off: a pan is used only when it has a job, and no check can know its reason; `GATE_B11=1` runs it as information.
- **B12** MARK_MOVES a box, ring, label or highlight that leaves its target: over a playing clip (the picture is held while a mark shows),
  or sliding more than 2 px from its place in a still or page that moves under it; a mark riding with its picture is fine.
- **B13** TEXT_OVERLAP two visible texts at rest whose letters intersect by more than 2 px each way, or a text running more than 2 px out of
  its card (B4's TEXT_ON_TEXT needs 15% of the smaller box and misses an edge sliver; B4's TEXT_CUT sees only clipped text).
- **B14** ROW_CENTRE a row of pictures (two or more on one floor at one height) whose visible content (the pictures' alpha bounds and their
  name lines) sits more than 8 px off the frame's centre, or whose gaps differ by more than 8 px; kit3 rows are read by `data-kit3="row"`.
- **B15** KIT3_REFUSAL a kit3 piece refused its input on these frames (`gate.tsx` catches it per frame; the reason is the flag; fix the
  input, never the kit). CHECK_CRASHED one check crashed: a flag naming the check, the error and where it was raised; the other checks still
  read; it blocks the pass and is fixed in the check, **never allowed**.
- **B16** MARK_OFF / MARK_REDUNDANT (`tools/pipeline/qa_marks.py`): a mark's border on letters, punctuation or a rule, a wash's edge through
  letters, a box across two lines or past its card, 60 px or more of blank beside its words; or nothing to pick the marked thing out from.
  MARK_LOOSE and MARK_UNSAID are information (`pipeline/gate/marks/`).
- **B17** LIT_UNSAID a lit phrase whose words aren't said within the window round its light (`tools/motion/qa_lit.py`): to look at, not
  blocking (a synonym flags too).
- **B19** (long form) CARDS (`tools/motion/qa_cards.py`): CARD_REASON a card shot (kit3's Page, Read, NumberBeside, BigNumber, TextBlock,
  Headline, Card and their kin) with no `// card: <why the text itself is the point and no picture shows it better>` above it; CARD_TIME
  cards on more than 8% of the film's screen time (the probe's `shots_<comp>.json`); CARD_CLOSE two card shots under 20 s apart.
- **B20** (long form) `tools/motion/qa_still_words.py`: STILL_UNDER_ACTION a held picture for most of a phrase of action or change;
  CARD_FOR_MOMENT a text or page card under words that name a moment you can see; MARK_SMALL a lit mark under 48 px tall at its full light;
  MARK_CORNER a lit mark in the frame's outer corner.
- **B21** (long form) `tools/motion/qa_centred.py`: LOGO_OFF_CENTRE a lone logo or hero object whose visual centre sits more than 12 px off
  its point left to right (3D pieces by kit3d's own measure); ICON_FACE_OFF a round profile icon whose face is off its circle's centre or
  the wrong size in it; ICON_NOT_REAL an icon not cut from the source's own footage (`make_icon.py`).
- **B22** (long form) `tools/motion/qa_shots.py`: SUBJECT_MISSING a still or a cropped/zoomed clip with no `// subject: [label] x y w h [-> x y
  w h]`; SUBJECT_LOST the subject not found at a glance where it lands (off-centre, cut, small or dim); ART_OVER_REAL artwork (a poster, an
  illustration) of people the source's own pictures show, with no `// art: <why>`; ART_CLOSE a third artwork shot inside 20 s; ART_SHARE artwork over its share of the
  film (full gate only); DARK a picture too dark to read where it stands alone (night shots by the footage brain pass).
- **B23** (long form) `tools/motion/qa_devices.py <video> [--list]`, from the code, no probe: DEVICE_SPREAD one graphic component the main
  picture of more than 6 appearances (a run of consecutive shots of it is one; its range copies are one device) with no `// device: <why
  this line needs it>` above a shot; ROUND_CROP a round crop of a screenshot as a shot's picture (Chip, PlacedIcon, kit3 Still's `icons`, a
  face circle over a clip), outright: the portraits of the video's main people (`[gate] leads`) only where the words under the shot name them and the shot
  says `// device: portrait <why>`, or `// device: passed <the creator's words>`; STAMP_PHRASE a stamp with no number, multiplier or record,
  or one asking a question, without `// stamp: <why it is the headline claim>`.
- **B24** TEXT_SHORT a text of ours at reading size on screen under its reading time (1.2 s, +0.03 s a character past 10), across cuts.
- **B25** MARK_SMALL a mark on a thing under 4% of the frame on a full-frame picture that never zooms into it (1.6x within 0.7 s: kit3
  Foot's zoom); **B25b** MARK_BLINK a mark lit under 0.5 s that goes while its picture stays.
- **B26** OUTRO the last 25 s ask for a like and a comment and the house SignOff never shows.
- STILL_SOURCE a full-frame clip standing still in its own source (a slide, a web page): to look at, not blocking (the eye's call).

Every gate tool reads the video's code folder with its subfolders. B17 and B19-B23 never take the gate down: a check that can't read says
why in the report.

**The sound half** is `EDIT tools/sound/gate_sound.py <video>` (A1-A13 + LOCK; what each catches and its numbers:
`tools/sound/SOUND_GATE.md`; the voice lock's checks: `standard/VOICE_LOCK.md`). It reads the same `gate_allow.json`. **The coherency
half** (long form): `EDIT tools/pipeline/coherency.py packet <video>` writes the packet (the script line by line, the interview, the real
voices, the shot table in film order, with a stamp of the inputs); a fresh reader (an agent never told what the chat thinks) writes
`videos/<video>/COHERENCY.md`; the chat closes every flag ("fixed: ..." or "allowed: <proof>"); after fixes the stamp changes and the read
runs again until it comes back clean; `coherency.py check <video>` is the gate's half.

**A flag means a fault.** The by-design cases are told apart inside the checks, so a flag is fixed, never argued:
- EMPTY_SLOT: an outline named a mark, or lying on a lit picture bigger than itself, is a mark.
- STILL: no still-candidate while a mark is on screen (B12 wants the picture frozen under its marks), on a big still under the house push
  (0.5%/s or more), on a card being read (8+ words of our text at 26 px+, never over an interview bite), or (long form) on a built graphic
  (boxes or svg over 5-90% of the frame, or no sharp picture) standing under 6 s; a lone picture card with none of our words stays a
  candidate. A full-frame clip standing still in its own source is STILL_SOURCE (listed).
- DISSOLVE: kept only when no motion explains the change (`qa_fades.confirm_dissolve`: each 12-px block's best shift within 5 px; 0.8 or
  more of the change left unexplained). FADE: kept only when the picture reaches black or white within 0.6 s past the edge
  (`confirm_fade`): a camera's exposure (into the sun, into shade, a lightning flash) is no fade.
- Grounds: a clip blurred 6 px or more or dimmed under 0.35 (opacity x brightness) shows neither its cadence nor a dissolve's double
  picture: HOLD, DISSOLVE and ASPECT skip it.
- TWICE: one clip restarted back to back is a loop. TEXT_OVERLAP: only texts at rest. TEXT_ON_TEXT: rolling digits (`data-gate="roll"`)
  pass each other. Words moving 3 px a frame or more (180 px/s) are in flight, not read (TEXT_ON_TEXT, TEXT_CUT).
- MARK_MOVES: a page that holds the whole mark is its target even under 2.5x its area. MARK_OFF: an untagged round or square ring is a
  graphic's ping, not a mark. B25: a picture already drawn 1.6x or more is the zoom.
- SOUND_NOTHING_SHOWN: an effect on the music's own turn (the bed's level moves 4 dB across it), on an event inside the footage (its
  picture changes 2.5x its usual) or on a probed spot mark counts as shown.
- SUBJECT: a letterboxed source shown whole is no window; a zoom's subject is judged where it lands; a small subject under the spot light
  is found; a built graphic's ground needs no subject. STILL_UNDER_ACTION: pieces acting the words out (2+ changes inside the held run) are
  no held picture; a shot whose words name an action the source has no footage of carries `// no-footage: <the action>, searched: <the
  wordings searched>` (3+ wordings; without `searched:` the comment doesn't count).
- Unnamed shapes are followed by place (matched to the nearest box of the frame before, never by order).

Proof that it holds: on a long film's first gate run, 423 flags were 26% real faults, each allow costing proof work; with the by-design
cases moved into the checks the same probe gives 132 flags, 81% real, and keeps 95% of the real ones. A change to a check is proven the
same way before it lands: on a probe whose flags are labelled by what their owners did (a fix = real, an allow with a design reason = by
design), precision and recall must not drop.

**Allows.** `videos/<video>/gate_allow.json` is a list of `{"check", "key", "reason"}` (plus `"frames": [a, b]` to hold an allow inside a
range, and `"measured"` where named); the key matches when it is inside the flag's key or its text; an entry without a reason fails. An allow
is written only with proof from the frames or the audio, never from reasoning ("a false positive"). **An allow key names the thing, never a
time or a frame:** a picture's file stem, a cue's note, a line's words (an allow keyed on a time dies at the next re-timing and comes back
as a flag to prove again; the SOUND keys carry the cue's note for this). A SOUND_NOTHING_SHOWN allow needs `"measured"`: the second the
change shows, read off frames, within -0.1/+0.25 s of the cue (an allow written from the code's intent, "the probe doesn't report custom
pieces", doesn't match). Never allowable: MARK_SOUND_OFF, CHECK_CRASHED, the sound half's A11 hard accent, A12 tired opening and LOCK.

**Signed-off stretches.** A stretch the creator passed as it is goes into video.toml as `[[gate.signed]]` with `frames = "0-3345"`,
`files = [the code it is drawn from]`, `sha = gate.files_sha(files)` and `note` = the creator's verdict; while its code is the code they
passed, its flags are listed apart and don't block; a change to any of its files brings them back (`STALE SIGN-OFF` in the report).

**The analysis cache** (`pipeline/gate/analysis_cache.json`): the per-play reads (B1 holds, B2 flashes and fades: minutes each on a long
film) and the still pass's source motion are kept under the clip file's size and time and the play's source seconds (a re-cut clip has a
new key; a check's code change bumps `CHECK_VER`); the still pass keeps its pictures per frame (a reprobe moves or drops them), so only
frames without a picture are drawn. A warm gate reads every play from the cache in about a minute.

**A crash is never a dead run.** In the probe, a piece that throws is caught by `gate.tsx`'s boundary and every hold of the page is
released when the frame is measured (React re-renders a frame after a throw, and an orphaned delayRender would let Remotion's timeout kill
the whole probe). Proof: `src/gatecrash_test_index.ts` throws on frames 10-14 of a 30-frame composition; `gate_probe.mjs` must finish and
log 5 refusals (`bash with_remotion_lock.sh "gate crash test" env QA_ENTRY=src/gatecrash_test_index.ts QA_COMP=GateCrash QA_GL=swangle
QA_PUBLIC=<an empty dir> node gate_probe.mjs <out_dir> 0.25 0-29 1`, from `tools/motion`): re-run it after any change to `gate.tsx`. In
the checks, each B-check runs inside a catch: a crash is a CHECK_CRASHED flag (`tests/test_gate_crash.py`); the scoped gate's steps do the
same. `qa_fades` doesn't judge a play of under 6 frames.

## 7. The incremental, shift-aware probe

A full probe of a long video (about 190,000 frames) takes 1.5-2 hours, and most rounds change a few shots or move the timing.
`tools/pipeline/reprobe.py`, run by `pipe.py gate` by itself:

1. **After every probe a snapshot** (`pipeline/gate/probe_state.json`): every shot's place, its **shape** (what it builds: each element's
   component and props with every number written as `#`, and its length in frames; from `audit.tsx`) and its **numbers**; every code file's
   hash; every top-level declaration's hash and the names it uses (imports followed to the declaration).
2. **The plan** (`PIPE tools/pipeline/reprobe.py <video> plan` prints it, nothing run): the old and new shot lists aligned by shape, in order
   (difflib); a matched shot whose numbers agree within 0.002 (a timing shift's float noise) draws the same picture, so its old lines are
   reused, moved by its own shift. A shot is probed when it is new, its shape or numbers changed (the seam of a timing change, a changed
   shot), or it names a component reached by a changed declaration: changed declarations and every declaration that names one, all the way
   up (a JSON file is one declaration; a whole module named through `import * as M` counts whole). Reach is by declaration, never by file:
   a data file the timing module imports would otherwise reach every shot. `gate.tsx` or the composition root changing, or a plan over 60%
   of the film, means a full probe.
3. **Sentinels**: every 12th frame of the film is probed too and compared with the reused lines; a reused shot whose sentinel differs (what
   the plan can't see: an absolute-time effect, a picture file changed under the same name) is probed whole in a second pass.
4. **The splice**: reused lines (moved) + new lines -> `probe.jsonl`; the still pass's pictures move with their frames, the probed ones go;
   `pipeline/gate/reprobe_plan.json`, `reprobe_report.json` and the gate report say how much was probed and reused.

`PIPE tools/pipeline/reprobe.py <video> verify --ranges a-b,c-d` probes those frames fresh into `pipeline/gate/verify/` and compares them
line by line with `probe.jsonl`: the proof that the spliced probe equals a full one. Proven so: the gate's own checks on a spliced probe and
on a full probe of the same window gave the same flags and the same clip plays, with every frame within 1 px and 0.03 opacity, at about a
seventh of a full probe's time for a typical round of edits. `--full` forces a full probe; `--reprobe a-b,c-d` probes given ranges by hand;
`review_reels.py` and `render --changed` use the same plan.

## 8. The review reels

`PIPE tools/pipeline/review_reels.py <video> --version N --since-version M` (or `--since-rev <git rev>`: the code at a revision, its `src/`
checked out under `tools/motion/out/rev_<sha>/`; or `--ranges a-b,...`: a patch list, a gate round's fixed ranges): the shots that changed
between two renders' code (each render's `parts_v<N>/state.json`, the same plan as the gate, matched by shape alone: a shot whose only change
is its length, the voice moved, is no new picture to look at), plus the shots a changed component reaches when it reaches 5 or fewer; a
component changed under more shots is shown by one example and listed. Each stretch is cut from the render's own parts at exact frames and
the current mix at the same film seconds (a raw H.264 stream and exact PCM per stretch, joined and muxed once: no drift), checked for sync at
the last stretch (picture offset 0, sound lag under a frame). Reels of at most `--max-min 8` minutes (`reel_1`, `reel_2` ...) at 720p, a
phone copy under 30 MB, and the list of film times with the words said there, in `MEDIA/videos/<video>/review/v<N>_reels/`. Options:
`--mix`, `--pad 0.4`, `--out`.

## 9. The scoped gate: the gate's checks inside every loop

**The gate confirms, it never discovers.** Checks that run only at the end, on the whole film, leave builders and fixers blind to them,
and every round's fixes become new, unchecked pictures the next run flags (check, many flags, fixes, check, many flags again). So every
builder and fixer runs `PIPE tools/pipeline/pipe.py <video> gate --scope a-b,c-d [--out <report>]` on their own shots until it is clean,
then hands back; the full `gate` before the render only confirms, and a flag it finds is a miss of the loop, written down as such. The
ranges are frames, as the gate report gives them ("frame 51234") or as the audit's `shots_<comp>.json` gives seconds (x 60).

1. **The shots**: the audit of the code as it is now; each range widened to the whole shots it touches (a shot is checked whole: its cut,
   its last 0.25 s).
2. **The probe**: those shots plus 60 frames each side, with their pictures (for B1 STILL), one Remotion job under heavy.py's ticket (it
   waits, never kills another job). Still holding the ticket it reads the last full probe (`pipeline/gate/probe.jsonl`): the film's state
   is that probe with the probed frames replaced, in memory only.
3. **The checks**: all of B0-B23 with the qa_* modules the gate calls. The per-frame and per-shot checks run on the probed frames, the
   per-play ones on the plays touching the scope (the full gate's analysis cache is read, never written), TWICE on the scope's plays against
   every play of the film, ART_CLOSE on the 20 s round the scope, CARD_CLOSE and B23 on the whole film's code.
4. **The scope's flags**: a flag whose frames meet a range; a pair flag (TWICE, CARD_CLOSE, ART_CLOSE) when one of its shots is in a range;
   CARD_REASON and LIT_UNSAID placed on their shot by the code and the words; a by-file flag (CUTOUT, SUBJECT_MISSING) at its file's first
   showing in the probed frames. The allows and the creator's sign-offs apply as in the full gate. The film's totals (CARD_TIME,
   DEVICE_SPREAD) are listed apart when the scope adds to them, never blocking; ART_SHARE needs the whole film and is left to the full gate.
5. **The report**: `pipeline/gate_scope.md` (or `--out`; each run's own copy and `flags.json` in `pipeline/gate/scope/<tag>/`, so fixers
   running side by side keep theirs); the flags printed; exit 1 while a flag is left, 0 when clean.

It never stamps `passed.txt` and never writes the full gate's files (`probe.jsonl`, `stamp.txt`, `probe_state.json`, `still/`, `gate.md`,
`flags.json`, `analysis_cache.json`, `shots_<comp>.json`); it runs no sound half and no coherency read. Outside the probed frames the film is
the last full probe: another fixer's changes there are not seen, and a timing change since it is said in the report. Proven against a full
gate run on the same unchanged shots: the same flags, identical in check, key, frames and words, in one to two minutes against a full run's
quarter of an hour; a clean scope exits 0; the full gate's files byte-identical after it. The probe costs about 20 ms a frame plus 12-20 s
to bundle, the checks seconds (about three times as long beside a render). `tests/test_gate_precision.py` holds the ranges' widening and
TWICE's pair rule.

## 10. The render: parts, retries, settings

- **Parts.** One lean bundle for the whole render (`tools/motion/lean_bundle.mjs`: its public dir a junction to the lean dir, so no part
  bundles again or copies the public dir; `QA_COPY=1` bundles per part; `QA_ENTRY=<entry>` renders a film registered on its own root from
  the code the gate passed) and one browser (`render_parts.mjs`). The frame count is the composition's own (the `COMP` line; a different
  video.toml or beats count is a NOTE). Parts of `[render] part_frames` (3000, about 50 s; `--chunks N` instead); each part renders to
  `<part>.part.mkv` and is renamed only when whole, so a file at `part_NNN.mkv` is always whole (Remotion can't resume a half-rendered file).
- **What is kept.** A part whose file holds every frame with the same edges and settings is kept; a part the last run finished but never
  recorded (it stopped mid-batch: a crash, a kill) is kept when its file holds every frame and was written after that run's manifest, by the
  same code, settings, length and plan (a re-run never deletes finished parts).
- **Failures.** A part that fails renders again alone at concurrency 4, then 2, while the rest go on at the video's; a part failing every
  way stops the line. "No frame found at position N for source X" re-encodes X (the original source in the message, never Remotion's temp
  copy: a keyframe every second, no B-frames, x264 slow CRF 12, the same frame count, or it isn't used; the original kept in
  `render/reencoded/`, listed in `pipeline/render_reencoded.json`) and the part tries again. A kit3 refusal stops the line with its reason.
  A part with no output for 5 minutes is killed (the whole process tree: a hang has no error and no driver reset, and a background job
  reports only when it ends) and counts as a failure, retried as above.
- **The GPU guard.** After every run, any NVIDIA driver reset (nvlddmkm in the system log) since the render began stops the line: the GPU is
  not tried again (`[render] gl = "swangle"` in every video.toml and the default). Windows only, skipped on macOS.
- **Settings** (`[render]` overrides each): x264 `veryfast` CRF 14, JPEG frames at quality 92, parallel encoding forced (`parallel:
  "force"`: Remotion 4.0.532 encodes while rendering only when free memory minus 1 GB per megapixel stays over 2 GB, 5.7 GB free at 1440p;
  4.0.534 removed that check), a 120-s frame timeout. Veryfast at CRF 14 matched slow at CRF 16 in SSIM against a lossless reference, about
  1.2x faster; its parts are bigger and are re-encoded by the finish anyway. Concurrency: `[render] concurrency` or `--concurrency` (default
  3). **The computer's own best is measured, never guessed:** `PIPE tools/pipeline/render_bench.py <video> [--frames a-b] [--variants
  a,b,...]` renders the same frames (600 from the film's middle by default) with each variant through the line's renderer under one ticket
  and compares each with a PNG-frame lossless reference by SSIM and PSNR, so a faster setting is adopted only at the same quality
  (`<out>/bench.md`). More concurrency is not always faster: past the CPU's cores it slows. Re-run it on a new computer and after a Remotion
  upgrade.
- **Files.** `parts_v<N>/parts.json` (every part: frames, seconds, concurrency, settings), `parts_v<N>/state.json` (what the render is made
  of: `--changed` and the review reels compare against it), `pipeline/render_v<N>.status.json` (parts done, fps, ETA), the parts joined by
  stream copy into `render/v<N>_picture.mkv` (frame count checked), `render/v<N>_picture.done.json` the done marker.
- **The render scan** runs on every full render (`tools/pipeline/qa_render_scan.py`, against the gate's probe): BLACK_DIP 1-6 frames much
  darker than both sides that come back; FLASH_FRAME 1-8 frames of one picture with a jump in and a jump out that neither the design nor the
  source explains; FROZEN a clip the probe says plays while its part of the rendered frame stands still; FRAMES a part with the wrong frame
  count. Some faults exist only in the real picture (a delayRender black frame, a render-time freeze). Report and strips in
  `pipeline/render_scan_v<N>/`; a flag stops the line before anything goes to the creator (the picture stays; the fix goes in as a patch).
  `--no-scan` or `[render] scan = false` skips it. Its frame measures are read back while the parts are unchanged.
- **Remotion stays pinned** (`tools/motion/package.json`: 4.0.532). An upgrade changes pixels (4.0.540 moves to Chrome 158, with Skia
  Graphite off on Windows), so it is an A/B of its own (render_bench.py and the gate on a known stretch), never a side change.

## 11. What the research said (sources)

| Finding | Source | What the line does |
|---|---|---|
| Remotion 4.0.532 encodes while rendering only when free memory minus 1 GB per megapixel stays over 2 GB; 4.0.534 removed the check ("20-35% longer" sequential) | github.com/remotion-dev/remotion `packages/renderer/src/prestitcher-memory-usage.ts` (v4.0.532), PR #11971 | `parallel: "force"` in render_parts.mjs |
| concurrency can speed up or slow down; benchmark it; the default is half the threads, max 8 | remotion.dev/docs/performance, /docs/cli/benchmark | render_bench.py on the video's own frames |
| `--x264-preset` (default medium); at constant quality a slower preset only saves bitrate; CRF 17-18 is visually lossless | remotion.dev/docs/cli/render; trac.ffmpeg.org/wiki/Encode/H.264 (2025-06-22, via the Wayback Machine) | veryfast at CRF 14 (SSIM equal to slow at 16) |
| PNG frames are slower than JPEG; `--jpeg-quality` default 80 | remotion.dev/docs/render-media | JPEG at 92 |
| `--hardware-acceleration`: NVENC on Windows from 4.0.236, not with CRF, not for `h264-mkv` | remotion.dev/docs/hardware-acceleration; renderer `get-codec-name.ts` | not used: the encode isn't the bottleneck |
| shared-memory capture (4.0.534+) doesn't run on Windows | remotion.dev/docs/shared-memory-capture | not used |
| "No frame found at position": the OffthreadVideo cache failed to serve the frame; most likely too little cache memory; long decodes from sparse keyframes under CPU load; a retry often succeeds | remotion.dev/docs/troubleshooting/no-frame-found-at-position; issues #7153, #8732 | re-encode the named clip (a keyframe every second, no B-frames), retry the part, then lower concurrency |
| no documented resume of a half-rendered output, no general frame retry; `--frames` ranges | remotion.dev/docs/render-media; /docs/cli/render | small parts, each whole or not at all |
| a render can hang after a Chrome crash during parallel encoding (no error, no frames); fixed in 4.0.541/4.0.543 | issue #12840, PRs #12841, #12896, #13188 | the stall watchdog (5 min, kill, retry the part) |
| delayRender: default 30 s, per-call timeout and `retries` (4.0.140); React can discard a render after delayRender (fixed for Remotion's own components in 4.0.535) | remotion.dev/docs/delay-render, /docs/timeout; PR #12103 | B3 BLANK catches a race's lost frames in the probe; the render scan in the render |
| ffmpeg `blackdetect` (d 2 s, pic_th 0.98, pix_th 0.10), `blackframe`, `freezedetect` (-60 dB, 2 s), `scdet` (8-14), `signalstats` YDIF | ffmpeg.org/ffmpeg-filters.html | the render scan measures its own (single black frames and 1-8 frame strays are under those filters' minimum durations) |
| the SSIM and PSNR filters need equal size, pixel format and frame count | ffmpeg.org/ffmpeg-filters.html | render_bench.py |
| WCAG 2.3.1 / ITU-R BT.1702-3: no more than 3 flashes in any second over 25% of the screen | w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html (2025-09-17); ITU-R BT.1702-3 (11/2023) | not a check yet (the faults found are single stray frames, not strobes); kept for strobe edits |
| dHash/pHash for near-duplicate frames | github.com/JohannesBuchner/imagehash; hackerfactor.com (2013-01-21) | not used for reuse (qa_reused's own frame matching measures it); dhash finds artwork in B22 |
| test impact analysis: select checks from what a diff touched, keep the map current | martinfowler.com/articles/rise-test-impact-analysis.html (2017-08-22) | reprobe.py's plan, by declaration |
| content-addressed action cache; track every input or get false hits | bazel.build/remote/caching | the analysis cache's keys (the file's size and time, the args, the check's version) |
| a build is correct when every reused value equals recomputing it; minimal when only changed inputs rerun | Mokhov, Mitchell, Peyton Jones, *Build Systems a la Carte*, JFP 2020 | the reprobe proof's test (incremental = full, every frame of the window) |

## 12. Around the line

- **Chapters are computed** (`PIPE tools/pipeline/chapters.py <video> [--write]`): `videos/<video>/chapters.json` lists the titles and the
  beat each opens on (`[{"title": "..."}, {"title": "...", "beat": "S04"}, ...]`; the first is 0:00 and needs no beat). Each chapter's time is
  its beat's first word minus 0.5 s, floored to the second, on the film's own timing (with the bites laid in). `pipe.py finish` writes them
  between `<!-- chapters -->` and `<!-- /chapters -->` in `post.md` and refuses what YouTube refuses (under 3 chapters, the first not at
  0:00, one under 10 s, out of order), so the pack follows every timing change; never re-read by hand.
- The `.srt` and the chapters are written before the 4K encode: a stale `[srt]` path fails in seconds, not after the encode.
- The hook `tools/hooks/no_edit_running_script.py` refuses an edit to a shell script while bash runs it (bash reads a script as it goes,
  so an edit breaks the running chain).
- `tools/hooks/sitecustomize.py` in both venvs prints an unwritable character as `?` instead of crashing the tool
  (`tools/hooks/install_sitecustomize.py` after a venv rebuild).
- A render's re-run keeps its finished parts (section 10, "What is kept").
