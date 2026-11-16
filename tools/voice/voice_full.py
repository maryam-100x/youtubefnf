"""The whole voice of a long video through the voice lock's stage 1 (standard/VOICE_LOCK.md): the script cut into sections, every
section voiced by autopick.py (the lines-before way: the two script lines before the span voiced inside the same request, then cut
away; the first section after the house warm-up; judged by accent, names, both recognisers and the opening), one take a section
(--k 1: takes are mostly clean, so one a section and a new take only where a take fails a check, a new seed, up to --tries), then the
layout (proto_narration.py over the whole script). The chain, the gate and the lock follow:
`bash tools/sound/voice_chain.sh <video>` then `EDIT tools/voice/voice_lock.py <video> lock`.

Sections: the script's chapters (`# ===== NAME =====` lines in the beats block), cut on beat boundaries into requests of about --words
words (never over --max-words, never a beat split; a chapter under --min-words joins the next request). Written to
<dj>/build/voice/sections.json with script.md's hash; a section whose autopick record holds a pick made on the current script.md and
whose pieces are on disk is done (the run resumes). Each autopick run holds a heavy.py "score" ticket (Whisper, the CTC model and the
guard run inside it). A take that can't be made (span_takes fails, e.g. on the credits) is a wait, never a stop at once: the balance
checked every 3 minutes for 30 minutes, then the run stops and says so.

  EDIT tools/voice/voice_full.py <video> [--plan] [--jobs 3] [--k0 600]
      [--tries 2] [--words 150] [--max-words 200] [--min-words 60] [--only S10-S20] [--no-layout]"""
import argparse
import json
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "common"))
from paths import PY_EDIT, PY_PIPE, REPO, TOOLS, WINDOWS  # noqa: E402
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sound"))
sys.path.insert(0, str(HERE.parent / "pipeline"))
import gatelib as G  # noqa: E402
import voice_lock as VL  # noqa: E402

ED = str(PY_EDIT)
GT = str(PY_PIPE)
LOCK = threading.Lock()


def chapters(script):
    """[(chapter name, [(beat, words)])] from the beats block"""
    text = Path(script).read_text(encoding="utf-8")
    body = text[text.index("## Beats"):] if "## Beats" in text else text
    out = [["", []]]
    for line in body.splitlines():
        m = re.match(r"^#\s*=+\s*(.*?)\s*=+\s*$", line)
        if m:
            out.append([m.group(1), []])
            continue
        m = G.BEAT_RE.match(line)
        if m:
            out[-1][1].append((m.group(1), len(m.group(2).split())))
    return [c for c in out if c[1]]


def plan(script, target, most, least):
    secs, cur, cur_w = [], [], 0
    for name, beats in chapters(script):
        if cur and cur_w >= least:          # a chapter starts a new request, unless the one open is too short to stand alone
            secs.append(cur)
            cur, cur_w = [], 0
        for b, w in beats:
            if cur and (cur_w + w > most or (cur_w >= target and cur_w + w > target + 25)):
                secs.append(cur)
                cur, cur_w = [], 0
            cur.append(b)
            cur_w += w
    if cur:
        if len(secs) and cur_w < least:     # the last request too short: it joins the one before
            secs[-1] += cur
        else:
            secs.append(cur)
    return [{"first": s[0], "last": s[-1], "beats": s} for s in secs]


def span_sha(P, first, last):
    import hashlib
    beats = G.script_beats(P["script"])
    ids = [b for b, _ in beats]
    if first not in ids or last not in ids:
        return None
    return hashlib.sha256("\n".join(v for _, v in beats[ids.index(first):ids.index(last) + 1]).encode("utf-8")).hexdigest()


def record_valid(P, d, sha):
    """a record with a pick holds for its span while the span's own lines are unchanged (span_sha256; older records: made on this
    very script.md, and then their span hash is written in so a later edit elsewhere leaves them valid)"""
    if d.get("pick") is None:
        return False
    a, b = d["span"]
    now = span_sha(P, a, b)
    if d.get("span_sha256"):
        return d["span_sha256"] == now
    return d.get("script_sha256") == sha


def covered(P, sha):
    """{beat: (take k, record span)} from every autopick record with a pick valid for its span now (a section voiced as a whole or
    split into smaller spans: both count); the newest record wins a beat"""
    out, when = {}, {}
    ids = [b for b, _ in G.script_beats(P["script"])]
    for rec in sorted((P["dj"] / "build" / "voice" / "autopick").glob("*/autopick_*.json")):
        try:
            d = json.loads(rec.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not record_valid(P, d, sha):
            continue
        a, b = d["span"]
        if not d.get("span_sha256") and d.get("script_sha256") == sha:      # backfill: valid on this script, so its lines are these
            d["span_sha256"] = span_sha(P, a, b)
            try:
                rec.write_text(json.dumps(d, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
            except OSError:
                pass
        if a in ids and b in ids:
            for x in ids[ids.index(a):ids.index(b) + 1]:
                if x not in out or d.get("when", "") >= when[x]:
                    out[x], when[x] = (int(d["pick"]), f"{a}-{b}"), d.get("when", "")
    return out


def done(P, sec, sha, cov=None):
    """the section's take (its own record's pick), or "split" when smaller records cover every beat; None while a beat has no pick
    or its piece is missing"""
    cov = covered(P, sha) if cov is None else cov
    pdir = P["dj"] / "build" / "voice" / "patch"
    if not all(b in cov and (pdir / f"{b}_{cov[b][0]}.wav").exists() for b in sec["beats"]):
        return None
    spans = {cov[b][1] for b in sec["beats"]}
    return cov[sec["beats"][0]][0] if spans == {f"{sec['first']}-{sec['last']}"} else "split"


def credits_left():
    r = subprocess.run([GT, str(TOOLS / "voice" / "voice_credits.py")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"([\d,]+) credits left", r.stdout)
    return int(m.group(1).replace(",", "")) if m else None


def log(path, msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with LOCK:
        print(line, flush=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


LAUNCH = """import subprocess, sys, time
sys.path.insert(0, r"%s")
from heavy import HeavyJob, memory
# an autopick starts only while the memory commit is under 85%% (near 90%% the computer can crash; macOS: RAM + swap in use)
while True:
    ram, free, limit = memory()
    if (limit - free) / limit < 0.85:
        break
    print(f"commit {(limit - free) / limit:.0%%}: waiting for 85%%", flush=True)
    time.sleep(30)
with HeavyJob(sys.argv[1], "score"):
    sys.exit(subprocess.run(sys.argv[2:]).returncode)
""" % str(HERE.parent / "pipeline")


def voice_section(P, sec, a, sha, logf, state):
    first, last = sec["first"], sec["last"]
    with LOCK:
        state.setdefault("launched", set()).add(f"{first}-{last}")     # this run's own: never counted as in flight elsewhere
    for t in range(a.tries):
        k0 = a.k0 + t * 10                  # a new seed each try (span_takes: seed 9100 + k); a name's extra takes stay inside the 10
        quota_wait = 0
        while True:
            # each autopick under its own heavy.py ticket, held by its own launcher process (two jobs in one process shared one
            # pid's ticket on the first run)
            # respellings sent to ElevenLabs only (the take spells the script): the ones whose word is in this span
            text = " ".join(v for b, v in G.script_beats(P["script"]) if b in sec["beats"])
            say = [p for p in (a.say or []) if p.split("=", 1)[0] in text]
            r = subprocess.run([ED, "-c", LAUNCH, f"{P['video']} voice {first}-{last} take {k0}", ED, str(HERE / "autopick.py"),
                                P["video"], first, last, "--k", str(a.k), "--k0", str(k0)] + (["--say"] + say if say else []),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO))
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 3 or "span_takes failed" in out and re.search(r"quota|credit|401|429", out, re.I):
                if quota_wait >= 30 * 60:
                    log(logf, f"{first}-{last}: STOP, ElevenLabs refused for 30 min: {out[-300:]}")
                    state["stop"] = "credits"
                    return None
                log(logf, f"{first}-{last}: the take could not be made ({out.strip().splitlines()[-1][:160] if out.strip() else r.returncode}); "
                          f"credits {credits_left()}; retry in 3 min")
                time.sleep(180)
                quota_wait += 180
                continue
            break
        takes = re.findall(r"take (\d+): (CLEAN|REJECT[^\n]*)", out)
        for k, v in takes:
            log(logf, f"{first}-{last} take {k}: {v[:260]}")
        if r.returncode == 0:
            m = re.search(r"PICK: take (\d+)", out)
            return int(m.group(1)) if m else None
        if r.returncode == 5:
            log(logf, f"{first}-{last}: STOP, " + ("not ready to voice: " + out.strip().splitlines()[0][:300] if "NOT READY TO VOICE" in out
                                                   else "script.md changed during the run"))
            state["stop"] = "script"
            return None
        if r.returncode != 2:
            log(logf, f"{first}-{last}: autopick failed (exit {r.returncode}): {out[-600:]}")
            state.setdefault("errors", []).append({"section": f"{first}-{last}", "exit": r.returncode, "tail": out[-600:]})
            return None
        log(logf, f"{first}-{last}: no clean take in try {t + 1}" + (f"; {out.strip().splitlines()[-1][:300]}" if out.strip() else ""))
    state.setdefault("failed", []).append(f"{first}-{last}")
    return None


FLOOR_S = 480.0


def words_a_second():
    """The creator's voice's speaking rate, pauses included: config/tts.toml [tts] words_per_second (measured on their first finished
    narration: its words over its seconds), 3.9 until it is measured."""
    import tomllib
    cfg = Path(__file__).resolve().parents[2] / "config" / "tts.toml"
    try:
        return float(tomllib.loads(cfg.read_text(encoding="utf-8")).get("tts", {}).get("words_per_second", 3.9))
    except (OSError, ValueError):
        return 3.9


def length_floor(script):
    """8:00 is the floor of a long video, measured on the SCRIPT before the voice: words / the voice's words a second
    (words_a_second) plus every HOLD's seconds (a real person's own clip is part of the film). The check runs where the fault starts (the voice), so a
    script under the floor is caught before it is voiced, not after.
    Returns (words, hold seconds, seconds), or None for a Short (video.toml kind)."""
    toml = Path(script).parent / "video.toml"
    if toml.exists():
        import tomllib
        if tomllib.loads(toml.read_text(encoding="utf-8")).get("video", {}).get("kind", "long") != "long":
            return None
    txt = Path(script).read_text(encoding="utf-8")
    words = sum(len(m.split()) for m in re.findall(r"^\[S\d+[a-z]?\]\s*VOICE:\s*(.*)$", txt, re.M))
    holds = sum(float(m) for m in re.findall(r"^\[S\d+\w*\]\s*HOLD:\s*([\d.]+)", txt, re.M))
    return words, holds, words / words_a_second() + holds


def main():
    G.utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--plan", action="store_true", help="write and print the sections only")
    # defaults measured on a long film's voice (18 sections; 18 of 41 takes rejected, 13 maybe British): a section that failed twice
    # passed on try 3 or 4 in 2 of 8 cases, while its halves passed in 1-2 tries: the split comes after 2 tries, not 4. The third job
    # runs only while commit is at or under --extra-commit.
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--k", type=int, default=1)
    ap.add_argument("--k0", type=int, default=600)
    ap.add_argument("--tries", type=int, default=2)
    ap.add_argument("--words", type=int, default=150)
    ap.add_argument("--max-words", type=int, default=200)
    ap.add_argument("--min-words", type=int, default=60)
    ap.add_argument("--only", help="a beat range: only the sections inside it (S10-S20)")
    ap.add_argument("--extra-commit", type=float, default=0.75, help="a third (and later) job starts a section only while the memory "
                    "commit is at or under this share (Windows' commit; macOS: RAM + swap in use)")
    ap.add_argument("--say", nargs="*", default=[], help="WORD=SAYING respellings for ElevenLabs only (span_takes --say), passed to the "
                    "sections whose lines hold WORD: e.g. 'centre=center' (a British spelling can pull its stretch British)")
    ap.add_argument("--no-layout", action="store_true")
    ap.add_argument("--under-floor", metavar="REASON", help="voice a long video's script although it measures under 8:00: only "
                    "for a prototype voiced before its full script exists, the reason written out (it goes in the log)")
    a = ap.parse_args()
    P = G.paths(a.video)
    VL.guard_video(f"../videos/{P['video']}", "voice_full.py")
    sha = VL.sha(P["script"])
    vdir = P["dj"] / "build" / "voice"
    vdir.mkdir(parents=True, exist_ok=True)
    secs = plan(P["script"], a.words, a.max_words, a.min_words)
    words = {b: w for _, bs in chapters(P["script"]) for b, w in bs}
    (vdir / "sections.json").write_text(json.dumps({"script_sha256": sha, "sections": secs}, indent=1), encoding="utf-8")
    print(f"{len(secs)} sections over {sum(len(s['beats']) for s in secs)} beats; words a section: "
          f"{min(sum(words[b] for b in s['beats']) for s in secs)}-{max(sum(words[b] for b in s['beats']) for s in secs)}")
    fl = length_floor(P["script"])
    if fl:
        n, hold, s_ = fl
        print(f"length: {n} words / {words_a_second()} + {hold:.1f} s of HOLDs = {s_ / 60:.0f}:{s_ % 60:04.1f}"
              + ("" if s_ >= FLOOR_S else f"  UNDER the 8:00 floor by {FLOOR_S - s_:.0f} s"))
    if a.plan:
        for s in secs:
            print(f"  {s['first']}-{s['last']} ({len(s['beats'])} beats, {sum(words[b] for b in s['beats'])} words)")
        return
    if fl and fl[2] < FLOOR_S:
        if not a.under_floor:
            sys.exit("voice_full: the script measures under 8:00 (the floor is checked on the script BEFORE the voice): back "
                     "to the research for real content, never padding; a prototype voiced before its full script "
                     "exists passes --under-floor \"<why>\"")
        print(f"under the floor on purpose: {a.under_floor}")
    # the voice lock's ready stamps checked here, before any section starts (otherwise every autopick refuses at its first line with
    # exit 5 and the run logs a missing stamp as "script.md changed during the run")
    import voice_ready as R
    R.require(P["video_dir"], "voice_full.py")
    if a.only:
        lo, hi = a.only.split("-")
        ids = [b for s in secs for b in s["beats"]]
        secs = [s for s in secs if ids.index(s["first"]) >= ids.index(lo) and ids.index(s["last"]) <= ids.index(hi)]
    logf = vdir / "voice_full.log"
    state = {"picks": {}}

    def inflight():
        """sections an autopick outside this run is voicing now: its command line names them (an earlier driver's children keep running
        after the driver stops, without their tickets). Windows: the python processes from CIM; macOS and Linux: ps"""
        if WINDOWS:
            cmd = ["powershell.exe", "-NoProfile", "-Command",
                   "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ForEach-Object { $_.ProcessId.ToString() + ' ' + "
                   "$_.ParentProcessId.ToString() + ' ' + $_.CommandLine }"]
        else:
            cmd = ["ps", "-axo", "pid=,ppid=,command="]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        me = __import__("os").getpid()
        mine = {me} | {int(c) for c in state.get("children", ())}
        out = set()
        for line in (r.stdout or "").splitlines():
            parts = line.strip().split(None, 2)
            if len(parts) < 3 or not parts[0].isdigit():
                continue
            pid, ppid, cmd = int(parts[0]), int(parts[1]) if parts[1].isdigit() else 0, parts[2]
            m = re.search(rf"autopick\.py\S*\s+{re.escape(P['video'])}\s+(S\d+[a-z]?)\s+(S\d+[a-z]?)\s", cmd + " ")
            if m and pid not in mine and ppid not in mine and not state.get("launched", set()) & {f"{m[1]}-{m[2]}"}:
                out.add(f"{m[1]}-{m[2]}")
        return out

    def pending():
        prior = logf.read_text(encoding="utf-8") if logf.exists() else ""
        state["presplit"] = set(re.findall(rf"(S\d+[a-z]?-S\d+[a-z]?): no clean take in try {a.tries};", prior))
        cov = covered(P, sha)
        busy = inflight()
        todo_, waiting = [], []
        for s in secs:
            name = f"{s['first']}-{s['last']}"
            k = done(P, s, sha, cov)
            if k is not None:
                state["picks"][name] = k
            elif name in busy:
                waiting.append(name)
            elif name not in state.setdefault("tried", set()):
                todo_.append(s)
        return todo_, waiting

    todo, waiting = pending()
    log(logf, f"== {P['video']}: {len(secs)} sections, {len(state['picks'])} done, {len(todo)} to voice"
              + (f", {len(waiting)} in flight elsewhere ({', '.join(waiting)})" if waiting else "") + f"; script {sha[:16]}; "
              f"credits {credits_left()}; jobs {a.jobs} (the third and later only while commit <= {a.extra_commit:.0%})")
    while todo and not state.get("stop"):
        it = iter(todo)

        def worker(i):
            while not state.get("stop"):
                if i >= 2:   # two autopicks at once; a third only while the memory commit is at or under --extra-commit
                    from heavy import memory
                    ram, free, limit = memory()
                    if (limit - free) / limit > a.extra_commit:
                        time.sleep(30)
                        continue
                with LOCK:
                    s = next(it, None)
                if s is None:
                    return
                state["tried"].add(f"{s['first']}-{s['last']}")
                # a section an earlier run already tried --tries times without a clean take goes straight to the split
                k = None if f"{s['first']}-{s['last']}" in state["presplit"] else voice_section(P, s, a, sha, logf, state)
                if k is not None:
                    with LOCK:
                        state["picks"][f"{s['first']}-{s['last']}"] = k
                    log(logf, f"{s['first']}-{s['last']}: PICK take {k}")
                elif not state.get("stop") and len(s["beats"]) >= 2:
                    # no clean take after its tries: voiced again as two shorter requests, and a half that fails is split again,
                    # down to single beats (a section can read maybe-British at a different spot in each take: the whole take
                    # hovering at the soft line); each piece the lines-before way as always
                    if split_voice(s):
                        with LOCK:
                            state["picks"][f"{s['first']}-{s['last']}"] = "split"
                            state.setdefault("failed", [])
                            if f"{s['first']}-{s['last']}" in state["failed"]:
                                state["failed"].remove(f"{s['first']}-{s['last']}")

        def split_voice(s):
            """voice a failed section as two halves, each split again when it fails; True when every beat got a picked take"""
            cov = covered(P, sha)
            h = len(s["beats"]) // 2
            halves = [{"first": s["beats"][0], "last": s["beats"][h - 1], "beats": s["beats"][:h]},
                      {"first": s["beats"][h], "last": s["beats"][-1], "beats": s["beats"][h:]}]
            # a half of one short beat can't be judged (the accent guard needs 4 s: a 3.9-s beat alone is rejected every time):
            # it is voiced with the beat beside it instead
            allids = [b for b, _ in G.script_beats(P["script"])]
            wc = {b: len(v.split()) for b, v in G.script_beats(P["script"])}
            for hs in halves:
                if len(hs["beats"]) == 1 and wc[hs["beats"][0]] < 14:
                    i = allids.index(hs["beats"][0])
                    nb = allids[i - 1] if i > 0 else allids[i + 1]
                    hs["beats"] = sorted({hs["beats"][0], nb}, key=allids.index)
                    hs["first"], hs["last"] = hs["beats"][0], hs["beats"][-1]
            log(logf, f"{s['first']}-{s['last']}: split into {halves[0]['first']}-{halves[0]['last']} and "
                      f"{halves[1]['first']}-{halves[1]['last']}")
            ok = True
            for hs in halves:
                if all(b in cov for b in hs["beats"]):      # an earlier run already picked takes for every beat of this half
                    continue
                kk = None if f"{hs['first']}-{hs['last']}" in state["presplit"] else voice_section(P, hs, a, sha, logf, state)
                if kk is not None:
                    log(logf, f"{hs['first']}-{hs['last']}: PICK take {kk}")
                elif state.get("stop") or len(hs["beats"]) < 2 or not split_voice(hs):
                    ok = False
            return ok
        th = [threading.Thread(target=worker, args=(i,)) for i in range(max(1, a.jobs))]
        for t in th:
            t.start()
            time.sleep(20)
        for t in th:
            t.join()
        # the sections another process was voicing: their records land when it ends; one that found no take is voiced here
        while inflight():
            time.sleep(30)
        todo, waiting = pending()
    for key in ("tried", "launched", "presplit"):     # sets, for the record
        state[key] = sorted(state.get(key, []))
    (vdir / "voice_full.json").write_text(json.dumps({"script_sha256": sha, **state}, indent=1), encoding="utf-8")
    missing = [f"{s['first']}-{s['last']}" for s in secs if f"{s['first']}-{s['last']}" not in state["picks"]]
    log(logf, f"== sections picked {len(state['picks'])} of {len(secs)}; credits {credits_left()}"
              + (f"; NOT DONE: {', '.join(missing)}" if missing else "") + (f"; stopped: {state['stop']}" if state.get("stop") else ""))
    if missing or state.get("stop"):
        sys.exit(2)
    if VL.sha(P["script"]) != sha:
        log(logf, "STOP: script.md changed during the run")
        sys.exit(5)
    if a.no_layout or a.only:
        return
    # every picked take re-cut into its lines with span_takes as it is now (the take's audio is on disk: no request is made), so
    # every join follows the same rule (the cut in the middle of the real pause, past a hiss); a section split by hand into
    # smaller records is re-cut record by record
    cov = covered(P, sha)
    takes = sorted({(span, k) for k, span in cov.values()}, key=lambda x: [b for b, _ in G.script_beats(P["script"])].index(x[0].split("-")[0]))
    for span, k in takes:
        first, last = span.split("-")
        r = subprocess.run([GT, str(TOOLS / "voice" / "span_takes.py"), f"../videos/{P['video']}", first, last, str(k), str(k),
                            "--name", f"autopick_{first}-{last}"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=str(TOOLS))
        if r.returncode:
            log(logf, f"recut {span} take {k} failed: {(r.stderr or r.stdout)[-300:]}")
            sys.exit(3)
    log(logf, f"recut: {len(takes)} takes cut into their lines again (no request)")
    ids = [b for s in secs for b in s["beats"]]
    r = subprocess.run([GT, str(HERE / "proto_narration.py"), P["video"], ids[0], ids[-1]], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(TOOLS))
    log(logf, f"layout: {(r.stdout or r.stderr).strip()[-400:]}")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
