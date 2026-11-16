"""Which English accent a voice take sounds like, window by window. rhotic.py only hears the r after a vowel, so a stretch that slips
into another accent with no such r passes it. This uses CommonAccent's ECAPA-TDNN accent classifier
(Jzuluaga/accent-id-commonaccent_ecapa, MIT, trained on Common Voice's 16 English accents) on 3-s windows and reports P(wanted),
P(avoided) and the top label for each, plus the take's mean. A screen like rhotic.py: the creator's ear is the judge.

  ACCENT tools/voice/accent_id.py <wav> [<wav> ...] [--win 3.0] [--hop 1.5] [--quiet] [--want us,canada] [--avoid england,...]

--want: the accents the voice should have (default North American: us, canada); --avoid: the ones it must not slip into (default
the British Isles plus Australia and New Zealand). The names are the model's own labels; an unknown one stops the run and prints
them all. With the defaults the output reads as before: "North American ... British-isles+AU/NZ ...".
Runs in its own venv (PY_ACCENT: torch CPU + speechbrain 1.0.3; the model in MODELS/commonaccent_ecapa, fetched at setup).
torchaudio 2.11 dropped list_audio_backends(), which speechbrain still calls at import: it is shimmed here, and audio is read with
ffmpeg."""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import torch
import torchaudio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG, MODELS  # noqa: E402

if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
from speechbrain.inference.classifiers import EncoderClassifier  # noqa: E402
from speechbrain.utils.fetching import LocalStrategy  # noqa: E402

MODEL = str(MODELS / "commonaccent_ecapa")
NA = ("us", "canada")                                                        # the wanted accent (default)
UK = ("england", "scotland", "wales", "ireland", "australia", "newzealand")    # the accents it must not slip into (default)
SR = 16000


def load(path):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wavs", nargs="+")
    ap.add_argument("--win", type=float, default=3.0)
    ap.add_argument("--hop", type=float, default=1.5)
    ap.add_argument("--quiet", action="store_true", help="only each file's summary line")
    ap.add_argument("--want", default=",".join(NA), help="the accents the voice should have (model labels, comma-separated)")
    ap.add_argument("--avoid", default=",".join(UK), help="the accents it must not slip into")
    a = ap.parse_args()
    want = tuple(x.strip() for x in a.want.split(",") if x.strip())
    avoid = tuple(x.strip() for x in a.avoid.split(",") if x.strip())
    clf = EncoderClassifier.from_hparams(source=MODEL, savedir=MODEL + "/_sb", run_opts={"device": "cpu"}, overrides={"pretrained_path": MODEL},
                                         local_strategy=LocalStrategy.COPY)   # local files only, copied (Windows: no symlink rights)
    labels = [clf.hparams.label_encoder.decode_ndim(i) for i in range(16)]
    bad = [k for k in want + avoid if k not in labels]
    if bad:
        sys.exit(f"unknown accent label(s) {', '.join(bad)}; the model's labels: {', '.join(labels)}")
    for path in a.wavs:
        x = load(path)
        W, H = int(a.win * SR), int(a.hop * SR)
        starts = list(range(0, max(1, len(x) - W + 1), H)) or [0]
        rows = []
        for s in starts:
            seg = x[s:s + W]
            if np.sqrt(np.mean(seg ** 2)) < 0.005:   # silence: no verdict
                continue
            out = clf.classify_batch(torch.from_numpy(seg).unsqueeze(0))
            # the classifier's outputs are cosine scores (AM-softmax); scaled by its training scale (30) they become probabilities
            p = torch.softmax(30 * out[0].reshape(-1), dim=-1).numpy()
            pw = p[[labels.index(k) for k in want]].sum(); pa = p[[labels.index(k) for k in avoid]].sum()
            rows.append((s / SR, pw, pa, labels[int(np.argmax(p))]))
        if not rows:
            print(f"{path}: silent")
            continue
        pw = np.mean([r[1] for r in rows]); pa = np.mean([r[2] for r in rows])
        worst = max(rows, key=lambda r: r[2] - r[1])
        slips = sum(1 for r in rows if r[2] > r[1])
        wl = "North American" if want == NA else f"wanted ({'+'.join(want)})"
        al = "British-isles+AU/NZ" if avoid == UK else f"avoided ({'+'.join(avoid)})"
        side = "British" if avoid == UK else "to the avoided side"
        print(f"{path}: {wl} {pw:.2f}  {al} {pa:.2f}  {slips} of {len(rows)} windows lean {side}; most at {worst[0]:.1f} s "
              f"({worst[1]:.2f} / {worst[2]:.2f})")
        if not a.quiet:
            wn = "N.American" if want == NA else "wanted"
            an = "British" if avoid == UK else "avoided"
            for tt, pn, pb, top in rows:
                flag = f"  <-- {an.lower()}" if pb > pn else ""
                print(f"    {tt:6.1f}s  {wn} {pn:.2f}  {an} {pb:.2f}  top {top}{flag}")


if __name__ == "__main__":
    sys.exit(main())
