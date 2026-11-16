"""Surprise: how predictable a narration is to a small language model, per word.

  EDIT tools/script/surprise.py <file> [<file> ...] [--model gpt2] [--words 170]
  EDIT tools/script/surprise.py --corpus [--groups script,ref] [--n 30]

LLM text is low-surprise and even; human text spikes (an odd word, a specific detail, a turn nobody saw coming). For each passage of
--words words it prints the mean surprisal (bits per token), its spread across sentences, and the share of tokens over 10 bits
("spikes"). Runs on the CPU with two threads (never beside a render: gpt2 takes ~0.5 GB of RAM). Files are script.md (VOICE lines) or
text; --corpus samples the human corpus (tools/script/human_corpus.py) for the comparison."""
import argparse
import math
import random
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load_model(name):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(2)
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(name)
    model.eval()
    return tok, model


def surprisal(text, tok, model):
    """Per-token surprisal in bits, with each token's character span."""
    import torch
    enc = tok(text, return_tensors="pt", return_offsets_mapping=True, truncation=True, max_length=1000)
    ids = enc["input_ids"]
    with torch.no_grad():
        logits = model(ids).logits[0]
    lp = torch.log_softmax(logits[:-1], dim=-1)
    tgt = ids[0, 1:]
    bits = (-lp[torch.arange(len(tgt)), tgt] / math.log(2)).tolist()
    spans = enc["offset_mapping"][0].tolist()[1:]
    return bits, spans


def profile(text, tok, model):
    bits, spans = surprisal(text, tok, model)
    if not bits:
        return {}
    # per-sentence means: a human narration swings between plain and surprising sentences
    ends = [m.end() for m in re.finditer(r"[.!?](\s|$)", text)] or [len(text)]
    sent, cur, k = [], [], 0
    for b, (a, _) in zip(bits, spans):
        while k < len(ends) and a >= ends[k]:
            if cur:
                sent.append(st.mean(cur))
            cur, k = [], k + 1
        cur.append(b)
    if cur:
        sent.append(st.mean(cur))
    return {"mean": round(st.mean(bits), 2), "sd_tokens": round(st.pstdev(bits), 2),
            "sd_sentences": round(st.pstdev(sent), 2) if len(sent) > 1 else 0.0,
            "spikes": round(sum(1 for b in bits if b > 10) / len(bits), 3), "tokens": len(bits)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--model", default="gpt2")
    ap.add_argument("--words", type=int, default=170)
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--groups", default="script,ref,tech,voice")
    ap.add_argument("--n", type=int, default=30)
    a = ap.parse_args()
    import blind_test as B
    tok, model = load_model(a.model)
    rng = random.Random(3)
    rows = []
    if a.corpus:
        import human_corpus as H
        groups = set(a.groups.split(","))
        texts = [(h, b) for h, b in H.load() if h.get("group") in groups and h.get("punctuated")]
        rng.shuffle(texts)
        for h, b in texts[:a.n]:
            for p in B.passages(B.normalise(B.declutter(b)), 1, a.words, rng):
                rows.append((f"human {h['channel']}"[:28], profile(p, tok, model)))
    for f in a.files:
        text = B.normalise(B.load_ours(f))
        chunks = [B.normalise(p) for p in B.load_ours(f).split("\n") if len(p.split()) > 40] if f.endswith(".txt") else \
            B.passages(text, 4, a.words, rng)
        for p in chunks:
            rows.append((Path(f).parent.name[:28] if f.endswith(".md") else Path(f).stem[:28], profile(p, tok, model)))
    for name, pr in rows:
        print(f"{name:<30} mean {pr['mean']:>5}  sd {pr['sd_tokens']:>5}  sent-sd {pr['sd_sentences']:>5}  spikes {pr['spikes']:>6}")
    by = {}
    for name, pr in rows:
        key = name.split(" ")[0] if name.startswith("human") else name
        by.setdefault(key, []).append(pr)
    print()
    for k, v in by.items():
        print(f"{k:<30} n={len(v):<3} mean {st.mean(x['mean'] for x in v):.2f}  sd {st.mean(x['sd_tokens'] for x in v):.2f}  "
              f"sent-sd {st.mean(x['sd_sentences'] for x in v):.2f}  spikes {st.mean(x['spikes'] for x in v):.3f}")


if __name__ == "__main__":
    main()
