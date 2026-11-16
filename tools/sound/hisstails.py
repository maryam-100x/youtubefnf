"""A13 of the sound gate: no word's tail lost at a cut. Every place the finished voice goes quiet after a word is held against the
narration as LAID OUT from the takes (build/voice/narration_laid.wav: the picked takes at the house tempo through chain D, before any
clean-up; else narration_prechain.wav): where the laid-out voice still sounds and the final doesn't, a cut, a mute or a fade ate the
word's end.

What A1 (tails.py) can miss and this catches: a hiss cut in half at a pause edge read off Whisper's word end (which ends before the
hiss), then faded further by a declick; a reference that already holds the cut (A1 reads narration_prechain.wav, which a second chain
run rewrites from its own input); a loss longer than A1's 15-60 ms release pass; and a word whose spelling doesn't end in a hiss though
its sound does ("6," said "six"). This check reads only the sound: the spelling, the word boxes and the word's length don't enter.

  For every speech run of the final (the runs tails.Align lines up with the reference, NCC >= 0.85 each), from the run's last frame:
    the final's sound end   = the first 5-ms frame under -45 dB broadband AND under -50 dB in 4-12 kHz (the mute bar, and the hiss's own)
    the reference's tail     = the frames from that point on, lined up and levelled by the run's offset and gain, while the reference
                               stays over either bar without a break (a breath after the word comes after a dip: never counted)
    lost                     = those frames plus any frame in the 60 ms before the end where the final sits 6+ dB under the
                               reference (a fade over the tail), while the reference is over either bar
  VOICED tails too (a pause mute can take the creak at a word's end, 80-180 ms under 1.2 kHz, to digital silence): the reference's
  frames over -45 dB (the mute bar) centred under 1.2 kHz, within 250 ms of the run's end, where the final is silenced (under
  -90 dB: a mute or a cut writes digital zero; a fade or a level change doesn't count); 30 ms or more is a "voiced:" flag
  (hisstails.py --fix lays it back).
  A flag: 15 ms or more lost with its loudest frame at -40 dB or louder (broadband or the 4-12 kHz band). The fix is in the step that
  cut (the chain starts from the layout again; a pause fix goes through a tool whose edge is measured, never by hand) or a re-take;
  tails.py --fix can lay a lost tail back from the reference when there is room.

  EDIT tools/sound/hisstails.py <video> [--final F --raw R --words W] [-v] [--fix]
--fix lays a lost hiss back from the layout where the final has room (voice_chain.sh runs it after tails.py --fix); one with no room
(the next word moved up by a cut pause) stays a flag: re-time or re-take."""
import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfiltfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

H5 = 0.005
BB_BAR, HF_BAR = -45.0, -50.0     # dB: a frame over either still sounds (the mute bar, -45 broadband; the hiss band's own)
LOUD = -40.0                      # dB: a lost stretch matters when its loudest frame reaches this (either measure)
MIN_LOST = 3                      # frames of 5 ms
FADE_LOOK = 12                    # frames before the end a fade is looked for (60 ms)
REACH = 50                        # frames after the end the tail may run (250 ms)
START_REACH = 24                  # frames after a run's end the hiss may start (a stop's closure before a final s: 120 ms)
HISS_DB = 5.0                     # dB: a frame is hiss when its 4-12 kHz band is within this of its whole level


V_BAR = -45.0                     # dB: a voiced tail frame of the reference sounds over this (the mute bar)
V_HZ = 1200.0                     # Hz: voiced = centred under this (a creak, a nasal; a breath sits at 1.5-3.5 kHz, a hiss over 4)
V_SILENT = -90.0                  # dB: the final there is silenced (a mute writes digital zero; a fade or a level change doesn't)
V_REACH = 50                      # frames of 5 ms past the run's end the tail is looked for (250 ms: a creak can run 80-180 ms after a short word)
V_MIN = 6                         # frames of 5 ms: 30 ms of the voice lost


def centroids(x, s0, n, h):
    """the spectral centre (Hz) of n 5-ms frames of x from sample s0"""
    out = np.zeros(n)
    win = np.hanning(h)
    f = np.fft.rfftfreq(h, 1.0 / (h / H5))
    for i in range(n):
        s = x[s0 + i * h:s0 + (i + 1) * h]
        if len(s) < h:
            break
        P = np.abs(np.fft.rfft(s * win)) ** 2
        out[i] = float((f * P).sum() / (P.sum() + 1e-20))
    return out


def band(x, sr):
    sos = butter(6, [4000, min(12000, 0.45 * sr)], btype="bandpass", fs=sr, output="sos")
    return sosfiltfilt(sos, x)


def lv(x, sr):
    return G.frame_db(x, sr, H5)


def reference(P):
    laid = Path(P["final"]).with_name("narration_laid.wav")
    return laid if laid.exists() else Path(P["raw"])


def run(P, quiet=False, al=None, ref=None, fix=False):
    """-> {"check", "final", "raw", "flags", ["fixed", "no_room"]}; fix=True lays every lost hiss back from the reference where the
    final has room (nothing else sounds there: the final under the reference or under -45 dB), levelled by the run's gain, 5-ms
    crossfade in, 15-ms fade out (tails.py --fix's way: the chain's own cut undone, the take's sound as it was, never a processed repair)"""
    import tails
    ref = Path(ref) if ref else reference(P)
    if not ref.exists():
        raise FileNotFoundError(f"no laid-out narration to compare with: {ref}")
    if al is None or Path(getattr(al, "_ref", "")).resolve() != ref.resolve():
        al = tails.Align(P["final"], ref, P["words"])
        al._ref = str(ref)
    sr, fm, pm = al.sr, al.fm, al.pm
    h = int(H5 * sr)
    pad = int(0.03 * sr)
    W = al.W
    flags, fixes, no_room = [], [], []
    anchors = [a for a in al.anchors if a[2] is not None]
    starts_ref = sorted(a[0] + a[2] for a in anchors)

    def levels(x, s0, s1):
        """5-ms broadband and 4-12 kHz levels of x[s0:s1] (the band filtered over a padded window: a whole narration filtered at once
        would hold GBs)"""
        a0, a1 = max(0, s0 - pad), min(len(x), s1 + pad)
        seg = x[a0:a1]
        bnd = band(seg, sr)[s0 - a0:s0 - a0 + (s1 - s0)] if len(seg) > 64 else np.zeros(max(0, s1 - s0))
        return lv(x[s0:s1], sr), lv(bnd, sr)

    for a, b, off, sc, g in anchors:
        # a window on the final from just before this run's end, and the same samples in the reference (exactly aligned frames)
        w0 = max(0, b - (FADE_LOOK + 4) * h)
        w1 = min(len(fm), b + (REACH + 20) * h)
        if w0 + off < 0 or w1 + off > len(pm) or w1 - w0 < 8 * h:
            continue
        fb, fh = levels(fm, w0, w1)
        pb, ph = levels(pm, w0 + off, w1 + off)
        n = min(len(fb), len(pb), len(fh), len(ph))
        i_end = (b - w0) // h                       # the run's last frame (the run: 10-ms frames over -35 dB)
        # the reference's next speech run (in this window's frames): nothing of the next word counts
        nxt = next((s for s in starts_ref if s > (b + off) + h), None)
        lim = min(n, i_end + REACH, ((nxt - (w0 + off)) // h) if nxt is not None else n)
        # the word's hiss in the reference: frames whose energy is mostly over 4 kHz (the 4-12 kHz band within HISS_DB of the whole:
        # a fricative's noise, never a breath, whose spectrum sits lower: an inhale at -28 dB broadband is -34 in the band), over the
        # band's bar; from just before the run's end until the first frame that isn't one, starting within the closure of a stop
        # (up to 120 ms: "six" is s-i-k-s, its last s after the k's silence)
        def hiss(q):
            return ph[q] + g > HF_BAR and ph[q] >= pb[q] - HISS_DB
        # every hiss stretch that starts in that reach (the word's own s before the run's end can be one: "six" starts with an s too),
        # each judged: lost = its frames where the final's band sits 6+ dB under the reference's (cut to silence, muted or faded)
        lost, q = [], max(0, i_end - FADE_LOOK)
        while q < min(lim, i_end + START_REACH):
            if not hiss(q):
                q += 1
                continue
            stop = q
            while stop < lim and (hiss(stop) or (stop + 1 < lim and hiss(stop + 1))):
                stop += 1
            here = [k for k in range(q, stop) if hiss(k) and fh[k] < ph[k] + g - 6.0]
            if len(here) > len(lost):
                lost = here
            q = stop + 1
        # the word the tail belongs to: the last one that starts inside the run (Whisper often boxes a final s into the next word)
        wb = [w for w in W if w["start"] <= b / sr - 0.02]
        word = wb[-1]["w"] if wb else "?"
        if len(lost) >= MIN_LOST and max(ph[q] + g for q in lost) >= LOUD:
            loud_bb = max(pb[q] + g for q in lost)
            loud_hf = max(ph[q] + g for q in lost)
            t = (w0 + lost[0] * h) / sr
            flags.append(G.flag("A13", f"hiss:{G.key(word) or '_'}@{t:.2f}", t, word,
                                f"{G.fmt_t(t)} '{word}': the final goes quiet while the laid-out take still sounds: {len(lost) * 5} ms of the "
                                f"word's end lost (loudest {loud_bb:.0f} dB, 4-12 kHz {loud_hf:.0f} dB) - a cut, mute or fade ate its tail; "
                                f"fix the step that cut (or a re-take), tails.py --fix lays it back where there is room",
                                ms=len(lost) * 5, loud=round(float(max(loud_bb, loud_hf)), 1)))
            if fix:
                i0, i1 = lost[0], lost[-1] + 1
                room = all(fb[k] < -45 or fb[k] <= pb[k] + g + 1.0 for k in range(i0, min(n, i1 + 3)))
                if room:
                    fixes.append((w0 + i0 * h, w0 + i1 * h, off, g))
                else:
                    no_room.append(flags[-1])
        # the VOICED tail (pause mutes can take the creak at the ends of words like "second.", "button.", "gone.": 80-180 ms under
        # 1.2 kHz at -16 to -44 dB, to digital silence; A1 reads releases and hiss and the pass above reads the hiss band, so neither
        # sees them): the reference's frames over V_BAR centred under V_HZ, from the run's
        # last 60 ms, connected to the run (never under -50 dB between them), where the final sits V_DROP dB under the reference
        # A creak is pulsed (frames dip between its pulses) and can follow a closure after a short final run (the "-ond" of "second."
        # is 60 ms, not a run of its own), so the frames are counted over V_REACH past the run's end, not held to one unbroken stretch,
        # and the final must be silenced there (a mute or a cut: under V_SILENT; the next word moved up by a cut pause sounds there,
        # and a misaligned run is quiet but not silent): the class is a mute that took the voice, never a level change
        vc = centroids(pm, w0 + off, n, h)
        k0, k1 = max(0, i_end - FADE_LOOK), min(n, i_end + V_REACH)
        vlost = [k for k in range(k0, k1) if pb[k] + g > V_BAR and vc[k] < V_HZ and fb[k] <= V_SILENT]
        gap_ok = True
        if vlost:     # the tail is the word's own: from where the final last sounded (the mute's start; a short word after the run's end,
            # "them." after "need", is no run of its own) to the first lost frame, the take never rests 20 ms under -50 dB
            js = next((j for j in range(vlost[0] - 1, -1, -1) if fb[j] > -50), min(i_end, vlost[0]))
            rest = 0
            for j in range(js, vlost[0]):
                rest = rest + 1 if pb[j] + g < -50 else 0
                if rest >= 4:
                    gap_ok = False
                    break
        if len(vlost) >= V_MIN and gap_ok and not any(f["key"].startswith("voiced:") and abs(f["t"] - (w0 + vlost[0] * h) / sr) < 0.05
                                                      for f in flags):     # two runs' windows can hold the same tail: once
            loud_v = max(pb[q] + g for q in vlost)
            t = (w0 + vlost[0] * h) / sr
            flags.append(G.flag("A13", f"voiced:{G.key(word) or '_'}@{t:.2f}", t, word,
                                f"{G.fmt_t(t)} '{word}': the final goes quiet while the laid-out take's voice still sounds (under "
                                f"{V_HZ / 1000:.1f} kHz: a creak, a nasal, a voiced end): {len(vlost) * 5} ms of the word's end lost (loudest "
                                f"{loud_v:.0f} dB) - a mute ate its tail; hisstails.py --fix lays it back where there is room",
                                ms=len(vlost) * 5, loud=round(float(loud_v), 1)))
            if fix:
                i0, i1 = vlost[0], vlost[-1] + 1
                room = all(fb[k] < -45 or fb[k] <= pb[k] + g + 1.0 for k in range(i0, min(n, i1 + 3)))
                if room:
                    fixes.append((w0 + i0 * h, w0 + i1 * h, off, g))
                else:
                    no_room.append(flags[-1])
    out = {"check": "A13", "final": str(P["final"]), "raw": str(ref), "flags": flags}
    if fix and fixes:
        import shutil
        import soundfile as sf
        final = Path(P["final"])
        backup = final.with_name(final.stem + "_prehiss.wav")
        shutil.copy2(final, backup)
        y = al.x.copy()
        cf, fo = int(0.005 * sr), int(0.015 * sr)
        for s0, s1, off, g in fixes:
            st_, en_ = s0 - cf, s1 + fo
            src = al.p[st_ + off:en_ + off] * (10 ** (g / 20))
            w_in = np.ones(en_ - st_)
            w_in[:cf] = np.linspace(0, 1, cf)
            w_out = np.ones(en_ - st_)
            w_out[-fo:] = np.linspace(1, 0, fo)
            mix = w_in * w_out           # the take's sound in, faded at both ends; the final's own sound under it gives way
            y[st_:en_] = y[st_:en_] * (1 - mix)[:, None] + src * mix[:, None]
        sf.write(str(final), y, sr, subtype="PCM_16")
        out["fixed"] = [round(s0 / sr, 3) for s0, *_ in fixes]
        out["backup"] = str(backup)
    out["no_room"] = no_room
    if not quiet:
        for f in flags:
            print(f["msg"])
        print(f"A13 hiss tails: {len(anchors)} speech runs against {ref.name}; {len(flags)} tail(s) lost" +
              (f"; laid back {len(out.get('fixed', []))} (backup {Path(out['backup']).name}), no room {len(no_room)}"
               if fix and out.get("fixed") else ""))
    return out


def main():
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--fix", action="store_true", help="lay every lost hiss back from the reference where there is room (the narration "
                    "rewritten in place, the old one kept as <name>_prehiss.wav); then the gate again")
    a = ap.parse_args()
    if a.fix:   # a locked narration is changed only by voice_layin.py (standard/VOICE_LOCK.md)
        sys.path.insert(0, str(G.VOICE_TOOLS))
        __import__("voice_lock").guard_argv(__file__)
    P = G.paths_from(a)
    res = run(P, quiet=False, ref=a.raw if a.raw else None, fix=a.fix)
    sys.exit(1 if (res["flags"] and not a.fix) or res.get("no_room") else 0)


if __name__ == "__main__":
    main()
