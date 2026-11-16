# What's new

*The studio's versions, newest at the top. `UPDATE.md` brings a new version into a creator's folder. Each entry says what the version
brings, what to set up (in order, each command with its environment, PIPE, EDIT, VISION, ACCENT or SYNTH, and the tests that prove
it) and what to read; a file renamed or removed is named with what replaced it. This file is the studio's: a creator's chat never
writes in it (their own history goes to `log/`).*

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
