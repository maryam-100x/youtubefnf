# tools/music: music made in code

Background music for a narrated video, written note by note on the narration's own words and played offline by a professional synth
(Surge XT, free). The method, the rules, the bar and the order of work are in `standard/MUSIC.md`; this folder is the code.

| Path | What it is |
|---|---|
| `music.py` | the one command: `render` (every bed of a video), `selftest`, `patches`, `audition`, `pick`, `check`, `mixdown`, `bands`, `judge`, `stand-in`, `ab` |
| `musickit/settings.py` | where things live (Surge XT from `config/paths.toml` through `tools/common/paths.py`) |
| `musickit/surge.py` | Surge XT driven offline from Python (pedalboard; a patch loaded as the plugin's state) |
| `musickit/compose.py` | the bar clock, chords and voice leading, tracks, per-layer shaping, the bus, `render_bed` (one WAV + metadata + grid) |
| `musickit/writing.py` | the bed-writing helpers (word lookups, `clock`, `fit_bpm`, `prog`, `arp16`, `eighths`, `held`, `subs`) and the sound kit |
| `musickit/bands.py`, `judge.py` | the checks against the bar: where the energy sits, and the stand-in ear (Audiobox Aesthetics) |
| `musickit/audition.py`, `pick.py`, `patch_check.py` | choosing sounds: measured alone in bulk, picked in context, checked for octave and added tones |
| `musickit/mixdown.py` | rebalancing a bed from its stems without rendering again |
| `musickit/loudness.py` | BS.1770 loudness (the same measure as `tools/sound/score.py`) |
| `musickit/stand_in_voice.py`, `ab_pair.py` | a speech-shaped test signal from word times; a blind pair for the creator's ears |
| `musickit/selftest.py` | the logic checked offline (no synth, no model, no audio packages) |
| `example/` | a made-up two-minute film ("How bridges are built"): its script, its word times for two voices, its music file `film.py` (the template for a video's `videos/<video>/score/music.py`), a pick list |
| `NOTICE.md` | licences and credits |

The beds go under the voice through the video's cue sheet (`code_beds(...)` in `tools/sound/score.py`): one mixer for every video,
whatever made its music. Commands run in the SYNTH environment (`tools/requirements/synth.txt`); `selftest` also runs in EDIT.
