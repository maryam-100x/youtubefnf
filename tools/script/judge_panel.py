"""The judge panel: several blind Claude judges, calibrated on many human
passages, for "does this narration read human?".

  PIPE tools/script/judge_panel.py pool <set> --human <id>[#n][@kind] ... --ours <file>[#para|#n][@kind] ... [--words 160] [--seed 1]
  PIPE tools/script/judge_panel.py packets <set> [--size 12] [--reps 2] [--seed 1] [--kinds k1,k2] [--tag r1]
  PIPE tools/script/judge_panel.py packets <set> --test-per 1 --humans-per 7 --tag s   # sparse: few test passages among humans
  PIPE tools/script/judge_panel.py brief <set> <packet> [--judge opus_clean --clean]   # the prompt for a Claude judge agent
  PIPE tools/script/judge_panel.py gate <set> --ours <sections.txt> [--reshuffle]      # THE GATE: each section alone among 7 calibration humans
  PIPE tools/script/judge_panel.py score <set> [--kinds ...] [--items kind1,kind2] [--tag r1]

The calibration set (built once, before the first gate, from the creator's own human corpus: tools/script/human_corpus.py): a set
named "calibration" of about 28 human passages across the corpus groups (scripted, talk, voice-over, documentary), e.g.
  PIPE tools/script/judge_panel.py pool calibration --human <id>#1 <id>#1 <id>#2 ...
Every gate set starts from its human passages. The repo ships no corpus and no calibration set: both are the creator's niche's own.

pool: cuts passages (whole sentences, the middle of each text) from human corpus texts (`human_corpus.py` ids; every human text goes
through blind_test's declutter, so speech-to-text noise is no evidence) and from our texts (a script.md's VOICE lines or a plain text
file; `#para` = every paragraph one passage), puts every passage through blind_test's normalise (numbers, quotes), and saves the pool.
packets: shuffles the pool into packets of --size passages, the authors spread so no packet holds many passages of one author, each
passage once per rep (rep 2 in a new order and new company: test-retest). Keys stay in MEDIA/script/blind_keys/panel/.
Claude judges are agents: `brief` prints what to give one; it writes <packet>__<judge>.json itself.
score: per judge and kind, mean P(AI) (the judge's probability that the passage is AI: AI at 80 = 0.80, HUMAN at 80 = 0.20), the
share called AI, the AUC against all human passages (0.5 = the judge can't tell that kind from humans), the human percentile of the
kind's median, test-retest agreement; --items prints every passage of those kinds with each judge's number and the tells named.
Creators' words stay in the media root (MEDIA/script/panel/), never in git."""
import argparse
import json
import random
import re
import statistics as st
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "common"))
import blind_test as B   # noqa: E402  (normalise, declutter, passages, load_ours, topics)
from paths import MEDIA  # noqa: E402

ROOT = MEDIA / "script" / "panel"
KEYS = MEDIA / "script" / "blind_keys" / "panel"

BRIEF = """# Blind test {name}

You are judging transcripts of YouTube narration. They come from videos on {topics}. Some were written by an AI (a large language
model) for a channel; the others are transcripts of real human YouTubers talking or reading their own script. The share is unknown: it
can be anything from none to all. Every passage went through the same clean-up (numbers as digits, punctuation). Some human ones come
from speech-to-text and may contain a misheard word: do not use transcription slips as evidence either way.

For each passage decide AI or HUMAN from the wording alone. Do not use any tools or search; read and judge. Answer with a JSON list only:
[{{"id": "P1", "verdict": "AI", "confidence": 75, "tells": "the 1-3 phrases or habits that decided it"}}, ...]
Confidence is 50 (a coin flip) to 100 (certain).

"""


def author(it):
    return it["kind"] if not it["kind"].startswith("human") else it["source"].split(" (")[0]


def section(it):
    """Our passages of the same test section (source "<file> #k") share a section: they never sit in one packet."""
    m = re.search(r" #(\d+)$", it["source"])
    return m.group(1) if m and not it["kind"].startswith("human") else ""


# ---- pool ------------------------------------------------------------------------------------------------------------------------------
def pool(name, humans, ours, words, seed):
    import human_corpus as H
    rng = random.Random(seed)
    corpus = {h["id"]: (h, body) for h, body in H.load()}
    items = []
    for spec in humans:
        spec, _, kind = spec.partition("@")
        vid, _, cnt = spec.partition("#")
        vid = vid[3:] if vid.startswith("yt:") else vid
        if vid not in corpus:
            print(f"no corpus text for {vid}")
            continue
        h, body = corpus[vid]
        for t in B.passages(B.normalise(B.declutter(body)), int(cnt or 1), words, rng):
            items.append({"kind": kind or "human", "source": f"{h['channel']} ({vid}, {(h.get('upload_date') or '')[:4]})", "text": t})
    for spec in ours:
        spec, _, kind = spec.partition("@")
        path, _, cnt = spec.partition("#")
        raw = B.load_ours(path)
        if cnt == "para":   # every non-blank line is a section, numbered by its place ("-" holds a place for a missing one)
            chunks = [(k, B.normalise(p)) for k, p in enumerate([x for x in raw.split("\n") if x.strip()], 1) if len(p.split()) > 40]
        else:
            chunks = list(enumerate(B.passages(B.normalise(raw), int(cnt or 2), words, rng), 1))
        for k, t in chunks:
            items.append({"kind": kind or "ours", "source": f"{Path(path).stem} #{k}", "text": t})
    d = ROOT / name
    d.mkdir(parents=True, exist_ok=True)
    old = json.loads((d / "pool.json").read_text(encoding="utf-8")) if (d / "pool.json").exists() else []
    n0 = len(old)
    for k, it in enumerate(items):
        it["iid"] = f"i{n0 + k + 1:03d}"
    (d / "pool.json").write_text(json.dumps(old + items, indent=1, ensure_ascii=False), encoding="utf-8")
    kinds = {}
    for it in items:
        kinds[it["kind"]] = kinds.get(it["kind"], 0) + 1
    print(f"{len(items)} new passages ({n0} before) -> {d / 'pool.json'}  {kinds}")


# ---- packets ---------------------------------------------------------------------------------------------------------------------------
def write_packet(name, pname, pk):
    d = ROOT / name
    lines = [BRIEF.format(name=f"{name}/{pname}", topics=B.topics())]
    key = {}
    for j, it in enumerate(pk, 1):
        lines.append(f"## P{j}\n{it['text']}\n")
        key[f"P{j}"] = it["iid"]
    (d / "packets").mkdir(exist_ok=True)
    (d / "packets" / f"{pname}.md").write_text("\n".join(lines), encoding="utf-8")
    (KEYS / name).mkdir(parents=True, exist_ok=True)
    (KEYS / name / f"{pname}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")


def sparse_packets(name, test_per, humans_per, seed, kinds=None, tag="s", only=None):
    """Few test passages per packet among many humans (the company a passage keeps changes its score: the same passages scored
    0.55 among other methods and 0.74 among their own siblings): each packet holds at most one passage of each kind and of each
    section, topped up with humans drawn without repeats inside the packet. `only`: pack just these passage ids, in packets numbered
    after the ones already there (a second run that re-shuffled every packet would re-write their keys, so the first round's verdicts
    would be scored against passages their judges never read)."""
    d = ROOT / name
    items = json.loads((d / "pool.json").read_text(encoding="utf-8"))
    hum = [it for it in items if it["kind"].startswith("human")]
    test = [it for it in items if not it["kind"].startswith("human") and (not kinds or it["kind"] in kinds)
            and (only is None or it["iid"] in only)]
    rng = random.Random(seed)
    rng.shuffle(test)
    bins = []
    for it in sorted(test, key=lambda x: rng.random()):
        for b in bins:
            if len(b) < test_per and all(x["kind"] != it["kind"] and section(x) != section(it) for x in b):
                b.append(it)
                break
        else:
            bins.append([it])
    made = []
    have = [int(m.group(1)) for p in (d / "packets").glob(f"{tag}_p*.md") if (m := re.match(rf"{tag}_p(\d+)$", p.stem))] \
        if only is not None and (d / "packets").exists() else []
    k0 = max(have, default=0)
    for k, b in enumerate(bins, k0 + 1):
        pk = b + rng.sample(hum, min(humans_per, len(hum)))
        rng.shuffle(pk)
        pname = f"{tag}_p{k:02d}"
        write_packet(name, pname, pk)
        made.append(pname)
    print(f"{len(made)} packets ({test_per} test + {humans_per} humans at most): {', '.join(made)}")


CALIBRATION = "calibration"   # the set whose human passages (about 28: scripted, talk, voice-over, documentary) calibrate every gate


def gate(name, ours, seed, append=True):
    """The production gate: our passages (a plain text file, one section per line: whole beats of about 130-200 words), each alone in
    its own packet among 7 of the calibration humans. A second run on the same set packs only its own new passages, in packets numbered
    after the existing ones, so verdicts already saved still match their keys; --reshuffle (append=False) re-packs every passage and
    rewrites every key (old verdicts then score against passages their judges never read)."""
    d = ROOT / name
    cal_file = ROOT / CALIBRATION / "pool.json"
    if not cal_file.exists():
        sys.exit(f"no calibration set at {cal_file}: build it first from the human corpus:\n"
                 f"  PIPE tools/script/judge_panel.py pool {CALIBRATION} --human <id>#1 <id>#1 ...")
    d.mkdir(parents=True, exist_ok=True)
    cal = json.loads(cal_file.read_text(encoding="utf-8"))
    if not (d / "pool.json").exists():
        (d / "pool.json").write_text(json.dumps([it for it in cal if it["kind"].startswith("human")], indent=1, ensure_ascii=False),
                                     encoding="utf-8")
    before = {it["iid"] for it in json.loads((d / "pool.json").read_text(encoding="utf-8"))}
    pool(name, [], [f"{o}#para@{Path(o).stem}" if "#" not in o else o for o in ours], 160, seed)
    new = {it["iid"] for it in json.loads((d / "pool.json").read_text(encoding="utf-8"))} - before
    sparse_packets(name, 1, 7, seed, None, "g", only=new if append else None)
    print("\nJudge each packet with a clean agent (Explore type, model opus: no project files in its context), the prompt from\n"
          f"  judge_panel.py brief {name} g_pNN --judge opus_clean --clean\nthen: judge_panel.py score {name}  (pass: every passage at or "
          f"under 0.47)")


def packets(name, size, reps, seed, kinds=None, tag="r"):
    d = ROOT / name
    items = json.loads((d / "pool.json").read_text(encoding="utf-8"))
    if kinds:
        items = [it for it in items if it["kind"] in kinds or it["kind"].startswith("human")]
    rng = random.Random(seed)
    (KEYS / name).mkdir(parents=True, exist_ok=True)
    made = []
    for rep in range(1, reps + 1):
        n_pk = max(1, round(len(items) / size))
        by_author = {}
        for it in items:
            by_author.setdefault(author(it), []).append(it)
        order = []
        for a in sorted(by_author, key=lambda a: rng.random()):
            grp = by_author[a][:]
            rng.shuffle(grp)
            order += grp
        bins = [[] for _ in range(n_pk)]
        offset = rng.randrange(n_pk)
        for k, it in enumerate(order):   # round robin over authors grouped together: each author spread across packets;
            sec = section(it)            # never two versions of one section in a packet (a judge spots "a rewrite of P9")
            cands = [(k + offset + j) % n_pk for j in range(n_pk)]
            free = [b for b in cands if not sec or all(section(x) != sec for x in bins[b])]
            pick = min(free or cands, key=lambda b: (len(bins[b]), cands.index(b)))
            bins[pick].append(it)
        for b, pk in enumerate(bins, 1):
            rng.shuffle(pk)
            pname = f"{tag}{rep}_p{b:02d}"
            lines = [BRIEF.format(name=f"{name}/{pname}", topics=B.topics())]
            key = {}
            for j, it in enumerate(pk, 1):
                lines.append(f"## P{j}\n{it['text']}\n")
                key[f"P{j}"] = it["iid"]
            (d / "packets").mkdir(exist_ok=True)
            (d / "packets" / f"{pname}.md").write_text("\n".join(lines), encoding="utf-8")
            (KEYS / name / f"{pname}.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
            made.append(pname)
    print(f"{len(made)} packets of ~{size}: {', '.join(made)}  ({d / 'packets'})")


def brief(name, pname, judge, clean=False):
    d = ROOT / name
    if clean:   # an Explore agent can't write files: it answers with the JSON, and the chat saves it as <packet>__<judge>.json
        print(f"Read the file {d / 'packets' / (pname + '.md')} and do exactly what it asks: judge every passage, from the wording alone. "
              f"Do not open, list or search any other file or folder, and do not search the web. Reply with the JSON list only, on one "
              f"line; give \"tells\" (at most 6 words) only on passages you call AI.\n(save the answer to "
              f"{d / 'verdicts' / (pname + '__' + judge + '.json')})")
        return
    print(f"Read the file {d / 'packets' / (pname + '.md')} and do exactly what it asks: judge every passage, from the wording alone. "
          f"Use no other tool except to read that one file and to write your answer; do not open, list or search any other file or "
          f"folder, and do not search the web. Write your JSON list (and nothing else) to {d / 'verdicts' / (pname + '__' + judge + '.json')} "
          f"with the Write tool. Then reply with only the word done.")


# ---- scoring ---------------------------------------------------------------------------------------------------------------------------
def p_ai(v):
    ai = str(v.get("verdict", "")).upper().startswith("AI")
    try:
        conf = float(v.get("confidence", 50))
    except (TypeError, ValueError):
        conf = 50.0
    conf = min(100.0, max(50.0, conf))
    return conf / 100 if ai else 1 - conf / 100


def load_verdicts(name, tag=""):
    """{(iid, judge): [P(AI), ...]}, tells {(iid, judge): [str]}"""
    d = ROOT / name
    scores, tells = {}, {}
    for f in sorted((d / "verdicts").glob(f"{tag}*__*.json")):
        pname, judge = f.stem.split("__", 1)
        kf = KEYS / name / f"{pname}.json"
        if not kf.exists():
            continue
        key = json.loads(kf.read_text(encoding="utf-8"))
        m = re.search(r"\[.*\]", f.read_text(encoding="utf-8"), re.S)
        if not m:
            print(f"unreadable: {f.name}")
            continue
        try:
            vs = json.loads(m.group(0))
        except json.JSONDecodeError:
            print(f"bad json: {f.name}")
            continue
        for v in vs:
            iid = key.get(str(v.get("id", "")).strip())
            if not iid:
                continue
            scores.setdefault((iid, judge), []).append(p_ai(v))
            tells.setdefault((iid, judge), []).append(str(v.get("tells", "")))
    return scores, tells


def auc(pos, neg):
    """P(a random passage of `pos` gets a higher P(AI) than a random human one); ties count half."""
    if not pos or not neg:
        return float("nan")
    s = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return s / (len(pos) * len(neg))


def score(name, kinds=None, items=None, tag=""):
    d = ROOT / name
    pool_ = {it["iid"]: it for it in json.loads((d / "pool.json").read_text(encoding="utf-8"))}
    scores, tells = load_verdicts(name, tag)
    judges = sorted({j for _, j in scores})
    allk = sorted({pool_[i]["kind"] for i, _ in scores})
    kinds = [k for k in (kinds or allk) if k in allk]
    item_mean = {}   # (iid, judge) -> mean over reps
    for (iid, j), v in scores.items():
        item_mean[(iid, j)] = st.mean(v)
    panel = {}   # iid -> mean over judges
    for iid in {i for i, _ in scores}:
        vs = [item_mean[(iid, j)] for j in judges if (iid, j) in item_mean]
        panel[iid] = st.mean(vs)
    cols = judges + ["PANEL"]
    print(f"{'kind':<20} {'n':>3}  " + "  ".join(f"{j[:13]:>13}" for j in cols) + "   (mean P(AI) / AUC vs all humans)")
    for k in kinds:
        ids = [i for i in panel if pool_[i]["kind"] == k]
        row = []
        for j in cols:
            if j == "PANEL":
                pos = [panel[i] for i in ids]
                neg = [panel[i] for i in panel if pool_[i]["kind"].startswith("human")]
            else:
                pos = [item_mean[(i, j)] for i in ids if (i, j) in item_mean]
                neg = [item_mean[(i, j)] for i in panel if pool_[i]["kind"].startswith("human") and (i, j) in item_mean]
            row.append(f"{st.mean(pos):.2f} / {auc(pos, neg):.2f}" if pos else "-")
        print(f"{k:<20} {len(ids):>3}  " + "  ".join(f"{r:>13}" for r in row))
    # test-retest: the same passage, the same judge, another packet
    pairs = [(v[0], v[1]) for v in scores.values() if len(v) >= 2]
    if len(pairs) > 5:
        a, b = zip(*pairs)
        r = st.correlation(a, b) if st.pstdev(a) and st.pstdev(b) else float("nan")
        flips = sum((x > 0.5) != (y > 0.5) for x, y in pairs) / len(pairs)
        print(f"\ntest-retest: {len(pairs)} passage-judge pairs, r = {r:.2f}, verdict flipped in {flips:.0%}, mean |diff| "
              f"{st.mean(abs(x - y) for x, y in pairs):.2f}")
    if len(judges) > 1:
        print("judge agreement (r over passages): " + ", ".join(
            f"{a}~{b} {st.correlation(*zip(*[(item_mean[(i, a)], item_mean[(i, b)]) for i in panel if (i, a) in item_mean and (i, b) in item_mean])):.2f}"
            for x, a in enumerate(judges) for b in judges[x + 1:]))
    hum = sorted(panel[i] for i in panel if pool_[i]["kind"].startswith("human"))
    if hum:
        print(f"humans on the panel: n={len(hum)}, 10th/50th/90th percentile {hum[len(hum) // 10]:.2f} / {st.median(hum):.2f} / "
              f"{hum[(9 * len(hum)) // 10]:.2f}")
    if items:
        for k in items.split(","):
            print(f"\n--- {k}")
            for iid in sorted(i for i in panel if pool_[i]["kind"] == k):
                nums = "  ".join(f"{j[:6]} {st.mean(scores[(iid, j)]):.2f}" for j in judges if (iid, j) in scores)
                tl = " | ".join(t for j in judges for t in tells.get((iid, j), []) if t)[:220]
                print(f"{iid} {pool_[iid]['source'][:26]:<26} panel {panel[iid]:.2f}  {nums}\n      {tl}")
    return panel, pool_


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pool")
    p.add_argument("name")
    p.add_argument("--human", nargs="*", default=[])
    p.add_argument("--ours", nargs="*", default=[])
    p.add_argument("--words", type=int, default=160)
    p.add_argument("--seed", type=int, default=1)
    k = sub.add_parser("packets")
    k.add_argument("name")
    k.add_argument("--size", type=int, default=12)
    k.add_argument("--reps", type=int, default=2)
    k.add_argument("--seed", type=int, default=1)
    k.add_argument("--kinds", default="")
    k.add_argument("--tag", default="r")
    k.add_argument("--test-per", type=int, default=0, help="sparse mode: this many test passages a packet (one per kind and section)")
    k.add_argument("--humans-per", type=int, default=8)
    b = sub.add_parser("brief")
    b.add_argument("name")
    b.add_argument("packet")
    b.add_argument("--judge", default="sonnet")
    b.add_argument("--clean", action="store_true", help="the prompt for a clean Explore-type judge (answers inline)")
    gt = sub.add_parser("gate")
    gt.add_argument("name")
    gt.add_argument("--ours", nargs="+", required=True)
    gt.add_argument("--seed", type=int, default=1)
    gt.add_argument("--reshuffle", action="store_true", help="re-pack every passage of the set and rewrite every key (verdicts already "
                    "saved no longer match); without it a second run packs only its new passages")
    s = sub.add_parser("score")
    s.add_argument("name")
    s.add_argument("--kinds", default="")
    s.add_argument("--items", default="")
    s.add_argument("--tag", default="")
    a = ap.parse_args()
    if a.cmd == "pool":
        pool(a.name, a.human, a.ours, a.words, a.seed)
    elif a.cmd == "packets" and a.test_per:
        sparse_packets(a.name, a.test_per, a.humans_per, a.seed, [x for x in a.kinds.split(",") if x] or None, a.tag)
    elif a.cmd == "packets":
        packets(a.name, a.size, a.reps, a.seed, [x for x in a.kinds.split(",") if x] or None, a.tag)
    elif a.cmd == "brief":
        brief(a.name, a.packet, a.judge, a.clean)
    elif a.cmd == "gate":
        gate(a.name, a.ours, a.seed, not a.reshuffle)
    else:
        score(a.name, [x for x in a.kinds.split(",") if x] or None, a.items, a.tag)


if __name__ == "__main__":
    main()
