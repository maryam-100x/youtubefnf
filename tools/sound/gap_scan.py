"""The line-gap scan and cut, before every render: every gap between two lines of 0.75 s+ with a breath after the word's fade, cut
the voice_edit.py way, latest first; each cut proved on the audio before it (edges <= -47 dB, the loudest thing removed a breath under
-25 dB, the next word after the cut). Prints the cuts (start, frames) for the picture and the words.

  EDIT tools/sound/gap_scan.py <video> <motion src folder> [--dry] [--inside] [--min 0.75]

--dry lists what it would cut. The scan starts 0.15 s inside each line's last word (Whisper can run a word past the dip after it, so a
scan from the word's end would begin inside the breath and miss it). A new take laid in by voice_edit.py span gets this scan before
the version goes out. After the cuts: captions_shift.py per cut, PIPE tools/motion/sync_words.py, the frames dropped before each next
shot, a before/after video for the creator."""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np, soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MOTION, PY_EDIT, TOOLS, VIDEOS  # noqa: E402
SLUG, SRC = sys.argv[1], sys.argv[2]
__import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
__import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
B = (VIDEOS / SLUG / 'build').as_posix()
PY = str(PY_EDIT)
VOICE_EDIT = str(TOOLS / 'voice' / 'voice_edit.py')
W = json.load(open(MOTION / 'src' / SRC / 'words.json', encoding='utf-8'))
dry = '--dry' in sys.argv
# breaths also sit in pauses INSIDE lines (a line holds several sentences) and in gaps under 0.75 s: --inside scans those too; --min
# sets the smallest gap looked at (default 0.75)
inside = '--inside' in sys.argv
MIN = float(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 0.75


def lv(x, sr, t0, t1, h=0.01):
    s = x[int(t0 * sr):int(t1 * sr)]
    k = int(h * sr); n = len(s) // k
    return 20 * np.log10(np.sqrt((s[:n * k].reshape(n, k) ** 2).mean(1)) + 1e-12)


def gap_dip(r, t0, b_start):
    """The dip that opens the gap: the first frame under -55 dB with no speech-loud frame (> -30 dB) after it before the next word
    (a first dip can sit inside a word, at the stop before its t, so the scan would read the word's rest as the next word and miss the
    breath and pause after it)."""
    bs = max(1, int((b_start - 0.05 - t0) / 0.01))
    return next((int(i) for i in np.where(r < -55)[0] if i < bs and (r[i:bs] <= -30).all()), None)


x, sr = sf.read(f'{B}/voice/narration.wav', dtype='float64')
gaps = []
for a, b in zip(W, W[1:]):
    if (a['beat'] == b['beat'] and not inside) or b['start'] - a['end'] < MIN:
        continue
    r = lv(x, sr, a['end'] - 0.15, b['start'] + 0.1)
    d = gap_dip(r, a['end'] - 0.15, b['start'])
    if d is None:
        continue
    later = r[d:]
    if (later > -50).sum() * 0.01 < 0.1:
        continue
    gaps.append((a, b))
shifts = []
for a, b in sorted(gaps, key=lambda g: -g[0]['end']):
    x, sr = sf.read(f'{B}/voice/narration.wav', dtype='float64')
    t0 = a['end'] - 0.15
    r = lv(x, sr, t0, b['start'] + 0.3)
    d0 = gap_dip(r, t0, b['start'])
    # the next word's onset: the first frame after the dip that is speech-loud (> -30 dB) and stays for 30 ms
    on = next((i for i in range(d0, len(r) - 3) if (r[i:i + 3] > -30).all()), None)
    if on is None:
        print(f'skip {a["w"]}->{b["w"]}: no onset found'); continue
    # the breath: frames above -50 between the dip and 30 ms before the onset
    br = [i for i in range(d0, on - 3) if r[i] > -50]
    if not br:
        print(f'skip {a["w"]}->{b["w"]}: no breath'); continue
    b_end = br[-1] + 1
    dead = [i for i in range(b_end, on - 3) if r[i] < -90]
    c1a, c1b = t0 + d0 * 0.01, t0 + (d0 + 5) * 0.01
    beat = a['beat']
    args = [PY, VOICE_EDIT, 'cut', B, beat, '--a', f'{c1a:.3f},{c1b:.3f}', '--pause', '0.35']
    if len(dead) >= 8:     # dead air after the breath: the cut ends inside it
        args += ['--b', f'{t0 + (b_end + 2) * 0.01:.3f},{t0 + (on - 4) * 0.01:.3f}']
    else:                  # the breath runs into the word: end right after it, silence back
        c2 = t0 + (b_end + 2) * 0.01
        if c2 > t0 + (on - 3) * 0.01:
            print(f'skip {a["w"]}->{b["w"]}: no room before the word'); continue
        args += ['--b', '0,0', '--c2', f'{c2:.3f}']
    if dry:
        print('would run', ' '.join(args[3:])); continue
    beats_before = open(f'{B}/beats.json', encoding='utf-8').read()
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode:
        print(f'skip {a["w"]}->{b["w"]}: {out.stderr.strip() or out.stdout.strip()}'); continue
    line = out.stdout.splitlines()[0]
    # proof on the audio before this cut
    m = re.search(r'cut \S+: ([\d.]+)-([\d.]+) out(?:, ([\d.]+) s of silence back)? \((\d+) frames', line)
    c1, c2, pad, n = float(m.group(1)), float(m.group(2)), float(m.group(3) or 0), int(m.group(4))
    try:
        e1 = lv(x, sr, c1 - 0.02, c1, 0.02)[0]; e2 = lv(x, sr, c2, c2 + 0.02, 0.02)[0]; pk = lv(x, sr, c1, c2).max()
    except (IndexError, ValueError):   # a cut too short to measure: not proved, so not kept
        e1 = e2 = pk = 0.0
    nxt = t0 + on * 0.01 - c2
    ok = e1 <= -47 and e2 <= -47 and pk <= -25 and nxt > 0
    print(f'{"OK " if ok else "BAD"} {beat} "{a["w"]}"->"{b["w"]}" at {t0:.2f}: {c1:.3f}-{c2:.3f} out, {pad:.2f} s back, {n} frames; '
          f'edges {e1:.0f}/{e2:.0f} dB, removed peak {pk:.0f} dB, next word {nxt:+.2f} s after')
    if not ok:   # put both back (audio and beats) and go on with the next gap (one bad edge never stops the whole run)
        sf.write(f'{B}/voice/narration.wav', x, sr, subtype='PCM_16')
        open(f'{B}/beats.json', 'w', encoding='utf-8').write(beats_before)
        print('   reverted, audio and beats; skipped'); continue
    shifts.append((c1, n))
json.dump(shifts, open(f'{B}/gap_scan_shifts.json', 'w'))
print('shifts', shifts)
