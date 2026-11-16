"""Line starts Whisper timed late: after a run of the captions, the first words of some lines come out late and squashed (three words
boxed into 0.11 s that the voice says over 0.67 s, a line's first word 0.2-0.3 s late); the pictures anchored on those words and the
subtitles land late, and the gate's A3 measures 0.36-0.60-s pauses that are 0.15-0.22 s. For every word after a sentence end or a line
change whose sound starts earlier than Whisper says (the narration's onset:
three 10-ms frames over -30 dB after 30 ms of quiet past the word before), the word starts at that onset; the squashed words after it
(under 80 ms each) share the span up to the first word Whisper timed whole, by letters. Rewrites build/captions/words.json in place
(backup words_prelinestarts.json); run right after dj captions, before sync_words and the gate.

  EDIT tools/sound/linestarts.py <video> [--dry]"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gatelib as G  # noqa: E402

FINE = 0.01
QUIET, ONSET, SQUASH = -45.0, -30.0, 0.08


def main():
    __import__("sys").path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "voice"))  # the voice lock (standard/VOICE_LOCK.md): a locked narration
    __import__("voice_lock").guard_argv(__file__, unless="--dry")  # is changed only by voice_layin.py
    G.utf8_stdout()
    ap = G.add_path_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    P = G.paths_from(a)
    x, sr = G.load_mono(P["final"])
    lf = G.frame_db(x, sr, FINE)
    path = Path(P["words"])
    raw = json.loads(path.read_text(encoding="utf-8"))
    W = raw["words"] if isinstance(raw, dict) else raw
    moved = 0
    for i in range(1, len(W)):
        p, b = W[i - 1], W[i]
        if not (p["beat"] != b["beat"] or re.search(r"[.!?][\"”')]*$", p["w"].strip())) or b["start"] - p["end"] > 3.0:
            continue
        # the pause after p: the LONGEST run of quiet (30 ms or more) starting no earlier than 50 ms before p's end. Never the first one:
        # a word-final stop's closure is 30-60 ms of quiet inside the word, and its release (a /k/ burst, a /ks/ hiss) is no onset
        # (a next word moved onto the /k/ of "back." would hide a 0.46-s pause with an inhale from the gate's A3)
        k0, kb = int((p["end"] - 0.05) / FINE), int(b["start"] / FINE)
        best, k = (0, -1), k0
        while k < kb:
            if (lf[k:k + 3] < QUIET).all():
                j = k
                while j < kb and lf[j] < QUIET:
                    j += 1
                if j - k > best[0]:
                    best = (j - k, k)
                k = j
            else:
                k += 1
        if best[1] < 0:
            continue
        k = best[1]
        while k < kb and not (lf[k:k + 3] > ONSET).all():
            k += 1
        on = k * FINE
        if on > b["start"] - 0.08:
            continue
        run = [i]
        while run[-1] + 1 < len(W) and W[run[-1]]["beat"] == b["beat"] and W[run[-1]]["end"] - W[run[-1]]["start"] < SQUASH:
            run.append(run[-1] + 1)
        last = run[-1]
        if len(run) == 1 or W[last]["end"] - W[last]["start"] < SQUASH:     # b alone (timed whole), or the beat ends squashed
            end, run = W[i]["end"], [i]
        else:
            end, run = W[last]["start"], run[:-1]
        letters = [max(1, len(re.sub(r"\W", "", W[j]["w"]))) for j in run]
        t, old = on, [(W[j]["w"], W[j]["start"]) for j in run]
        for j, n in zip(run, letters):
            W[j] = dict(W[j], start=round(t, 3), end=round(t + (end - on) * n / sum(letters), 3))
            t = W[j]["end"]
        moved += 1
        print(f"  {b['beat']}: {' '.join(w for w, _ in old)!r} from {old[0][1]:.2f} -> {on:.2f} (the voice's onset; "
              f"{len(run)} word(s) over {on:.2f}-{end:.2f})")
    print(f"{moved} line start(s) moved")
    if moved and not a.dry:
        shutil.copy(path, path.with_name("words_prelinestarts.json"))
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=1 if "\n" in path.read_text(encoding="utf-8")[:200] else None),
                        encoding="utf-8")
        print(f"-> {path} (backup words_prelinestarts.json)")


if __name__ == "__main__":
    main()
