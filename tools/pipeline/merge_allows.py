"""merge_allows.py: fold the parts' allow files (rebuild/allow_<part>.json, written by the section owners in a gate fix round so no two
agents edit one file) into the video's gate_allow.json. Entries are {"check", "key", "reason"}; the same (check, key) keeps the newest
reason. Idempotent: run it again after more parts report.
When rebuild/ranges.json names each part's frames ({"a": [f0, f1], ...}), every entry from allow_<part>.json carries "frames" (its part's,
+-120) and gate.allowed() matches it only to a flag starting inside them (keys match as substrings, so a one-word key like 'shoot'
without frames would silence the same word's flag anywhere in the film).

  PIPE tools/pipeline/merge_allows.py 012-city-at-night
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import VIDEOS_REPO  # noqa: E402


def main(slug):
    folder = VIDEOS_REPO / slug
    target = folder / "gate_allow.json"
    base = json.loads(target.read_text(encoding="utf-8")) if target.exists() else []
    rp = folder / "rebuild" / "ranges.json"
    ranges = {k: v for k, v in json.loads(rp.read_text(encoding="utf-8")).items() if not k.startswith("_")} if rp.exists() else {}
    parts = sorted((folder / "rebuild").glob("allow_*.json"))
    if ranges:
        # entries merged before the ranges existed carry no frames: drop those the part files hold, they come back with their frames
        from_parts = set()
        for f in parts:
            ents = json.loads(f.read_text(encoding="utf-8"))
            ents = ents.get("allows") or ents.get("entries") or [] if isinstance(ents, dict) else ents
            from_parts |= {(e.get("check"), e.get("key")) for e in ents if isinstance(e, dict)}
        before = len(base)
        # every entry a part file holds comes back from it with its part's CURRENT frames, whatever frames its older copy had (a new
        # voice moves the ranges by hundreds of frames: keeping the old copies would double the entries, each on its old window)
        base = [e for e in base if (e.get("check"), e.get("key")) not in from_parts]
        if before != len(base):
            print(f"  {before - len(base)} older entries dropped (their parts re-add them with the parts' current frames)")
    seen = {(e.get("check"), e.get("key"), tuple(e.get("frames") or ())): i for i, e in enumerate(base)}
    added = replaced = 0
    for f in parts:
        try:
            entries = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            raise SystemExit(f"{f.name}: not valid JSON ({e})")
        if isinstance(entries, dict):
            entries = entries.get("allows") or entries.get("entries") or []
        for e in entries:
            if not (isinstance(e, dict) and e.get("check") and e.get("key") and e.get("reason")):
                raise SystemExit(f"{f.name}: an entry without check/key/reason: {e}")
            part = f.stem.split("_", 1)[1]
            # an entry that names its own frames keeps them (an allow on a clip other parts play too sits on its flag's own frames:
            # the part's range +-120 would reach into the next part and silence that part's flag there)
            if part in ranges and not e.get("frames"):
                f0, f1 = ranges[part]
                e = dict(e, frames=[max(0, f0 - 120), f1 + 120])
            k = (e["check"], e["key"], tuple(e.get("frames") or ()))
            if k in seen:
                base[seen[k]] = e
                replaced += 1
            else:
                seen[k] = len(base)
                base.append(e)
                added += 1
        print(f"  {f.name}: {len(entries)} entries")
    target.write_text(json.dumps(base, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"gate_allow.json: {len(base)} entries ({added} added, {replaced} replaced)")


if __name__ == "__main__":
    main(sys.argv[1])
