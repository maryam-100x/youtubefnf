"""Takes of whole voice sections for the creator to pick by ear: an accent slip lives in a whole request, not in one line, so the
whole section has to come out right. A long video's narration is rendered in sections (dj tts, [tts] mode = "continuous": one
ElevenLabs request per section, linked to the sections before by request id), so a British section is re-rendered whole, exactly as it
was made: the same text, voice, model, settings and request-id links, only the seed new.

Name each section by any beat in it. Writes, per section, <out>/<mm>m<ss>_<first>-<last>_0_now.wav (the current render) and _1 ... _n
(the takes) for listening: edges trimmed, pauses as the narration's ([tts] max_pause), levelled to the current render. The raw takes and
their timestamps go to <out>/raw/ in the cache's own format, so a picked take drops into build/voice/cache under the section's key
(--use) and the next `dj tts` cuts it into beats like any other section. Whisper (small.en) reads every take back against the script.

Every take is also scored for rhoticity (rhotic.py: a take that drops the r after vowels is British for sure; one that keeps it still goes to
the ear: a take can keep its r's and still sound British). When the text itself pulls the accent (a line full of British places and
royal titles: every render British), --tag puts a direction in front of the text (the model takes free-text tags) and
--stability overrides the voice's stability; the tag's characters are cut from the stored timestamps, so the cached section still spells
the script. New takes number on from the ones already there.

  cd tools && PIPE voice/section_takes.py ../videos/<video> <out dir> S12 S14 S18 [--n 4] [--seed 7300] [--tag "[American accent]"] [--stability 0.65]
  cd tools && PIPE voice/section_takes.py ../videos/<video> <out dir> --use S12=2 S14=1   (the old cached render kept as .orig)"""
import argparse
import re
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from beat_takes import check  # noqa: E402
from dj import script as dj_script  # noqa: E402
from dj import tts  # noqa: E402
from dj.__main__ import video_config  # noqa: E402
from dj.core import SR, Ctx, load_config, read_wav, write_wav  # noqa: E402
from rhotic import score as rhotic_score  # noqa: E402


def sections(ctx, tcfg, leads=False):
    """The narration's sections as `dj tts` makes them: [(beat ids, text, cache wav)], in order (the same breaks as tts.run); leads=True
    adds each section's lines before (dj tts voices a section after them in the same request and keys its cache on both)."""
    all_beats = dj_script.load(ctx)["beats"]
    beats = [b for b in all_beats if not b.get("hold")]
    breaks = {i for i, b in enumerate(beats) if i and ((all_beats[all_beats.index(b) - 1].get("hold") and
                                                        not all_beats[all_beats.index(b) - 1].get("join")) or
                                                       (ctx.fmt != "short" and (b.get("vis") or {}).get("chapter")))}
    breaks |= {i for i, b in enumerate(beats) if i and b["id"] in set(tcfg.get("fresh_at", []))}   # as tts.run (fresh_at: a new request)
    groups = tts.section_groups([tts.voice_text(tcfg, b["voice"]) for b in beats], breaks, tcfg.get("section_words", 150))
    cache = ctx.path("voice", "cache", "x").parent
    before_n = int(tcfg.get("section_before", 2))
    out = []
    for g in groups:
        text = " ".join(tts.voice_text(tcfg, beats[i]["voice"]).strip() for i in g)
        lead = " ".join(tts.voice_text(tcfg, beats[i]["voice"]).strip() for i in range(max(0, g[0] - before_n), g[0])) if before_n and g[0] else ""
        wav = cache / f"sec_{tts.cache_key(tcfg, f'{lead} {text}' if lead else text)}.wav"
        out.append(([beats[i]["id"] for i in g], text, wav, lead) if leads else ([beats[i]["id"] for i in g], text, wav))
    return out


def listen(x, tcfg, target=None):
    """A take as it will sound in the narration: edges trimmed, long pauses tightened, at the current render's level."""
    x = tts.tighten_pauses(tts.trim_edges(x), tcfg.get("max_pause", 0.16))
    v = tts.voiced_db(x)
    if target is not None and v is not None:
        x = np.clip(x.astype(np.float64) * 10 ** ((target - v) / 20), -32768, 32767).astype(np.int16)
    return x


def main():
    __import__("voice_lock").guard_argv(__file__, when="--use")  # the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("beats", nargs="*")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--seed", type=int, default=7300)
    ap.add_argument("--use", nargs="*", default=[], help="BEAT=N: take N becomes the cached render of BEAT's section")
    ap.add_argument("--tag", default="", help='a direction tag sent in front of the text, e.g. "[American accent]"')
    ap.add_argument("--stability", type=float, default=None)
    ap.add_argument("--say", nargs="*", default=[], help="WORD=SAYING respellings sent to ElevenLabs for these takes only, the same length "
                    "(a name said wrong: Maria=María); the cache key and captions keep the script's spelling")
    ap.add_argument("--link-ids", nargs="*", default=None, help="request ids to link instead of the sections before (a first section "
                    "has nothing before it; linked to the American takes of a later section it has their accent to follow)")
    ap.add_argument("--cold", action="store_true", help="a long-form take without its lines before in the request (a test only: "
                    "it starts cold, and dj tts can't use it: the section's cache is keyed on the lines before too)")
    ap.add_argument("--no-links", action="store_true", help="send no request ids of the sections before (a take free of an earlier "
                    "section's accent-pulling context, one of the versions that differ for the ear)")
    ap.add_argument("--check-model", default="small.en", help="the Whisper model that reads each take back (tiny.en when the PC is loaded: small.en can take 10+ min a take with the CPU shared; the ear decides anyway)")
    a = ap.parse_args()
    __import__("voice_ready").require(a.video, __file__)  # stage 0 of the voice lock: facts, cold read, bites, names stamped on this script
    cfg = load_config(None, video_config(a.video))  # the script's CONFIG: lines, as dj applies them
    ctx = Ctx(a.video, cfg)
    tcfg = ctx.cfg["tts"]   # the Shorts profile ([tts.short]) is applied in ctx.cfg: cfg["tts"] would re-voice a Short in the long-form voice
    secs = sections(ctx, tcfg, leads=True)
    # takes linked by request id only come out exhausted and breathy, so a take is voiced as dj tts voices its section: its lines before
    # ([tts] section_before) open the same request, the house lead_in before them, and are cut away; the raw take keeps the whole request
    # (the cache's format, "lead" = where the section starts), and <take>.own.wav holds the section alone for listening and the screens.
    # --cold sends the section alone (a test only).
    out, raw = Path(a.out), Path(a.out) / "raw"
    where = lambda bid: next(k for k, s in enumerate(secs) if bid in s[0])  # noqa: E731
    if a.use:
        for u in a.use:
            bid, n = u.split("=")
            ids, text, wav, lead = secs[where(bid)]
            src = next(raw.glob(f"*_{ids[0]}-{ids[-1]}_{n}.wav"))
            meta = json.loads(src.with_suffix(".align.json").read_text(encoding="utf-8"))
            if meta["text"] != (f"{lead} {text}" if lead else text):
                raise SystemExit(f"{src.name}: its text isn't the section's request any more (the script changed, or a --cold take)")
            for f in (wav, wav.with_suffix(".align.json")):
                if f.exists() and not f.with_name(f.name + ".orig").exists():  # a changed line has no render to keep
                    shutil.copy2(f, f.with_name(f.name + ".orig"))
            shutil.copy2(src, wav)
            shutil.copy2(src.with_suffix(".align.json"), wav.with_suffix(".align.json"))
            print(f"  {ids[0]}-{ids[-1]}: take {n} is now the cached render ({wav.name}; the old one kept as .orig)")
        return
    # the request ids of every section before, as continuous_elevenlabs links them (the last three are sent)
    rids = [json.loads(w.with_suffix(".align.json").read_text(encoding="utf-8")).get("request_id") if w.with_suffix(".align.json").exists()
            else None for _, _, w, _ in secs]
    beats = {b["id"]: b for b in json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]}
    out.mkdir(parents=True, exist_ok=True)
    raw.mkdir(exist_ok=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(a.check_model, device="cpu", compute_type="int8")
    report = json.loads((out / "sections.json").read_text(encoding="utf-8")) if (out / "sections.json").exists() else {}
    for bid in a.beats:
        k = where(bid)
        ids, text, wav, lead = secs[k]
        if a.cold:
            lead = ""
        t0 = beats[ids[0]]["start"]
        name = f"{int(t0 // 60):02d}m{int(t0 % 60):02d}_{ids[0]}-{ids[-1]}"
        if wav.exists():
            now = read_wav(wav)
            target = tts.voiced_db(listen(now, tcfg))
            write_wav(out / f"{name}_0_now.wav", listen(now, tcfg))
        else:  # a changed line: no render of the new text yet, so no take 0 is paid for (dj tts would voice it once, unrespelled);
            # the takes are levelled to the first one
            print(f"  {ids[0]}-{ids[-1]}: no cached render of this text yet: new takes only, levelled to the first")
            target = None
        # linked as dj tts links it: never across a fresh_at start (a fresh section's takes would follow an earlier request's accent,
        # though the narration itself voices them unlinked)
        fresh = set(tcfg.get("fresh_at", []))
        f0 = max([i for i in range(k + 1) if secs[i][0][0] in fresh] or [0])
        prev = [] if a.no_links else (a.link_ids[-3:] if a.link_ids else [r for r in rids[f0:k] if r][-3:])
        print(f"\n{name}: {len(ids)} beats, {len(text.split())} words, " +
              (f"after its {len(lead.split())} words before" if lead else f"linked to {len(prev)} request(s) before"))
        if lead:
            prev = []   # as dj tts: the lines before carry the context, no request ids
        old = report.get(name, {}).get("takes", [{"take": 0, "file": f"{name}_0_now.wav", "note": "the current render"}])
        rows = list(old)
        j0 = max(r["take"] for r in rows)
        for j in range(j0 + 1, j0 + a.n + 1):
            t = json.loads(json.dumps(tcfg))
            t["elevenlabs"]["seed"] = a.seed + 10 * k + j
            if a.stability is not None:
                t["elevenlabs"].setdefault("voice_settings", {})["stability"] = a.stability
            # no --model option: the voice model never changes (an older model sounds like computer TTS)
            dst = raw / f"{name}_{j}.wav"
            if a.tag and a.tag in t["elevenlabs"].get("prefix", ""):  # the default prefix already carries "[American accent]"
                print(f"  {a.tag} is in the [tts.elevenlabs] prefix already: not sent twice"); a.tag = ""
            req = f"{lead} {text}" if lead else text
            sent = f"{a.tag} {req}" if a.tag else req
            for pair in a.say:
                word, say = pair.split("=", 1)
                assert len(word) == len(say), f"--say {pair}: the respelling must keep the length (the timestamps map 1:1)"
                sent = re.sub(rf"(?<!\w){re.escape(word)}(?!\w)", say, sent)
            al, rid = tts.elevenlabs(t, sent, None, None, dst, prev_ids=None if lead else prev)
            for pair in a.say:  # the stored take spells the script again (dj tts checks the timestamps spell the text)
                word, say = pair.split("=", 1)
                if isinstance(al, dict) and "characters" in al:
                    al["characters"] = list("".join(al["characters"]).replace(say, word))
            if a.tag:  # the tag's characters (and the space after it) out of the timestamps: the stored take spells the script
                cut = len(a.tag) + 1
                if "".join(al["characters"][cut:]) != req:
                    print(f"  take {j}: the timestamps don't spell tag + text; stored as returned")
                else:
                    al = {kk: (v[cut:] if isinstance(v, list) else v) for kk, v in al.items()}
            off = len(lead) + 1 if lead else 0
            dst.with_suffix(".align.json").write_text(json.dumps({"alignment": al, "request_id": rid, "text": req, "lead": off}), encoding="utf-8")
            x = read_wav(dst)
            own = dst
            if off:  # the section alone, cut where dj tts cuts it: the real pause after the lines before
                st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
                xdb = tts.frame_db(x)
                s = tts.gap_between(xdb, tts.quiet_floor(xdb), en[off - 2], st[off], st[req[:off - 1].rfind(" ") + 1])[1]
                x = x[s:]
                al = {kk: ([u - s / SR for u in v[off:]] if kk.startswith("character_") and kk.endswith("seconds") else
                           v[off:] if isinstance(v, list) else v) for kk, v in al.items()}
                own = dst.with_name(dst.stem + ".own.wav")
                write_wav(own, x)
                own.with_suffix(".align.json").write_text(json.dumps({"alignment": al, "request_id": rid, "text": text}), encoding="utf-8")
            weak = [f"{w} -{d:.0f} dB" for w, _, d in tts.swallowed(x, al)]
            f = out / f"{name}_{j}.wav"
            y = listen(x, tcfg, target)
            if target is None:
                target = tts.voiced_db(y)
            write_wav(f, y)
            heard, missing, low = check(model, f, text)
            rh = rhotic_score(own, {"alignment": al})
            first = " ".join(heard.split()[:3])
            print(f"  take {j}: {len(y) / SR:5.2f} s  seed {t['elevenlabs']['seed']}  " + ("OK" if not missing else "MISSING " + " ".join(missing)) +
                  f"  r-dip {rh['median_dip']} Hz ({rh['share_over_400']:.0%} over 400)" + ("  NON-RHOTIC" if rh["median_dip"] < 400 else "") +
                  f"  starts: {first!r}" + (f"  weak endings: {', '.join(weak)}" if weak else ""))
            rows.append({"take": j, "file": f.name, "seconds": round(len(y) / SR, 2), "seed": t["elevenlabs"]["seed"], "request_id": rid,
                         "tag": a.tag, "links": len(prev), "stability": t["elevenlabs"].get("voice_settings", {}).get("stability"), "rhotic_dip": rh["median_dip"],
                         "rhotic_share": rh["share_over_400"], "missing": missing, "weak_endings": weak, "unsure": low, "heard": heard})
        report[name] = {"beats": ids, "text": text, "takes": rows}
        (out / "sections.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
