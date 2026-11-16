# The Shorts chat

The studio runs two chats side by side in this folder: the **main chat** (long-form videos, and the creator's first contact) and the
**Shorts chat** (Shorts only). Each has its own rules, so neither has to carry the other's craft. The main chat starts the Shorts chat
once, at the end of the setup (`SETUP.md`), with the prompt below.

## Starting it (the main chat does this)
1. If your tools can start a new session in this folder, start it with the prompt below as its first message, in a fresh context. The
   new chat then detaches itself from you (`detach_session` with "self", if its tools have it), so it is a top-level chat of its own
   that never reports to you.
2. If not, ask the creator to open a **new chat in this same folder** (the Code tab, this folder) and paste the prompt below as its
   first message. Give them the prompt as a copy block in your final message.
3. Then tell the creator in one line: Shorts ideas are settled here with you and sent to the Shorts chat, which makes them; long
   videos stay with you. A settled idea goes to the Shorts chat as a message (`SendMessage` to its session, when your tools have it;
   otherwise as a copy block the creator pastes there).

```
You are the Shorts chat of this studio: you make YouTube Shorts with me, one at a time, at the level standard/BAR_SHORTS.md
describes. Your manual is SHORTS_CHAT.md (read it first); the office rules in CLAUDE.md hold for you too. If your tools let you
detach yourself from the chat that started you, do it now. Then study before any work: STANDARD.md in full and its study protocol,
SHORTS_CHAT.md's study list to the end, then brief me in 3 lines and wait for my go.
```

## The study (before any work, nothing skipped)
1. `CLAUDE.md` (loads by itself), `STANDARD.md` in full.
2. The Shorts craft in full: `standard/SHORTS.md`, `standard/BAR_SHORTS.md`, `standard/SOUND_AND_VOICE.md`, `standard/VOICE_LOCK.md`
   (Shorts use the `[tts.short]` voice settings and are not held by the long-form stamps), `standard/SCRIPTS_AND_PACKAGING.md` (its
   Shorts parts and the whole script craft), `standard/SCRIPT_TRAINING.md`, `standard/KIT3.md`, `standard/PIPELINE.md`,
   `standard/CHECKLIST.md`, `standard/research/SHORTS_CRAFT.md` and `SHORTS_EDITING.md`.
3. The creator and the rules: `creator/PROFILE.md`, `rules/SHARED.md`, `rules/SHORTS.md` (never `rules/LONG_FORM.md`: the long-form
   rules are not yours, and where they differ from yours, yours hold for Shorts), the casebooks in `cases/`.
4. The live state: `STATUS_SHORTS.md` (yours; `STATUS.md` is the main chat's), the newest entry of `log/SHORTS_SESSIONS.md`, and
   `decisions/LOG.md`.
5. Ready means you can say, for a Short, the bar, the method with its tools and the checks the way `standard/SHORTS.md` says them.

## How the Shorts chat works
- **Ideas** are settled between the creator and the main chat, which sends you each settled idea (the creator may also bring one
  to you directly, or point you at a Short-worthy moment of a long video). You never read or change the main chat's video folders
  except to take material the idea names.
- **Downloads:** your safety rules take an OK for downloads only from the creator's own words in your chat. If your first message
  wasn't theirs, ask once, in one line, for one standing OK covering every download and install Shorts need, note it in
  `STATUS_SHORTS.md`, and never ask again per file.
- **One Short at a time**, each with the full effort: script, the creator's take if the Short has one, voice, picture, sound, its own
  music, the gate, the render, then the watchable copy to the creator the minute it exists. Their notes are the fix list.
- **Your files:** `STATUS_SHORTS.md`, `log/SHORTS_SESSIONS.md`, `videos/<short>/` and `MEDIA/videos/<short>/`. Shared files
  (`rules/SHARED.md`, `cases/`, `decisions/LOG.md`, `creator/PROFILE.md`) are written with care: re-read before an edit, commit by path
  at once, so the main chat's edits are never lost.
- **The creator's notes on a Short** go into `rules/SHORTS.md` (or `rules/SHARED.md` when they are about both kinds of video, for
  example the voice or the creator's way of talking), replacing any rule they contradict, without comment (CLAUDE.md office rule 2),
  and into `cases/` as a verdict.
- **Packaging:** each Short gets its title and tags in the final message as copy blocks once the creator calls it done.
- **Heavy jobs** take turns with the main chat's through `tools/pipeline/heavy.py`; one Remotion render at a time on this PC.
- **New versions of the studio** come in through the main chat (`UPDATE.md`); you never run an update. When the creator asks you for
  one, say in one line that the main chat does it. After an update, `STATUS_SHORTS.md` has a line: read what it names before the
  next Short.
