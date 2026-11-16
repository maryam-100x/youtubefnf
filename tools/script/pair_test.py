"""The pair test: style only. A real creator's passage and ours on the SAME content, side by side; the judge picks the human one.
50% = the wording can't be told apart; 100% = always caught. It measures the lingo, the sentence structure and the natural way of
talking, not who has opinions (the judge panel's blind test mixes both).

  PIPE tools/script/pair_test.py make <set> --content <content.json> --ours <file>@<method> ... [--validation <validation.json>] [--per 6] [--reps 2]
  PIPE tools/script/pair_test.py brief <set> <packet>             # the prompt for a clean judge agent (Explore type; it answers inline)
  PIPE tools/script/pair_test.py score <set> [--features]          # per method: how often the human is picked, per content; stylometrics

The repo ships no content or validation sets: the chat builds the creator's own from the niche's human corpus
(tools/script/human_corpus.py), in MEDIA/script/panel/<set>/:
  content.json: [{"cid", "clean": the human passage cleaned of caption noise only, "points": its content as neutral notes}]: pick
      6-12 passages of about 160 words from the corpus (different creators), clean each by hand, write its points; the writer under
      test gets only the points and writes one passage per line, in the content's order (the ours file, "<file>@<method>")
  validation.json: [{"vid", "a": {"channel", "text"}, "b": {...}}], two different human creators on the same content: their "human
      picked" share must sit near 50% (the test itself works)
Score: P(human picked) per judgment = confidence/100 when the judge picks the human, 1 - confidence/100 when it picks ours.
Pass: at or under 0.60 on every content. Creators' words stay in the media root, never in git."""
import argparse
import json
import random
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
import blind_test as B   # noqa: E402
from paths import MEDIA  # noqa: E402

ROOT = MEDIA / "script" / "panel"
KEYS = MEDIA / "script" / "blind_keys" / "panel"

BRIEF = """# Pair test {name}

Each item below has two transcripts, A and B, of YouTube narration (videos on {topics}) that say the same things. One is the real
transcript of a human YouTuber, cleaned of speech-to-text errors; the other was written by an AI from notes of the same content.
Both went through the same clean-up (numbers as digits). Decide from the wording alone (word choice, sentence structure, rhythm, the
way it talks) which one the human said. Do not use any tools or search. Answer with a JSON list only:
[{{"id": "Q1", "human": "A", "confidence": 70, "tells": "the 1-3 things that decided it"}}, ...]
Confidence is 50 (a coin flip) to 100 (certain).

"""


def make(name, content, ours, validation, per, reps, seed):
    rng = random.Random(seed)
    d = ROOT / name
    (d / "packets").mkdir(parents=True, exist_ok=True)
    (KEYS / name).mkdir(parents=True, exist_ok=True)
    cont = json.loads(Path(content).read_text(encoding="utf-8"))
    pairs = []
    for spec in ours:
        path, _, method = spec.rpartition("@")
        lines = [x for x in Path(path).read_text(encoding="utf-8").split("\n") if len(x.split()) > 30]
        for c, t in zip(cont, lines):
            pairs.append({"kind": method, "cid": c["cid"], "human": B.normalise(c["clean"]), "ours": B.normalise(t)})
    if validation:
        for v in json.loads(Path(validation).read_text(encoding="utf-8")):
            pairs.append({"kind": "validation_human_vs_human", "cid": v["vid"], "human": B.normalise(v["a"]["text"]),
                          "ours": B.normalise(v["b"]["text"]), "who": f"{v['a']['channel']} vs {v['b']['channel']}"})
    (d / "pairs.json").write_text(json.dumps(pairs, indent=1, ensure_ascii=False), encoding="utf-8")
    made = []
    cap = max(2, per // max(1, len({p["kind"] for p in pairs})))   # a method's pairs spread over the packets
    for rep in range(1, reps + 1):
        order = pairs[:]
        rng.shuffle(order)
        bins = []
        for p in order:   # one content per packet, methods spread
            for b in bins:
                if len(b) < per and all(x["cid"] != p["cid"] for x in b) and sum(x["kind"] == p["kind"] for x in b) < cap:
                    b.append(p)
                    break
            else:
                bins.append([p])
        for k, b in enumerate(bins, 1):
            pname = f"r{rep}_p{k:02d}"
            lines, key = [BRIEF.format(name=f"{name}/{pname}", topics=B.topics())], {}
            for j, p in enumerate(b, 1):
                human_is_a = rng.random() < 0.5
                a, bb = (p["human"], p["ours"]) if human_is_a else (p["ours"], p["human"])
                lines.append(f"## Q{j}\n**A:** {a}\n\n**B:** {bb}\n")
                key[f"Q{j}"] = {"pair": pairs.index(p), "human": "A" if human_is_a else "B"}
            (d / "packets" / f"{pname}.md").write_text("\n".join(lines), encoding="utf-8")
            (KEYS / name / f"{pname}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
            made.append(pname)
    print(f"{len(pairs)} pairs, {len(made)} packets: {', '.join(made)}  ({d / 'packets'})")


def brief(name, pname):
    d = ROOT / name
    print(f"Read the file {d / 'packets' / (pname + '.md')} and do exactly what it asks, from the wording alone. Do not open, list or "
          f"search any other file or folder, and do not search the web. Reply with the JSON list only, on one line, each \"tells\" at "
          f"most 8 words.\n(save the answer to {d / 'verdicts' / (pname + '__<judge>.json')})")


def load(name):
    d = ROOT / name
    pairs = json.loads((d / "pairs.json").read_text(encoding="utf-8"))
    res = {}   # pair index -> [(judge, p_human_picked, tells)]
    for f in sorted((d / "verdicts").glob("*__*.json")):
        pname, judge = f.stem.split("__", 1)
        key = json.loads((KEYS / name / f"{pname}.json").read_text(encoding="utf-8"))
        m = re.search(r"\[.*\]", f.read_text(encoding="utf-8"), re.S)
        for v in json.loads(m.group(0)) if m else []:
            k = key.get(str(v.get("id")))
            if not k:
                continue
            c = min(100.0, max(50.0, float(v.get("confidence", 50)))) / 100
            right = str(v.get("human", "")).strip().upper()[:1] == k["human"]
            res.setdefault(k["pair"], []).append((judge, c if right else 1 - c, str(v.get("tells", ""))))
    return pairs, res


def score(name, features=False):
    pairs, res = load(name)
    kinds = sorted({p["kind"] for p in pairs})
    cids = sorted({p["cid"] for p in pairs if not p["kind"].startswith("validation")})
    print(f"P(the human picked), every judgment; pass = at or under 0.60 on every content\n{'method':<26} {'mean':>5} {'picked':>6} "
          + " ".join(f"{c:>4}" for c in cids) + "  passed")
    for k in kinds:
        idx = [i for i, p in enumerate(pairs) if p["kind"] == k]
        allv = [x for i in idx for _, x, _ in res.get(i, [])]
        if not allv:
            continue
        if k.startswith("validation"):
            per = [f"{pairs[i]['cid']} {st.mean(x for _, x, _ in res[i]):.2f}" for i in idx if i in res]
            print(f"{k:<26} {st.mean(allv):>5.2f} {sum(x > 0.5 for x in allv) / len(allv):>6.0%}  (a picked; 0.50 = can't tell two humans apart) "
                  + ", ".join(per))
            continue
        cells, ok = [], 0
        for c in cids:
            v = [x for i in idx if pairs[i]["cid"] == c for _, x, _ in res.get(i, [])]
            cells.append(f"{st.mean(v):.2f}" if v else "  - ")
            ok += bool(v) and st.mean(v) <= 0.60
        print(f"{k:<26} {st.mean(allv):>5.2f} {sum(x > 0.5 for x in allv) / len(allv):>6.0%} " + " ".join(f"{x:>4}" for x in cells)
              + f"  {ok}/{len(cids)}")
    if features:
        import voice_metrics as V
        keys = ["wps", "wps_sd", "long_share", "short_share", "contractions", "markers_all", "open_and", "open_so", "open_but",
                "open_the", "i", "you", "we", "q", "evaluative", "explainer_all", "triplet", "llm_all", "numbers", "word_len", "mattr",
                "content_share", "even_rhythm", "just", "really", "actually"]
        rows = []
        for i, p in enumerate(pairs):
            if p["kind"].startswith("validation") or i not in res:
                continue
            fh, fo = V.features(p["human"]), V.features(p["ours"])
            rows.append(({k: fo.get(k, 0) - fh.get(k, 0) for k in keys}, st.mean(x for _, x, _ in res[i])))
        print(f"\nwhich wording differences (ours minus the human's, same content) go with the judges catching us: r over {len(rows)} pairs")
        out = []
        for k in keys:
            xs = [r[0][k] for r in rows]
            ys = [r[1] for r in rows]
            if len(xs) > 1 and st.pstdev(xs) > 0:
                out.append((st.correlation(xs, ys), k, st.mean(xs)))
        for r, k, m in sorted(out, key=lambda t: -abs(t[0])):
            print(f"  {k:<14} r = {r:+.2f}   (ours minus human, mean {m:+.2f})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("name")
    m.add_argument("--content", required=True)
    m.add_argument("--ours", nargs="+", required=True)
    m.add_argument("--validation")
    m.add_argument("--per", type=int, default=6)
    m.add_argument("--reps", type=int, default=2)
    m.add_argument("--seed", type=int, default=1)
    b = sub.add_parser("brief")
    b.add_argument("name")
    b.add_argument("packet")
    s = sub.add_parser("score")
    s.add_argument("name")
    s.add_argument("--features", action="store_true")
    a = ap.parse_args()
    if a.cmd == "make":
        make(a.name, a.content, a.ours, a.validation, a.per, a.reps, a.seed)
    elif a.cmd == "brief":
        brief(a.name, a.packet)
    else:
        score(a.name, a.features)


if __name__ == "__main__":
    main()
