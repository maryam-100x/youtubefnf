"""Makes an instant voice clone in the creator's ElevenLabs account from their recorded sample (SETUP.md step 9), so they never
upload anything by hand. Prints the new voice's id, which goes into config/tts.toml. The key is read only inside
dj.tts.elevenlabs_key() and never printed.

    PIPE tools/voice/clone_voice.py "<voice name>" <sample.wav> [<more files of the same voice>]

Run it only for a voice the creator chose to make (their own recording); it never touches the account's other voices. ElevenLabs'
background-noise removal stays off: the sample is either clean already or rebuilt (rebuild_sample.py), and the removal can thin
the voice. Endpoint: POST https://api.elevenlabs.io/v1/voices/add (multipart: name, files), as ElevenLabs' API reference and
official Python SDK send it.
"""
import json
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dj.tts import elevenlabs_key  # noqa: E402

URL = "https://api.elevenlabs.io/v1/voices/add"


def clone(name, files):
    parts = [("files", (Path(f).name, Path(f).read_bytes(), "audio/wav" if str(f).lower().endswith(".wav") else
                        "application/octet-stream")) for f in files]
    r = httpx.post(URL, headers={"xi-api-key": elevenlabs_key()}, data={"name": name, "remove_background_noise": "false"},
                   files=parts, timeout=300)
    if r.status_code != 200:
        raise SystemExit(f"ElevenLabs refused the clone ({r.status_code}): {r.text[:600]}")
    return r.json()


def main():
    if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    name, files = sys.argv[1], sys.argv[2:]
    missing = [f for f in files if not Path(f).is_file()]
    if missing:
        raise SystemExit(f"no such file: {', '.join(missing)}")
    d = clone(name, files)
    print(f"VOICE {d.get('voice_id')} {json.dumps(name)}")
    if d.get("requires_verification"):
        print("ElevenLabs asks to verify this voice before it can be used: the creator opens it in My Voices and follows the steps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
