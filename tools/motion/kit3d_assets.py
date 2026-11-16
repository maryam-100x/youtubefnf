"""kit3d's assets (standard/3D.md): everything the 3D pieces read, built once into PUBLIC/kit3d/ (public-dir paths 'kit3d/...'), plus
the demo's lean public dir TMP/pub_kit3d (hard links, so a bundle never copies the whole public dir).

The demo (src/kit3d/Kit3dDemo.tsx) runs on DEMO MATERIAL DRAWN HERE (a logo, two scenes, a cover, a phone clip: shapes and colour,
nobody's picture), so it renders on any PC with nothing to license. A video's 3D pieces take the creator's own material: --logo <svg>,
--photo <name>=<picture>, --cover <picture>, --clip <video>; each is written under its own name beside the demo's.

Editing venv (cv2, PIL, numpy; rembg, transformers + torch CPU for parallax):
  EDIT tools/motion/kit3d_assets.py [all|basics|emblem|parallax|clip|earth|link] [--force] [--logo <file.svg>]
      [--photo <name>=<picture> ...] [--cover <picture>] [--clip <video> [--ss 0] [--t 5]] [--world <the 3-km world map .jpg>]

What it makes (each step skips what is already there; --force redoes it):
  basics    the folders; the demo's drawn pictures: img/demo_people.jpg (two people in front of a street, for Parallax25D),
            img/demo_city.jpg (a skyline at dusk: a stage ground, the emblem's reflection, a second parallax), img/demo_cover.jpg (a
            cover for CaseNumber3D), logos/demo_logo.svg (a badge with white lettering in a dark outline, for Emblem3D); any --photo and
            --cover given (img/<name>.jpg); LICENCES.tsv; and the licensed files still to place by hand (the HDRI, the fonts, the
            world map), each with its source.
  emblem    a logo's silhouette for extrusion: the logo rasterised at 4096 px (a headless Edge or Chrome: the SVG as a browser draws it),
            its alpha traced into polygons (OpenCV contours with holes) -> kit3d/logos/<name>_4k.png (the face's picture) and
            <name>_shape.json (the outline, plus the 'raised' block: the white lettering with its outline, extruded a little prouder
            than the base). <name> is demo_logo, and the --logo file's name.
  parallax  a picture made into layers for Parallax25D: depth (Depth-Anything-V2-Small, Apache-2.0: the depth only, no pixel
            changed), the subject's matte (BiRefNet via rembg, MIT), the background behind the subject filled by OpenCV's Telea
            inpainting (classical, no generated content; only slivers of it ever show). -> kit3d/img/<name>.jpg (the original),
            <name>_fg.png (subject RGBA), <name>_bg.jpg, <name>_depth.png / <name>_bgdepth.png (16-bit depth packed in R (high byte)
            and G (low byte), 1920 px; 1 = nearest). For every picture in img/ that basics wrote (the demo's and each --photo).
  clip      the phone's footage: --clip <video> from --ss for --t s, cropped to 2:1 round its centre, 1920 px, CRF 16 ->
            clips/<video name>.mp4; and the demo's drawn clip, clips/demo_phone.mp4 (a moving colour field with shapes on it).
  earth     the world map (NASA Black Marble 2016, 3 km a pixel, 8192x4096, from NASA Earth Observatory's Night Lights page: pass
            --world <the downloaded file> once) -> earth/blackmarble_8k.jpg; and the detail patch for close globe moves ->
            earth/bm500_patch.jpg: NASA's 500-m tile B1 (90W-0, 0-90N), cropped to the bounds globe.tsx's PATCH names (read from
            src/kit3d/globe.tsx, so the two never drift), decoded at half size (~1 km a pixel).
  link      TMP/pub_kit3d/kit3d/* as hard links of PUBLIC/kit3d/*.

Licences and sources: kit3d/LICENCES.tsv (written here) and standard/3D.md section 6.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import FFMPEG, MAC, MOTION, PUBLIC, TMP, WINDOWS  # noqa: E402
from kit3_demo_assets import field_clip, grain, gradient, person, poster  # noqa: E402  (the drawing helpers the 2D demo uses)

ROOT = PUBLIC / 'kit3d'
PUB = TMP / 'pub_kit3d' / 'kit3d'
GLOBE = MOTION / 'src' / 'kit3d' / 'globe.tsx'
FORCE = False

LICENCES = [
    # file, what, source URL, licence, credit line (empty = none needed)
    ('hdri/studio_small_09_2k.hdr', 'Studio Small 09 HDRI (2k)', 'https://polyhaven.com/a/studio_small_09', 'CC0 (polyhaven.com/license)', ''),
    ('fonts/display.ttf', "the look's display family at its display weight (src/look.json)", 'https://fonts.google.com (fetched by look_fonts.py)',
     'SIL Open Font License 1.1', ''),
    ('earth/blackmarble_8k.jpg', 'NASA Black Marble 2016 (3 km, 8192x4096)', 'https://earthobservatory.nasa.gov/features/NightLights',
     'NASA imagery, not copyrighted in the US (nasa.gov brand center); no NASA insignia, no implied endorsement', 'NASA Earth Observatory'),
    ('earth/bm500_patch.jpg', "NASA Black Marble 2016 tile B1 (500 m), globe.tsx's PATCH bounds at half size (~1 km)",
     'https://science.nasa.gov/earth/earth-observatory/earth-at-night/maps', 'as the world map above', 'NASA Earth Observatory'),
    ('img/demo_people.jpg', 'demo picture: two people in front of a street', 'drawn by kit3d_assets.py', 'no third-party content', ''),
    ('img/demo_city.jpg', 'demo picture: a skyline at dusk', 'drawn by kit3d_assets.py', 'no third-party content', ''),
    ('img/demo_cover.jpg', 'demo cover', 'drawn by kit3d_assets.py', 'no third-party content', ''),
    ('logos/demo_logo.svg', 'demo logo: a badge with white lettering', 'drawn by kit3d_assets.py', 'no third-party content', ''),
    ('clips/demo_phone.mp4', 'demo clip: a moving colour field with shapes', 'drawn by kit3d_assets.py', 'no third-party content', ''),
    ('(model) depth-anything/Depth-Anything-V2-Small-hf', 'monocular depth for Parallax25D (no pixel generated)',
     'https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf', 'Apache-2.0 (Base/Large/Giant are CC-BY-NC: never used)', ''),
    ('(model) birefnet-general (rembg)', 'subject matte for Parallax25D', 'https://github.com/ZhengPeng7/BiRefNet', 'MIT', ''),
]
BY_HAND = ['hdri/studio_small_09_2k.hdr', 'earth/blackmarble_8k.jpg']   # fonts/display.ttf: PIPE tools/motion/look_fonts.py

DEMO_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3A7BD5"/><stop offset="1" stop-color="#7A4FD6"/></linearGradient></defs>
  <rect x="20" y="20" width="1160" height="480" rx="96" fill="url(#g)"/>
  <text x="600" y="350" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-weight="900" font-size="300" fill="#FFFFFF"
        stroke="#101014" stroke-width="22" stroke-linejoin="round" paint-order="stroke">DEMO</text>
</svg>
"""


def link(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not FORCE:
        return
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


# ---------------------------------------------------------------- the demo's drawn pictures
def demo_people(w=3840, h=2160):
    """two people in front of a street: a near subject on a far background, the case Parallax25D is for"""
    im = Image.fromarray(grain(gradient(w, h, (236, 190, 150), (120, 96, 110)), 21, 5))
    d = ImageDraw.Draw(im)
    hz = int(0.58 * h)
    for i, x in enumerate(range(-100, w, 420)):                                   # the street's far blocks
        top = hz - 300 - (i * 173) % 520
        d.rectangle((x, top, x + 380, hz), fill=(96 + (i * 17) % 40, 84 + (i * 11) % 30, 96))
        for wy in range(top + 40, hz - 40, 90):                                   # their windows
            for wx in range(x + 40, x + 340, 90):
                d.rectangle((wx, wy, wx + 44, wy + 50), fill=(250, 214, 150) if (wx + wy + i) % 3 else (70, 64, 80))
    d.rectangle((0, hz, w, h), fill=(70, 66, 72))                                 # the road
    for k in range(6):
        d.rectangle((k * 700 + 100, int(0.78 * h), k * 700 + 420, int(0.80 * h)), fill=(220, 214, 196))
    for (x0, pw, ph, skin, shirt, legs) in ((0.24, 0.20, 0.80, (214, 170, 140), (60, 90, 150), (40, 40, 48)),
                                            (0.53, 0.22, 0.86, (150, 104, 80), (190, 70, 60), (60, 56, 50))):
        cw, ch = int(pw * w), int(ph * h)
        fig = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        person(skin, shirt, legs)(ImageDraw.Draw(fig), cw, ch)
        im.paste(fig, (int(x0 * w), h - ch), fig)
    return im


def demo_city(w=3840, h=2160):
    """a skyline at dusk over water"""
    im = Image.fromarray(grain(gradient(w, h, (40, 52, 110), (236, 140, 96)), 22, 4))
    d = ImageDraw.Draw(im)
    hz = int(0.66 * h)
    for i, x in enumerate(range(-60, w, 230)):
        top = hz - 260 - (i * 211) % 900
        d.rectangle((x, top, x + 200, hz), fill=(28 + (i * 7) % 20, 30, 52))
        for wy in range(top + 30, hz - 30, 70):
            for wx in range(x + 24, x + 180, 52):
                if (wx * 7 + wy * 3 + i) % 5 < 2:
                    d.rectangle((wx, wy, wx + 22, wy + 30), fill=(255, 220, 150))
    water = grain(gradient(w, h - hz, (70, 60, 100), (16, 20, 44)), 23, 6)
    im.paste(Image.fromarray(water), (0, hz))
    return im


def find_browser():
    """a Chromium browser that can draw an SVG headless: Edge or Chrome"""
    c = []
    if WINDOWS:
        for base in (os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)'), os.environ.get('PROGRAMFILES', 'C:/Program Files')):
            c += [Path(base) / 'Microsoft/Edge/Application/msedge.exe', Path(base) / 'Google/Chrome/Application/chrome.exe']
    elif MAC:
        c += [Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
              Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'), Path('/Applications/Chromium.app/Contents/MacOS/Chromium')]
    c += [Path(p) for p in (shutil.which(n) for n in ('msedge', 'google-chrome', 'chromium', 'chrome')) if p]
    for p in c:
        if p.exists():
            return p
    raise SystemExit('kit3d_assets: no Edge or Chrome found (the emblem step draws the SVG with one)')


def to_jpg(src, dst):
    dst = Path(dst)
    if dst.exists() and not FORCE:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if Path(src).suffix.lower() in ('.jpg', '.jpeg'):
        link(src, dst)
    else:
        Image.open(src).convert('RGB').save(dst, quality=95)


def basics(a):
    for sub in ('logos', 'hdri', 'fonts', 'earth', 'img', 'clips'):
        (ROOT / sub).mkdir(parents=True, exist_ok=True)
    for rel, make in (('img/demo_people.jpg', demo_people), ('img/demo_city.jpg', demo_city),
                      ('img/demo_cover.jpg', lambda: poster(1288, 1594, (40, 70, 120), (12, 16, 30), (230, 160, 60), 3))):
        if FORCE or not (ROOT / rel).exists():
            make().save(ROOT / rel, quality=93)
    if FORCE or not (ROOT / 'logos/demo_logo.svg').exists():
        (ROOT / 'logos/demo_logo.svg').write_text(DEMO_LOGO_SVG, encoding='utf-8')
    rows = list(LICENCES)
    for name, src in a.photo:
        to_jpg(src, ROOT / f'img/{name}.jpg')
        rows.append((f'img/{name}.jpg', "the creator's picture", str(Path(src).name), "the creator's (fill in)", ''))
    if a.cover:
        to_jpg(a.cover, ROOT / f'img/{Path(a.cover).stem}.jpg')
        rows.append((f'img/{Path(a.cover).stem}.jpg', "the creator's cover", Path(a.cover).name, "the creator's (fill in)", ''))
    if a.logo:
        link(a.logo, ROOT / f'logos/{Path(a.logo).stem}.svg')
        rows.append((f'logos/{Path(a.logo).stem}.svg', "the creator's logo", Path(a.logo).name, "the creator's (fill in)", ''))
    with open(ROOT / 'LICENCES.tsv', 'w', encoding='utf-8') as f:
        f.write('file\twhat\tsource\tlicence\tcredit\n')
        for row in rows:
            f.write('\t'.join(row) + '\n')
    src = {r[0]: r[2] for r in LICENCES}
    for rel in BY_HAND:
        if not (ROOT / rel).exists() and not (rel == 'earth/blackmarble_8k.jpg' and a.world):
            print(f'basics: place {ROOT / rel} by hand (from {src[rel]})')


# ---------------------------------------------------------------- emblem
def rasterise_svg(svg, png, width=4096):
    """The SVG drawn by a browser (gradients, masks and clip paths exactly as Chrome draws them), on transparency, at `width` px."""
    txt = Path(svg).read_text(encoding='utf-8')
    m = re.search(r'viewBox="([\d.\s-]+)"', txt)
    vx, vy, vw, vh = [float(v) for v in m.group(1).split()]
    h = round(width * vh / vw)
    html = Path(png).with_suffix('.html')
    html.write_text(f'<html><body style="margin:0;background:transparent"><img src="{Path(svg).as_uri()}" '
                    f'style="display:block;width:{width}px;height:{h}px"></body></html>', encoding='utf-8')
    subprocess.run([str(find_browser()), '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--screenshot={png}',
                    f'--window-size={width},{h}', '--default-background-color=00000000', html.as_uri()],
                   check=True, capture_output=True, timeout=120)
    html.unlink()
    return width, h


def trace(mask, eps_px=1.2, min_area=400):
    """Polygons (outer rings with their holes) of a binary mask, in the mask's pixels."""
    import cv2
    cs, hier = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    shapes = []
    if hier is None:
        return shapes
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1:   # a hole: taken with its parent
            continue
        if cv2.contourArea(c) < min_area:
            continue
        outer = cv2.approxPolyDP(c, eps_px, True)[:, 0, :].tolist()
        holes = []
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) >= min_area / 4:
                holes.append(cv2.approxPolyDP(cs[j], eps_px, True)[:, 0, :].tolist())
            j = hier[j][0]
        shapes.append({'outer': outer, 'holes': holes})
    return shapes


def emblem(name='demo_logo'):
    import cv2
    out_png = ROOT / f'logos/{name}_4k.png'
    out_json = ROOT / f'logos/{name}_shape.json'
    if out_json.exists() and not FORCE:
        print('emblem: kept', out_json)
        return
    w, h = rasterise_svg(ROOT / f'logos/{name}.svg', out_png)
    rgba = np.asarray(Image.open(out_png).convert('RGBA'))
    # crop to the logo's ink (+ 16 px), so the face's UVs map the picture's own bounds
    a = rgba[..., 3]
    ys, xs = np.where(a > 8)
    x0, x1, y0, y1 = max(xs.min() - 16, 0), min(xs.max() + 17, w), max(ys.min() - 16, 0), min(ys.max() + 17, h)
    rgba = rgba[y0:y1, x0:x1]
    Image.fromarray(rgba).save(out_png, optimize=True)
    a = rgba[..., 3]
    base = (a > 127).astype(np.uint8)
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    # the raised block: the white lettering and its dark outline (white pixels, closed, grown by the outline's width)
    rgb = rgba[..., :3].astype(np.int16)
    white = ((rgb.min(axis=2) > 225) & (a > 200)).astype(np.uint8)
    white = cv2.morphologyEx(white, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # the outline round the lettering is dark (luminance < 80) and touches the white within ~1.4% of the logo's width; the block is
    # white | that dark ring, holes filled, so it follows the logo's own outline instead of a blob grown from the letters
    k = max(3, round(rgba.shape[1] * 0.014))
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    near = cv2.dilate(white, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
    dark = ((lum < 80) & (a > 200)).astype(np.uint8) & near
    raised = cv2.morphologyEx(white | dark, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    ff = raised.copy()
    cv2.floodFill(ff, None, (0, 0), 1)
    raised = (raised | (1 - ff)) & base   # holes filled (the counters of a, d, e)
    data = {'w': int(rgba.shape[1]), 'h': int(rgba.shape[0]), 'png': f'kit3d/logos/{name}_4k.png',
            'base': trace(base), 'raised': trace(raised, min_area=900)}
    out_json.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    Image.fromarray((np.dstack([base, raised, raised * 0]) * 255).astype(np.uint8)).resize(
        (rgba.shape[1] // 4, rgba.shape[0] // 4)).save(ROOT / f'logos/{name}_shape_check.png')
    print(f'emblem: {out_json} ({len(data["base"])} base shapes, {len(data["raised"])} raised, '
          f'{sum(len(s["outer"]) for s in data["base"])} + {sum(len(s["outer"]) for s in data["raised"])} points)')


# ---------------------------------------------------------------- parallax
def pack16(d01, path):
    v = np.clip(np.round(d01 * 65535), 0, 65535).astype(np.uint32)
    rgb = np.dstack([(v >> 8).astype(np.uint8), (v & 255).astype(np.uint8), np.zeros_like(v, dtype=np.uint8)])
    Image.fromarray(rgb, 'RGB').save(path, optimize=True)


def parallax(name):
    import cv2
    src = ROOT / f'img/{name}.jpg'
    if (ROOT / f'img/{name}_bgdepth.png').exists() and not FORCE:
        print('parallax: kept', name)
        return
    im = Image.open(src).convert('RGB')
    W, H = im.size
    # 1. depth (relative inverse depth: bigger = nearer), at 1920 px
    from transformers import pipeline
    pipe = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf', device='cpu')
    small = im.resize((1920, round(1920 * H / W)), Image.LANCZOS)
    pred = pipe(small)['predicted_depth']
    d = pred.squeeze().numpy().astype(np.float32)
    d = cv2.resize(d, small.size, interpolation=cv2.INTER_CUBIC)
    lo, hi = np.percentile(d, 1), np.percentile(d, 99.7)
    d = np.clip((d - lo) / (hi - lo), 0, 1)
    d = cv2.GaussianBlur(d, (0, 0), 1.5)
    # 2. the subject's matte at full size
    from rembg import new_session, remove
    sess = new_session('birefnet-general')
    m = np.asarray(remove(im, session=sess, only_mask=True)).astype(np.float32) / 255
    if m.shape != (H, W):
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    fg = np.dstack([np.asarray(im), np.round(m * 255).astype(np.uint8)])
    Image.fromarray(fg, 'RGBA').save(ROOT / f'img/{name}_fg.png', optimize=True)
    # 3. the background behind the subject: the matte grown just past its soft edge, filled by Telea (classical) at quarter size,
    #    the fill pasted into the full-size picture only inside the grown matte
    grow = round(W * 0.006)   # just past the matte's soft edge (a wider growth leaves a dark ghost of fill beside the heads)
    hole = cv2.dilate((m > 0.06).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
    q = 4
    small_rgb = cv2.resize(np.asarray(im), (W // q, H // q), interpolation=cv2.INTER_AREA)
    small_hole = cv2.resize(hole, (W // q, H // q), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small_rgb, small_hole, 9, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC)
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 3)[..., None]
    bg = (np.asarray(im).astype(np.float32) * (1 - soft) + filled.astype(np.float32) * soft).round().clip(0, 255).astype(np.uint8)
    Image.fromarray(bg).save(ROOT / f'img/{name}_bg.jpg', quality=93)
    # 4. depths: the subject's own (its depth grown outward so its edge never stretches back to the far depth) and the background's
    #    (the subject's region filled from around it)
    hd = cv2.resize(hole, small.size, interpolation=cv2.INTER_NEAREST)
    md = cv2.resize(m, small.size, interpolation=cv2.INTER_LINEAR)
    d8 = (d * 255).astype(np.uint8)
    bgd = cv2.inpaint(d8, hd, 15, cv2.INPAINT_TELEA).astype(np.float32) / 255
    bgd = np.minimum(bgd, d + 0.02)   # never nearer than what was there
    bgd = cv2.GaussianBlur(bgd, (0, 0), 4)
    # the subject's depth: the model's depth blurs from near to far across the last ~10 px of a silhouette, so a mesh built on it
    # pulls the edge pixels back and they smear into spikes as the camera moves. So the depth is read only from the subject's core
    # (the matte eroded by 14 px), its internal range halved round its median (the people stay one near layer with gentle relief, no
    # tear between two of them), and everything outside the core, edge band included, is filled outward from the core (Telea on the
    # depth) and smoothed: the outline moves exactly with the subject.
    fgd = d.copy()
    inner = md > 0.5
    if inner.any():
        core = cv2.erode(inner.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (29, 29))).astype(bool)
        if core.sum() < 500:
            core = inner
        med = float(np.median(d[core]))
        rel = np.where(core, med + (d - med) * 0.5, 0).astype(np.float32)
        hw, hh = rel.shape[1] // 2, rel.shape[0] // 2   # filled at half size (the fill is smooth by nature), then brought back up
        fill = cv2.inpaint(cv2.resize(rel, (hw, hh), interpolation=cv2.INTER_AREA),
                           cv2.resize((~core).astype(np.uint8), (hw, hh), interpolation=cv2.INTER_NEAREST), 11, cv2.INPAINT_TELEA)
        fill = cv2.resize(fill, (rel.shape[1], rel.shape[0]), interpolation=cv2.INTER_CUBIC)
        fgd = np.where(core, rel, fill)
        fgd = cv2.GaussianBlur(fgd, (0, 0), 5)
    pack16(fgd, ROOT / f'img/{name}_depth.png')
    pack16(bgd, ROOT / f'img/{name}_bgdepth.png')
    # a check sheet: picture, depth, matte, filled background
    sheet = Image.new('RGB', (1920, 1080))
    for i, pic in enumerate([small, Image.fromarray((d * 255).astype(np.uint8)).convert('RGB'),
                             Image.fromarray((m * 255).astype(np.uint8)).convert('RGB'), Image.fromarray(bg)]):
        sheet.paste(pic.resize((960, 540)), ((i % 2) * 960, (i // 2) * 540))
    sheet.save(ROOT / f'img/{name}_check.jpg', quality=88)
    print(f'parallax: {name} ({W}x{H}) depth, matte ({(m > 0.5).mean():.1%} subject), bg filled ({hole.mean():.1%} of the frame)')


# ---------------------------------------------------------------- clip
def clip(a):
    demo = ROOT / 'clips/demo_phone.mp4'
    if FORCE or not demo.exists():
        field_clip(demo, 30, 5.0, 31, (30, 60, 110), (220, 150, 80), 0.3,
                   [(260, 300, 420, 360, '0xF2EEE6'), (1240, 220, 380, 520, '0x2A2E38')], w=1920, h=960)
        print('clip:', demo)
    if not a.clip:
        return
    out = ROOT / f'clips/{Path(a.clip).stem}.mp4'
    if out.exists() and not FORCE:
        print('clip: kept', out)
        return
    # 2:1 round the centre (a 16:9 source loses equal bands top and bottom), 1920 px wide
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-ss', str(a.ss), '-t', str(a.t), '-i', str(a.clip),
                    '-vf', 'crop=iw:trunc(iw/4)*2:0:(ih-trunc(iw/4)*2)/2,scale=1920:960:flags=lanczos', '-an', '-c:v', 'libx264',
                    '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)], check=True)
    print('clip:', out)


# ---------------------------------------------------------------- earth
def patch_bounds():
    """globe.tsx's PATCH {lon0, lon1, lat0, lat1}: the patch is cut to exactly the segment the globe lays it on"""
    if not GLOBE.exists():
        raise SystemExit(f'earth: {GLOBE} is missing (its PATCH names the detail patch\'s bounds)')
    m = re.search(r'PATCH\s*=\s*\{\s*lon0:\s*(-?[\d.]+),\s*lon1:\s*(-?[\d.]+),\s*lat0:\s*(-?[\d.]+),\s*lat1:\s*(-?[\d.]+)',
                  GLOBE.read_text(encoding='utf-8'))
    if not m:
        raise SystemExit(f'earth: no PATCH = {{lon0, lon1, lat0, lat1}} in {GLOBE}')
    lon0, lon1, lat0, lat1 = (float(v) for v in m.groups())
    if not (-90 <= lon0 < lon1 <= 0 and 0 <= lat0 < lat1 <= 90):
        raise SystemExit(f'earth: PATCH {lon0}..{lon1} lon, {lat0}..{lat1} lat is outside tile B1 (90W-0, 0-90N)')
    return lon0, lon1, lat0, lat1


def earth(a):
    """The world map (3 km a pixel, 22.8 px a degree) and the detail patch for close globe moves: NASA Black Marble 2016 at 500 m
    (tile B1: 90W-0, 90N-0, 21600 px square, 240 px a degree), cropped to globe.tsx's PATCH, decoded at half size: ~1 km a pixel, so a
    move that ends inside the patch lands on detail instead of a blur."""
    world = ROOT / 'earth/blackmarble_8k.jpg'
    if a.world:
        link(a.world, world)
    if not world.exists():
        print(f'earth: no world map yet: download NASA Black Marble 2016 (3 km, 8192x4096) from '
              f'https://earthobservatory.nasa.gov/features/NightLights and pass --world <the file>')
    out = ROOT / 'earth/bm500_patch.jpg'
    if out.exists() and not FORCE:
        print('earth: kept', out)
        return
    lon0, lon1, lat0, lat1 = patch_bounds()
    tile = TMP / 'kit3d_bm_B1.jpg'
    if not tile.exists():
        tile.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['curl', '-s', '-L', '-o', str(tile),
                        'https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/144000/144898/BlackMarble_2016_B1.jpg'],
                       check=True)
    # ffmpeg refuses a 21600-px picture and a full RGB decode needs ~1.4 GB of memory: decode at half size with the JPEG's own DCT
    # scaling (draft: 10800 px, 120 px a degree, ~350 MB), still 5x the 8k map's detail
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(tile)
    im.draft('RGB', (10800, 10800))
    k = im.size[0] / 21600
    x0, x1, y0, y1 = (lon0 + 90) * 240, (lon1 + 90) * 240, (90 - lat1) * 240, (90 - lat0) * 240
    im = im.convert('RGB').crop((round(x0 * k), round(y0 * k), round(x1 * k), round(y1 * k)))
    im.save(out, quality=94)
    tile.unlink()
    print('earth:', out)


def link_pub():
    for p in ROOT.rglob('*'):
        if p.is_file() and not p.name.endswith('_check.png') and not p.name.endswith('_check.jpg'):
            link(p, PUB / p.relative_to(ROOT))
    print('link:', PUB)


def main():
    global FORCE
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('what', nargs='?', default='all', choices=['all', 'basics', 'emblem', 'parallax', 'clip', 'earth', 'link'])
    ap.add_argument('--force', action='store_true', help='redo what is already there')
    ap.add_argument('--logo', help="the creator's logo (an SVG): traced as logos/<its name>_shape.json")
    ap.add_argument('--photo', action='append', default=[], type=lambda s: tuple(s.split('=', 1)),
                    help="<name>=<picture>: the creator's picture, made into parallax layers as img/<name>*")
    ap.add_argument('--cover', help="the creator's cover for CaseNumber3D -> img/<its name>.jpg")
    ap.add_argument('--clip', help="the creator's footage for the phone -> clips/<its name>.mp4")
    ap.add_argument('--ss', type=float, default=0.0, help='--clip: the start in s')
    ap.add_argument('--t', type=float, default=5.0, help='--clip: the length in s')
    ap.add_argument('--world', help='the downloaded NASA Black Marble 2016 3-km world map')
    a = ap.parse_args()
    FORCE = a.force
    basics(a)
    if a.what in ('all', 'emblem'):
        emblem('demo_logo')
        if a.logo:
            emblem(Path(a.logo).stem)
    if a.what in ('all', 'parallax'):
        for n in ['demo_people', 'demo_city'] + [name for name, _src in a.photo]:
            parallax(n)
    if a.what in ('all', 'clip'):
        clip(a)
    if a.what in ('all', 'earth'):
        earth(a)
    link_pub()


if __name__ == '__main__':
    main()
