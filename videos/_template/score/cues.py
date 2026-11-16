"""The cue sheet of a video: its whole soundtrack, music and effects, on the narration's words (standard/SOUND_AND_VOICE.md, step 7;
the music: standard/MUSIC.md). Copy this file to videos/<id>-<slug>/score/cues<id>.py, set SRC, and point video.toml [score] cues at
it. Built by the pipeline's score step (`PIPE tools/pipeline/pipe.py <video> score`) or `EDIT tools/sound/score.py <this file> <out.wav>`.
After the creator's first finished video, start each new sheet from the newest finished video's sheet instead of this one."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools" / "sound"))
sys.path.insert(0, str(REPO / "tools" / "common"))
from paths import MOTION, MUSIC, VIDEOS  # noqa: E402,F401
from score import PALETTE, Cue, Film, Sfx, code_beds, pal  # noqa: E402,F401

VIDEO = HERE.parent.name                       # videos/<id>-<slug>
SRC = MOTION / "src" / "v12"                   # the video's tools/motion/src/<src> (video.toml [video] src)
BUILD = VIDEOS / VIDEO / "build"
FILM = F = Film(SRC / "words.json", SRC / "beats.json")
VOICE = str(BUILD / "voice" / "narration.wav")
DURATION = FILM.duration

# ---- the mix (standard/SOUND_AND_VOICE.md, "Music: the mixing rules"; a Short: the Shorts values there)
UNDER = 13.0              # each music cue's level under the voice: the measured "voice-music" in the report is the bar (~22 dB)
GAP_MIN = 22.0            # under speech the music is held at least this far under the voice (250-ms windows)
DUCK_DB = 5.0
CARVE_DB = 8.0
SIDE_DUCK_DB = 2.5
LEVEL_BEDS = 0.6          # the creator's own tracks: their builds and drops evened out (code beds carry level 0: written steady)
LEVEL_JUMP = 2.0
HANDOFF_STYLE = "smooth"
VOICE_COMP = None         # the voice comes in finished from its chain; never compressed again
MIX_LUFS = -14.0
MIX_CEIL = -1.2

# ---- the music: one of the two sources (the creator's choice, creator/PROFILE.md), or both in one video
# Music made in code: the beds tools/music rendered for this video (SYNTH tools/music/music.py render videos/<video>/score/music.py)
CUES = code_beds(BUILD / "music", under=UNDER)
# The creator's own tracks instead (each measured and gridded first: analyze_tracks.py, grid.py), e.g.:
# CUES = [
#     Cue("A", str(MUSIC / "<folder>" / "<track>.wav"), 0.0, F.b("S04"), align=(<a downbeat in the track>, 0.0), under=UNDER,
#         exit="button"),
#     Cue("B", str(MUSIC / "<folder>" / "<track>.wav"), F.b("S04"), DURATION, align=(<its downbeat>, F.b("S04")), under=UNDER,
#         hold_in=True, exit="fade", fout=1.0),
# ]

SILENCES = []             # designed silences (film seconds): [(t0, t1), ...]; the mix never drops to silence outside them

# ---- the effects: autocues.py's lines plus the chat's own (the statement drop, impacts, clicks...), every one a rated sound
SFX = [
    # Sfx(pal("bass_drop"), F.w("S02", "<the statement's key word>"), db=PALETTE["bass_drop"]["db"], note="statement drop"),
]
