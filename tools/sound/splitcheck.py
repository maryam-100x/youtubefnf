"""A take split through a word: span_takes cuts a span's take back into its lines, and a cut inside the next line's first consonant
leaves its quiet start ("wh", "f") at the end of the line before, where the chain treats it as silence, while the line after starts on
its vowel (the listener hears the word's first sound swallowed).

For every pair of consecutive beats in build/voice/patch/used.json (or the beat files of the narration): the last 80 ms of the line before
rising into noise or voice (its last 20 ms over -50 dB and louder than the 60 ms before them) and/or the next line's first 10 ms already
over -38 dB (an onset with no lead-in) = a split through a word. --fix moves the line before's rising tail (from its last frame under -66
dB) to the head of the line after, both files kept as *_presplit.wav.

  EDIT tools/sound/splitcheck.py <video> [--fix]"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402


def lv(y, sr, hop=0.005):
    h = int(hop * sr)
    n = len(y) // h
    return 20 * np.log10(np.sqrt((y[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, when="--fix")  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--fix", action="store_true")
    a = ap.parse_args()
    P = G.paths(a.video)
    vb = Path(P["final"]).parent
    beats = json.loads(Path(P["beats"]).read_text(encoding="utf-8"))["beats"]
    used = {}
    up = vb / "patch" / "used.json"
    if up.exists():
        used = json.loads(up.read_text(encoding="utf-8"))
    files = []
    for b in beats:
        f = vb / "patch" / f"{used[b['id']]}.wav" if b["id"] in used else Path(b.get("wav") or vb / f"{b['id']}.wav")
        files.append((b["id"], f))
    bad = 0
    for (b1, f1), (b2, f2) in zip(files, files[1:]):
        if not (f1.exists() and f2.exists()):
            continue
        x1, sr = sf.read(f1, always_2d=True)
        x2, _ = sf.read(f2, always_2d=True)
        l1, l2 = lv(x1.mean(1), sr), lv(x2.mean(1), sr)
        tail_rise = len(l1) > 16 and l1[-4:].max() > -50 and l1[-4:].mean() > l1[-16:-4].mean() + 6
        head_hot = len(l2) > 2 and l2[:2].max() > -38
        # a whole word head after the line's own silence (a line ending on 170 ms of the next line's first word at -14 dB after 0.2 s
        # under -70, the next line beginning in the middle of that word): the head runs longer than tail_rise's 20 ms, so it isn't
        # rising at the end; the next line starts inside the word
        k = len(l1) - 1
        while k > 0 and l1[k] > -60:
            k -= 1
        tail_word = (len(l1) > 40 and 12 <= len(l1) - 1 - k <= 60 and l1[k + 1:].max() > -35
                     and l1[max(0, k - 23):k + 1].max() < -55 and l2[:4].max() > -45)
        tail_rise = tail_rise or tail_word
        if tail_rise or head_hot:
            bad += 1
            print(f"SPLIT {b1}|{b2}: {f1.name} ends {'on a word head after its silence' if tail_word else 'rising to ' + format(l1[-4:].max(), '.0f') + ' dB' if tail_rise else 'quiet'}; "
                  f"{f2.name} starts at {l2[:2].max():.0f} dB{' (no lead-in)' if head_hot else ''}")
            if a.fix and tail_rise:
                k = len(l1) - 1
                while k > 0 and l1[k] > -66:
                    k -= 1
                cut = (k + 1) * int(0.005 * sr)
                for f in (f1, f2):
                    bk = f.with_name(f.stem + "_presplit.wav")
                    if not bk.exists():
                        shutil.copy(f, bk)
                sf.write(f1, x1[:cut], sr, subtype=sf.info(str(f1)).subtype)
                sf.write(f2, np.concatenate([x1[cut:], x2]), sr, subtype=sf.info(str(f2)).subtype)
                print(f"   moved {(len(x1) - cut) / sr * 1000:.0f} ms from {f1.name}'s tail to {f2.name}'s head")
    print(f"{bad} split(s) through a word ({len(files) - 1} boundaries read)")
    sys.exit(1 if bad and not a.fix else 0)


if __name__ == "__main__":
    main()
