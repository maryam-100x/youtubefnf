"""Re-voice only some beats of a finished ElevenLabs narration and keep every other take as it is (a note on one or two lines shouldn't
change the lines already approved: a whole new request re-reads everything). Each patched beat is one request with the beats around it
as previous/next text (prosody), trimmed, levelled to the old beat, and spliced in with the old gaps. The result is written as
narration_final.wav next to build/, so the normal steps take it from there:

  cd tools && PIPE voice/voice_patch.py ../videos/<video> S05 S07 [--takes 2]
  cd tools && PIPE -m dj tts ../videos/<video> && PIPE -m dj captions ../videos/<video>

With --takes N every patched beat gets N takes (build/voice/patch/<beat>_<n>.wav), each checked by Whisper against the script; the
best match is used (or the one named with --use S03=3), the others stay for the creator's ear. A beat that is new in the script (not in
build/beats.json) is voiced the same way and set in its script place (it must be listed); holds are left out (dj tts puts them back).
Run it BEFORE editing anything else: the old beats come from build/beats.json and build/voice/narration.wav (move narration_final.wav
away first if one exists, or it is the 'old' narration).

Order when a patched line has NEW words: build the generated narration first (dj tts, no narration_final), THEN edit the script, then run
this, then dj tts again. A line edited before the generated build changes its section's cache key, and dj tts re-voices the whole
section. The splice writes narration_final.beats.json (its exact beat boundaries), which dj tts cuts at instead of guessing them with
Whisper."""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from dj import script as dj_script  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, load_config, read_wav, write_wav  # noqa: E402
from dj.tts import all_tempo, beat_tempo, elevenlabs, sound_end, sound_start, swallowed, tighten_pauses, trim_edges  # noqa: E402


def rms(x):
    return float(np.sqrt(np.mean((x.astype(np.float64) / 32768) ** 2)) + 1e-9)


def limit(xf):
    """Peaks over -1 dBFS brought under it by a look-ahead gain; the level stays. (A fast-attack limiter on the signal halved, then
    doubled, lets fast peaks through and the doubling clips them: re-voiced lines come out sounding bass-boosted and peaky.) The gain
    each sample needs to stay under -1 dBFS, held over +-4 ms (the minimum) and smoothed over the same window (the mean of those minima
    can't exceed the gain any peak needs, so nothing passes the ceiling)."""
    ceil = 0.891 * 32767
    a = np.abs(xf) if xf.ndim == 1 else np.abs(xf).max(axis=1)
    g = np.minimum(1.0, ceil / np.maximum(a, 1e-9))
    w = 2 * int(0.004 * SR) + 1
    p = w // 2
    g = np.lib.stride_tricks.sliding_window_view(np.pad(g, p, mode="edge"), w).min(axis=-1)
    c = np.cumsum(np.insert(np.pad(g, p, mode="edge"), 0, 0.0))
    g = (c[w:] - c[:-w]) / w
    return xf * (g if xf.ndim == 1 else g[:, None])


def edge_in_sound(nar, i):
    """A slot edge with sound on both sides (20 ms each over -45 dB) cuts through a word: --keep-old replaces a patched beat's old slot
    whole, so a neighbour's word that runs over the edge goes with it (a short "the" or "it" at a slot's end is lost). Beat boundaries
    often sit 25-50 ms inside a word after cuts that moved them. Returns the two levels, or None."""
    w = int(0.02 * SR)
    if i < w or i > len(nar) - w:   # the narration's own start or end
        return None
    lv = [20 * np.log10(rms(nar[max(0, j):j + w])) for j in (i - w, i)]
    return None if min(lv) <= -45 else lv


def pause_mid(nar, i):
    """The middle of the longest quiet run (10-ms frames under -50 dB, 80 ms or more) within 0.5 s of a slot edge: the pause between the
    two lines (a line's own pauses are capped at 0.12 s, a stop consonant's closure ~60 ms). None when there is no such run."""
    h = int(0.01 * SR)
    a0, a1 = max(0, i - SR // 2), min(len(nar), i + SR // 2)
    seg = nar[a0:a1].astype(np.float64) / 32768
    n = len(seg) // h
    q = 20 * np.log10(np.sqrt((seg[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-12) < -50
    runs, r0 = [], None
    for k in range(n + 1):
        if k < n and q[k]:
            r0 = k if r0 is None else r0
        elif r0 is not None:
            runs.append((r0, k))
            r0 = None
    best = max(runs, key=lambda r: r[1] - r[0], default=None)
    return None if not best or best[1] - best[0] < 8 else a0 + (best[0] + best[1]) * h // 2


def words_match(cfg, wav, text):
    from dj.captions import heard_words
    hw = heard_words(cfg, wav)
    heard = " ".join(h["w"] for h in hw)
    k = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).split()  # noqa: E731
    return difflib.SequenceMatcher(a=k(text), b=k(heard)).ratio(), heard, hw


def edges(x):
    """trim_edges, then each edge out to where the sound really starts / dies (never clip a consonant)."""
    y = trim_edges(x)
    off = next((i for i in range(0, len(x) - len(y) + 1, 480) if np.array_equal(x[i:i + 480], y[:480])), 0)
    a = sound_start(x, (off + int(0.03 * SR)) / SR, 0.0, reach=0.15)
    b = sound_end(x, (off + len(y) - int(0.12 * SR)) / SR, len(x) / SR, reach=0.3)
    return x[min(a, off):max(b, off + len(y))]


def main():
    __import__("voice_lock").guard_argv(__file__)  # the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("beats", nargs="+")
    ap.add_argument("--takes", type=int, default=1)
    ap.add_argument("--use", nargs="*", default=[], help="BEAT=N: use take N for that beat (picked by ear or by measuring)")
    ap.add_argument("--no-prev", action="store_true", help="send no previous line as context (the model can speak a short "
                    "previous_text into every take of the next line)")
    ap.add_argument("--keep-old", action="store_true", help="keep every old beat's slot exactly (a clean, never-patched narration); "
                    "the new takes get the continuous mode's edges (0.03 s lead, 0.06 s tail + the punctuation gap)")
    a = ap.parse_args()
    __import__("voice_ready").require(a.video, __file__)  # stage 0 of the voice lock: facts, cold read, bites, names stamped on this script
    # the script's CONFIG: lines, as dj applies them (without them a patched beat gets the default tail and pause cap instead of the
    # video's own sentence gap and pauses)
    cfg = load_config(None, video_config(a.video))
    ctx = Ctx(a.video, cfg)
    if (ctx.build.parent / "narration_final.wav").exists():
        raise SystemExit("narration_final.wav exists: move it away first (the old narration must be the generated one)")
    meta = dj_script.load(ctx)
    texts = {b["id"]: b["voice"] for b in meta["beats"] if b.get("voice")}
    old = json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]
    nar = read_wav(ctx.build / "voice" / "narration.wav")
    old_by = {b["id"]: b for b in old}
    order = [b for b in meta["beats"] if b.get("voice") and not b.get("hold")]  # the script's order (new beats included, holds out)
    ids = [b["id"] for b in order]
    new = [i for i in ids if i not in old_by]
    if set(new) - set(a.beats):
        raise SystemExit(f"new beats in the script must be listed to be voiced: {sorted(set(new) - set(a.beats))}")
    # a patched slot's edge inside a word is moved to the middle of the pause next to it, for both beats that share it (the neighbour's
    # word stays whole; edge_in_sound); an edge with no pause within 0.5 s stops the patch
    moved = {}
    if a.keep_old:
        spf = SR * ctx.fd[0] / ctx.fd[1]
        for bid in a.beats:
            if bid not in old_by:
                continue
            for side, i in (("start", round(old_by[bid]["start_f"] * spf)), ("end", round((old_by[bid]["start_f"] + old_by[bid]["frames"]) * spf))):
                lv = edge_in_sound(nar, i)
                if not lv or i in moved:
                    continue
                m = pause_mid(nar, i)
                if m is None:
                    raise SystemExit(f"{bid}'s slot {side} at {i / SR:.3f} s is inside a word ({lv[0]:.0f} / {lv[1]:.0f} dB) with no pause "
                                     f"within 0.5 s: move that boundary in build/beats.json by hand, then run this again")
                moved[i] = m
                print(f"  {bid} slot {side} {i / SR:.3f} s was inside a word ({lv[0]:.0f} / {lv[1]:.0f} dB): moved to the pause at {m / SR:.3f} s")
    out_dir = ctx.build / "voice" / "patch"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts, last_seg, bounds, pos = [], None, [], 0
    for i, b in enumerate(order):
        ob = old_by.get(b["id"])
        if ob:
            # the slot from its frame numbers (exact; the seconds in beats.json are rounded to 4 decimals, which shifts slots by a
            # sample or two and grows beats by a frame when dj tts rounds them up again)
            spf = SR * ctx.fd[0] / ctx.fd[1]
            s, e = round(ob["start_f"] * spf), round((ob["start_f"] + ob["frames"]) * spf)
            s, e = moved.get(s, s), moved.get(e, e)   # a boundary moved out of a word moves for both beats that share it
            v = int(round(ob["voice_end"] * SR))
            if a.keep_old and b["id"] == order[-1]["id"]:  # the last slot carries the tail, which dj tts adds again
                e -= int(round(cfg["tts"].get("tail", 0) * SR))
            # the old voiced part, its edges trimmed, and a sentence gap after it ([tts] gaps): the old slot boundaries can carry silence
            # from an earlier split, which becomes dead air in a Short
            seg = nar[s:e] if a.keep_old else trim_edges(nar[s:v])
        else:
            seg = last_seg  # a new beat: levelled to the beat before it
        gap = np.zeros(int(cfg["tts"].get("gaps", {}).get("sentence", 0.12) * SR), np.int16)
        if b["id"] in a.beats:
            text = texts[b["id"]]
            prev = texts.get(ids[i - 1]) if i and not a.no_prev else None
            nxt = texts.get(ids[i + 1]) if i + 1 < len(ids) else None
            best = None
            use = dict(u.split("=") for u in a.use)
            # a take picked by ear (--use) is used as it is: no takes are made or checked for that beat (span_takes.py can write
            # takes 2-4 of a beat whose take 1 doesn't exist, and the loop would voice a take 1 nobody asked for)
            for k in ([] if b["id"] in use else range(1, a.takes + 1)):
                wav = out_dir / f"{b['id']}_{k}.wav"
                aj = wav.with_suffix(".align.json")
                if not wav.exists():
                    tcfg = dict(cfg["tts"])
                    tcfg["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "seed": cfg["tts"]["elevenlabs"].get("seed", 0) + k - 1}
                    al, _ = elevenlabs(tcfg, text, prev, nxt, wav)
                    if al:
                        aj.write_text(json.dumps(al), encoding="utf-8")
                score, heard, hw = words_match(cfg, wav, text)
                # a final t/d/k/p the voice barely said; needs the take's own timestamps (Whisper's word times are too loose: a swallowed
                # ending can read 1 dB under on them and 33 dB under on the timestamps)
                weak = swallowed(read_wav(wav), json.loads(aj.read_text(encoding="utf-8"))) if aj.exists() else None
                score -= 0.05 * len(weak or [])
                # a take that stops while still sounding: ElevenLabs cut its last word (the file ends before its own last character,
                # the last 40 ms still loud). Voice such a line in context instead (voice_context.py)
                tail = read_wav(wav)[-int(0.04 * SR):].astype(np.float64)
                cut = 20 * np.log10(np.sqrt(np.mean((tail / 32768) ** 2)) + 1e-12) > -40
                score -= 0.5 if cut else 0
                print(f"  {b['id']} take {k}: score {score:.2f}  heard: {heard}" +
                      ("  | endings not checked (no timestamps)" if weak is None else
                       f"  | weak endings: {', '.join(f'{w} -{d:.0f} dB' for w, _, d in weak)}" if weak else "  | endings clear") +
                      ("  | ENDS MID-SOUND (clipped: voice it with voice_context.py)" if cut else ""))
                if best is None or score > best[0]:
                    best = (score, wav)
            if b["id"] in use:
                best = (None, out_dir / f"{b['id']}_{use[b['id']]}.wav")
                if not best[1].exists():
                    raise SystemExit(f"--use {b['id']}={use[b['id']]}: {best[1]} doesn't exist")
            x = tighten_pauses(edges(read_wav(best[1])), cfg["tts"].get("max_pause", 0))  # the continuous mode's pauses
            tempo = float(cfg["tts"].get("tempo", 1.0))
            if abs(tempo - 1.0) > 1e-3:  # the narration runs at [tts] tempo; the new take must match it (dj tts won't redo the final)
                x = all_tempo({"tempo": tempo}, [{"voice": text}], [x])[0]
            # the Shorts speed ([tts] hook_syl_s, tempo_all, tempo_share): the factor a fresh build gives this beat (dj tts leaves the
            # final alone, so new lines would come out unsped next to sped old ones)
            if cfg["tts"].get("tempo_all") or (b["id"] == ids[0] and not cfg["tts"].get("hook_like_rest")):  # hook_tempo's own rule
                x = beat_tempo(cfg["tts"], text, x, b["id"] == ids[0], b["id"])
            # the old beat's level, but never by clipping (a hard clip crushes ~8 dB of peaks and the mic sounds like it peaks; stopping
            # the gain where the take's peak reaches -1 dBFS leaves peaky takes 6-9.5 dB under the rest). So: the full gain, and only
            # the peaks over -1 dBFS caught by a gentle limiter
            xf = x.astype(np.float64) * (rms(seg) / rms(x))
            if float(np.abs(xf).max()) > 0.891 * 32767:
                xf = limit(xf)
            x = np.clip(np.round(xf), -32768, 32767).astype(np.int16)
            if a.keep_old:  # trim_edges keeps 0.12 s after the last sound: +0.06 s = the continuous mode's 0.06 s tail + 0.12 s sentence gap
                last = text.rstrip().rstrip("\"')")[-1:]
                g = cfg["tts"].get("gaps", {}).get("sentence" if last in ".?!" else "comma", 0.12) - 0.06
                x = np.concatenate([x, np.zeros(int(max(g, 0) * SR), np.int16)])
            print(f"  {b['id']}: {len(seg) / SR:.2f} s -> {len(x) / SR:.2f} s ({best[1].name})")
            seg = x
        piece = [seg] if (a.keep_old and (ob or b["id"] in a.beats)) else [seg, gap]
        parts += piece
        n = sum(len(q) for q in piece)
        bounds.append({"id": b["id"], "a": pos, "b": pos + n})
        pos += n
        last_seg = seg
    final = np.concatenate(parts)
    dst = ctx.build.parent / "narration_final.wav"
    write_wav(dst, final)
    # the splice's own beat boundaries (samples), so dj tts cuts it exactly there instead of guessing them with Whisper (on a long
    # splice the Whisper split puts a few cuts inside a word)
    dst.with_name(dst.stem + ".beats.json").write_text(json.dumps({"sr": SR, "beats": bounds}), encoding="utf-8")
    # which beats of the narration are patches now (the voice guard's TONE JUMP "voiced alone as a patch"): this splice's beats added to
    # the ones still in from an earlier splice; dj tts clears it when it builds from the generation (so the guard never flags beats an
    # earlier run dropped)
    rec = out_dir / "used.json"
    used = json.loads(rec.read_text(encoding="utf-8")) if rec.exists() else {}
    used.update({b: f"{b}_{dict(u.split('=') for u in a.use).get(b, 'best')}" for b in a.beats})
    rec.write_text(json.dumps(used, indent=1), encoding="utf-8")
    print(f"-> {dst} ({len(final) / SR:.2f} s) + {dst.stem}.beats.json; patched beats now: {', '.join(sorted(used))}")


if __name__ == "__main__":
    main()
