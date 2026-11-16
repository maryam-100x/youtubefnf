"""Loaded by Python at every start in the repo's venvs (a copy sits in each one's site-packages; this file is the source,
`tools/hooks/install_sitecustomize.py` puts it there again after a venv is rebuilt). Two things, for every tool that runs in a venv:

1. The studio's own environment (tools/common/paths.py: studio_env). `studio_env.json`, written next to this copy by the installer,
   lists the studio's program folders (put first on PATH) and its cache variables (set). So a tool that starts ffmpeg, node or npx,
   or a library that downloads a model, uses the studio's own copies and folders in MEDIA, never the computer's, whether or not the
   tool imports paths.py.
2. A character the terminal's code page can't write prints as '?' instead of crashing the tool: a mix or a gate that prints an arrow
   or a tick to a file or a pipe would otherwise die on a UnicodeEncodeError when run without PYTHONIOENCODING (Windows' cp1252).
   Only the error handling changes, never the encoding, so whatever reads the output reads the same bytes as before."""
import json
import os
import sys

try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_env.json"), encoding="utf-8") as _f:
        _env = json.load(_f)
    if os.path.isdir(_env.get("media", "")):   # folders a library must find (Ultralytics falls back to C:/tmp without its own)
        for _d in _env.get("dirs", []):
            os.makedirs(_d, exist_ok=True)
    for _k, _v in _env.get("set", {}).items():
        os.environ[_k] = _v
    _first = _env.get("path", [])
    _key = next((k for k in os.environ if k.upper() == "PATH"), "PATH")
    _rest = [p for p in os.environ.get(_key, "").split(os.pathsep) if p and p not in _first]
    os.environ[_key] = os.pathsep.join(_first + _rest)
except FileNotFoundError:
    pass
except Exception:  # noqa: BLE001   never stop a Python from starting
    pass

for _s in (sys.stdout, sys.stderr):
    try:
        # a UTF stream writes every character already; any other (cp1252) gets 'replace', whatever it had (Git Bash's runs start
        # with 'surrogateescape', which still raises on an arrow)
        if _s is not None and not str(getattr(_s, "encoding", "") or "").lower().replace("-", "").startswith("utf"):
            _s.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
