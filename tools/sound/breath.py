"""The shared voice chain's first clean-up step (voice_chain.sh): the safe breath pass. breath_cut.py's regions, muted only where the
kind is sentence/comma and the loudest frame is -24 dB or quieter (a full pass cuts real word ends), and a region starts only where the
word before has died away (under -45 dB, 10-ms frames), else it is dropped, so a mute never takes a word's last sound.
narration.wav -> narration_nb.wav (the original kept as narration_prebreath.wav), the report in
<dj>/pipeline/gate_sound/breath_report.json.

  EDIT tools/sound/breath.py <video> [--in W --out O --words J --report R]"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
import breath_cut as BC  # noqa: E402


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--in", dest="src")
    ap.add_argument("--out")
    ap.add_argument("--words")
    ap.add_argument("--report")
    a = ap.parse_args()
    P = G.paths(a.video, words=a.words)
    vdir = P["final"].parent
    src = Path(a.src) if a.src else P["final"]
    out = Path(a.out) if a.out else vdir / "narration_nb.wav"
    if not a.src:
        shutil.copy2(src, vdir / "narration_prebreath.wav")     # always the current narration
        src = vdir / "narration_prebreath.wav"
    x, sr = sf.read(str(src), dtype="float64", always_2d=False)
    words = sorted(G.load_words(P["words"]), key=lambda w: w["start"])
    words = [dict(w, word=w["w"]) for w in words]
    mono = x.mean(1) if x.ndim == 2 else x
    regions, skipped = BC.find_regions(mono, sr, words)
    safe = [r for r in regions if r["kind"] in ("sentence", "comma") and r["loudest_db"] <= -24]
    h = int(0.01 * sr)
    nf = len(mono) // h
    lv = 20 * np.log10(np.sqrt((mono[:nf * h].reshape(nf, h) ** 2).mean(1)) + 1e-12)

    def settle(r):
        j, e = int(r["start"] * 100), int(r["end"] * 100)
        while j < e and j < nf and lv[j] > -45:
            j += 1
        return dict(r, start=j / 100) if e - j >= 5 else None
    safe = [q for q in map(settle, safe) if q]
    y = BC.mute(x, sr, safe)
    y, nclick = BC.declick(y, sr)
    sf.write(str(out), y, sr, subtype="PCM_16")
    rep = Path(a.report) if a.report else P["out"] / "breath_report.json"
    G.write_json(rep, {"safe": safe, "all": regions, "skipped": skipped})
    print(f"{len(regions)} regions, {len(safe)} muted (sentence/comma, <= -24 dB), {sum(r['end'] - r['start'] for r in safe):.1f} s; "
          f"{len(skipped)} left alone; {nclick} declicks -> {out}")
    if BC.DROPS_ON_SOUND:   # a cut through a word before this step; not faded (the gate's A13/A1 name the word)
        print(f"  ! {len(BC.DROPS_ON_SOUND)} drop(s) into silence ON sound, left for the gate: {BC.DROPS_ON_SOUND[:10]}")


if __name__ == "__main__":
    main()
