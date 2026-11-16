"""Fix two kinds of sound-gate flag in place, from the gate's own report (a join of takes can leave word-head scraps, A7, and the
breath pass can leave inhales in short pauses, A3 BREATH; every inhale between words goes):
  A7 scrap   the island is muted: from the last 10-ms frame under -45 dB before it to the first under -45 dB after it (a mute
             starts and ends in quiet), 5-ms fades;
  A3 breath  the same, over the breath's own frames (its t and ms in the report).
A7 runs only when asked (--only A7,A3) and only after each island was checked by its frames and Whisper medium: an A7 flag can be a
real short word with a gap after it, and muting it loses the word.
Nothing else is touched and no time moves; run close_gaps.py after it (the pause around a muted scrap or breath is then dead air), then
dj captions and sync_words. Writes <final>_prefixflags.wav as a backup. Every mute is printed with its edges' levels.

  EDIT tools/sound/fixflags.py <video> [--report gate_sound.json] [--only A3|A7,A3] [--keys k1,k2]"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

HOP = 0.01
QUIET = -45.0


def flags_of(report, cid):
    c = report["checks"][cid] if isinstance(report["checks"], dict) else next(x for x in report["checks"] if x.get("check") == cid)
    return c.get("flags", c.get("open", []))


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--report", help="the gate's json (default <dj>/pipeline/gate_sound/gate_sound.json)")
    ap.add_argument("--only", default="A3")
    ap.add_argument("--exact", action="store_true", help="where no quiet edge is near, mute exactly the flagged span (a breath touching a word; check A2 after)")
    ap.add_argument("--keys", help="comma list of flag keys: fix only these (each checked by its frames first)")
    ap.add_argument("--reach-ms", type=int, default=60, help="how far a mute may grow out of the flagged span to a quiet edge (default 60 ms: "
                    "a word's own sound stays); an inhale longer than the gate measured over -45 dB (280 ms of breath flagged as 130) "
                    "needs more, given per key with --keys after its frames were read")
    ap.add_argument("--span", nargs=3, action="append", metavar=("T0", "T1", "WHY"), help="mute exactly T0-T1 (5-ms fades), a sound the "
                    "gate names without a mute of its own (an A9 at a bite's split can be a 20-ms scrap of an inhale, -42 dB, centred "
                    "1.5-1.9 kHz, the chain had muted around); read its frames first and say why")
    a = ap.parse_args()
    P = G.paths(a.video)
    final = Path(P["final"])
    if a.span:      # exact spans, read and written as windows only (the narration's other samples aren't loaded or touched)
        shutil.copy(final, final.with_name(final.stem + "_prefixflags.wav"))
        with sf.SoundFile(str(final), "r+") as fh:
            sr, fade = fh.samplerate, int(0.005 * fh.samplerate)
            for t0, t1, why in a.span:
                s0, s1 = int(float(t0) * sr), int(float(t1) * sr)
                fh.seek(s0 - fade)
                y = fh.read(s1 - s0 + 2 * fade, dtype="float64", always_2d=True)
                gg = np.ones(len(y))
                gg[:fade] = np.linspace(1, 0, fade)
                gg[fade:fade + (s1 - s0)] = 0
                gg[fade + (s1 - s0):] = np.linspace(0, 1, len(y) - fade - (s1 - s0))
                edge = lambda q: 20 * np.log10(np.sqrt(np.mean(q ** 2)) + 1e-12)
                print(f"  muted {float(t0):.3f}-{float(t1):.3f} s ({why}); edges {edge(y[:fade]):.0f} / {edge(y[-fade:]):.0f} dB")
                fh.seek(s0 - fade)
                fh.write(y * gg[:, None])
        print(f"{len(a.span)} span(s) muted in {final} (backup {final.stem}_prefixflags.wav); time kept")
        return
    rep = json.loads(Path(a.report or P["out"] / "gate_sound.json").read_text(encoding="utf-8"))
    x, sr = sf.read(final, always_2d=True)
    m = x.mean(1)
    h = int(sr * HOP)
    n = len(m) // h
    db = 20 * np.log10(np.sqrt((m[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12)
    spans = []
    want = set(a.only.split(","))
    if "A7" in want:
        for f in flags_of(rep, "A7"):
            spans.append(("A7", f["t"], f["t"] + f.get("ms", 100) / 1000, f["word"], f["key"]))
    if "A2" in want:
        # A2's "scrap after a mute": an island of a longer sound (a breath) left between two mutes (e.g. 55 ms at -26 dB, digital
        # silence on both sides); muted the same way, between quiet edges. A2's clicks are not touched.
        for f in flags_of(rep, "A2"):
            m_ = re.match(r"scrap after a mute: (\d+) ms", f.get("msg", ""))
            if m_:
                spans.append(("A2", f["t"], f["t"] + int(m_[1]) / 1000, f["word"], f["key"]))
            else:
                print(f"  A2 {f['key']}: not a scrap after a mute: left as it is")
    if "A3" in want:
        for f in flags_of(rep, "A3"):
            # any A3 flag that measures a sound in a pause (the gate's "breath:" keys, or a hand-read one such as "hiss:"); a flag it
            # can't fix is said, never dropped without a word
            if "breath in the pause after it: " in f.get("msg", ""):
                ms = int(f["msg"].split("breath in the pause after it: ")[1].split(" ms")[0])
                spans.append(("A3", f["t"], f["t"] + ms / 1000, f["word"], f["key"]))
            else:
                print(f"  A3 {f['key']}: not a sound in a pause (a long pause is close_gaps' or inner_gaps'): left as it is")
    if a.keys:
        keys = set(a.keys.split(","))
        spans = [sp for sp in spans if sp[4] in keys]
    if not spans:
        print("nothing to fix")
        return
    shutil.copy(final, final.with_name(final.stem + "_prefixflags.wav"))
    g = np.ones(len(m))
    fade = int(0.005 * sr)
    for cid, t0, t1, word, _k in sorted(spans, key=lambda s: s[1]):
        i, j = int(t0 / HOP), int(np.ceil(t1 / HOP))
        i0, j0 = i, j
        while i > 0 and db[i - 1] >= QUIET and i0 - i < a.reach_ms // 10:   # out to quiet, never more than 60 ms (a word's own sound stays)
            i -= 1
        while j < n and db[j] >= QUIET and j - j0 < a.reach_ms // 10:
            j += 1
        if db[max(0, i - 1)] >= QUIET or db[min(n - 1, j)] >= QUIET:
            if not a.exact:
                print(f"  {cid} {G.fmt_t(t0)} {word!r}: SKIPPED, no quiet edge within {a.reach_ms} ms (a word runs into it): fix by hand")
                continue
            i, j = i0, j0          # --exact: only the flagged frames, 5-ms fades
        s0, s1 = i * h, j * h
        g[s0:s1] = 0
        g[max(0, s0 - fade):s0] = np.minimum(g[max(0, s0 - fade):s0], np.linspace(1, 0, s0 - max(0, s0 - fade)))
        g[s1:s1 + fade] = np.minimum(g[s1:s1 + fade], np.linspace(0, 1, len(g[s1:s1 + fade])))
        print(f"  {cid} {G.fmt_t(i * HOP)} {word!r}: muted {i * HOP:.2f}-{j * HOP:.2f} s (edges {db[max(0, i - 1)]:.0f} / "
              f"{db[min(n - 1, j)]:.0f} dB)")
    sf.write(final, x * g[:, None], sr, subtype=sf.info(str(final)).subtype)
    print(f"{len(spans)} muted in {final} (backup {final.stem}_prefixflags.wav); next: close_gaps.py, dj captions, sync_words")


if __name__ == "__main__":
    main()
