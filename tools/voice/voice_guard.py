"""The voice guard: screens a narration for the voice faults that cost a listener's trust, re-voices the flagged sections by itself and
keeps the take closest to the creator's approved voice. What eats a review is finding where the voice turns British, until when, and
where its tone changes into a different one; the guard finds those first. The creator's ear stays the judge of the video; the guard
decides what reaches it.

Flags, per section and beat with times (calibrated on the creator's own verdicts by voice_guard_calib.py; the numbers live in the
model file, MODEL below):
  ACCENT         a stretch that sounds British: a probe on the accent and speaker embeddings (voice_guard_embed.py, both trained on the
                 creator's flagged spans against their approved narrations) plus CommonAccent's P(UK) (P(UK) alone until the
                 reference holds enough flagged accent spans: voice_guard_calib.py); on a take with ElevenLabs timestamps also
                 rhotic.py's r (a median dip under 400 Hz = British for sure)
  CLOSE/DEEP     deep and close, as if leaning into the mic: the beat's pitch, low band, presence and tilt against the narration's own
                 baseline and the approved voice (voice_guard_tone.py)
  WHISPER        whispery and mysterious: voiced share, CPP, harmonicity down; also any content word with almost no voiced energy
  TONE JUMP      the voice of a beat differs from the beat before it (the ElevenLabs request changed its mind, or a beat was patched in
                 alone)
  TIRED OPENING  the first sentence of a request starts breathy and low (voice_check.py's OPENING, if present)
  SWALLOWED WORD a content word 4+ dB under the narration's words (7+ at a sentence's end), or a final consonant barely released

  cd tools && PIPE voice/voice_guard.py ../videos/<video>      (build/voice/narration.wav + the build's beats and the edit's
                                                               words.json from video.toml)
  cd tools && PIPE voice/voice_guard.py <narration.wav> --words <words.json> [--beats <beats.json>]
      [--out <report.md>] [--force] [--retake [--cap 3000] [--max-takes 3] [--seed 8300] [--dry]]

--retake (a video dir only): every flagged section is voiced again whole, section_takes.py's way (same text, settings and links, a new
seed; never a patch, never EQ or gain: regenerate, never process), each take screened with the same measures, the best one kept
(section_takes.py --use), then `dj tts`, `dj captions` and sync_words.py rebuild the narration and the word times, and the guard screens
the result once more. Credit-aware: the balance from voice_credits.py first, a take costs about 0.46 credits a character (the model
with the prefix; <MEDIA>/voice/elevenlabs_usage.csv logs every call), it stops at --cap credits and never voices a section more than
--max-takes times. The takes stay in VIDEOS/<video>/review/voice_guard_takes/ for the creator's ear. Exits 1 while anything is flagged.

The model (MODEL) is built from the creator's own takes, never shipped: fill <MEDIA>/voice/guard/ at setup (voice_guard_calib.py's
docstring has the layout), then
  ACCENT tools/voice/voice_guard_embed.py <MEDIA>/voice/guard
  PIPE tools/voice/voice_guard_tone.py <MEDIA>/voice/guard
  PIPE tools/voice/voice_guard_calib.py
Without it the guard stops and prints these commands."""
import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import MEDIA, PY_ACCENT, PY_PIPE, TOOLS, VIDEOS  # noqa: E402
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))   # tools/: the dj package
import voice_guard_tone as tone  # noqa: E402

GT = PY_PIPE
ACCENT_PY = PY_ACCENT
GUARD_DIR = MEDIA / "voice" / "guard"   # the creator's approved and flagged takes (voice_guard_calib.py builds the model from them)
MODEL = GUARD_DIR / "voice_guard_model.json"
BUILD = ("the voice guard has no model yet: it is built from the creator's own takes.\n"
         f"  1. put approved narrations (wav + .words.json) in {GUARD_DIR / 'approved'} (Shorts voice: approved/short/), and takes\n"
         f"     with faults heard in them (wav + .spans.json) in {GUARD_DIR / 'flagged'} (voice_guard_calib.py's docstring has the layout)\n"
         f"  2. ACCENT tools/voice/voice_guard_embed.py {GUARD_DIR}\n"
         f"  3. PIPE tools/voice/voice_guard_tone.py {GUARD_DIR}\n"
         "  4. PIPE tools/voice/voice_guard_calib.py\n"
         "  (ACCENT and PIPE: the two pythons `python tools/common/paths.py` prints)")


def load_model():
    """The guard's model (MODEL), or a stop with the commands that build it."""
    if not MODEL.exists():
        raise SystemExit(BUILD)
    return json.loads(MODEL.read_text(encoding="utf-8"))


UK = ("england", "scotland", "wales", "ireland", "australia", "newzealand")
CREDITS_PER_CHAR = 0.46
FUNCTION = {"a", "an", "the", "to", "of", "in", "on", "at", "it", "its", "it's", "is", "was", "and", "but", "or", "so", "he", "she", "they",
            "we", "you", "i", "him", "her", "his", "for", "with", "as", "by", "be", "been", "that", "this", "than", "then", "from", "up",
            "out", "me", "my", "our", "your", "their", "them", "are", "were", "has", "had", "have", "do", "did", "not", "no", "just",
            "he's", "you're", "we're", "i'm", "that's", "there", "what", "when", "how", "why", "who", "if", "into", "about", "like"}
KINDS = ["ACCENT", "ACCENT?", "CLOSE/DEEP", "WHISPER", "TONE JUMP", "TIRED OPENING", "SWALLOWED WORD"]


# ---------- the ears ----------
def embed_json(wav, force=False):
    """voice_guard_embed.py's cache for a wav (made in the accent venv when stale)."""
    out = wav.with_name(wav.name + ".guard_embed.json")
    if force or not out.exists():
        subprocess.run([str(ACCENT_PY), str(HERE / "voice_guard_embed.py"), str(wav)] + (["--force"] if force else []),
                       check=True, capture_output=True)
    d = json.loads(out.read_text(encoding="utf-8"))
    st = wav.stat()
    if d.get("stamp") != f"{st.st_size}-{int(st.st_mtime)}-v1":
        subprocess.run([str(ACCENT_PY), str(HERE / "voice_guard_embed.py"), str(wav)], check=True, capture_output=True)
        d = json.loads(out.read_text(encoding="utf-8"))
    return d


def probe(model, X):
    Z = (np.asarray(X) - np.array(model["mu"])) / np.array(model["sd"])
    return 1 / (1 + np.exp(-(Z @ np.array(model["w"]) + model["b"])))


def smooth(v, k=5):
    v = np.asarray(v, float)
    out = np.copy(v)
    h = k // 2
    for i in range(len(v)):
        out[i] = np.median(v[max(0, i - h): i + h + 1])
    return out


def accent_scores(E, M, voice, words=None):
    """Per window: the guard's accent score in 0-1 (the mean of the two probes and P(UK), smoothed over 5 windows).
    With `words`, a window that is mostly not speech (under 40% of it inside a word) is left out before the smoothing: an embedding of
    silence is no voice (three windows over a 6-s HOLD can score 0.78 and make a 'hard British' beat whose own speech scores
    0.005-0.25)."""
    if not E["t"]:
        return np.zeros(0), np.zeros(0)
    labels = E["labels"]
    p_uk = np.array([sum(p[labels.index(k)] for k in UK) for p in E["p"]])
    pa = probe(M["accent_probe_acc"], E["acc"])
    ps = probe(M["accent_probe_spk"], E["spk"])
    w = M.get("accent_weights", {"acc": 1.0, "spk": 1.0, "p_uk": 1.0})
    s = (w["acc"] * pa + w["spk"] * ps + w["p_uk"] * p_uk) / (w["acc"] + w["spk"] + w["p_uk"])
    t = np.array(E["t"]) + E["win"] / 2
    if words:
        half = E["win"] / 2
        keep = np.array([sum(max(0.0, min(c + half, x["end"]) - max(c - half, x["start"])) for x in words
                             if x["end"] > c - half and x["start"] < c + half) >= 0.4 * E["win"] for c in t], bool)
        t, s = t[keep], s[keep]
    return t, smooth(s)


def stretches_over(ts, sc, thr, min_s):
    """Where a window score stays over thr for min_s seconds or more: [(t0, t1)] (window centres; a window is 2 s)."""
    out, start, prev = [], None, None
    for t, v in zip(ts, sc):
        if start is not None and t - prev > 1.0:   # a gap in the windows (silence left out): a stretch never spans it
            if prev + 1.0 - start >= min_s:
                out.append((start, prev + 1.0))
            start = None
        if v > thr and start is None:
            start = t - 1.0
        if v <= thr and start is not None:
            if prev + 1.0 - start >= min_s:
                out.append((start, prev + 1.0))
            start = None
        prev = t
    if start is not None and prev + 1.0 - start >= min_s:
        out.append((start, prev + 1.0))
    return out


def self_accent(E):
    """Each window's accent embedding against the narration's own mean, as a smoothed robust z: a stretch that sounds unlike the rest."""
    if len(E["t"]) < 8:
        return np.zeros(0)
    A = np.array(E["acc"])
    c = A.mean(0)
    c /= np.linalg.norm(c)
    d = 1 - A @ c
    med = float(np.median(d))
    mad = max(1.4826 * float(np.median(np.abs(d - med))), 1e-6)
    return smooth((d - med) / mad)


def window_mean(ts, sc, t0, t1):
    m = (ts >= t0) & (ts < t1)
    if not m.any():  # a beat shorter than the hop: the nearest window
        if not len(ts):
            return float("nan")
        m = np.abs(ts - (t0 + t1) / 2) <= 1.25
    return float(sc[m].mean()) if m.any() else float("nan")


# ---------- the words ----------
def load_words(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    ws = d["words"] if isinstance(d, dict) else d
    return [{"w": w["w"], "start": float(w["start"]), "end": float(w["end"]), "beat": w.get("beat")} for w in ws if w.get("w")]


def words_from_align(al, offset=0.0):
    """Words with times from ElevenLabs character timestamps (a take's .align.json)."""
    al = al.get("alignment", al)
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    out, i = [], 0
    while i < len(ch):
        if ch[i].isspace():
            i += 1
            continue
        j = i
        while j < len(ch) and not ch[j].isspace():
            j += 1
        out.append({"w": "".join(ch[i:j]), "start": st[i] + offset, "end": en[j - 1] + offset, "beat": None})
        i = j
    return out


def word_rows(fr, words):
    """Per word: level (80th pct of its frames), voiced energy share, CPP; function words and words under 0.25 s carry no verdict."""
    rows = []
    for w in words:
        a, b = w["start"], w["end"]
        m = (fr["t"] >= a) & (fr["t"] < b)
        if m.sum() < 3:
            rows.append({**w, "level": None})
            continue
        lev = fr["level"][m]
        e = 10 ** (lev / 10)
        ves = float(e[fr["f0"][m] > 0].sum() / (e.sum() + 1e-12))
        bands = 10 ** (fr["bands"][m] / 10)
        hi = float(bands[:, 5:7].sum() / (bands.sum() + 1e-12))  # the share of the word's energy over 2.4 kHz: breath, not voice
        key = re.sub(r"[^a-z']", "", w["w"].lower())
        rows.append({**w, "level": float(np.percentile(lev, 80)), "ves": ves, "hi": hi, "cpp": float(np.median(fr["cpp"][m])),
                     "content": key not in FUNCTION and (b - a) >= 0.25, "final": bool(re.search(r"[.?!…][\"')\]]*$", w["w"]))})
    return rows


# ---------- the tone ----------
def z_of(s, base, ref):
    """A beat's tone as z-scores: against the narration's own baseline, and against the creator's approved voice (the model's ref) where that
    is further off in the same direction (a whole narration can be off; level and range are relative things, own baseline only)."""
    z = {}
    for k in base:
        if s is None or k not in s:
            z[k] = 0.0
            continue
        zo = (s[k] - base[k][0]) / base[k][1]
        zr = (s[k] - ref[k][0]) / ref[k][1] if ref and k in ref and k not in ("level", "f0_range") else zo
        z[k] = zr if abs(zr) > abs(zo) and np.sign(zo) == np.sign(zr) else zo
    return z


def baseline(stats_list):
    base = {}
    keys = [k for k in (stats_list[0] or {}) if k not in ("n",)]
    for k in keys:
        v = np.array([s[k] for s in stats_list if s and k in s], float)
        if not len(v):
            continue
        med = float(np.median(v))
        mad = 1.4826 * float(np.median(np.abs(v - med)))
        base[k] = (med, max(mad, 1e-6))
    return base


def tone_index(z, rule):
    return sum(w * z.get(k, 0.0) for k, w in rule["w"].items()) / sum(abs(w) for w in rule["w"].values())


def emb_dist(rows, E, M):
    """Per beat: its mean speaker embedding; how far it sits from the narration's own voice (z_self) and from the beat before (z_prev),
    as robust z-scores over the narration's beats (a chapter's cold start can sit 10 MADs from its narration's voice)."""
    if not E["t"]:
        return
    ts = np.array(E["t"]) + E["win"] / 2
    S = np.array(E["spk"])
    vecs = []
    for r in rows:
        m = (ts >= r["start"]) & (ts < r["end"])
        if not m.any():
            m = np.abs(ts - (r["start"] + r["end"]) / 2) <= 1.5
        v = S[m].mean(0) if m.any() else None
        vecs.append(v / np.linalg.norm(v) if v is not None else None)
    have = [v for v in vecs if v is not None]
    if len(have) < 4:
        return
    c = np.mean(have, 0)
    c /= np.linalg.norm(c)
    d_self = np.array([1 - v @ c if v is not None else np.nan for v in vecs])
    d_prev = np.full(len(vecs), np.nan)
    for i in range(1, len(vecs)):
        if vecs[i] is not None and vecs[i - 1] is not None:
            d_prev[i] = 1 - vecs[i] @ vecs[i - 1]
    for name, d in (("z_self", d_self), ("z_prev", d_prev)):
        ok = np.isfinite(d)
        med = float(np.median(d[ok]))
        mad = max(1.4826 * float(np.median(np.abs(d[ok] - med))), 1e-6)
        for r, x in zip(rows, d):
            r[name] = float((x - med) / mad) if np.isfinite(x) else None
            r[name.replace("z_", "d_")] = float(x) if np.isfinite(x) else None


# ---------- the screen ----------
def screen(wav, words, beats, M, sections=None, voice="long", align=None, force=False, label="", patched=()):
    """One narration (or one take): -> {"beats": [...], "words": [...], "sections": [...], "flags": n}. beats: [{id, start, end, text}]."""
    E = embed_json(wav, force)
    fr = tone.frames(tone.load(wav))
    ts, acc = accent_scores(E, M, voice, words)
    thr = M["thresholds"]
    hard = stretches_over(ts, acc, thr["accent"], thr["accent_min_s"])
    soft = stretches_over(ts, acc, thr["accent_soft"], thr["accent_min_s"])
    zsa = self_accent(E)
    soft += stretches_over(ts, zsa, thr["self_acc_z"], thr["accent_min_s"]) if len(zsa) else []
    ref = M.get("ref", {}).get(voice)
    rows = []
    for b in beats:
        if re.search(r"\dh$", b["id"]) or b["end"] - b["start"] < 0.3:  # a hold (a clip's own sound) or a stub
            continue
        s = tone.stats(fr, b["start"], b["end"])
        rows.append({"id": b["id"], "start": b["start"], "end": b["end"], "text": b.get("text", ""), "stats": s,
                     "accent": window_mean(ts, acc, b["start"], b["end"]) if len(ts) else float("nan"), "flags": []})
    base = baseline([r["stats"] for r in rows if r["stats"]]) if rows else {}
    emb_dist(rows, E, M)
    prev_z = None
    for i, r in enumerate(rows):
        z = z_of(r["stats"], base, ref) if r["stats"] else {}
        r["z"] = z
        hit = [(a, b) for a, b in hard if min(b, r["end"]) - max(a, r["start"]) > 0.3]
        if hit:
            r["flags"].append(("ACCENT", r["accent"], f"British {fmt_t(hit[0][0])}-{fmt_t(hit[-1][1])} (score {r['accent']:.2f})"))
        elif [(a, b) for a, b in soft if min(b, r["end"]) - max(a, r["start"]) > 0.3]:
            r["flags"].append(("ACCENT?", r["accent"], f"maybe British (score {r['accent']:.2f}): for the creator's ear"))
        for kind, rule in M["tone_rules"].items():
            if z and kind != "TIRED OPENING":
                v = tone_index(z, rule)
                r[kind] = v
                if v > rule["thr"]:
                    r["flags"].append((kind, v, f"{kind.lower()} {v:+.1f} ({', '.join(f'{k} {z[k]:+.1f}' for k in rule['w'] if abs(z.get(k, 0)) >= 1.0)})"))
        if prev_z and z:
            keys = M["jump"]["keys"]
            d = float(np.sqrt(sum((z[k] - prev_z[k]) ** 2 for k in keys if k in z and k in prev_z)))
            r["jump"] = d
            if d > M["jump"]["thr"]:
                r["flags"].append(("TONE JUMP", d, f"jump {d:.1f} from {rows[i - 1]['id']} ({', '.join(f'{k} {z[k] - prev_z[k]:+.1f}' for k in keys if abs(z.get(k, 0) - prev_z.get(k, 0)) >= 1.0)})"))
        if r.get("z_self") is not None and r["z_self"] > M["jump"]["self_thr"]:
            r["flags"].append(("CLOSE/DEEP", r["z_self"], f"a different voice from the narration's own (embedding z {r['z_self']:+.1f})"))
        if r.get("z_prev") is not None and r["z_prev"] > M["jump"]["prev_thr"]:
            r["flags"].append(("TONE JUMP", r["z_prev"], f"the voice changes from {rows[i - 1]['id']} (embedding z {r['z_prev']:+.1f})"))
        if patched and r["id"] in patched:
            r["flags"].append(("TONE JUMP", 1.0, "voiced alone as a patch (a separate generation never blends; re-voice it with its section)"))
        prev_z = z if z else prev_z
    # openings: the narration's first beat and each section's first (a request starts cold there): the tired index, or the level down
    # with the voicing or CPP down (a tired opening measured level -2.4, voicing -1.5, CPP -1.2 MADs under its narration)
    starts = {rows[0]["id"]} if rows else set()
    if sections:
        starts |= {s["beats"][0] for s in sections}
    tired = M["tone_rules"].get("TIRED OPENING")
    for r in rows:
        if r["id"] not in starts or not r.get("z") or voice != "long":
            continue
        z = r["z"]
        v = tone_index(z, tired) if tired else 0.0
        if (tired and v > tired["thr"]) or (z.get("level", 0) <= -2.0 and (z.get("cpp", 0) <= -1.0 or z.get("voiced", 0) <= -1.0)):
            r["flags"] = [f for f in r["flags"] if f[0] != "TIRED OPENING"]
            r["flags"].append(("TIRED OPENING", v, f"opens tired: level {z.get('level', 0):+.1f}, CPP {z.get('cpp', 0):+.1f}, voiced {z.get('voiced', 0):+.1f} MADs vs the narration"))
    wr = word_rows(fr, words)
    content = [w for w in wr if w.get("level") is not None and w.get("content")]
    med_level = float(np.median([w["level"] for w in content])) if content else 0.0
    # words
    bad_words = []
    by_beat = {r["id"]: r for r in rows}
    off = 0
    for w in content:
        d = w["level"] - med_level
        if d <= -15.0:  # no voice at this word's time: the word times are off here, not the voice
            off += 1
            continue
        # a word that ends a sentence or a clause falls: a natural fall, not a fault (approved sentence ends sit 7-12 dB under)
        lim = thr["quiet_db"] if not re.search(r"[.?!…,;:][\"')\]]*$", w["w"]) else 99.0
        # whispered = no pitch AND the energy sits in the breath band (a whispered word measured 59 % over 2.4 kHz; a sentence's last
        # word in vocal fry has no pitch either but keeps its energy under 2 kHz: 8 %)
        if w["ves"] < thr["whisper_ves"] and w["hi"] > thr["whisper_hi"] and (w["end"] - w["start"]) >= 0.2:
            bad_words.append((w, "SWALLOWED WORD", f"'{w['w']}' {w['start']:.2f} s: whispered (voiced energy {w['ves']:.2f}, breath {w['hi']:.2f})"))
        elif d <= -lim:
            bad_words.append((w, "SWALLOWED WORD", f"'{w['w']}' {w['start']:.2f} s: {d:+.1f} dB"))
    if off > max(3, len(content) // 50):
        print(f"  ! {off} of {len(content)} content words hold no voice at their time: the word times don't fit this narration (re-sync them)")
    if align is not None:  # a take with timestamps: dj's final-consonant check and rhotic's r
        from dj.core import read_wav
        from dj.tts import swallowed
        from rhotic import score as rhotic_score
        x = read_wav(wav)
        for word, t, under in swallowed(x, align.get("alignment", align)):
            bad_words.append(({"w": word, "start": t, "end": t, "beat": None}, "SWALLOWED WORD", f"'{word}' {t:.2f} s: last consonant {under:.0f} dB under"))
        rh = rhotic_score(wav, align)
        if rh["n"] >= 4 and rh["median_dip"] < 400:
            for r in rows:
                r["flags"].append(("ACCENT", 1.0, f"non-rhotic: median r-dip {rh['median_dip']} Hz"))
    for w, kind, msg in bad_words:
        bid = w.get("beat") or next((r["id"] for r in rows if r["start"] - 0.05 <= w["start"] < r["end"]), None)
        if bid in by_beat:
            by_beat[bid]["flags"].append((kind, 1.0, msg))
    # sections
    secs = []
    for s in (sections or [{"beats": [r["id"] for r in rows], "name": label or wav.name}]):
        sr = [by_beat[b] for b in s["beats"] if b in by_beat]
        if not sr:
            continue
        kinds = {}
        for r in sr:
            for k, v, _ in r["flags"]:
                kinds[k] = max(kinds.get(k, 0), v)
        acc_s = float(sum(max(0, r["end"] - r["start"]) for r in sr if any(k == "ACCENT" for k, _, _ in r["flags"])))
        secs.append({"name": s.get("name") or f"{sr[0]['id']}-{sr[-1]['id']}", "beats": s["beats"], "start": sr[0]["start"], "end": sr[-1]["end"],
                     "kinds": kinds, "accent_s": acc_s, "text": s.get("text", ""), "cache": s.get("cache"),
                     "retake": bool(set(kinds) - {"SWALLOWED WORD", "ACCENT?"})})
    return {"beats": rows, "words": bad_words, "sections": secs, "flags": sum(len(r["flags"]) for r in rows), "accent_t": ts.tolist(),
            "accent_s": acc.tolist()}


def fmt_t(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


def report(res, title):
    L = [f"# Voice guard: {title}\n"]
    n = res["flags"]
    L.append(f"{n} flag(s) in {len(res['beats'])} beats, {sum(1 for s in res['sections'] if s['retake'])} of {len(res['sections'])} section(s) to re-voice.\n")
    L.append("| section | time | flags | first words |\n|---|---|---|---|")
    for s in res["sections"]:
        k = ", ".join(f"{a} {b:.2f}" if a == "ACCENT" else a for a, b in sorted(s["kinds"].items())) or "clean"
        L.append(f"| {s['name']} | {fmt_t(s['start'])}-{fmt_t(s['end'])} | {k}{' -> RETAKE' if s['retake'] else ''} | {s['text'][:60]} |")
    L.append("\n| beat | time | accent | flags |\n|---|---|---|---|")
    for r in res["beats"]:
        if r["flags"]:
            L.append(f"| {r['id']} | {fmt_t(r['start'])}-{fmt_t(r['end'])} | {r['accent']:.2f} | {'; '.join(m for _, _, m in r['flags'])} |")
    return "\n".join(L) + "\n"


# ---------- the video ----------
def video_setup(video):
    from dj.__main__ import video_config
    from dj.core import Ctx, load_config
    from section_takes import sections as dj_sections
    cfg = load_config(None, video_config(video))
    ctx = Ctx(video, cfg)
    tcfg = ctx.cfg["tts"]
    secs = []
    for ids, text, wav in dj_sections(ctx, tcfg):
        secs.append({"beats": ids, "text": text, "cache": wav, "name": f"{ids[0]}-{ids[-1]}"})
    beats_j = json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]
    beats = [{"id": b["id"], "start": b["start"], "end": b["voice_end"], "text": b.get("voice", "")} for b in beats_j if b.get("voice") and not b.get("hold")]
    words = None
    vt = Path(video) / "video.toml"
    src = None
    if vt.exists():
        src = tomllib.loads(vt.read_text(encoding="utf-8")).get("video", {}).get("src")
        wj = TOOLS / "motion" / "src" / (src or "") / "words.json"
        if src and wj.exists():
            words = wj
    cap = ctx.build / "captions" / "words.json"
    if words is not None and not words_fit(words, beats):
        print(f"  ! {words} does not fit this narration (other beats or length): " + ("using dj's captions words" if cap.exists() else "pass --words"))
        words = None
    if words is None and cap.exists():
        words = cap
    return ctx, tcfg, secs, beats, words, src


def words_fit(path, beats):
    """Do these word times belong to this narration: the same beat ids, and the last word inside the narration's length."""
    try:
        ws = load_words(path)
    except Exception:
        return False
    ids = {w["beat"] for w in ws if w.get("beat")}
    bids = {b["id"] for b in beats}
    return bool(ids) and len(ids & bids) >= 0.9 * len(bids) and ws[-1]["end"] <= beats[-1]["end"] + 2.0


def credits_left():
    out = subprocess.run([str(GT), str(HERE / "voice_credits.py")], capture_output=True, text=True).stdout
    m = re.search(r"([\d,]+) credits left", out)
    return int(m.group(1).replace(",", "")) if m else None


NUMBERY = re.compile(r"^(\d+|[a-z]+(teen|ty|th|st|nd|rd)|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|hundred|thousand|"
                     r"million|billion|half|vi|v|and|a)$")


def real_missing(missing):
    """section_takes' Whisper check lists every script word it didn't hear; numbers come back as digits ('ten' -> '10', 'Chapter 5' ->
    'Chapter V'), so number words are no miss. What is left is a dropped word."""
    return [m for m in missing if not NUMBERY.match(m.lower().strip("'"))]


def take_score(res):
    """Lower is better: the flags' weight, then the accent score."""
    kinds = {k for r in res["beats"] for k, _, _ in r["flags"]}
    acc = float(np.nanmean([r["accent"] for r in res["beats"]])) if res["beats"] else 0.0
    return (len([k for k in kinds if k != "SWALLOWED WORD"]) * 10 + len(res["words"]), acc)


def retake(video, ctx, tcfg, secs_flagged, M, voice, a, out_dir):
    """Re-voice each flagged section whole, screen the takes, keep the best one: -> [(section name, take k or None)]."""
    left = credits_left()
    print(f"ElevenLabs: {left:,} credits left" if left is not None else "ElevenLabs: balance unknown")
    spent, picks = 0, []
    prefix = tcfg.get("elevenlabs", {}).get("prefix", "")
    for s in secs_flagged:
        cost = int(CREDITS_PER_CHAR * (len(prefix) + len(s["text"])))
        name_beat = s["beats"][0]
        best = None
        for k in range(1, a.max_takes + 1):
            if spent + cost > a.cap or (left is not None and left - spent - cost < 500):
                print(f"  {s['name']}: stopping, {spent} spent of the {a.cap} cap ({left - spent if left else '?'} left)")
                break
            if a.dry:
                print(f"  {s['name']}: would voice take {k} (~{cost} credits)")
                spent += cost
                continue
            r = subprocess.run([str(GT), str(HERE / "section_takes.py"), str(video), str(out_dir), name_beat, "--n", "1", "--seed", str(a.seed + 10 * k)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            spent += cost
            if r.returncode:
                print(f"  {s['name']}: section_takes failed:\n{r.stdout[-800:]}{r.stderr[-800:]}")
                break
            rep = json.loads((out_dir / "sections.json").read_text(encoding="utf-8"))
            sec_name = next((n for n, d in rep.items() if d["beats"][0] == s["beats"][0]), None)
            take = max(t["take"] for t in rep[sec_name]["takes"])
            raw = out_dir / "raw" / f"{sec_name}_{take}.wav"
            if raw.with_name(raw.stem + ".own.wav").exists():  # a lines-before take (standard/VOICE_LOCK.md): screen the section alone, not its lines before
                raw = raw.with_name(raw.stem + ".own.wav")
            al = json.loads(raw.with_suffix(".align.json").read_text(encoding="utf-8"))
            tw = words_from_align(al)
            tb = [{"id": f"{sec_name}#{take}", "start": 0.0, "end": tw[-1]["end"] if tw else 0.0, "text": s["text"]}]
            res = screen(raw, tw, tb, M, sections=[{"beats": [tb[0]["id"]], "name": f"take {take}", "text": s["text"]}], voice=voice, align=al,
                         label=f"take {take}")
            missing = real_missing(rep[sec_name]["takes"][-1].get("missing", []))
            sc = take_score(res)
            flags = "; ".join(m for r_ in res["beats"] for _, _, m in r_["flags"]) or "clean"
            print(f"  {s['name']} take {take}: {flags}" + (f"  MISSING {' '.join(missing)}" if missing else ""))
            if missing:
                continue
            if best is None or sc < best[0]:
                best = (sc, take, sec_name)
            if sc[0] == 0:
                break
        if best and not a.dry:
            sc, take, sec_name = best
            if sc[0] == 0 or a.keep_best:
                subprocess.run([str(GT), str(HERE / "section_takes.py"), str(video), str(out_dir), "--use", f"{name_beat}={take}"], check=True,
                               capture_output=True)
                picks.append((s["name"], take))
                print(f"  {s['name']}: take {take} in (its old render kept as .orig)")
            else:
                print(f"  {s['name']}: no take passed; the best (take {take}) is in {out_dir} for the creator's ear")
                picks.append((s["name"], None))
        elif not a.dry:
            picks.append((s["name"], None))
    print(f"spent about {spent} credits")
    return picks


def rebuild(video, src):
    for cmd in (["-m", "dj", "tts", str(video)], ["-m", "dj", "captions", str(video)]):
        r = subprocess.run([str(GT)] + cmd, cwd=str(TOOLS), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit(f"{' '.join(cmd)} failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")
    if src:
        r = subprocess.run([str(GT), str(TOOLS / "motion" / "sync_words.py"), Path(video).resolve().name, src], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            raise SystemExit(f"sync_words failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")


def main():
    __import__("voice_lock").guard_argv(__file__, when="--retake")  # the voice lock (standard/VOICE_LOCK.md): a locked narration is changed only by voice_layin.py
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="a video dir (../videos/<video>) or a narration wav")
    ap.add_argument("--words")
    ap.add_argument("--beats", help="beats.json (dj's build/beats.json or the edit's) when the target is a wav")
    ap.add_argument("--voice", choices=["long", "short"], default=None)
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true", help="recompute the embedding cache")
    ap.add_argument("--retake", action="store_true")
    ap.add_argument("--cap", type=int, default=3000)
    ap.add_argument("--max-takes", type=int, default=3)
    ap.add_argument("--seed", type=int, default=8300)
    ap.add_argument("--dry", action="store_true", help="--retake without voicing: say what it would cost")
    ap.add_argument("--keep-best", action="store_true", help="--retake: use the best take even when none passed every measure")
    a = ap.parse_args()
    M = load_model()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    target = Path(a.target)
    if target.is_dir():
        ctx, tcfg, secs, beats, words_path, src = video_setup(target)
        wav = ctx.build / "voice" / "narration.wav"
        voice = a.voice or ctx.fmt
        if a.words:
            words_path = Path(a.words)
        title = f"{ctx.slug} ({wav})"
    else:
        wav, ctx, secs, src = target, None, None, None
        voice = a.voice or ("short" if "short" in wav.name else "long")
        if not a.words:
            raise SystemExit("a wav needs --words <words.json>")
        words_path = Path(a.words)
        beats = []
        if a.beats:
            bj = json.loads(Path(a.beats).read_text(encoding="utf-8"))
            beats = [{"id": b["id"], "start": b["start"], "end": b.get("voice_end", b.get("end")), "text": b.get("voice", "")} for b in bj["beats"]
                     if b.get("voice") or "voice_end" in b or not b.get("hold")]
        title = str(wav)
    if not words_path or not Path(words_path).exists():
        raise SystemExit("no words.json: run dj captions + sync_words.py first, or pass --words")
    words = load_words(words_path)
    if not beats:  # no beats: one per words.json beat id
        ids = []
        for w in words:
            if w["beat"] and w["beat"] not in ids:
                ids.append(w["beat"])
        beats = [{"id": i, "start": min(w["start"] for w in words if w["beat"] == i), "end": max(w["end"] for w in words if w["beat"] == i),
                  "text": " ".join(w["w"] for w in words if w["beat"] == i)} for i in ids]
    patched = set()
    rec = ctx.build / "voice" / "patch" / "used.json" if ctx is not None else None
    if rec is not None and rec.exists():   # voice_patch's record of the beats spliced into this narration
        patched = set(json.loads(rec.read_text(encoding="utf-8")))
    elif ctx is not None and (ctx.build / "voice" / "patch").exists():   # no record (a splice made without one): every take on disk
        patched = {re.sub(r"_\d+$", "", p.stem) for p in (ctx.build / "voice" / "patch").glob("*.wav")}
    res = screen(wav, words, beats, M, sections=secs, voice=voice, force=a.force, patched=patched)
    text = report(res, title)
    print(text)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    if a.retake:
        if ctx is None:
            raise SystemExit("--retake needs a video dir")
        flagged = [s for s in res["sections"] if s["retake"]]
        if not flagged:
            print("nothing to re-voice")
            return 0
        out_dir = VIDEOS / ctx.slug / "review" / "voice_guard_takes"
        out_dir.mkdir(parents=True, exist_ok=True)
        flagged.sort(key=lambda s: (-len(set(s["kinds"]) - {"SWALLOWED WORD"}), -s["accent_s"]))
        picks = retake(target, ctx, tcfg, flagged, M, voice, a, out_dir)
        if any(k for _, k in picks) and not a.dry:
            print("rebuilding the narration (dj tts, dj captions, sync_words)")
            rebuild(target, src)
            words = load_words(words_path)
            beats_j = json.loads((ctx.build / "beats.json").read_text(encoding="utf-8"))["beats"]
            beats = [{"id": b["id"], "start": b["start"], "end": b["voice_end"], "text": b.get("voice", "")} for b in beats_j if b.get("voice") and not b.get("hold")]
            res = screen(wav, words, beats, M, sections=secs, voice=voice, force=True)
            text = report(res, title + " (after the retakes)")
            print(text)
            if a.out:
                Path(a.out).write_text(Path(a.out).read_text(encoding="utf-8") + "\n" + text, encoding="utf-8")
    return 1 if res["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
