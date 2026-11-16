# The workflow of a long video

*Part of `STANDARD.md`. The craft files say HOW (`standard/LONG_FORM.md` the picture, `standard/KIT3.md` the pieces,
`standard/SCRIPTS_AND_PACKAGING.md` the script, `standard/VOICE_LOCK.md` and `standard/SOUND_AND_VOICE.md` the voice, `standard/MUSIC.md`
the music, `standard/PIPELINE.md` the gate and renders); this file says IN WHAT ORDER, WHAT BLOCKS, and the exact commands from a topic
to a finished 60-second prototype, then the full film. PIPE and EDIT are the two Pythons (`python tools/common/paths.py` prints them);
`<video>` is the video's folder name under `videos/`; commands run from the repo root unless they say `cd tools/motion`.*

**Why the order is held by machines.** Measured on real builds: one film took 185 h, and most of the creator's notes on it were in
classes that already had a rule written down; what worked were machines that block (a cap on number cards, a reuse check, a pause pass,
a passed prototype: each took its class to 0). Two full cuts thrown away before a prototype passed cost ~64 h; 13 voice changes after the
voice "passed" cost 11+ h and 7 mixes; 26 fact fixes that landed after the voice cost a 5-h patch round. On another film, 47 of 73
hours went into a 49-minute cut built before the creator saw one finished minute, thrown away whole; every time, the creator's watch
found the faults early, and no gate, coherency read or agent review predicted them. So every stage ends on a stamp a machine checks,
and the expensive steps refuse to run before what shapes them is settled.

## 1. The stages, and what blocks

`PIPE tools/workflow/stages.py <video> status | stamp <stage> --note "<proof>" | require <stage>` (stamps in `videos/<video>/stages.json`;
the script stages are hashed on `script.md`: an edit makes them stale and the stages after them refuse).

| Stage | Done when (the stamp) | Needs |
|---|---|---|
| idea | the creator's pick, quoted in the note; the "already on YouTube?" check done; `UPDATE.md`'s quiet check run | |
| research | the research pack with depth marks, "Not researched yet" and `CRITIC.md` (`research_pack.py` passes) | idea |
| script | final: the lint clean, the blind gate run, the coherency read of the script | research |
| facts | every claim checked against its source, on this script's hash | script |
| coldread | a first-time listener's pass, on this hash | script |
| bites | the bites table's TEASE / PARAPHRASE lines are in the script (a clip never repeats our words) | script |
| names | every name in `tools/sound/names.json`, every respelled one measured | script |
| prototype | the first 60 s at the finished look, the creator's pass quoted in the note (`skip` when `creator/choices.toml` says `prototype_first = false`) | script |
| voice | locked: `voice_lock.json` and `voice_lock.py <video> verify` passes | facts, coldread, bites, names |
| picture | every section at the prototype's level (with no prototype: the opening's), the full gate passed on its code stamp | |
| render | the full render (`pipe.py render`) | prototype, voice, picture |
| review | the review copy to the creator, their notes in `REVIEW_vN.md`, every judgement fix a sample or a reel they saw | render |
| final | the 4K and the upload pack (`post.md`) | review |

The voicing tools (`dj tts`, `span_takes`, `autopick`, `voice_full` ...) refuse (exit 5) until script, facts, coldread, bites and names
are stamped on the current script; `pipe.py render` refuses without the prototype, voice and picture stamps and a passing gate.

## 2. From a topic to the finished 60-second prototype

The prototype is the opening (the first ~60 s, to a natural break) built EXACTLY as the finished video will be: final script lines,
the real voice, every picture picked and cut, the graphics, the effects and music, the gate passed, rendered and mixed. Never a rough
cut, never placeholders on screen. It goes to the creator before anything else of the film is built; the full film starts at their
pass, and their notes on it set the video's level.

**When the creator chose the whole video in one go** (`creator/choices.toml`: `prototype_first = false`, asked at setup), nothing
waits for them until the full film. Steps 0-5 run as written. Step 6 voices the whole script at once (section 3's step 2:
`voice_full.py`, then the layout, the chain, the sound gate and the lock over all of it). Steps 7-12 build the opening first, held to
the bar (`standard/BAR_LONG_FORM.md`) exactly as a prototype would be, gate passed; that opening is the level for every section. Then
section 3 goes straight on from its step 3 (no stop, no prototype stamp: `stages.py status` shows it as `skip` and `pipe.py render`
doesn't wait for it), and Steps 13-14 run once, on the full film: its watchable copy is the creator's first watch, and their notes on
it are the review (the `review` stage).

**Keep the clock** in `videos/<video>/BUILD.md` (the write-ahead log): a table of stages with start and end times (the PC's clock,
taken by `date` in the same command that writes the time), the jobs running and where their output lands, the storyboard, what is built,
then a timed log of every step and snag. A compaction or a new chat loses nothing, and the next video's clock comes down where the snags
were.

**Six principles that make it fast** (a measured prototype went from finished research to the creator's copy in under 2 h against
~9 h 20 min for one built without them):
1. **One mind holds the whole context and does every judgement itself.** The chat reads the research, the rules and the casebook,
   writes the script and builds the picture. Agents get only exact, self-contained jobs (the three script checks, N coherency readers,
   page captures, downloads, cutting given spans, code from an exact shot list); no brief is written for judgement work, since a brief
   loses half of what its writer knew.
2. **Everything that can run at once runs at once.** The three script checks are three agents in ONE message; the voice is made while
   the picture is coded; captures and downloads run while code is written; heavy jobs queue through `tools/pipeline/heavy.py` so they
   start the second the slot frees.
3. **Measure, never eyeball.** Every box, outline, word time and span comes from the pixels or the voice's word times, computed by a
   tool: "the perfect amount of zoom, exactly centred, exactly on the outline, starting and ending on the perfect spots" is arithmetic on
   measured numbers, done in seconds.
4. **Check before the render, on the code.** The static audit and the gate's probe read the shots from the code (no render); the
   casebook is read against the storyboard shot by shot. A fault costs a one-line edit, not a second version and the creator's watch.
5. **The factory line.** While the PC's render slot is busy, the next stage's work is built (the next section's options, storyboard
   and code).
6. **The write-ahead log** above.

### Step 0. The video's folders
- `videos/<video>/` from `videos/_template/`: `script.md` (dj's script format), `video.toml` (from `tools/pipeline/video.example.toml`:
  the composition id, its source folder, the public dir, the audit's plays, the sound settings), `BUILD.md`, `score/cues.py` (the cue
  sheet, later).
- The media side `MEDIA/videos/<video>/` and the public dir's folder `PUBLIC/<video>/` (`clips/`, `img/`, `pages/`, `art/`, `dl/`).
- `PIPE tools/workflow/stages.py <video> status`.

### Step 1. Idea
The creator's pick (their intuition picks; no idea research they didn't ask for). Before any work, **the "already on YouTube?" check**:
a logged-in YouTube search for the topic; if bigger channels already have it, the video needs the untold part (or it's another idea).
Then `stages.py <video> stamp idea --note "<the creator's words>"`.

### Step 2. Research
Current to the day of the build; receipts from the primary source; footage and pages found as research goes
(`standard/research/FOOTAGE_SOURCING.md`); facts into `kb/` first. The pack: items with depth marks (`[depth: deep | medium |
shallow]`), a "Not researched yet" list of at least 5 items, `CRITIC.md` (a fresh agent's critical read against the subject itself:
"what would someone who lived through this say we missed?"), `OPINIONS.md` (3-6 suggested interview questions). Research is never called
complete. `PIPE tools/script/research_pack.py <research folder> [--write]` must pass; then `stages.py <video> stamp research --note "..."`.

### Step 3. Script
`standard/SCRIPTS_AND_PACKAGING.md`, with a picture in mind for every line.
1. One writer (the chat) drafts the whole script from the research, in dj's format (`## Beats`, `# ===== SECTION =====`, `[S01] VOICE:`,
   `[S05h] HOLD: 2.3` for a real person's bite).
2. **Three checks at once**, three fresh agents launched in ONE message: the spoken edit (the same facts, said like a person), the cold
   read (a first-time listener from the niche, the casebook's script cases as its list: a hedge kept from the research, a definition
   wedged inside a clause), the fact check (every claim against its source; of every "new", "now", "for the first time" claim: did the
   previous version already have it? only the new part stays).
3. ONE merge by the writer; only misreads that really happened are respelled for the voice.
4. `PIPE tools/pipeline/pipe.py <video> script` (= `tools/script/script_lint.py --strict`), `PIPE tools/script/tell_lint.py
   videos/<video>/script.md --style`; the length measured (a full long video ~8 minutes or more on the script, no ceiling).
5. Every new proper noun into `tools/sound/names.json`; `EDIT tools/voice/voice_ready.py <video> names --measure --stamp`.

### Step 4. The blind gate
Before the voice, the script is read blind (`standard/SCRIPTS_AND_PACKAGING.md`): the measure is `PIPE tools/script/pair_test.py
make|brief|score` (the same content by a real creator and by us; a clean judge agent picks the human; 0.50 = can't tell);
`PIPE tools/script/judge_panel.py gate <set> --ours <sections.txt>` as a secondary number (each section alone among calibrated human
passages, a clean judge with no project context). It is run once as a number: it never blocks or loops (rewording moves the same passage
~0.1 between packets). The lever it measures is the creator's own view in a section, which comes next. Then the coherency read of the
script, and the stamps: `stages.py <video> stamp script|facts|coldread|bites --note "<the proof>"`.

### Step 5. The creator's view
The interview: 3-6 open questions from `OPINIONS.md`, trimmed to the spots where the video takes a view and the fact-heavy spots;
their answers blended into the script in the chat's words (never verbatim, never made up), each section carrying it. The questions can
go out while Step 7's picture work starts; a script change after the answers re-runs Step 3's lint and re-stamps (the stamps are
hashed).

### Step 6. The voice of the prototype, locked
`standard/VOICE_LOCK.md`, made beside the picture (Steps 7-10 run while the takes generate):
1. Takes and the machine's pick: `EDIT tools/voice/autopick.py <video> <first beat> <last beat> [--k 3]` (the lines-before way, the
   first section after the house warm-up; judged by accent, names, both recognisers and the opening; a section with no clean take exits
   2: reword and voice again, never keep). Takes already on disk: `--score <stem> <k...> --first <B> --last <B>`.
2. The layout: `PIPE tools/voice/proto_narration.py <video> <first beat> <last beat>`.
3. The chain and the sound gate: `bash tools/sound/voice_chain.sh <video>` (it ends on `EDIT tools/sound/gate_sound.py <video>`,
   A1-A13; exit 3 while anything is flagged; fixes are the tools it names, never a hand cut).
4. The voice's own `words.json` and `beats.json` replace the placeholders in `tools/motion/src/<video>/`, and every shot re-times itself.
5. The lock: `EDIT tools/voice/voice_lock.py <video> lock --note "prototype"`. The words are frozen before the gate scans; a later fix is
   a lay-in (`voice_layin.py`). When the full film is voiced, `unlock --why "the full film's sections"`, the stages, and a new lock.

### Step 7. The storyboard
`videos/<video>/STORYBOARD.md` (`standard/LONG_FORM.md`, method step 6): one row per shot (words, picture and why, subject box,
move, marks, sound), the Findings on top. Until the voice lands, shots are timed on placeholder words (`PIPE
tools/motion/placeholder_words.py`, 3.24 words a second). Read every row against `cases/PICTURE.md` and `cases/COHERENCE.md` before any
code. Every claim line names the moment that proves it.

### Step 8. The options boards
`standard/LONG_FORM.md`, method step 7: per line a few easy candidates from different sources (`EDIT tools/footage/pick_boards.py boards
videos/<video>/script.md <out> --beats S01-S09` for the whole prototype in one run, or `EDIT tools/footage/find_shot.py "<line>" --n 12
--sheet <png>` per line; a candidate source scanned whole with `PIPE tools/motion/source_sheet.py`), written into
`videos/<video>/options/OPTIONS_<section>.json`, drawn with `PIPE tools/motion/options_board.py <spec.json>` and `--md`, the pick and why in
each slot. Pages are captured now (`node tools/footage/capture_page.mjs <url> <out.png> <selector> --mark "<phrase>"`, at phone width).
Downloads run now (yt-dlp, the native format ladder, modest, stopping at any sign-in or bot prompt).

### Step 9. The clips, cut with the prep script
Copy `tools/motion/prep_template.py` to `tools/motion/prep<id>.py` and fill its tables: `CLIPS` (name: source, in, out, a filter
before the scale or ""; each with a comment of what the span shows and where its source's own shot starts and ends, measured on frames),
`BOXES` (every measured box a shot lights, in each file's own pixels). Then:
- `PIPE tools/motion/prep<id>.py --check`: cut at the source's own frame rate, `-bf 0`, `-map 0:v:0 -dn`,
  `setpts=PTS-STARTPTS`, whole with a letterbox's bars kept, into `PUBLIC/v<id>/clips/`; each clip's last frame into
  `src/clipdurs.json` (under its lock) and the gate's manifest `prep<id>_clips.json`; `--check` scans each cut for a camera cut inside.
- `EDIT tools/motion/prep<id>.py --proof [<dir>]`: every box drawn on a crop of its file, looked at (a box is reused only after that).
- The marks' boxes from the pixels: `EDIT tools/motion/automark.py <image> "<what>" --proof <out.jpg>`; outlines for the spot look:
  `EDIT tools/motion/spotmask.py <image> x,y,w,h --what <thing> --count N`; a zoomed clip from the 4K master.
- Board picks to an agent as exact span lists when there are many: `EDIT tools/footage/pick_boards.py cut <out>/PICKS.json --prefix
  <video> --manifest prep<id>_clips.json [--run <clips dir>]`.
- `PIPE tools/pipeline/pipe.py <video> link` (the lean public dir of hard links gets every new file).

### Step 10. The composition, from the template
Copy `tools/motion/src/_template/` to `tools/motion/src/<video>/` (`standard/LONG_FORM.md`, method step 10): the timing file (`w`, `we`,
`b0`, `bEnd`, `bStart`, `bStop`, `MISSES`), the composition registered as `gated(<Comp>)` on its own root and entry
`src/<video>_index.ts`. Each shot one line on its words, every `at` a phrase, nothing in seconds; kit3 for every standard piece
(`standard/KIT3.md`), the video's own graphics file only for its own ideas; the comments the checks read above every shot (`// subject:`,
`// art:`, `// card:`, `// zoom:`, `// device:`, `// stamp:`, `// no-footage:`, `// named-moment:`, `// repeat:`). Then:
- `cd tools/motion && npx tsc --noEmit -p .`
- `PIPE tools/pipeline/pipe.py <video> audit` (0 overruns, every play against its file, every shot under 0.5 s, both edges against
  the source's cuts) and `pipe.py <video> plays` (every play's first, middle and last frame on sheets, read).
- The code checks of `standard/LONG_FORM.md` "Before it goes to the creator" (`qa_options.py`, `qa_continued.py`, `qa_cards.py`,
  `qa_still_words.py`, `qa_shots.py`, `qa_devices.py`, `qa_repeat_pics.py`, `qa_kept_area.py`, `qa_upscaled.py`, `qa_fades.py`).
- `node tools/motion/qa_camera.mjs src/<video>/<Comp>.tsx`: 0 TWO MOVES.
- Proof stills of every graphic, quote, cut-out and mark (first frame and end state): `cd tools/motion && bash with_remotion_lock.sh
  "<what>" env QA_ENTRY=src/<video>_index.ts QA_COMP=<Comp> QA_PUBLIC=<lean public dir> node stills.mjs <out dir> 1 <frame> ...` (frames
  at 60 fps), looked at. Stills catch what no gate does: frame numbers taken at 30 fps on a 60-fps composition, a dark cut-out vanishing
  over a dark ground, lettering on a blurred ground that contradicts the label above it.
- The scoped gate on the shots just built: `PIPE tools/pipeline/pipe.py <video> gate --scope <f0-f1>` (with `QA_ENTRY=src/<video>_index.ts`
  set), until it is clean or every flag left is disproved on its frame. A flag is fixed at its source; an allow goes into
  `videos/<video>/gate_allow.json` only with the proof (the check, a key that names the thing, never a frame number, which goes stale on
  a cut; the reason with the crop that proves it).

### Step 11. The music and the cue sheet
`standard/MUSIC.md` and `standard/SOUND_AND_VOICE.md`: the bed for the opening chosen and placed on its downbeats (the creator's own
tracks in MUSIC, or music made in code with `tools/music/`), one sound world, ~22 dB under the voice, the next bed on a downbeat where
the story turns. The cue sheet `videos/<video>/score/cues.py`: `EDIT tools/sound/autocues.py <video> --out <snippet.py>` writes every
marker, stamp, count-up and landing from the gate's probe; the chat adds the drop, the whooshes on real flights, pops and impacts by hand;
only rated house sounds (`pal(name)`); at most ~3 marks in any 5 s; no whoosh on a glide inside one picture; no effect over -7 LU against
the voice. The cue sheet's END and `video.toml`'s `frames` match the composition's length.

### Step 12. The gate
`QA_ENTRY=src/<video>_index.ts PIPE tools/pipeline/pipe.py <video> gate`: the sound half (A1-A13 + the lock) and the picture half
(B0-B26 on every frame of the code, no render), plus the coherency read: `EDIT tools/pipeline/coherency.py packet <video>`, then
`EDIT tools/pipeline/coherency_shards.py split <video> --n 3` (one brief per reader: N fresh reader agents in ONE message, each writes
its shard's flags), `coherency_shards.py merge <video>`, `coherency.py check <video>`. **One full gate round:** the real faults fixed and
checked by `gate --scope` on their own shots, the rest allowed with proof, the full gate run again only with `--reuse` (only the changed
frames re-probed). It confirms; a flag it finds is a miss of Step 10's loop, written down in BUILD.md.

### Step 13. Render, scan, mix, export
- `PIPE tools/pipeline/pipe.py <video> render` (1440p parts through `render_parts.mjs`, under the Remotion ticket; one Remotion job on the
  PC; the render scan `qa_render_scan.py` runs on it by itself: black dips, stray frames, render-time freezes). A scan flag is fixed in
  the code or the kit and the stretch re-rendered.
- The mix: `PIPE tools/pipeline/pipe.py <video> score --picture <render>`; its report read (voice over music ~22 dB, no silences outside
  the designed ones, no effect over -7 LU, -14 LUFS, true peak at most -1 dBTP).
- The export for the creator: the render's video stream copied + the mix as AAC 320k (no re-encode).

### Step 14. Delivery
The watchable copy goes to the creator the minute it exists (`SendUserFile`; a file over 30 MB shows only in the desktop app: say so),
with nothing of the chat's between the render and them: no review pass of the chat's or an agent's on it. Before sending, the verdict
the chat expects goes into `cases/PREDICTIONS.md`. The creator's interview questions go with it if Step 5 hasn't run yet. Their watch is
the fix list: each fix of their judgement goes back as a sample of just that moment, one at a time; a clear fix is fixed and patched
without a sample. Every verdict, passed or flagged, goes into its casebook the same turn, and every note is checked across the whole
prototype (a note is a sample of a class). The prototype stage ends at their pass: `stages.py <video> stamp prototype --note "<their
words>"`. A passed stretch is signed in `video.toml` (`[[gate.signed]]`), so the gate never re-litigates it.

## 3. The full build

Starts at the creator's pass (with no prototype: as soon as the opening is built and gated). The prototype (or that opening) is the
bar for every section, shot by shot: a level, never devices to copy (each section
finds its own best pictures).
1. **The script final** for the whole film (Step 3's checks on the new sections, the interview answers in, the stamps on the final
   hash). Never a word changed by a builder: a script problem goes to the main chat.
2. **The voice for the rest:** `EDIT tools/voice/voice_full.py <video> --no-layout` (sections of ~150 words on beat boundaries, one take
   each, a new take only where one fails, up to 3 jobs at once; the prototype's words stay as they are; a section failing twice is split),
   then the layout over the whole script, `voice_lock.py <video> unlock --why "..."`, `voice_chain.sh <video>`, the sound gate, `lock`.
   The section builders write against the script's exact words meanwhile; anchors on lines not voiced yet sit in `MISSES` and the
   composition refuses to render, which is right.
3. **The sections, in parallel when the film is long:** one builder per section (a chat agent), each with its OWN files only:
   `src/<video>/body_<x>.tsx` exporting `shots<X>(): Shot[]`, `src/<video>/graphics_<x>.tsx`, `prep<id>_<x>.py` (+ its clips
   manifest), `videos/<video>/score/cues_<x>.py` (`def sfx(F)` returning the section's `Sfx` list). The main chat's composition puts the
   prototype's shots and every section's list on one timeline sorted by time: a shot runs until the next, so a section's first shot
   starts on its first beat's first word. Shared files (the timing file, kit3, `lib.tsx`, `Root.tsx`, `names.json`, the main cue sheet,
   the shared tools) change only through the main chat; a fix to a shared piece goes there. The builder's brief carries: the bar (the
   passed prototype: its export, code and BUILD.md), the script and the storyboard's Findings, the casebooks, `standard/KIT3.md` and
   `standard/LONG_FORM.md`, the devices the film already uses (`qa_devices.py <video> --list`), the PC rules below, and what to report.
4. **Each builder's method:** options (Step 8) -> `STORYBOARD_<x>.md` (Step 7) -> prep (Step 9) -> body and graphics (Step 10, `npx tsc
   --noEmit -p .` clean in its own files) -> **stage 1** (before the voice is final): prep `--check` and the code checks, one at a time,
   reported -> **stage 2** (after "voice final"): `pipe.py <video> link`, the scoped gate on its own frames until clean, proof stills of
   every graphic, quote, cut-out and mark, reported. A builder's report: shots and seconds, its files, each check's result, the named
   moments and repeats with their reasons, anything not found after three different searches (and what was used), any rule it could not
   meet and why; no "done" for anything not proven on a frame. The main chat forwards each note of the creator's as a CLASS, and the
   builder finds every instance in its range.
5. **The music and the sound** for the whole film: one bed world, the beds placed by the main chat; the sections' cues merged.
6. **One full gate round, one coherency read** on the whole film (`--n 8` readers or more for a film of ~1,000 shots), fixes by `--scope`,
   then `stages.py <video> stamp picture --note "..."`.
7. **Render the minute the gate passes** (`pipe.py <video> render`); the mix; the watchable copy to the creator the minute it exists.
   **The 4K starts the same minute** (`pipe.py <video> finish`, `--test 0-10` first on a new chain): if their watch finds a major fault,
   the 4K is cancelled; fixes that come later are spliced in.
8. **The review:** the creator's notes are the whole fix list; the chat's own finds stop once the copy is sent. Each judgement fix a
   sample (one at a time, in film order, unchecked by the chat); many changed shots as one reel per part (`PIPE
   tools/pipeline/review_reels.py <video> --version N --since-version M`, planned from the code diff between the versions, each with its
   film times in the message; reels planned from notes miss shots). Anything for the creator's phone stays under 30 MB (a copy at ~850
   kbps). Fixes after the render are patches (`pipe.py patch --ranges`), shown as one patch reel; the timing never moves after the voice
   lock (a voice fix is a lay-in). Patches are spliced into the delivered 4K (`splice_patch.py`: only the stretch round each patch
   re-encoded, ~1 min) instead of waiting or re-encoding the whole file.
9. **Loudness:** `finish_long.py`'s own check can fail on true peak (-0.82 or -0.94 dBTP): the fix is the audio alone from the mix a few
   tenths of a dB lower, the picture stream-copied (minutes), never a new encode.
10. **The upload pack, built while the 4K encodes** (after the creator calls the video done: `standard/SCRIPTS_AND_PACKAGING.md`): the
    title, the description with chapters (`chapters.json` + post.md's `<!-- chapters -->` markers: `pipe.py finish` writes them from the
    final words), the picture credits (from the shots' sources and the on-screen credits, under YouTube's 5,000 characters), tags, the
    ad-suitability answers, a check that any "nothing new yet" line is still true; all as copy blocks in the final message. When the video
    goes up is the creator's call.

## 4. The defaults that keep a build from looping

- **The creator sees finished minutes before the rest is built.** A rework of a whole film shows them its first finished minutes before
  the rest is redone (a film re-cut whole in 16 h drew ~45 notes in its first ten minutes).
- **One gate round a build.** The full gate runs once, when the voice is locked and the picture is built; real faults are fixed and the
  rest allowed with proof; fixes are checked by `gate --scope` on their own shots (1-2 min), never by another full run (a 49-minute cut
  ran the full gate 6 times, 297 min, and still passed a film the creator called a mess).
- **One coherency read a build,** on the first full build; after the fixes only the changed lines are read (repeated reads converge on
  opinion: 24, 21, 12, 4, 4, 4 flags).
- **Nothing of the chat's stands between the render and the creator.** After their full watch, their notes are the whole fix list.
- **The words are frozen before the gate scans** (the voice lock; a later change is a lay-in), and the pace comes from new pictures,
  never from re-framing the same shots (a pace round that re-framed shots cost ~3 h and was undone).
- **Long jobs survive:** a running script can't be edited (a hook refuses); media prep never re-runs while a gate scan reads the
  pictures; a crashing check is a flag (CHECK_CRASHED), a piece that throws is a refusal flag, and a render re-run keeps its finished
  parts (check what a re-run keeps before running it).
- **Ready before the next video:** while the creator uploads, the time-wasters and mistake classes of this build get their fixes at the
  source (a tool that can't make the mistake, a template that starts right), then the clean-up, then the next video.

## 5. The week and the machine

- Read the usage (`get_usage`) at the start of a video and at each checkpoint. Near the weekly limit, start the long machine jobs (render,
  probe, 4K) before it hits: they run without the chat.
- Agents: memory measured before each launch; several builders' downloads and cuts at once can crash the PC, so heavy jobs take
  `heavy.py` tickets, one Remotion job at a time, and the hook `tools/hooks/commit_guard.py` refuses to start a heavy job at 85% memory
  commit or more. Each builder: one ffmpeg at a time, `-ss` before `-i`, contact sheets of 4K sources with `-skip_frame nokey` at low
  size, no recursive disk scans, downloads modest (a short span with `--download-sections` when a source is long), kill only its own
  PIDs, delete only its own intermediates. `src/clipdurs.json` is shared: preps write it under its lock, nobody commits it.
- A long background job gets a done-marker and a stall watchdog; a chained job (render -> mix -> patches -> 4K) is armed as one waiter, so
  no hour is lost between steps.
- Effort: making a video is xhigh (`CLAUDE.md`, "Working in this app").

## 6. Where each craft's checks live

Voice: `standard/VOICE_LOCK.md`, `standard/SOUND_AND_VOICE.md`. Music: `standard/MUSIC.md`. Picture gate and renders:
`standard/PIPELINE.md`. The picture: `standard/LONG_FORM.md`. Components: `standard/KIT3.md`, `standard/3D.md`,
`standard/GRAPHICS_KIT2.md`. Script: `standard/SCRIPTS_AND_PACKAGING.md`, `standard/SCRIPT_TRAINING.md`. The stages:
`tools/workflow/stages.py`. Every check in one list: `standard/CHECKLIST.md`.
