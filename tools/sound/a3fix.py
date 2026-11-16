"""The A3 fix, in the voice chain (tools/sound/voice_chain.sh) because the chain's breath passes skip some inhales (after s/t endings,
inside a spelling guard): mute every breath the sound gate's own A3 measure finds in a pause (pauses.Voice.measure), from the last
frame under -45 dB before it (a mute starts only once the word before has died under -45 dB) to the first frame under -45 dB
after it (the whole inhale, no tail left to click), never into the next word's onset (the measure's i1), with 5-ms
fades; and in the inside-a-sentence pauses over the bar with no breath, the frames already under -50 dB set to digital silence, so
inner_gaps.py can cut them to 0.12 s. Prints every change.
  EDIT tools/sound/a3fix.py <in.wav> <out.wav> <words.json>"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
import pauses as PZ  # noqa: E402

src, out, words = sys.argv[1:4]
V = PZ.Voice(src)
x, sr = sf.read(src, always_2d=True)
W = G.load_words(words)
F = PZ.FINE
lf = V.lf
fade = int(0.005 * sr)


def mute(i, e, why):
    a, b = int(i * F * sr), int(e * F * sr)
    if b - a <= 2 * fade:
        return
    ramp = np.linspace(1, 0, fade)[:, None]
    x[a:a + fade] *= ramp
    x[a + fade:b - fade] = 0
    x[b - fade:b] *= ramp[::-1]
    print(f"  muted {a / sr:.3f}-{b / sr:.3f} s ({(b - a) / sr * 1000:.0f} ms): {why}")


for k in range(len(W) - 1):
    a, b = W[k], W[k + 1]
    m = V.measure(a, b)
    if not m:
        continue
    i0, i1 = m["i0"], m["i1"]
    for r in m["breaths"]:
        s = int(round(r["t"] / F))
        e = s + int(round(r["ms"] / 1000 / F))
        while s > i0 and lf[s - 1] >= -45:
            s -= 1
        while e < i1 and lf[e] >= -45:
            e += 1
        if lf[s] >= -45 and s > 0 and lf[s - 1] >= -45:
            print(f"  SKIPPED a breath after {a['w']!r} at {r['t']:.2f} s: no quiet frame before it (a mute starts only in quiet)")
            continue
        # a short "breath" that starts where the word's own sound ends is the word's tail, not an inhale (muting it costs the word its
        # release, and the gate's A1 finds it lost against the take)
        # judged on the whole run over -45 dB, not the part A3 saw inside its pause window (a 160-ms inhale 50 ms after a t's burst can
        # read as 80 ms inside the window and be kept as the t's tail)
        # the breath's whole run: on past the measure's window (i1 walks back over a flat inhale as if it were the next word's rising
        # onset) through every frame that is breath-like (over -45 dB, under -25, centred 1.5-3.5 kHz), never into the next word's sound
        ef = min(e, i1)
        while ef < len(lf) and -45 <= lf[ef] < -25 and PZ.BREATH_HZ <= V.cen[ef] <= 3500:
            ef += 1
        if s - i0 <= 3 and r["ms"] <= 80 and (max(e, ef) - s) * F <= 0.08:
            print(f"  KEPT {r['ms']} ms after {a['w']!r} at {r['t']:.2f} s: it starts on the word's end (its own tail; A1 would call it lost)")
            continue
        mute(s, max(min(e, i1), ef), f"breath after {a['w']!r} ({r['ms']} ms, {r['loud']} dB, {r['hz']} Hz)")
    inside = not a["w"].rstrip('"\'”)').endswith((".", "?", "!")) and a.get("beat") == b.get("beat")
    if inside and m["length"] > 0.20 and not m["breaths"]:
        run = [j for j in range(i0, i1) if lf[j] < -50]
        if run:
            mute(run[0], run[-1] + 1, f"quiet inside the {m['length']:.2f}-s pause after {a['w']!r}, set to digital silence for inner_gaps")
sf.write(out, x, sr, subtype="PCM_24" if sf.info(src).subtype == "PCM_24" else sf.info(src).subtype)
print("->", out)
