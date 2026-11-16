"""qa_word_holes.py: speech in the narration that no word in words.json covers. When the aligner squeezes a long phrase ("a hundred
and thirty-seven thousand") into 0.5 s, 1.5 s of live speech is left with no word: the music's duck follows the words and lets go, so the
music swells for a second or two, and the picture's anchors on those words land late. Fails on any run of 0.4 s+ where the narration
is over -32 dBFS (50-ms RMS) and no word (padded 80/150 ms) covers it. Run after every voice landing: a hole means the alignment of
that beat is wrong (re-sync it).

  PIPE tools/sound/qa_word_holes.py <narration.wav> <words.json>
"""
import contextlib
import json
import sys
import wave

import numpy as np

HOP, DB, MIN = 0.05, -32.0, 0.4


def main(wav, words):
    W = json.load(open(words, encoding='utf-8'))
    rms = []
    with contextlib.closing(wave.open(wav)) as f:
        sr, ch, sw = f.getframerate(), f.getnchannels(), f.getsampwidth()
        hop = int(HOP * sr)
        while True:
            b = f.readframes(hop * 200)
            if not b:
                break
            a = np.frombuffer(b, dtype={2: np.int16, 4: np.int32}[sw]).astype(np.float32).reshape(-1, ch).mean(1)
            a /= 32768 if sw == 2 else 2 ** 31
            m = len(a) // hop
            rms += list(20 * np.log10(np.sqrt((a[:m * hop].reshape(m, hop) ** 2).mean(1)) + 1e-9))
    rms = np.array(rms)
    cov = np.zeros(len(rms), bool)
    for x in W:
        cov[max(0, int((x['start'] - 0.08) / HOP)):int((x['end'] + 0.15) / HOP) + 1] = True
    sp = (rms > DB) & ~cov
    runs, i = [], 0
    while i < len(sp):
        if sp[i]:
            j = i
            while j < len(sp) and sp[j]:
                j += 1
            if (j - i) * HOP >= MIN:
                t = i * HOP
                beat = next((x['beat'] for x in reversed(W) if x['start'] <= t), '?')
                runs.append(f'{t:8.2f} s  {(j - i) * HOP:.2f} s of speech with no word  ({beat})')
            i = j
        else:
            i += 1
    print(f'qa_word_holes: {len(runs)} holes')
    for r in runs:
        print('  ' + r)
    sys.exit(1 if runs else 0)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
