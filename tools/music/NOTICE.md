# tools/music: licences and credits

| Part | Licence | In this repository? |
|---|---|---|
| `tools/music/` (this code, its example) | the repository's licence | yes |
| **Surge XT** 1.3.4 (the Surge Synth Team, github.com/surge-synthesizer/surge) | GPL-3.0. The audio it renders is not covered by its licence: the music is the creator's | no: the setup installs it (`standard/MUSIC.md`, the install) |
| Surge XT's patches (`patches_factory/`, `patches_3rdparty/`) | shipped inside the GPL-3.0 Surge repository, which names no separate licence for them | no `.fxp` files: every sound is named by its path in the library every Surge XT install ships |
| **pedalboard** 0.9.26 (Spotify) | GPL-3.0 | no (installed from PyPI into the SYNTH environment) |
| mido 1.3.3 | MIT | no (PyPI) |
| librosa 1.0.1 | ISC | no (PyPI) |
| soundfile 0.14.0 | BSD-3-Clause | no (PyPI) |
| numpy 2.5.4, scipy 1.18.1 | BSD | no (PyPI) |
| torch 2.15.0, torchaudio 2.11.1 | BSD-style | no (PyTorch's CPU index) |
| **Audiobox Aesthetics** (Meta): the package `audiobox_aesthetics` 0.0.4 and its checkpoint `facebook/audiobox-aesthetics` | CC-BY 4.0: credit it where it is used | no (PyPI; the checkpoint downloads from Hugging Face into `MEDIA/models/hf`) |

`tools/music/` imports pedalboard (GPL-3.0) and drives Surge XT (GPL-3.0): anyone who passes on a copy of this code with those parts
should pass it on under GPL-3.0 terms. The quality model is credited as: *Audiobox Aesthetics, Meta (CC-BY 4.0).* Nothing here is
legal advice.

Nothing of any audio is in this repository: no renders, no stems, no recordings, no patch files, no model weights. The example's
narration is a made-up text (`example/script.txt`) with generated word times; `music.py stand-in` makes a speech-shaped test signal
from those times, which is not speech.
