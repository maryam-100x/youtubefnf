"""Loudness by the standard the platforms use (ITU-R BS.1770: K-weighting, 400-ms blocks, absolute and relative gates), at 48 kHz.
The same measure as tools/sound/score.py, which sets every bed under the voice by it."""
from __future__ import annotations

import numpy as np

from .settings import SR


def kweight(x):
    """BS.1770 K-weighting (the shelf, then the RLB high-pass) at 48 kHz."""
    from scipy.signal import lfilter
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    return lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)


def lufs(x):
    """Integrated loudness. x: (n, 2) at 48 kHz."""
    if len(x) < SR // 2:
        return -70.0
    k = kweight(x)
    blk, hop = int(0.4 * SR), int(0.1 * SR)
    ms = np.array([(k[i:i + blk] ** 2).mean(axis=0).sum() for i in range(0, len(k) - blk, hop)])
    lk = -0.691 + 10 * np.log10(ms + 1e-12)
    g = ms[lk > -70]
    if not len(g):
        return -70.0
    rel = -0.691 + 10 * np.log10(g.mean()) - 10
    g = ms[(lk > -70) & (lk > rel)]
    return float(-0.691 + 10 * np.log10(g.mean() + 1e-12))


def rms_db(x):
    return 20 * np.log10(np.sqrt((np.asarray(x, np.float64) ** 2).mean()) + 1e-12) if len(x) else -120.0
