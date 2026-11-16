"""Chat health: is this chat getting too long to work well? It reads the chat's own transcript and tells the chat (never the creator)
when its context is near the auto-compact, and after every compaction.

What a long chat costs:
- The context window is 1,000,000 tokens and auto-compact starts at 97% (the app's get_usage shows both). A compaction replaces the
  whole conversation with a summary of ~15-45K tokens. The study a new chat does (STANDARD.md) fills about half the window, so after
  the first compaction the chat no longer holds the standard, the rules or the creator's messages in full: it works from a summary.
- Every call re-reads the whole context (cached, but it counts against the plan's limits): a call at 900K tokens costs about twice one
  at 450K, so the weekly limits empty faster the longer a chat runs.

Levels (each from the transcript, no model needed):
  green  under 85% of the window and never compacted: keep working.
  amber  85% or more: the auto-compact comes at 97%; bring STATUS.md, the session log and HANDOFF.md up to date at the next checkpoint
         so the summary loses nothing. Not a reason to switch chats.
  red    compacted at least once: the study's detail is a summary; at once re-read STANDARD.md, the craft's standard file for the work in
         hand and STATUS.md (the SessionStart hook says so right after the compaction), and keep working. Not a reason to switch
         either: one compaction is no reason; a new chat is due when the chat got dumber and slower (the creator says so, or the chat
         sees it: a rule forgotten, the same mistake corrected twice).

  PIPE tools/hooks/chat_health.py <transcript.jsonl> [...]   a report per transcript (compactions with their times, context per call, the level)
  PIPE tools/hooks/chat_health.py --hook                     run by the UserPromptSubmit and SessionStart hooks (.claude/settings.json):
                                                             reads the hook's JSON on stdin and prints one line for the model only at amber
                                                             or red (once per 5% step, once per compaction); incremental, so a 700 MB
                                                             transcript costs one read
State per session in TMP/chat_health/<session>.json.
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from paths import TMP  # noqa: E402
except Exception:  # noqa: BLE001  (a hook never fails on its own set-up: the system temp folder stands in)
    TMP = Path(tempfile.gettempdir())

WINDOW = 1_000_000      # the model's context window in the desktop app (get_usage shows it; change it here if the chat's differs)
AMBER = 0.85            # bring the records up to date before the auto-compact (not a reason to switch)
AUTO_COMPACT = 0.97     # where the app compacts by itself (get_usage: autoCompactsAtPercent 97)
STATE = Path(TMP) / "chat_health"


def ctx_of(rec):
    """The context size of one model call: everything it read (new input + cache read + cache written)."""
    u = (rec.get("message") or {}).get("usage") or {}
    it = u.get("iterations") or []
    src = it[-1] if it else u
    return sum(int(src.get(k) or 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def scan(path, offset=0):
    """Read a transcript from `offset`: (calls [(ts, ctx)], compactions [(ts, pre, post)], first ts, new offset at a line end)."""
    calls, comps, first = [], [], None
    pos = offset
    with open(path, "rb") as fh:
        fh.seek(offset)
        lines = []
        for raw in fh:                   # streamed: a long chat's transcript can pass 700 MB
            if not raw.endswith(b"\n"):
                break                    # a line still being written waits for the next run
            pos += len(raw)
            lines.append(raw) if (b'"compact_boundary"' in raw or (b'"type":"assistant"' in raw and b'"usage"' in raw)
                                  or first is None) else None
            if first is None and lines:
                try:
                    first = json.loads(lines[0]).get("timestamp")
                except ValueError:
                    pass
    end = pos - offset
    for raw in lines:
        if not raw.strip():
            continue
        is_comp = b'"compact_boundary"' in raw
        is_call = b'"type":"assistant"' in raw and b'"usage"' in raw
        if not (is_comp or is_call or first is None):
            continue
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        ts = rec.get("timestamp")
        if first is None and ts:
            first = ts
        if rec.get("isSidechain"):
            continue                     # a subagent's own calls are not this chat's context
        if is_comp and rec.get("subtype") == "compact_boundary":
            m = rec.get("compactMetadata") or {}
            comps.append((ts, m.get("preTokens"), m.get("postTokens")))
        elif is_call and rec.get("type") == "assistant":
            c = ctx_of(rec)
            if c:
                calls.append((ts, c))
    return calls, comps, first, offset + end


def level(ctx, n_comp):
    if n_comp:
        return "red"
    return "amber" if ctx >= AMBER * WINDOW else "green"


def local(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return "?"


def report(path):
    calls, comps, first, _ = scan(path)
    last = calls[-1][1] if calls else 0
    print(f"\n{Path(path).name}  ({os.path.getsize(path) / 1e6:.0f} MB)  from {local(first)} to {local(calls[-1][0]) if calls else '?'}")
    print(f"  model calls: {len(calls)}   compactions: {len(comps)}   context now: {last:,} tokens ({last / WINDOW:.0%})   level: {level(last, len(comps))}")
    for ts, pre, post in comps:
        print(f"  compacted {local(ts)}: {pre:,} -> {post:,} tokens" if pre and post else f"  compacted {local(ts)}")
    if calls:
        cs = sorted(c for _, c in calls)
        print(f"  context per call: median {cs[len(cs) // 2]:,}, 90th pct {cs[int(len(cs) * 0.9)]:,}; calls over {AMBER:.0%}: "
              f"{sum(c >= AMBER * WINDOW for c in cs) / len(cs):.0%}; all calls together read {sum(cs) / 1e6:,.0f}M tokens")
        hit = next((ts for ts, c in calls if c >= AMBER * WINDOW), None)
        if hit:
            print(f"  first call over {AMBER:.0%}: {local(hit)}")


def hook():
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    path, sid = inp.get("transcript_path"), inp.get("session_id") or "unknown"
    if not path or not os.path.exists(path):
        return
    STATE.mkdir(parents=True, exist_ok=True)
    sf = STATE / f"{sid}.json"
    st = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {"offset": 0, "ctx": 0, "comps": [], "said": []}
    if os.path.getsize(path) < st["offset"]:   # a rewritten file: start over
        st = {"offset": 0, "ctx": 0, "comps": [], "said": []}
    calls, comps, _, st["offset"] = scan(path, st["offset"])
    if calls:
        st["ctx"] = calls[-1][1]
    st["comps"] += [c[0] for c in comps]
    lv = level(st["ctx"], len(st["comps"]))
    pct = st["ctx"] / WINDOW
    key = f"{lv}:{len(st['comps'])}:{int(pct * 20)}"   # say it once per compaction and once per 5% step
    msg = None
    if lv != "green" and key not in st["said"]:
        st["said"].append(key)
        if lv == "red":
            msg = (f"[chat health] This chat has been compacted {len(st['comps'])} time(s) (last {local(st['comps'][-1])}); the context is "
                   f"{pct:.0%} of {WINDOW // 1000}K. The study's detail is now a summary: before more work, re-read STANDARD.md, the "
                   "standard/ file of the craft in hand and STATUS.md, then keep working. Not a reason to switch chats: a new chat is "
                   "due only when this one got dumber and slower (the creator says so, or a rule was forgotten, the same mistake "
                   "corrected twice). Keep STATUS.md and HANDOFF.md current at checkpoints (tools/hooks/chat_health.py).")
        else:
            msg = (f"[chat health] This chat's context is {pct:.0%} of {WINDOW // 1000}K tokens (auto-compact at {AUTO_COMPACT:.0%}, which "
                   "drops everything to a ~24K summary). At the next checkpoint bring STATUS.md, the session log and HANDOFF.md up to "
                   "date so the summary loses nothing; not a reason to switch chats (tools/hooks/chat_health.py).")
    sf.write_text(json.dumps(st), encoding="utf-8")
    if msg:
        event = inp.get("hook_event_name") or "UserPromptSubmit"
        print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg}}))


def main():
    if "--hook" in sys.argv:
        try:
            hook()
        except Exception as e:            # a hook must never block the creator's prompt
            print(f"chat_health hook error: {type(e).__name__}", file=sys.stderr)
        return
    for p in sys.argv[1:]:
        report(p)


if __name__ == "__main__":
    main()
