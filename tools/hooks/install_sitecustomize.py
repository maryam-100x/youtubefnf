"""Puts tools/hooks/sitecustomize.py into every venv of the repo that exists (the pipeline, editing, vision and accent venvs of
tools/common/paths.py). The setup runs it once after building the venvs; run it again after a venv is rebuilt:
  PIPE tools/hooks/install_sitecustomize.py
Windows venvs keep their packages in <venv>/Lib/site-packages, macOS and Linux ones in <venv>/lib/python3.X/site-packages."""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from paths import VENV_ACCENT, VENV_EDIT, VENV_PIPE, VENV_VISION  # noqa: E402

SRC = Path(__file__).resolve().parent / "sitecustomize.py"
VENVS = [VENV_PIPE, VENV_EDIT, VENV_VISION, VENV_ACCENT]


def site_packages(venv):
    win = venv / "Lib" / "site-packages"
    if win.is_dir():
        return [win]
    return sorted(p for p in venv.glob("lib/python3*/site-packages") if p.is_dir())


for v in VENVS:
    found = site_packages(Path(v))
    for sp in found:
        shutil.copyfile(SRC, sp / "sitecustomize.py")
        print(f"installed -> {sp / 'sitecustomize.py'}")
    if not found:
        print(f"no venv at {v}")
