"""The voice guard's accent verdict on one wav, as JSON (for the voice lock: autopick.py, voice_layin.py and the gate's A11).
voice_guard.screen() on the wav with its words (one beat per words' "beat", or the whole wav as one); prints {"hard": [...], "soft":
[...], "tone": [...], "flags": n}: hard = ACCENT (a British stretch, or rhotic.py's non-rhotic r on a take with timestamps), soft = ACCENT?
(maybe British). The lock's rule: a hard or soft accent flag rejects a take (standard/VOICE_LOCK.md stage 1: British stretches hide in
sections kept "by measures"), and a hard one fails the final narration (A11).

  PIPE tools/voice/accent_take.py <wav> --words <words.json> [--beats <beats.json>] [--voice long|short]
      [--video <videos/<video>>]       (--video: the whole narration with dj's sections, as voice_guard.py <video dir> does)
      [--span T0 T1]                   (only flags on beats that overlap these seconds)
  PIPE tools/voice/accent_take.py <wav> --in-place T0 T1 [--grid-t0 G]
      IN PLACE (a line can pass alone and fail A11 in the narration): <wav> is the piece laid where it will sit, with the narration's
      own seconds around it (voice_layin's preview, autopick's place file); the guard's 2-s windows (hop 0.5 s, as the gate) on all
      four 0.125-s grid offsets; a hard or maybe stretch that overlaps T0-T1 by over 0.3 s on any of them rejects. --grid-t0: the
      wav's start on the narration's clock (the gate's own grid is the offset that lines the windows up with the narration's 0.5-s
      grid; reported as "gate")."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
sys.path.insert(0, str(HERE))
import voice_guard as VG  # noqa: E402

OFFSETS = 4                 # grid offsets judged in place (hop 0.5 / 4 = 0.125 s apart)


def in_place(wav, t0, t1, grid_t0=None):
    """-> {"hard": [...], "soft": [...], "offsets": [...], "gate": i or None}: the accent where the piece sits. A take judged alone has
    its last second under-covered (the 2-s windows stop a second before the file's end and the 5-window median thins it): a take can
    read 0.35-0.44 at its end alone and 0.76 over 4 s in the narration, at the join into the next take. The narration's grid is one
    of a continuum of offsets, so all four are judged: a stretch on any of them rejects (the margin)."""
    wav = Path(wav)
    hop = 0.5 / OFFSETS
    subprocess.run([str(VG.ACCENT_PY), str(HERE / "voice_guard_embed.py"), str(wav), "--hop", str(hop), "--force"],
                   check=True, capture_output=True)
    E = json.loads(Path(str(wav) + ".guard_embed.json").read_text(encoding="utf-8"))
    if abs(float(E["hop"]) - hop) > 1e-9:
        raise SystemExit(f"{wav}: the embedding's hop is {E['hop']}, not {hop}")
    M = VG.load_model()  # the creator-built model, or a stop with the commands that build it
    thr = M["thresholds"]
    gate = None
    if grid_t0 is not None:     # window j starts at grid_t0 + j * hop on the narration's clock; the gate's start on multiples of 0.5
        gate = int(round((-grid_t0 % 0.5) / hop)) % OFFSETS
    out = {"hard": [], "soft": [], "offsets": [], "gate": gate, "wav": str(wav), "span": [round(t0, 3), round(t1, 3)]}
    for o in range(OFFSETS):
        sub = {**E, "t": E["t"][o::OFFSETS], "p": E["p"][o::OFFSETS], "acc": E["acc"][o::OFFSETS], "spk": E["spk"][o::OFFSETS],
               "hop": 0.5}
        ts, acc = VG.accent_scores(sub, M, "long")
        row = {"offset": o, "max": round(float(acc.max()), 3) if len(acc) else None, "hard": [], "soft": []}
        for kind, bar in (("hard", thr["accent"]), ("soft", thr["accent_soft"])):
            for a, b in VG.stretches_over(ts, acc, bar, thr["accent_min_s"]):
                if min(b, t1) - max(a, t0) > 0.3:
                    item = {"offset": o, "start": round(float(a), 2), "end": round(float(b), 2), "gate": o == gate,
                            "msg": f"{'British' if kind == 'hard' else 'maybe British'} {VG.fmt_t(a)}-{VG.fmt_t(b)} in place "
                                   f"(grid offset {o * hop:.3f} s{', the gate' + chr(39) + 's own' if o == gate else ''}, peak "
                                   f"{float(acc[(ts >= a) & (ts <= b)].max()):.2f})"}
                    row[kind].append(item)
                    out[kind].append(item)
        out["offsets"].append(row)
    if out["hard"]:        # a hard stretch is also a maybe one: report it once, as hard
        out["soft"] = [s for s in out["soft"] if not any(h["offset"] == s["offset"] and h["start"] <= s["end"] and s["start"] <= h["end"]
                                                          for h in out["hard"])]
    return out


def in_place_rejects(res):
    """the reasons an in-place verdict rejects a take: a British stretch on any grid offset (the gate fails on its own; the others are
    the margin), a maybe-British one on the gate's own grid (or on any when the grid isn't known), as autopick rejects a maybe alone"""
    why = [h["msg"] for h in res["hard"]]
    why += [s["msg"] for s in res["soft"] if res.get("gate") is None or s["offset"] == res["gate"]]
    return why


def main():
    for s in (sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav", nargs="?")
    ap.add_argument("--words")
    ap.add_argument("--beats")
    ap.add_argument("--voice", default="long", choices=["long", "short"])
    ap.add_argument("--video")
    ap.add_argument("--span", nargs=2, type=float)
    ap.add_argument("--json")
    ap.add_argument("--in-place", nargs=2, type=float, metavar=("T0", "T1"))
    ap.add_argument("--grid-t0", type=float)
    a = ap.parse_args()
    if a.in_place:
        res = in_place(a.wav, a.in_place[0], a.in_place[1], a.grid_t0)
        s = json.dumps(res, ensure_ascii=False, indent=1)
        if a.json:
            Path(a.json).write_text(s, encoding="utf-8")
        print(s)
        return
    M = VG.load_model()  # the creator-built model, or a stop with the commands that build it
    secs = None
    if a.video:
        ctx, tcfg, secs, beats, words_path, _src = VG.video_setup(Path(a.video))
        wav = Path(a.wav) if a.wav else ctx.build / "voice" / "narration.wav"
        words = VG.load_words(a.words or words_path)
        voice = ctx.fmt
    else:
        wav = Path(a.wav)
        words = VG.load_words(a.words)
        voice = a.voice
        if a.beats:
            bj = json.loads(Path(a.beats).read_text(encoding="utf-8"))
            beats = [{"id": b["id"], "start": b["start"], "end": b.get("voice_end", b.get("end")), "text": b.get("voice", "")}
                     for b in bj["beats"]]
        else:
            ids = list(dict.fromkeys(w["beat"] or "take" for w in words))
            beats = [{"id": i, "start": min(w["start"] for w in words if (w["beat"] or "take") == i),
                      "end": max(w["end"] for w in words if (w["beat"] or "take") == i), "text": ""} for i in ids]
    import wave
    with wave.open(str(wav)) as wf:
        dur = wf.getnframes() / wf.getframerate()
    if dur < 4.0:
        raise SystemExit(f"{wav}: {dur:.1f} s is too short for the accent guard (its windows are 2 s; give it 4 s or more: the whole take)")
    res = VG.screen(wav, words, beats, M, sections=secs, voice=voice)
    out = {"hard": [], "soft": [], "tone": [], "wav": str(wav)}
    for r in res["beats"]:
        if a.span and (r["end"] < a.span[0] or r["start"] > a.span[1]):
            continue
        for kind, v, msg in r["flags"]:
            item = {"beat": r["id"], "start": round(r["start"], 2), "end": round(r["end"], 2), "kind": kind, "msg": msg,
                    "score": round(float(r["accent"]), 3) if r["accent"] == r["accent"] else None}
            out["hard" if kind == "ACCENT" else "soft" if kind == "ACCENT?" else "tone"].append(item)
    out["accent_by_beat"] = {r["id"]: (round(float(r["accent"]), 3) if r["accent"] == r["accent"] else None) for r in res["beats"]}
    s = json.dumps(out, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(s, encoding="utf-8")
    print(s)


if __name__ == "__main__":
    main()
