"""A2's fix, on the cleaned voice (levels only, no time moves, so the word times stay true); it fixes exactly what mutescan.py finds:
  1. every SCRAP (a lone burst over -55 dB, 60 ms at most, right after 30 ms or more of digital silence, quiet after): muted, with a
     10-ms fade back in after it. With the raw takes, a scrap that is the take's own lone burst (a word's release laid back by
     tails.py --fix) is left alone;
  2. every CHOP (a mute that starts on sound, the last 10 ms over -45 dB, within 0.22 s of a word's end): the 40 ms before the mute
     fade out, so the word decays instead of stepping into silence. With the raw takes, a chop where the take dies too is left.
In the voice chain (tools/sound/voice_chain.sh) it runs before tails.py --fix: what a mute took from a word's end is laid back
after, from the take, and checked by A1.

  EDIT tools/sound/fixmutes.py <video> [--final F --raw R --words W]
      [--out O]   (default: the final rewritten in place, the old one kept as <name>_prefixmutes.wav)
      [--no-raw]  (every finding fixed, nothing checked against the take)"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402
import mutescan as MS  # noqa: E402


def run(P, out=None, use_raw=True, quiet=False):
    al = None
    if use_raw and Path(P["raw"]).exists():
        from tails import Align
        al = Align(P["final"], P["raw"], P["words"])
    x, sr = sf.read(str(P["final"]), always_2d=True)
    info = sf.info(str(P["final"]))
    mono = x.mean(1)
    W = al.W if al is not None else G.load_words(P["words"])
    chops, scraps, exempt = MS.find(mono, sr, W, al, chop_bar=-45.0)
    g = np.ones(len(mono))
    f10, f40 = int(0.01 * sr), int(0.04 * sr)
    for s in scraps:
        a, b = s["s"], s["e"]
        g[a:b] = 0
        g[b:b + f10] = np.minimum(g[b:b + f10], np.linspace(0, 1, len(g[b:b + f10])))
    for c in chops:
        r0 = c["s"]
        g[max(0, r0 - f40):r0] = np.minimum(g[max(0, r0 - f40):r0], np.linspace(1, 0, r0 - max(0, r0 - f40)))
    y = x * g[:, None]
    dst = Path(out) if out else Path(P["final"])
    res = {"final": str(P["final"]), "out": str(dst), "scraps_muted": [round(s["t"], 3) for s in scraps],
           "chops_faded": [(round(c["t"], 3), c["word"]) for c in chops],
           "left": [{k: v for k, v in e.items() if k not in ("s", "e")} for e in exempt]}
    if scraps or chops or out:
        if not out:
            bak = dst.with_name(dst.stem + "_prefixmutes.wav")
            shutil.copy2(dst, bak)
            res["backup"] = str(bak)
        sf.write(str(dst), y if x.shape[1] > 1 else y[:, 0], sr, subtype=info.subtype)
    if not quiet:
        print(f"fixmutes: {len(scraps)} scraps muted {res['scraps_muted']}; {len(chops)} chopped word ends faded {res['chops_faded']}; "
              f"{len(exempt)} left (the take's own sound) -> {dst}" + (f" (backup {res['backup']})" if "backup" in res else ""))
    return res


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__)  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--out", help="write here instead of rewriting the final in place")
    ap.add_argument("--no-raw", action="store_true")
    a = ap.parse_args()
    res = run(G.paths_from(a), out=a.out, use_raw=not a.no_raw)
    G.write_json(a.json, res)


if __name__ == "__main__":
    main()
