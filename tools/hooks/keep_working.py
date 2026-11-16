"""Keep working: the Stop hook that keeps a chat from going idle in the middle of work the creator asked for. "Keep going until it's
done" written down as a rule gets broken; a rule the model has to remember is no fix, so this runs every time a desktop chat in this
folder tries to end its turn and refuses the stop while the next step is still the chat's own.

The idea: when the creator asks for something, the chat does it and stops only once it is done, or at a wall where it cannot go on
without the creator. It never stops in between just to report. But the hook never makes a chat work around the clock either: a chat
that is done, or told "not yet", is never pushed to invent work nobody asked for. Only the work the creator asked for counts, and the
chat's task list (the app's update_plan) is where that work is.

The stop is blocked only when ALL of these hold (read from the chat's own transcript, no model):
  - the chat is on a task list: this turn set or moved it (update_plan), or the turn was started by its own job's notification;
    a turn the creator started where the chat never touched the list (a question, "wait", "not yet", a new subject) is never blocked,
    and the old list is parked when that turn ends;
  - and it shows work still undone: steps not done on the list (at a wrap_up, those still "pending", never started; with no wrap_up,
    every step not "completed"), or a wrap-up recap that still names the chat's own next steps ("Next: ...", "comes after", "still
    needs"), or, in a turn its own job's notification started, it worked and went quiet with no wrap-up at all;
  - the last wrap_up asks the creator nothing (an `ask` = the next step is the creator's: a decision, a go-ahead, notes on a sample);
  - the next step on the list is not the creator's: a step whose text starts with "You:" (an account, a key, a choice, their notes)
    and is the in-progress one (or, with none in progress, the first not done) means the chat waits on them, so the stop passes
    (the app may have no wrap_up: the list is how a chat says "your turn" there);
  - no job the chat launched in the background (Bash run_in_background, an async Agent, a Monitor) is still running (open for at
    most 4 h; a persistent Monitor never counts);
  - it is a desktop chat (headless `claude -p` runs are never touched).
A step that is really done but was never ticked is cleared by marking it (update_plan done); a step that was dropped, by a new list.
Ticking steps done after a wrap-up keeps that wrap-up as the last word, and another chat's message (origin "peer") starts a turn of its
own, like the creator's (so a peer-started turn never runs on as the previous notification's turn).
A turn is blocked at most 3 times; the 4th stop passes with a line to the creator, so a stuck chat can never loop forever.

  .claude/settings.json -> hooks.Stop: "<PIPE>" tools/hooks/keep_working.py --hook   (reads the hook's JSON on stdin; written by
                                                                                    tools/hooks/install_hooks.py)
  PIPE tools/hooks/keep_working.py <transcript.jsonl>   what the hook would have decided at the transcript's last record (a dry run,
                                                         nothing written); cut a transcript with head -n to replay any past stop
State per session in TMP/keep_working/<session>.json (incremental, like chat_health.py); every decision is logged to log.txt there.
"""
import json
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
    from paths import TMP  # noqa: E402
except Exception:  # noqa: BLE001  (a hook never fails on its own set-up: the system temp folder stands in)
    TMP = Path(tempfile.gettempdir())

STATE = Path(TMP) / "keep_working"
FIRST_READ = 40 * 2**20          # a first run reads only the transcript's last 40 MB (a long chat's transcript can pass 700 MB)
OPEN_MAX_S = 4 * 3600            # a background job with no notification after 4 h counts as gone
MAX_BLOCKS = 3                   # per turn; then the stop passes with a line to the creator
READ_ONLY = {"Read", "Grep", "Glob", "ToolSearch", "ReadNotifications", "WebSearch", "WebFetch", "Skill", "ListAgents",
             "mcp__ccd_turn__wrap_up", "mcp__ccd_session_mgmt__list_sessions", "mcp__ccd_session_mgmt__get_session",
             "mcp__ccd_session_mgmt__get_usage", "mcp__Claude_Browser__get_page_text", "mcp__Claude_Browser__read_page",
             "mcp__Claude_Browser__find", "mcp__Claude_Browser__tabs_context"}
# a wrap-up recap that still lists the chat's own next steps ("Next: the breath fixes, the voice check, then the prototype."); a step
# that is the creator's goes in the wrap-up's ask instead
NEXT = re.compile(r"\bnext\s*[:\-–—]|\bcomes? (?:after|next)\b|\bstill (?:to do|needs?|left)\b|\bleft to do\b|"
                  r"\bnot (?:done|built|run|started|finished) yet\b", re.I)
YOURS = re.compile(r"^\s*(?:you|your (?:part|turn)|creator)\s*[:\-–—]", re.I)   # a step that is the creator's to do
NOTE = re.compile(r"<task-id>([^<]+)</task-id>(.*?)</task-notification>", re.S)
DONE = re.compile(r"<status>(completed|failed|killed|stopped|cancelled|error)</status>|<event>\[Monitor expired")


def ts_of(rec):
    try:
        return datetime.fromisoformat(rec["timestamp"].replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def closed(st, text):
    """A notification ends its job: a final status, or a Monitor's expiry (its events carry no status)."""
    for tid, body in NOTE.findall(text):
        if DONE.search(body):
            st["open"].pop(tid, None)


def new_turn(uuid, origin):
    return {"uuid": uuid, "origin": origin, "work": False, "tools": [], "wrapped": False, "ask": None, "planned": False,
            "wrap_open": []}


def plan_update(st, inp):
    """Follow the app's task list: a new list, advance, done [n], start n (1-based), as update_plan's own rules."""
    items = inp.get("items")
    if isinstance(items, list):
        st["plan"] = [{"c": str(i.get("content", ""))[:60], "s": i.get("status", "pending")} for i in items if isinstance(i, dict)]
        return
    plan = st.setdefault("plan", [])
    if inp.get("advance"):
        for s in plan:
            if s["s"] == "in_progress":
                s["s"] = "completed"
                break
        for s in plan:
            if s["s"] == "pending":
                s["s"] = "in_progress"
                break
    for i in inp.get("done") or []:
        if isinstance(i, int) and 1 <= i <= len(plan):
            plan[i - 1]["s"] = "completed"
    k = inp.get("start")
    if isinstance(k, int) and 1 <= k <= len(plan):
        plan[k - 1]["s"] = "in_progress"


def feed(st, rec):
    """Update the state with one transcript record."""
    typ = rec.get("type")
    if rec.get("timestamp"):
        st["last"] = ts_of(rec)
    if rec.get("entrypoint"):
        st["entry"] = rec["entrypoint"]
    if typ == "user":
        msg = rec.get("message") or {}
        content = msg.get("content")
        origin = (rec.get("origin") or {}).get("kind")
        if isinstance(content, str) and content.lstrip().startswith("<task-notification>"):
            closed(st, content)
        if origin in ("human", "task-notification", "peer") and not (isinstance(content, list) and content and
                                                             isinstance(content[0], dict) and content[0].get("type") == "tool_result"):
            st["turn"] = new_turn(rec.get("uuid"), origin)
        r = rec.get("toolUseResult")
        if isinstance(r, dict):
            tid = r.get("backgroundTaskId") or (r.get("agentId") if r.get("isAsync") else None) or \
                (r.get("taskId") if not r.get("persistent") else None)
            if tid:                            # open until its end notification, at most until its timeout or 4 h
                st["open"][tid] = ts_of(rec) + min(OPEN_MAX_S, (r.get("timeoutMs") or 1e12) / 1000)
    elif typ == "attachment":
        a = rec.get("attachment") or {}
        p = a.get("prompt")
        if isinstance(p, str) and p.lstrip().startswith("<task-notification>"):
            closed(st, p)
    elif typ == "assistant":
        for b in (rec.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            t = st["turn"]
            t["tools"].append(name)
            if name == "mcp__ccd_turn__wrap_up":
                t["wrapped"], t["ask"] = True, (inp.get("ask") or "").strip() or None
                t["recap"] = str(inp.get("recap") or "")
                t["wrap_open"] = [s["c"] for s in st.get("plan", []) if s["s"] == "pending"]
                for s in st.get("plan", []):           # the wrap-up ticks the list off in the app
                    s["s"] = "completed"
            elif name == "mcp__ccd_turn__update_plan":
                plan_update(st, inp)
                t["planned"] = True
                if t["wrapped"] and not isinstance(inp.get("items"), list) and not inp.get("advance") and not inp.get("start"):
                    # only ticking steps off after a wrap-up (this hook's own advice: "mark it done and stop"): the wrap-up
                    # stays the last word, minus the steps just marked
                    plan = st.get("plan", [])
                    ticked = {plan[i - 1]["c"] for i in inp.get("done") or [] if isinstance(i, int) and 1 <= i <= len(plan)}
                    t["wrap_open"] = [c for c in t.get("wrap_open", []) if c not in ticked]
                else:
                    t["wrapped"], t["ask"] = False, None   # a list moved after a wrap-up: that wrap-up is no longer the last word
            elif name not in READ_ONLY:
                t["work"] = True


def load(sid):
    p = STATE / f"{sid}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"offset": None, "open": {}, "turn": new_turn(None, None), "blocks": {}, "entry": None, "plan": []}


def scan(st, path):
    size = Path(path).stat().st_size
    off = st["offset"]
    if off is None or off > size:
        off = max(0, size - FIRST_READ)
    with open(path, "rb") as fh:
        fh.seek(off)
        if off and st["offset"] is None:
            fh.readline()                      # a first read starts mid-file: skip to a line end
            off = fh.tell()
        for raw in fh:
            if not raw.endswith(b"\n"):
                break                          # a line still being written waits for the next run
            off += len(raw)
            if b'"type":"api-request-blob"' in raw[:200] or b'"type":"last-prompt"' in raw[:200]:
                continue
            try:
                feed(st, json.loads(raw))
            except Exception:
                continue
    st["offset"] = off


def decide(st, now=None):
    """(allow, why)."""
    now = now or time.time()
    if st.get("entry") and st["entry"] != "claude-desktop":
        return True, f"not a desktop chat ({st['entry']})"
    t = st["turn"]
    t.setdefault("planned", False)
    t.setdefault("wrap_open", [])
    running = [k for k, until in st["open"].items() if now < until]
    if t["ask"]:
        return True, "the wrap-up asks the creator: " + t["ask"][:80]
    if running:
        return True, "background job(s) running: " + ", ".join(running[:4])
    if not t["planned"] and t["origin"] != "task-notification":
        return True, "not on a task list this turn (the creator's question, a 'wait', or done)"
    plan = st.get("plan", [])
    nxt = next((s for s in plan if s["s"] == "in_progress"), None) or next((s for s in plan if s["s"] != "completed"), None)
    if nxt and YOURS.match(nxt["c"]):
        return True, "the next step is the creator's: " + nxt["c"]
    left = t["wrap_open"] if t["wrapped"] else [s["c"] for s in st.get("plan", []) if s["s"] != "completed"]
    if left:
        return False, f"your task list for what the creator asked still has {len(left)} step(s) not done ({'; '.join(left[:4])})"
    if t["wrapped"]:
        m = NEXT.search(t.get("recap") or "")
        if m:
            return False, f"your wrap-up still names work of yours to do (\"{m.group(0)}\")"
        return True, "every step on the task list is done"
    if t["origin"] == "task-notification" and t["work"]:
        return False, "you went quiet in the middle of your own work (no wrap-up after your job's notification)"
    return True, "every step on the task list is done"


def settle(st, allow):
    """A turn the creator started that ends without touching the list parks it: the new message may have changed the work."""
    t = st["turn"]
    if allow and not t.get("planned") and t["origin"] == "human":
        st["plan"] = []


def log(line):
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / "log.txt", "a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")


def hook():
    try:
        inp = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return
    path, sid = inp.get("transcript_path"), inp.get("session_id") or "unknown"
    if not path or not Path(path).exists():
        return
    STATE.mkdir(parents=True, exist_ok=True)
    st = load(sid)
    scan(st, path)
    allow, why = decide(st)
    settle(st, allow)
    key = st["turn"]["uuid"] or "?"
    n = st["blocks"].get(key, 0)
    out = None
    if allow:
        log(f"{sid[:8]} ALLOW {why}")
    elif n >= MAX_BLOCKS:
        log(f"{sid[:8]} ALLOW after {n} blocks: {why}")
        out = {"systemMessage": f"Stop hook (keep_working): this chat ended its turn after {n} warnings that the next step was its own "
                                f"({why})."}
    else:
        st["blocks"] = {key: n + 1}            # only the current turn's count is kept
        log(f"{sid[:8]} BLOCK {n + 1}/{MAX_BLOCKS} {why}")
        out = {"decision": "block",
               "reason": (f"keep_working hook (block {n + 1}/{MAX_BLOCKS}): you are ending the turn, but {why}. "
                          "What the creator asked for is finished before you stop, never paused just to report: do the next of those "
                          "steps now, with no message about it (the creator hears from you when there is something for them). If a step is "
                          "already done, mark it (update_plan done) and stop; if it "
                          "was dropped or the creator changed the work, give the list its real steps; if the next step is the "
                          "creator's (an account, a key, a choice, their notes), make it the in-progress step on the list as "
                          "\"You: <what they do>\" (update_plan) and stop, without writing your message again (they have it). "
                          "Never start anything the creator did not ask for to get past this hook.")}
    (STATE / f"{sid}.json").write_text(json.dumps(st), encoding="utf-8")
    if out:
        print(json.dumps(out))


def dry(path):
    st = {"offset": None, "open": {}, "turn": new_turn(None, None), "blocks": {}, "entry": None, "plan": []}
    scan(st, path)
    allow, why = decide(st, st.get("last"))       # as of the transcript's last record: the moment it stopped
    t = st["turn"]
    print(f"entry {st['entry']}; turn from {t['origin']} {t['uuid']}; tools {len(t['tools'])} (work {t['work']}); "
          f"wrap_up {t['wrapped']} ask {t['ask']!r}; open jobs {st['open']}")
    print(("ALLOW " if allow else "BLOCK ") + why)


if __name__ == "__main__":
    if "--hook" in sys.argv:
        hook()
    else:
        for p in sys.argv[1:]:
            dry(p)
