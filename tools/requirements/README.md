# The Python environments

Four environments (five when the music is made in code), each pinned to the exact versions the pipeline was built and tested on. The setup (`SETUP.md`) creates them with
`uv` (one tool that installs the right Python and the packages on Windows and macOS).

| Environment | Python | File | Where it lives | What runs in it |
|---|---|---|---|---|
| PIPE | 3.14 | `pipe.txt` | `<repo>/tools/.venv` | the pipeline: `dj` (voice, captions), sound, voice tools, the gate, hooks, faster-whisper, yt-dlp |
| EDIT | 3.12 | `edit.txt` | `MEDIA/envs/edit` | pictures and QA: OpenCV, cut-outs, librosa, torch (CPU), the script tools |
| VISION | 3.12 | `vision.txt` | `MEDIA/envs/vision` | object detection for the footage brain (YOLO) |
| ACCENT | 3.12 | `accent.txt` | `MEDIA/envs/accent` | the accent check on voice takes (speechbrain) |
| SYNTH | 3.12 | `synth.txt` | `MEDIA/envs/synth` | music made in code (`tools/music/`): Surge XT through pedalboard, the quality model (Audiobox Aesthetics). Only when the creator chose music made in code |

Torch is pinned as the CPU build. On Windows and Linux install it from PyTorch's CPU index:
`uv pip install -r tools/requirements/edit.txt --python <env python> --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match`.
On macOS the plain PyPI wheels are the CPU/Metal build: no extra index. Packages marked `sys_platform` install only where they apply
(the NVIDIA libraries for faster-whisper's GPU path and pywin32 on Windows).
