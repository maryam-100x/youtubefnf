"""Takes of a span of consecutive lines voiced as ONE request in its place. An accent lives in a whole request, so a span where the
accent slips is re-voiced whole: one request with the lines before it voiced in the same request and cut away (or the line before as
previous_text), and the head of the line after voiced too and cut away (voice_context.py's method: a request's last word comes back
clipped when nothing follows it). Each take is split back into its lines at the pauses between them (the returned character times,
refined on the audio) and written as build/voice/patch/<beat>_<k>.wav (+ .align.json, times relative to the piece) for
`voice_patch.py --keep-old ... --use <beat>=<k>`. A listening file per take holds the narration's own seconds before and after the span,
the take levelled to the span it replaces; _0_now is the span as it is. Every take is screened with rhotic.py (the r after vowels: a
median dip under ~400 Hz is British for sure; a take over it still goes to the ear).

  cd tools && PIPE voice/span_takes.py ../videos/<video> <first beat> <last beat> <first take> <last take> [--around 3.0] [--seed 9100]
Costs the span's characters (+ the [tts.elevenlabs] prefix, the lines before and the head) per take; every call is logged in
<MEDIA>/voice/elevenlabs_usage.csv."""
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
from dj.tts import all_tempo, elevenlabs, frame_db, gap_between, quiet_floor, sound_start, tighten_pauses, voice_text  # noqa: E402
from rhotic import score as rhotic_score  # noqa: E402
from voice_patch import limit  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("first")
    ap.add_argument("last")
    ap.add_argument("k0", type=int)
    ap.add_argument("k1", type=int)
    ap.add_argument("--around", type=float, default=3.0, help="seconds of the narration before and after the span in each listening file")
    ap.add_argument("--seed", type=int, default=9100, help="take k uses this + k (clear of the narration's own seeds)")
    ap.add_argument("--context", default="narration_unlifted.wav", help="the narration in build/voice the listening files take their "
                    "seconds around the span from (a clean one: a clipped word of the old narration at a sample's start sounds like the take)")
    ap.add_argument("--say", nargs="*", default=[], help="WORD=SAYING respellings sent to ElevenLabs only, the same length (a foreign name "
                    "that comes out in its native accent: the text does it, never a tag); the stored take and its timestamps spell the "
                    "script again")
    ap.add_argument("--prev-text", help="previous_text sent instead of the line before (an outro after a quiet line comes out whispery "
                    "and tired; [tts.elevenlabs] lead_in gives an awake one)")
    ap.add_argument("--tail", help="the text voiced after the span's last line and cut away (default: the next line's first three words, "
                    "or \"And that's it.\" after the last line, which can pull an outro toward a wind-down)")
    ap.add_argument("--before", type=int, default=2, help="voice the N lines before the span in the same request and cut them away (a "
                    "line voiced alone, or at a section's end, comes out tired and breathy; inside its section it doesn't). No "
                    "previous_text then: the house lead_in opens the request. 0 = previous_text only")
    ap.add_argument("--before-min-s", type=float, default=10.0, help="the lines before reach at least this many seconds spoken (more "
                    "lines are taken until they do, at 3 words a second; the warm-up in front when the script runs out): a line voiced "
                    "after under 6 s of lines before opens tired; a request is warm by construction from 10 s (opening.py "
                    "WARM_CONTEXT_S). 0 = exactly --before lines")
    ap.add_argument("--name", help="the takes' file stem instead of <first>-<last> (variants of one span side by side)")
    ap.add_argument("--no-prev", action="store_true", help="no line before as context: a fresh request (a British place name in the "
                    "line before can pull every take of the next line British; as voice_patch's --no-prev)")
    ap.add_argument("--language-code", help="ElevenLabs language_code for these takes (e.g. en): the model and its normaliser held to it")
    ap.add_argument("--dict", action="append", default=[], help="a pronunciation dictionary for these takes: ID[:VERSION] "
                    "(tools/voice/eleven_dict.py makes one from tools/sound/names.json)")
    ap.add_argument("--plain", action="append", default=[], help="a name sent as written, not the names table's respelling (the "
                    "dictionary's alias serves it)")
    ap.add_argument("--warmup", help="the spoken lines voiced before a span that has no line before it (the video's first section) and "
                    "cut away, as the lines before are (the first request is the only one with nothing spoken before it, and its opening "
                    "comes out exhausted). Default: [tts.elevenlabs] warmup; '' = none (a cold start, for a test)")
    a = ap.parse_args()
    __import__("voice_ready").require(a.video, __file__)  # stage 0 of the voice lock (standard/VOICE_LOCK.md): facts, cold read, bites, names stamped
    cfg = load_config(None, video_config(a.video))
    if a.plain:
        cfg["tts"]["plain_names"] = list(a.plain)
    if a.language_code:
        cfg["tts"]["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "language_code": a.language_code}
    if a.dict:
        cfg["tts"]["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "pronunciation_dictionaries": [
            {"id": d.split(":")[0], **({"version": d.split(":")[1]} if ":" in d else {})} for d in a.dict]}
    ctx = Ctx(a.video, cfg)
    beats = [b for b in dj_script.load(ctx)["beats"] if b.get("voice") and not b.get("hold")]
    ids = [b["id"] for b in beats]
    i0, i1 = ids.index(a.first), ids.index(a.last)
    span = beats[i0:i1 + 1]
    texts = [voice_text(cfg.get("tts", {}), b["voice"]).strip() for b in span]   # the names table's respellings (tools/sound/names.json)
    text = " ".join(texts)
    prev = beats[i0 - 1]["voice"] if i0 and not a.no_prev else None
    if a.prev_text is not None:
        prev = a.prev_text or None
    # the lines before get the names table and --say too (a name sent as written in the lines before, ahead of the line's respelled one,
    # pulls every take of the line into the foreign pronunciation)
    nb = a.before
    if a.before and a.before_min_s:      # the lines before reach the warm minimum
        while i0 - nb > 0 and sum(len(b["voice"].split()) for b in beats[i0 - nb:i0]) / 3.0 < a.before_min_s:
            nb += 1
    before = " ".join(voice_text(cfg.get("tts", {}), b["voice"]).strip() for b in beats[max(0, i0 - nb):i0]) if a.before else ""
    # the video's first section has no line before it: the house warm-up is voiced there instead and cut away the same way (without it
    # the opening sits under the rest of its own take; the unspoken lead_in alone does not hold it; standard/VOICE_LOCK.md "The opening")
    warmup = a.warmup if a.warmup is not None else cfg["tts"]["elevenlabs"].get("warmup", "")
    if a.before and i0 == 0 and warmup and not a.prev_text:
        before = warmup.strip()
    elif a.before and a.before_min_s and warmup and not a.prev_text and len(before.split()) / 3.0 < a.before_min_s:
        before = (warmup.strip() + " " + before).strip()      # the script ran out of lines before the warm minimum: the warm-up in front
    if before:
        print(f"lines before the span: {nb if i0 else 0} ({len(before.split())} words, ~{len(before.split()) / 3.0:.0f} s at 3 words/s)")
    if before:
        prev = None           # nothing unspoken before the section; dj.tts.elevenlabs opens it with the house lead_in
    nxt_full = beats[i1 + 1]["voice"].strip() if i1 + 1 < len(beats) else "And that's it."
    if a.tail is not None:
        nxt_full = a.tail
    head = " ".join(nxt_full.split()[:3])
    rest = nxt_full[len(head):].strip() or None
    pdir = ctx.build / "voice" / "patch"
    raw_dir = pdir / "span_raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    stem = a.name or f"{a.first}-{a.last}"   # variants of one span side by side: give each its own k range too (the per-line files are <beat>_<k>)
    out = pdir / f"samples_{stem}"
    out.mkdir(exist_ok=True)
    rms = lambda v: float(np.sqrt(np.mean((v / 32768) ** 2))) + 1e-12  # noqa: E731
    db = lambda x, t: 20 * np.log10(rms(x[max(0, int(t * SR)):int((t + 0.01) * SR)]))  # noqa: E731
    # the span as it is now, and the narration around it (build/beats.json: the narration's own beat slots)
    tempo = float(cfg["tts"].get("tempo", 1.0))
    old = {b["id"]: b for b in json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]} \
        if (ctx.build / "beats.json").exists() else {}
    # a beat the old narration never had (a rebuilt script's new line) has no "now" to compare
    if old and (ctx.build / "voice" / a.context).exists() and a.first in old and a.last in old:
        nar = read_wav(ctx.build / "voice" / a.context).astype(np.float64)
        s0, s1 = old[a.first]["start"], old[a.last]["voice_end"]
        now = nar[int(s0 * SR):int(s1 * SR)]
        pre = nar[int((s0 - a.around) * SR):int(s0 * SR)]
        nxt_start = old[ids[i1 + 1]]["start"] if i1 + 1 < len(ids) and ids[i1 + 1] in old else s1 + 0.3
        post = nar[int(nxt_start * SR):int((nxt_start + a.around) * SR)]
        gap = np.zeros(int(max(0.0, nxt_start - s1) * SR))
        write_wav(out / f"{stem}_0_now.wav", np.round(np.clip(np.concatenate([pre, now, gap, post]), -32768, 32767)).astype(np.int16))
    else:   # no narration yet (a new video's names test before its voice, standard/VOICE_LOCK.md stage 0): the takes alone, nothing around them
        now = pre = post = gap = np.zeros(0)
    print(f"span {a.first}-{a.last}: {len(text)} characters (+ head {head!r}); now {len(now) / SR:.2f} s")
    for k in range(a.k0, a.k1 + 1):
        raw = raw_dir / f"{stem}_{k}.wav"
        # a take on disk is re-used only while it says this span's words: the cache is keyed by stem and seed, not by the text
        # (older takes of the same span and seed would be picked up for new words and fail the assert below)
        if raw.exists() and raw.with_suffix(".align.json").exists():
            old_al = json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8"))
            if not "".join(old_al["characters"]).startswith(text):
                print(f"take {k}: made on older words, made again")
                for f in [raw, raw.with_suffix(".align.json")] + sorted(raw_dir.glob(f"{raw.stem}_span*")):
                    f.unlink()
        if not raw.exists():
            tcfg = dict(cfg["tts"])
            tcfg["elevenlabs"] = {**cfg["tts"]["elevenlabs"], "seed": a.seed + k}
            sent = text
            sent_before = before
            for pair in a.say:
                word, say = pair.split("=", 1)
                assert word in sent, f"--say {pair}: {word!r} is not in the span"
                sent = sent.replace(word, say)
                sent_before = sent_before.replace(word, say)
            sent_all = f"{sent_before} {sent} {head}" if before else f"{sent} {head}"
            al, _ = elevenlabs(tcfg, sent_all, prev, rest, raw)
            if before:   # the lines before are cut away: the take's alignment starts at the span; the audio keeps them (lo finds the cut)
                n0 = len(sent_before) + 1
                al = {"characters": al["characters"][n0:], "character_start_times_seconds": al["character_start_times_seconds"][n0:],
                      "character_end_times_seconds": al["character_end_times_seconds"][n0:], "before_end": al["character_end_times_seconds"][n0 - 2]}
            for pair in a.say:  # the stored take spells the script again: the respelled characters give way to the word's, timed evenly
                word, say = pair.split("=", 1)
                chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
                i = "".join(chars).find(say)
                while i >= 0:
                    t0, t1, n = st[i], en[i + len(say) - 1], len(word)
                    chars[i:i + len(say)] = list(word)
                    st[i:i + len(say)] = [t0 + (t1 - t0) * q / n for q in range(n)]
                    en[i:i + len(say)] = [t0 + (t1 - t0) * (q + 1) / n for q in range(n)]
                    i = "".join(chars).find(say, i + n)
            raw.with_suffix(".align.json").write_text(json.dumps(al), encoding="utf-8")
        al = json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8"))
        x = read_wav(raw).astype(np.float64)
        chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
        assert "".join(chars).startswith(text), "".join(chars)[:80]
        # the span's edges, as voice_context: back to the silence before the first sound; past the last word to the head's first sound
        t = st[0]
        if "before_end" in al:   # the quietest 10 ms between the lines before and the span's first character
            g = np.arange(al["before_end"], max(al["before_end"] + 0.011, st[0] - 0.01), 0.005)
            lo = int(min(g, key=lambda q: db(x, q)) * SR)
            # ...but never after the first word's own onset (soft starts like "That's" or "Somebody" are lost when the quietest
            # 10 ms falls inside the word): dj's onset search walks back from the first character to where its sound starts
            # The character times run late, so before_end can sit inside the first word ("Tha-" lost again): the real pause
            # between the lines before and the span is read from the audio, the way dj tts cuts between beats (gap_between)
            xdb = frame_db(x)
            fl = quiet_floor(xdb)
            onset = sound_start(x, st[0], al["before_end"] - 0.5, xdb, fl)
            pause = gap_between(xdb, fl, al["before_end"] - 0.3, st[0], al["before_end"] - 0.6)[1]
            lo = min(lo, onset, pause)
        else:
            while t > 0 and db(x, t) > -60:
                t -= 0.01
            lo = int(max(0.0, t - 0.02) * SR)
        t = en[len(text) - 1] - 0.25
        while db(x, t) > -65 and t < len(x) / SR - 0.02:
            t += 0.01
        while db(x, t) < -45 and t < len(x) / SR - 0.02:
            t += 0.01
        hi = int((t - 0.06) * SR)
        xdb5 = frame_db(x)
        fl5 = quiet_floor(xdb5)

        def pause_mid(e_prev, s_next, w_prev):
            """the middle of the real pause between two lines: gap_between's longest quiet run near the character times; they can
            run 150-250 ms late (the window then starts after the pause and the cut falls inside the next word's /h/), so with no run
            there the search reaches 0.45 s back. None when the lines run together"""
            for tw, back in ((w_prev, 0.25), (None, 0.45)):
                ce, cs = gap_between(xdb5, fl5, e_prev, s_next, tw, back=back)
                if cs - ce >= int(0.02 * SR):
                    return (ce + cs) // 2
            return None
        # the span's end: the middle of the pause before the head of the next line (60 ms before the head's first sound past -45 dB
        # can cut a final t: a quiet frame inside the word stops the walk)
        if len(chars) > len(text) + 1:
            last0 = text.rstrip().rfind(" ") + 1
            m_ = pause_mid(en[len(text) - 1], st[len(text) + 1], st[last0] if last0 else None)
            if m_ is not None and m_ > lo + int(0.2 * SR):
                hi = m_
        # the cuts between lines: the quietest 10 ms between one line's last character and the next one's first
        def band_db(t, n=int(0.01 * SR)):   # the 4-12 kHz level of the 10 ms at t (numpy only: this venv has no scipy)
            s = x[max(0, int(t * SR)):max(0, int(t * SR)) + n] / 32768
            if len(s) < n:
                return -120.0
            w = np.hanning(n)
            X = np.abs(np.fft.rfft(s * w)) ** 2
            f = np.fft.rfftfreq(n, 1 / SR)
            return float(10 * np.log10(2 * X[(f >= 4000) & (f <= 12000)].sum() / (n * (w ** 2).sum()) + 1e-12))
        cuts, pos = [lo], 0
        for j in range(len(texts) - 1):
            pos += len(texts[j]) + 1
            e_prev, s_next = en[pos - 2], st[pos]
            # never inside the next line's first word (a quiet first word is lost when the quietest 10 ms falls after its start)
            a0, a1 = max(e_prev - 0.05, lo / SR), min(max(s_next - 0.01, e_prev + 0.02), hi / SR)
            grid = np.arange(a0, max(a0 + 0.011, a1), 0.005)
            best = min(grid, key=lambda g: db(x, g))
            # the cut goes in the MIDDLE of the real pause between the lines, read from the audio as dj tts reads it (gap_between:
            # the longest quiet run near the character times, which run 30-60 ms late): the quietest 10 ms before the next line's first
            # character can sit inside a soft onset ("Your" at -36 dB, "In"), which then ends the previous line's piece. With no quiet
            # run (the lines run together) the quietest point
            line0 = pos - 1 - len(texts[j])
            w_prev = st[line0 + texts[j].rstrip().rfind(" ") + 1] if " " in texts[j].strip() else None
            m_ = pause_mid(e_prev, s_next, w_prev)
            if m_ is not None and lo + int(0.05 * SR) < m_ < hi:
                best = m_ / SR - 0.005
            # ...and never inside the last word's hiss (a final "six"): a cut still on sound moves on to the first 10 ms under -45 dB
            # broadband and -50 dB in 4-12 kHz before the next line (an /s/ sits in the band a loudness check misses)
            if db(x, best) > -45 or band_db(best) > -50:
                later = [g for g in grid if g > best and db(x, g) <= -45 and band_db(g) <= -50]
                if later:
                    best = later[0]
            cuts.append(int((best + 0.005) * SR))
        cuts.append(hi)
        pos = 0
        for j, b in enumerate(span):
            piece = x[cuts[j]:cuts[j + 1]].copy()
            f = int(0.01 * SR)
            piece[:f] *= np.linspace(0, 1, f)
            piece[-f:] *= np.linspace(1, 0, f)
            dst = pdir / f"{b['id']}_{k}.wav"
            write_wav(dst, np.round(piece).astype(np.int16))
            off = cuts[j] / SR
            n = len(texts[j])
            dst.with_suffix(".align.json").write_text(json.dumps({
                "characters": chars[pos:pos + n],
                "character_start_times_seconds": [v - off for v in st[pos:pos + n]],
                "character_end_times_seconds": [v - off for v in en[pos:pos + n]]}), encoding="utf-8")
            pos += n + 1
        y = x[lo:hi]
        # the listening file at the speed and pauses the take will have in the video (raw 1.0x takes don't sound like the video's
        # speed): voice_patch's own steps, the continuous mode's pauses, then [tts] tempo
        ys = tighten_pauses(np.round(np.clip(y, -32768, 32767)).astype(np.int16), cfg["tts"].get("max_pause", 0))
        if abs(tempo - 1.0) > 1e-3:
            ys = all_tempo({"tempo": tempo}, [{"voice": text}], [ys])[0]
        ys = ys.astype(np.float64)
        z = ys * (rms(now) / rms(ys)) if len(now) else ys
        if np.abs(z).max() > 0.891 * 32767:
            z = limit(z)
        f = out / f"{stem}_{k}.wav"
        write_wav(f, np.round(np.clip(np.concatenate([pre, z, gap, post]), -32768, 32767)).astype(np.int16))
        # where the take sits in it (autopick's in-place accent ear): s0 = the file's start on the narration's clock
        f.with_suffix(".place.json").write_text(json.dumps({"pre": len(pre) / SR, "take": len(z) / SR, "gap": len(gap) / SR,
                                                            "post": len(post) / SR,
                                                            "s0": (s0 - len(pre) / SR) if len(now) else None}), encoding="utf-8")
        span_wav = raw_dir / f"{stem}_{k}_span.wav"
        write_wav(span_wav, np.round(np.clip(y, -32768, 32767)).astype(np.int16))
        rh = rhotic_score(span_wav, {"alignment": {"characters": chars[:len(text)],
                                                    "character_start_times_seconds": [v - lo / SR for v in st[:len(text)]],
                                                    "character_end_times_seconds": [v - lo / SR for v in en[:len(text)]]}})
        print(f"  take {k}: {len(z) / SR:5.2f} s at {tempo}x (now {len(now) / SR:.2f})  r-dip {rh['median_dip']} Hz ({rh['share_over_400']:.0%} over 400)"
              + ("  NON-RHOTIC (British for sure)" if rh["median_dip"] < 400 else "") + f"  -> {f.name}")
    print("listening files ->", out)


if __name__ == "__main__":
    main()
