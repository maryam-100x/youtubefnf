"""Cut an ElevenLabs section take back into its beats exactly as dj tts's continuous mode did when it was voiced (dj.tts.continuous_elevenlabs,
the inner loop, with no API call and no cache key: the section's own text, alignment and audio from build/voice/cache), so a line can be
rebuilt from the untouched take sample for sample (raw_rebuild.py). Returns int16 clips at 1.0x with their gaps, as the build had them
before [tts] tempo, levelling and loudness."""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # tools/: the dj package
from dj.core import SR, read_wav  # noqa: E402
from dj.tts import (first_sound, frame_db, gap_between, quiet_floor, sound_end, sound_start,  # noqa: E402
                    tighten_pauses)


def cut_section(parts, meta, wav, tcfg):
    text = " ".join(parts)
    al = meta["alignment"]
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    if "".join(al["characters"]) != text:
        raise ValueError("the section's timestamps don't spell these parts")
    gaps = tcfg.get("gaps") or {"sentence": 0.12, "comma": 0.07, "word": 0.04}
    x = read_wav(wav)
    xdb = frame_db(x)
    floor = quiet_floor(xdb)
    spans, pos = [], 0
    for p in parts:
        spans.append((pos, pos + len(p)))
        pos += len(p) + 1

    def last_word_start(j):
        p = parts[j].rstrip()
        k = max(p.rfind(" "), 0)
        return st[spans[j][0] + (k + 1 if k else 0)]
    inner = [gap_between(xdb, floor, en[spans[j][1] - 1], st[spans[j + 1][0]], last_word_start(j)) for j in range(len(parts) - 1)]
    clips, pos = [], 0
    for j, p in enumerate(parts):
        a, b = pos, pos + len(p)
        pos = b + 1
        prev_end = en[a - 2] if j else 0.0
        nxt_start = st[pos] if j + 1 < len(parts) else len(x) / SR
        if j:
            s = inner[j - 1][1] / SR
        else:
            s0 = sound_start(x, st[a], prev_end, xdb, floor)
            f0 = first_sound(xdb, floor, int(st[a] * SR) // 160 + 2) if False else None  # EDGE_HOP is read below
            from dj.tts import EDGE_HOP
            f0 = first_sound(xdb, floor, int(st[a] * SR) // EDGE_HOP + 2)
            s = (min(s0, f0) if f0 is not None else s0) / SR
        e = (inner[j][0] / SR) if j + 1 < len(parts) else sound_end(x, en[b - 1], nxt_start, xdb, floor) / SR
        keep = []
        for m in re.finditer(r"\.\.\.|…", p):
            c0 = a + m.start() - 1
            while c0 > a and not p[c0 - a].isalnum():
                c0 -= 1
            c1 = a + m.end()
            while c1 < b and not p[c1 - a].isalnum():
                c1 += 1
            if c1 < b:
                p0, p1 = en[c0], st[c1]
                keep.append((int((p0 - s) * SR), int((min(p1, p0 + 0.5) - s) * SR), int((p1 - s) * SR)))
        seg, out, prev = x[int(s * SR): int(e * SR)], [], 0
        for k0, k1, k2 in keep:
            out += [tighten_pauses(seg[prev:k0], tcfg.get("max_pause", 0)), seg[k0:k1]]
            prev = k2
        seg = np.concatenate(out + [tighten_pauses(seg[prev:], tcfg.get("max_pause", 0))])
        fl = min(int(0.005 * SR), len(seg))
        seg = seg.copy()
        seg[:fl] = (seg[:fl] * np.linspace(0, 1, fl)).astype(seg.dtype)
        seg[-fl:] = (seg[-fl:] * np.linspace(1, 0, fl)).astype(seg.dtype)
        last = p.rstrip().rstrip("\"')")[-1:]
        gap = gaps["sentence"] if last in ".?!…" else gaps["comma"] if last in ",;:" else gaps["word"]
        clips.append(np.concatenate([seg, np.zeros(int(gap * SR), np.int16)]))
    return clips
