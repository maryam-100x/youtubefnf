"""The studio's own programs (SETUP.md step 2): uv, Node.js and ffmpeg, each a pinned release checked against its published SHA-256 and
unpacked into MEDIA/apps. The studio never uses, updates or removes a program the computer already has: these copies are its own, and
every tool finds them through tools/common/paths.py (UV, NODE, NPM, NPX, FFMPEG, FFPROBE and the PATH of studio_env). The Pythons are
uv's job (tools/setup/envs.py, into MEDIA/apps/python). Standard library only: it runs in any Python 3.11+.

    PIPE tools/setup/apps.py            install what is missing or not at its pinned version, then check every program
    PIPE tools/setup/apps.py --check    check only
    PIPE tools/setup/apps.py --plan     what would be downloaded, from where, how big

A new version of the studio that moves a pin brings the new copy in the same way (UPDATE.md step 6): the old folder is replaced.
"""
import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import APPS, FFMPEG, FFPROBE, MAC, NODE, NPM, TMP, UV, WINDOWS  # noqa: E402

UA = {"User-Agent": "studio-setup"}
UV_VERSION = "0.13.6"
NODE_VERSION = "24.14.1"
FFMPEG_VERSION = {"windows": "8.0.1", "mac": "9.0.2"}
_GH_UV = f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/"
_NODE = f"https://nodejs.org/dist/v{NODE_VERSION}/"
_FF_WIN = "https://github.com/GyanD/codexffmpeg/releases/download/8.0.1/ffmpeg-8.0.1-full_build.zip"
_FF_MAC = "https://ffmpeg.martin-riedl.de/download/macos/"
# per platform: (url, sha256) of each archive (the releases' own published digests)
PINS = {
    "windows-x64": {
        "uv": [(_GH_UV + "uv-x86_64-pc-windows-msvc.zip", "a2a8820d5eea32f08ef467ef3b7f66883a9b076d5737a2fc2fbb5f458d1bb50f")],
        "node": [(_NODE + f"node-v{NODE_VERSION}-win-x64.zip", "6e50ce5498c0cebc20fd39ab3ff5df836ed2f8a31aa093cecad8497cff126d70")],
        "ffmpeg": [(_FF_WIN, "467cde100a47ed4b03a897988aeb4a296890c1e2b2d2864204657d002bc5fb90")],
    },
    "windows-arm64": {
        "uv": [(_GH_UV + "uv-aarch64-pc-windows-msvc.zip", "c2426c0c8e28b53d8c440e47a18d96ad4db51e159866c0e81435b196d7f0081c")],
        "node": [(_NODE + f"node-v{NODE_VERSION}-win-arm64.zip", "a7b7c68490e4a8cde1921fe5a0cfb3001d53f9c839e416903e4f28e727b62f60")],
        "ffmpeg": [(_FF_WIN, "467cde100a47ed4b03a897988aeb4a296890c1e2b2d2864204657d002bc5fb90")],   # x64, runs emulated
    },
    "mac-arm64": {
        "uv": [(_GH_UV + "uv-aarch64-apple-darwin.tar.gz", "60fbd5c8a1ed681845eea28d9d622fcde03c51e91a43465b64a1e17db1ed3472")],
        "node": [(_NODE + f"node-v{NODE_VERSION}-darwin-arm64.tar.gz", "25495ff85bd89e2d8a24d88566d7e2f827c6b0d3d872b2cebf75371f93fcb1fe")],
        "ffmpeg": [(_FF_MAC + "arm64/1789931890_9.0.2/ffmpeg.zip", "c8ed4c4e6978a03c485edbfe4e0a5dc2380f8a30bba5150531b31b094492d924"),
                   (_FF_MAC + "arm64/1789931890_9.0.2/ffprobe.zip", "fcbe839537485eaee7a7a8bc5cbc0f90d53617e80943e8a5b2e31cb851197ea6")],
    },
    "mac-x64": {
        "uv": [(_GH_UV + "uv-x86_64-apple-darwin.tar.gz", "63ba17fdda55ad1a230d4b37fc6017ffa10c23688c83818bd3bfdf914c652a02")],
        "node": [(_NODE + f"node-v{NODE_VERSION}-darwin-x64.tar.gz", "2526230ad7d922be82d4fdb1e7ee1e84303e133e3b4b0ec4c2897ab31de0253d")],
        "ffmpeg": [(_FF_MAC + "amd64/1789931006_9.0.2/ffmpeg.zip", "7c6b4125b191cbf773832dc51f424cf2b6bb7da43007d1e066f95909e47cacd4"),
                   (_FF_MAC + "amd64/1789931006_9.0.2/ffprobe.zip", "2322438ed2f6319a691291b247d09c69dcaa3a982460d1f269a7e1af335cfdfd")],
    },
}


def plat():
    m = platform.machine().lower()
    arm = m in ("arm64", "aarch64")
    if WINDOWS:
        return "windows-arm64" if arm else "windows-x64"
    if MAC:
        return "mac-arm64" if arm else "mac-x64"
    raise SystemExit("Linux: install uv, Node.js 24 and ffmpeg into MEDIA/apps by hand (uv/, node/bin/, ffmpeg/bin/), or set the "
                     "programs' keys in config/paths.toml")


def version_of(cmd, args):
    """The program's version line, or None when it doesn't run."""
    try:
        r = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (r.stdout or r.stderr or "").strip().splitlines()
    return out[0] if r.returncode == 0 and out else None


def wanted():
    """name -> (program to run, its version arguments, the text its version line must hold)"""
    ff = FFMPEG_VERSION["windows" if WINDOWS else "mac"]
    return {
        "uv": (UV, ["--version"], f"uv {UV_VERSION}"),
        "node": (NODE, ["--version"], f"v{NODE_VERSION}"),
        "ffmpeg": (FFMPEG, ["-version"], f"version {ff}"),
    }


def state():
    """name -> (ok, the version line it has)"""
    out = {}
    for name, (cmd, args, want) in wanted().items():
        own = Path(cmd).is_absolute() and str(Path(cmd)).startswith(str(APPS))
        v = version_of(cmd, args) if own else None
        out[name] = (bool(v and want in v), v)
    if out["ffmpeg"][0]:
        out["ffmpeg"] = (bool(version_of(FFPROBE, ["-version"])), out["ffmpeg"][1])
    return out


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(url, digest):
    f = TMP / "downloads" / url.rstrip("/").split("/")[-1]
    if "martin-riedl" in url:  # ffmpeg.zip and ffprobe.zip: keep the architecture and build in the name
        f = f.with_name(url.split("/")[-2] + "_" + f.name)
    f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists() and sha256(f) == digest:
        return f
    print(f"  downloading {url}", flush=True)
    part = f.with_name(f.name + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, open(part, "wb") as o:
        shutil.copyfileobj(r, o, 1 << 20)
    got = sha256(part)
    if got != digest:
        part.unlink()
        raise SystemExit(f"{url}: SHA-256 {got} is not the published {digest}; nothing installed")
    part.replace(f)
    return f


def unpack(archive, into):
    """Unpack with no member landing outside `into` (zip: checked by path; tar: the 'data' filter)."""
    into.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        root = into.resolve()
        with zipfile.ZipFile(archive) as z:
            for m in z.infolist():
                dest = (into / m.filename).resolve()
                if root != dest and root not in dest.parents:
                    raise SystemExit(f"{archive.name}: {m.filename} would land outside {into}")
            z.extractall(into)
    else:
        with tarfile.open(archive) as t:
            t.extractall(into, filter="data")


def lift(folder):
    """An archive with one top folder: that folder, else the folder itself."""
    kids = [p for p in folder.iterdir()]
    return kids[0] if len(kids) == 1 and kids[0].is_dir() else folder


def install(name, pins):
    new = APPS / f".{name}.new"
    if new.exists():
        shutil.rmtree(new)
    stage = APPS / f".{name}.unpack"
    if stage.exists():
        shutil.rmtree(stage)
    for url, digest in pins:
        unpack(download(url, digest), stage)
    if name == "ffmpeg" and MAC:  # two single-file zips: the programs go into bin/, made runnable
        (new / "bin").mkdir(parents=True)
        for exe in ("ffmpeg", "ffprobe"):
            shutil.move(str(stage / exe), new / "bin" / exe)
            os.chmod(new / "bin" / exe, 0o755)
        shutil.rmtree(stage)
    else:
        shutil.move(str(lift(stage)), new)
        if stage.exists():
            shutil.rmtree(stage)
    if name == "uv" and not WINDOWS:
        for exe in ("uv", "uvx"):
            if (new / exe).exists():
                os.chmod(new / exe, 0o755)
    if name == "node":
        (new / "studio.npmrc").write_text("# the studio's npm settings (empty: npm's defaults, never the user's own .npmrc)\n",
                                          encoding="utf-8")
    final = APPS / name
    if final.exists():   # the studio's own older copy: replaced (deleted for good; nothing of the computer's is ever here)
        shutil.rmtree(final)
    new.replace(final)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="check only")
    ap.add_argument("--plan", action="store_true", help="what would be downloaded, from where, how big")
    a = ap.parse_args()
    pins = PINS[plat()]
    st = state()
    if a.plan:
        for name, (ok, v) in st.items():
            for url, _ in pins[name]:
                if ok:
                    print(f"{name:7s} ok ({v})")
                    break
                req = urllib.request.Request(url, headers=UA, method="HEAD")
                try:
                    with urllib.request.urlopen(req, timeout=30) as r:
                        size = int(r.headers.get("Content-Length") or 0)
                except OSError:
                    size = 0
                print(f"{name:7s} {url}  {size / 1e6:.0f} MB -> {APPS / name}")
        return 0
    if not a.check:
        APPS.mkdir(parents=True, exist_ok=True)
        for name, (ok, v) in st.items():
            if not ok:
                print(f"{name}: installing the studio's own copy into {APPS / name}", flush=True)
                install(name, pins[name])
    # the programs' paths come from paths.py at import; a fresh process sees the new copies
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import apps; apps.report()",
                        str(Path(__file__).resolve().parent)])
    return r.returncode


def report():
    bad = 0
    for name, (ok, v) in state().items():
        cmd = wanted()[name][0]
        print(f"{name:7s} {'ok ' if ok else 'BAD'} {v or 'not found'}   {cmd}")
        bad += not ok
    if not bad:
        print(f"npm     ok  {version_of(NPM, ['--version'])}   {NPM}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    sys.exit(main())
