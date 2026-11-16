# The Python environments

Four environments (five when the music is made in code), each pinned to the exact versions the pipeline was built and tested on.
`tools/setup/envs.py` builds them (`SETUP.md` step 4) with the studio's own `uv` on Pythons it installs into `MEDIA/apps/python`
(never the computer's own Python; nothing put on PATH or into Windows' registry), and checks each one's key imports:
`PIPE tools/setup/envs.py` (the four), `PIPE tools/setup/envs.py synth` (one by name), `--check` (the imports only).

| Environment | Python | File | Where it lives | What runs in it |
|---|---|---|---|---|
| PIPE | 3.14.0 | `pipe.txt` | `<repo>/tools/.venv` | the pipeline: `dj` (voice, captions), sound, voice tools, the gate, hooks, faster-whisper, yt-dlp |
| EDIT | 3.12.10 | `edit.txt` | `MEDIA/envs/edit` | pictures and QA: OpenCV, cut-outs, librosa, torch (CPU), the script tools |
| VISION | 3.12.10 | `vision.txt` | `MEDIA/envs/vision` | object detection for the footage brain (YOLO) |
| ACCENT | 3.12.10 | `accent.txt` | `MEDIA/envs/accent` | the accent check on voice takes (speechbrain) |
| SYNTH | 3.12.10 | `synth.txt` | `MEDIA/envs/synth` | music made in code (`tools/music/`): Surge XT through pedalboard, the quality model (Audiobox Aesthetics). Only when the creator chose music made in code |

Torch is pinned as the CPU build: on Windows and Linux envs.py installs a file that holds torch from PyTorch's CPU index
(`--index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match`); on
macOS the plain PyPI wheels are the CPU/Metal build. Packages marked `sys_platform` install only where they apply (the NVIDIA
libraries for faster-whisper's GPU path and pywin32 on Windows). A package added by hand goes in the same way, through the studio's
uv: `uv pip install <package> --python <env python>` (in PowerShell through `PIPE tools/common/paths.py --run`), and into the file
here when it stays.
