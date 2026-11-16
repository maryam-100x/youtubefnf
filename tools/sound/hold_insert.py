"""Room for a clip that speaks for itself (a hold): silence put in a finished narration right after one beat's voice, the beat made
that much longer, every later beat moved (beats.json, as voice_edit.py does). The clip then starts right on the beat's last word, with
no fragment of the next line before it. Then `cd tools && PIPE -m dj captions ../videos/<video>` and `PIPE tools/motion/sync_words.py`.

  EDIT tools/sound/hold_insert.py <build dir> S12 3.0      (the build dir: MEDIA/videos/<video>/build)"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

spec = importlib.util.spec_from_file_location("voice_edit", Path(__file__).resolve().parents[1] / "voice" / "voice_edit.py")
VE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(VE)


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    build, beat, secs = Path(sys.argv[1]), sys.argv[2], float(sys.argv[3])
    nar = build / "voice" / "narration.wav"
    x, sr = sf.read(nar, dtype="float64")
    fpf = sr // VE.FPS
    B = json.loads((build / "beats.json").read_text(encoding="utf-8"))
    ids = [b["id"] for b in B["beats"]]
    i = ids.index(beat)
    b = B["beats"][i]
    n = int(round(secs * VE.FPS))
    at = int(b["voice_end"] * sr) + int(0.12 * sr)          # just after the beat's last word (its own short tail stays before the hold)
    pad = np.zeros((n * fpf,) + x.shape[1:])
    y = np.concatenate([x[:at], pad, x[at:]])
    b["frames"] += n
    VE.shift_beats(B, i + 1, n)
    VE.retime(B)
    B["duration"] = round(B["total_frames"] / VE.FPS, 3)
    sf.write(nar, y, sr, subtype="PCM_16")
    (build / "beats.json").write_text(json.dumps(B, indent=1), encoding="utf-8")
    print(f"hold after {beat}: {n} frames ({n / VE.FPS:.2f} s) of silence at {at / sr:.3f} s; narration {len(y) / sr:.3f} s")


if __name__ == "__main__":
    main()
