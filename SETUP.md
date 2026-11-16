# SETUP: from a fresh clone to the first video

*For the chat. The creator just cloned this repo and said "let's get started". You set the studio up with them, **one step at a
time**: say in one to three plain lines what happens now (and what they must do, if anything), do it, check it worked, write the step
as done in `STATUS.md` (Phase: "Setup: step N done"), then the next step. Never show the whole list; never ask what you can find out
yourself. You run every command; the creator only does what needs a human (an installer window, an account, a payment, a login, a
key, listening to a voice). When a step fails, find out why and fix it before going on. Adapt every step to what you find on their
computer: Windows works best (with an NVIDIA graphics card renders are fastest); on a Mac use the macOS lines.*

**One go covers every install.** The creator's first message holds their OK for everything the setup and the videos download and
install (README, step 3). Never ask again per program, package, model or file: say in a line what you are installing as you do it.
If their first message has no such OK, ask once for one go covering all of it, then never again.

**Before step 1:** if the repo was cloned into a subfolder rather than into the folder this chat runs in, say so and continue there
(every command below runs from the repo's root). Then name the clone's source `studio`: `git remote rename origin studio` (new
versions of the studio come from it, `UPDATE.md`; a remote of the creator's own, if they ever want one, is then free to be `origin`).
If `git config user.name` prints nothing, give this folder its own git identity, so the chats' commits work:
`git config user.name "Studio"` and `git config user.email "studio@localhost"` (this folder only, nothing global, nothing of the
creator's).

---

## Part A: the computer (this chat)

### Step 1: look at the computer
Check, without asking: the OS and version, CPU, RAM, the graphics card (NVIDIA or not), free space on each drive, and which of these
are already installed: Git, `uv`, Node.js (version), ffmpeg (version), Python. Then tell the creator in two lines what you found and
what you will install. A long video needs about 100-200 GB free while it is made: pick the drive for the media root (MEDIA) with the
most room (a short path without spaces, e.g. `D:/Studio` or `C:/Studio`; macOS `~/Studio`).

### Step 2: install the programs that are missing
- **Windows** (winget, one at a time, each checked with its `--version` afterwards):
  `winget install --id astral-sh.uv -e`, `winget install --id OpenJS.NodeJS.LTS -e` (Node 24 or newer),
  `winget install --id Gyan.FFmpeg -e`. A new terminal may be needed for PATH: re-check with the full path if a command isn't found.
- **macOS**: Homebrew first if missing (the creator runs its one-line installer from https://brew.sh in Terminal, since it asks for
  their password), then `brew install uv node ffmpeg`.
- Git is already there (the clone worked).
Python itself is installed by `uv` in step 4, in the exact versions the pipeline needs.

### Step 3: the media root and the paths
Write `config/paths.toml` from `config/paths.example.toml` with `media = "<the folder from step 1>"` (forward slashes). Then
`uv run --no-project python tools/common/paths.py --init` creates MEDIA's folders and prints every path; check it shows them all.

### Step 4: the Python environments
From `tools/requirements/README.md`: create the four environments (PIPE, EDIT, VISION, ACCENT; SYNTH comes only in step 10) with `uv venv <place> --python <version>` and install each file
with `uv pip install -r tools/requirements/<file> --python <env python>` (the torch line on Windows: that README). Check each by
importing its key packages (`dj`'s imports for PIPE, `cv2, librosa, torch` for EDIT, `ultralytics` for VISION, `speechbrain` for
ACCENT). This step downloads a few GB: tell the creator it takes a while and keep going with step 5 meanwhile.

### Step 5: Remotion (the video engine)
`cd tools/motion && npm ci`. Then a test render of the template composition (a few seconds, `standard/PIPELINE.md` names the
command): it proves headless Chrome, the GPU setting and ffmpeg work. On Windows with NVIDIA the config renders on the GPU; if the
render fails on the GPU, switch the config to the software renderer and say so in one line.

### Step 6: the models
`PIPE tools/setup/models.py` downloads the small models the tools use (face detection and matching, object detection, text
embeddings, the speech-to-text model) into MEDIA/models and checks each file. Whisper's model downloads on first use.

### Step 7: the house sound effects
Unpack `assets/house_sfx.zip` into MEDIA's effects folder and build the effects palette from its manifest
(`PIPE tools/sound/palette_from_manifest.py`). Check: the palette lists all 29 effects and each file opens.

### Step 8: the hooks, then a fresh chat
`PIPE tools/hooks/install_hooks.py` writes `.claude/settings.json` (the hooks that keep the work safe and moving: the memory guard,
no kills by name, permanent deletes, keep working). The app loads hooks and this repo's `CLAUDE.md` when a chat starts, so the setup
continues in a fresh chat. Write STATUS.md ("Setup: step 8 done, next step 9"), commit, and tell the creator, as the final message:

> Part one is done. Now open a **new chat in this same folder** (Code tab, this folder) and say **"Let's get started. You have my
> OK to download and install everything the setup and our videos need."** That chat is your main chat from now on; it finishes the
> setup with you.

---

## Part B: the voice, the music, the creator (the main chat)

*A chat that finds "Setup: step 8 done" in STATUS.md starts here, after reading CLAUDE.md. The study (STANDARD.md section 2) comes
after the setup, before the first video.*

### Step 9: the voice
1. The creator needs an **ElevenLabs** account on a paid plan (Creator or higher for a professional voice clone; Starter is enough for
   an instant clone or a stock voice). They make it themselves at https://elevenlabs.io; you wait.
2. Ask: **their own voice, or a stock voice?**
   - **Their own (a clone):** an instant clone needs 1-3 minutes of clean speech; a professional clone needs 30 minutes or more and
     sounds much closer (recommended for a channel). Guide the recording in plain steps: a quiet room, a phone or a microphone close
     to the mouth, the same distance throughout, reading anything in their normal telling-a-friend voice, no music. They upload it in
     ElevenLabs (Voices -> Add a new voice) and tell you the voice's name when it is ready.
   - **A stock voice:** pick 4-5 American English narrator voices from the Voice Library that fit `creator/PROFILE.md`'s mood (if the
     interview hasn't run yet, ask two questions first: calm or punchy, deeper or lighter), render the same two sentences in each
     through the pipeline, send the files, the creator picks one.
3. **The API key:** the creator makes one in ElevenLabs (Profile -> API keys) and pastes it into the file `MEDIA/secrets/elevenlabs_api_key.txt`
   themselves (you create the empty file and open its folder for them; you never see, print or type the key).
4. Write `config/tts.toml` from `config/tts.example.toml` with the voice id (from the ElevenLabs API: list the voices and match the
   name) and the settings the template gives for long form and `[tts.short]`.
5. Test: a three-sentence take through `dj tts`, the accent check and the voice guard's first calibration (`standard/VOICE_LOCK.md`);
   send it. When the creator likes it, save it as their first approved take in `MEDIA/voice/guard/approved/` (the guard's reference grows
   from their approved takes).

### Step 10: the music
Ask once: **should the chat make the music in code, or do they want to pick the music themselves?** Say plainly that the chat can make
good, fitting music for each chapter itself.
- **Made in code:** `standard/MUSIC.md`, section 8: Surge XT (`PIPE tools/setup/surge.py`: covered by their one go, no new ask),
  the SYNTH environment (`tools/requirements/synth.txt`, the same way as
  the others), then its test in order (selftest, the patches, the model, the example's four beds AT THE BAR) and the example's
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
