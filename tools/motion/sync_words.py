"""Word times for the Remotion build, keyed by the SCRIPT's words: the captions step keeps what the voice said ("4th", "2001",
"$12.99"), the scenes reference the script ("fourth", "two thousand one"). Per beat, the script tokens are aligned to the heard
words (difflib); a heard number that stands for several script words ("2001" = "two thousand one") has its time spread over them
by length. Writes src/<src folder>/words.json ([{w, start, end, beat}]) and src/<src folder>/beats.json (the beat slots and the duration).

  PIPE tools/motion/sync_words.py <video folder name> <src subfolder>      e.g. 012-my-first-video v012"""
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import VIDEOS, VIDEOS_REPO  # noqa: E402
from onsets import apply_onsets  # noqa: E402

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
BUILD = VIDEOS / sys.argv[1] / "build"
DST = Path(__file__).parent / "src" / sys.argv[2]


def key(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'").replace("'", ""))


def spread(tokens, a, z):
    """Times for `tokens` spread over [a, z] by length."""
    L = [len(t) + 1 for t in tokens]
    tot, t, out = sum(L), a, []
    for n in L:
        d = (z - a) * n / tot
        out.append((round(t, 3), round(t + d, 3)))
        t += d
    return out


def main():
    beats = json.loads((BUILD / "beats.json").read_text(encoding="utf-8"))
    heard = json.loads((BUILD / "captions" / "words.json").read_text(encoding="utf-8"))["words"]
    heard = apply_onsets(heard, VIDEOS_REPO / BUILD.parent.name / "captions_fix.json")  # measured onsets (onsets.py)
    out, warn = [], 0
    for b in beats["beats"]:
        if not b.get("voice"):
            continue
        script = b["voice"].split()
        hw = [h for h in heard if h["beat"] == b["id"]]
        if not hw:
            print(f"  {b['id']}: nothing heard")
            continue
        sm = difflib.SequenceMatcher(a=[key(s) for s in script], b=[key(h["w"]) for h in hw], autojunk=False)
        times = [None] * len(script)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                for k in range(i2 - i1):
                    times[i1 + k] = (hw[j1 + k]["start"], hw[j1 + k]["end"])
            elif op == "replace":
                for k, tt in enumerate(spread(script[i1:i2], hw[j1]["start"], hw[j2 - 1]["end"])):
                    times[i1 + k] = tt
                if (i2 - i1) > 1 or (j2 - j1) > 1:
                    warn += 1
        for k in range(len(script)):  # words the voice skipped: a zero-length slot after the previous word
            if times[k] is None:
                prev = times[k - 1][1] if k and times[k - 1] else hw[0]["start"]
                times[k] = (prev, prev)
                print(f"  {b['id']}: '{script[k]}' not heard")
        out += [{"w": s, "start": round(a, 3), "end": round(z, 3), "beat": b["id"]} for s, (a, z) in zip(script, times)]
    DST.mkdir(parents=True, exist_ok=True)
    (DST / "words.json").write_text(json.dumps(out, indent=0), encoding="utf-8")
    slots = [{"id": b["id"], "start": b["start"], "voice_end": b["voice_end"], "end": b["end"]} for b in beats["beats"]]
    (DST / "beats.json").write_text(json.dumps({"duration": beats["duration"], "narration": beats["narration"], "beats": slots}, indent=0), encoding="utf-8")
    print(f"{len(out)} script words timed, {warn} multi-word replacements, duration {beats['duration']} s -> {DST}")


if __name__ == "__main__":
    main()
