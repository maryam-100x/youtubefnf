# Studio: a Claude-run video studio for YouTube

This repo turns a Claude chat into a full video partner: it researches, writes the script, voices it with your AI voice, edits the
picture in code (Remotion), places the sound and music, checks every frame and every word before a render, and hands you the finished
video. Long-form documentary-style videos and Shorts, for any niche.

## Start
1. Install the **Claude desktop app** (https://claude.ai/download) and sign in. You need a paid Claude plan (Max is recommended: a
   video is a lot of work).
2. Open the app's **Code** tab and send this message (if it asks you to choose a folder first, any folder is fine: the chat makes
   the studio's own folder in your user folder):

   **Set up the video studio from https://github.com/maryam-100x/youtubefnf. You have my OK to download and install everything the
   setup and our videos need.**

That's all. The chat installs everything, sets the studio up with you one step at a time and tells you whenever it needs you (an
account, a sign-in, a click). The last sentence lets it install everything without asking you each time. The studio keeps its own
copies of every program in its own folders: nothing else on your computer is changed.

Only if the app says Git is missing before you can start (Windows): install it from https://git-scm.com/download/win and open the app
again. A Mac needs an M1 chip or newer and macOS 14 or newer; if a window asks to install developer tools, click Install.

You'll also need a paid **ElevenLabs** plan for the voice; the chat walks you through it when it's time. Music is made by the chat in
code, or you pick your own.

## New versions
The studio gets new versions now and then (`CHANGELOG.md` says what each brings), and your main chat tells you when one is out. To
bring one in, tell your main chat: **"Update the studio. You have my OK to download and install what it needs."** It brings the new
version in and keeps everything that's yours: your rules and taste, your voice, your videos, your settings. It sets up anything new.

## For the Claude chat that got this link
The creator wants this studio set up on their computer, even if all they wrote was the link and "start". Do it yourself; their part
is only what needs a human.
1. If you can't run commands on this computer (a plain chat, not the desktop app's Code tab), say in one line: open the Code tab of the
   Claude desktop app and paste the link there.
2. If their message has no OK for downloads and installs, ask once, in one line, for one go covering everything the setup and the
   videos download and install; never ask again per item.
3. Clone the repo into a new folder `studio` in the creator's user folder (`C:/Users/<name>/studio`, Mac `~/studio`; if that path
   has a space or a non-English letter, `C:/studio`; if a `studio` with something in it is there, `studio-2`), or the folder they
   named. Never into the folder this chat runs in: the app may have made it for this chat alone (deleted with the chat, and its long
   path breaks Chrome on Windows). `git clone https://github.com/maryam-100x/youtubefnf <that folder>`. Install Git first if it is
   missing (`winget install --id Git.Git -e` on Windows, `xcode-select --install` on a Mac). Install nothing else yourself: the
   studio brings its own copies of every program and never uses or changes the computer's own.
4. Read the clone's `CLAUDE.md`, then follow its `SETUP.md` from the first step. One step at a time: say what happens, do it, check it
   worked, then the next.
