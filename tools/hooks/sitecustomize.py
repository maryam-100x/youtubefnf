"""Loaded by Python at every start in the repo's venvs (a copy sits in each one's site-packages; this file is the source,
`tools/hooks/install_sitecustomize.py` puts it there again after a venv is rebuilt). A character the terminal's code page can't write
prints as '?' instead of crashing the tool: a mix or a gate that prints an arrow or a tick to a file or a pipe would otherwise die on a
UnicodeEncodeError when run without PYTHONIOENCODING (Windows' cp1252). Only the error handling changes, never the encoding, so
whatever reads the output reads the same bytes as before."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        # a UTF stream writes every character already; any other (cp1252) gets 'replace', whatever it had (Git Bash's runs start
        # with 'surrogateescape', which still raises on an arrow)
        if _s is not None and not str(getattr(_s, "encoding", "") or "").lower().replace("-", "").startswith("utf"):
            _s.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
