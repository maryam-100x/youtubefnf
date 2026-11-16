# THE STANDARD

*The level this studio works at, and how to work at it. Any chat in this folder starts here, right after `CLAUDE.md`.*

**How to use this file.** Study it fully before your first piece of work (section 2). Then, before each piece of work, re-read the
standard of that craft (`standard/*.md`) and the newest build of its kind in `videos/`. Every output starts from this studio's own
files, never from general knowledge. When this file and a rule in `rules/` disagree, the rule wins and this file is rewritten to it.

---

## 1. The bar

There are no example videos to copy. The bar is written down, in detail, in two files, and every video reaches it:
- **Long form:** `standard/BAR_LONG_FORM.md`: the qualities every minute has (with their numbers), two worked 60-second openings shot
  by shot, and what makes a finished long video hit.
- **Shorts:** `standard/BAR_SHORTS.md`: the qualities every shot has, and worked example Shorts shot by shot.

**The bar is the quality, never the moves.** A new video reaches this level with its own pictures, effects, sound and music for what
it shows. Copying a worked example's devices (its chart, its count-up, its fonts, its layout) is the template mistake: every video
answers its own words.

**What "done" means:** a video can still have faults; the creator reviews and we adjust. But it never reaches them below this bar, and
their notes on one video are a sample of what to check everywhere.

**Once the creator signs a video off as their new standard**, it becomes the newest bar: write in `standard/BAR_LONG_FORM.md` (or
`BAR_SHORTS.md`) what it does at that level and where its files are, and study it before the next video of its kind.

## 2. The study protocol (a chat new to this folder, before any work)

The study has no time limit and is never skipped.
1. `CLAUDE.md` (loads by itself), then **this file in full**.
2. **Every craft standard of your chat, in full.** The main chat: `standard/LONG_FORM.md`, `BAR_LONG_FORM.md`, `SOUND_AND_VOICE.md`,
   `MUSIC.md`, `SCRIPTS_AND_PACKAGING.md`, `SCRIPT_TRAINING.md`, `VOICE_LOCK.md`, `PIPELINE.md`, `WORKFLOW.md`, `KIT3.md`, `3D.md`,
   `GRAPHICS_KIT2.md`, `REVIEWERS_EYE.md`, `CHECKLIST.md`. The Shorts chat: the list in `SHORTS_CHAT.md`.
3. **The craft research** your standards cite, in `standard/research/` (its README lists each file): read the ones your craft names
   before that craft's first piece of work.
4. **The creator and the rules:** `creator/PROFILE.md`; `rules/SHARED.md` and your own rules file in full; the casebooks in `cases/`
   (the lines the creator's verdicts drew).
5. **The knowledge:** `kb/README.md` (what is known about the niche and where), then what the next video needs.
6. **The live state:** `STATUS.md` (the Shorts chat: `STATUS_SHORTS.md`), the newest entry of the session log, `decisions/LOG.md`.
7. **Ready means every check of the craft can be run, never a feeling.** Before a piece goes to the creator, its craft file's "before
   it goes to the creator" list is run item by item on that piece. Proof stills and word sheets show whether a picture matches its
   words, never whether its subject stays whole and centred while the clip moves: that needs its own check.
8. **Brief the creator in 3 lines** (what you studied, what is live, what is next), then wait for their go unless they already named
   the task. Never claim to be as good as the chat before; if asked, say what you read.

Before each piece of work: re-read its `standard/` file, open the newest build of that kind, then build.

## 3. How we work

**Roles.** The creator and the chat are equals (`CLAUDE.md`). The creator owns their life and their channel, the ideas (their
intuition picks; no idea research they didn't ask for), the opinions in the videos (after each script the chat interviews them, and
never makes one up) and the final verdict on taste: their ears judge audio, their eye judges pictures. The chat owns the making:
script, voice, edit, sound, music, the words of the packaging, and holds the work to the plan. How the work gets done is the chat's to
decide and do, told in a line, never asked. Agents do grunt work and wide reading; the craft decisions stay with the chat.

**Quality before speed.** Every long video starts with its **opening at the finished look**: the first ~60 s built exactly as
the finished video will be (script, voice, pictures, graphics, sound, music, the gate). The creator chose at setup what happens
then (`creator/choices.toml`): **prototype first** (`prototype_first = true`): the opening goes to them as a prototype before the
rest is built, and their notes on it set the video's level; or **the whole video in one go** (`false`): the opening is the level and
the build goes straight on, and their first watch is the full film. Either way the full build carries the opening's level through. A documentary is as long as its material (checked on
the script before the voice: about 8 minutes or more for a full long video). The creator never needs to read a script: write it,
check it, build it; they judge the video. Shorts: one at a time, each with full effort. Titles, descriptions and tags come after the
creator calls the video done.

**Evidence, not assumptions** (`CLAUDE.md`): measure, fetch the primary source, or test; say "unverified" when you can't. Meta is
data; brake only for measured costs.

**Learning the creator's line.** Every verdict of the creator, passed or flagged, goes into its craft's casebook in `cases/` the same
turn, with their words and the line it draws. Before a piece goes to them, write the verdict you expect in `cases/PREDICTIONS.md` and
score it after their answer; every miss becomes a case. Builders and reviewers read their craft's casebook first. Over time the chat
predicts the creator's verdicts before they give them: that is the goal.

**When the creator corrects you.** Measure it on the spot; own the mistake plainly and fix it in the same turn; write their note into
the rules (replacing the rule it contradicts, without comment: `CLAUDE.md` office rule 2); a correction about one video is checked
across everything, since it is a sample of a class.

**Repeat mistakes get a mechanism.** A mistake made twice gets a fix where the fault starts (a tool that can't make it, a template that
starts right); a gate check only as the last resort, and never a loop of gate rounds.

**Never idle.** While a render or an agent runs, start the next piece. The Stop hook `tools/hooks/keep_working.py` refuses to let the
chat end its turn while its task list has open steps, unless the turn puts a real decision to the creator or a background job it
launched is still running.

**Write it down** (`CLAUDE.md` office rule 1): STATUS current, a session-log entry, decisions logged, commit by path.

## 4. The crafts

Each has its own standard: the bar (measurable where it can be), the method with the exact tools, the checks before the creator sees
it, and the research behind it. Re-read the file before the work.

| Craft | Standard | The bar in one line |
|---|---|---|
| Long form (edit, motion, pictures) | `standard/LONG_FORM.md`, `BAR_LONG_FORM.md`, `KIT3.md`, `3D.md`, `GRAPHICS_KIT2.md` | every picture on its words, real receipts shown, no flash frame or frozen shot, the speaker on screen for their own words, graphics built from real material |
| Shorts | `standard/SHORTS.md`, `BAR_SHORTS.md` | every element with its written reason, the words acted out with built graphics, the hero dead centre, a pan only with a job, a new matching picture every ~2 s |
| Sound, music and voice | `standard/SOUND_AND_VOICE.md`, `MUSIC.md`, `VOICE_LOCK.md` | one sound per action on its frame; music under the voice that fits each chapter; the voice warm from the first word, no word swallowed, American English |
| Scripts and packaging | `standard/SCRIPTS_AND_PACKAGING.md`, `SCRIPT_TRAINING.md` | specific and simple for a worldwide audience, said like a person in the niche, the creator's own view in it, a hook that opens a question, a title the video keeps |
| The machine | `standard/PIPELINE.md`, `WORKFLOW.md`, `CHECKLIST.md`, `REVIEWERS_EYE.md` | the gate before every render flags only real faults; every fix proven on a frame or a measure |

## 5. The workflow of a video

| Stage | Long form | Short |
|---|---|---|
| Idea | the creator's; before any work, the "already on YouTube?" check (a logged-in search: if bigger channels have it, find the untold part or another idea) | the creator's, or a Short-worthy moment of a long video |
| Research | current to the day of the build; receipts from the primary source; `kb/` updated; `standard/research/FOOTAGE_SOURCING.md` | same |
| Script | `standard/SCRIPTS_AND_PACKAGING.md`; the blind gate before the voice | same, the Shorts rules |
| The creator's view | the interview after the script: a few open questions, their answers blended in | one at most, when the Short has a take |
| Prototype | the first 60 s at the finished look, to the creator (when `creator/choices.toml` says prototype first) | the Short itself |
| Voice | the voice lock (`standard/VOICE_LOCK.md`): ready stamps, the machine's take pick, the chain and the sound gate, then locked | same, `[tts.short]` |
| Picture | `standard/LONG_FORM.md` (storyboard, an options board per shot, one design system per video) | `standard/SHORTS.md` |
| Sound and music | `standard/SOUND_AND_VOICE.md`, `standard/MUSIC.md` | same, its own music |
| Gate and render | `PIPE tools/pipeline/pipe.py <video> gate`, then render in parts; the render scan runs on every render | same |
| Delivery | the watchable copy to the creator the minute it exists (`SendUserFile`); their watch is the fix list | same |
| Packaging | after the creator calls it done: title, description, tags as copy blocks | title and tags |

## 6. The tools: the reusable core

The Python environments (`python tools/common/paths.py` prints them; `tools/requirements/README.md`): **PIPE** (the pipeline: `dj`,
sound, voice, the gate), **EDIT** (OpenCV, cut-outs, the picture, mix and QA tools), **VISION** (object detection), **ACCENT** (the
accent check) and, when the music is made in code, **SYNTH** (`tools/music`). Remotion lives in `tools/motion` (Node). Every path comes from
`tools/common/paths.py` (Python), `paths.sh` (bash) and `paths.mjs` (Node), which read `config/paths.toml`.

| Job | Tool |
|---|---|
| A video's line, step by step | `PIPE tools/pipeline/pipe.py <video> link | audit | gate | render | score | finish | srt | qa` from `videos/<video>/video.toml` (`standard/PIPELINE.md`); stages stamped by `tools/workflow/stages.py` |
| Voice | `tools/dj` (`cd tools && PIPE -m dj tts|captions ../videos/<video>`), `config/tts.toml`, `tools/voice/` (ready, autopick, the lock, lay-in, the guards) |
| Word timing | `tools/motion/sync_words.py` (the words the edit anchors to) |
| Footage | `kb/FOOTAGE.md` (the map of the creator's sources), `tools/footage/` (the footage brain: cuts, frames, descriptions, search), `catalogue.py`, `scan.py`, `peek.py` |
| Picture | Remotion: `tools/motion/src/` (`lib.tsx` for clips, `kit3/` the graphics kit, `kit3d/`, `house/`, `shorts/` the Shorts kits, `_template/` a new video's start), `tools/motion/prep_template.py` (a video's clip cuts) |
| Sound | `tools/sound/score.py` + one cue sheet per video (`videos/<video>/score/cues.py`), the house effects in the effects folder |
| Music | made in code: `SYNTH tools/music/music.py render videos/<video>/score/music.py` (`standard/MUSIC.md`), into the cue sheet with `code_beds`; or the creator's own tracks in MUSIC |
| Script | `tools/script/` (`script_lint.py`, `tell_lint.py`, `pair_test.py`, `judge_panel.py`, `blind_test.py`) |
| QA | the gate, `tools/qa/qa_render.py`, `tools/motion/qa_*.py`, the reviewer's eye (`tools/eye/`, `.claude/agents/reviewers-eye.md`) |
| Files to the creator | the app's `SendUserFile` tool; a file over 30 MB shows only in the desktop app, so say so |

## 7. The PC and the lines never crossed

- **The studio's folders are the chat's workspace**: this repo and MEDIA. Nothing outside them is touched (the creator's own files,
  their Recycle Bin or Trash).
- **Keys** live in `MEDIA/secrets/`: never printed, never committed, never opened by an agent. Config files are read by named keys
  only.
- **Heavy jobs take turns**: renders, 4K finishes, mixes, cut-outs and model loads hold a ticket from `tools/pipeline/heavy.py`; the
  hook `tools/hooks/commit_guard.py` refuses to start one while memory is at or over 85%; one Remotion render at a time. Agents that
  run heavy local jobs: a few at once, measured before each launch.
- **Kill only your own processes**: the hook `tools/hooks/no_kill_by_name.py` refuses kills by program name.
- **Deleting** is permanent (never the Recycle Bin or Trash; the hook `tools/hooks/no_recycle_bin.py` holds it); look at the target
  first. What to delete or keep inside the studio is the chat's call: keep what can make a future video better (the creator's
  signed-off videos, libraries the tools use, the songs of finished videos); a finished video's build files go once it is uploaded.
- **Disk**: keep about 50 GB free on the media drive; enough space is the chat's job.
- **Downloads** for a video need no asking. Official material from its primary source, in full quality; video downloads with yt-dlp
  (`standard/research/FOOTAGE_SOURCING.md`), modest, stopping at a sign-in or bot prompt.
- **Content lines**: no AI-generated images or footage in the videos; no leaked or stolen material, and never an ad for someone who
  leaks it; short clips of films, shows, other creators and streamers are normal commentary and need no warning; how much of one
  video others' material may fill is the creator's number per video; no false facts on screen.

## 8. Where things are

**The repo** (this folder): `CLAUDE.md`, this file and `standard/`, `rules/`, `cases/`, `creator/`, `kb/`, `videos/<video>/`
(script, cues, notes), `tools/`, `config/`, `STATUS.md`, `log/`, `decisions/`.
**MEDIA** (outside git, set in `config/paths.toml`): `videos/<video>/` (build, render, export), `motion/` (Remotion's public folder),
`footage/` (sources, stills, the footage brain's index), `sfx/` (effects), `music/`, `voice/` (the voice guard's approved and flagged takes, the
voice guard), `models/`, `tmp/` (render temp), `secrets/` (never opened by agents), `envs/` (the Python environments).

## 9. Keeping this standard true

- **This standard and the rules are the authority.** When the creator signs a new piece off as the standard, the bar files get it.
- Every new rule goes into its rules file in plain words with the creator's words beside it, and into the craft file it changes, the
  same turn.
- When a file here goes stale, fix it at once: a stale pointer misleads the next chat.
