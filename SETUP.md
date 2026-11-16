# SETUP: from a fresh clone to the first video

*For the chat. The creator just cloned this repo and said "let's get started". You set the studio up with them, **one step at a
time**: say in one to three plain lines what happens now (and what they must do, if anything), do it, check it worked, write the step
as done in `STATUS.md` (Phase: "Setup: step N done"), then the next step. Never show the whole list; never ask what you can find out
yourself. You run every command; the creator only does what needs a human (an installer window, an account, a payment, a login, a
key, listening to a voice). When a step fails, find out why and fix it before going on. Adapt every step to what you find on their
computer: Windows works best (with an NVIDIA graphics card renders are fastest); on a Mac use the macOS lines. No warnings or side
notes along the way or at the end (how deletes work, disk space, what you checked): only what happens and what they do.*

**One go covers every install.** The creator's first message holds their OK for everything the setup and the videos download and
install (the README's message; when they only pasted the link, you asked for it once). Never ask again per program, package, model or file: say in a line what you are installing as you do it.
If their first message has no such OK, ask once for one go covering all of it, then never again.

**The studio is its own environment.** Everything it installs goes into its own two folders, the clone and MEDIA (step 1): its own
uv, Python, Node.js and ffmpeg, and every cache, model and setting of theirs. It never uses, updates, removes or reconfigures anything
the computer already has (another Python, Node or ffmpeg, a global setting, another project's folder or files, whatever another
`CLAUDE.md` or a memory says about them), so what is installed already doesn't matter: no step is skipped or changed because
something like it is there. The one exception is Git, which the clone needs: one that is there is used as it is; a missing one is
installed (`winget install --id Git.Git -e` on Windows; on a Mac `xcode-select --install`, whose window the creator clicks).

**Before step 1:** the studio is cloned into a new folder `studio` in the creator's user folder (`C:/Users/<name>/studio`, Mac
`~/studio`; if that path has a space or a non-English letter, `C:/studio`; if a `studio` with something in it is there already,
`studio-2`, and so on; say which in a line), or the folder they named. Never into the folder this chat runs in: the app may have made
it for this chat alone (it is deleted with the chat, and its long path breaks Chrome on Windows), and never into a folder OneDrive or
iCloud syncs. Every command below runs from that clone's root. Never ask them to make a folder, install Git or
run a command: that is yours. Then name the clone's source `studio`: `git remote rename origin studio` (new
versions of the studio come from it, `UPDATE.md`; a remote of the creator's own, if they ever want one, is then free to be `origin`).
Give this folder its own git identity, so the chats' commits work the same on every computer: `git config user.name "Studio"` and
`git config user.email "studio@localhost"` (this folder only: nothing global, nothing of the creator's).

---

## Part A: the computer (this chat)

### Step 1: look at the computer
Check, without asking: the OS and version, CPU (x64 or ARM), RAM, the graphics card (NVIDIA or not) and free space on each drive. No
need to look for programs: the studio brings its own. **A Mac needs Apple silicon (M1 or newer) and macOS 14 or newer** (`sw_vers
-productVersion`, `uname -m` = arm64): the studio's Python packages exist ready-made only for those. An older macOS: the creator updates
it first (System Settings, General, Software Update) and you wait; an Intel Mac can't run the studio: say so plainly, in one line. A long video needs about 100-200 GB free while it is made: the media root
(MEDIA) goes on the drive with the most room, in a **new folder** (one that doesn't exist yet, or is empty), a short path without
spaces: `D:/Studio` or `C:/Studio` (macOS `~/Studio`); if that one is taken, `Studio2`, and so on. Then tell the creator in two lines
what you found and where the studio will live.

### Step 2: the media root, uv and the pipeline's Python
1. Write `config/paths.toml` from `config/paths.example.toml` with `media = "<the folder from step 1>"` (forward slashes).
2. **uv** (it installs the studio's Pythons), version 0.13.6 from its release, into `MEDIA/apps/uv`. Below, `<MEDIA>` is the folder
   written out.
   - Windows (the same lines in PowerShell and Git Bash; an ARM computer takes `uv-aarch64-pc-windows-msvc.zip`):
     `curl.exe -L --fail --create-dirs -o <MEDIA>/tmp/downloads/uv.zip https://github.com/astral-sh/uv/releases/download/0.13.6/uv-x86_64-pc-windows-msvc.zip`,
     then its SHA-256 (`certutil -hashfile <MEDIA>/tmp/downloads/uv.zip SHA256`) must be
     `a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f` (ARM: `c2426c0c8e28b53d8c440e47a18d96ad4db51e159866c0e81435b196d7f0081c`),
     then `mkdir` the folder `<MEDIA>/apps/uv` and `C:/Windows/System32/tar.exe -xf <MEDIA>/tmp/downloads/uv.zip -C <MEDIA>/apps/uv`.
   - macOS (Apple silicon):
     `curl -L --fail --create-dirs -o <MEDIA>/tmp/downloads/uv.tar.gz https://github.com/astral-sh/uv/releases/download/0.13.6/uv-aarch64-apple-darwin.tar.gz`,
     then `shasum -a 256` of it must be `60fbd5c8a1ed681845eea28d9d622fcde03c51e91a43465b64a1e17db1ed3472`, then
     `mkdir -p <MEDIA>/apps/uv && tar -xzf <MEDIA>/tmp/downloads/uv.tar.gz -C <MEDIA>/apps/uv --strip-components 1`.
   A hash that doesn't match: delete the file, download it once more; a second mismatch stops the setup (tell the creator).
3. **The pipeline's Python** into `MEDIA/apps/python`, then its environment (still empty) in the clone, with `<UV>` =
   `<MEDIA>/apps/uv/uv.exe` (macOS `<MEDIA>/apps/uv/uv`):
   `<UV> python install 3.14.0 --install-dir <MEDIA>/apps/python --no-bin --no-registry --no-config --cache-dir <MEDIA>/cache/uv`
   (`--no-bin --no-registry`: nothing is put on PATH or into Windows' registry), then
   `<UV> venv tools/.venv --python <the python of the one cpython-3.14.0 folder in MEDIA/apps/python> --no-config --cache-dir <MEDIA>/cache/uv`
   (Windows `.../python.exe`, macOS `.../bin/python3.14`). From here PIPE is `tools/.venv/Scripts/python.exe` (macOS
   `tools/.venv/bin/python`), and every step runs through it.
4. `PIPE tools/common/paths.py --init` creates MEDIA's folders and prints every path; check it shows them all.

### Step 3: Node.js and ffmpeg
`PIPE tools/setup/apps.py`: the studio's own Node.js and ffmpeg, pinned releases checked against their published SHA-256, unpacked
into `MEDIA/apps`; it ends by checking every program (uv, node, npm, ffmpeg, ffprobe) and prints `ok` for each. From now on the tools
find them by themselves (`tools/common/paths.py`). A command of yours that runs one of them directly (node, npm, npx, uv, ffmpeg,
ffprobe) goes through `PIPE tools/common/paths.py --run [--in <folder>] <command>`, which gives it the studio's programs and caches,
so it never reaches a program the computer has of its own.

### Step 4: the Python environments
`PIPE tools/setup/envs.py` builds the four environments (PIPE's packages, EDIT, VISION, ACCENT; SYNTH comes only in step 10) with the
studio's uv on Pythons it installs into `MEDIA/apps/python`, installs each pinned file of `tools/requirements/` (torch as the CPU
build), puts the studio's start-up file into each one and checks each one's key imports (`ok` per environment). It downloads a few
GB: run it in the background, tell the creator it takes a while and keep going with step 5 meanwhile.

### Step 5: Remotion (the video engine)
`PIPE tools/common/paths.py --run --in tools/motion npm ci`. Then a test render of the template composition (a few seconds,
`standard/PIPELINE.md` section 0 names the command; run it through `--run` the same way): it proves headless Chrome, the GPU setting
and ffmpeg work. On Windows with NVIDIA the config renders on the GPU; if the render fails on the GPU, switch the config to the
software renderer and say so in one line.

### Step 6: the models
`PIPE tools/setup/models.py` downloads the small models the tools use (face detection and matching, object detection, text
embeddings, the speech-to-text model) into MEDIA/models and checks each file. Whisper's model downloads on first use.

### Step 7: the house sound effects
`PIPE tools/sound/palette_from_manifest.py` unpacks `assets/house_sfx.zip` into MEDIA's effects folder (`MEDIA/sfx/house`) and builds
the effects palette from its manifest. Check (`--check`): the palette lists all 29 effects and each file opens.

### Step 8: the hooks, then a fresh chat
`PIPE tools/hooks/install_hooks.py` writes `.claude/settings.json` (the hooks that keep the work safe and moving: the studio's own
programs and caches for every command, the memory guard, no kills by name, permanent deletes, keep working). The app loads hooks and this repo's `CLAUDE.md` when a chat starts, so the setup
continues in a fresh chat that runs in the studio folder itself. Write STATUS.md ("Setup: step 8 done, next step 9") and commit. If
your app gives you a way to start a new session in another folder, start it yourself in the studio folder with the message below and
tell the creator in one line where to find it. Otherwise tell them, as the final message (with the clone's full path written out),
one line that part one worked, then this, and nothing else:

> Part one is done. Now open a **new chat in the studio folder** (Code tab, choose the folder `<the clone's full path>`) and say
> **"Let's get started. You have my OK to download and install everything the setup and our videos need."** That chat is your main
> chat from now on; it finishes the setup with you.

---

## Part B: the voice, the music, the creator (the main chat)

*A chat that finds "Setup: step 8 done" in STATUS.md starts here, after reading CLAUDE.md. The study (STANDARD.md section 2) comes
after the setup, before the first video.*

First, one check in Bash: `command -v node ffmpeg` prints the two in `MEDIA/apps` (the hook from step 8 put the studio's programs
first). If it prints other places or nothing, the hook didn't reach this shell: run `PIPE tools/hooks/install_hooks.py` again,
and until a fresh chat has them, run those programs through `PIPE tools/common/paths.py --run` (never the computer's own).

### Step 9: the voice
1. The creator needs an **ElevenLabs** account on the **Creator** plan: the studio's voice comes as uncompressed 48 kHz WAV
   (`wav_48000`), tested and working on Creator (Pro is not needed; the cheaper Starter was never tested for it). They make it
   themselves at https://elevenlabs.io; you wait.
2. Ask: **their own voice, or a stock voice?**
   - **Their own, as an instant clone (recommended):** 1-3 minutes of clean speech, ready in minutes. It is the kind of clone the
     studio's own videos were made with, at the level they show. Guide the recording in plain steps: a quiet room, a phone or a
     microphone close to the mouth, the same distance throughout, reading anything in their normal telling-a-friend voice, no music.
     They put the file into `MEDIA/voice/sample/` (you make the folder and open it for them). Then the **mic check**:
     `EDIT tools/voice/rebuild_sample.py <the file> --check`. A full-band mic: they upload that file in ElevenLabs as an instant voice
     clone (where that is in today's ElevenLabs, you look up and tell them). A narrow mic (a headset, a laptop or Bluetooth mic: an
     instant clone copies the mic too, so its voice would sound muffled whatever comes after): rebuild the sample first,
     `EDIT tools/voice/rebuild_sample.py <the file>` (a few minutes; it writes `<name>_rebuilt.wav` beside it), and they upload both
     files as two instant clones, "<name>" and "<name> rebuilt". They tell you the names when the clones are ready; with two, the
     test in item 5 voices the same sentences with both and they pick by ear (the rebuilt one usually wins), and only the pick goes
     into `config/tts.toml`. Nothing is ever processed on the voice afterwards: the clone itself sounds right.
   - **A professional clone** only if they ask for one, now or later: 30 minutes or more of recording and some hours of training,
     closer still to their voice; the same guide, longer.
   - **A stock voice:** pick 4-5 American English narrator voices from the Voice Library that fit `creator/PROFILE.md`'s mood (if the
     interview hasn't run yet, ask two questions first: calm or punchy, deeper or lighter), render the same two sentences in each
     through the pipeline, send the files, the creator picks one.
3. **The API key:** the creator makes one at https://elevenlabs.io/app/api/api-keys (the link ElevenLabs' own quickstart
   gives; a key with no restrictions on what it may do) and pastes it into the file `MEDIA/secrets/elevenlabs_api_key.txt`
   themselves (you create the empty file and open its folder for them; you never see, print or type the key).
4. Write `config/tts.toml` from `config/tts.example.toml` with the voice id (from the ElevenLabs API: list the voices and match the
   name) and the settings the template gives for long form and `[tts.short]`.
5. Test: a three-sentence take through `dj tts` (with two clones: the same three sentences from each, sent as two files named A and B,
   and the pick goes into `config/tts.toml`), the accent check and the voice guard's first calibration (`standard/VOICE_LOCK.md`);
   send it. When the creator likes it, save it as their first approved take in `MEDIA/voice/guard/approved/` (the guard's reference grows
   from their approved takes).

### Step 10: the music
Ask once: **should the chat make the music in code, or do they want to pick the music themselves?** Say plainly that the chat can make
good, fitting music for each chapter itself.
- **Made in code:** `standard/MUSIC.md`, section 8: Surge XT (`PIPE tools/setup/surge.py`: covered by their one go, no new ask),
  the SYNTH environment (`PIPE tools/setup/envs.py synth`), then its test in order (selftest, the patches, the model, the example's four beds AT THE BAR) and the example's
  opening bed sent to them, so they hear what you make. The music of each video is then written on its narration's word times.
- **Their own picks:** they put tracks they have the rights to into `MEDIA/music/` (any folders); the chat analyses them
  (`tools/sound/analyze_tracks.py`) and picks per chapter by the mixing rules in `standard/SOUND_AND_VOICE.md`.
Both can be mixed: the choice is written in `creator/PROFILE.md` and can change any time.

### Step 11: the interview
Run `creator/interview/PLAN.md` round 1 as a conversation (a few questions at a time). Their answers go verbatim into
`creator/interview/round-01.md`, your reading into `creator/PROFILE.md`. Then set their accent colour in
`tools/motion/src/brand.ts` and their sign-off (if they want one), and render one still of a title card and the sign-off to show
them.

Then one question, on its own, in these plain words (adapt only the language): "How should I make each long video? **1. Prototype
first:** I build the first minute exactly as the finished video will look, you watch it and give notes, and only then I build the
rest, so anything that isn't your taste is caught before hours go into it (the safer pick while I'm still learning your taste).
**2. The whole video in one go:** faster to a finished video; your first watch is the full video, and your notes come after. You can
switch any time." Write the answer into `creator/choices.toml` (`prototype_first = true` for 1, `false` for 2) and a line in
`creator/PROFILE.md`; commit. When they later say to switch, change the same key.

### Step 12: the niche's words and the human corpus
From the creators they named: build the human-script corpus (`tools/script/human_corpus.py`, captions of those creators' videos) and
the lingo study (`kb/LINGO.md`, `standard/research/LINGO.md`). These are what scripts are measured against
(`standard/SCRIPT_TRAINING.md`). Downloads go through yt-dlp, modest; if YouTube asks for a sign-in, the creator exports their
browser's YouTube cookies into `MEDIA/secrets/yt_cookies.txt` (guide them; never handle the cookies yourself).

### Step 13: the Shorts chat
Start the Shorts chat as `SHORTS_CHAT.md` says, then tell the creator: Shorts ideas go there, long videos come here.

### Step 14: ready
Write STATUS.md: "Setup done. Next: the study, then the first video." Commit. Run the study (STANDARD.md section 2), brief the creator
in 3 lines, and ask for the first topic. The first long video starts as a 60-second prototype at the finished look, or is built
whole in one go, as `creator/choices.toml` says (`standard/WORKFLOW.md`).
