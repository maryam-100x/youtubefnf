#!/usr/bin/env bash
# A built Short's voice chain after `dj tts` (standard/SHORTS.md, the sound gate before anything renders), one Short at a time:
#   captions (Whisper's words) -> the voice guard (accent, tone: a flagged section is voiced again) -> the raw take kept as
#   narration_prechain.wav (A1 compares the final voice against it) -> pausefix -> shorts_tighten (every gap to ~0.07 s) -> captions
#   again -> sync_words (tools/motion/src/<src>/words.json, beats.json) -> the sound gate A1-A13 (tools/sound/gate_sound.py).
#   bash tools/sound/short_chain.sh <slug> <src folder> [--no-guard]
# Exits: 4 the voice is locked, 5 script.md changed mid-chain.
set -u
. "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"
SLUG=${1:?usage: short_chain.sh <slug> <src folder> [--no-guard]}; SRC=${2:?usage: short_chain.sh <slug> <src folder> [--no-guard]}
SND=$REPO/tools/sound
HEAVY=$MEDIA/tmp/heavy                 # the heavy-job tickets (tools/common/paths.py: HEAVY)
read -r SLUG DJ < <("$EDIT" - "$SLUG" "$SND" <<'EOF'
import sys
sys.path.insert(0, sys.argv[2])
import gatelib as G
P = G.paths(sys.argv[1])
print(P["video"], str(P["dj"]).replace("\\", "/"))
EOF
)
SLUG=${SLUG%$'\r'}; DJ=${DJ%$'\r'}   # Windows python ends its line with a carriage return: never let it into a path
V=$DJ/build/voice
# the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by tools/voice/voice_layin.py
"$EDIT" "$REPO/tools/voice/voice_lock.py" "$SLUG" refuse short_chain.sh || exit 4
SCRIPT=$REPO/videos/$SLUG/script.md; H0=$({ sha256sum "$SCRIPT" 2>/dev/null || shasum -a 256 "$SCRIPT"; } | cut -c1-64)   # a script edited mid-chain: the result doesn't land
same_script() { [ "$({ sha256sum "$SCRIPT" 2>/dev/null || shasum -a 256 "$SCRIPT"; } | cut -c1-64)" = "$H0" ] || { echo "== STOP $(date +%H:%M:%S): script.md changed during the chain ($1): voice the changed lines, run it again"; exit 5; }; }
cap() { ( "$PIPE" "$REPO/tools/pipeline/heavy.py" take score "$SLUG captions" ${BASHPID:-$$}; cd "$REPO/tools" && PYTHONUTF8=1 "$PIPE" -m dj captions "../videos/$SLUG" 2>&1 | tail -2; rm -f "$HEAVY/${BASHPID:-$$}.json" ) }
# the raw narration rebuilt from the cached takes first (no credits), so a re-run starts from the takes, not from a tightened voice
echo "== $SLUG tts (cached) $(date +%H:%M:%S)"; (cd "$REPO/tools" && PYTHONUTF8=1 "$PIPE" -m dj tts "../videos/$SLUG" 2>&1 | tail -1)
echo "== $SLUG captions 1 $(date +%H:%M:%S)"; cap
if [ "${3:-}" != "--no-guard" ]; then
  # a flagged section is voiced again whole and the best take kept (--retake rebuilds the narration, captions and words)
  echo "== guard $(date +%H:%M:%S)"; (cd "$REPO/tools" && PYTHONUTF8=1 "$PIPE" voice/voice_guard.py "../videos/$SLUG" --retake --cap 3000 --max-takes 3 2>&1 | tail -14)
fi
cp "$V/narration.wav" "$V/narration_prechain.wav"
# breaths inside pauses muted first (A3/A4: a breath after a word ending in a hiss is one the tighten can't cut through)
echo "== pausefix $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/pausefix.py" "$V/narration.wav" "$V/narration_pf.wav" 2>&1 | tail -1 && cp "$V/narration_pf.wav" "$V/narration.wav"
echo "== tighten $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/shorts_tighten.py" "$SLUG" 2>&1 | tail -3
echo "== captions 2 $(date +%H:%M:%S)"; cap
echo "== sync $(date +%H:%M:%S)"; PYTHONUTF8=1 "$PIPE" "$REPO/tools/motion/sync_words.py" "$SLUG" "$SRC" 2>&1 | tail -2
same_script "before the gate"
echo "== sound gate $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/gate_sound.py" "$SLUG" 2>&1 | tail -10
echo "== done $SLUG $(date +%H:%M:%S)"
