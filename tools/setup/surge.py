"""Install Surge XT for music made in code (the setup's step 10, only when the creator chose it): download the official build, check
its size and MD5 against the release's, and put it into MEDIA/apps/surge-xt/Surge Synth Team/ as the plugin and its library
(SurgeXTData), nothing outside the studio's folders:
  Windows  the portable zip, unpacked with a safe extractor (no member may land outside the folder), plus an empty SurgeXTUserData
           folder beside the library: Surge's own portable marker, so its user folder stays here instead of Documents
  macOS    the signed .dmg, mounted read-only; its .pkg expanded with pkgutil (no installer, no install scripts, no admin password)
           and the plugin bundle and the library copied out (Surge's package names: scripts/installer_mac/make_installer.sh at
           release_xt_1.3.4). The music tools point Surge at the library with SURGE_DATA_HOME. Surge on a Mac always keeps a small
           user folder in ~/Documents/Surge XT (its macOS code has no portable user folder).

    PIPE tools/setup/surge.py            # download (if missing), check, unpack, then confirm the plugin and the library are found
    PIPE tools/setup/surge.py --check    # confirm only

The creator's one go for the setup's installs covers it (SETUP.md); --plan prints the file, its source and its size.
    PIPE tools/setup/surge.py --plan
"""
import hashlib
import shutil
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


def unpack_mac(dmg, dest):
    """The plugin and its library out of the .dmg without its installer: Surge XT.vst3 from the VST3 package's payload, the
    library (the folder holding patches_factory) from the resources package's payload."""
    team = dest / "Surge Synth Team"
    if (team / "Surge XT.vst3").exists() and (team / "SurgeXTData" / "patches_factory").exists():
        print(f"{team} already holds Surge XT: left as it is")
        return
    mnt, out = TMP / "surge_dmg", TMP / "surge_pkg"
    shutil.rmtree(out, ignore_errors=True)
    mnt.mkdir(parents=True, exist_ok=True)
    subprocess.run(["hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", str(mnt), str(dmg)], check=True,
                   stdout=subprocess.DEVNULL)
    try:
        pkgs = sorted(p for p in mnt.rglob("*.pkg") if p.is_file())
        if not pkgs:
            raise SystemExit(f"no installer package inside {dmg.name}: nothing copied")
        subprocess.run(["pkgutil", "--expand-full", str(pkgs[0]), str(out)], check=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mnt)], check=False, stdout=subprocess.DEVNULL)
    vst3 = out / "Surge_XT_VST3.pkg" / "Payload" / "Surge XT.vst3"
    if not vst3.is_dir():
        vst3 = next((p for p in out.rglob("Surge XT.vst3") if p.is_dir()), None)
    data = next((p.parent for p in out.rglob("patches_factory") if p.is_dir()), None)
    if not vst3 or not data:
        raise SystemExit(f"the package's layout changed (plugin: {vst3}, library: {data}): nothing copied; see {out}")
    team.mkdir(parents=True, exist_ok=True)
    shutil.copytree(vst3, team / "Surge XT.vst3", symlinks=True, dirs_exist_ok=True)
    shutil.copytree(data, team / "SurgeXTData", symlinks=True, dirs_exist_ok=True)
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(dest)], check=False, stderr=subprocess.DEVNULL)
    shutil.rmtree(out, ignore_errors=True)
    print(f"copied the plugin and its library into {team} (no installer run)")


def keep_user_folder_here():
    """Windows: Surge walks up from its plugin for a SurgeXTUserData folder and keeps its user folder there; without one it makes
    Documents/Surge XT (which a synced Documents folder then uploads)."""
    team = DEST / "Surge Synth Team"
    if WINDOWS and team.is_dir():
        (team / "SurgeXTUserData").mkdir(exist_ok=True)


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
            unpack_mac(f, DEST)
    keep_user_folder_here()
    check()


if __name__ == "__main__":
    main()
