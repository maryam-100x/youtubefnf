"""The Python environments (SETUP.md step 4, tools/requirements/README.md): each one made by the studio's own uv from a Python uv
installs into MEDIA/apps/python (never the computer's own Python, never registered with Windows, no program put on PATH), its pinned
packages installed, its key imports checked, and the studio's start-up file put in (tools/hooks/install_sitecustomize.py), so every
tool in it runs with the studio's own programs and caches. Standard library only: it runs in any Python 3.11+ (the setup runs it with
the pipeline venv's still-empty Python).

    PIPE tools/setup/envs.py                   pipe, edit, vision, accent (the setup's four)
    PIPE tools/setup/envs.py synth             any of them by name (synth: music made in code, step 10)
    PIPE tools/setup/envs.py --check [names]   the imports only

Run again after a file in tools/requirements/ changed (UPDATE.md step 6): it installs that file again into its environment.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import (MAC, PYTHONS, REPO, TOOLS, UV, VENV_ACCENT, VENV_EDIT, VENV_PIPE, VENV_SYNTH, VENV_VISION,  # noqa: E402
                   _venv_python, studio_env)

REQ = TOOLS / "requirements"
# name: (where it lives, the Python it is built on, its pinned packages, what must import)
ENVS = {
    "pipe": (VENV_PIPE, "3.14.0", "pipe.txt", "dj.core, faster_whisper, yt_dlp, parselmouth, mutagen, httpx, PIL, numpy"),
    "edit": (VENV_EDIT, "3.12.10", "edit.txt", "cv2, librosa, torch, rembg, transformers, yt_dlp"),
    "vision": (VENV_VISION, "3.12.10", "vision.txt", "ultralytics, torch, torchvision"),
    # the voice tools themselves: they shim torchaudio before speechbrain loads (a bare `import speechbrain` fails on torchaudio 2.11)
    "accent": (VENV_ACCENT, "3.12.10", "accent.txt", "accent_id, voice_guard_embed"),
    "synth": (VENV_SYNTH, "3.12.10", "synth.txt", "pedalboard, torch"),
}
SETUP_FOUR = ["pipe", "edit", "vision", "accent"]
TORCH_CPU = ["--index-url", "https://download.pytorch.org/whl/cpu", "--extra-index-url", "https://pypi.org/simple",
             "--index-strategy", "unsafe-best-match"]


def env():
    e = dict(os.environ)
    s = studio_env()
    e.update(s["set"])
    key = next((k for k in e if k.upper() == "PATH"), "PATH")
    e[key] = os.pathsep.join(s["path"] + [p for p in e.get(key, "").split(os.pathsep) if p and p not in s["path"]])
    return e


def uv(*args):
    print("  uv " + " ".join(str(a) for a in args), flush=True)
    r = subprocess.run([UV, *[str(a) for a in args]], env=env())
    if r.returncode:
        raise SystemExit(f"uv {args[0]} {args[1] if len(args) > 1 else ''} failed ({r.returncode})")


def check(name):
    place, _, _, mods = ENVS[name]
    py = _venv_python(Path(place))
    code = (f"import sys; sys.path[:0] = [{str(TOOLS)!r}, {str(TOOLS / 'voice')!r}]; import {mods}; "
            "print(sys.version.split()[0])")
    r = subprocess.run([str(py), "-c", code], capture_output=True, text=True, env=env(), cwd=str(REPO))
    ok = r.returncode == 0
    detail = r.stdout.strip() if ok else (r.stderr.strip().splitlines() or ["?"])[-1]
    print(f"{name:7s} {'ok ' if ok else 'BAD'} python {detail if ok else ''} {py}" + ("" if ok else f"\n        {detail}"))
    return ok


def build(name):
    place, version, req, _ = ENVS[name]
    place = Path(place)
    py = _venv_python(place)
    print(f"{name}: {place} (Python {version}, {req})", flush=True)
    uv("python", "install", version, "--install-dir", PYTHONS, "--no-bin", "--no-registry")
    if not py.exists():
        uv("venv", place, "--python", version)
    torch = any(ln.startswith("torch==") for ln in (REQ / req).read_text(encoding="utf-8").splitlines())
    extra = TORCH_CPU if torch and not MAC else []
    uv("pip", "install", "-r", REQ / req, "--python", py, *extra)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help=f"any of {', '.join(ENVS)} (default: {', '.join(SETUP_FOUR)})")
    ap.add_argument("--check", action="store_true", help="check the imports only")
    a = ap.parse_args()
    names = a.names or SETUP_FOUR
    bad = [n for n in names if n not in ENVS]
    if bad:
        ap.error(f"no environment {bad}; there are {list(ENVS)}")
    if not Path(UV).is_absolute():
        raise SystemExit("the studio's own uv isn't installed yet (SETUP.md step 2)")
    if not a.check:
        for n in names:
            build(n)
        subprocess.run([sys.executable, str(TOOLS / "hooks" / "install_sitecustomize.py")], check=True)
    ok = [check(n) for n in names]
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
