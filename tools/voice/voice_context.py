"""Takes of one line voiced INSIDE a longer request, cut back at the pause before the next line. A short line voiced alone comes back
from ElevenLabs clipped (its last word ends before its own last character, cut off mid-sound); the continuous narration never has this,
because every line there is cut from a longer stream. So: the line + the head of the next line in one request (the previous line as
previous_text), then the cut 0.06 s before the next line's first sound (measured on the audio: the returned timestamps can be up to
0.2 s off), and the head from the real silence before the line's first sound. Writes build/voice/patch/<beat>_<k>.wav (+ .align.json)
for voice_patch.py --use <beat>=<k>, and a listening file per take in build/voice/patch/samples_<beat>/ (the line between the
narration's own neighbours, levelled to the line it replaces or to its neighbours, peaks limited as voice_patch does).

  cd tools && PIPE voice/voice_context.py ../videos/<video> <beat> <first take> <last take> "<head of the next line>" [--around a,b,c,d]
  --around: narration.wav seconds for the listening files: the line before (a-b) and the line after (c-d)"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj import script as dj_script  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, load_config, read_wav, write_wav  # noqa: E402
from dj.tts import elevenlabs  # noqa: E402
from voice_patch import limit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("beat")
    ap.add_argument("k0", type=int)
    ap.add_argument("k1", type=int)
    ap.add_argument("head", help="the first words of the next line, voiced after this one and cut away")
    ap.add_argument("--around", default="")
    a = ap.parse_args()
    cfg = load_config(None, video_config(a.video))
    ctx = Ctx(a.video, cfg)
    beats = [b for b in dj_script.load(ctx)["beats"] if b.get("voice") and not b.get("hold")]
    ids = [b["id"] for b in beats]
    i = ids.index(a.beat)
    text, prev = beats[i]["voice"], beats[i - 1]["voice"] if i else None
    # the last line has no next one: <head> is then any short continuation, voiced and cut away the same way ("See you in the next one.")
    nxt = beats[i + 1]["voice"] if i + 1 < len(beats) else a.head
    assert nxt.startswith(a.head), f"the next line starts {nxt[:40]!r}"
    pdir = ctx.build / "voice" / "patch"
    raw_dir = pdir / "context_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rms = lambda v: float(np.sqrt(np.mean((v / 32768) ** 2))) + 1e-12  # noqa: E731
    db = lambda x, t: 20 * np.log10(rms(x[max(0, int(t * SR)):int((t + 0.01) * SR)]))  # noqa: E731
    takes = []
    for k in range(a.k0, a.k1 + 1):
        dst, raw = pdir / f"{a.beat}_{k}.wav", raw_dir / f"{a.beat}_{k}.wav"
        if not raw.exists():
            tcfg = dict(cfg["tts"])
            tcfg["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "seed": cfg["tts"]["elevenlabs"].get("seed", 0) + k - 1}
            al, _ = elevenlabs(tcfg, f"{text} {a.head}", prev, nxt[len(a.head):].strip() or None, raw)
            raw.with_suffix(".align.json").write_text(json.dumps(al), encoding="utf-8")
        al = json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8"))
        x = read_wav(raw).astype(np.float64)
        s = "".join(al["characters"])
        t = al["character_start_times_seconds"][0]
        while t > 0 and db(x, t) > -60:   # back to the real silence before the line's first sound
            t -= 0.01
        lo = int(max(0.0, t - 0.02) * SR)
        t = al["character_end_times_seconds"][len(text) - 1] - 0.25   # into the line's last word, then on to its silence and the next sound
        while db(x, t) > -65:
            t += 0.01
        while db(x, t) < -45:
            t += 0.01
        hi = int((t - 0.06) * SR)
        y = x[lo:hi].copy()
        f = int(0.03 * SR)
        y[-f:] *= np.linspace(1, 0, f)
        write_wav(dst, np.round(y).astype(np.int16))
        dst.with_suffix(".align.json").write_text(json.dumps({key: v[:len(text)] for key, v in al.items()}), encoding="utf-8")
        assert s.startswith(text), s[:60]
        takes.append((k, y))
        print(f"  {a.beat} take {k}: {lo / SR:.2f}-{hi / SR:.2f} s of the request ({len(y) / SR:.2f} s), next line at {t:.2f} s")
    if a.around:
        p0, p1, n0, n1 = (float(v) for v in a.around.split(","))
        nar = read_wav(ctx.build / "voice" / "narration.wav").astype(np.float64)
        pre, post = nar[int(p0 * SR):int(p1 * SR)], nar[int(n0 * SR):int(n1 * SR)]
        ref = np.concatenate([pre, post])
        out = pdir / f"samples_{a.beat}"
        out.mkdir(exist_ok=True)
        gap = np.zeros(int(0.26 * SR))
        for k, y in takes:
            z = y * (rms(ref) / rms(y))
            if np.abs(z).max() > 0.891 * 32767:
                z = limit(z)
            write_wav(out / f"{a.beat}_{k}.wav", np.round(np.clip(np.concatenate([pre, z, gap, post]), -32768, 32767)).astype(np.int16))
        print("  listening files ->", out)


if __name__ == "__main__":
    main()
