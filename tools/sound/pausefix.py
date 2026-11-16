"""A3's fix in the shared voice chain (voice_chain.sh, after the hiccup pass, before close_gaps). The cap and close_gaps only shorten
SILENT gaps, and the hiccup pass leaves a breath it can't place by Whisper's word times, so a pause with an inhale in it would stay
0.3-0.5 s. This reads the audio itself: every stretch between speech (from a word's tail falling under -38 dB to the next 3 frames over
-30 dB, 20-ms frames) longer than 0.25 s is muted from where the tail has died (under -45 dB: a mute starts only in quiet; else the
valley before the breath) to 40 ms before the next sound (a soft onset stays), with 15-ms fades; close_gaps then shortens the silence.
A stretch with a frame over -24 dB is speech the frames misread and is left alone. Then pauses.py (A3) measures what is left.

  EDIT tools/sound/pausefix.py <in.wav> <out.wav> [--report r.json]"""
import argparse
import json

import numpy as np
import soundfile as sf


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--report")
    a = ap.parse_args()
    x, sr = sf.read(a.src, dtype="float64", always_2d=False)
    mono = x.mean(1) if x.ndim == 2 else x
    h = int(0.02 * sr)
    n = len(mono) // h
    lv = 20 * np.log10(np.sqrt((mono[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
    g = np.ones(len(mono))
    f = int(0.015 * sr)
    done = []
    j = 0
    while j < n - 3:
        if lv[j] > -38:          # inside speech
            j += 1
            continue
        k = j
        while k + 3 < n and not (lv[k:k + 3] > -30).all():
            k += 1
        if (k - j) * 0.02 > 0.25 and lv[j:k].max() <= -24 and lv[j:k].max() > -60:
            # the mute starts where the word has died (under -45 dB); a tail that runs straight into the breath never gets there, so
            # then at the valley between them (else a mute would start on sound, at -33 to -40 dB, and cut the word's end)
            m0 = j
            while m0 < k - 2 and lv[m0] > -45:
                m0 += 1
            if m0 >= k - 2:
                m0 = j + int(np.argmin(lv[j:max(j + 1, k - 2)]))
            m1 = k - 2   # 40 ms before the next sound: a lip noise 80 ms out would split the silence and leave the pause long
            if m1 - m0 >= 3:
                i0, i1 = m0 * h, m1 * h
                g[i0:i0 + f] = np.minimum(g[i0:i0 + f], np.linspace(1, 0, f))
                g[i0 + f:i1 - f] = 0
                g[i1 - f:i1] = np.minimum(g[i1 - f:i1], np.linspace(0, 1, f))
                done.append((round(j * 0.02, 2), round((k - j) * 0.02, 2), round(float(lv[j:k].max()), 1)))
        j = k + 3
    y = x * (g[:, None] if x.ndim == 2 else g)
    sf.write(a.out, y, sr, subtype="PCM_16")
    if a.report:
        json.dump({"muted": done}, open(a.report, "w"), indent=1)
    print(f"{len(done)} pauses over 0.25 s had sound in them, muted for close_gaps (at, length, loudest):", done[:12])


if __name__ == "__main__":
    main()
