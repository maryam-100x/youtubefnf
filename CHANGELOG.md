# What's new

*The studio's versions, newest at the top. `UPDATE.md` brings a new version into a creator's folder. Each entry says what the version
brings, what to set up (in order, each command with its environment, PIPE, EDIT, VISION, ACCENT or SYNTH, and the tests that prove
it) and what to read; a file renamed or removed is named with what replaced it. This file is the studio's: a creator's chat never
writes in it (their own history goes to `log/`).*

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
