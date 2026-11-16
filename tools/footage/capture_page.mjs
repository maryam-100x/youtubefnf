// A sharp screenshot of one block of a public web page, for "receipt" shots (an official page's screenshot with a zoom and a
// highlighter is normal content making). A headless Chromium browser (Edge, else Chrome) over the DevTools protocol: a fresh empty
// profile, no login, nothing clicked or accepted; cookie banners and sticky headers are hidden with CSS, not answered.
//   node tools/footage/capture_page.mjs <url> <out.png> <css selector | text=<words>> [--up 0] [--width 1280] [--scale 2] [--pad 24] [--wait 7000] [--mobile 0] [--declutter 0] [--wrap 0]
// --mobile 1: the page is laid out as a phone at --width (DevTools device emulation): narrower than a desktop window can go (the browser
// keeps windows ~450 px or wider), so the text wraps more and comes out bigger in a card of the same size.
// Scale 2 is the ceiling on heavy pages: at 3 the browser can stop answering Page.captureScreenshot (any window size).
// Writes <out.png> (the block at <scale>x) and <out>.json (the block's rect and the text boxes of its leaf elements, in the png's
// pixels, so a highlighter or ring can be placed on a word without measuring by hand; tools/footage/snap_marks.py snaps them to the ink).
// The browser: CAPTURE_BROWSER (a full path) when set, else the first of Edge and Chrome found at their usual places (Windows, macOS,
// Linux).
import {spawn, spawnSync} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {TMP} from '../common/paths.mjs';

const [, , url, out, selector, ...rest] = process.argv;
if (!url || !out || !selector) {
  console.error('usage: node capture_page.mjs <url> <out.png> <css selector> [--width 1280] [--scale 2] [--pad 24] [--wait 7000]');
  process.exit(2);
}
const opt = (k, d) => {
  const i = rest.indexOf(`--${k}`);
  return i >= 0 ? Number(rest[i + 1]) : d;
};
const MARKS = rest.flatMap((v, i) => (rest[i - 1] === '--mark' ? [v] : []));
const W = opt('width', 1280), SCALE = opt('scale', 2), PAD = opt('pad', 24), WAIT = opt('wait', 7000), UP = opt('up', 0), MOBILE = opt('mobile', 0);
const DECLUTTER = opt('declutter', 0);
// --wrap <px>: the block itself is laid out that many CSS px wide, so its text wraps the way a phone shows it. For old fixed-width pages
// that ignore --mobile (an archived page can come out as one 1000-px line); only the block's line width changes, never its words or its type.
const WRAP = opt('wrap', 0);
// --ua <string>: a declared User-Agent, for sites whose access policy asks automated tools to name themselves and a contact (some answer a
// headless browser with "Undeclared Automated Tool"); the contact comes from the caller, never from this file
const UA = rest.includes('--ua') ? rest[rest.indexOf('--ua') + 1] : '';
// --bg <css colour>: the block gets this background, for white type whose own dark ground starts below the block's top (white footnotes
// come out white on white); a capture without it is unchanged
const BG = rest.includes('--bg') ? rest[rest.indexOf('--bg') + 1] : '';
// --css <rules>: extra CSS for one page (a page that paints only what's on screen with content-visibility, say)
const CSS = rest.includes('--css') ? rest[rest.indexOf('--css') + 1] : '';
// --replace "<from>=><to>" (repeatable): the page's own words swapped in its text nodes before the capture, ONLY to show a non-English
// page's line in an English translation, and the shot then says "translated from <language>" (a translation proxy page can capture black)
const REPL = rest.flatMap((v, i) => (rest[i - 1] === '--replace' ? [v.split('=>')] : []));
// the block: a CSS selector, or text=<words> (the smallest visible element containing them), then UP parents
const FIND = `(() => {
  const q = ${JSON.stringify(selector)};
  let el = null;
  if (q.startsWith('text=')) {
    const want = q.slice(5);
    for (const e of document.querySelectorAll('body *')) {
      if (e.tagName === 'SCRIPT' || !e.textContent.includes(want)) continue;
      const b = e.getBoundingClientRect();
      if (b.width > 0 && b.height > 0 && (!el || el.contains(e))) el = e;
    }
  } else el = document.querySelector(q);
  for (let k = 0; k < ${UP} && el && el.parentElement; k++) el = el.parentElement;
  return el;
})()`;
const BROWSERS = [
  process.env.CAPTURE_BROWSER,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/microsoft-edge',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean);
const BROWSER = BROWSERS.find((p) => fs.existsSync(p));
if (!BROWSER) {
  console.error('capture: no Edge or Chrome found; set CAPTURE_BROWSER to the browser\'s full path');
  process.exit(2);
}
const PORT = 9300 + Math.floor(Math.random() * 600);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// At most SLOTS captures at once on this machine: each headless browser takes ~2 GB, and many at once beside other jobs can run the
// machine out of memory. A slot is a lock file holding its PID; a dead owner's slot is taken over. CAPTURE_SLOTS overrides the count.
const SLOTS = Number(process.env.CAPTURE_SLOTS || 2);
const SLOT_DIR = path.join(TMP, 'capture_slots');
fs.mkdirSync(SLOT_DIR, {recursive: true});
const alive = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return e.code === 'EPERM'; } };
let slotFile = null;
for (let waited = 0; !slotFile; waited += 2) {
  for (let i = 0; i < SLOTS && !slotFile; i++) {
    const f = path.join(SLOT_DIR, `slot${i}.lock`);
    try {
      fs.writeFileSync(f, String(process.pid), {flag: 'wx'});
      slotFile = f;
    } catch {
      const owner = Number(fs.readFileSync(f, 'utf8') || 0);
      if (!owner || !alive(owner)) { try { fs.unlinkSync(f); } catch {} }
    }
  }
  if (!slotFile) {
    if (waited % 30 === 0) console.error(`capture: waiting for a free slot (${SLOTS} captures already running)`);
    if (waited > 900) { console.error('capture: no free slot after 15 min'); process.exit(3); }
    await sleep(2000);
  }
}
const releaseSlot = () => { try { if (slotFile && fs.readFileSync(slotFile, 'utf8') === String(process.pid)) fs.unlinkSync(slotFile); } catch {} };
process.on('exit', releaseSlot);
for (const s of ['SIGINT', 'SIGTERM']) process.on(s, () => { releaseSlot(); process.exit(130); });

const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'capture-'));
// --nogpu 1: software compositing (captures can come out solid black while a render holds the GPU)
const NOGPU = rest.includes('--nogpu') && rest[rest.indexOf('--nogpu') + 1] !== '0';
const edge = spawn(BROWSER, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--mute-audio', `--force-device-scale-factor=${SCALE}`, `--window-size=${W},1200`, ...(NOGPU ? ['--disable-gpu'] : []),
  'about:blank'], {stdio: 'ignore'});

try {
  let target;
  for (let i = 0; i < 100 && !target; i++) {
    try {
      target = (await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()).find((t) => t.type === 'page');
    } catch {}
    if (!target) await sleep(150);
  }
  if (!target) throw new Error('the browser did not open its DevTools port');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let n = 0;
  const pending = new Map();
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
  };
  const send = (method, params = {}) => new Promise((res, rej) => {
    const id = ++n;
    const to = setTimeout(() => rej(new Error(`${method}: no answer in 90 s`)), 90000);
    pending.set(id, (d) => { clearTimeout(to); d.error ? rej(new Error(`${method}: ${d.error.message}`)) : res(d.result); });
    ws.send(JSON.stringify({id, method, params}));
  });
  const js = async (expression) => {
    const r = await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
    return r.result.value;
  };

  if (MOBILE) await send('Emulation.setDeviceMetricsOverride', {width: W, height: opt('vh', 1200), deviceScaleFactor: SCALE, mobile: true});  // --vh: the phone's height; a block taller than it is painted only to the viewport's bottom
  if (UA) await send('Emulation.setUserAgentOverride', {userAgent: UA});
  await send('Page.enable');
  await send('Page.navigate', {url});
  await sleep(WAIT);
  console.error('loaded', await js(`location.href + ' | ' + document.title + ' | ' + document.readyState`));
  // --prescroll N: scroll down N screens, 2 s each, before looking for the block: content that loads only on scroll (comments, feeds)
  for (let k = 0; k < opt('prescroll', 0); k++) {
    await js(`window.scrollBy(0, innerHeight * 0.9)`);
    await sleep(2000);
  }
  // hide what floats over the page (consent banners, sticky headers, chat bubbles) without answering any of it
  await js(`(async () => {
    const st = document.createElement('style');
    // never html or body themselves: a site can put "cookie-banner-visible" on <html>, and the rule would hide the whole page ("block not
    // found" on text that is there); a body class like "modal-open" would do the same under --declutter
    const N = ':not(html):not(body)';
    st.textContent = '#onetrust-consent-sdk, .onetrust-pc-dark-filter, [id*=cookie i]' + N + ', [class*=cookie-banner i]' + N + ' {display: none !important}'
      // --declutter 1: dimming layers and page-wide fades too (a capture can come out grey under a modal's dim)
      + (${DECLUTTER} ? ' ' + ['[class*=overlay i]', '[class*=backdrop i]', '[class*=modal i]', '[class*=popup i]', '[id*=overlay i]', '#cmpwrapper', '.cmpwrapper', '[id^=cmp i]', '[class*=consent i]'].map((s) => s + N).join(', ') + ' {display: none !important}'
        + ' html, body, body > *, main, article {filter: none !important; opacity: 1 !important}' : '');
    st.textContent += ' ' + ${JSON.stringify(CSS)};
    document.head.appendChild(st);
    for (const [a, b] of ${JSON.stringify(REPL)}) {
      const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = tw.nextNode(); n; n = tw.nextNode()) if (n.data.includes(a)) n.data = n.data.split(a).join(b);
    }
    // a consent manager that styles its own host inline with !important beats the sheet above, so it is hidden inline too (a shadow-DOM
    // dim greys the capture); hidden, never answered
    if (${DECLUTTER}) document.querySelectorAll('#cmpwrapper, .cmpwrapper, [id^=cmp i]').forEach((e) => e.style.setProperty('display', 'none', 'important'));
    // and the scroll lock the hidden dialog leaves (body position fixed, overflow hidden): the page never scrolls to the block, which then
    // lies below the viewport and comes out as bare background; set inline because the lock's own !important rules outrank a sheet
    if (${DECLUTTER}) {
      for (const e of [document.documentElement, document.body]) e.style.setProperty('overflow', 'visible', 'important');
      document.body.style.setProperty('position', 'static', 'important');
      document.body.style.setProperty('top', 'auto', 'important');
    }
    const el = ${FIND};
    if (!el) throw new Error('block not found: ' + ${JSON.stringify(selector)});
    if (${JSON.stringify(BG)}) el.style.setProperty('background-color', ${JSON.stringify(BG)}, 'important');
    if (${WRAP}) {
      if (getComputedStyle(el).display === 'inline') el.style.setProperty('display', 'block', 'important');
      for (const [k, v] of [['width', '${WRAP}px'], ['max-width', '${WRAP}px'], ['white-space', 'normal']]) el.style.setProperty(k, v, 'important');
    }
    el.scrollIntoView({block: 'center'});
    await new Promise((r) => setTimeout(r, 2500));
    document.querySelectorAll('video, iframe').forEach((v) => v.remove());
    // body's descendants and anything a script hung straight under <html> (a consent dialog that sits beside <body> and covers the text)
    const FLOAT = 'html > *:not(head):not(body), body *';
    for (const e of document.querySelectorAll(FLOAT)) {
      const p = getComputedStyle(e).position;
      if ((p === 'fixed' || p === 'sticky') && !e.contains(el) && !el.contains(e)) e.style.setProperty('display', 'none', 'important');
    }
    await Promise.all([...el.querySelectorAll('img')].map((i) => i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; setTimeout(r, 5000); })));
    window.scrollTo(0, el.getBoundingClientRect().y + scrollY - ${PAD});
    await new Promise((r) => setTimeout(r, 1500));
    // again after the scroll: some headers turn sticky only when the page scrolls back up (and cover the top of the block)
    for (const e of document.querySelectorAll(FLOAT)) {
      const p = getComputedStyle(e).position;
      if ((p === 'fixed' || p === 'sticky') && !e.contains(el) && !el.contains(e)) e.style.setProperty('display', 'none', 'important');
    }
    await new Promise((r) => setTimeout(r, 500));
    return 1;
  })()`);
  console.error('cleaned');
  if (opt('debug', 0)) {  // --debug 1: what sits over the block's centre (to find a dimming layer), with its opacity and background
    console.error(await js(`(() => { const el = ${FIND}; const b = el.getBoundingClientRect();
      return JSON.stringify(document.elementsFromPoint(b.x + b.width / 2, b.y + b.height / 2).slice(0, 8).map((e) => {
        const c = getComputedStyle(e); return e.tagName + '#' + e.id + '.' + String(e.className).slice(0, 60) + ' op=' + c.opacity + ' bg=' + c.backgroundColor + ' filt=' + c.filter + ' pos=' + c.position; })); })()`));
  }
  const info = await js(`(() => {
    const el = ${FIND};
    const b = el.getBoundingClientRect();
    // never left of or above the page: the screenshot clamps a negative clip to 0, and every mark and word box measured from a negative
    // origin then sat that far right of its text
    const x0 = Math.max(0, b.x + scrollX - ${PAD}), y0 = Math.max(0, b.y + scrollY - ${PAD});
    const words = [];
    for (const e of el.querySelectorAll('*')) {
      if (e.children.length || !e.textContent.trim()) continue;
      const rg = document.createRange();
      rg.selectNodeContents(e);
      const r = rg.getBoundingClientRect(); // the ink of the text, not the element's box
      if (r.width < 1) continue;
      words.push({text: e.textContent.trim(), x: (r.x + scrollX - x0) * ${SCALE}, y: (r.y + scrollY - y0) * ${SCALE}, w: r.width * ${SCALE}, h: r.height * ${SCALE}});
    }
    const marks = [];
    for (const phrase of ${JSON.stringify(MARKS)}) {
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = tw.nextNode(); n; n = tw.nextNode()) {
        const i = n.textContent.indexOf(phrase);
        if (i < 0) continue;
        const rg = document.createRange();
        rg.setStart(n, i);
        rg.setEnd(n, i + phrase.length);
        for (const r of rg.getClientRects()) marks.push({phrase, x: (r.x + scrollX - x0) * ${SCALE}, y: (r.y + scrollY - y0) * ${SCALE}, w: r.width * ${SCALE}, h: r.height * ${SCALE}});
        break;
      }
    }
    return {clip: {x: x0, y: y0, width: b.x + scrollX + b.width + ${PAD} - x0, height: b.y + scrollY + b.height + ${PAD} - y0}, words, marks};
  })()`);
  console.error('measured', JSON.stringify(info.clip));
  const shot = await send('Page.captureScreenshot', {format: 'png', clip: {...info.clip, scale: 1}, captureBeyondViewport: false});
  fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
  fs.writeFileSync(out.replace(/\.png$/i, '') + '.json', JSON.stringify({url, selector, captured: new Date().toISOString(), scale: SCALE, width: W, ...info}, null, 1));
  console.log(out, Math.round(info.clip.width * SCALE), 'x', Math.round(info.clip.height * SCALE), `${info.words.length} text boxes`);
  ws.close();
} finally {
  // the whole browser, children included: on Windows edge.kill() ends only the parent, and every capture would leave its renderers and
  // GPU process running until the RAM is full
  if (process.platform === 'win32') {
    spawnSync('taskkill', ['/PID', String(edge.pid), '/T', '/F'], {stdio: 'ignore'});
    // then anything still running on this profile (a process the tree kill can't reach once its parent is gone)
    const exe = path.basename(BROWSER);
    spawnSync('powershell', ['-NoProfile', '-Command', `Get-CimInstance Win32_Process -Filter "Name='${exe}'" | Where-Object { $_.CommandLine -like '*${path.basename(profile)}*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }`], {stdio: 'ignore'});
  } else {
    edge.kill();
    // macOS and Linux: the helpers started on this profile go too
    spawnSync('pkill', ['-f', path.basename(profile)], {stdio: 'ignore'});
  }
  await sleep(800);
  // the browser can still hold the profile's files for a moment after it exits (EPERM): the capture is already written, so a profile
  // that won't go is left in the temp folder instead of failing the run
  try {
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 300});
  } catch (e) {
    console.error('profile left in temp:', e.code);
  }
}
