"""The reviewer's eye: score a run's predicted notes against the creator's real notes on the same video (calibration; no model), so
the reviewer is trusted only as far as it has been measured.

  PIPE tools/eye/eye_score.py merge <notes.json> <part1.json> [<part2.json> ...] [<whole.json>]
      the parts' and the whole pass's notes as one run (notes.json and notes.md), sorted by time
  PIPE tools/eye/eye_score.py candidates <key.json> <pred.json> [--window 5]
      lists, per note of the creator's, the predicted notes within the window (and up to twice it, marked), to judge the matches by eye
  PIPE tools/eye/eye_score.py score <key.json> <match.json> [<match.json> ...] [--md <out.md>]
      the numbers per run and per confidence cut: recall over all the creator's notes, over the judgement notes, over the ones no tool
      catches; precision strict (predictions that match one of the creator's notes) and judged (plus the unmatched ones a judge found real)

key.json:   {"video", "notes": [{"id": "K1", "t": "0:05", "t_end": "0:09"|null, "what", "words" (the creator's own), "msg", "row",
            "judgement": bool, "tool": "none" | the deterministic check that catches it}]}
match.json: {"run", "pred": <pred.json path>, "matches": [{"key": "K1", "pred": [3, 7], "why"}],
            "unmatched": [{"pred": 5, "real": "yes"|"no"|"unsure", "why"}]}
A match means the same spot (within ~5 s, or inside the creator's stretch) and the same issue: the fix would be the same."""
import argparse
import json
import sys
from pathlib import Path

CUTS = {"high": ("high",), "high+medium": ("high", "medium"), "all": ("high", "medium", "low")}


def secs(t):
    if t is None or t == "":
        return None
    if isinstance(t, (int, float)):
        return float(t)
    parts = [float(x) for x in str(t).split(":")]
    return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def candidates(a):
    key, pred = load(a.key), load(a.pred)
    for k in key["notes"]:
        k0 = secs(k["t"])
        k1 = secs(k.get("t_end")) or k0
        print(f"\n{k['id']} {k['t']}{'-' + k['t_end'] if k.get('t_end') else ''} [{'J' if k['judgement'] else 'D'}:{k['tool']}] {k['what']}")
        for p in pred["notes"]:
            p0 = secs(p["t"])
            p1 = secs(p.get("t_end")) or p0
            gap = max(0.0, max(k0, p0) - min(k1, p1))
            if gap <= 2 * a.window:
                mark = "  " if gap <= a.window else "~ "
                print(f"   {mark}P{p['id']} {p['t']} ({p['confidence']}) {p['what'][:150]}")


def score_run(key, m):
    pred = load(m["pred"])
    notes = {p["id"]: p for p in pred["notes"]}
    matched_keys = {}
    for x in m["matches"]:
        for pid in x["pred"]:
            matched_keys.setdefault(x["key"], set()).add(pid)
    real = {u["pred"]: u["real"] for u in m.get("unmatched", [])}
    rows = []
    for cut, levels in CUTS.items():
        inn = {pid for pid, p in notes.items() if p.get("confidence", "low") in levels}
        hit = {k for k, pids in matched_keys.items() if pids & inn}
        groups = {"all": key["notes"], "judgement": [k for k in key["notes"] if k["judgement"]],
                  "no tool": [k for k in key["notes"] if k["tool"].startswith("none")]}
        rec = {g: (sum(1 for k in ks if k["id"] in hit), len(ks)) for g, ks in groups.items()}
        matched_preds = {pid for pids in matched_keys.values() for pid in pids} & inn
        judged = matched_preds | {pid for pid in inn if real.get(pid) == "yes"}
        rows.append({"cut": cut, "n_pred": len(inn), "recall": rec, "prec_strict": (len(matched_preds), len(inn)),
                     "prec_judged": (len(judged), len(inn)), "unsure": sum(1 for pid in inn - matched_preds if real.get(pid) == "unsure")})
    return pred.get("model", m.get("run", "?")), rows


def pct(x):
    return f"{x[0]}/{x[1]} = {100 * x[0] / x[1]:.0f}%" if x[1] else "-"


def score(a):
    key = load(a.key)
    out = [f"# Reviewer's eye score: {key['video']} ({len(key['notes'])} notes of the creator's; "
           f"{sum(1 for k in key['notes'] if k['judgement'])} judgement; {sum(1 for k in key['notes'] if k['tool'].startswith('none'))} no tool catches)\n",
           "| run | cut | predicted | recall all | recall judgement | recall no-tool | precision strict | precision judged |",
           "|---|---|---|---|---|---|---|---|"]
    for mp in a.match:
        m = load(mp)
        model, rows = score_run(key, m)
        for r in rows:
            out.append(f"| {m.get('run', model)} | {r['cut']} | {r['n_pred']} | {pct(r['recall']['all'])} | {pct(r['recall']['judgement'])} | "
                       f"{pct(r['recall']['no tool'])} | {pct(r['prec_strict'])} | {pct(r['prec_judged'])}"
                       f"{' (' + str(r['unsure']) + ' unsure)' if r['unsure'] else ''} |")
    text = "\n".join(out) + "\n"
    print(text)
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8")


def merge(a):
    """The parts' and the whole pass's notes as one run: sorted by time, numbered again, each with the part it came from."""
    notes, video, model = [], "", ""
    for src in a.parts:
        d = load(src)
        video, model = d.get("video", video), d.get("model", model)
        for n in d["notes"]:
            n = dict(n, part=Path(src).stem)
            notes.append(n)
    notes.sort(key=lambda n: (secs(n["t"]) or 0.0, n.get("part", "")))
    for i, n in enumerate(notes, 1):
        n["src_id"], n["id"] = n["id"], i
    Path(a.out).write_text(json.dumps({"video": video, "model": model, "notes": notes}, indent=1, ensure_ascii=False), encoding="utf-8")
    with Path(a.out).with_suffix(".md").open("w", encoding="utf-8") as f:
        f.write(f"# Reviewer's eye notes: {video} ({model}, {len(notes)} notes)\n\n")
        for n in notes:
            f.write(f"- **{n['t']}**{'-' + n['t_end'] if n.get('t_end') else ''} [{n['confidence']}] {n['what']} *Fix:* {n['fix']} "
                    f"({n['rule']})\n")
    print(f"{len(notes)} notes -> {a.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("merge")
    g.add_argument("out")
    g.add_argument("parts", nargs="+")
    c = sub.add_parser("candidates")
    c.add_argument("key")
    c.add_argument("pred")
    c.add_argument("--window", type=float, default=5.0)
    s = sub.add_parser("score")
    s.add_argument("key")
    s.add_argument("match", nargs="+")
    s.add_argument("--md")
    a = ap.parse_args()
    {"candidates": candidates, "score": score, "merge": merge}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
