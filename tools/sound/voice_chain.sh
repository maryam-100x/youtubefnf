#!/usr/bin/env bash
# The shared voice chain (long form): <dj>/build/voice/narration.wav (dj tts's output, the takes spliced) -> the cleaned voice, then
# the sound gate. The order: captions 0, the early word check (A5), the safe breath pass, the raw takes kept as narration_prechain.wav,
# the 0.25-s cap, captions 1, the hiccup pass, the pause fix (breaths inside long pauses muted), every pause inside a sentence cut to
# 0.12 s (inner_gaps.py: only digital silence is cut, after --breaths mutes an inhale left inside the pause that the breath pass's
# spelling guard skipped; the words from captions 1 still fit, as hiccup and pausefix only mute), close_gaps at 0.2 s (heard as
# ~0.25 s), captions 2, sync; then the clean-up after it: fixmutes (scraps after a mute, chopped ends faded), tails --fix (word ends
# the chain cut, laid back from the takes), hisstails --fix, up to 3 rounds of the A3 fix, and the sound gate (A1-A13, gate_sound.py),
# which stops the run (exit 3) while anything is flagged.
#   bash tools/sound/voice_chain.sh <video>          (the folder name under videos/, or its number; its files from video.toml's dj)
# Before the first take: EDIT tools/sound/names.py <video> (A6: every name has a voice spelling in names.json).
# Exits: 2 no narration, 3 the gate has open flags, 4 the voice is locked, 5 script.md changed mid-chain, 6 misread words, 7 captions failed.
set -eu
. "$(dirname "${BASH_SOURCE[0]}")/../common/paths.sh"
VID=${1:?usage: voice_chain.sh <video folder name>}
SND=$REPO/tools/sound
HEAVY=$MEDIA/tmp/heavy                 # the heavy-job tickets (tools/common/paths.py: HEAVY)
read -r VID DJ SRC < <("$EDIT" - "$VID" "$SND" <<'EOF'
import sys
sys.path.insert(0, sys.argv[2])
import gatelib as G
P = G.paths(sys.argv[1])
print(P["video"], str(P["dj"]).replace("\\", "/"), P["cfg"].get("video", {}).get("src", ""))
EOF
)
VID=${VID%$'\r'}; DJ=${DJ%$'\r'}; SRC=${SRC%$'\r'}   # Windows python ends its line with a carriage return: never let it into a path
B=$DJ/build
[ -f "$B/voice/narration.wav" ] || { echo "no $B/voice/narration.wav: run dj tts first"; exit 2; }
# the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by tools/voice/voice_layin.py
"$EDIT" "$REPO/tools/voice/voice_lock.py" "$VID" refuse voice_chain.sh || exit 4
# script.md's hash at the start: a chain whose script changed under it does not land. The narration and beats as they came in are
# kept; a changed script puts them back and stops (exit 5)
SCRIPT=$REPO/videos/$VID/script.md
H0=$(sha256sum "$SCRIPT" | cut -c1-64)
# the chain always starts from the narration as LAID OUT from the takes (narration_laid.wav + beats_laid.json, written by the layout,
# tools/voice/proto_narration.py), never from an earlier run's output or a hand edit, so narration_prechain.wav (A1's reference) never
# holds a cut. A fix after the chain is a chain tool on its output, then gate_sound.py; the gate's A1 and A13 read the layout.
if [ -f "$B/voice/narration_laid.wav" ]; then
  cp "$B/voice/narration_laid.wav" "$B/voice/narration.wav"
  if [ -f "$B/beats_laid.json" ]; then cp "$B/beats_laid.json" "$B/beats.json"; fi
  echo "== from the layout (narration_laid.wav)"
fi
cp "$B/voice/narration.wav" "$B/voice/narration_chainstart.wav"; cp "$B/beats.json" "$B/beats_chainstart.json"
same_script() { if [ "$(sha256sum "$SCRIPT" | cut -c1-64)" != "$H0" ]; then cp "$B/voice/narration_chainstart.wav" "$B/voice/narration.wav"; cp "$B/beats_chainstart.json" "$B/beats.json"; echo "== STOP $(date +%H:%M:%S): script.md changed during the chain ($1): narration.wav and beats.json put back as they came in; voice the changed lines, then run the chain again"; exit 5; fi; }
# every captions pass is followed by linestarts.py: Whisper times some lines' first words late and squashed, and every later step,
# the picture's cues and the gate read those times.
# A failed `dj captions` stops the chain (its exit is read past the pipe), so no later step reads the words of an older run.
cap() { ( "$PIPE" "$REPO/tools/pipeline/heavy.py" take score "$VID captions (voice chain)" $BASHPID; cd "$REPO/tools" && { "$PIPE" -m dj captions "../videos/$VID" 2>&1 | tail -2; rc=${PIPESTATUS[0]}; }; rm -f "$HEAVY/$BASHPID.json"; if [ "$rc" != 0 ]; then echo "== STOP $(date +%H:%M:%S): dj captions failed (exit $rc, above): every later step would read the words of an older run"; exit 7; fi; PYTHONUTF8=1 "$EDIT" "$SND/linestarts.py" "$VID" | tail -1 ) || exit 7; }
echo "== captions 0 $(date +%H:%M:%S)"; cap
# the words, judged where the gate judges them, before the long passes: a misread or swapped word would otherwise pass every take
# check and fail the gate's A5 only at the END of a long chain. The laid narration's own words (captions 0, Whisper in context) against
# the script now: a misread word stops the chain here (a cut word end is the final gate's: the chain moves the times) and names the
# beats to re-take
A5EARLY=$(PYTHONUTF8=1 "$EDIT" "$SND/gate_sound.py" "$VID" --only A5 -v 2>/dev/null | grep -E "\[key words:" || true)
if [ -n "$A5EARLY" ]; then
  echo "$A5EARLY"
  echo "== STOP $(date +%H:%M:%S): the laid voice has misread words (A5, above): re-take those beats' sections (autopick.py), lay out again, then run the chain"
  exit 6
fi
echo "== breath $(date +%H:%M:%S)"; "$EDIT" "$SND/breath.py" "$VID"
cp "$B/voice/narration.wav" "$B/voice/narration_prechain.wav"
cp "$B/voice/narration_nb.wav" "$B/voice/narration.wav"
echo "== cap $(date +%H:%M:%S)"; "$EDIT" "$SND/shorts_tighten.py" "$VID" --cap 0.25 | tail -3
echo "== captions 1 $(date +%H:%M:%S)"; cap; same_script "after captions 1"
echo "== hiccup $(date +%H:%M:%S)"; "$EDIT" "$SND/hiccup_breaths.py" "$B/voice/narration.wav" "$B/captions/words.json" "$B/voice/narration_hic.wav" | tail -3
cp "$B/voice/narration_hic.wav" "$B/voice/narration.wav"
echo "== pausefix $(date +%H:%M:%S)"; "$EDIT" "$SND/pausefix.py" "$B/voice/narration.wav" "$B/voice/narration_pf.wav" | tail -2
cp "$B/voice/narration_pf.wav" "$B/voice/narration.wav"
echo "== inner_gaps $(date +%H:%M:%S)"; "$EDIT" "$SND/inner_gaps.py" "$B/voice/narration.wav" "$B/voice/narration_ig.wav" --words "$B/captions/words.json" --beats "$B/beats.json" --breaths --quiet -50 | grep -E "breath|pause"
cp "$B/voice/narration_ig.wav" "$B/voice/narration.wav"
echo "== close_gaps $(date +%H:%M:%S)"; "$EDIT" "$SND/close_gaps.py" "$B/voice/narration.wav" "$B/voice/narration_cg.wav" --gap 0.2 --beats "$B/beats.json" --shoulders | tail -3
cp "$B/voice/narration_cg.wav" "$B/voice/narration.wav"
echo "== captions 2 $(date +%H:%M:%S)"; cap; same_script "after captions 2"
if [ -n "$SRC" ]; then echo "== sync $(date +%H:%M:%S)"; "$PIPE" "$REPO/tools/motion/sync_words.py" "$VID" "$SRC" | tail -2; fi
echo "== fixmutes $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/fixmutes.py" "$VID"
echo "== tails --fix $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/tails.py" "$VID" --fix | head -3
# a hiss a cut or mute ate is laid back from the layout where there is room (hisstails.py, the gate's A13)
echo "== hiss --fix $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/hisstails.py" "$VID" --fix | tail -2 || true
# the A3 second pass: captions 2's fresh word edges show inside pauses the first pass's words hid (an inhale Whisper had counted as the
# word's own sound); one more inner_gaps --breaths on them, anything under -42 dB (close_gaps' own no-speech level) cuttable inside the
# protected window (40 ms after the word, 30 ms before the onset), then captions, sync and tails again (the re-timed words can show a
# word end the pass's words moved). Each re-caption moves the word edges a little and shows the next pause, so it repeats while A3 still
# finds a long pause inside a sentence, at most 3 rounds
for round in 1 2 3; do
  PYTHONUTF8=1 "$EDIT" "$SND/gate_sound.py" "$VID" --only A3 --json "$DJ/pipeline/gate_sound/gate_a3.json" -v 2>/dev/null | grep -qE "inside a sentence|breath in the pause" || break
  # the A3 fix (a3fix.py): every breath the gate's own A3 measure finds muted quiet to quiet (a mute starts and ends only under -45 dB),
  # the quiet of an over-long inner pause set to silence, so the inner_gaps pass below cuts it to 0.12 s
  echo "== a3fix $((round + 1)) $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/a3fix.py" "$B/voice/narration.wav" "$B/voice/narration_a3.wav" "$B/captions/words.json" | tail -4
  cp "$B/voice/narration_a3.wav" "$B/voice/narration.wav"
  echo "== inner_gaps pass $((round + 1)) $(date +%H:%M:%S)"; "$EDIT" "$SND/inner_gaps.py" "$B/voice/narration.wav" "$B/voice/narration_ig2.wav" --words "$B/captions/words.json" --beats "$B/beats.json" --breaths --quiet -42 | grep -E "breath|pause"
  cp "$B/voice/narration_ig2.wav" "$B/voice/narration.wav"
  echo "== captions $((round + 2)) $(date +%H:%M:%S)"; cap
  if [ -n "$SRC" ]; then echo "== sync $(date +%H:%M:%S)"; "$PIPE" "$REPO/tools/motion/sync_words.py" "$VID" "$SRC" | tail -2; fi
  echo "== tails --fix $((round + 1)) $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/tails.py" "$VID" --fix | head -3
  echo "== hiss --fix $((round + 1)) $(date +%H:%M:%S)"; PYTHONUTF8=1 "$EDIT" "$SND/hisstails.py" "$VID" --fix | tail -2 || true
done
same_script "before the gate"
echo "== sound gate $(date +%H:%M:%S)"
if ! PYTHONUTF8=1 "$EDIT" "$SND/gate_sound.py" "$VID"; then
  echo "== STOP: the sound gate has open flags. Fix each (a re-take, the chain) or prove it wrong by its frames; nothing renders before."
  exit 3
fi
echo "== done $(date +%H:%M:%S)"
