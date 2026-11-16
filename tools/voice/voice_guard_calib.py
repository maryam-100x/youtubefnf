"""Calibrate the voice guard on the creator's own verdicts: every take with a fault they heard (flagged spans) against the narrations
they approved. Reads the two ears' caches (<wav>.guard_embed.json, <wav>.guard_tone.json: 2.0-s windows, hop 0.5), labels each window
by the flagged spans, and measures, per measure, how well it separates them: recall on each flagged span, false alarms on the approved
narrations, the thresholds that come out. Prints the report (markdown, also written to --out) and writes the model the guard uses
(probe weights, thresholds, the approved voice's tone) to <MEDIA>/voice/guard/voice_guard_model.json. Nothing of it ships with the
repo: every creator builds their own from their own voice.

The reference folder, <MEDIA>/voice/guard/ (filled at setup, grown whenever a fault is heard):
  approved/            narrations the creator approved: <name>.wav, with <name>.words.json (the edit's or dj's captions words.json:
                       [{w, start, end, beat}]) and optionally <name>.beats.json (dj's build/beats.json). A wav without words still
                       counts for the window measures (accent, distance); the beat measures (tone, jumps) need the words.
  approved/short/      the same for the Shorts voice (it is set up livelier than the long-form read, so it gets its own baseline)
  flagged/             takes with faults heard in them: <name>.wav + <name>.spans.json = [[t0, t1, "<kind>"], ...] (seconds; a negative
                       time counts from the end), kinds ACCENT, CLOSE, WHISPER, BREATHY, TIRED, SWALLOWED; words/beats as above
  flagged/short/       the same for Shorts takes
  live/                optional: narrations to see the model on, never trained on (live/short/ for Shorts)
Name files <video>_<anything>.wav: the files of one video are left out together in the held-out check of the accent probes.
What it needs: at least one approved narration with its words (2+ beats). The accent probes need at least MIN_ACCENT_WINDOWS flagged
ACCENT windows (about 10 s of British speech, over one span or several); with fewer, the model's accent score is CommonAccent's P(UK)
alone (accent_weights acc 0, spk 0) and the report says so. The tone kinds need no flagged spans: their thresholds come from the
approved beats; flagged ones only add the report's recall columns.

  ACCENT tools/voice/voice_guard_embed.py <MEDIA>/voice/guard         (the embedding caches; ACCENT = the accent venv's python)
  PIPE tools/voice/voice_guard_tone.py <MEDIA>/voice/guard            (the tone caches)
  PIPE tools/voice/voice_guard_calib.py [--dir <MEDIA>/voice/guard] [--out <report.md>] [--model <model.json>]
      (--out defaults to CALIB.md next to the model; --manifest <json> takes the same entries written by hand instead of the folder:
      {"approved": [{name, wav, words?, beats?, voice?}], "approved_raw": [...], "flagged": [{..., spans}], "live": [...]})"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import MEDIA  # noqa: E402
sys.path.insert(0, str(HERE))

GUARD_DIR = MEDIA / "voice" / "guard"
UK = ("england", "scotland", "wales", "ireland", "australia", "newzealand")
TONE = ["f0", "f0_range", "voiced", "voicing", "cpp", "hnr", "low", "sub", "presence", "air", "tilt", "level"]
SPAN_KINDS = ("ACCENT", "CLOSE", "WHISPER", "BREATHY", "TIRED", "SWALLOWED")
MIN_ACCENT_WINDOWS = 20   # flagged ACCENT windows the accent probes need (2-s windows, hop 0.5 s: ~10 s of British speech)


def entries_from_folder(root):
    """The calibration entries from the reference folder (layout in the docstring) -> {"approved", "approved_raw", "flagged", "live"}."""
    root = Path(root)
    man = {"approved": [], "approved_raw": [], "flagged": [], "live": []}
    for group in ("approved", "flagged", "live"):
        d = root / group
        if not d.exists():
            continue
        for w in sorted(d.rglob("*.wav")):
            rel = w.relative_to(d)
            voice = "short" if rel.parts[0].lower() == "short" and len(rel.parts) > 1 else "long"
            e = {"name": f"{group}/{rel.with_suffix('').as_posix()}", "wav": str(w), "voice": voice}
            for key in ("words", "beats"):
                f = w.with_name(w.stem + f".{key}.json")
                if f.exists():
                    e[key] = str(f)
            if group == "flagged":
                f = w.with_name(w.stem + ".spans.json")
                if not f.exists():
                    print(f"  ! {w}: no {f.name} (the faults' spans), left out", file=sys.stderr)
                    continue
                sp = json.loads(f.read_text(encoding="utf-8"))
                sp = sp.get("spans", []) if isinstance(sp, dict) else sp
                bad = [x for x in sp if len(x) < 3 or x[2] not in SPAN_KINDS]
                if bad:
                    print(f"  ! {f.name}: spans need [t0, t1, kind] with kind one of {', '.join(SPAN_KINDS)}: {bad[:3]}", file=sys.stderr)
                e["spans"] = [x for x in sp if x not in bad]
            man["approved_raw" if group == "approved" and "words" not in e else group].append(e)
    return man


def source(name):
    """The video a file comes from: its file name up to the first "_", a trailing version tag (v2, v2.1) dropped."""
    return re.sub(r"v\d+(\.\d+)*$", "", Path(name).name.split("_")[0])


def load_entry(e, group):
    w = Path(e["wav"])
    ej, tj = w.with_name(w.name + ".guard_embed.json"), w.with_name(w.name + ".guard_tone.json")
    if not ej.exists() or not tj.exists():
        print(f"  (no cache yet for {e['name']})", file=sys.stderr)
        return []
    E, T = json.loads(ej.read_text(encoding="utf-8")), json.loads(tj.read_text(encoding="utf-8"))
    dur = E["seconds"]
    spans = []
    for s in e.get("spans", []):
        t0, t1 = s[0], s[1]
        t0 = dur + t0 if t0 < 0 else t0
        t1 = dur + t1 if t1 < 0 else t1
        spans.append((t0, t1, s[2]))
    tone = {round(r["t"], 1): r for r in T["rows"]}
    labels = E["labels"]
    rows = []
    for t, spk, acc, p in zip(E["t"], E["spk"], E["acc"], E["p"]):
        tr = tone.get(round(t, 1))
        if tr is None:
            continue
        c = t + E["win"] / 2
        kind = next((k for a, b, k in spans if a <= c < b), "")
        rows.append({"name": e["name"], "group": group, "t": t, "kind": kind, "voice": e.get("voice", "long"),
                     "spk": np.array(spk), "acc": np.array(acc), "p_uk": sum(p[labels.index(k)] for k in UK),
                     "p_us": p[labels.index("us")] + p[labels.index("canada")], **{k: tr[k] for k in TONE}})
    return rows


def auc(pos, neg):
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if not len(pos) or not len(neg):
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order))
    ranks[order] = np.arange(1, len(order) + 1)
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def logreg(X, y, l2=1.0, iters=300):
    """L2-regularised logistic regression by Newton's method on standardised features."""
    mu, sd = X.mean(0), X.std(0) + 1e-6
    Z = (X - mu) / sd
    Z = np.hstack([Z, np.ones((len(Z), 1))])
    w = np.zeros(Z.shape[1])
    wt = np.where(y == 1, 0.5 / max(y.mean(), 1e-6), 0.5 / max(1 - y.mean(), 1e-6))  # classes weigh the same
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Z @ w))
        g = Z.T @ ((p - y) * wt) + l2 * np.r_[w[:-1], 0]
        H = (Z * (p * (1 - p) * wt)[:, None]).T @ Z + l2 * np.diag(np.r_[np.ones(Z.shape[1] - 1), 0])
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-6:
            break
    return {"mu": mu.tolist(), "sd": sd.tolist(), "w": w[:-1].tolist(), "b": float(w[-1])}


def apply(model, X):
    Z = (X - np.array(model["mu"])) / np.array(model["sd"])
    return 1 / (1 + np.exp(-(Z @ np.array(model["w"]) + model["b"])))


def smooth(v, k=5):
    v = np.asarray(v, float)
    if len(v) < k:
        return v
    out = np.copy(v)
    h = k // 2
    for i in range(len(v)):
        out[i] = np.median(v[max(0, i - h): i + h + 1])
    return out


def stretches(ts, flags, hop=0.5, win=2.0):
    """Contiguous flagged windows -> [(t0, t1)] in seconds."""
    out, start, prev = [], None, None
    for t, f in zip(ts, flags):
        if f and start is None:
            start = t
        if not f and start is not None:
            out.append((start, prev + win))
            start = None
        prev = t
    if start is not None:
        out.append((start, prev + win))
    return out


def beat_rows(e, group):
    """Per beat of a narration (its beats.json or the beats named in words.json): the tone stats, pace and pause share, labelled by its
    flagged spans (cached as <wav>.guard_beats.json)."""
    if not e.get("words"):
        return []
    w = Path(e["wav"])
    cache = w.with_name(w.name + ".guard_beats.json")
    import voice_guard_tone as tone
    st = w.stat()
    stamp = f"{st.st_size}-{int(st.st_mtime)}-v{tone.VERSION}"
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("stamp") == stamp:
            rows = d["rows"]
            return label_beats(rows, e, group)
    words = json.loads(Path(e["words"]).read_text(encoding="utf-8"))
    words = words["words"] if isinstance(words, dict) else words
    beats = []
    if e.get("beats"):
        for b in json.loads(Path(e["beats"]).read_text(encoding="utf-8"))["beats"]:
            if b.get("voice_end", b.get("end", 0)) - b["start"] > 0.3 and not b.get("hold"):
                beats.append((b["id"], b["start"], b.get("voice_end", b["end"])))
    else:
        ids = []
        for x in words:
            if x.get("beat") and x["beat"] not in ids:
                ids.append(x["beat"])
        for i in ids:
            ws = [x for x in words if x["beat"] == i]
            beats.append((i, min(x["start"] for x in ws), max(x["end"] for x in ws)))
    fr = tone.frames(tone.load(w))
    rows = []
    for bid, t0, t1 in beats:
        s = tone.stats(fr, t0, t1)
        if not s:
            continue
        m = (fr["t"] >= t0) & (fr["t"] < t1)
        nw = sum(1 for x in words if t0 - 0.05 <= x["start"] < t1)
        s.update({"id": bid, "start": t0, "end": t1, "pace": nw / max(t1 - t0, 0.1), "gaps": float(1 - fr["speech"][m].mean())})
        rows.append(s)
    cache.write_text(json.dumps({"stamp": stamp, "rows": rows}), encoding="utf-8")
    return label_beats(rows, e, group)


def beat_emb_dist(brows, man):
    """Per beat: the speaker embedding's distance from the narration's own voice (d_self) and from the beat before (d_prev), and their
    robust z-scores within the file (z_d_self, z_d_prev)."""
    for g in ("flagged", "approved", "live"):
        for e in man[g]:
            rr = [r for r in brows if r["name"] == e["name"]]
            if not rr:
                continue
            w = Path(e["wav"])
            ej = w.with_name(w.name + ".guard_embed.json")
            if not ej.exists():   # no embedding cache yet (load_entry said so): its beats count as no distance
                for r in rr:
                    r.update(d_self=0.0, d_prev=0.0, z_d_self=0.0, z_d_prev=0.0)
                continue
            E = json.loads(ej.read_text(encoding="utf-8"))
            ts = np.array(E["t"]) + E["win"] / 2
            S = np.array(E["spk"])
            vecs = []
            for r in rr:
                m = (ts >= r["start"]) & (ts < r["end"])
                if not m.any():
                    m = np.abs(ts - (r["start"] + r["end"]) / 2) <= 1.5
                v = S[m].mean(0) if m.any() else None
                vecs.append(v / np.linalg.norm(v) if v is not None else None)
            have = [v for v in vecs if v is not None]
            c = np.mean(have, 0)
            c /= np.linalg.norm(c)
            for i, (r, v) in enumerate(zip(rr, vecs)):
                r["d_self"] = float(1 - v @ c) if v is not None else 0.0
                r["d_prev"] = float(1 - v @ vecs[i - 1]) if i and v is not None and vecs[i - 1] is not None else 0.0
            for k in ("d_self", "d_prev"):
                x = np.array([r[k] for r in rr])
                med = float(np.median(x))
                mad = max(1.4826 * float(np.median(np.abs(x - med))), 1e-6)
                for r in rr:
                    r["z_" + k] = (r[k] - med) / mad


def label_beats(rows, e, group):
    dur = max((r["end"] for r in rows), default=0.0)
    spans = [((dur + s[0]) if s[0] < 0 else s[0], (dur + s[1]) if s[1] < 0 else s[1], s[2]) for s in e.get("spans", [])]
    out = []
    for r in rows:
        kind = ""
        for a, b, k in spans:
            if min(b, r["end"]) - max(a, r["start"]) > 0.5 * (r["end"] - r["start"]):
                kind = k
                break
        out.append({**r, "name": e["name"], "group": group, "kind": kind})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(GUARD_DIR), help="the reference folder (layout in the docstring)")
    ap.add_argument("--manifest", default=None, help="the same entries as a JSON file instead of the folder")
    ap.add_argument("--out", default=None, help="the report (default: CALIB.md next to the model)")
    ap.add_argument("--model", default=None, help="where the model goes (default: <dir>/voice_guard_model.json, the guard's MODEL)")
    a = ap.parse_args()
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8", errors="replace")
    a.model = a.model or str(Path(a.dir) / "voice_guard_model.json")
    a.out = a.out or str(Path(a.model).with_name("CALIB.md"))
    if a.manifest:
        man = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    else:
        man = entries_from_folder(a.dir)
    for g in ("flagged", "approved", "approved_raw", "live"):
        man.setdefault(g, [])
    if not man["approved"]:
        raise SystemExit(f"no approved narration with its words in {Path(a.dir) / 'approved'}: the guard's baselines come from the "
                         "creator's approved voice (<name>.wav + <name>.words.json; see this file's docstring)")
    rows = []
    for g in ("flagged", "approved", "approved_raw", "live"):
        for e in man.get(g, []):
            rows += load_entry(e, "approved" if g == "approved_raw" else g)
    if not any(r["group"] == "approved" for r in rows):
        raise SystemExit("no approved narration has its caches yet: run voice_guard_embed.py (ACCENT) and voice_guard_tone.py (PIPE) "
                         f"on {a.dir} first (this file's docstring)")
    L = []
    pr = L.append
    pr("# Voice guard calibration (windows of 2.0 s, hop 0.5 s)\n")
    names = sorted({r["name"] for r in rows}, key=lambda n: (next(r["group"] for r in rows if r["name"] == n), n))
    pr("| file | group | windows | flagged kinds |\n|---|---|---|---|")
    for n in names:
        rr = [r for r in rows if r["name"] == n]
        kinds = sorted({r["kind"] for r in rr if r["kind"]})
        pr(f"| {n} | {rr[0]['group']} | {len(rr)} | {', '.join(kinds) or '-'} |")

    # ---------- ACCENT ----------
    pr("\n## ACCENT\n")
    acc_pos = [r for r in rows if r["kind"] == "ACCENT"]
    approved = [r for r in rows if r["group"] == "approved"]
    rest = [r for r in rows if r["group"] == "flagged" and r["kind"] == ""]
    pr(f"Positives: {len(acc_pos)} windows heard as British; negatives: {len(approved)} approved windows (+ {len(rest)} unflagged windows of flagged files).\n")
    pr("| score | AUC vs approved | AUC vs unflagged rest |\n|---|---|---|")
    pr(f"| CommonAccent P(UK) (accent_id.py's model) | {auc([r['p_uk'] for r in acc_pos], [r['p_uk'] for r in approved]):.3f} | {auc([r['p_uk'] for r in acc_pos], [r['p_uk'] for r in rest]):.3f} |")
    probes = len(acc_pos) >= MIN_ACCENT_WINDOWS
    weights = {"acc": 1.0, "spk": 1.0, "p_uk": 1.0} if probes else {"acc": 0.0, "spk": 0.0, "p_uk": 1.0}
    models = {}
    if not probes:
        pr(f"\nThe accent probes need at least {MIN_ACCENT_WINDOWS} flagged ACCENT windows (about 10 s of British speech; {len(acc_pos)} "
           "here): the guard's accent score is CommonAccent's P(UK) alone until flagged/ holds them.\n")
        for feat in ("acc", "spk"):
            dim = len(rows[0][feat])
            models[feat] = {"mu": [0.0] * dim, "sd": [1.0] * dim, "w": [0.0] * dim, "b": 0.0}   # unused: weight 0
            for r in rows:
                r[f"probe_{feat}"] = 0.5
    else:
        # the probes: leave one source out (a source = the video the flagged windows come from)
        for feat in ("acc", "spk"):
            X = np.stack([r[feat] for r in rows if r["group"] != "live"])
            y = np.array([1.0 if r["kind"] == "ACCENT" else 0.0 for r in rows if r["group"] != "live"])
            sources = np.array([source(r["name"]) for r in rows if r["group"] != "live"])
            used = np.array([r["kind"] in ("ACCENT", "") for r in rows if r["group"] != "live"])  # other kinds stay out of the accent probe
            models[feat] = logreg(X[used], y[used], l2=5.0)
            loo = np.full(len(y), np.nan)
            in_sample = []
            for src_ in sorted(set(sources)):
                tr = (sources != src_) & used
                if not (y[tr] == 1).any():   # no other source has accent spans: this fold is scored in-sample
                    loo[sources == src_] = apply(models[feat], X[sources == src_])
                    in_sample.append(src_)
                    continue
                m = logreg(X[tr], y[tr], l2=5.0)
                loo[sources == src_] = apply(m, X[sources == src_])
            pos_s = loo[(y == 1)]
            neg_s = loo[(y == 0) & np.array([r["group"] == "approved" for r in rows if r["group"] != "live"])]
            rest_s = loo[(y == 0) & np.array([r["group"] == "flagged" for r in rows if r["group"] != "live"])]
            note = f"; in-sample for {', '.join(in_sample)}" if in_sample else ""
            pr(f"| probe on the {'accent' if feat == 'acc' else 'speaker'} embedding (leave-one-video-out{note}) | {auc(pos_s, neg_s):.3f} | {auc(pos_s, rest_s):.3f} |")
            for i, r in enumerate([r for r in rows if r["group"] != "live"]):
                r[f"probe_{feat}"] = float(loo[i])
            for r in [r for r in rows if r["group"] == "live"]:
                r[f"probe_{feat}"] = float(apply(models[feat], r[feat][None, :])[0])
    for r in rows:
        r["guard"] = (weights["p_uk"] * r["p_uk"] + weights["acc"] * r["probe_acc"] + weights["spk"] * r["probe_spk"]) / sum(weights.values())
    pos_g = [r["guard"] for r in acc_pos]
    pr(f"| the guard's score ({'the mean of the three' if probes else 'P(UK) alone'}) | {auc(pos_g, [r['guard'] for r in approved]):.3f} | {auc(pos_g, [r['guard'] for r in rest]):.3f} |")
    # thresholds: the probe score at which 1 % of approved windows (smoothed) fire
    thresholds = {}
    pr("\n### Per span, at a threshold set for 1 % of approved windows (scores smoothed over 5 windows)\n")
    for feat, label in (("p_uk", "P(UK)"), ("probe_acc", "accent probe"), ("probe_spk", "speaker probe"), ("guard", "the guard's score")):
        app_s = np.concatenate([smooth([r[feat] for r in rows if r["name"] == n]) for n in names if any(r["name"] == n and r["group"] == "approved" for r in rows)])
        thr = float(np.percentile(app_s, 99))
        thresholds[feat] = thr
        thresholds[feat + "_soft"] = float(np.percentile(app_s, 97))
        pr(f"**{label}**: threshold {thr:.3f} (99th percentile of approved windows; {np.mean(app_s > thr) * 100:.1f} % fire)\n")
        pr("| span | flagged start-end | windows over | detected stretches |\n|---|---|---|---|")
        for e in man["flagged"]:
            rr = [r for r in rows if r["name"] == e["name"]]
            if not rr:
                continue
            ts = np.array([r["t"] for r in rr])
            sc = smooth([r[feat] for r in rr])
            dur = ts[-1] + 2.0
            for s in e.get("spans", []):
                if s[2] != "ACCENT":
                    continue
                t0 = dur + s[0] if s[0] < 0 else s[0]
                t1 = dur + s[1] if s[1] < 0 else s[1]
                inside = (ts + 1.0 >= t0) & (ts + 1.0 < t1)
                over = (sc[inside] > thr).mean() if inside.any() else float("nan")
                st = [f"{x:.1f}-{y:.1f}" for x, y in stretches(ts, sc > thr) if y > t0 - 2 and x < t1 + 2]
                pr(f"| {e['name']} | {t0:.1f}-{t1:.1f} | {over * 100:.0f} % | {', '.join(st) or '-'} |")
            # false alarms outside the accent spans of this file
            out = np.ones(len(ts), bool)
            for s in e.get("spans", []):
                t0 = dur + s[0] if s[0] < 0 else s[0]
                t1 = dur + s[1] if s[1] < 0 else s[1]
                out &= ~((ts + 1.0 >= t0) & (ts + 1.0 < t1))
            if out.any() and (sc[out] > thr).any():
                st = [f"{x:.1f}-{y:.1f}" for x, y in stretches(ts[out], sc[out] > thr)]
                pr(f"| {e['name']} (outside its spans) | - | {(sc[out] > thr).mean() * 100:.0f} % | {', '.join(st)} |")
        for n in [e["name"] for e in man["approved"]] + [e["name"] for e in man["live"]]:
            rr = [r for r in rows if r["name"] == n]
            if not rr:
                continue
            ts = np.array([r["t"] for r in rr])
            sc = smooth([r[feat] for r in rr])
            st = [f"{x:.1f}-{y:.1f}" for x, y in stretches(ts, sc > thr)]
            if st:
                pr(f"| {n} ({rr[0]['group']}) | none | {(sc > thr).mean() * 100:.1f} % | {', '.join(st)} |")
        pr("")

    # ---------- TONE, per beat ----------
    pr("\n## TONE per beat (CLOSE, WHISPER, BREATHY, TIRED, SWALLOWED) against the narration's own beats\n")
    pr("A beat is flagged when over half of it lies in one of the flagged spans. z = (beat - the file's median over its beats) / (1.4826 x MAD). "
       "AUC: flagged beats against the same files' unflagged beats, and against every approved beat (z against each file's own baseline).\n")
    brows = []
    for g in ("flagged", "approved", "live"):
        for e in man[g]:
            brows += beat_rows(e, g)
    TB = TONE + ["pace", "gaps"]
    for n in sorted({r["name"] for r in brows}):
        rr = [r for r in brows if r["name"] == n]
        for k in TB:
            v = np.array([r[k] for r in rr], float)
            med = float(np.median(v))
            mad = max(1.4826 * float(np.median(np.abs(v - med))), 1e-6)
            for r in rr:
                r["z_" + k] = (r[k] - med) / mad
    INDEX = {"CLOSE": {"f0": -1, "voiced": -1, "cpp": -1, "hnr": -1, "sub": 1, "low": 1, "level": -1},
             "WHISPER": {"f0": -1, "voiced": -1, "cpp": -1, "hnr": -1, "level": -1, "sub": 1},
             "BREATHY": {"cpp": -1, "hnr": -1, "voiced": -1, "air": 1},
             "TIRED": {"voiced": -1, "cpp": -1, "hnr": -1, "level": -1, "tilt": -1}}
    for r in brows:
        for kind, w in INDEX.items():
            r["idx_" + kind] = sum(wt * r["z_" + k] for k, wt in w.items()) / sum(abs(wt) for wt in w.values())
    beat_emb_dist(brows, man)
    app_b = [r for r in brows if r["group"] == "approved"]
    # the tone jump between consecutive beats (the z-vector distance over f0, low, presence, cpp, level): its 99th pct on approved beats
    JK = ["f0", "low", "presence", "cpp", "level"]
    jumps = []
    for n in sorted({r["name"] for r in app_b}):
        rr = [r for r in brows if r["name"] == n]
        for p0, p1 in zip(rr, rr[1:]):
            jumps.append(float(np.sqrt(sum((p1["z_" + k] - p0["z_" + k]) ** 2 for k in JK))))
    if not jumps:
        raise SystemExit("the approved narrations need 2+ beats each (their words.json beat ids): the tone-jump threshold comes from them")
    jump_thr = float(np.percentile(jumps, 99))
    pr(f"Tone jump between consecutive approved beats (z distance over {', '.join(JK)}): median {np.median(jumps):.2f}, 95th {np.percentile(jumps, 95):.2f}, 99th {jump_thr:.2f} (the guard's TONE JUMP threshold).\n")
    TB = TB + ["d_self", "d_prev"]
    for kind in ("CLOSE", "WHISPER", "BREATHY", "TIRED", "SWALLOWED"):
        pos = [r for r in brows if r["kind"] == kind]
        if not pos:
            continue
        files = sorted({r["name"] for r in pos})
        neg = [r for r in brows if r["name"] in files and r["kind"] == ""]
        pr(f"**{kind}** ({len(pos)} beats in {', '.join(files)}; {len(neg)} unflagged beats there, {len(app_b)} approved beats)\n")
        pr("| feature | mean z (flagged) | AUC vs the files' rest | AUC vs approved |\n|---|---|---|---|")
        for k in TB + ["idx_" + kk for kk in INDEX]:
            key = k if k.startswith("idx_") else "z_" + k
            pr(f"| {k} | {np.mean([r[key] for r in pos]):+.2f} | {auc([r[key] for r in pos], [r[key] for r in neg]):.3f} | {auc([r[key] for r in pos], [r[key] for r in app_b]):.3f} |")
        pr("")
    # the index thresholds: what fires on 1 % of approved beats, and the recall of each kind's beats there
    pr("| index | threshold (99th pct of approved beats) | approved beats over | flagged beats over, by kind |\n|---|---|---|---|")
    for kind in INDEX:
        key = "idx_" + kind
        thr = float(np.percentile([r[key] for r in app_b], 99))
        rec = {kk: f"{np.mean([r[key] > thr for r in brows if r['kind'] == kk]) * 100:.0f} % of {sum(1 for r in brows if r['kind'] == kk)}" for kk in ("CLOSE", "WHISPER", "BREATHY", "TIRED") if any(r["kind"] == kk for r in brows)}
        pr(f"| {kind} | {thr:.2f} | {np.mean([r[key] > thr for r in app_b]) * 100:.1f} % | {'; '.join(f'{a}: {b}' for a, b in rec.items())} |")
    pr("")
    pr("### The flagged beats, one by one (z against their own file)\n")
    pr("| file | beat | kind | f0 | voiced | cpp | hnr | sub | low | level | idx CLOSE | idx WHISPER |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in [r for r in brows if r["kind"]]:
        pr(f"| {r['name']} | {r['id']} | {r['kind']} | " + " | ".join(f"{r['z_' + k]:+.1f}" for k in ("f0", "voiced", "cpp", "hnr", "sub", "low", "level")) + f" | {r['idx_CLOSE']:+.2f} | {r['idx_WHISPER']:+.2f} |")
    pr("")

    # the speaker embedding's distance from the approved voice, per kind (a voice profile with no approved take has no centroid)
    pr("\n## Distance from the approved voice (speaker embedding, cosine to the approved centroid of the same voice profile)\n")
    cent = {}
    for v in ("long", "short"):
        if not any(r["voice"] == v for r in approved):
            continue
        X = np.stack([r["spk"] for r in approved if r["voice"] == v])
        c = X.mean(0)
        cent[v] = (c / np.linalg.norm(c)).tolist()
    for r in rows:
        r["dist"] = float(1 - r["spk"] @ np.array(cent[r["voice"]])) if r["voice"] in cent else float("nan")
    app_d = np.array([r["dist"] for r in approved])
    pr(f"approved windows: median {np.median(app_d):.3f}, 95th {np.percentile(app_d, 95):.3f}, 99th {np.percentile(app_d, 99):.3f}\n")
    pr("| kind | windows | median distance | AUC vs approved |\n|---|---|---|---|")
    for kind in ("ACCENT", "CLOSE", "WHISPER", "BREATHY", "TIRED", "SWALLOWED", ""):
        rr = [r for r in rows if r["group"] == "flagged" and r["kind"] == kind and np.isfinite(r["dist"])]
        if rr:
            pr(f"| {kind or 'unflagged rest'} | {len(rr)} | {np.median([r['dist'] for r in rr]):.3f} | {auc([r['dist'] for r in rr], app_d):.3f} |")
    for n in [e["name"] for e in man["live"]]:
        rr = [r for r in rows if r["name"] == n and np.isfinite(r["dist"])]
        if rr:
            pr(f"| {n} (live) | {len(rr)} | {np.median([r['dist'] for r in rr]):.3f} | {auc([r['dist'] for r in rr], app_d):.3f} |")
    # the within-narration accent distance: each window's accent embedding against its own file's mean, as a z-score, smoothed
    # (a chapter voiced in a slipped accent can sit 2-10 MADs from the rest of its narration)
    zs_app = []
    for n in names:
        rr = [r for r in rows if r["name"] == n]
        A = np.stack([r["acc"] for r in rr])
        c = A.mean(0)
        c /= np.linalg.norm(c)
        d = 1 - A @ c
        med = float(np.median(d))
        mad = max(1.4826 * float(np.median(np.abs(d - med))), 1e-6)
        z = smooth((d - med) / mad)
        for r, v in zip(rr, z):
            r["z_self_acc"] = float(v)
        if rr[0]["group"] == "approved":
            zs_app.append(z)
    self_acc_thr = float(np.percentile(np.concatenate(zs_app), 99))
    pr(f"\n## Within-narration accent distance (z of each window's accent embedding from its own narration's mean, smoothed): threshold {self_acc_thr:.2f} (99th pct of approved)\n")
    pr("| file | stretches over (3 s or more) | flagged accent spans |\n|---|---|---|")
    for n in names:
        rr = [r for r in rows if r["name"] == n]
        if rr[0]["group"] == "approved" and not any(r["z_self_acc"] > self_acc_thr for r in rr):
            continue
        ts = np.array([r["t"] for r in rr])
        st = [f"{x:.0f}-{y:.0f}" for x, y in stretches(ts, np.array([r["z_self_acc"] for r in rr]) > self_acc_thr) if y - x >= 3.0]
        fl = next((e for g in ("flagged", "live") for e in man[g] if e["name"] == n), None)
        spans = ", ".join(f"{s[0]:.0f}-{s[1]:.0f}" for s in (fl or {}).get("spans", []) if s[2] == "ACCENT")
        pr(f"| {n} | {', '.join(st) or '-'} | {spans or '-'} |")
    # the approved voice's tone, per profile: median and MAD of every tone feature over the approved windows (the guard's "ref")
    ref = {}
    for v in ("long", "short"):
        rr = [r for r in approved if r["voice"] == v]
        if not rr:
            continue
        ref[v] = {}
        for k in TONE:
            x = np.array([r[k] for r in rr], float)
            med = float(np.median(x))
            ref[v][k] = [med, max(1.4826 * float(np.median(np.abs(x - med))), 1e-6)]
    old = json.loads(Path(a.model).read_text(encoding="utf-8")) if Path(a.model).exists() else {}
    model = {"about": "voice_guard probes and thresholds, trained by voice_guard_calib.py on the creator's approved and flagged takes",
             "accent_probe_acc": models["acc"], "accent_probe_spk": models["spk"], "centroid": cent, "ref": ref,
             "accent_weights": weights,
             "thresholds": {"accent": round(thresholds["guard"], 4), "accent_soft": round(thresholds["guard_soft"], 4), "accent_min_s": 4.0,
                            "self_acc_z": round(self_acc_thr, 2), "quiet_db": 4.0, "quiet_final_db": 7.0, "whisper_ves": 0.25, "whisper_hi": 0.35},
             "tone_rules": {"CLOSE/DEEP": {"w": INDEX["CLOSE"], "thr": round(float(np.percentile([r["idx_CLOSE"] for r in app_b], 99)), 3)},
                            "WHISPER": {"w": INDEX["WHISPER"], "thr": round(float(np.percentile([r["idx_WHISPER"] for r in app_b], 99)), 3)},
                            "TIRED OPENING": {"w": INDEX["TIRED"], "thr": round(float(np.percentile([r["idx_TIRED"] for r in app_b], 99)), 3)}},
             "jump": {"keys": ["f0", "low", "presence", "cpp", "level"], "thr": round(jump_thr, 2),
                      "self_thr": round(float(np.percentile([r["z_d_self"] for r in app_b], 99)), 2),
                      "prev_thr": round(float(np.percentile([r["z_d_prev"] for r in app_b], 99)), 2)}}
    Path(a.model).parent.mkdir(parents=True, exist_ok=True)
    Path(a.model).write_text(json.dumps(model, indent=1), encoding="utf-8")
    text = "\n".join(L)
    print(text)
    Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(f"model: {a.model}\nreport: {a.out}")


if __name__ == "__main__":
    sys.exit(main())
