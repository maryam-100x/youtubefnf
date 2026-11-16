"""Install Surge XT for music made in code (the setup's step 10, only when the creator chose it): download the official build, check
its size and MD5 against the release's, and on Windows unpack it into MEDIA/apps/surge-xt with a safe extractor (no member may land
outside the folder). On macOS it downloads and checks the .dmg and opens it: the creator clicks through Surge's installer.

    PIPE tools/setup/surge.py            # download (if missing), check, unpack/open, then confirm the plugin and the library are found
    PIPE tools/setup/surge.py --check    # confirm only

The creator's one go for the setup's installs covers it (SETUP.md); --plan prints the file, its source and its size.
    PIPE tools/setup/surge.py --plan
"""
import hashlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import APPS, MAC, TMP, WINDOWS  # noqa: E402

UA = {"User-Agent": "studio-setup"}
BASE = "https://github.com/surge-synthesizer/releases-xt/releases/download/1.3.4/"
BUILDS = {  # the release's own md5sum.txt
    "windows": ("surge-xt-win64-1.3.4-portable-install.zip", 301_759_660, "30023479e71252e91a7b7a9a59cbaa7d"),
    "mac": ("surge-xt-macOS-1.3.4.dmg", None, "8d64166483e704f7b07fd1893b3c4dd9"),
}
DEST = APPS / "surge-xt"


def build():
    if WINDOWS:
        return BUILDS["windows"]
    if MAC:
        return BUILDS["mac"]
    raise SystemExit("Linux: install Surge XT 1.3.4 from the release's .deb/.rpm (github.com/surge-synthesizer/releases-xt), then "
                     "set surge_xt_vst3 and surge_xt_data in config/paths.toml if it is not in /usr/lib/vst3 and /usr/share/surge-xt")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(name, size, digest):
    f = TMP / "downloads" / name
    f.parent.mkdir(parents=True, exist_ok=True)
    if not (f.exists() and md5(f) == digest):
        print(f"downloading {BASE + name} ...", flush=True)
        part = f.with_name(f.name + ".part")
        with urllib.request.urlopen(urllib.request.Request(BASE + name, headers=UA), timeout=60) as r, open(part, "wb") as o:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                o.write(b)
        part.replace(f)
    if size and f.stat().st_size != size:
        raise SystemExit(f"{f}: {f.stat().st_size} bytes, the release says {size}: not used (delete it and run again)")
    if md5(f) != digest:
        raise SystemExit(f"{f}: MD5 {md5(f)}, the release says {digest}: not used (delete it and run again)")
    print(f"{name}: size and MD5 match the release")
    return f


def unpack(z, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        print(f"{dest} is not empty: left as it is")
        return
    root = dest.resolve()
    with zipfile.ZipFile(z) as zf:
        for m in zf.infolist():
            target = (dest / m.filename).resolve()
            if root not in target.parents and target != root:
                raise SystemExit(f"unsafe name in the zip: {m.filename!r}: nothing unpacked")
        zf.extractall(dest)
    print(f"unpacked into {dest}")


def check():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "music"))
    from musickit.settings import surge_paths
    vst3, data = surge_paths()
    n = sum(1 for _ in (data / "patches_factory").rglob("*.fxp")) + sum(1 for _ in (data / "patches_3rdparty").rglob("*.fxp"))
    print(f"Surge XT found: plugin {vst3}, library {data} ({n} patches)")


def main():
    name, size, digest = build()
    if "--plan" in sys.argv:
        print(f"file {name}, from {BASE + name}, " + (f"{size / 1e6:.0f} MB" if size else "~300 MB") + f", MD5 {digest}")
        return
    if "--check" not in sys.argv:
        f = download(name, size, digest)
        if WINDOWS:
            unpack(f, DEST)
        else:
            subprocess.run(["open", str(f)], check=False)
            print("Surge's installer is open: the creator clicks through it (the default places), then run this with --check")
            return
    check()


if __name__ == "__main__":
    main()
