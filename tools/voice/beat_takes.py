"""Takes of single beats for the creator to pick by ear (which one slips into another accent, which one is just normal).

Each take: the same voice, model and settings as the narration (config/tts.toml [tts]), only the seed new; the beat voiced with its
neighbours as previous/next text so it sits in the flow; leading/trailing silence trimmed and pauses over 0.16 s cut to 0.12 s like the
narration's; levelled to the current beat's voiced level. Whisper (small.en) reads every take back against the script, so a take with a
dropped or garbled word is flagged before anyone hears it. Writes <out>/<beat>_0_now.wav (the current one), <beat>_1.wav ... and
takes.json.

  PIPE tools/voice/beat_takes.py <build dir> <out dir> S12 S14 [--n 4] [--seed 7100] [--text S12b "new words"]"""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj import tts  # noqa: E402
from dj.core import SR, load_config, read_wav, write_wav  # noqa: E402


def norm(s):
    return [w for w in re.sub(r"[^a-z0-9' ]", " ", s.lower().replace("’", "'").replace("-", " ")).split() if w]


def check(model, wav, text):
    segs, _ = model.transcribe(str(wav), language="en", beam_size=5, word_timestamps=True)
    words = [(w.word.strip(), w.probability) for s in segs for w in s.words]
    heard = " ".join(w for w, _ in words)
    want, got = norm(text), norm(heard)
    missing = [w for w in want if w not in got]
    low = [(w, round(p, 2)) for w, p in words if p < 0.5]
    return heard, missing, low


def main():
    a = sys.argv[1:]
    build, out = Path(a[0]), Path(a[1])
    ids, n, seed0, texts, i = [], 4, 7100, {}, 2
    while i < len(a):
        if a[i] == "--n":
            n = int(a[i + 1]); i += 2
        elif a[i] == "--seed":
            seed0 = int(a[i + 1]); i += 2
        elif a[i] == "--text":
            texts[a[i + 1]] = a[i + 2]; i += 3
        else:
            ids.append(a[i]); i += 1
    cfg = load_config()   # config/tts.toml (dj.core)
    tcfg = cfg["tts"]
    beats = json.loads((build / "beats.json").read_text(encoding="utf-8"))["beats"]
    voiced = [b for b in beats if b.get("voice")]
    pos = {b["id"]: k for k, b in enumerate(voiced)}
    out.mkdir(parents=True, exist_ok=True)
    from faster_whisper import WhisperModel
    model = WhisperModel("small.en", device="cpu", compute_type="int8")
    report = {}
    for bid in ids:
        k = pos[bid]
        b = voiced[k]
        text = texts.get(bid, b["voice"])
        prev = voiced[k - 1]["voice"] if k > 0 else None
        nxt = voiced[k + 1]["voice"] if k + 1 < len(voiced) else None
        now = read_wav(b["wav"])
        target = tts.voiced_db(now)
        shutil.copy2(b["wav"], out / f"{bid}_0_now.wav")
        rows = [{"take": 0, "file": f"{bid}_0_now.wav", "seconds": round(len(now) / SR, 2), "note": "the current one"}]
        print(f"\n{bid}: \"{text[:90]}\" (now {len(now) / SR:.2f} s)")
        for j in range(1, n + 1):
            t = copy.deepcopy(tcfg)
            t["elevenlabs"]["seed"] = seed0 + 10 * k + j
            raw = out / f"{bid}_{j}.raw.wav"
            tts.elevenlabs(t, text, prev, nxt, raw)
            x = read_wav(raw)
            raw.unlink()
            x = tts.trim_edges(x)
            x = tts.tighten_pauses(x, tcfg.get("max_pause", 0.16), keep=0.12)
            v = tts.voiced_db(x)
            if v is not None and target is not None:
                x = np.clip(x.astype(np.float64) * 10 ** ((target - v) / 20), -32768, 32767).astype(np.int16)
            f = out / f"{bid}_{j}.wav"
            write_wav(f, x)
            heard, missing, low = check(model, f, text)
            flag = "OK" if not missing else "MISSING " + " ".join(missing)
            print(f"  take {j}: {len(x) / SR:5.2f} s  seed {t['elevenlabs']['seed']}  {flag}  unsure: {low}")
            rows.append({"take": j, "file": f.name, "seconds": round(len(x) / SR, 2), "seed": t["elevenlabs"]["seed"], "heard": heard,
                         "missing": missing, "unsure": low})
        report[bid] = {"text": text, "takes": rows}
    (out / "takes.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n{sum(len(r['takes']) - 1 for r in report.values())} takes in {out}")


if __name__ == "__main__":
    main()
