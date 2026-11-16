# What's new

*The studio's versions, newest at the top. `UPDATE.md` brings a new version into a creator's folder. Each entry says what the version
brings, what to set up (in order, each command with its environment, PIPE, EDIT, VISION, ACCENT or SYNTH, and the tests that prove
it) and what to read; a file renamed or removed is named with what replaced it. This file is the studio's: a creator's chat never
writes in it (their own history goes to `log/`).*

## v1.9 (2026-11-16)
- **Brings:** a quiet chat while it works. Long stretches that need nothing from the creator (a study, downloads, checks, a
  render) show at most one label of a few words per stage, also when the app asks what the chat is doing: no counts, limits,
  retries or skipped items, no problems it handles itself, a correction said once, a choice not repeated back (`CLAUDE.md`,
  talking to the creator). The question to answer is the last line of a message. The keep-working hook no longer asks for a
  line when it moves the chat on. The setup starts the Shorts chat during the setup itself and tells the creator about it once,
  in the closing message (`SETUP.md` steps 13-14, `SHORTS_CHAT.md`). The effort ask says where the setting is.
- **Set up:** nothing (the hook reads its new wording at the next stop). A folder whose setup is done and whose Shorts chat was
  never started: start it now as `SHORTS_CHAT.md` says, and tell the creator in one line.
- **Read:** `CLAUDE.md`, "Talking to the creator" and "Effort follows the work".

## v1.8 (2026-11-16)
- **Brings:** one line in `CLAUDE.md`, talking to the creator: a question that doesn't hang on the running work (a render, a
  check) is asked in the message that ends the turn, not held back until the work is done; the work's result follows in one
  line, only if it changes something for them.
- **Set up:** nothing.
- **Read:** `CLAUDE.md`, "Talking to the creator".

## v1.7 (2026-11-16)
- **Brings:** three fixes to the look's pieces and one to how the chat talks. Tracked text is centred to the pixel: CSS tracking adds
  its space after the last letter too, which pushed the date, the turn card, the number, the stamp and the button labels a few
  pixels left of centre (`TRACK_END` in `tools/motion/src/look.ts`). The "underline" stamp now sits on the look's solid card
  surface with the bar along its bottom, so it reads on a bright sky too. The look board's header keeps a long look name on one
  line (its description wraps instead). `CLAUDE.md`, talking to the creator: a job that spans turns says each piece of news once,
  and the helpers behind the work are never mentioned. A folder whose chat already fixed any of these in `house/cards.tsx`,
  `house/signoff.tsx`, `_look/LookBoard.tsx` or `shorts/kitS.tsx`: the studio's fix covers it, so their change is not re-applied
  in the merge unless it did something more.
- **Set up:** nothing to install. `PIPE tools/motion/look_board.py --current --scale 2` and every tile looked at; the Template
  test render (`standard/PIPELINE.md` section 0).
- **Read:** `CLAUDE.md`, "Talking to the creator".

## v1.6 (2026-11-16)
- **Brings:** solid plates and clean shadows, found by looking at every tile at full size. Every look's card surface is fully solid
  (`colors.surface_alpha` 1: before, the picture showed faintly through the subscribe ask, the info cards and the question card);
  the "box" stamp sits on the look's solid card surface; the "underline" stamp's bar sits just under the letters, and its shadow is
  tight (no dark glow); the sign-off's two buttons cast one shadow together (the comment button's no longer darkens the like
  button's edge); the "bar" subscribe ask's avatar lost its half-see-through ring. The board's pictures: no bright sun behind an
  info card's edge or a number's words, and the sea's horizon higher so the sign-off has room under it.
- **Set up:** nothing to install. A creator whose look is already written: in `tools/motion/src/look.json`, `colors.surface_alpha`
  to 1 (keep theirs only if they chose see-through cards themselves), then `PIPE tools/motion/look_board.py --current --scale 2`
  and every tile looked at. A chat in step 11's look part renders the boards again.
- **Read:** nothing new.

## v1.5 (2026-11-16)
- **Brings:** the look's pieces and its board, redesigned and checked at full size in every look. The sign-off is one column on one
  axis at the frame's safe edge: the question card over a row of two same-height buttons, like and comment (centred low for "bar",
  right-aligned at the lower right for "corner"); nothing moves when "Like" turns "Liked". The subscribe ask sits on the same edge.
  The stamp's "underline" and "box" styles read on a bright picture (the words in the look's ink over the coloured bar; a dark plate
  inside the box). The board: a label on every piece, drawn pictures instead of blurs, a Short shown as two real frames (a caption
  and a hero word, outlined as the captions are), kit3's number beside the picture of what it counts, an info card as wide as its
  words. `look_board.py --scale 2` renders every tile as a whole 1920 x 1080 frame, for checking before anything is sent.
- **Set up:** nothing to install. A chat in step 11's look part renders the boards again and checks them at full size before
  sending.
- **Read:** `SETUP.md` step 11, items 1 and 2.

## v1.4 (2026-11-16)
- **Brings:** a look of the creator's own. Every graphic (the cards, numbers, stamps, kit3 and kit3d, the sign-off, the subscribe
  ask, the Shorts' flash and captions) now takes its fonts, colours, corners, shadows, pop and the asks' designs and words from one
  file, `tools/motion/src/look.json`. Four starting looks (`tools/motion/looks/`: Clean, Bold, Documentary, Playful), a board that
  shows a look on the studio's real pieces (`tools/motion/look_board.py`), and a setup step that makes the creator's own look with
  them from a starting one (`SETUP.md` step 11). Fonts come from a shelf of 19 Google Fonts (`tools/motion/src/fonts.ts`), with
  the extended Latin letters where a font has them; the Shorts captions use the look's caption font (before, a wrong font name
  fell back to Arial). The studio's default look and accent changed: a video made before this version keeps its own render; its
  next render takes the look.
- **Set up:** `PIPE tools/motion/look_fonts.py` (the look's display font as a file, for the 3D numbers). Then a creator whose
  setup is past step 11: run step 11's look part now (the four boards, their pick, their changes, then write it in), their accent
  and channel name carried into it; a chat in the middle of step 11 starts its look part over from item 1. `tools/motion/src/brand.ts`
  takes the studio's version, then their `BRAND` and `CHANNEL` lines go back in. `npx tsc --noEmit -p .` in `tools/motion` passes.
- **Read:** `SETUP.md` step 11, `UPDATE.md` ("What is the creator's": `look.json`, and brand.ts's two lines), `standard/KIT3.md` 1.2.

## v1.3 (2026-11-16)
- **Brings:** renders on any computer: the frames rendered at once are capped at the computer's CPU cores (before, a computer with
  fewer than 6 cores could not render at all), and a failed part's retries step lower from there. The chat's lines while it works are plain words, never the work's own (merge, commit,
  hook). The ElevenLabs API key: the direct link to the key page. The voice question names all three answers (a new clone of
  their voice, a clone already in their account, a stock voice); a clone already there is used only when they choose it. The voice sample is recorded by the studio:
  `tools/voice/record_sample.py` opens a page in the creator's browser (the text to read, the mic, a level bar, one Record
  button, Save), the file lands in its folder and the chat carries on by itself; `tools/voice/clone_voice.py` makes the instant
  clone in their ElevenLabs account, so they never upload by hand. The music setup sends no sample and asks nothing: the creator
  first hears the music in their first video. The music synthesizer stays inside the studio: on Windows its user folder moves
  from Documents to `SurgeXTUserData/` beside its library; on a Mac it is copied out of the official .dmg (no installer, no admin
  password, nothing in /Library).
- **Set up (music made in code only):** `PIPE tools/setup/surge.py --check` (it adds the Windows user folder; on a Mac set up with
  the old installer, `PIPE tools/setup/surge.py` copies Surge into the studio and the /Library copy can stay or go). On Windows,
  a `Documents/Surge XT` that holds nothing but Surge's empty folders and its README.txt was made by the studio: delete it.
- **Read:** `CLAUDE.md` ("Talking to the creator"), `SETUP.md` step 9 items 2 and 3, step 10. A chat in the middle of step 9 that asked
  for a recording by hand starts the recorder instead.

## v1.2 (2026-11-16)
- **Brings:** the voice from a weak mic: a clone sample from a headset or a laptop mic is rebuilt as if from a good mic before it is
  cloned (`tools/voice/rebuild_sample.py`, a speech restoration model; the creator picks between the two clones by ear). The Mac:
  the setup checks for Apple silicon and macOS 14 or newer (the Python packages exist ready-made only for those), the memory checks
  read macOS's own memory pressure, the voice scripts run on macOS's bash, renders link the media instead of copying it.
- **Set up:** nothing to install (EDIT has every package the rebuild needs; its model downloads into MEDIA/models/hf the first time).
- **Read:** `SETUP.md` step 9 (the mic check), step 1 on a Mac.

## v1.1 (2026-11-16)
- **Brings:** a chat that waits on the creator says so once: their step goes on the task list as "You: ..." and the keep-working hook
  lets the turn end there (before, it pushed the chat to write the same message again). No unasked warnings or side notes. The voice:
  the Creator plan is enough (48 kHz WAV tested on it), and an instant clone from a few minutes of speech is the recommended own voice.
- **Set up:** nothing to install (the hook runs from `tools/hooks/keep_working.py` as it is; `.claude/settings.json` is unchanged).
  A chat in the middle of the setup carries on from its step, now reading `SETUP.md` step 9 as it is in this version.
- **Read:** `CLAUDE.md` ("Talking to the creator", "Waiting on the creator"), `SETUP.md` step 9.

## v1 (2026-11-16)
- **Brings:** the first version: long videos and Shorts, from the idea to the finished film (script, voice, picture, sound, music in
  code, every check), as an environment of its own: its own programs and caches in its own folders, nothing of the computer's used
  or changed.
- **Set up:** `SETUP.md`, from step 1.
- **Read:** `CLAUDE.md`, then `STANDARD.md` (the study, its section 2).
