"""A clone sample from a weak mic (a headset, a laptop or Bluetooth mic), rebuilt as if it was recorded on a good one, before the voice
is cloned (SETUP.md step 9). An instant clone copies the mic as well as the voice: a sample with no highs gives a clone with no highs,
whatever is done to its takes later. Rebuilding the sample once, before the clone, is what fixes it: a speech restoration model
(Sidon v0.1, MIT, sarulab-speech) re-synthesises the speech at 48 kHz with the voice kept. A headset sample measured 9 kHz of
bandwidth before and 14-16 kHz after; the clone made from the rebuilt sample was picked by ear over the one from the original.
The creator then has two clones voice the same lines and picks by ear (the original's clone stays a choice).

    EDIT tools/voice/rebuild_sample.py <recording> --check          the mic check: its bandwidth, and whether a rebuild is worth it
    EDIT tools/voice/rebuild_sample.py <recording> [-o <out.wav>]   rebuild it (default: <recording>_rebuilt.wav beside it)

Any audio file works (a phone's m4a, mp3, wav: read through the studio's ffmpeg). It runs on the CPU in EDIT on every computer (a few
minutes for a 3-minute sample); the model (~1.2 GB, pinned) downloads into MODELS/hf the first time.
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import FFMPEG  # noqa: E402

SIDON = ("sarulab-speech/sidon-v0.1", "b3b02d8bbd55fdbc410e6e46e76ef95ace4fbf52")       # repo, pinned revision (MIT)
W2V = ("facebook/w2v-bert-2.0", "da985ba0987f70aaeb84a80f2851cfac8c697a7b")             # its feature extractor's settings (MIT)
SR = 48_000
WEAK_BELOW_HZ = 10_000      # speech that stops below this came through a narrow mic (a headset: ~8 kHz; good mics 12.8 kHz+)


def read(path, sr=SR):
    """Mono float32 at sr, any format, through the studio's ffmpeg."""
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).copy()


def bandwidth(x, sr=SR):
    """The highest frequency the speech still reaches: the top edge where the voiced frames' average spectrum is within 50 dB of its
    loudest 1/3-octave band (a headset sample stops near 8-9 kHz, a good mic goes past 14 kHz)."""
    from scipy.signal import welch
    n = 2048
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    voiced = frames[rms > rms.max() * 10 ** (-30 / 20)]          # within 30 dB of the loudest frame: speech, not the pauses
    if len(voiced) == 0:
        return 0.0
    f, p = welch(voiced.reshape(-1), fs=sr, nperseg=4096)
    db = 10 * np.log10(p + 1e-20)
    centres = 100 * 2 ** (np.arange(0, 36) / 3)                   # 1/3-octave bands, 100 Hz to ~20 kHz
    centres = centres[centres < sr / 2 * 0.95]
    band = np.array([db[(f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))].mean() for c in centres])
    top = band.max()
    reach = centres[band >= top - 50]
    return float(reach.max()) if len(reach) else 0.0


def rebuild(x):
    """Sidon v0.1, the official demo's inference (HF Space sarulab-speech/sidon_demo_beta, app.py) with its CPU models."""
    import torch
    import torchaudio
    import transformers
    from huggingface_hub import hf_hub_download
    fe_path = hf_hub_download(SIDON[0], filename="feature_extractor_cpu.pt", revision=SIDON[1])
    dec_path = hf_hub_download(SIDON[0], filename="decoder_cpu.pt", revision=SIDON[1])
    pre = transformers.SeamlessM4TFeatureExtractor.from_pretrained(W2V[0], revision=W2V[1])
    fe = torch.jit.load(fe_path, map_location="cpu")
    dec = torch.jit.load(dec_path, map_location="cpu")
    with torch.inference_mode():
        w = 0.9 * (x / max(float(np.abs(x).max()), 1e-9))
        target_n = len(w)                                         # input and output are both 48 kHz
        w = torch.tensor(w, dtype=torch.float32).view(1, -1)
        w = torchaudio.functional.highpass_biquad(w, SR, 50)
        w16 = torchaudio.functional.resample(w, SR, 16_000)
        w16 = torch.nn.functional.pad(w16, (0, 24000))
        outs, cache = [], None
        for chunk in w16.view(-1).split(16000 * 96):
            inputs = pre(torch.nn.functional.pad(chunk, (160, 160)), return_tensors="pt")
            feat = fe(inputs["input_features"])["last_hidden_state"]
            if cache is not None:
                feat = torch.cat([cache, feat], dim=1)
            outs.append(dec(feat.transpose(1, 2)).view(-1)[:-960])
            cache = feat[:, -1:]
        return torch.cat(outs).float().numpy()[:target_n]


def write(path, y):
    import soundfile as sf
    peak = float(np.abs(y).max()) or 1.0
    sf.write(str(path), np.clip(y * (0.89 / peak), -1, 1), SR, subtype="PCM_16")      # peaks at -1 dBFS


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("recording")
    ap.add_argument("-o", "--out", help="where the rebuilt sample goes (default: <recording>_rebuilt.wav)")
    ap.add_argument("--check", action="store_true", help="the mic check only")
    a = ap.parse_args()
    src = Path(a.recording)
    x = read(src)
    bw = bandwidth(x)
    weak = bw < WEAK_BELOW_HZ
    print(f"{src.name}: {len(x) / SR:.1f} s, speech reaches {bw / 1000:.1f} kHz -> "
          + ("a narrow mic: rebuild it before cloning" if weak else "a full-band mic: clone it as it is"))
    if a.check:
        return 0
    out = Path(a.out) if a.out else src.with_name(src.stem + "_rebuilt.wav")
    t0 = time.time()
    y = rebuild(x)
    write(out, y)
    print(f"rebuilt in {time.time() - t0:.0f} s -> {out} (speech now reaches {bandwidth(y) / 1000:.1f} kHz)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
