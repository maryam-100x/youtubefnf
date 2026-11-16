# UPDATE: bringing in a new version of the studio

*For the main chat. The studio this folder was cloned from gets new versions now and then (a new craft, better tools, fixes);
`CHANGELOG.md` says what each version brings. An update brings the new version in and keeps everything that is the creator's. The
main chat runs it; the Shorts chat never does (it reads its line in `STATUS_SHORTS.md` afterwards).*

## When
- **The creator asks** ("Update the studio", in any words). Their words carry the OK for the downloads and installs the update needs
  (a chat takes an OK only from the creator's own words in it; if their message has none, ask once, in one line, for one go that
  covers everything the update brings, and never ask again per item).
- **At the start of each new long video** the main chat checks quietly: steps 2 and 3 below, a fetch only, nothing changes. A new
  version: tell the creator in one line what it brings and that "update" brings it in. Nothing new, or the fetch fails (offline):
  say nothing about it.
- **Never in the middle of a video.** A video being built keeps the tools it started with: the update waits until that video is
  uploaded, and the chat says so in one line. If the creator says "now", it runs now.

## What is the creator's
- **Their files:** `STATUS.md`, `STATUS_SHORTS.md`, `HANDOFF.md`, `log/`, `decisions/`, `creator/`, `cases/`, `kb/`, `videos/` (all but
  `videos/_template/`), `tools/motion/src/brand.ts`, `tools/sound/names.json`, `standard/research/LINGO.md`; each video's code in
  `tools/motion/` (`src/<video>/`, `prep<id>*.py` and their `_clips.json`); the files the tools write as videos are made
  (`tools/motion/src/clipdurs.json`, `tools/motion/src/clipedges.json`, `tools/motion/data/*.json`); in `tools/motion/src/Root.tsx`
  their videos' registrations (both sides' registrations stay); the git-ignored ones
  (`config/paths.toml`, `config/tts.toml`, `.claude/settings.json`, `tools/sound/palette.json`), which an update changes only where a new version's "Set up" says
  so (a new key); and MEDIA, outside the repo, which an update never touches.
- **Every change their side made to any other file:** a rule rewritten to the creator's taste (CLAUDE.md office rule 2), a standard
  adjusted to them, a tool their chat fixed for their computer.

**The rule of every update: their changes win; the studio's additions come in.**

## The steps
1. **Ready.** `PIPE tools/pipeline/heavy.py` shows no heavy job (no render, mix or finish from either chat); if one runs, wait for it.
   `git status --short`: changed tracked files are the creator's work not committed yet; commit them by path ("before the studio
   update"). Untracked files stay as they are. (A commit that fails for "Author identity unknown": the folder's own identity, as
   `SETUP.md` gives it before step 1.)
2. **The source.** The studio is the remote named `studio` (`git remote -v`; the setup names it so). Without one: the remote whose
   address is the repository this folder was cloned from, renamed to `studio`; if there is none, ask the creator once for the link
   they cloned from and `git remote add studio <link>`. Then `git fetch studio` and `git remote set-head studio --auto`.
   `git log --oneline HEAD..studio/HEAD` empty means up to date: tell the creator in one line and stop.
3. **What's new.** `git diff HEAD...studio/HEAD -- CHANGELOG.md` shows the new entries (newest at the top). Each says what it brings,
   what to set up and what to read. A version needs nothing more than its entry and this file.
4. **A way back.** `git tag before-update-<version>` (the newest new entry's version, for example `before-update-v2`).
5. **Merge.** `git merge --no-ff --no-commit studio/HEAD`, then:
   - **Conflicts** (`git diff --name-only --diff-filter=U`), each settled by the rule of every update, then `git add <file>`:
     - *A creator file* (the list above): keep this folder's side, `git checkout --ours -- <file>`. If the new version's entry says
       the file needs something new (a field, a heading), add only that, their content untouched.
     - *Prose* (rules, standards, manuals): lines their side changed stay theirs; the studio's other new lines come in. When both
       sides added a rule with the same number, both stay and the studio's takes the next free number (and the incoming files that
       name it are changed to match).
     - *Code:* take the studio's version, `git checkout --theirs -- <file>`. Then read what their side changed in it
       (`git log -p $(git merge-base HEAD studio/HEAD)..HEAD -- <file>`; for a renamed file, under its old name, which the entry
       gives) and apply that change again if it is still needed (a fix for their computer, a feature they asked for). Then the
       file still runs (its `--help`, its selftest) and their change still does what it was for.
     - *A file the studio removed or renamed that their side changed:* the entry says what replaced it; carry their change there
       (as code above), then `git rm <old file>`. Every mention of the old name in the studio's files (`git grep -n <old name>`)
       is changed to the new one.
     (`--ours` is this folder, the creator's side; `--theirs` is the studio's new version.)
   - **Clashes git can't see.** A new studio rule can contradict one of the creator's without touching the same lines. Read what
     comes in for the rules and standards (`git diff HEAD...studio/HEAD -- rules/ standard/ STANDARD.md CLAUDE.md SHORTS_CHAT.md`)
     against the creator's own: their side's changes (`git diff $(git merge-base HEAD studio/HEAD) HEAD -- rules/ standard/
     STANDARD.md CLAUDE.md SHORTS_CHAT.md`), `cases/` and `creator/PROFILE.md`. Where a new studio rule contradicts theirs (both
     can't be followed), theirs stays and the studio's is taken out of the merge, silently (office rule 2). Where the two only pull
     against each other (both can be followed), both stay and theirs decides where they meet. A studio rule they had replaced
     stays replaced, whatever its new wording. A clash settled here goes into `decisions/LOG.md` (one record), never to the
     creator.
   - **Commit:** `git commit -m "Studio update to <version>"`. This commit takes the whole merge (a merge can't be committed by
     path), so first: no `.git/index.lock` (the Shorts chat is not in the middle of a commit), and `git diff --cached --name-only`
     shows only the merge's files.
6. **Set up what's new.** Each new entry's "Set up" items, oldest version first, the way `SETUP.md` runs a step: say what in one
   line, do it, check it worked (an item step 5 already did is checked, not done twice). Whatever the entry says: a changed file under `tools/requirements/` is installed into the
   environment it names, a changed `package.json` gets `npm install` in its folder, a changed `tools/hooks/settings.template.json`
   gets `PIPE tools/hooks/install_hooks.py` (the hooks load in the next chat).
7. **Check.** The tests each entry names, all passing, before the next piece of work.
8. **Read and write down.** Each entry's "Read" items now, and `CLAUDE.md` again if it changed (the app loaded the old one when this
   chat started; reading it now is enough). Then `STATUS.md` under Phase ("Studio: <version>, updated YYYY-MM-DD", replacing an
   older such line), one line in `STATUS_SHORTS.md` under "For the next session" ("Studio updated to <version>: read its entry in
   CHANGELOG.md and the files it names before the next Short"), an entry in `log/SESSIONS.md`; commit by path.
9. **Tell the creator** in two lines: what is new for them, and anything they do. Only when the hooks changed is that a fresh chat
   in this folder (the app loads hooks when a chat starts), started with "Let's continue. You have my OK to download and install
   everything our videos need."

## When something goes wrong
- Before the commit: `git merge --abort` puts everything back as it was.
- After it, if the creator wants the update undone: `git reset --keep before-update-<version>` returns to the state before (their
  own commits stay; the update can be run again later).
- `refusing to merge unrelated histories` (the studio's history was started anew, or this folder has no git history): never force
  it. Bring in the studio's own files path by path (`git checkout studio/HEAD -- <path>`, never a creator file, never a file their
  side changed without step 5's rule), then step 5's clash check, the commit, and steps 6 to 9.
