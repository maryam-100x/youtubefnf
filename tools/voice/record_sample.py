"""The voice sample recorder: a page in the creator's own browser with the text to read, a microphone choice, a level bar and one
big button. The recording is saved as a WAV straight into MEDIA/voice/sample/ and the recorder ends, so the chat carries on by
itself (SETUP.md step 9): the creator never handles a file. The browser's own voice processing (echo cancelling, noise
suppression, automatic gain) is switched off, because an instant clone would copy it along with the voice.

    PIPE tools/voice/record_sample.py [--text <a .txt or .md file with the text to read>] [--name <file name start>]

Run it in the background. It prints the page's address (it also opens it in the default browser), then the saved file's path
("SAVED <path>") once the creator presses Save, and exits; with nothing saved it ends after 2 hours ("NOT SAVED"). Only this
computer can open the page (127.0.0.1 and a one-time token in its address). Without --text it shows a neutral text of its own.
"""
import argparse
import html
import http.server
import json
import re
import secrets
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import MEDIA  # noqa: E402

SAMPLE = MEDIA / "voice" / "sample"
WAIT_S = 2 * 3600
MAX_BYTES = 300 * 2**20

TEXT = """Last summer I decided to fix the old bike that had been sitting in my parents' shed for almost six years. The tires were
flat, the chain was orange with rust, and one of the brakes didn't do anything at all. My first thought was simple: how hard can
this really be?

It turns out the answer is: harder than it looks, but easier than you'd think. I watched a few videos, wrote a list, and spent
about forty dollars on parts. A new chain, two inner tubes, brake pads, and a small bottle of oil. That was it.

The chain was the worst part. I must have dropped the little pin three or four times, and every single time it rolled under the
workbench, into the darkest corner it could find. At one point I was lying flat on the floor with a flashlight in my mouth,
wondering why I didn't just buy a new bike.

But then something clicked. Literally. The chain slid into place, the wheel turned, and everything ran smoothly for the first time
in years. I actually laughed out loud.

So I took it out for a ride. Down the hill, past the bakery on the corner, along the river and back. Eight miles, maybe nine. The brakes worked, the gears worked, and I didn't fall off once, which honestly felt like a small miracle.

Here's the thing I keep coming back to. Most of the stuff we think we can't do, we've just never tried. Not because it's
impossible, but because starting feels awkward. You don't know the words, you don't have the tools, and you're pretty sure you'll
look silly.

And you might. That's fine. Look silly for an afternoon, and at the end of it you know how to do something new. Would you rather
have a perfect afternoon, or a bike that works?

Anyway, that's my story. The bike still lives in the shed, but now it gets out every weekend. And next time something breaks, I
think I'll try to fix it first."""

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Record your voice</title>
<style>
:root { --bg:#f6f6f4; --card:#fff; --ink:#1b1b1b; --soft:#666; --line:#e2e2de; --go:#d93c3c; --ok:#2f8f4e; --warn:#b26b00; }
@media (prefers-color-scheme: dark) { :root { --bg:#151515; --card:#1f1f1f; --ink:#f0f0f0; --soft:#a0a0a0; --line:#333;
  --go:#ef5a5a; --ok:#4cbb6c; --warn:#e6a23c; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width:860px; margin:0 auto; padding:24px 16px 48px; }
h1 { font-size:26px; margin:0 0 4px; }
.sub { color:var(--soft); margin:0 0 20px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin-bottom:16px; }
ol { margin:0; padding-left:22px; } li { margin:4px 0; }
.row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
select { font:inherit; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink);
  max-width:100%; }
button { font:inherit; font-weight:600; border:0; border-radius:999px; padding:12px 22px; cursor:pointer; }
button:disabled { opacity:.45; cursor:default; }
#rec { background:var(--go); color:#fff; font-size:20px; padding:16px 34px; }
#rec.on { background:var(--ink); color:var(--bg); }
.plain { background:transparent; color:var(--ink); border:1px solid var(--line); }
.save { background:var(--ok); color:#fff; }
.meter { flex:1; min-width:180px; height:14px; border-radius:7px; background:var(--line); overflow:hidden; }
.meter > div { height:100%; width:0; background:var(--ok); transition:width .06s linear; }
#time { font-variant-numeric:tabular-nums; font-size:20px; min-width:64px; }
#hint, #note { color:var(--soft); }
#note.warn { color:var(--warn); }
.text { font-size:21px; line-height:1.65; max-height:52vh; overflow-y:auto; padding-right:8px; }
.text p { margin:0 0 14px; }
.hide { display:none; }
audio { width:100%; margin:8px 0 12px; }
.done { font-size:20px; color:var(--ok); font-weight:600; }
</style></head><body><main>
<h1>Record your voice</h1>
<p class="sub">About 2 minutes of you reading the text below. The studio makes your voice from it.</p>
<div class="card"><ol>
<li>A quiet room with soft things in it (curtains, a bed, a sofa). No music, TV or fan.</li>
<li>The microphone about a hand's width from your mouth, the same distance the whole time.</li>
<li>Read in your normal voice, the way you'd tell a friend a story. A slip? Pause, and say the sentence again.</li>
</ol></div>
<div class="card" id="setup">
<div class="row"><button id="on" class="save">Turn on the microphone</button>
<span id="ask" class="hide">Your browser asks to use the microphone: click <b>Allow</b>.</span></div>
<p id="err" class="hide"></p>
</div>
<div class="card hide" id="deck">
<div class="row" style="margin-bottom:12px"><label for="mic">Microphone</label><select id="mic"></select></div>
<div class="row" style="margin-bottom:6px"><div class="meter"><div id="lvl"></div></div></div>
<p id="hint">Say something: the bar should move well past the middle when you speak, and never turn red.</p>
<div class="row"><button id="rec">Record</button><span id="time">0:00</span><span id="note"></span></div>
<div id="after" class="hide">
<audio id="play" controls></audio>
<div class="row"><button id="save" class="save">Save this recording</button><button id="again" class="plain">Record again</button></div>
</div>
<p id="fin" class="done hide">Saved. You can close this page: the chat takes it from here.</p>
</div>
<div class="card"><div class="text">__TEXT__</div></div>
</main>
<script>
const T = "__TOKEN__";
const $ = (id) => document.getElementById(id);
let ctx, stream, src, node, sink, recording = false, chunks = [], peakNow = 0, t0 = 0, timer, wav = null;
const WORKLET = "class R extends AudioWorkletProcessor{process(i){const c=i[0]&&i[0][0];if(c)this.port.postMessage(c.slice(0));return true}}registerProcessor('r',R);";

async function openMic(id) {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  if (src) src.disconnect();
  stream = await navigator.mediaDevices.getUserMedia({audio: {deviceId: id ? {exact: id} : undefined, channelCount: 1,
    echoCancellation: false, noiseSuppression: false, autoGainControl: false}});
  src = ctx.createMediaStreamSource(stream);
  src.connect(node);
}

async function listMics() {
  const all = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "audioinput");
  const cur = stream.getAudioTracks()[0].getSettings().deviceId;
  $("mic").innerHTML = "";
  for (const d of all) {
    const o = document.createElement("option");
    o.value = d.deviceId; o.textContent = d.label || "Microphone";
    if (d.deviceId === cur) o.selected = true;
    $("mic").appendChild(o);
  }
}

$("on").onclick = async () => {
  $("on").disabled = true; $("ask").classList.remove("hide");
  try {
    ctx = new AudioContext();
    await ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], {type: "application/javascript"})));
    node = new AudioWorkletNode(ctx, "r");
    sink = ctx.createGain(); sink.gain.value = 0; node.connect(sink); sink.connect(ctx.destination);
    node.port.onmessage = (e) => {
      const c = e.data; let p = 0;
      for (let k = 0; k < c.length; k++) { const a = Math.abs(c[k]); if (a > p) p = a; }
      if (p > peakNow) peakNow = p;
      if (recording) chunks.push(c);
    };
    await openMic();
    await ctx.resume();
    await listMics();
    $("setup").classList.add("hide"); $("deck").classList.remove("hide");
    setInterval(draw, 50);
  } catch (e) {
    $("ask").classList.add("hide"); $("on").disabled = false;
    const denied = e && (e.name === "NotAllowedError" || e.name === "SecurityError");
    $("err").textContent = denied
      ? "The browser was not allowed to use the microphone. Click the icon left of the address, allow the microphone, then reload this page."
      : (e && e.name === "NotFoundError" ? "No microphone was found. Plug one in, then reload this page." : "The microphone did not start: " + e);
    $("err").classList.remove("hide");
  }
};

$("mic").onchange = async () => { if (!recording) { await openMic($("mic").value); } };

let shown = 0;
function draw() {
  shown = Math.max(peakNow, shown * 0.85); peakNow = 0;
  const db = shown > 0 ? 20 * Math.log10(shown) : -90;
  const w = Math.max(0, Math.min(100, (db + 50) * 2));
  $("lvl").style.width = w + "%";
  $("lvl").style.background = db > -1 ? "var(--go)" : "var(--ok)";
}

const fmt = (s) => Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0");
function tick() {
  const s = (performance.now() - t0) / 1000;
  $("time").textContent = fmt(s);
  $("note").className = "";
  $("note").textContent = s < 60 ? "Keep reading: at least 1 minute" : (s < 180 ? "Good. Stop whenever the text ends" : "That's plenty: press Stop");
}

$("rec").onclick = () => {
  if (!recording) {
    chunks = []; wav = null; recording = true; t0 = performance.now();
    $("rec").textContent = "Stop"; $("rec").classList.add("on"); $("mic").disabled = true;
    $("after").classList.add("hide"); tick(); timer = setInterval(tick, 250);
    return;
  }
  recording = false; clearInterval(timer);
  $("rec").textContent = "Record"; $("rec").classList.remove("on"); $("mic").disabled = false;
  const n = chunks.reduce((a, c) => a + c.length, 0);
  const x = new Float32Array(n); let o = 0, peak = 0, clips = 0;
  for (const c of chunks) { x.set(c, o); o += c.length; }
  for (let k = 0; k < n; k++) { const a = Math.abs(x[k]); if (a > peak) peak = a; if (a >= 0.99) clips++; }
  const secs = n / ctx.sampleRate;
  $("note").className = "";
  if (secs < 60) {
    $("note").textContent = "That was under a minute. Press Record and read a little longer.";
    $("note").className = "warn";
    return;
  }
  if (clips > ctx.sampleRate * 0.01) { $("note").textContent = "It got too loud in places: if you can, record again a little further from the mic."; $("note").className = "warn"; }
  else if (peak < 0.06) { $("note").textContent = "It's very quiet: if you can, record again a little closer to the mic."; $("note").className = "warn"; }
  else { $("note").textContent = "Listen back if you like, then save."; }
  wav = toWav(x, ctx.sampleRate);
  $("play").src = URL.createObjectURL(wav);
  $("after").classList.remove("hide");
};

$("again").onclick = () => { $("after").classList.add("hide"); $("note").textContent = ""; wav = null; };

$("save").onclick = async () => {
  if (!wav) return;
  $("save").disabled = true; $("again").disabled = true; $("save").textContent = "Saving...";
  try {
    const r = await fetch("/save?t=" + T, {method: "POST", body: wav});
    if (!r.ok) throw new Error(await r.text());
    $("after").classList.add("hide"); $("rec").classList.add("hide"); $("note").textContent = "";
    $("fin").classList.remove("hide");
    if (stream) stream.getTracks().forEach((t) => t.stop());
  } catch (e) {
    $("save").disabled = false; $("again").disabled = false; $("save").textContent = "Save this recording";
    $("note").textContent = "Saving failed: " + e.message; $("note").className = "warn";
  }
};

function toWav(x, sr) {
  const b = new ArrayBuffer(44 + x.length * 2), v = new DataView(b);
  const s = (o, t) => { for (let k = 0; k < t.length; k++) v.setUint8(o + k, t.charCodeAt(k)); };
  s(0, "RIFF"); v.setUint32(4, 36 + x.length * 2, true); s(8, "WAVE"); s(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, sr, true);
  v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); s(36, "data"); v.setUint32(40, x.length * 2, true);
  for (let k = 0, o = 44; k < x.length; k++, o += 2) { const c = Math.max(-1, Math.min(1, x[k])); v.setInt16(o, c < 0 ? c * 32768 : c * 32767, true); }
  return new Blob([b], {type: "audio/wav"});
}
</script></body></html>
"""


def text_html(raw):
    """The text to read as paragraphs: markdown headings, list markers and emphasis dropped, blank lines between paragraphs."""
    paras = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        lines = [re.sub(r"^([-*>]|\d+\.)\s+", "", ln).replace("**", "").replace("__", "") for ln in lines]
        if lines:
            paras.append("<p>" + html.escape(" ".join(lines)) + "</p>")
    return "\n".join(paras)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", help="a .txt or .md file with the text to read (default: the recorder's own)")
    ap.add_argument("--name", default="sample", help="the saved file's name start (default: sample)")
    ap.add_argument("--no-open", action="store_true", help="print the address only (no browser opened)")
    ap.add_argument("--out-dir", help="save into this folder instead of MEDIA/voice/sample (the tests)")
    a = ap.parse_args()
    out_dir = Path(a.out_dir) if a.out_dir else SAMPLE
    raw = Path(a.text).read_text(encoding="utf-8-sig") if a.text else TEXT
    token = secrets.token_urlsafe(16)
    page = PAGE.replace("__TEXT__", text_html(raw)).replace("__TOKEN__", token).encode("utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    saved, done = [], threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _ok_token(self):
            return secrets.compare_digest(parse_qs(urlsplit(self.path).query).get("t", [""])[0], token)

        def _send(self, code, body, ctype="text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.split("?")[0] == "/" and self._ok_token():
                self._send(200, page, "text/html; charset=utf-8")
            else:
                self._send(404, b"not here")

        def do_POST(self):
            if self.path.split("?")[0] != "/save" or not self._ok_token():
                self._send(404, b"not here")
                return
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if 0 < n <= MAX_BYTES else b""
            if body[:4] != b"RIFF" or body[8:12] != b"WAVE":
                self._send(400, b"that was not a WAV recording")
                return
            out = out_dir / f"{a.name}_{time.strftime('%Y%m%d-%H%M%S')}.wav"
            out.write_bytes(body)
            saved.append(out)
            self._send(200, json.dumps({"file": out.name}).encode("utf-8"), "application/json")
            done.set()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/?t={token}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"RECORDER {url}", flush=True)
    try:
        if not a.no_open:
            webbrowser.open(url)
    except Exception:  # noqa: BLE001  the address above is the way in when no browser opens by itself
        pass
    done.wait(WAIT_S)
    time.sleep(1)   # the page gets its answer before the server goes
    srv.shutdown()
    if saved:
        print(f"SAVED {saved[-1]}", flush=True)
        return 0
    print("NOT SAVED (nothing was saved within 2 hours)", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
